# gf180mcu_3v3_12t_2r2w_sram_1024x32 expanded Column Periphery Physical

| Check | Result |
| --- | --- |
| Source shell | `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` |
| Logical shape | `1024 x 32` |
| Physical rows / groups | `256` / `4` |
| Size | `1019.545um x 1306.950um` |
| Area | `1.332494mm^2` |
| Area/bit | `40.665um^2/bit` |
| Row-edge width | `167.360um` |
| Port strip width | `37.840um` |
| Boundary pins | `175` |
| Magic DRC | `0` |
| Footprint status | `pass_max` |

This is the hybrid compact hard-macro physical abstract for top-level integration:
GDS, LEF, blackbox CDL/SV, behavioral model, decode contract, row-edge
corridors, boundary pins, M4/M5 power, Avalon control/row-select stdcells,
and compact column precharge/sense and write-driver leaves are emitted. Column
periphery placement consumes the existing top/bottom control bands before
growing the wrapper.

Full device-expanded schematic-vs-layout LVS remains staged separately from
this physical wrapper summary.
