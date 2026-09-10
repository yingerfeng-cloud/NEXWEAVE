# Equipment RCA Pack V1.0

`equipment-rca-pack` is the M9 declarative domain package for evidence-backed equipment root-cause knowledge. It extends the public `core-pack` Equipment concept without adding equipment, KKS, failure-mode or RCA branches to platform code.

The package contains:

- `semantic.json`: equipment/component, observation, cause, mechanism, verification, exclusion, action, case and expert-rule types; evidence-required relations; governed identifiers and terminology.
- `authoring.json`: page templates, a constrained assistant prompt, lint rules and safe UI metadata.
- `evaluation.json`: the versioned standard question set covering answerable, unanswerable, conflict, counterfactual, multi-source and insufficient-evidence behavior.
- `manifest.json`: canonical JSON checksums and an Ed25519 signature. The verification-only public key is in `publisher-public-key.json`; the private signing key was not retained in the repository.

This package supports knowledge analysis, not automatic diagnosis. It must never emit an automatic operating instruction, probability of failure or final engineering decision. Formal Claims and causal Relations still require accepted Evidence, valid SourceAnchors, human review and an immutable Release.

The repository does not include authorized real RCA data or expert approval. `examples/synthetic-rca-case.json` is an explicitly synthetic technical fixture and is not pilot evidence.

## Verify

```bash
.venv/bin/python scripts/verify_m9_pack.py
.venv/bin/pytest -q packages/domain/tests/test_m9_equipment_rca_pack.py
```

Installation continues to use the M4 trust-key, Pack registration and reliable installation APIs. Installation creates a DRAFT SchemaVersion; a separate authorized publication step is mandatory.
