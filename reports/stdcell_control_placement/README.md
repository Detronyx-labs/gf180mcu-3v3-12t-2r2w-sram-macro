# Stdcell Control Placement

This report places only the Avalon stdcell control gates inside the
existing top/bottom control bands. It does not grow macro width or height.

| Macro | Status | Placed stdcells | Deferred row-select | Overall util | Max row util |
| --- | --- | ---: | ---: | ---: | ---: |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `PASS` | 276 | 256 | 0.127 | 0.128 |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `PASS` | 276 | 512 | 0.074 | 0.075 |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `PASS` | 322 | 512 | 0.157 | 0.158 |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `PASS` | 354 | 1024 | 0.108 | 0.109 |

This placement stage deliberately defers row-select/WL-buffer instances out of
the top/bottom control bands. They are closed by the row-pitch-compatible
Avalon expansion in `reports/stdcell_row_select_placement/` and
`reports/stdcell_row_select_gds_merge/`. Periphery leaf placement remains open.
