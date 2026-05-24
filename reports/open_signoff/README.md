# current Open-Source Signoff Report

- Overall status: `WARN`
- Status counts: `{'PASS': 62, 'WARN': 2, 'OPEN': 5}`

This is an open-source evidence gate, not a foundry signoff waiver.

| Area | Check | Status | Detail | Evidence |
| --- | --- | --- | --- | --- |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `RC6 physical shell Magic DRC` | `PASS` | drc_errors=0 | `build/full_control_arrays_reference/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control/layout/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `RC6 shell area budget` | `PASS` | status=pass_target, area=0.158936904mm^2, max=0.2mm^2 | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `RC6 shell deliverables exist` | `PASS` | missing=[] | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `RC6 physical shell Magic DRC` | `PASS` | drc_errors=0 | `build/full_control_arrays_reference/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control/layout/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `RC6 shell area budget` | `PASS` | status=pass_target, area=0.546718184mm^2, max=0.6mm^2 | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `RC6 shell deliverables exist` | `PASS` | missing=[] | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `RC6 physical shell Magic DRC` | `PASS` | drc_errors=0 | `build/full_control_arrays_reference/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `RC6 shell area budget` | `PASS` | status=pass_target, area=0.288130248mm^2, max=0.35mm^2 | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `RC6 shell deliverables exist` | `PASS` | missing=[] | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `RC6 physical shell Magic DRC` | `PASS` | drc_errors=0 | `build/full_control_arrays_reference/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `RC6 shell area budget` | `PASS` | status=pass_target, area=1.036998888mm^2, max=1.2mm^2 | `build/full_control_arrays_reference/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `RC6 shell deliverables exist` | `PASS` | missing=[] | `build/full_control_arrays_reference/MANIFEST.json` |
| `inv` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_inv/layout/gf180mcu_3v3_12t_sram_ctrl_inv.drc.log` |
| `inv` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_inv/layout/gf180mcu_3v3_12t_sram_ctrl_inv.netgen_lvs.log` |
| `inv` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_inv/layout/gf180mcu_3v3_12t_sram_ctrl_inv.netgen_lvs.log` |
| `inv` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `nand2` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand2/layout/gf180mcu_3v3_12t_sram_ctrl_nand2.drc.log` |
| `nand2` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand2/layout/gf180mcu_3v3_12t_sram_ctrl_nand2.netgen_lvs.log` |
| `nand2` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand2/layout/gf180mcu_3v3_12t_sram_ctrl_nand2.netgen_lvs.log` |
| `nand2` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `nand3` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand3/layout/gf180mcu_3v3_12t_sram_ctrl_nand3.drc.log` |
| `nand3` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand3/layout/gf180mcu_3v3_12t_sram_ctrl_nand3.netgen_lvs.log` |
| `nand3` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand3/layout/gf180mcu_3v3_12t_sram_ctrl_nand3.netgen_lvs.log` |
| `nand3` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `nand4` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand4/layout/gf180mcu_3v3_12t_sram_ctrl_nand4.drc.log` |
| `nand4` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand4/layout/gf180mcu_3v3_12t_sram_ctrl_nand4.netgen_lvs.log` |
| `nand4` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nand4/layout/gf180mcu_3v3_12t_sram_ctrl_nand4.netgen_lvs.log` |
| `nand4` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `nor2` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nor2/layout/gf180mcu_3v3_12t_sram_ctrl_nor2.drc.log` |
| `nor2` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nor2/layout/gf180mcu_3v3_12t_sram_ctrl_nor2.netgen_lvs.log` |
| `nor2` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_nor2/layout/gf180mcu_3v3_12t_sram_ctrl_nor2.netgen_lvs.log` |
| `nor2` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `row_select3_wlbuf` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_row_select3_wlbuf/layout/gf180mcu_3v3_12t_sram_ctrl_row_select3_wlbuf.drc.log` |
| `row_select3_wlbuf` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_row_select3_wlbuf/layout/gf180mcu_3v3_12t_sram_ctrl_row_select3_wlbuf.netgen_lvs.log` |
| `row_select3_wlbuf` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_row_select3_wlbuf/layout/gf180mcu_3v3_12t_sram_ctrl_row_select3_wlbuf.netgen_lvs.log` |
| `row_select3_wlbuf` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `row_select4_wlbuf` | `current control primitive Magic DRC` | `PASS` | drc_errors=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_row_select4_wlbuf/layout/gf180mcu_3v3_12t_sram_ctrl_row_select4_wlbuf.drc.log` |
| `row_select4_wlbuf` | `current control primitive Netgen LVS` | `PASS` | lvs=match_unique, disconnected_pins=0 | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_row_select4_wlbuf/layout/gf180mcu_3v3_12t_sram_ctrl_row_select4_wlbuf.netgen_lvs.log` |
| `row_select4_wlbuf` | `current Netgen log scan` | `PASS` | match marker present | `build/control_primitives/gf180mcu_3v3_12t_sram_ctrl_row_select4_wlbuf/layout/gf180mcu_3v3_12t_sram_ctrl_row_select4_wlbuf.netgen_lvs.log` |
| `row_select4_wlbuf` | `current primitive deliverables exist` | `PASS` | missing=[] | `build/control_primitives/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `current structural CDL sanity` | `PASS` | subckt/ends present; no constanted write/precharge control assignments | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control.stage_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `current generated SV syntax` | `PASS` | iverilog accepted | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control.stage_control_matrix.sv` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `current standalone gate area warning label` | `PASS` | standalone_gate_area_mm2=1.273463414 | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control/README.md` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `current structural CDL sanity` | `PASS` | subckt/ends present; no constanted write/precharge control assignments | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control.stage_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `current generated SV syntax` | `PASS` | iverilog accepted | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control.stage_control_matrix.sv` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `current standalone gate area warning label` | `PASS` | standalone_gate_area_mm2=2.200312944 | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control/README.md` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `current structural CDL sanity` | `PASS` | subckt/ends present; no constanted write/precharge control assignments | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control.stage_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `current generated SV syntax` | `PASS` | iverilog accepted | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control.stage_control_matrix.sv` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `current standalone gate area warning label` | `PASS` | standalone_gate_area_mm2=2.246035345 | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control/README.md` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `current structural CDL sanity` | `PASS` | subckt/ends present; no constanted write/precharge control assignments | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control.stage_control_matrix.cdl` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `current generated SV syntax` | `PASS` | iverilog accepted | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control.stage_control_matrix.sv` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `current standalone gate area warning label` | `PASS` | standalone_gate_area_mm2=4.128926353 | `build/stage_control_matrix/gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control/README.md` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `current real footprint estimate` | `PASS` | release estimate 0.199629mm^2 <= max 0.200000mm^2; status=release_lvs_leaf_fits_budget | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `Timothy xdec pitch fits folded rows` | `PASS` | row_pitch=4.326875um, tim_xdec64_pitch=3.101797um | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `current real footprint estimate` | `WARN` | release LVS strip estimate 0.620487mm^2 is 3.41% over max; dense DRC-only lower bound 0.599635mm^2 fits; status=needs_abutted_strip_lvs_dense_width | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `Timothy xdec pitch fits folded rows` | `PASS` | row_pitch=4.328437um, tim_xdec64_pitch=3.101797um | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `current real footprint estimate` | `WARN` | release LVS strip estimate 0.361900mm^2 is 3.40% over max; dense DRC-only lower bound 0.341047mm^2 fits; status=needs_abutted_strip_lvs_dense_width | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `Timothy xdec pitch fits folded rows` | `PASS` | row_pitch=4.328437um, tim_xdec64_pitch=3.101797um | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `current real footprint estimate` | `PASS` | release estimate 1.176922mm^2 <= max 1.200000mm^2; status=release_lvs_leaf_fits_budget | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `Timothy xdec pitch fits folded rows` | `PASS` | row_pitch=4.329219um, tim_xdec64_pitch=3.101797um | `build/stage_row_edge_budget/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `current area vs duplicated Timothy 1RW baseline` | `PASS` | ratio=1.029x, stage=0.199629mm^2, duplicated_timothy=0.193971mm^2 | `build/stage_vs_timothy_6t/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `current area vs duplicated Timothy 1RW baseline` | `PASS` | ratio=0.800x, stage=0.620487mm^2, duplicated_timothy=0.775884mm^2 | `build/stage_vs_timothy_6t/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `current area vs duplicated Timothy 1RW baseline` | `PASS` | ratio=0.933x, stage=0.361900mm^2, duplicated_timothy=0.387942mm^2 | `build/stage_vs_timothy_6t/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `current area vs duplicated Timothy 1RW baseline` | `PASS` | ratio=0.758x, stage=1.176922mm^2, duplicated_timothy=1.551767mm^2 | `build/stage_vs_timothy_6t/MANIFEST.json` |
| `Residual Risk` | `Full Macro LVS` | `OPEN` | integrated row-edge strip plus array/periphery full Netgen LVS is still a next physical closure step | `open-source package boundary` |
| `Residual Risk` | `PEX` | `OPEN` | full array/tile/periphery parasitic extraction and Liberty characterization are not final | `open-source package boundary` |
| `Residual Risk` | `EM/IR` | `OPEN` | open-source package records power topology but does not replace solver-grade EM/IR signoff | `open-source package boundary` |
| `Residual Risk` | `Antenna/Density` | `OPEN` | macro-level antenna and density decks still need final GDS integration context | `open-source package boundary` |
| `Residual Risk` | `Silicon SRAM Signoff` | `OPEN` | SNM/read-disturb/half-select/dual-write sweeps need extracted final leaf/tile/periphery RC | `open-source package boundary` |
