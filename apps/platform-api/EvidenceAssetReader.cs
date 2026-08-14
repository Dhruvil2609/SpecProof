using System.Collections.Concurrent;

namespace SpecProof.Platform.Api;

public sealed record EvidenceAsset(Stream Content, string ContentType, string FileName);

public interface IEvidenceAssetReader
{
    Task<EvidenceAsset?> ReadAsync(
        Guid tenantId,
        string bucket,
        string objectKey,
        CancellationToken cancellationToken);
}

public sealed class FileSystemEvidenceAssetReader(IConfiguration configuration) : IEvidenceAssetReader
{
    private readonly string root = configuration["ObjectStorage:EvidenceRoot"]
        ?? Path.Combine(AppContext.BaseDirectory, "evidence-assets");

    public Task<EvidenceAsset?> ReadAsync(
        Guid tenantId,
        string bucket,
        string objectKey,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var expectedPrefix = $"{tenantId:N}/";
        if (!string.Equals(bucket, TenantObjectStorageNamespace.BuildBucketName(tenantId), StringComparison.Ordinal)
            || !objectKey.StartsWith(expectedPrefix, StringComparison.Ordinal))
        {
            return Task.FromResult<EvidenceAsset?>(null);
        }

        var bucketRoot = Path.GetFullPath(Path.Combine(root, bucket));
        var path = Path.GetFullPath(Path.Combine(bucketRoot, objectKey.Replace('/', Path.DirectorySeparatorChar)));
        if (!path.StartsWith(bucketRoot + Path.DirectorySeparatorChar, StringComparison.Ordinal)
            || !File.Exists(path))
        {
            return Task.FromResult<EvidenceAsset?>(null);
        }

        EvidenceAsset asset = new(
            File.OpenRead(path),
            ContentTypeFor(path),
            Path.GetFileName(path));
        return Task.FromResult<EvidenceAsset?>(asset);
    }

    private static string ContentTypeFor(string path) => Path.GetExtension(path).ToLowerInvariant() switch
    {
        ".jpg" or ".jpeg" => "image/jpeg",
        ".png" => "image/png",
        ".json" => "application/json",
        _ => "application/octet-stream",
    };
}

public sealed class InMemoryEvidenceAssetReader : IEvidenceAssetReader
{
    private readonly ConcurrentDictionary<(Guid TenantId, string Bucket, string Key), byte[]> assets = new();

    public void Add(Guid tenantId, string bucket, string objectKey, byte[] content) =>
        assets[(tenantId, bucket, objectKey)] = content;

    public Task<EvidenceAsset?> ReadAsync(
        Guid tenantId,
        string bucket,
        string objectKey,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(
            assets.TryGetValue((tenantId, bucket, objectKey), out var content)
                ? new EvidenceAsset(new MemoryStream(content, writable: false), "application/octet-stream", Path.GetFileName(objectKey))
                : null);
    }
}
