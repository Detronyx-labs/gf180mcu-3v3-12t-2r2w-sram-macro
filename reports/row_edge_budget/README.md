# RC7 Folded Row-Edge Budget

| Macro | Physical WL / groups | Shell area | Est. with RC7 LVS strip | Delta | Allowed strip / port | RC7 LVS leaf | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `detronyx_12t_2w2r_512x8_rc6_fullctrl` | `64` / `8` | `0.158937mm^2` | `0.199629mm^2` | `+0.040692mm^2 / 25.6%` | `38.112um` | `37.840um` | `release_lvs_leaf_fits_budget` |
| `detronyx_12t_2w2r_512x32_rc6_fullctrl` | `128` / `4` | `0.546718mm^2` | `0.620487mm^2` | `+0.073769mm^2 / 13.5%` | `29.553um` | `37.840um` | `needs_abutted_strip_lvs_dense_width` |
| `detronyx_12t_2w2r_1024x8_rc6_fullctrl` | `128` / `8` | `0.288130mm^2` | `0.361900mm^2` | `+0.073769mm^2 / 25.6%` | `33.027um` | `37.840um` | `needs_abutted_strip_lvs_dense_width` |
| `detronyx_12t_2w2r_1024x32_rc6_fullctrl` | `256` / `4` | `1.036999mm^2` | `1.176922mm^2` | `+0.139923mm^2 / 13.5%` | `42.762um` | `37.840um` | `release_lvs_leaf_fits_budget` |

Dense lower-bound probe:

| Macro | Dense DRC-only strip | Dense estimated area |
| --- | ---: | ---: |
| `detronyx_12t_2w2r_512x8_rc6_fullctrl` | `29.405um` | `0.188126mm^2` |
| `detronyx_12t_2w2r_512x32_rc6_fullctrl` | `29.405um` | `0.599635mm^2` |
| `detronyx_12t_2w2r_1024x8_rc6_fullctrl` | `29.405um` | `0.341047mm^2` |
| `detronyx_12t_2w2r_1024x32_rc6_fullctrl` | `29.405um` | `1.137370mm^2` |

Interpretation:

- `RC7 LVS leaf` is the current DRC/LVS-clean standalone row_select4 WL-buffer leaf width.
- `Dense DRC-only` is a lower-bound experiment; it is DRC-clean but not LVS-clean and is not a release artifact.
- The final physical answer must be an abutted row-edge strip sharing wells, taps, rails, and local routes.
- Timothy's `xdec64` row pitch is recorded in `MANIFEST.json`; it fits the RC6 row pitch for these folded shells.
