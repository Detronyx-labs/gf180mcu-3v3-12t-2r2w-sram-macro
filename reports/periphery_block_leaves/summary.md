# 12T Periphery Block Leaves RC1

These are split, extractable transistor-level periphery leaves built from the
same Tim-derived GF180 3.3V MOS primitives as the selected-path slice.

| Leaf | Block | Devices | Size | Area | DRC | LVS | Disconnected Pins |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| `detronyx_12t_write_row_decode7_wl_driver_rc1` | `write_row_decode7_wl_driver` | `38` | `85.280um x 189.895um` | `16194.246um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_read_row_decode7_wl_driver_rc1` | `read_row_decode7_wl_driver` | `38` | `85.280um x 189.895um` | `16194.246um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_write_driver_rc1` | `write_driver` | `26` | `58.760um x 135.755um` | `7976.964um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_precharge_sense_rc1` | `precharge_sense` | `7` | `25.280um x 62.075um` | `1569.256um^2` | `0` | `match_unique` | `0` |
| `detronyx_12t_write_conflict_rc1` | `write_conflict` | `12` | `33.420um x 82.435um` | `2754.978um^2` | `0` | `match_unique` | `0` |

## Macro Matrix Upper-Bound Estimate

This is a deliberately pessimistic count using un-abutted leaf footprints.
It is not the final area target; the next pass must share predecode, rails,
and taps before full macro DRC/LVS.

| Macro | Naive row decode leaves | Write driver leaves | Read leaves | Naive devices | Shared-predecode devices | Naive leaf area |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `detronyx_12t_2w2r_512x8_macro_shell_rc1` | `1024W + 1024R` | `16` | `16` | `78364` | `33788` | `33.321309mm^2` |
| `detronyx_12t_2w2r_512x32_macro_shell_rc1` | `1024W + 1024R` | `64` | `64` | `79948` | `35372` | `33.779528mm^2` |
| `detronyx_12t_2w2r_1024x8_macro_shell_rc1` | `2048W + 2048R` | `16` | `16` | `156188` | `66556` | `66.487124mm^2` |
| `detronyx_12t_2w2r_1024x32_macro_shell_rc1` | `2048W + 2048R` | `64` | `64` | `157772` | `68140` | `66.945343mm^2` |

## Status

This closes the block-leaf physical split.  Full macro signoff remains open
until these leaves are tiled, routed to the 12T array, extracted, and checked
with full macro LVS/PEX/antenna/EMIR.
