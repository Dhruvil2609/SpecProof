using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using SpecProof.Contracts;
using SpecProof.Platform.Api;
using SpecProof.Platform.Data;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class WebhookNotificationDispatchTests
{
    [Fact]
    public async Task EnqueueAsync_MatchingActiveSubscription_IsIdempotent()
    {
        await using var database = CreateDatabase();
        var subscription = CreateSubscription();
        database.WebhookSubscriptions.Add(subscription);
        await database.SaveChangesAsync();
        var queue = new WebhookNotificationQueue();
        var request = new WebhookNotificationRequest(
            subscription.TenantId,
            Guid.NewGuid(),
            "inspection.completed",
            "{\"inspectionId\":\"inspection-1\"}");

        var first = await queue.EnqueueAsync(database, request, CancellationToken.None);
        var replay = await queue.EnqueueAsync(database, request, CancellationToken.None);

        Assert.Single(first.JobIds);
        Assert.Equal(first.JobIds, replay.JobIds);
        var job = Assert.Single(await database.BackgroundJobs.ToArrayAsync());
        Assert.Equal(WebhookNotificationQueue.QueueName, job.QueueName);
        Assert.Equal(WebhookNotificationQueue.JobType, job.JobType);
    }

    [Fact]
    public async Task DispatchAsync_QueuedJob_SendsSignedJsonAndCompletes()
    {
        await using var database = CreateDatabase();
        var subscription = CreateSubscription();
        database.WebhookSubscriptions.Add(subscription);
        var queue = new WebhookNotificationQueue();
        await database.SaveChangesAsync();
        var eventId = Guid.NewGuid();
        const string body = "{\"inspectionId\":\"inspection-1\"}";
        var enqueue = await queue.EnqueueAsync(
            database,
            new WebhookNotificationRequest(
                subscription.TenantId,
                eventId,
                "inspection.completed",
                body),
            CancellationToken.None);
        var job = await database.BackgroundJobs.SingleAsync(candidate => candidate.Id == enqueue.JobIds[0]);
        var secret = Encoding.UTF8.GetBytes("webhook-secret");
        var handler = new CapturingHandler();
        var dispatcher = new WebhookNotificationDispatcher(
            new HttpClient(handler),
            new InMemoryKeyStorage(WebhookNotificationQueue.SecretKeyId(subscription.Id), secret),
            NullLogger<WebhookNotificationDispatcher>.Instance);

        var outcome = await dispatcher.DispatchAsync(database, job, CancellationToken.None);

        Assert.Equal(NotificationDispatchOutcome.Completed, outcome);
        Assert.Equal("completed", job.Status);
        Assert.Equal(1, job.Attempts);
        Assert.NotNull(job.CompletedAtUtc);
        Assert.Equal(body, handler.Body);
        Assert.Equal("inspection.completed", handler.EventType);
        Assert.Equal(eventId.ToString(), handler.EventId);
        var expectedSignature = Convert.ToHexString(
            HMACSHA256.HashData(secret, Encoding.UTF8.GetBytes(body))).ToLowerInvariant();
        Assert.Equal($"sha256={expectedSignature}", handler.Signature);
    }

    [Theory]
    [InlineData(0, NotificationDispatchOutcome.RetryScheduled, "queued")]
    [InlineData(4, NotificationDispatchOutcome.DeadLettered, "dead_letter")]
    public async Task DispatchAsync_FailedDelivery_TransitionsRetryAndDeadLetterState(
        int initialAttempts,
        NotificationDispatchOutcome expectedOutcome,
        string expectedStatus)
    {
        await using var database = CreateDatabase();
        var subscription = CreateSubscription();
        database.WebhookSubscriptions.Add(subscription);
        await database.SaveChangesAsync();
        var queue = new WebhookNotificationQueue();
        var enqueue = await queue.EnqueueAsync(
            database,
            new WebhookNotificationRequest(
                subscription.TenantId,
                Guid.NewGuid(),
                "inspection.completed",
                "{\"inspectionId\":\"inspection-1\"}"),
            CancellationToken.None);
        var job = await database.BackgroundJobs.SingleAsync(candidate => candidate.Id == enqueue.JobIds[0]);
        job.Attempts = initialAttempts;
        await database.SaveChangesAsync();
        var availableBeforeDispatch = job.AvailableAtUtc;
        var dispatcher = new WebhookNotificationDispatcher(
            new HttpClient(new CapturingHandler(HttpStatusCode.ServiceUnavailable)),
            new InMemoryKeyStorage(
                WebhookNotificationQueue.SecretKeyId(subscription.Id),
                Encoding.UTF8.GetBytes("webhook-secret")),
            NullLogger<WebhookNotificationDispatcher>.Instance);

        var outcome = await dispatcher.DispatchAsync(database, job, CancellationToken.None);

        Assert.Equal(expectedOutcome, outcome);
        Assert.Equal(expectedStatus, job.Status);
        Assert.Equal(initialAttempts + 1, job.Attempts);
        Assert.True(job.AvailableAtUtc > availableBeforeDispatch);
        Assert.Equal(
            expectedOutcome == NotificationDispatchOutcome.DeadLettered,
            job.CompletedAtUtc is not null);
    }

    private static SpecProofDbContext CreateDatabase()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseInMemoryDatabase($"webhook-notification-{Guid.NewGuid():N}")
            .Options;
        return new SpecProofDbContext(options);
    }

    private static WebhookSubscription CreateSubscription()
    {
        var nowUtc = DateTimeOffset.UtcNow;
        return new WebhookSubscription
        {
            Id = Guid.NewGuid(),
            TenantId = Guid.NewGuid(),
            Url = "https://webhook.example.test/events",
            EventTypesJson = JsonSerializer.Serialize(
                new[] { "inspection.completed" },
                SpecProofJsonOptions.Canonical),
            SecretHashSha256 = new string('a', 64),
            Active = true,
            CreatedAtUtc = nowUtc,
            UpdatedAtUtc = nowUtc,
        };
    }

    private sealed class InMemoryKeyStorage(string keyId, byte[] keyMaterial) : ISecureKeyStorage
    {
        public Task StoreAsync(
            string requestedKeyId,
            ReadOnlyMemory<byte> requestedKeyMaterial,
            CancellationToken cancellationToken) =>
            throw new NotSupportedException();

        public Task<byte[]> LoadAsync(string requestedKeyId, CancellationToken cancellationToken)
        {
            Assert.Equal(keyId, requestedKeyId);
            return Task.FromResult(keyMaterial.ToArray());
        }
    }

    private sealed class CapturingHandler(
        HttpStatusCode responseStatusCode = HttpStatusCode.Accepted) : HttpMessageHandler
    {
        public string? Body { get; private set; }

        public string? EventType { get; private set; }

        public string? EventId { get; private set; }

        public string? Signature { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            Body = await request.Content!.ReadAsStringAsync(cancellationToken);
            EventType = request.Headers.GetValues("X-SpecProof-Event").Single();
            EventId = request.Headers.GetValues("X-SpecProof-Event-Id").Single();
            Signature = request.Headers.GetValues("X-SpecProof-Signature").Single();
            return new HttpResponseMessage(responseStatusCode);
        }
    }
}
