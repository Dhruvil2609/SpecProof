using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace SpecProof.Platform.Api;

public interface ISecureKeyProtector
{
    string ProviderName { get; }

    byte[] Protect(ReadOnlySpan<byte> keyMaterial);

    byte[] Unprotect(ReadOnlySpan<byte> protectedKeyMaterial);
}

public interface ISecureKeyStorage
{
    Task StoreAsync(string keyId, ReadOnlyMemory<byte> keyMaterial, CancellationToken cancellationToken);

    Task<byte[]> LoadAsync(string keyId, CancellationToken cancellationToken);
}

public sealed partial class ProtectedFileKeyStorage(
    ISecureKeyProtector protector,
    string storageDirectory) : ISecureKeyStorage
{
    public async Task StoreAsync(
        string keyId,
        ReadOnlyMemory<byte> keyMaterial,
        CancellationToken cancellationToken)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(keyId);
        if (keyMaterial.IsEmpty)
        {
            throw new ArgumentException("Key material cannot be empty.", nameof(keyMaterial));
        }

        var destination = ResolvePath(keyId);
        Directory.CreateDirectory(storageDirectory);
        var temporary = Path.Combine(
            storageDirectory,
            $".{Path.GetFileName(destination)}.{Guid.NewGuid():N}.tmp");
        var protectedMaterial = protector.Protect(keyMaterial.Span);
        try
        {
            await File.WriteAllBytesAsync(temporary, protectedMaterial, cancellationToken);
            File.Move(temporary, destination, overwrite: true);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(protectedMaterial);
            if (File.Exists(temporary))
            {
                File.Delete(temporary);
            }
        }
    }

    public async Task<byte[]> LoadAsync(string keyId, CancellationToken cancellationToken)
    {
        var source = ResolvePath(keyId);
        var protectedMaterial = await File.ReadAllBytesAsync(source, cancellationToken);
        try
        {
            return protector.Unprotect(protectedMaterial);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(protectedMaterial);
        }
    }

    private string ResolvePath(string keyId)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(keyId);
        if (!SafeKeyId().IsMatch(keyId))
        {
            throw new ArgumentException(
                "Key IDs may contain only letters, numbers, periods, underscores, and hyphens.",
                nameof(keyId));
        }

        return Path.Combine(storageDirectory, $"{keyId}.key");
    }

    [GeneratedRegex(@"\A[A-Za-z0-9][A-Za-z0-9._-]{0,99}\z", RegexOptions.CultureInvariant)]
    private static partial Regex SafeKeyId();
}

[SupportedOSPlatform("windows")]
public sealed class WindowsCngKeyProtector : ISecureKeyProtector, IDisposable
{
    private readonly CngKey wrappingKey;

    public WindowsCngKeyProtector(
        string wrappingKeyName,
        bool requireTpm = false,
        bool machineScope = true)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(wrappingKeyName);
        var provider = requireTpm
            ? CngProvider.MicrosoftPlatformCryptoProvider
            : CngProvider.MicrosoftSoftwareKeyStorageProvider;
        var openOptions = machineScope ? CngKeyOpenOptions.MachineKey : CngKeyOpenOptions.None;
        var creationOptions = machineScope
            ? CngKeyCreationOptions.MachineKey
            : CngKeyCreationOptions.None;
        wrappingKey = KeyExists(wrappingKeyName, provider, openOptions)
            ? CngKey.Open(wrappingKeyName, provider, openOptions)
            : CngKey.Create(
                CngAlgorithm.Rsa,
                wrappingKeyName,
                new CngKeyCreationParameters
                {
                    Provider = provider,
                    ExportPolicy = CngExportPolicies.None,
                    KeyCreationOptions = creationOptions,
                    KeyUsage = CngKeyUsages.Decryption,
                    Parameters =
                    {
                        new CngProperty(
                            "Length",
                            BitConverter.GetBytes(3072),
                            CngPropertyOptions.None),
                    },
                });
        ProviderName = provider.Provider;
    }

    public string ProviderName { get; }

    public byte[] Protect(ReadOnlySpan<byte> keyMaterial)
    {
        using var rsa = new RSACng(wrappingKey);
        return rsa.Encrypt(keyMaterial, RSAEncryptionPadding.OaepSHA256);
    }

    public byte[] Unprotect(ReadOnlySpan<byte> protectedKeyMaterial)
    {
        using var rsa = new RSACng(wrappingKey);
        return rsa.Decrypt(protectedKeyMaterial, RSAEncryptionPadding.OaepSHA256);
    }

    public void Dispose() => wrappingKey.Dispose();

    private static bool KeyExists(
        string keyName,
        CngProvider provider,
        CngKeyOpenOptions openOptions)
    {
        try
        {
            return CngKey.Exists(keyName, provider, openOptions);
        }
        catch (CryptographicException)
        {
            return false;
        }
    }
}
