FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet restore apps/platform-api/SpecProof.Platform.Api.csproj
RUN dotnet publish apps/platform-api/SpecProof.Platform.Api.csproj \
    --configuration Release \
    --no-restore \
    --output /app/publish \
    /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
LABEL org.opencontainers.image.title="SpecProof Platform API" \
      org.opencontainers.image.vendor="SpecProof" \
      org.opencontainers.image.source="https://github.com/Dhruvil2609/SpecProof"
RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/publish .
EXPOSE 8080
USER $APP_UID
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8080/healthz || exit 1
ENTRYPOINT ["dotnet", "SpecProof.Platform.Api.dll"]
