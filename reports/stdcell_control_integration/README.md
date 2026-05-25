# Avalon Stdcell Control Integration

This report binds the SRAM control matrix to real GF180MCU 3.3V
Avalon standard-cell collateral for ordinary digital logic.
The initial control matrix keeps SRAM-specific row-select/WL-buffer cells as
logical custom leaves; the later row-select expansion report maps those leaves
to row-pitch-compatible Avalon `NAND4 + 3*INV` physical rows.

| Macro | Physical WL Rows | Control Gates | Avalon Gates | Custom Row-Select |
| --- | ---: | ---: | ---: | ---: |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `64` | `532` | `276` | `256` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `128` | `788` | `276` | `512` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `128` | `834` | `322` | `512` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `256` | `1378` | `354` | `1024` |

Included Avalon collateral:

- merged GDS
- LEF and min/nom/max tech LEF
- CDL
- Verilog
- TT/SS/FF Liberty corners

The published top macro GDS files physically contain the placed
Avalon `INV`/`NAND`/`NOR` control stdcells after the GDS merge step. The
row-select/WL-buffer physical expansion is in
`reports/stdcell_row_select_gds_merge/`; periphery leaves remain separate until
full macro periphery integration is generated.
