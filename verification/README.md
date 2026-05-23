# Verification

This directory contains a focused transistor-level storage check for the
GF180MCU 3.3V 12T 2R2W bitcell topology used by the published macro abstracts.

It verifies the leaf behavior that should be true before spending more effort
on full macro signoff:

- write 1 and write 0;
- retention after write;
- both independent read ports;
- read disturb resistance;
- disabled-write disturb resistance;
- simultaneous same-data writes;
- opposite same-cell dual-write as an illegal conflict observation.

It does not replace full macro LVS/PEX, sense-amplifier/write-driver
characterization, Liberty generation, EM/IR, density, antenna, or foundry
signoff.

## Run

Install `ngspice` and point the runner at a GF180MCU PDK. The script accepts
`--gf180-pdk`, or uses `GF180_PDK_ROOT`, or derives the path from `PDK_ROOT` and
`PDK_VERSION`.

```bash
python3 verification/run_leaf_storage_checks.py
```

The generated report is written to `verification/results/README.md`. Raw
generated decks and ngspice logs are written under `verification/results/spice/`
and are intentionally git-ignored.
