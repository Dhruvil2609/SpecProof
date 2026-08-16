namespace SpecProof.Station.Host;

public static class StationEnvironment
{
    public const string EnvironmentFileVariable = "SPEC_PROOF_STATION_ENV_FILE";

    private static readonly string[] AllowedPrefixes =
        ["SPEC_PROOF_", "OTEL_", "ASPNETCORE_", "DOTNET_"];

    public static void LoadConfiguredFile()
    {
        var path = Environment.GetEnvironmentVariable(EnvironmentFileVariable);
        if (string.IsNullOrWhiteSpace(path))
        {
            return;
        }

        foreach (var pair in ParseFile(path))
        {
            if (Environment.GetEnvironmentVariable(pair.Key) is null)
            {
                Environment.SetEnvironmentVariable(pair.Key, pair.Value);
            }
        }
    }

    public static IReadOnlyDictionary<string, string> ParseFile(string path)
    {
        if (!File.Exists(path))
        {
            throw new FileNotFoundException("The configured station environment file was not found.", path);
        }

        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var rawLine in File.ReadLines(path))
        {
            var line = rawLine.Trim();
            if (line.Length == 0 || line.StartsWith('#'))
            {
                continue;
            }

            var separator = line.IndexOf('=');
            if (separator <= 0)
            {
                throw new InvalidDataException("Station environment entries must use KEY=VALUE syntax.");
            }

            var key = line[..separator].Trim();
            var value = line[(separator + 1)..].Trim();
            if (!AllowedPrefixes.Any(prefix => key.StartsWith(prefix, StringComparison.Ordinal)))
            {
                throw new InvalidDataException($"Station environment key is not allowed: {key}");
            }
            if (value.Length == 0)
            {
                throw new InvalidDataException($"Station environment value is empty: {key}");
            }
            if (!values.TryAdd(key, value))
            {
                throw new InvalidDataException($"Station environment key is duplicated: {key}");
            }
        }

        return values;
    }
}
