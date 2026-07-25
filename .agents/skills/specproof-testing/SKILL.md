---
name: specproof-testing
description: Testing skill for SpecProof. ALWAYS ACTIVE — every SpecProof task requires automated tests. Covers unit, integration, E2E, regression, cross-platform, performance, and security tests for Python, .NET, TypeScript, database, camera, measurement, perception, and all other code.
---

# SpecProof Testing Skill

## When to Use
Activate this skill whenever you write, modify, or review test code for any SpecProof component.

## Test Writing Rules

### 1. Test File Naming
- Python: `test_{module_name}.py` in `tests/` parallel structure
- .NET: `{ClassName}Tests.cs` in `*.Tests` projects
- TypeScript: `{component}.test.tsx` or `{module}.test.ts` co-located

### 2. Test Function Naming
```
Python:   test_{feature}_{scenario}_{expected_result}
.NET:     {Method}_{Scenario}_{ExpectedResult}
TS:       describe('{Feature}') → it('should {expected behaviour}')
```

### 3. Test Structure (AAA Pattern)
```
Arrange → set up test data and dependencies
Act     → call the function/method under test
Assert  → verify the expected outcome
```

### 4. Test Data
- Use factories/fixtures, not inline construction
- All timestamps in UTC
- Use known geometry for measurement tests (rectangles, circles with known dimensions)
- Use synthetic captures for perception tests
- Never use production data

### 5. Assertions
- One logical assertion per test (multiple asserts for one concept is OK)
- Use descriptive assertion messages
- For floating point: use tolerance-based comparisons
  - Python: `pytest.approx(expected, abs=tolerance)`
  - .NET: `Assert.InRange(actual, low, high)`
  - TS: `expect(actual).toBeCloseTo(expected, decimals)`

### 6. Coverage Requirements
| Component | Minimum |
|-----------|---------|
| Domain logic (POM, measurement, decision) | 90% |
| API endpoints | 85% |
| Geometry utilities | 85% |
| Database repositories | 80% |
| Frontend components | 75% |
| Infrastructure/config | 60% |

### 7. Test Categories (Python markers / xUnit traits)
```
@pytest.mark.unit          / [Trait("Category", "Unit")]
@pytest.mark.integration   / [Trait("Category", "Integration")]
@pytest.mark.e2e           / [Trait("Category", "E2E")]
@pytest.mark.regression    / [Trait("Category", "Regression")]
@pytest.mark.cross_platform / [Trait("Category", "CrossPlatform")]
@pytest.mark.performance   / [Trait("Category", "Performance")]
@pytest.mark.security      / [Trait("Category", "Security")]
```

### 8. Mock Rules
- Mock external dependencies (camera, network, filesystem)
- Do NOT mock the unit under test
- Use real database for integration tests (Docker PostgreSQL)
- Use real object storage for integration tests (Docker MinIO)

### 9. Test Execution
```powershell
# Python
pytest tests/ -v --cov=src --cov-report=html

# .NET
dotnet test --verbosity normal --collect:"XPlat Code Coverage"

# TypeScript
pnpm test -- --coverage
```

## After Writing Tests
1. Run all tests and verify they pass
2. Check coverage meets minimums
3. Update the test count in `docs/tracking/PROGRESS.md`
4. Add test IDs to the phase document test case table if applicable
