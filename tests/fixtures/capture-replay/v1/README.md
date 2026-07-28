# Capture Replay Corpus v1

This directory defines the versioned replay scenarios used by Phase 2 tests.

Synthetic packages are generated during tests to keep the repository small and deterministic.
Qualified RealSense `.bag` and `.spcapture` files belong in the matching scenario directory and
are stored through Git LFS.

Required hardware corpus scenarios:

- `valid`
- `low-light`
- `reflective-fabric`
- `black-fabric`
- `missing-depth`
- `calibration-expired`
- `corrupted`
- `interrupted`
