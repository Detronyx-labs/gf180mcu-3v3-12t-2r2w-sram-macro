# GF180MCU 3.3V 12T 2R2W SRAM Macro

<p align="center">
  <img src="assets/work-in-progress.svg" alt="WORK IN PROGRESS - NOT TAPEOUT SIGNOFF" width="100%">
</p>

This package contains the current Detronyx custom SRAM review collateral for a GF180MCU 3.3V-oriented 12T two-read/two-write hard macro. It is prepared for external engineering review, not presented as foundry tapeout signoff.

## Macro Variants

| Macro | Rows | Data width | Bits | Size um | Area mm2 | Area per bit um2 | Pins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | 1024 | 32 | 32768 | 1003.960 x 1172.280 | 1.176922 | 35.917 | 175 |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | 1024 | 8 | 8192 | 585.560 x 618.040 | 0.361900 | 44.177 | 79 |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | 512 | 32 | 16384 | 1003.960 x 618.040 | 0.620487 | 37.872 | 171 |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | 512 | 8 | 4096 | 585.560 x 340.920 | 0.199629 | 48.738 | 75 |

## Verification Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| 12T leaf storage checks | `PASS` locally | See `verification/README.md` and `verification/results/README.md`. |
| Final pin-LVS / R-aware PEX | `{'OPEN': 5, 'PASS': 24, 'WARN': 4}` | See `reports.zip` path `reports/pin_lvs_pex_signoff/README.md`. |
| Release Netgen LVS gate | `PASS` | Tile device LVS plus macro-top tile blackbox LVS. Counts: `{'PASS': 8}`. The prior VSS PDN column / `c3_r1_rbl` short is fixed and covered as a regression target. See `reports.zip` path `reports/lvs_gate/README.md` and `verification/`. |
| C-aware timing proxy | `WARN` | Source: `openrcx_geometry_fallback`. See `reports.zip` path `reports/cap_pex_timing/README.md`. |
| Native Magic C extraction | `OPEN` | Local GF180MCU Magic techfile emits R/devices but no capacitance coefficients; OpenRCX fallback is used for C timing proxy. |
| Local density/fill and antenna | `PASS` | KLayout GF180 density and antenna decks pass on all four published GDS variants. |
| Foundry signoff | `OPEN` | Needs independent PDK/foundry-grade LVS/PEX/DRC/EM/IR review. |

## Contents

- `macros/`: GDS, LEF, SPICE blackbox, SystemVerilog blackbox/behavioral/decode contracts, pin JSON, and per-macro summaries.
- `reports.zip`: generated physical, signoff, C/OpenRCX timing, and staged open-source evidence.
- `verification/`: release-facing LVS and connectivity scripts for the packaged extracted reports.
- `scripts/`: release-facing generator entrypoints and helper modules used to build the array and final physical macro collateral.
- `MANIFEST.json`: package file inventory, public macro aliases, and GDS top-cell rewrite status.

## Implementation Basis

- Timothy Edwards / Open Circuit Design GF180MCU 3.3V SRAM macros: https://github.com/RTimothyEdwards/gf180mcu_ocd_ip_sram
- Timothy Edwards 512x8 3.3V SRAM macro used as the main GF180 transistor/layout reference: https://github.com/RTimothyEdwards/gf180mcu_ocd_ip_sram/tree/main/cells/gf180mcu_ocd_ip_sram__sram512x8m8wm1
- Original Google/GF open GF180MCU SRAM macro repository: https://github.com/google/globalfoundries-pdk-ip-gf180mcu_fd_ip_sram

## Regeneration Notes

This publication bundle is generated from the Detronyx GF180 SRAM experiment workspace. The public package intentionally uses neutral macro aliases and includes release-facing verification and generator scripts, not the full local experiment workspace. For local regeneration, use the matching Detronyx workspace flow that produced `reports/final_physical`, `reports/pin_lvs_pex_signoff`, `reports/lvs_gate`, and `reports/cap_pex_timing`. Use the KLayout Python package when regenerating the bundle if GDS top-cell names must be rewritten to the public aliases.

## Review Questions

- Are the 12T 2W2R bitcell and shared M4/M5 escape assumptions physically defensible for GF180MCU?
- Is the current footprint strategy acceptable before investing in full custom periphery expansion?
- What minimum extra characterization is required before this can become tapeout-intent memory collateral?
- Should the next step be full OpenRCX/DEF-based extraction, foundry-rule PEX, or transistor-level sense/write periphery closure?

## Known Open Items

- Full device-expanded macro LVS for the final abutted row-edge/control matrix.
- Final extracted-RC SPICE characterization with real decoder, write driver, precharge, and sense amplifier devices.
- SNM/read-disturb/half-select/dual-write sweeps on final extracted parasitics.
- Liberty characterization: setup/hold, clk-to-q, pin caps, power, and invalid arcs.
- EM/IR with real current profiles, foundry density/fill review, latch-up/package review, and final tapeout signoff.
