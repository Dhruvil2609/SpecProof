using System.Net.Http.Json;
using System.Text.Json;

namespace SpecProof.Platform.Api;

public interface ITechPackImportGateway
{
    Task<JsonElement> ImportAsync(
        Stream content,
        string fileName,
        string contentType,
        Guid techPackId,
        int version,
        string brand,
        string styleCode,
        string garmentCategory,
        CancellationToken cancellationToken);

    Task<JsonElement> ValidateAsync(
        JsonElement techPack,
        string sizeCode,
        CancellationToken cancellationToken);
}

public sealed class TechPackImportGateway(HttpClient httpClient) : ITechPackImportGateway
{
    public async Task<JsonElement> ImportAsync(
        Stream content,
        string fileName,
        string contentType,
        Guid techPackId,
        int version,
        string brand,
        string styleCode,
        string garmentCategory,
        CancellationToken cancellationToken)
    {
        using var requestContent = new MultipartFormDataContent();
        using var fileContent = new StreamContent(content);
        fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(contentType);
        requestContent.Add(fileContent, "file", fileName);
        requestContent.Add(new StringContent(techPackId.ToString()), "tech_pack_id");
        requestContent.Add(new StringContent(version.ToString(System.Globalization.CultureInfo.InvariantCulture)), "version");
        requestContent.Add(new StringContent(brand), "brand");
        requestContent.Add(new StringContent(styleCode), "style_code");
        requestContent.Add(new StringContent(garmentCategory), "garment_category");

        using var response = await httpClient.PostAsync(
            "v1/tech-packs/import",
            requestContent,
            cancellationToken);
        return await ReadResponseAsync(response, cancellationToken);
    }

    public async Task<JsonElement> ValidateAsync(
        JsonElement techPack,
        string sizeCode,
        CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "v1/tech-packs/validate",
            new { techPack, sizeCode },
            cancellationToken);
        return await ReadResponseAsync(response, cancellationToken);
    }

    private static async Task<JsonElement> ReadResponseAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        var payload = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(
                $"Measurement service returned {(int)response.StatusCode}: {payload}",
                null,
                response.StatusCode);
        }

        using var document = JsonDocument.Parse(payload);
        return document.RootElement.Clone();
    }
}
