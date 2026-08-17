using System.Security.Cryptography;
using SpecProof.Platform.Api;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class SecureKeyStorageTests
{
    [Fact]
    public async Task ProtectedFileKeyStorage_StoreAndLoad_PersistsOnlyCiphertext()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"specproof-keys-{Guid.NewGuid():N}");
        try
        {
            var storage = new ProtectedFileKeyStorage(new TestKeyProtector(), directory);
            var plaintext = "unit-test-signing-key-material"u8.ToArray();

            await storage.StoreAsync("evidence-key-v1", plaintext, CancellationToken.None);
            var persisted = await File.ReadAllBytesAsync(
                Path.Combine(directory, "evidence-key-v1.key"));
            var loaded = await storage.LoadAsync("evidence-key-v1", CancellationToken.None);

            Assert.NotEqual(plaintext, persisted);
            Assert.Equal(plaintext, loaded);
        }
        finally
        {
            if (Directory.Exists(directory))
            {
                Directory.Delete(directory, recursive: true);
            }
        }
    }

    [Theory]
    [InlineData("../outside")]
    [InlineData("nested/key")]
    [InlineData("key with spaces")]
    public async Task ProtectedFileKeyStorage_UnsafeKeyId_RejectsPathTraversal(string keyId)
    {
        var storage = new ProtectedFileKeyStorage(
            new TestKeyProtector(),
            Path.Combine(Path.GetTempPath(), $"specproof-keys-{Guid.NewGuid():N}"));

        await Assert.ThrowsAsync<ArgumentException>(() =>
            storage.StoreAsync(keyId, new byte[] { 1 }, CancellationToken.None));
    }

    [Fact(Skip = "Requires a Windows host with persistent CNG key-provider access")]
    public void WindowsCngKeyProtector_SoftwareProvider_RoundTripsWithNonExportableKey()
    {
        if (!OperatingSystem.IsWindows())
        {
            return;
        }

        var keyName = $"SpecProof-Test-{Guid.NewGuid():N}";
        try
        {
            using var protector = new WindowsCngKeyProtector(keyName, machineScope: false);
            var plaintext = RandomNumberGenerator.GetBytes(32);

            var protectedMaterial = protector.Protect(plaintext);
            var unprotected = protector.Unprotect(protectedMaterial);

            Assert.Equal(CngProvider.MicrosoftSoftwareKeyStorageProvider.Provider, protector.ProviderName);
            Assert.NotEqual(plaintext, protectedMaterial);
            Assert.Equal(plaintext, unprotected);
            using var key = CngKey.Open(
                keyName,
                CngProvider.MicrosoftSoftwareKeyStorageProvider);
            Assert.Equal(CngExportPolicies.None, key.ExportPolicy);
        }
        finally
        {
            try
            {
                using var key = CngKey.Open(
                    keyName,
                    CngProvider.MicrosoftSoftwareKeyStorageProvider);
                key.Delete();
            }
            catch (CryptographicException)
            {
                // The test key was already removed by the provider.
            }
        }
    }

    private sealed class TestKeyProtector : ISecureKeyProtector
    {
        public string ProviderName => "unit-test";

        public byte[] Protect(ReadOnlySpan<byte> keyMaterial) => Transform(keyMaterial);

        public byte[] Unprotect(ReadOnlySpan<byte> protectedKeyMaterial) =>
            Transform(protectedKeyMaterial);

        private static byte[] Transform(ReadOnlySpan<byte> value)
        {
            var transformed = value.ToArray();
            for (var index = 0; index < transformed.Length; index++)
            {
                transformed[index] ^= 0xA5;
            }

            return transformed;
        }
    }
}
