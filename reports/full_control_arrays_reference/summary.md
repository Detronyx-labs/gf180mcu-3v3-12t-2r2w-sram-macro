# RC4B Timothy-Style Array Run

| Macro | Logical Shape | Physical Tile Grid | Size | Area | Budget | Area/bit | DRC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gf180mcu_3v3_12t_2r2w_sram_512x8_source_full_control` | `512x8` | `16x16` | `466.200um x 340.920um` | `0.158937mm^2` | `pass_target` | `38.803um^2/bit` | `0` |
| `gf180mcu_3v3_12t_2r2w_sram_512x32_source_full_control` | `512x32` | `32x32` | `884.600um x 618.040um` | `0.546718mm^2` | `pass_target` | `33.369um^2/bit` | `0` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x8_source_full_control` | `1024x8` | `32x16` | `466.200um x 618.040um` | `0.288130mm^2` | `pass_target` | `35.172um^2/bit` | `0` |
| `gf180mcu_3v3_12t_2r2w_sram_1024x32_source_full_control` | `1024x32` | `64x32` | `884.600um x 1172.280um` | `1.036999mm^2` | `pass_target` | `31.647um^2/bit` | `0` |

Status: route-contract array shells with explicit control footprint bands.
When generated from `power_strapped_control` tiles, lower-metal tile rails are tied to macro M4/M5 VDD/VSS straps.
Signal periphery, extracted full-macro PEX, and EM/IR remain separate signoff steps.
