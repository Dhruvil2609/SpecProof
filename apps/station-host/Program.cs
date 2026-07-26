namespace SpecProof.Station.Host;

public static class Program
{
    public static void Main()
    {
        var clock = new SystemClock();
        Console.WriteLine($"specproof.station.started_at_utc={clock.UtcNow():O}");
    }
}

public interface IClock
{
    DateTimeOffset UtcNow();
}

public sealed class SystemClock : IClock
{
    public DateTimeOffset UtcNow() => DateTimeOffset.UtcNow;
}
