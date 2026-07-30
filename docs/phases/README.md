# SpecProof Development Phases

**Last Updated:** 2026-07-30T17:19:06Z  
**Language:** en

This folder is the authoritative roadmap for SpecProof development phases.

## Development Track Policy

Hardware is not currently available. Until qualified RGB-D camera hardware, capture
fixtures, calibration artefacts, and controlled test surfaces are available, the
project proceeds on a software-first track:

- Implement all coding modules using mock providers, replay adapters, synthetic
  fixtures, metadata-only fixtures, Docker services, and contract tests.
- Keep RealSense SDK calls isolated behind camera-provider abstractions.
- Write automated tests for domain logic, APIs, storage, queues, contracts, and UI
  workflows without requiring physical hardware.
- Mark hardware execution, physical calibration, camera streaming, disconnect/reconnect,
  stability, pilot, and measurement-validation study gates as deferred hardware
  acceptance items.
- Do not block Phase 3-6 software implementation on missing hardware when equivalent
  mock, replay, synthetic, or service-level tests can be written.
- Do not mark hardware acceptance tasks complete until real hardware evidence exists.

## Phase Completion Model

Each phase can have two independent completion states:

| State | Meaning |
|-------|---------|
| Software complete | Code, contracts, automated tests, docs, and non-hardware integrations pass locally or in CI. |
| Hardware accepted | Physical camera, calibration, accuracy, stability, and pilot gates pass on qualified hardware. |

Phases 2, 7, and 8 contain hardware acceptance gates. Their software work may proceed
and be considered software-complete before hardware is available, but final production
acceptance waits for hardware evidence.

## Phase Order

| Phase | Focus | Hardware Needed for Coding? | Hardware Needed for Final Acceptance? |
|------:|-------|-----------------------------|---------------------------------------|
| 0 | Development environment setup | No | Only for capture workstation acceptance |
| 1 | Project foundation | No | No |
| 2 | Capture station core | No, use mock/replay/synthetic fixtures | Yes |
| 3 | Perception pipeline | No, use synthetic/replay captures | Yes for accuracy calibration evidence |
| 4 | Measurement engine | No, use synthetic geometry and replay packages | Yes for final accuracy validation |
| 5 | Platform and trust layer | No | No |
| 6 | Web application | No, use simulated station/capture APIs | No |
| 7 | Integration and pilot | Partially, software E2E can use simulation | Yes |
| 8 | Production hardening | Partially, packaging/security can proceed | Yes for HIL/stability release gates |

## Required Evidence

Software evidence can include:

- Unit tests.
- Contract tests.
- Integration tests against Docker services.
- Synthetic capture/package fixtures.
- Replay fixtures stored through Git LFS.
- Browser/UI tests against simulated APIs.
- CI logs.

Hardware evidence must include:

- Camera model, serial, firmware, SDK version, USB controller, and cable.
- Calibration artefact identity and measured thresholds.
- Capture package checksums and logs.
- Disconnect/reconnect evidence.
- Stability-run logs and metrics.
- Operator or technician name and UTC timestamp.
