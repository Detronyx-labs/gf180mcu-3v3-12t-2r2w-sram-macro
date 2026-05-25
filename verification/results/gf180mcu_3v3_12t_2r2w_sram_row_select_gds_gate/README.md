# GF180MCU 12T SRAM Row-Select GDS Gate

- Counts: `{'PASS': 23}`

| Scope | Check | Status | Detail | Evidence |
| --- | --- | --- | --- | --- |
| `row_select_placement` | `manifest status` | `PASS` | status=PASS | `reports/stdcell_row_select_placement/MANIFEST.json` |
| `row_select_gds` | `manifest status` | `PASS` | status=PASS | `reports/stdcell_row_select_gds_merge/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `GDS merge status` | `PASS` | status=PASS detail=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_512x8/layout/gf180mcu_3v3_12t_2r2w_sram_512x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `row-select stdcell count` | `PASS` | row_selects=256 placed=1024 gds_delta=1024 | `reports/stdcell_row_select_gds_merge/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `footprint unchanged` | `PASS` | bbox={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 585.56, 'top_um': 340.92, 'width_um': 585.56, 'height_um': 340.92} | `macros/gf180mcu_3v3_12t_2r2w_sram_512x8/layout/gf180mcu_3v3_12t_2r2w_sram_512x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `row-select stdcell names present` | `PASS` | missing=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_512x8/layout/gf180mcu_3v3_12t_2r2w_sram_512x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `custom row-select leaf removed from full-control CDL` | `PASS` | exists=True custom_refs=False | `macros/gf180mcu_3v3_12t_2r2w_sram_512x8/abstract/gf180mcu_3v3_12t_2r2w_sram_512x8.stdcell_full_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `GDS merge status` | `PASS` | status=PASS detail=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_512x32/layout/gf180mcu_3v3_12t_2r2w_sram_512x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `row-select stdcell count` | `PASS` | row_selects=512 placed=2048 gds_delta=2048 | `reports/stdcell_row_select_gds_merge/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `footprint unchanged` | `PASS` | bbox={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 1003.96, 'top_um': 618.04, 'width_um': 1003.96, 'height_um': 618.04} | `macros/gf180mcu_3v3_12t_2r2w_sram_512x32/layout/gf180mcu_3v3_12t_2r2w_sram_512x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `row-select stdcell names present` | `PASS` | missing=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_512x32/layout/gf180mcu_3v3_12t_2r2w_sram_512x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `custom row-select leaf removed from full-control CDL` | `PASS` | exists=True custom_refs=False | `macros/gf180mcu_3v3_12t_2r2w_sram_512x32/abstract/gf180mcu_3v3_12t_2r2w_sram_512x32.stdcell_full_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `GDS merge status` | `PASS` | status=PASS detail=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x8/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `row-select stdcell count` | `PASS` | row_selects=512 placed=2048 gds_delta=2048 | `reports/stdcell_row_select_gds_merge/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `footprint unchanged` | `PASS` | bbox={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 585.56, 'top_um': 618.04, 'width_um': 585.56, 'height_um': 618.04} | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x8/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `row-select stdcell names present` | `PASS` | missing=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x8/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `custom row-select leaf removed from full-control CDL` | `PASS` | exists=True custom_refs=False | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x8/abstract/gf180mcu_3v3_12t_2r2w_sram_1024x8.stdcell_full_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `GDS merge status` | `PASS` | status=PASS detail=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x32/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `row-select stdcell count` | `PASS` | row_selects=1024 placed=4096 gds_delta=4096 | `reports/stdcell_row_select_gds_merge/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `footprint unchanged` | `PASS` | bbox={'left_um': 0.0, 'bottom_um': 0.0, 'right_um': 1003.96, 'top_um': 1172.28, 'width_um': 1003.96, 'height_um': 1172.28} | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x32/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `row-select stdcell names present` | `PASS` | missing=[] | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x32/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32.gds` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `custom row-select leaf removed from full-control CDL` | `PASS` | exists=True custom_refs=False | `macros/gf180mcu_3v3_12t_2r2w_sram_1024x32/abstract/gf180mcu_3v3_12t_2r2w_sram_1024x32.stdcell_full_control_matrix.cdl` |
| `smoke_drc` | `GF180 main.drc on 512x8 row-select GDS` | `PASS` | violations=0 categories=[] | `reports/stdcell_row_select_gds_merge/gf180mcu_3v3_12t_2r2w_sram_512x8/main_drc.lyrdb` |
