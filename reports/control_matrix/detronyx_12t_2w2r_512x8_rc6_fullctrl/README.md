# detronyx_12t_2w2r_512x8_rc6_fullctrl RC7 Control Matrix

- Logical rows: `512`
- Physical WL rows: `64`
- Data width: `8`
- Address bits: `9`
- Row address bits: `6`
- Group select bits: `3` (`8` groups)
- Predecode gate instances: `132`
- 4-way group-select gate instances: `64`
- Row-select WL-buffer instances: `256`
- Equality/conflict gate instances: `80`
- Total control gate instances: `532`
- Unabutted standalone gate-bbox upper bound, not a macro footprint: `1.273463mm^2`

Do not use this standalone number as SRAM macro area.  It multiplies
un-abutted gate leaf bounding boxes and intentionally overstates area.
The physical row-select implementation is a row-edge strip sharing
rails/taps/routing with the array.
Use `make audit-12t-rc7-row-edge-budget` for the footprint estimate.
