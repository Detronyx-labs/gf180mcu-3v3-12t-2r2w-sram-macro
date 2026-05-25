# RC7 Control Primitive Leaves

| Primitive | Devices | Size | Area | DRC | LVS |
| --- | ---: | ---: | ---: | ---: | --- |
| `detronyx_12t_ctrl_inv_rc7` | `2` | `13.420um x 41.995um` | `563.573um^2` | `0` | `match_unique` |
| `detronyx_12t_ctrl_nand2_rc7` | `4` | `17.840um x 51.135um` | `912.248um^2` | `0` | `match_unique` |
| `detronyx_12t_ctrl_nand3_rc7` | `6` | `22.260um x 60.275um` | `1341.722um^2` | `0` | `match_unique` |
| `detronyx_12t_ctrl_nand4_rc7` | `8` | `26.680um x 69.415um` | `1851.992um^2` | `0` | `match_unique` |
| `detronyx_12t_ctrl_nor2_rc7` | `4` | `17.840um x 51.135um` | `912.248um^2` | `0` | `match_unique` |
| `detronyx_12t_ctrl_row_select3_wlbuf_rc7` | `12` | `33.420um x 83.435um` | `2788.398um^2` | `0` | `match_unique` |
| `detronyx_12t_ctrl_row_select4_wlbuf_rc7` | `14` | `37.840um x 92.575um` | `3503.038um^2` | `0` | `match_unique` |

These leaves are the transistor-level custom-gate basis for the RC7 shared
predecode, address equality, and compact row-select/WL-driver matrix.
They use Tim-derived 3.3V MOS primitives without transistor resizing.
