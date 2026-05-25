# detronyx_12t_2w2r_512x32_rc6_fullctrl RC7 Control Matrix

- Logical rows: `512`
- Physical WL rows: `128`
- Data width: `32`
- Address bits: `9`
- Row address bits: `7`
- Group select bits: `2` (`4` groups)
- Predecode gate instances: `164`
- 4-way group-select gate instances: `32`
- Row-select WL-buffer instances: `512`
- Equality/conflict gate instances: `80`
- Total control gate instances: `788`
- Unabutted standalone gate-bbox upper bound, not a macro footprint: `2.200313mm^2`

Do not use this standalone number as SRAM macro area.  It multiplies
un-abutted gate leaf bounding boxes and intentionally overstates area.
The physical row-select implementation is a row-edge strip sharing
rails/taps/routing with the array.
Use `make audit-12t-rc7-row-edge-budget` for the footprint estimate.
