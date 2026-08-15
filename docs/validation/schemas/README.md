# Validation Study Schemas

Generate the authoritative versioned JSON Schema with:

```powershell
specproof-validation-study schema --output docs/validation/schemas/study-observation-v1.schema.json
```

The normalized CSV and Parquet datasets use the same `StudyObservation` v1 fields. Entity
identifiers cover garments, POMs, operators, placements, and repeats; each row preserves both
the controlled manual reference and automated reading.
