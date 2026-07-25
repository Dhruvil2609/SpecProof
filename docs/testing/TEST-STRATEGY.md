# SpecProof — Test Strategy

**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Timezone:** UTC  
**Language:** en  

---

## 1. Testing Philosophy

Every feature developed by AI Codex **must** ship with automated tests. There are no exceptions. Tests are the primary quality gate in an AI-driven development workflow.

---

## 2. Test Pyramid

```text
         ╱  E2E / Acceptance  ╲     ← Few, high-value scenarios
        ╱  Integration Tests   ╲    ← API, DB, cross-service
       ╱    Contract Tests      ╲   ← API schema compliance
      ╱      Unit Tests          ╲  ← Majority — fast, isolated
     ╱__________________________ ╲
```

### Distribution Targets

| Layer | Percentage | Speed | Scope |
|-------|-----------|-------|-------|
| Unit | 60–70% | <100ms each | Single function/class |
| Contract | 5–10% | <500ms each | API schema validation |
| Integration | 15–25% | <5s each | Database, service boundaries |
| E2E | 5–10% | <30s each | Full workflow |

---

## 3. Test Types

### 3.1 Unit Tests
- **Python:** pytest with fixtures
- **.NET:** xUnit with NSubstitute for mocking
- **TypeScript:** Vitest or Jest
- **Coverage target:** ≥80% line coverage for domain logic
- **Naming:** `test_{feature}_{scenario}_{expected_result}`

### 3.2 Integration Tests
- Database tests use Docker-based PostgreSQL
- API tests use `WebApplicationFactory` (.NET) or `httpx` (Python)
- Object storage tests use MinIO in Docker
- Must be idempotent and parallelisable

### 3.3 Contract Tests
- Verify OpenAPI spec compliance
- Verify gRPC proto compliance
- Verify capture package format
- Verify evidence record schema

### 3.4 Regression Tests
- Capture-replay corpus with known outputs
- Model output regression (golden results)
- Measurement regression on known geometry
- Cross-platform replay comparison

### 3.5 Cross-Platform Tests
- Same test inputs on Windows and Linux runners
- Measurement results must match within defined tolerance
- Capture packages must load on both platforms
- No platform-specific failures

### 3.6 Hardware-in-Loop Tests
- Camera capture stability (30-minute run)
- USB disconnect/reconnect recovery
- Calibration accuracy verification
- Run on qualified Windows and Linux agents

### 3.7 Performance Tests
- Pipeline latency benchmarks
- Database query benchmarks
- API response time benchmarks
- Memory usage under load

### 3.8 Security Tests
- Tenant isolation verification
- Authentication/authorisation boundary tests
- Secret leak detection
- SBOM vulnerability scanning

---

## 4. Test Automation Rules

1. **Every PR must include tests** — no feature code merges without tests
2. **Tests run in CI** — Windows + Linux runners for every PR
3. **Failing tests block merge** — no exceptions
4. **Test names describe behaviour** — not implementation
5. **No flaky tests** — flaky tests must be fixed or quarantined immediately
6. **Tests must be fast** — unit tests <100ms, integration <5s
7. **Tests must be independent** — no test depends on another test's state
8. **Use factories/fixtures** — not inline test data
9. **UTC timestamps in test data** — match production behaviour
10. **i18n test data** — verify with English locale; framework tests verify locale switching

---

## 5. CI Test Matrix

| Test Suite | Windows Runner | Linux Runner | Trigger |
|-----------|:-:|:-:|---------|
| .NET unit tests | ✅ | ✅ | Every PR |
| .NET integration tests | ✅ | ✅ | Every PR |
| Python lint (Ruff) | ✅ | ✅ | Every PR |
| Python type check (Pyright) | ✅ | ✅ | Every PR |
| Python unit tests | ✅ | ✅ | Every PR |
| Frontend lint + test | ✅ | ✅ | Every PR |
| Frontend build | ✅ | ✅ | Every PR |
| Contract tests | ✅ | ✅ | Every PR |
| Database migration tests | ✅ | ✅ | Every PR |
| Capture-replay regression | ✅ | ✅ | Every PR |
| ONNX inference smoke | ✅ | ✅ | Every PR |
| Cross-platform replay | ✅ | ✅ | Nightly |
| Performance benchmarks | ✅ | — | Nightly |
| Security scan | ✅ | ✅ | Weekly |
| Hardware-in-loop | Qualified agent | Qualified agent | Release branch |
| Installer tests | ✅ | ✅ | Release branch |

---

## 6. Coverage Targets

| Component | Minimum Line Coverage |
|-----------|----------------------|
| Domain logic (POM, measurement, decision) | 90% |
| API endpoints | 85% |
| Geometry utilities | 85% |
| Database repositories | 80% |
| Frontend components | 75% |
| Infrastructure/config | 60% |

---

## 7. Test Data Management

- Synthetic test data for unit tests (known shapes, known measurements)
- Capture-replay corpus for regression (versioned, Git LFS)
- Database seed scripts for integration tests
- All test timestamps in UTC
- No production data in test fixtures
