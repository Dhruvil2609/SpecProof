using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Routing;
using Microsoft.EntityFrameworkCore;
using SpecProof.Contracts;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api;

public static class WebApplicationEndpoints
{
    public static RouteGroupBuilder MapWebApplicationEndpoints(this RouteGroupBuilder api)
    {
        api.MapGet("/web/dashboard", GetDashboardAsync)
            .WithName("GetWebDashboard")
            .RequireSpecProofPermission(PlatformPermissions.ReadInspections);
        api.MapGet("/web/inspections", GetInspectionsAsync)
            .WithName("GetWebInspections")
            .RequireSpecProofPermission(PlatformPermissions.ReadInspections);
        api.MapGet("/web/inspections/{id:guid}", GetInspectionAsync)
            .WithName("GetWebInspection")
            .RequireSpecProofPermission(PlatformPermissions.ReadInspections);
        api.MapPost("/web/inspections/{id:guid}/reviews", ReviewInspectionAsync)
            .WithName("ReviewWebInspection")
            .RequireSpecProofPermission(PlatformPermissions.ReviewInspections);
        api.MapGet("/web/evidence/{id:guid}", GetEvidenceAsync)
            .WithName("GetWebEvidence")
            .RequireSpecProofPermission(PlatformPermissions.VerifyEvidence);
        api.MapGet("/web/evidence/{id:guid}/asset", GetEvidenceAssetAsync)
            .WithName("GetWebEvidenceAsset")
            .RequireSpecProofPermission(PlatformPermissions.VerifyEvidence);
        api.MapPost("/web/tech-packs/import", ImportTechPackAsync)
            .WithName("ImportWebTechPack")
            .DisableAntiforgery()
            .RequireSpecProofPermission(PlatformPermissions.ManageSpecs);
        api.MapPost("/web/tech-packs/imports/{draftId:guid}/approve", ApproveTechPackImportAsync)
            .WithName("ApproveWebTechPackImport")
            .RequireSpecProofPermission(PlatformPermissions.ManageSpecs);
        return api;
    }

    private static async Task<IResult> ImportTechPackAsync(
        HttpRequest request,
        ITechPackImportGateway gateway,
        SpecProofDbContext database,
        TenantScopeAccessor tenantScope,
        CancellationToken cancellationToken)
    {
        if (!request.HasFormContentType)
        {
            return Results.Problem(statusCode: StatusCodes.Status415UnsupportedMediaType);
        }

        var form = await request.ReadFormAsync(cancellationToken);
        var file = form.Files.GetFile("file");
        if (file is null)
        {
            return Results.ValidationProblem(
                new Dictionary<string, string[]> { ["file"] = ["A tech-pack file is required."] });
        }

        var techPackId = Guid.TryParse(form["techPackId"], out var parsedTechPackId)
            ? parsedTechPackId
            : Guid.NewGuid();
        var version = int.TryParse(form["version"], out var parsedVersion) && parsedVersion > 0
            ? parsedVersion
            : 1;
        var brand = form["brand"].ToString();
        var styleCode = form["styleCode"].ToString();
        var category = form["garmentCategory"].ToString();
        await using var stream = file.OpenReadStream();
        JsonElement imported;
        try
        {
            imported = await gateway.ImportAsync(
                stream,
                file.FileName,
                file.ContentType,
                techPackId,
                version,
                string.IsNullOrWhiteSpace(brand) ? "Unknown" : brand,
                string.IsNullOrWhiteSpace(styleCode) ? "UNKNOWN" : styleCode,
                string.IsNullOrWhiteSpace(category) ? "t_shirt" : category,
                cancellationToken);
        }
        catch (HttpRequestException exception)
        {
            return Results.Problem(
                title: "Tech-pack import failed",
                detail: exception.Message,
                statusCode: exception.StatusCode is null ? 503 : (int)exception.StatusCode);
        }

        var now = DateTimeOffset.UtcNow;
        var draft = new TechPackImportDraft
        {
            Id = Guid.NewGuid(),
            TenantId = tenantScope.TenantId ?? throw new InvalidOperationException("Tenant context is required"),
            TechPackId = techPackId,
            OriginalFileName = file.FileName,
            ContentType = file.ContentType,
            DraftJson = imported.GetRawText(),
            Status = GetBoolean(imported, "approved") ? "READY" : "MAPPING_REQUIRED",
            SourceHashSha256 = GetString(imported, "versionHashSha256", "version_hash_sha256") ?? string.Empty,
            CreatedAtUtc = now,
            UpdatedAtUtc = now,
        };
        database.TechPackImportDrafts.Add(draft);
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/web/tech-packs/imports/{draft.Id}", new { draft.Id, TechPack = imported });
    }

    private static async Task<IResult> ApproveTechPackImportAsync(
        Guid draftId,
        ApproveTechPackImportRequest request,
        ITechPackImportGateway gateway,
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var draft = await database.TechPackImportDrafts.SingleOrDefaultAsync(
            candidate => candidate.Id == draftId,
            cancellationToken);
        if (draft is null)
        {
            return Results.NotFound();
        }
        if (draft.ApprovedAtUtc is not null)
        {
            return Results.Conflict(new { detail = "This tech-pack import is already approved." });
        }

        using var document = JsonDocument.Parse(draft.DraftJson);
        try
        {
            await gateway.ValidateAsync(document.RootElement, request.SizeCode, cancellationToken);
        }
        catch (HttpRequestException exception)
        {
            return Results.Problem(
                title: "Tech-pack validation failed",
                detail: exception.Message,
                statusCode: StatusCodes.Status422UnprocessableEntity);
        }

        var root = document.RootElement;
        var now = DateTimeOffset.UtcNow;
        var version = new TechPackVersion
        {
            Id = Guid.NewGuid(),
            TenantId = draft.TenantId,
            TechPackId = draft.TechPackId,
            Version = request.Version,
            Brand = GetString(root, "brand", "brand") ?? "Unknown",
            StyleCode = GetString(root, "styleCode", "style_code") ?? "UNKNOWN",
            GarmentCategory = GetString(root, "garmentCategory", "garment_category") ?? "t_shirt",
            DataJson = draft.DraftJson,
            VersionHashSha256 = GetString(root, "versionHashSha256", "version_hash_sha256") ?? draft.SourceHashSha256,
            Approved = true,
            CreatedAtUtc = now,
            UpdatedAtUtc = now,
        };
        draft.Status = "APPROVED";
        draft.ApprovedAtUtc = now;
        draft.UpdatedAtUtc = now;
        database.TechPackVersions.Add(version);
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created(
            $"/api/v1/web/tech-packs/{version.TechPackId}/versions/{version.Version}",
            MapTechPack(version));
    }

    private static async Task<IResult> GetDashboardAsync(
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var inspectionRecords = await database.InspectionRecords
            .Where(record => record.DeletedAtUtc == null)
            .OrderByDescending(record => record.CapturedAtUtc)
            .Take(100)
            .ToArrayAsync(cancellationToken);
        var stations = await MapStationsAsync(database, cancellationToken);
        var techPackRecords = await database.TechPackVersions
            .OrderByDescending(version => version.CreatedAtUtc)
            .Take(100)
            .ToArrayAsync(cancellationToken);
        var users = await MapUsersAsync(database, cancellationToken);
        var evidenceRecords = await database.EvidenceRecords
            .OrderByDescending(record => record.CreatedAtUtc)
            .Take(100)
            .ToArrayAsync(cancellationToken);

        return Results.Ok(
            new WebDashboardDto(
                inspectionRecords.Select(MapInspection).ToArray(),
                stations,
                techPackRecords.Select(MapTechPack).ToArray(),
                users,
                evidenceRecords.Select(MapEvidence).ToArray()));
    }

    private static async Task<IResult> GetInspectionsAsync(
        int page,
        int pageSize,
        string? search,
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var boundedPage = Math.Max(page, 1);
        var boundedPageSize = Math.Clamp(pageSize, 1, 100);
        var query = database.InspectionRecords.Where(record => record.DeletedAtUtc == null);
        if (!string.IsNullOrWhiteSpace(search))
        {
            query = query.Where(
                record =>
                    record.OrderCode.Contains(search)
                    || record.StyleCode.Contains(search)
                    || record.StationCode.Contains(search));
        }

        var total = await query.CountAsync(cancellationToken);
        var records = await query
            .OrderByDescending(record => record.CapturedAtUtc)
            .Skip((boundedPage - 1) * boundedPageSize)
            .Take(boundedPageSize)
            .ToArrayAsync(cancellationToken);
        return Results.Ok(
            new PagedResultDto<InspectionDetailDto>(
                records.Select(MapInspection).ToArray(),
                boundedPage,
                boundedPageSize,
                total));
    }

    private static async Task<IResult> GetInspectionAsync(
        Guid id,
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var record = await database.InspectionRecords.SingleOrDefaultAsync(
            candidate => candidate.Id == id && candidate.DeletedAtUtc == null,
            cancellationToken);
        return record is null ? Results.NotFound() : Results.Ok(MapInspection(record));
    }

    private static async Task<IResult> ReviewInspectionAsync(
        Guid id,
        ReviewInspectionRequest request,
        ClaimsPrincipal principal,
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var inspection = await database.InspectionRecords.SingleOrDefaultAsync(
            candidate => candidate.Id == id && candidate.DeletedAtUtc == null,
            cancellationToken);
        if (inspection is null)
        {
            return Results.NotFound();
        }

        Guid? actorId = Guid.TryParse(
            principal.FindFirstValue(ClaimTypes.NameIdentifier),
            out var parsedActorId)
            ? parsedActorId
            : null;
        var now = DateTimeOffset.UtcNow;
        var review = new ReviewAction
        {
            Id = Guid.NewGuid(),
            TenantId = inspection.TenantId,
            InspectionId = inspection.Id,
            ActorId = actorId,
            Outcome = request.Outcome.ToUpperInvariant(),
            Note = request.Note.Trim(),
            CreatedAtUtc = now,
            UpdatedAtUtc = now,
        };
        database.ReviewActions.Add(review);
        database.AuditEvents.Add(
            new AuditEvent
            {
                Id = Guid.NewGuid(),
                TenantId = inspection.TenantId,
                EventType = "inspection.reviewed",
                EntityType = "inspection",
                EntityId = inspection.Id,
                ActorId = actorId,
                PayloadJson = JsonSerializer.Serialize(
                    new { review.Id, review.Outcome, review.Note },
                    SpecProofJsonOptions.Canonical),
                OccurredAtUtc = now,
            });
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> GetEvidenceAsync(
        Guid id,
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var record = await database.EvidenceRecords.SingleOrDefaultAsync(
            candidate => candidate.Id == id,
            cancellationToken);
        return record is null ? Results.NotFound() : Results.Ok(MapEvidence(record));
    }

    private static async Task<IResult> GetEvidenceAssetAsync(
        Guid id,
        string objectKey,
        SpecProofDbContext database,
        TenantScopeAccessor tenantScope,
        IEvidenceAssetReader assetReader,
        CancellationToken cancellationToken)
    {
        var evidence = await database.EvidenceRecords.SingleOrDefaultAsync(
            candidate => candidate.Id == id,
            cancellationToken);
        if (evidence is null || tenantScope.TenantId is not Guid tenantId)
        {
            return Results.NotFound();
        }

        var configuration = await database.TenantConfigurations.SingleOrDefaultAsync(cancellationToken);
        var bucket = configuration?.ObjectStorageBucket
            ?? TenantObjectStorageNamespace.BuildBucketName(tenantId);
        var asset = await assetReader.ReadAsync(
            tenantId,
            bucket,
            objectKey,
            cancellationToken);
        return asset is null
            ? Results.NotFound()
            : Results.File(asset.Content, asset.ContentType, asset.FileName, enableRangeProcessing: true);
    }

    public static InspectionDetailDto MapInspection(InspectionRecord record)
    {
        var result = JsonSerializer.Deserialize(
            record.InspectionResultJson,
            SpecProofJsonContext.Default.InspectionResultDto);
        var measurements = result?.Measurements.Select(
            measurement => new WebMeasurementDto(
                measurement.PomId,
                measurement.CanonicalName,
                measurement.MeasuredValueMm,
                measurement.TargetValueMm,
                measurement.LowerToleranceMm,
                measurement.UpperToleranceMm,
                measurement.DeviationMm,
                measurement.Confidence,
                measurement.Status.ToString().ToUpperInvariant(),
                measurement.Overlay ?? []))
            .ToArray() ?? [];
        return new InspectionDetailDto(
            record.Id,
            record.CaptureId,
            record.OrderCode,
            record.StyleCode,
            record.SizeCode,
            record.StationCode,
            record.CapturedAtUtc,
            record.Status.ToUpperInvariant(),
            record.EvidenceRecordHash,
            measurements);
    }

    public static TechPackDetailDto MapTechPack(TechPackVersion version)
    {
        var mappings = new List<TechPackMappingDto>();
        using var document = JsonDocument.Parse(version.DataJson);
        if (TryGetProperty(document.RootElement, "importedPoms", "imported_poms", out var imported)
            && imported.ValueKind == JsonValueKind.Array)
        {
            foreach (var pom in imported.EnumerateArray())
            {
                mappings.Add(
                    new TechPackMappingDto(
                        GetString(pom, "originalTerm", "original_term") ?? string.Empty,
                        GetString(pom, "canonicalPomId", "canonical_pom_id"),
                        (GetString(pom, "mappingStatus", "mapping_status") ?? "unknown").ToUpperInvariant()));
            }
        }

        return new TechPackDetailDto(
            version.TechPackId,
            version.Brand,
            version.StyleCode,
            version.GarmentCategory,
            version.Version,
            version.Approved ? "APPROVED" : "MAPPING_REQUIRED",
            version.VersionHashSha256,
            mappings);
    }

    public static EvidenceDetailDto MapEvidence(EvidenceRecord record)
    {
        using var document = JsonDocument.Parse(record.EvidenceJson);
        var root = document.RootElement;
        var versions = TryGetProperty(root, "versions", "versions", out var versionElement)
            ? versionElement
            : default;
        return new EvidenceDetailDto(
            record.Id,
            record.InspectionId,
            record.RecordHashSha256,
            record.PreviousHashSha256,
            record.SignatureAlgorithm ?? "UNSIGNED",
            !string.IsNullOrWhiteSpace(record.SignatureValueBase64),
            GetString(versions, "modelVersion", "model_version") ?? "unknown",
            GetString(versions, "ontologyVersion", "ontology_version") ?? "unknown",
            GetString(versions, "compilerVersion", "compiler_version") ?? "unknown",
            record.CreatedAtUtc);
    }

    private static async Task<StationDetailDto[]> MapStationsAsync(
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var stations = await database.Stations.ToArrayAsync(cancellationToken);
        var factories = await database.Factories.ToDictionaryAsync(factory => factory.Id, cancellationToken);
        var result = new List<StationDetailDto>(stations.Length);
        foreach (var station in stations)
        {
            var health = await database.StationHealthReports
                .Where(report => report.StationId == station.Id)
                .OrderByDescending(report => report.CheckedAtUtc)
                .FirstOrDefaultAsync(cancellationToken);
            var calibrationExpiry = await database.CalibrationRecords
                .Where(calibration => database.Cameras
                    .Where(camera => camera.StationId == station.Id)
                    .Select(camera => camera.Id)
                    .Contains(calibration.CameraId))
                .OrderByDescending(calibration => calibration.CalibratedAtUtc)
                .Select(calibration => (DateTimeOffset?)calibration.ExpiresAtUtc)
                .FirstOrDefaultAsync(cancellationToken);
            var software = await database.StationSoftwareVersions
                .Where(version => version.StationId == station.Id)
                .OrderByDescending(version => version.ReportedAtUtc)
                .Select(version => version.Version)
                .FirstOrDefaultAsync(cancellationToken);
            var status = health?.Status ?? "offline";
            result.Add(
                new StationDetailDto(
                    station.Id,
                    station.StationCode,
                    factories.GetValueOrDefault(station.FactoryId)?.Name ?? "Unknown",
                    status.ToUpperInvariant(),
                    health?.CameraStatus ?? "Unknown",
                    health?.StorageStatus ?? "Unknown",
                    health?.ClockStatus ?? "Unknown",
                    health?.OfflineQueueDepth ?? 0,
                    calibrationExpiry ?? DateTimeOffset.UnixEpoch,
                    software ?? "unknown"));
        }

        return result.ToArray();
    }

    private static async Task<UserAccountDto[]> MapUsersAsync(
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        var users = await database.Users.ToArrayAsync(cancellationToken);
        var roles = await database.Roles.ToDictionaryAsync(role => role.Id, cancellationToken);
        var assignments = await database.UserRoles.ToArrayAsync(cancellationToken);
        return users.Select(
            user =>
            {
                var roleId = assignments.FirstOrDefault(assignment => assignment.UserId == user.Id)?.RoleId;
                return new UserAccountDto(
                    user.Id,
                    user.DisplayName,
                    user.Email,
                    roleId is not null && roles.TryGetValue(roleId.Value, out var role)
                        ? role.Name
                        : "Unassigned",
                    user.IsActive);
            })
            .ToArray();
    }

    private static string? GetString(JsonElement element, string camelName, string snakeName) =>
        TryGetProperty(element, camelName, snakeName, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private static bool GetBoolean(JsonElement element, string propertyName) =>
        element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(propertyName, out var value)
        && value.ValueKind == JsonValueKind.True;

    private static bool TryGetProperty(
        JsonElement element,
        string camelName,
        string snakeName,
        out JsonElement value)
    {
        if (element.ValueKind == JsonValueKind.Object
            && (element.TryGetProperty(camelName, out value)
                || element.TryGetProperty(snakeName, out value)))
        {
            return true;
        }

        value = default;
        return false;
    }
}
