# Avalon GF180MCU 3.3V Stdcell Collateral

This directory vendors the Avalon `gf180mcu_as_sc_mcu7t3v3` standard-cell
library collateral required by the SRAM control-matrix release package.

Source repository:
https://github.com/AvalonSemiconductors/gf180mcu_as_sc_mcu7t3v3

License: Apache-2.0.  See `LICENSE`.

Included views:

- merged GDS
- CDL
- LEF and min/nom/max tech LEF
- Verilog model
- TT/SS/FF Liberty corners

The SRAM release uses Avalon cells for ordinary digital control gates
(`INV`, `NAND2`, `NAND3`, `NAND4`, `NOR2`).  SRAM-specific row-select and
wordline-buffer cells remain custom RC7 leaves under
`reports/control_leaf_library/`.
