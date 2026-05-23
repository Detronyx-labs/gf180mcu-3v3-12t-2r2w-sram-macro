# gf180mcu_3v3_12t_2r2w_sram_1024x32 current Final Physical

| Check | Result |
| --- | --- |
| Source shell | `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` |
| Logical shape | `1024 x 32` |
| Physical rows / groups | `256` / `4` |
| Size | `1003.960um x 1172.280um` |
| Area | `1.176922mm^2` |
| Area/bit | `35.917um^2/bit` |
| Row-edge width | `167.360um` |
| Port strip width | `37.840um` |
| Boundary pins | `175` |
| Magic DRC | `None` |
| Footprint status | `pass_max` |

This is the final hard-macro physical abstract for top-level integration:
GDS, LEF, Magic, blackbox CDL/SV, behavioral model, decode contract,
row-edge corridors, boundary pins, and M4/M5 power are emitted.

The dense transistor-level row-select matrix is still represented by the
current structural CDL and leaf library rather than expanded into this top
GDS one row at a time.
