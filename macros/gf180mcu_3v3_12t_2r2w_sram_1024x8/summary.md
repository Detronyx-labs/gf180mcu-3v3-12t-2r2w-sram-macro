# gf180mcu_3v3_12t_2r2w_sram_1024x8 expanded Column Periphery Physical

| Check | Result |
| --- | --- |
| Source shell | `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` |
| Logical shape | `1024 x 8` |
| Physical rows / groups | `128` / `8` |
| Size | `594.640um x 666.920um` |
| Area | `0.396577mm^2` |
| Area/bit | `48.410um^2/bit` |
| Row-edge width | `167.360um` |
| Port strip width | `37.840um` |
| Boundary pins | `79` |
| Magic DRC | `0` |
| Footprint status | `warn_within_5pct` |

This is the hybrid compact hard-macro physical abstract for top-level integration:
GDS, LEF, blackbox CDL/SV, behavioral model, decode contract, row-edge
corridors, boundary pins, M4/M5 power, Avalon control/row-select stdcells,
and compact column precharge/sense and write-driver leaves are emitted. Column
periphery placement consumes the existing top/bottom control bands before
growing the wrapper.

Full device-expanded schematic-vs-layout LVS remains staged separately from
this physical wrapper summary.
