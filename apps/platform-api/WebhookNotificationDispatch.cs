using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using SpecProof.Contracts;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api;

public enum NotificationDispatchOutcome
{
    Completed,
    RetryScheduled,
    DeadLettered,
}

public sealed record WebhookNotificationPayload(
    Guid SubscriptionId,
    Guid EventId,
    string EventType,
    string PayloadJson);

public sealed record WebhookNotificationEnqueueResult(IReadOnlyList<Guid> JobIds);

public sealed class WebhookNotificationQueue
{
    public const string QueueName = "notifications";
    public const string JobType = "webhook.dispatch";

    public async Task<WebhookNotificationEnqueueResult> EnqueueAsync(
        SpecProofDbContext database,
        WebhookNotificationRequest request,
        CancellationToken cancellationToken)
    {
        using var _ = JsonDocument.Parse(request.PayloadJson);
        var subscriptions = await database.WebhookSubscriptions
            .Where(subscription => subscription.TenantId == request.TenantId && subscription.Active)
            .ToArrayAsync(cancellationToken);
        var matchingSubscriptions = subscriptions.Where(subscription =>
            JsonSerializer.Deserialize<string[]>(
                subscription.EventTypesJson,
                SpecProofJsonOptions.Canonical)?.Contains(
                    request.EventType,
                    StringComparer.Ordinal) == true);
        var nowUtc = DateTimeOffset.UtcNow;
        var jobIds = new List<Guid>();
        foreach (var subscription in matchingSubscriptions)
        {
            var jobId = CreateJobId(subscription.Id, request.EventId, request.EventType);
            jobIds.Add(jobId);
            if (await database.BackgroundJobs.AnyAsync(job => job.Id == jobId, cancellationToken))
            {
                continue;
            }

            var payload = new WebhookNotificationPayload(
                subscription.Id,
                request.EventId,
                request.EventType,
                request.PayloadJson);
            database.BackgroundJobs.Add(
                new BackgroundJobRecord
                {
                    Id = jobId,
                    TenantId = request.TenantId,
                    QueueName = QueueName,
                    JobType = JobType,
                    PayloadJson = JsonSerializer.Serialize(payload, SpecProofJsonOptions.Canonical),
                    Status = "queued",
                    AvailableAtUtc = nowUtc,
                    CreatedAtUtc = nowUtc,
                    UpdatedAtUtc = nowUtc,
                });
        }

        await database.SaveChangesAsync(cancellationToken);
        return new WebhookNotificationEnqueueResult(jobIds);
    }

    public static string SecretKeyId(Guid subscriptionId) => $"webhook-{subscriptionId:N}";

    private static Guid CreateJobId(Guid subscriptionId, Guid eventId, string eventType)
    {
        var key = $"{subscriptionId:N}:{eventId:N}:{eventType}";
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(key));
        return new Guid(hash.AsSpan(0, 16));
    }
}

public sealed class WebhookNotificationDispatcher(
    HttpClient httpClient,
    ISecureKeyStorage keyStorage,
    ILogger<WebhookNotificationDispatcher> logger)
{
    private const int MaximumAttempts = 5;

    public async Task<NotificationDispatchOutcome> DispatchAsync(
        SpecProofDbContext database,
        BackgroundJobRecord job,
        CancellationToken cancellationToken)
    {
        if (job.QueueName != WebhookNotificationQueue.QueueName
            || job.JobType != WebhookNotificationQueue.JobType)
        {
            throw new ArgumentException("The job is not a webhook notification.", nameof(job));
        }

        job.Status = "processing";
        job.Attempts++;
        job.StartedAtUtc = DateTimeOffset.UtcNow;
        job.UpdatedAtUtc = job.StartedAtUtc.Value;
        await database.SaveChangesAsync(cancellationToken);

        try
        {
            var payload = JsonSerializer.Deserialize<WebhookNotificationPayload>(
                job.PayloadJson,
                SpecProofJsonOptions.Canonical)
                ?? throw new JsonException("Webhook notification payload is missing.");
            var subscription = await database.WebhookSubscriptions.IgnoreQueryFilters()
                .SingleOrDefaultAsync(
                    candidate =>
                        candidate.Id == payload.SubscriptionId
                        && candidate.TenantId == job.TenantId
                        && candidate.Active,
                    cancellationToken)
                ?? throw new InvalidOperationException("The webhook subscription is unavailable.");
            var secret = await keyStorage.LoadAsync(
                WebhookNotificationQueue.SecretKeyId(subscription.Id),
                cancellationToken);
            try
            {
                var body = Encoding.UTF8.GetBytes(payload.PayloadJson);
                var signature = Convert.ToHexString(HMACSHA256.HashData(secret, body)).ToLowerInvariant();
                using var request = new HttpRequestMessage(HttpMethod.Post, subscription.Url)
                {
                    Content = new ByteArrayContent(body),
                };
                request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
                request.Headers.Add("X-SpecProof-Event", payload.EventType);
                request.Headers.Add("X-SpecProof-Event-Id", payload.EventId.ToString());
                request.Headers.Add("X-SpecProof-Signature", $"sha256={signature}");
                using var response = await httpClient.SendAsync(request, cancellationToken);
                response.EnsureSuccessStatusCode();
            }
            finally
            {
                CryptographicOperations.ZeroMemory(secret);
            }

            job.Status = "completed";
            job.CompletedAtUtc = DateTimeOffset.UtcNow;
            job.UpdatedAtUtc = job.CompletedAtUtc.Value;
            await database.SaveChangesAsync(cancellationToken);
            return NotificationDispatchOutcome.Completed;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            var deadLettered = job.Attempts >= MaximumAttempts;
            job.Status = deadLettered ? "dead_letter" : "queued";
            job.AvailableAtUtc = DateTimeOffset.UtcNow.AddSeconds(Math.Pow(2, job.Attempts));
            job.CompletedAtUtc = deadLettered ? DateTimeOffset.UtcNow : null;
            job.UpdatedAtUtc = DateTimeOffset.UtcNow;
            await database.SaveChangesAsync(cancellationToken);
            logger.LogWarning(
                exception,
                "Webhook notification job {JobId} attempt {Attempt} failed; status is {Status}",
                job.Id,
                job.Attempts,
                job.Status);
            return deadLettered
                ? NotificationDispatchOutcome.DeadLettered
                : NotificationDispatchOutcome.RetryScheduled;
        }
    }
}

public sealed class WebhookNotificationWorker(
    IServiceScopeFactory scopeFactory,
    ILogger<WebhookNotificationWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await ProcessNextAsync(stoppingToken);
            }
            catch (Exception exception) when (exception is not OperationCanceledException)
            {
                logger.LogError(exception, "Notification worker iteration failed");
            }

            await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken);
        }
    }

    private async Task ProcessNextAsync(CancellationToken cancellationToken)
    {
        await using var scope = scopeFactory.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        var nowUtc = DateTimeOffset.UtcNow;
        var job = await database.BackgroundJobs.IgnoreQueryFilters()
            .Where(candidate =>
                candidate.QueueName == WebhookNotificationQueue.QueueName
                && candidate.JobType == WebhookNotificationQueue.JobType
                && candidate.Status == "queued"
                && candidate.AvailableAtUtc <= nowUtc)
            .OrderBy(candidate => candidate.AvailableAtUtc)
            .ThenBy(candidate => candidate.Id)
            .FirstOrDefaultAsync(cancellationToken);
        if (job is null)
        {
            return;
        }

        var dispatcher = scope.ServiceProvider.GetRequiredService<WebhookNotificationDispatcher>();
        await dispatcher.DispatchAsync(database, job, cancellationToken);
    }
}

public sealed record WebhookNotificationRequest(
    Guid TenantId,
    Guid EventId,
    string EventType,
    string PayloadJson) : ITenantBoundRequest;

public sealed record WebhookNotificationResponse(IReadOnlyList<Guid> JobIds);
