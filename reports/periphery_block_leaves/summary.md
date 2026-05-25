# 12T Periphery Block Leaves

These are split, extractable transistor-level periphery leaves built from the
same Tim-derived GF180 3.3V MOS primitives as the selected-path slice.
The release defaults use compact DRC/LVS-clean route-channel spacing while
preserving the transistor spacing needed to avoid extractor device merging.

| Leaf | Block | Devices | Size | Area | DRC | LVS | Disconnected Pins |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| `detronyx_12t_write_row_decode7_wl_driver_rc1` | `write_row_decode7_wl_driver` | `38` | `80.960um x 120.715um` | `9773.086um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_read_row_decode7_wl_driver_rc1` | `read_row_decode7_wl_driver` | `38` | `80.960um x 120.715um` | `9773.086um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_write_driver_rc1` | `write_driver` | `26` | `25.950um x 68.880um` | `1787.436um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_precharge_sense_rc1` | `precharge_sense` | `7` | `18.710um x 24.455um` | `457.553um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_write_conflict_rc1` | `write_conflict` | `12` | `29.100um x 53.395um` | `1553.794um^2` | `0` | `match_unique` | `0` |

## Macro Matrix Upper-Bound Estimate

This is a deliberately pessimistic count using un-abutted leaf footprints.
It is not the final area target; the next pass must share predecode, rails,
and taps before full macro DRC/LVS.

| Macro | Naive row decode leaves | Write driver leaves | Read leaves | Naive devices | Shared-predecode devices | Naive leaf area |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `detronyx_12t_2w2r_512x8_macro_shell_rc1` | `1024W + 1024R` | `16` | `16` | `78364` | `33788` | `20.052755mm^2` |
| `detronyx_12t_2w2r_512x32_macro_shell_rc1` | `1024W + 1024R` | `64` | `64` | `79948` | `35372` | `20.160514mm^2` |
| `detronyx_12t_2w2r_1024x8_macro_shell_rc1` | `2048W + 2048R` | `16` | `16` | `156188` | `66556` | `40.068036mm^2` |
| `detronyx_12t_2w2r_1024x32_macro_shell_rc1` | `2048W + 2048R` | `64` | `64` | `157772` | `68140` | `40.175795mm^2` |

## Status

This closes compact standalone block-leaf DRC/LVS, including x32
tile-pitch-compatible write-driver and precharge/sense column leaves.  Full macro signoff remains
open until the column leaves are array-abutted, routed, extracted, and checked
inside the published macro GDS.
