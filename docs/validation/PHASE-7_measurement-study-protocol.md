# Phase 7 Measurement Validation Study Protocol

**Schema:** `study-observation-v1`
**Hardware gate:** Deferred until qualified cameras, fixtures, garments, and operators are available.

## Study Design

- Select at least 30 garments spanning approved styles, sizes, colours, and expected tolerance positions.
- Use at least 3 trained operators who do not see automated results during manual measurement.
- Re-place every garment at least 3 times per operator; collect at least 2 automated repeats without moving the garment.
- Randomize garment, operator, and placement order. Record anonymized operator IDs and stable garment IDs.
- Use the approved tech-pack version and calibrated manual instrument for every reference reading.
- Record manual and automated readings in millimetres using `study-observation-v1`.

## Collection Procedure

1. Verify station health, camera identity, calibration validity, clock synchronization, and approved tech-pack binding.
2. Record one independent manual reference per garment/POM before revealing automated measurements.
3. For each randomized operator and placement, remove and replace the garment, then run the required repeats.
4. Do not delete rejected or invalid runs; record and classify them through the normal review workflow.
5. Export the controlled CSV, retain the signed inspection evidence, and calculate its SHA-256 manifest.
6. Run `specproof-validation-study analyse --input observations.csv --output-directory report`.

## Per-POM Acceptance

- Same-placement repeatability: 95th-percentile standard deviation ≤2 mm.
- Operator reproducibility: 95th-percentile operator range ≤4 mm.
- Manual agreement: mean absolute error ≤5 mm; report bias and Bland–Altman limits.
- False-pass rate ≤2%; false-fail rate ≤5%.
- Crossed Gauge R&R standard deviation ≤4 mm.
- Every POM must pass independently; aggregate averages cannot hide a weak POM.

## Required Evidence

- Controlled input CSV and normalized Parquet observations.
- JSON and HTML per-POM reports.
- Garment/operator randomization sheet and instrument calibration record.
- Signed inspection evidence and hashes for all automated readings.
- Deviations, exclusions, and review decisions with accountable approval.
