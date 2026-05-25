# gf180mcu_3v3_12t_2r2w_sram_512x8 expanded Column Periphery Physical

| Check | Result |
| --- | --- |
| Source shell | `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` |
| Logical shape | `512 x 8` |
| Physical rows / groups | `64` / `8` |
| Size | `594.640um x 389.800um` |
| Area | `0.231791mm^2` |
| Area/bit | `56.590um^2/bit` |
| Row-edge width | `167.360um` |
| Port strip width | `37.840um` |
| Boundary pins | `75` |
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
