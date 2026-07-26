# SpecProof User Manual

**Audience:** Factory QC operators and reviewers  
**Status:** Living draft  
**Last Updated:** 2026-07-26T13:20:00Z

## 1. What SpecProof Does

SpecProof helps inspect finished garments by capturing RGB-D data, measuring approved points of measure, comparing results with the correct tech-pack tolerances, and producing a traceable pass/fail/review record.

The MVP workflow is flat or relaxed garment metrology on a defined capture surface. Mannequin, turntable, virtual try-on, and catalogue-scanning workflows are not part of the MVP unless later approved.

## 2. Operator Responsibilities

- Use only approved capture stations.
- Confirm the correct order, style, colour, and size before capture.
- Place one garment inside the indicated capture zone.
- Keep the capture surface clean and unobstructed.
- Follow recapture instructions when SpecProof reports framing, orientation, calibration, or confidence issues.
- Escalate failed or review results according to factory quality procedures.

## 3. Inspection Workflow

### Step 1 - Prepare Station

1. Confirm the station is powered on.
2. Confirm the camera, lighting, network, and local services are healthy.
3. Confirm calibration is current.
4. Clean the capture surface if needed.

### Step 2 - Select Garment Context

1. Select or scan the order.
2. Select the style/SKU.
3. Select colour and nominal size.
4. Confirm the approved spec version is loaded.

### Step 3 - Place Garment

1. Place a single finished garment on the capture surface.
2. Align it according to the on-screen guide.
3. Smooth only according to the approved measurement protocol.
4. Remove hands, tools, packaging, and other garments from the capture zone.

### Step 4 - Capture

1. Review live RGB/depth indicators.
2. Wait for the station to confirm framing and lighting.
3. Start capture.
4. Do not move the garment until capture finishes.

### Step 5 - Review Result

SpecProof returns one of four decision states:

| Status | Meaning | Operator Action |
|--------|---------|-----------------|
| `PASS` | Required measurements are within tolerance and confidence thresholds. | Continue workflow or release item according to factory SOP. |
| `FAIL` | One or more measurements are out of tolerance with sufficient confidence. | Review failed POMs and follow rework/reject SOP. |
| `REVIEW` | Confidence, calibration, capture quality, or rule execution cannot support an automated decision. | Recapture if instructed or send to manual review. |
| `INVALID` | Wrong item, wrong size, overlap, station failure, or missing required data. | Correct the issue and repeat capture. |

## 4. Evidence Shown to Operators

Each result should show:

- Measured value.
- Target value.
- Lower and upper tolerance.
- Deviation.
- Confidence.
- Status per point of measure.
- Visual overlay showing the measured path or anchors.
- Recapture or review guidance when needed.

## 5. Common Recapture Reasons

- Garment outside the capture zone.
- Multiple garments or overlapping fabric.
- Severe wrinkles beyond approved protocol.
- Wrong orientation.
- Missing or occluded landmarks.
- Depth clipping or poor lighting.
- Expired calibration.
- Camera or station health check failure.

## 6. Manual Review

Use manual review when SpecProof returns `REVIEW`, when a failure appears caused by placement, or when factory SOP requires human confirmation.

Reviewers should record:

- Reason for review.
- Manual decision.
- Any manual measurement value.
- Whether the item was recaptured, reworked, accepted, or rejected.

## 7. Do Not Do

- Do not inspect more than one garment at once.
- Do not use unapproved smoothing or stretching.
- Do not bypass calibration warnings.
- Do not alter raw capture files.
- Do not reuse a result for a different garment, size, colour, or style.

## 8. Support Escalation

Escalate to a supervisor or administrator when:

- The station repeatedly reports camera, lighting, or calibration failure.
- The same garment type repeatedly enters `REVIEW`.
- A tech-pack mapping appears incorrect.
- The expected order/style/size is missing.
- The station cannot sync inspection records.
