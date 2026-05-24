# GF180MCU 12T SRAM Local Open-Source Signoff

- Overall status: `WARN`
- Status counts: `{'PASS': 24, 'OPEN': 5, 'WARN': 4}`

This is the strongest local open-source gate currently available in this tree.
It is not a foundry signoff replacement.

| Area | Check | Status | Detail | Evidence |
| --- | --- | --- | --- | --- |
| `Open signoff` | `Prior staged open signoff` | `PASS` | counts={'OPEN': 5, 'PASS': 62, 'WARN': 2} | `build/open_signoff/MANIFEST.json` |
| `LVS` | `current transistor control primitive Netgen LVS` | `PASS` | checked=7, fails=0, details=[] | `build/control_primitives/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `Magic final macro DRC` | `PASS` | manifest_drc=0, parsed_drc=0 | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_1024x32/layout/gf180mcu_3v3_12t_2r2w_sram_1024x32.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `Magic PEX extraction` | `PASS` | rc_spice_bytes=2009110, stats={'subckt': 2, 'resistors': 4153, 'capacitors': 0, 'mos': 0, 'instances': 2240}, has_rc=True | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x32/pex/gf180mcu_3v3_12t_2r2w_sram_1024x32.magic_pex.log` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `Final abstract pin LVS` | `PASS` | ref_pins=175, extracted_pins=175, missing=[], extra=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x32/pex/gf180mcu_3v3_12t_2r2w_sram_1024x32.current_pdk.spice` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `Full device-expanded macro LVS` | `OPEN` | final top GDS is a hard-macro abstract; full row-select/predecode device expansion remains separate from this top-level GDS | `build/open_signoff/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `KLayout GF180 density deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x32/density/gf180mcu_3v3_12t_2r2w_sram_1024x32.density.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `KLayout GF180 antenna deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x32/antenna/gf180mcu_3v3_12t_2r2w_sram_1024x32.antenna.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32` | `Local EM/IR power strap audit` | `WARN` | proxy pass: M5 VSS=40.0um, VDD=24.0um over 1004.0um; 32 column ties. No solver-grade current map. | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_1024x32/abstract/gf180mcu_3v3_12t_2r2w_sram_1024x32.pins.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `Magic final macro DRC` | `PASS` | manifest_drc=0, parsed_drc=0 | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_1024x8/layout/gf180mcu_3v3_12t_2r2w_sram_1024x8.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `Magic PEX extraction` | `PASS` | rc_spice_bytes=516893, stats={'subckt': 2, 'resistors': 1049, 'capacitors': 0, 'mos': 0, 'instances': 704}, has_rc=True | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x8/pex/gf180mcu_3v3_12t_2r2w_sram_1024x8.magic_pex.log` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `Final abstract pin LVS` | `PASS` | ref_pins=79, extracted_pins=79, missing=[], extra=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x8/pex/gf180mcu_3v3_12t_2r2w_sram_1024x8.current_pdk.spice` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `Full device-expanded macro LVS` | `OPEN` | final top GDS is a hard-macro abstract; full row-select/predecode device expansion remains separate from this top-level GDS | `build/open_signoff/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `KLayout GF180 density deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x8/density/gf180mcu_3v3_12t_2r2w_sram_1024x8.density.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `KLayout GF180 antenna deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_1024x8/antenna/gf180mcu_3v3_12t_2r2w_sram_1024x8.antenna.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8` | `Local EM/IR power strap audit` | `WARN` | proxy pass: M5 VSS=40.0um, VDD=24.0um over 585.6um; 16 column ties. No solver-grade current map. | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_1024x8/abstract/gf180mcu_3v3_12t_2r2w_sram_1024x8.pins.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `Magic final macro DRC` | `PASS` | manifest_drc=0, parsed_drc=0 | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_512x32/layout/gf180mcu_3v3_12t_2r2w_sram_512x32.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `Magic PEX extraction` | `PASS` | rc_spice_bytes=1014745, stats={'subckt': 2, 'resistors': 2105, 'capacitors': 0, 'mos': 0, 'instances': 1216}, has_rc=True | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x32/pex/gf180mcu_3v3_12t_2r2w_sram_512x32.magic_pex.log` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `Final abstract pin LVS` | `PASS` | ref_pins=171, extracted_pins=171, missing=[], extra=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x32/pex/gf180mcu_3v3_12t_2r2w_sram_512x32.current_pdk.spice` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `Full device-expanded macro LVS` | `OPEN` | final top GDS is a hard-macro abstract; full row-select/predecode device expansion remains separate from this top-level GDS | `build/open_signoff/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `KLayout GF180 density deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x32/density/gf180mcu_3v3_12t_2r2w_sram_512x32.density.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `KLayout GF180 antenna deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x32/antenna/gf180mcu_3v3_12t_2r2w_sram_512x32.antenna.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32` | `Local EM/IR power strap audit` | `WARN` | proxy pass: M5 VSS=40.0um, VDD=24.0um over 1004.0um; 32 column ties. No solver-grade current map. | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_512x32/abstract/gf180mcu_3v3_12t_2r2w_sram_512x32.pins.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `Magic final macro DRC` | `PASS` | manifest_drc=0, parsed_drc=0 | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_512x8/layout/gf180mcu_3v3_12t_2r2w_sram_512x8.drc.log` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `Magic PEX extraction` | `PASS` | rc_spice_bytes=269499, stats={'subckt': 2, 'resistors': 537, 'capacitors': 0, 'mos': 0, 'instances': 448}, has_rc=True | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x8/pex/gf180mcu_3v3_12t_2r2w_sram_512x8.magic_pex.log` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `Final abstract pin LVS` | `PASS` | ref_pins=75, extracted_pins=75, missing=[], extra=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x8/pex/gf180mcu_3v3_12t_2r2w_sram_512x8.current_pdk.spice` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `Full device-expanded macro LVS` | `OPEN` | final top GDS is a hard-macro abstract; full row-select/predecode device expansion remains separate from this top-level GDS | `build/open_signoff/MANIFEST.json` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `KLayout GF180 density deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x8/density/gf180mcu_3v3_12t_2r2w_sram_512x8.density.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `KLayout GF180 antenna deck` | `PASS` | returncode=0, violations=0, sample_categories=[] | `build/pin_lvs_pex_signoff/gf180mcu_3v3_12t_2r2w_sram_512x8/antenna/gf180mcu_3v3_12t_2r2w_sram_512x8.antenna.lyrdb` |
| `gf180mcu_3v3_12t_2r2w_sram_512x8` | `Local EM/IR power strap audit` | `WARN` | proxy pass: M5 VSS=40.0um, VDD=24.0um over 585.6um; 16 column ties. No solver-grade current map. | `build/final_physical/gf180mcu_3v3_12t_2r2w_sram_512x8/abstract/gf180mcu_3v3_12t_2r2w_sram_512x8.pins.json` |
| `SNM proxy` | `12T VDD sweep ngspice` | `PASS` | missing=[] bad=[] checked=18 | `build` |
| `SNM proxy` | `12T disturb/conflict ngspice` | `PASS` | missing=[] bad=[] checked=3 corners | `build` |
| `SNM` | `Butterfly SNM / extracted final RC SNM` | `OPEN` | current local evidence is VDD sweep and disturb/conflict; butterfly SNM on final extracted RC is not implemented yet | `build` |
