# 12T 2R2W Leaf Storage Verification

This report is a transistor-level leaf/topology check. It does not claim full macro PEX signoff.

- PDK: GF180MCU ngspice model deck resolved locally by the runner.
- Raw generated decks/logs are written under `verification/results/spice/` and intentionally not committed.
- PASS: `17`
- FAIL: `0`
- INFO: `1`

| Test | Corner | VDD | Status | Detail |
| --- | --- | ---: | --- | --- |
| `write_read_retention` | `typical` | 3.30 | `PASS` | all thresholds met |
| `write_read_retention` | `ff` | 3.30 | `PASS` | all thresholds met |
| `write_read_retention` | `ss` | 3.30 | `PASS` | all thresholds met |
| `dual_read_disturb` | `typical` | 3.30 | `PASS` | all thresholds met |
| `dual_read_disturb` | `ff` | 3.30 | `PASS` | all thresholds met |
| `dual_read_disturb` | `ss` | 3.30 | `PASS` | all thresholds met |
| `disabled_write_hold` | `typical` | 3.30 | `PASS` | all thresholds met |
| `disabled_write_hold` | `ff` | 3.30 | `PASS` | all thresholds met |
| `disabled_write_hold` | `ss` | 3.30 | `PASS` | all thresholds met |
| `same_data_dual_write` | `typical` | 3.30 | `PASS` | all thresholds met |
| `same_data_dual_write` | `ff` | 3.30 | `PASS` | all thresholds met |
| `same_data_dual_write` | `ss` | 3.30 | `PASS` | all thresholds met |
| `write_read_retention` | `typical` | 1.62 | `PASS` | all thresholds met |
| `write_read_retention` | `typical` | 1.80 | `PASS` | all thresholds met |
| `write_read_retention` | `typical` | 2.50 | `PASS` | all thresholds met |
| `write_read_retention` | `typical` | 3.00 | `PASS` | all thresholds met |
| `write_read_retention` | `typical` | 3.60 | `PASS` | all thresholds met |
| `same_cell_conflict_observation` | `typical` | 3.30 | `INFO` | same-cell opposite dual-write is illegal; observed q=6.08e-07 qb=3.3 |

## Interpretation

- `write_read_retention` checks write-1, hold-1, read-1, write-0, hold-0, and read-0 behavior.
- `dual_read_disturb` checks that both independent read ports can discharge their bitlines without flipping the cell.
- `disabled_write_hold` checks that toggling write data lines with wordlines low does not disturb stored data.
- `same_data_dual_write` checks simultaneous same-data writes through both write ports.
- `same_cell_conflict_observation` is intentionally `INFO`: opposite same-cell dual-write is an illegal operation that must be blocked or arbitrated above the bitcell.

