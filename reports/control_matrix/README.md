# RC7 Structural Control Matrix

| Macro | Logical | Physical WL | Gates | Group Sel | Row Select | Eq Gates | Unabutted Gate UB, Not Footprint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `detronyx_12t_2w2r_512x8_rc6_fullctrl` | `512x8` | `64` | `532` | `64` | `256` | `78` | `1.273463mm^2` |
| `detronyx_12t_2w2r_512x32_rc6_fullctrl` | `512x32` | `128` | `788` | `32` | `512` | `78` | `2.200313mm^2` |
| `detronyx_12t_2w2r_1024x8_rc6_fullctrl` | `1024x8` | `128` | `834` | `64` | `512` | `88` | `2.246035mm^2` |
| `detronyx_12t_2w2r_1024x32_rc6_fullctrl` | `1024x32` | `256` | `1378` | `32` | `1024` | `88` | `4.128926mm^2` |

This replaces the RC6 behavioral one-hot/equality contract with a structural
custom-gate CDL/SV matrix built from RC7 DRC/LVS-clean transistor leaves.
The address contract is folded: low address bits select the data group
inside a physical row, and the remaining address bits select physical
wordline rows.

The last column is deliberately pessimistic and must not be read as macro
footprint.  It assumes every gate is placed as an independent un-abutted
leaf.  Real placement uses a row-edge strip; use
`make audit-12t-rc7-row-edge-budget` for footprint numbers.

The next physical step is a row-edge strip generator that abuts the
row-select devices and shares taps/rails instead of instantiating these
standalone gate leaves.
