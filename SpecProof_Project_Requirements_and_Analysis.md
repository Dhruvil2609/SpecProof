# SpecProof — Project Requirements and Analysis

**Document type:** Product requirements, system analysis, and phased delivery plan  
**Version:** 1.0  
**Date:** 25 July 2026  
**Status:** Draft for technical validation  

---

## 1. Executive Summary

SpecProof is a proposed hardware-plus-software system for automatically measuring finished garments, validating those measurements against a brand's graded technical specification, and producing a signed, tamper-evident result that a brand and factory can both verify.

The intended workflow is:

1. An operator places a finished garment on a defined capture surface.
2. An RGB-D camera captures aligned colour and depth data under controlled illumination.
3. The system reconstructs a metric surface representation of the garment.
4. Garment type, size, construction landmarks, seams, edges, and measurement anchors are identified.
5. Brand-specific points of measure are translated into executable measurement rules.
6. Measurements are normalised to a defined reference configuration and compared with graded tolerances.
7. The system creates an explainable pass/fail result and an auditable measurement record.

The supplied business material positions the product as a low-cost subscription rig for per-unit garment inspection rather than AQL sampling. It proposes three main technical differentiators: drape-compensated measurement, specification-constrained landmark detection, and a point-of-measure compiler with a canonical ontology.

### Critical product decision

The supplied infographic depicts a mannequin and motorised turntable inside a frame, while the formal SpecProof documents describe a garment placed on a capture surface. These are materially different products:

- **Flat/relaxed garment metrology:** Measures finished garments against flat-lay tech-pack protocols.
- **Mannequin/turntable 3D scanning:** Produces a rotating 3D representation for visualisation, cataloguing, or virtual try-on.

The first MVP should implement **flat/relaxed garment metrology**, because it aligns with the stated patent concepts, manual tape-measure protocol, tech-pack validation, and factory QC workflow. Turntable scanning should remain a separate future module unless a validated customer requirement proves otherwise.

---

## 2. Source-Derived Product Definition

The source materials define SpecProof as a calibrated RGB-D capture station with controlled illumination and a defined capture surface, connected to a perception, measurement, validation, and record pipeline.

### Core proposed innovations

1. **Drape-compensated measurement**
   - Develop or flatten the local 3D garment surface with low distortion.
   - Account for fabric slack, tension, and material compliance.
   - Map measurements to a reference configuration matching the manual smoothing protocol.

2. **Specification-constrained construction landmark detection**
   - Use learned landmark proposals.
   - Fit the complete landmark set as a graph.
   - Regularise the graph using geometry implied by the graded specification for the detected size.
   - Recover occluded points, reject outliers, and provide measurement-specific explanations.

3. **Point-of-measure compiler and canonical ontology**
   - Normalise brand-specific measurement terminology.
   - Resolve units, offsets, path types, anchor points, and doubling rules.
   - Compile each definition into an executable measurement program.

4. **Supporting trust layer**
   - Bind each result to calibration state, model/ruleset versions, and a hash of the raw capture.
   - Maintain an append-only, tamper-evident record visible to authorised brand and factory users.

### Business constraints carried into engineering

- Hardware target in the supplied model: approximately **£580 per rig**.
- No upfront hardware charge in the proposed commercial model.
- Subscription tiers in the supplied plan: **£259, £699, and £1,299 per month**.
- First sales target: UK and European nearshore factories and mid-market brands.
- Initial hardware should use standard catalogue parts with at least two suppliers per part.

These are planning assumptions, not validated engineering outcomes. The cost target must be re-baselined after the proof-of-concept bill of materials and calibration hardware are finalised.

---

## 3. Problem Statement

Manual garment measurement has four systemic weaknesses:

- It is slow enough that factories normally inspect only a sample.
- Results vary by operator, placement, smoothing force, interpretation, and fatigue.
- Brand-specific tech packs are inconsistent and not directly machine-executable.
- Brand and factory measurements can disagree without a neutral evidence record.

SpecProof must therefore solve both a **metrology problem** and a **trust/workflow problem**.

A successful system cannot merely estimate garment dimensions from an image. It must establish repeatability, traceability, calibration control, measurement uncertainty, rule-version control, and explainable deviations from a specific graded tech pack.

---

## 4. Goals and Non-Goals

## 4.1 MVP goals

- Capture synchronised RGB and depth data from a controlled station.
- Calibrate the camera to the measurement plane and establish metric scale.
- Identify one initial garment category, recommended: **short-sleeve T-shirt**.
- Support 6–10 agreed points of measure for that category.
- Import a structured tech-pack template in CSV/XLSX/JSON form.
- Segment the garment and identify required edges and landmarks.
- Compute measurements with confidence and uncertainty indicators.
- Compare measurements against size-specific targets and tolerances.
- Produce a pass/fail inspection record with source images, depth data, software versions, calibration ID, and measurement evidence.
- Provide a review screen for low-confidence or failed measurements.
- Demonstrate repeatability across operators and repeated placements.

## 4.2 Pilot goals

- Add 3–5 garment categories.
- Add controlled onboarding of brand-specific point-of-measure definitions.
- Add multi-tenant brand/factory accounts and role-based access.
- Add production-line device management and remote diagnostics.
- Add signed inspection records and immutable audit history.
- Add export/API integration for PLM, ERP, QMS, or warehouse systems.
- Validate throughput and accuracy in a factory-like environment.

## 4.3 Non-goals for MVP

- Full digital twin generation for virtual try-on.
- Photorealistic 360° catalogue asset creation.
- Automatic support for every garment category.
- Fully autonomous handling of folded, heavily occluded, or overlapping garments.
- Unsupervised ingestion of arbitrary PDF tech packs with no human verification.
- Legal-grade non-repudiation without an external security and legal review.
- Claims that measurements match manual protocols until validated by a controlled metrology study.

---

## 5. Stakeholders and Users

| Stakeholder | Primary need |
|---|---|
| Factory QC operator | Fast, simple placement and unambiguous result |
| Factory quality manager | Traceable inspection history, trends, rework decisions |
| Brand technical designer | Measurement evidence tied to the correct tech pack and size |
| Brand quality/compliance team | Cross-factory consistency and supplier performance analytics |
| SpecProof support engineer | Device health, calibration, logs, remote diagnostics |
| System administrator | Tenant, user, permissions, retention, and policy management |
| Data/ML engineer | Curated datasets, annotation, model registry, drift monitoring |
| Auditor or dispute reviewer | Reproducible evidence and clear chain of custody |

---

## 6. Functional Requirements

## 6.1 Station and device control

- Detect connected RGB-D camera and verify serial number.
- Load camera intrinsics, depth scale, and station-specific extrinsics.
- Control or validate lighting state before capture.
- Display live RGB, depth, exposure, clipping, and alignment indicators.
- Prevent capture when calibration is expired or station checks fail.
- Support station health diagnostics: camera, USB bandwidth, storage, temperature, lighting, network, and clock synchronisation.

## 6.2 Calibration

The system shall support:

- Camera intrinsic verification.
- RGB-to-depth alignment verification.
- Camera-to-capture-plane extrinsic calibration.
- Scale verification using a traceable calibration artefact.
- Lens/depth distortion checks.
- Flatness and orientation checks for the capture surface.
- Lighting uniformity verification.
- Calibration version, operator, artefact ID, date, and expiry storage.
- Daily quick check and scheduled full calibration.

A calibration record must be associated with every inspection.

## 6.3 Capture workflow

- Operator selects or scans order, style, colour, and nominal size.
- System retrieves the approved spec version.
- Operator places one garment within an indicated capture zone.
- System checks framing, occlusion, overlap, severe wrinkles, and garment orientation.
- System captures one or more RGB-D frames.
- Raw captures are stored or retained according to tenant policy.
- Operator receives a result or an actionable recapture instruction.

## 6.4 Garment perception

- Background/capture-surface subtraction.
- RGB-depth registration.
- Garment segmentation.
- Garment category and orientation classification.
- Boundary, seam, and construction-feature extraction.
- Landmark proposal generation with confidence scores.
- Graph-based landmark refinement using category geometry and graded-spec constraints.
- Explicit handling of missing/occluded landmarks.

## 6.5 Surface and geometry processing

- Generate an organised point cloud or mesh from aligned RGB-D data.
- Remove invalid depth, flying pixels, and statistical outliers.
- Estimate local normals and surface confidence.
- Detect the support plane and garment-to-plane separation.
- Generate a low-distortion 2D parameterisation where required.
- Preserve the mapping between the developed surface and original 3D coordinates.
- Compute geodesic or projected paths according to each measurement rule.

## 6.6 Measurement engine

Each executable point-of-measure rule should define:

- Measurement ID and canonical name.
- Garment category and applicable size range.
- Start/end anchors.
- Anchor fallback logic.
- Straight, projected, contour, or geodesic path.
- Offset from seam/edge/landmark.
- Whether to double a flat width.
- Unit and rounding rule.
- Reference configuration.
- Tolerance source and tolerance direction.
- Minimum confidence and review policy.

The output shall include measured value, target, lower/upper tolerance, deviation, confidence, uncertainty estimate, pass/fail/review status, and visual evidence overlay.

## 6.7 Tech-pack and ontology management

- Import structured data from CSV/XLSX initially.
- Store original brand terminology without overwriting it.
- Map original terms to canonical point-of-measure definitions.
- Require human approval for new or ambiguous mappings.
- Version specs, sizes, tolerances, grading rules, and mappings.
- Prevent retroactive modification of an inspection's referenced spec.
- Provide a test mode to execute a new compiled rule against historical captures.

## 6.8 Inspection decision engine

Supported statuses:

- **PASS:** Every required measurement is within tolerance and above confidence threshold.
- **FAIL:** At least one required measurement is outside tolerance with sufficient confidence.
- **REVIEW:** Capture quality, confidence, calibration, or rule execution does not support an automated decision.
- **INVALID:** Wrong item, wrong size, overlap, station failure, or missing mandatory data.

A failed result must name the exact point of measure, target, tolerance, actual value, deviation, and evidence location.

## 6.9 Record and audit layer

Each inspection record should include:

- Tenant, factory, station, operator, order, SKU/style, colour, and size.
- Capture timestamp from a synchronised clock.
- Raw/derived capture hashes.
- Camera serial and firmware/SDK version.
- Calibration record ID.
- Model, ontology, compiler, and ruleset versions.
- Tech-pack/spec version.
- Measurement results and confidence/uncertainty.
- Human review actions and reasons.
- Append-only status transitions.
- Digital signature or service signature, subject to security design.

A cryptographic hash makes alteration detectable but does not by itself prove identity, custody, or legal non-repudiation. Key management, signer identity, timestamping, retention, access control, and independent verification must be designed explicitly.

## 6.10 Reporting and integrations

- Inspection result screen with overlays.
- Batch/order summary.
- Defect and out-of-tolerance Pareto analysis.
- Supplier/style/size trend analysis.
- CSV and PDF export.
- REST API and webhook/event output.
- Future PLM connectors for systems such as Browzwear, CLO, or Centric, subject to vendor API availability and commercial agreements.

---

## 7. Non-Functional Requirements

## 7.1 Measurement quality

Initial engineering targets, subject to validation:

| Attribute | Proof-of-concept target | Pilot target |
|---|---:|---:|
| Repeatability, same placement | ≤ 2 mm standard deviation for supported POMs | ≤ 1.5 mm |
| Reproducibility, different operators/placements | ≤ 4 mm 95% range | ≤ 3 mm |
| Agreement with approved manual protocol | Mean absolute error ≤ 5 mm | Category/POM-specific ≤ 3 mm where feasible |
| Automated-decision coverage | ≥ 70% | ≥ 90% for supported categories |
| False-pass rate | Must be measured; prioritise minimisation | Agreed customer threshold per use case |

A single universal accuracy number is misleading. Performance must be reported by garment category, fabric type, point of measure, size, placement condition, and confidence band.

## 7.2 Performance

- Live preview: 15–30 FPS where supported.
- Capture validation: under 2 seconds.
- MVP processing: under 15 seconds per garment on the development workstation.
- Pilot target: under 5 seconds per garment for supported categories.
- UI feedback must remain responsive during processing.

## 7.3 Availability and resilience

- Station must queue inspections during temporary internet loss.
- No inspection may be lost after operator confirmation.
- Local database and object store should use durable writes.
- Synchronisation must be idempotent.
- Device software should recover safely after power loss.

## 7.4 Security

- Tenant isolation and role-based access control.
- TLS for data in transit.
- Encryption for sensitive data at rest.
- Per-device identity and certificate rotation.
- Signed software updates.
- Secrets stored outside source code.
- Immutable or append-only audit stream.
- Security review of cryptographic record design.
- Configurable data retention and deletion policy.

## 7.5 Privacy

The system is intended to capture garments, not people. The station should prevent or warn when faces or people enter the capture area. Factory data, order identifiers, and tech packs may be commercially sensitive and require contractual and technical controls.

## 7.6 Maintainability

- Modular pipeline with stable interfaces.
- Reproducible environments and pinned dependencies.
- Automated unit, integration, hardware-in-loop, and regression tests.
- Model registry and dataset versioning.
- Structured logs, metrics, traces, and remote diagnostics.
- Backward-compatible record reader for historical inspections.

---

## 8. Proposed System Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ Capture Station                                             │
│ RGB-D camera + lighting + calibrated surface + mini PC      │
└───────────────────────┬──────────────────────────────────────┘
                        │
               Station Agent / Device API
                        │
       ┌────────────────┴─────────────────┐
       │                                  │
Capture & Calibration              Local Job Queue
       │                                  │
       └───────────────┬──────────────────┘
                       │
              Perception Pipeline
      segmentation → point cloud → landmarks
                       │
              Surface Normalisation
                       │
             POM Compiler Runtime
                       │
             Measurement & Decision
                       │
      Evidence Package + Signed Audit Record
                       │
          Local Cache / Central Platform
                       │
      Web UI, API, analytics, integrations
```

### Recommended implementation split

- **Station agent:** Python service controlling the camera and capture pipeline.
- **Computer vision/geometry:** Python, PyTorch, OpenCV, Open3D, NumPy/SciPy.
- **Performance-critical geometry:** C++ extension only after profiling proves necessary.
- **Platform API:** Python FastAPI for an all-Python MVP, or .NET for the commercial control plane if the team prefers a strongly typed enterprise backend. Avoid duplicating domain logic across both during MVP.
- **Web application:** React/TypeScript or Angular/TypeScript.
- **Data:** PostgreSQL for structured metadata; S3-compatible object storage for raw and derived captures.
- **Messaging:** Redis Streams, RabbitMQ, or a managed queue for asynchronous processing.
- **Observability:** OpenTelemetry-compatible logs, metrics, and traces.

---

## 9. Data Model — Minimum Entities

- Tenant
- Organisation
- Factory
- Brand
- User
- Role
- Station
- Camera
- CalibrationRecord
- GarmentCategory
- Style/SKU
- Size
- TechPack
- TechPackVersion
- PointOfMeasureDefinition
- CanonicalPOM
- POMMapping
- CompiledMeasurementRule
- ModelVersion
- RulesetVersion
- Inspection
- CaptureAsset
- MeasurementResult
- Decision
- ReviewAction
- AuditEvent
- DeviceHealthEvent

Every mutable business definition must be versioned. Inspection records must point to immutable versions.

---

## 10. Hardware Requirements and Analysis

## 10.1 RGB-D camera

The supplied concept names the Intel RealSense D435. Official specifications list active stereoscopic depth, RGB, up to 1280×720 depth, an operating range of roughly 0.3–3 m, and USB 3.0 Type-C. This is adequate for an initial research rig, but it must be benchmarked on dark, reflective, black, fuzzy, thin, and low-texture fabrics.

RealSense is now operated as a separate company following its 2025 spinout from Intel. Supply continuity, SDK maintenance, replacement camera qualification, and a second-source strategy should therefore be part of the product plan.

**Camera selection criteria:**

- Depth accuracy at the proposed working distance.
- Minimum depth distance.
- Depth noise on black and reflective textiles.
- RGB-depth alignment quality.
- Global versus rolling shutter implications.
- USB stability and cable length.
- SDK support on the target OS.
- Long-term availability and unit cost.

A second camera family, such as an Orbbec stereo/depth device, should be evaluated before design freeze.

## 10.2 Lighting

- High-CRI LED panels with diffusion.
- Stable, flicker-free constant-current drivers.
- Symmetrical placement to reduce specular highlights and cast shadows.
- Fixed exposure and white-balance profiles after calibration.
- Shielding from uncontrolled ambient light.
- Lighting health check using a uniformity target.

## 10.3 Capture surface and frame

- Rigid aluminium extrusion frame.
- Dimensionally stable, matte, non-reflective capture surface.
- High visual/depth contrast against expected garment colours.
- Replaceable or cleanable surface material.
- Fixed camera mount with anti-rotation hardware.
- Calibration-target mounting points.
- Safety covers and cable strain relief.

## 10.4 Compute unit

The infographic suggests an entry-level mini PC. That is reasonable for capture and classical geometry, but model training should occur on a separate GPU workstation or cloud GPU.

**Pilot station target:**

- Modern 6–12 core x86-64 CPU.
- 16 GB RAM minimum; 32 GB preferred.
- 512 GB NVMe minimum.
- USB 3.x controller with verified sustained bandwidth.
- Gigabit Ethernet.
- TPM 2.0 or equivalent secure key storage.
- Optional NVIDIA GPU only if station-side inference requires it.

## 10.5 Optional turntable

Do not include a turntable in the metrology MVP. It introduces pose changes, garment movement, registration error, safety concerns, and a different measurement protocol. Add it only for a separately defined mannequin/catalogue scanning use case.

---

## 11. Machine Learning and Geometry Workstreams

## 11.1 Dataset programme

The project requires a purpose-built dataset containing:

- RGB, depth, camera metadata, and calibration state.
- Garment category, style, size, fabric composition, colour, and construction attributes.
- Multiple placements by multiple operators.
- Manual reference measurements from trained technical designers.
- Landmark and seam annotations.
- Capture-quality labels.
- Difficult cases: black, white, patterned, shiny, sheer, ribbed, thick, folded, and asymmetric garments.

### Ground-truth protocol

- Write a formal manual measurement SOP for every supported POM.
- Train and qualify reference measurers.
- Use repeated independent measurements.
- Record environmental conditions and instruments.
- Assess inter- and intra-rater variation before treating manual readings as truth.
- Maintain measurement instrument calibration records.

## 11.2 Baseline before advanced IP

Build a transparent baseline first:

1. Plane/background subtraction.
2. 2D garment segmentation.
3. Contour and corner heuristics.
4. Depth correction and point-cloud generation.
5. Basic landmark model.
6. Straight/projected measurement rules.
7. Repeatability study.

Then incrementally introduce graph constraints, surface development, fabric compensation, and learned ontology matching. This sequencing makes technical gains measurable and prevents an opaque end-to-end model from hiding failure modes.

## 11.3 Model governance

- Dataset cards and model cards.
- Training code and configuration versioning.
- Fixed validation and challenge sets.
- Per-category/POM metrics.
- Drift detection after deployment.
- Approval workflow before promoting a model.
- Ability to reproduce any historical result with the recorded model and ruleset version.

---

## 12. Validation and Acceptance Strategy

## 12.1 Test levels

- Unit tests for geometry and rule calculations.
- Synthetic tests with known shapes and distances.
- Camera/SDK integration tests.
- Calibration regression tests.
- Golden-capture regression suite.
- Hardware-in-loop tests.
- Repeated placement studies.
- Multi-operator reproducibility studies.
- Environmental tests for lighting, temperature, and vibration.
- Security and audit-chain tests.
- Factory pilot acceptance tests.

## 12.2 Recommended measurement study

For each supported garment category:

- At least 30 distinct garments covering sizes, colours, fabrics, and constructions.
- At least 3 trained manual measurers.
- At least 3 manual repeats per garment/POM.
- At least 3 operators and 3 station placements.
- Compare bias, repeatability, reproducibility, limits of agreement, and false-pass/false-fail rates.
- Report results by POM; do not aggregate away weak measurements.

A Gauge R&R-style study is appropriate, adapted for the manual reference and automated station.

## 12.3 MVP acceptance gates

The MVP may progress to factory pilot only when:

- Calibration remains stable for the defined interval.
- The supported POM list is frozen and documented.
- Accuracy and repeatability targets are met on an unseen challenge set.
- Low-confidence cases are routed to review rather than silently passed.
- Every result can be traced to capture, calibration, spec, model, and ruleset versions.
- Device recovery and offline operation are tested.
- Safety and electrical risks are assessed.

---

## 13. Compliance and Legal Workstreams

The business plan budgets for UKCA/CE, RoHS, WEEE, and insurance, but actual obligations depend on final hardware, power architecture, radio modules, importer/manufacturer role, and market. Obtain specialist conformity advice before production.

Required workstreams may include:

- Electrical and mechanical safety.
- EMC testing.
- UKCA/CE technical file and declaration.
- RoHS and WEEE obligations.
- Product and public liability insurance.
- Cybersecurity and update policy.
- Data-protection review.
- Supplier declarations and component traceability.

### IP caveat

The supplied attorney assessment states that SpecProof appears patent-eligible and new based on information provided, but explicitly states that no separate prior-art search was performed and that patent offices may identify relevant prior art. It recommends seeking patent protection. The presentation separately states that a UK patent application was filed. Before external claims are made, retain formal evidence of the filing number, filing date, applicant/owner, and exact scope, and align all documents to the verified status.

---

## 14. Major Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Depth noise on difficult fabrics | Incorrect geometry and measurements | Camera benchmark, multi-frame fusion, confidence masks, alternative camera |
| Manual reference is inconsistent | Invalid training and acceptance data | Formal SOP, qualified measurers, repeated readings, Gauge R&R |
| Tech packs are ambiguous | Incorrect compiled rules | Human approval, canonical ontology, versioned mapping tests |
| Drape compensation is not sufficiently accurate | Core differentiation fails | Baseline experiments, restricted garment scope, measurable ablation studies |
| False passes | Customer quality and liability exposure | Conservative confidence policy, review state, per-POM thresholds |
| Hardware cost exceeds £580 | Business model pressure | Updated BOM, design-to-cost, supplier qualification, tiered hardware |
| Camera/SDK supply changes | Production interruption | Second-source camera abstraction and qualification |
| Patent claims are overstated | Legal and credibility risk | Use verified filing status and attorney-approved wording |
| Tamper-evident record is treated as legally conclusive | Dispute and security risk | Independent cryptographic/security/legal design review |
| Factory workflow friction | Low adoption | One-action capture, clear recapture guidance, offline operation, operator trials |
| Scope expands into 360° scanning/virtual try-on | Delayed metrology MVP | Separate product requirements and roadmap streams |

---

## 15. Delivery Roadmap

## Phase 0 — Discovery and protocol definition (4–6 weeks)

- Freeze the MVP use case and first garment category.
- Select 6–10 POMs.
- Write manual reference SOP.
- Build camera and fabric test matrix.
- Reconcile flat-lay versus turntable scope.
- Confirm IP filing status and confidentiality controls.
- Produce preliminary compliance classification.

**Exit:** approved product requirements, measurement protocol, risk register, and research rig BOM.

## Phase 1 — Research rig and capture foundation (6–8 weeks)

- Assemble controlled frame, surface, lighting, camera, and workstation.
- Implement station agent, live preview, capture, and calibration.
- Record aligned RGB-D datasets.
- Establish depth-quality benchmarks.

**Exit:** repeatable calibrated captures and documented station setup.

## Phase 2 — Baseline metrology proof of concept (8–12 weeks)

- Segmentation, plane subtraction, point cloud, basic landmarks, and measurement rules.
- Structured tech-pack import.
- Evidence overlays and result UI.
- Initial repeatability and agreement study.

**Exit:** selected T-shirt POMs measured end-to-end with quantified performance.

## Phase 3 — Advanced SpecProof pipeline (12–20 weeks)

- Graph-constrained landmark refinement.
- Surface development/drape compensation experiments.
- Ontology and compiler v1.
- Confidence, uncertainty, and review policies.
- Ablation studies against the baseline.

**Exit:** defensible evidence that each advanced method improves defined metrics.

## Phase 4 — Pilot platform and trust layer (10–14 weeks)

- Multi-tenant platform, users, station management, immutable versioning.
- Audit package, signatures, offline synchronisation, reporting, API.
- Remote diagnostics and update mechanism.
- Security review.

**Exit:** pilot-ready system and operating procedures.

## Phase 5 — Factory pilot (8–12 weeks)

- Limited deployment at one or two partner sites.
- Compare against existing QC workflow.
- Measure throughput, operator intervention, false-pass/fail rates, uptime, and support burden.
- Re-baseline unit economics and production BOM.

**Exit:** go/no-go decision for productisation.

---

## 16. Team Requirements

Minimum core team for the technical programme:

- Product owner with garment-QC domain authority.
- Computer vision/3D geometry lead.
- ML engineer.
- Backend/platform engineer.
- Frontend engineer.
- Embedded/device or systems engineer.
- QA/test automation engineer.
- Technical designer/garment technologist.
- Contract mechanical/electrical/compliance specialists.
- Security/cryptography reviewer for the trust layer.

A two-founder team can deliver discovery and an early proof of concept, but reliable metrology, dataset creation, compliance, and pilot operations require specialist support.

---

## 17. Open Questions

1. Is the inspection protocol flat-lay, lightly smoothed, naturally relaxed, or mannequin-mounted?
2. Which garment category and exact POMs define the MVP?
3. What is the accepted manual reference standard for each POM?
4. What false-pass risk is acceptable to the first pilot customer?
5. Must all raw captures be retained, and for how long?
6. Is processing required fully on-premises, cloud-assisted, or hybrid?
7. Which tech-pack formats are used by the first design partner?
8. Does the brand or factory own the inspection record and raw data?
9. Which party signs the dual-party record and how are keys managed?
10. What is the verified UK patent application status and scope?
11. Which compliance standards apply to the final power supply, enclosure, and connectivity?
12. Can the target £580 BOM support calibration artefacts, industrial cabling, enclosure, manufacturing test, warranty, and field support?

---

## 18. Recommended Immediate Actions

1. Freeze the flat-lay garment measurement MVP and remove the turntable from the first build.
2. Select a T-shirt measurement protocol and create a signed-off POM dictionary.
3. Buy or borrow two candidate RGB-D cameras and run a controlled fabric depth benchmark.
4. Build a rigid research station with measurable lighting and calibration controls.
5. Conduct a manual measurement repeatability study before model training.
6. Create the canonical inspection record schema and versioning model early.
7. Verify patent filing evidence and maintain confidentiality around unfiled implementation details.
8. Treat the £580 hardware cost as a hypothesis until a production-ready BOM is established.

---

## 19. Web Research References

- Intel/RealSense D435 specifications: https://www.intel.com/content/www/us/en/products/sku/128255/intel-realsense-depth-camera-d435/specifications.html
- RealSense SDK (`librealsense`): https://github.com/realsenseai/librealsense
- RealSense SDK release/platform information: https://github.com/realsenseai/librealsense/releases
- RealSense corporate/product site: https://www.realsenseai.com/
- Open3D documentation: https://www.open3d.org/docs/release/
- Open3D RGB-D reconstruction tutorial: https://www.open3d.org/docs/release/tutorial/reconstruction_system/index.html
- Open3D RGB-D point-cloud API: https://www.open3d.org/docs/0.19.0/python_api/open3d.geometry.PointCloud.html
- NVIDIA CUDA installation guide for Linux: https://docs.nvidia.com/cuda/cuda-installation-guide-linux/

---

## 20. Source Materials Used

- *SpecProof — Automated Garment Measurement* presentation.
- *Competitor Analysis*.
- *Business Model*.
- *SpecProof — Founders' Presentation Script*.
- *IP Registrability Assessment*, Potter Clarkson LLP, 30 June 2026.
- User-supplied 3D scanning system infographic.

