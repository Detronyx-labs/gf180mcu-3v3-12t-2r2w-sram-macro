# Verification

This directory contains release-facing verification scripts for the published
GF180MCU 3.3V 12T 2R2W SRAM extracted-SPICE reports, plus the local 12T leaf
storage checks used before macro-level LVS/PEX work.

- `gf180mcu_3v3_12t_2r2w_sram_lvs_gate.py` runs the full release LVS gate:
  extracted 4x4 tile device LVS plus macro-top blackbox connectivity LVS.
- `gf180mcu_3v3_12t_2r2w_sram_periphery_lvs.py` gates the packaged
  transistor-level row decode/WL-driver, write-driver, precharge/sense, and
  write-conflict leaf reports.
- `gf180mcu_3v3_12t_2r2w_sram_tile_lvs.py` checks the extracted 4x4 tile subcircuit against an
  independently generated 12T MOS reference.
- `gf180mcu_3v3_12t_2r2w_sram_macro_lvs.py` checks the macro-top tile instance connectivity
  with the tile treated as an LVS-clean blackbox.

`gf180mcu_3v3_12t_2r2w_sram_connectivity_check.py` remains a fast text tripwire for the same
macro-top failure mode, but the Netgen scripts are the real LVS checks.

These checks do not replace full device-expanded macro LVS/PEX,
sense-amplifier/write-driver characterization, Liberty generation, EM/IR,
density, antenna, or foundry signoff.

## Release LVS

To check the published extracted SPICE, run the scripts with no positional
argument. They use `reports/pin_lvs_pex_signoff` when the package has unpacked
reports, or `reports.zip` in the repository publication layout.

```bash
python3 verification/gf180mcu_3v3_12t_2r2w_sram_lvs_gate.py
python3 verification/gf180mcu_3v3_12t_2r2w_sram_periphery_lvs.py
python3 verification/gf180mcu_3v3_12t_2r2w_sram_tile_lvs.py
python3 verification/gf180mcu_3v3_12t_2r2w_sram_macro_lvs.py
python3 verification/gf180mcu_3v3_12t_2r2w_sram_connectivity_check.py
```

The Netgen scripts accept `--netgen-setup`; otherwise they use
`GF180_NETGEN_SETUP`, `NETGEN_SETUP`, or the usual `GF180_PDK_ROOT` /
`PDK_ROOT` environment layout.

`gf180mcu_3v3_12t_2r2w_sram_tile_lvs.py` should pass when the 4x4 tile device
topology is clean. `gf180mcu_3v3_12t_2r2w_sram_macro_lvs.py` should pass when
the macro-top tile instance connectivity is clean. The release gate currently
passes on all four published macro variants and reports no tile signal ports
tied to `VDD` or `VSS`; the old `c3_r1_rbl` to `VSS` failure mode is kept as a
regression target by these scripts.

The periphery gate currently checks five generated Tim-derived leaf blocks:
write row decode/WL driver, read row decode/WL driver, write driver,
precharge/sense, and write-conflict control. Each leaf must have Magic DRC
`0`, Netgen LVS `match`/`match_unique`, zero disconnected pins, and the expected
pin contract, including `dout` as the SAOUT-equivalent read output.

## Leaf Storage

The leaf storage runner checks write, retention, independent dual read,
read-disturb, disabled-write hold, same-data dual write, and opposite same-cell
dual-write conflict observation on the 12T topology.

```bash
python3 verification/run_leaf_storage_checks.py
```

The generated report is written to `verification/results/README.md`. Raw
generated decks and ngspice logs are written under `verification/results/spice/`
and are intentionally git-ignored.
