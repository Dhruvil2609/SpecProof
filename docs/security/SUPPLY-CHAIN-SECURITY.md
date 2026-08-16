# Supply-Chain Security

## Scope

Every release records locked Python, NuGet, npm, and OCI base-image components in CycloneDX
format. Built application images receive separate image SBOMs because only an image scan can
observe operating-system packages and files added during build.

## Local Generation

Restore .NET assets before generating the workspace SBOM:

```powershell
dotnet restore SpecProof.slnx
.venv\Scripts\python.exe tools/security/generate_sbom.py
```

The command writes `artifacts/sbom/specproof.cdx.json` and fails when a project lacks restored
NuGet assets or a container base image is not version-pinned. The generated document includes
the manifest or project source for each normalized component and package hashes when the lock
format supplies them.

## CI Gates

`.github/workflows/security.yml` runs on pull requests, `main`, and a weekly schedule. It:

1. scans tracked source for credentials;
2. creates and uploads the workspace CycloneDX SBOM;
3. audits Python, NuGet, and npm dependencies;
4. runs Trivy source, secret, and configuration scans;
5. builds every application/infrastructure image;
6. rejects fixed high or critical image vulnerabilities; and
7. uploads a CycloneDX SBOM for every built image.

The Trivy action is pinned to the immutable commit for its signed `v0.36.0` release. The
Python audit runs against a frozen all-groups export rather than the audit tool's temporary
environment.

Security scan and SBOM quality gates close only after the remote workflow completes and the
security owner reviews all reports. Findings are remediated, risk-accepted with expiry and
owner, or block release; they are never hidden by an undocumented ignore rule.
