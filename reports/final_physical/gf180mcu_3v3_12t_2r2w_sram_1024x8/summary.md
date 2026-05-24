# gf180mcu_3v3_12t_2r2w_sram_1024x8 current Final Physical

| Check | Result |
| --- | --- |
| Source shell | `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` |
| Logical shape | `1024 x 8` |
| Physical rows / groups | `128` / `8` |
| Size | `585.560um x 618.040um` |
| Area | `0.361900mm^2` |
| Area/bit | `44.177um^2/bit` |
| Row-edge width | `167.360um` |
| Port strip width | `37.840um` |
| Boundary pins | `79` |
| Magic DRC | `0` |
| Footprint status | `warn_within_5pct` |

This is the final hard-macro physical abstract for top-level integration:
GDS, LEF, Magic, blackbox CDL/SV, behavioral model, decode contract,
row-edge corridors, boundary pins, and M4/M5 power are emitted.

The dense transistor-level row-select matrix is still represented by the
current structural CDL and leaf library rather than expanded into this top
GDS one row at a time.
