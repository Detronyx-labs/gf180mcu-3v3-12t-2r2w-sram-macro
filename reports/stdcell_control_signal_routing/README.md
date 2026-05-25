# Stdcell Control Signal Routing

Top-level M2/M3 routes connect the expanded Avalon control/predecode netlist endpoints, including macro address/enable pins and row-select NAND input sinks.
The route geometry is emitted into one idempotent child route cell per macro, instantiated at the top level without changing the macro footprint.

| Macro | Status | Routed nets | Routed endpoints | Row-select input nets | Macro-pin nets | Route shapes | Footprint |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `PASS` | 381 | 5112 | 100 | 44 | 36253 | `true` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `PASS` | 333 | 2904 | 68 | 44 | 20749 | `true` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `PASS` | 299 | 2772 | 68 | 40 | 19783 | `true` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `PASS` | 283 | 1732 | 52 | 40 | 12487 | `true` |

Smoke DRC:

- `gf180mcu_3v3_12t_2r2w_sram_512x8`: GF180 KLayout `main.drc` PASS, `0` violations, report `reports/stdcell_control_signal_routing/gf180mcu_3v3_12t_2r2w_sram_512x8/main_drc.lyrdb`.
