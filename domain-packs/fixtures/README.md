# M4 signed Domain Pack fixtures

These JSON-only fixtures prove deterministic composition without adding domain concepts to platform
code. Each namespace uses a separate Ed25519 **test-only** publisher key. Never trust these keys
outside automated tests or local demonstrations. Their deterministic seeds are confined to the M4
verification script so signatures and tamper tests can be reproduced.

- `core-pack` owns the reusable `nexweave.io/equipment` concept.
- `equipment-rca-pack` depends on core and declares terminology and an evidence-aware relation; it
  does not implement diagnosis.
- `maintenance-pack` independently depends on core and reuses the same Equipment stable key.

All manifests use the frozen `RFC8785-JCS/1` integer-only subset and prohibit executable content.
