# detronyx_12t_2w2r_1024x32_rc6_fullctrl RC7 Control Matrix

- Logical rows: `1024`
- Physical WL rows: `256`
- Data width: `32`
- Address bits: `10`
- Row address bits: `8`
- Group select bits: `2` (`4` groups)
- Predecode gate instances: `232`
- 4-way group-select gate instances: `32`
- Row-select WL-buffer instances: `1024`
- Equality/conflict gate instances: `90`
- Total control gate instances: `1378`
- Unabutted standalone gate-bbox upper bound, not a macro footprint: `4.128926mm^2`

Do not use this standalone number as SRAM macro area.  It multiplies
un-abutted gate leaf bounding boxes and intentionally overstates area.
The physical row-select implementation is a row-edge strip sharing
rails/taps/routing with the array.
Use `make audit-12t-rc7-row-edge-budget` for the footprint estimate.
