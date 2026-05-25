# GF180MCU 12T SRAM Stdcell Control Routing Gate

- Counts: `{'PASS': 18}`

| Scope | Check | Status | Detail | Evidence |
| --- | --- | --- | --- | --- |
| `control_signal_routing` | `manifest status` | `PASS` | status=PASS | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `routing status` | `PASS` | status=PASS detail=[] | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `route cell present in GDS` | `PASS` | route_cell=gf180mcu_3v3_12t_2r2w_sram_1024x32_stdcell_control_signal_routes gds_exists=True | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x32/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `routed net/endpoints coverage` | `PASS` | routed_nets=381, routed_endpoints=5112, row_select_input_nets=100, macro_pin_nets=44 | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `footprint unchanged` | `PASS` | bbox_after={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 1003.96, 'top_um': 1172.28, 'width_um': 1003.96, 'height_um': 1172.28} | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x32/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `routing status` | `PASS` | status=PASS detail=[] | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `route cell present in GDS` | `PASS` | route_cell=gf180mcu_3v3_12t_2r2w_sram_1024x8_stdcell_control_signal_routes gds_exists=True | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x8/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `routed net/endpoints coverage` | `PASS` | routed_nets=333, routed_endpoints=2904, row_select_input_nets=68, macro_pin_nets=44 | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `footprint unchanged` | `PASS` | bbox_after={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 585.56, 'top_um': 618.04, 'width_um': 585.56, 'height_um': 618.04} | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x8/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `routing status` | `PASS` | status=PASS detail=[] | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `route cell present in GDS` | `PASS` | route_cell=gf180mcu_3v3_12t_2r2w_sram_512x32_stdcell_control_signal_routes gds_exists=True | `macros/gf180mcu_3v3_12t_2r2w_sram_512x32/layout/gf180mcu_3v3_12t_2r2w_sram_512x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `routed net/endpoints coverage` | `PASS` | routed_nets=299, routed_endpoints=2772, row_select_input_nets=68, macro_pin_nets=40 | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `footprint unchanged` | `PASS` | bbox_after={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 1003.96, 'top_um': 618.04, 'width_um': 1003.96, 'height_um': 618.04} | `macros/gf180mcu_3v3_12t_2r2w_sram_512x32/layout/gf180mcu_3v3_12t_2r2w_sram_512x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `routing status` | `PASS` | status=PASS detail=[] | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `route cell present in GDS` | `PASS` | route_cell=gf180mcu_3v3_12t_2r2w_sram_512x8_stdcell_control_signal_routes gds_exists=True | `macros/gf180mcu_3v3_12t_2r2w_sram_512x8/layout/gf180mcu_3v3_12t_2r2w_sram_512x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `routed net/endpoints coverage` | `PASS` | routed_nets=283, routed_endpoints=1732, row_select_input_nets=52, macro_pin_nets=40 | `reports/stdcell_control_signal_routing/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `footprint unchanged` | `PASS` | bbox_after={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 585.56, 'top_um': 340.92, 'width_um': 585.56, 'height_um': 340.92} | `macros/gf180mcu_3v3_12t_2r2w_sram_512x8/layout/gf180mcu_3v3_12t_2r2w_sram_512x8.gds` |
| `smoke_drc` | `GF180 main.drc on 512x8 routed control GDS` | `PASS` | violations=0 categories=[] | `reports/stdcell_control_signal_routing/gf180mcu_3v3_12t_2r2w_sram_512x8/main_drc.lyrdb` |
