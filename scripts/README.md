# Generator Scripts

This directory is a release-facing snapshot of the macro generator entrypoints used by the package build.
It is included for review and reproducibility; the full Detronyx workspace is still required for local regeneration.

Primary source-workspace targets:

```bash
make build-gf180mcu-3v3-12t-2r2w-sram-array-macros
make build-gf180mcu-3v3-12t-2r2w-sram-periphery-leaves
make build-gf180mcu-3v3-12t-2r2w-sram-final-physical
make package-gf180mcu-3v3-12t-2r2w-sram-macro
```

Release script names in this package:

- `build_gf180mcu_3v3_12t_2r2w_sram_periphery_slice.py`
- `build_gf180mcu_3v3_12t_2r2w_sram_periphery_leaves.py`
