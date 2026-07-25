# SpecProof — Project Documentation

**Created:** 2026-07-25T13:15:00Z  
**Last Updated:** 2026-07-25T13:15:00Z  
**Default Language:** en (English)  
**Timezone:** UTC  

---

## Documentation Structure

```text
docs/
├── README.md                          # This file — documentation index
├── phases/                            # Development phase documents
│   ├── PHASE-0_development-environment-setup.md
│   ├── PHASE-1_project-foundation.md
│   ├── PHASE-2_capture-station-core.md
│   ├── PHASE-3_perception-pipeline.md
│   ├── PHASE-4_measurement-engine.md
│   ├── PHASE-5_platform-and-trust-layer.md
│   ├── PHASE-6_web-application.md
│   ├── PHASE-7_integration-and-pilot.md
│   └── PHASE-8_production-hardening.md
├── tracking/                          # Development progress tracking
│   ├── PROGRESS.md                    # Master progress tracker
│   ├── CHANGELOG.md                   # All changes log
│   └── DECISIONS.md                   # Architecture Decision Records
├── testing/                           # Test strategy and standards
│   └── TEST-STRATEGY.md
├── standards/                         # Coding and quality standards
│   └── CODING-STANDARDS.md
└── i18n/                              # Internationalisation
    └── I18N-STRATEGY.md
```

## Development Principles

1. **All development by AI Codex** — every phase includes agent-executable skill files
2. **Automatic test cases** — every feature ships with unit, integration, and regression tests
3. **Production-grade** — no shortcuts; code must meet production quality gates
4. **UTC timestamps** — all dates and times in UTC for global consistency
5. **Multi-language support** — i18n-ready from day one, English default
6. **Progress tracking** — every task tracked with status and timestamps

## Phase Overview

| Phase | Name | Status | Dependencies |
|-------|------|--------|--------------|
| 0 | Development Environment Setup | `NOT_STARTED` | None |
| 1 | Project Foundation | `NOT_STARTED` | Phase 0 |
| 2 | Capture Station Core | `NOT_STARTED` | Phase 1 |
| 3 | Perception Pipeline | `NOT_STARTED` | Phase 2 |
| 4 | Measurement Engine | `NOT_STARTED` | Phase 3 |
| 5 | Platform & Trust Layer | `NOT_STARTED` | Phase 4 |
| 6 | Web Application | `NOT_STARTED` | Phase 5 |
| 7 | Integration & Pilot | `NOT_STARTED` | Phase 6 |
| 8 | Production Hardening | `NOT_STARTED` | Phase 7 |

## Quick Start

1. Read [Phase 0](phases/PHASE-0_development-environment-setup.md) to set up the development environment
2. Review [Progress Tracker](tracking/PROGRESS.md) for current status
3. Check [Test Strategy](testing/TEST-STRATEGY.md) for testing requirements
4. Reference [Coding Standards](standards/CODING-STANDARDS.md) for quality gates
