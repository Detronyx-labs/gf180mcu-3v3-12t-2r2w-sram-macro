#!/usr/bin/env python3
"""Run transistor-level storage checks for the GF180MCU 12T 2R2W leaf."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


CORNERS_3V3 = ("typical", "ff", "ss")
VDD_SWEEP = (1.62, 1.80, 2.50, 3.00, 3.30, 3.60)


@dataclass
class CaseResult:
    name: str
    corner: str
    vdd: float
    status: str
    detail: str
    spice: str
    log: str
    measures: dict[str, float]


def find_gf180_pdk(explicit: str | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("GF180_PDK_ROOT"):
        candidates.append(Path(os.environ["GF180_PDK_ROOT"]))
    pdk_root = os.environ.get("PDK_ROOT")
    pdk_version = os.environ.get("PDK_VERSION")
    if pdk_root and pdk_version:
        candidates.append(Path(pdk_root) / "gf180mcu" / "versions" / pdk_version / "gf180mcuD")
        candidates.append(Path(pdk_root) / "volare" / "gf180mcu" / "versions" / pdk_version / "gf180mcuD")
    if pdk_root:
        candidates.extend(sorted((Path(pdk_root) / "gf180mcu" / "versions").glob("*/gf180mcuD")))
        candidates.extend(sorted((Path(pdk_root) / "volare" / "gf180mcu" / "versions").glob("*/gf180mcuD")))
    candidates.extend(
        sorted((Path.home() / ".volare" / "gf180mcu" / "versions").glob("*/gf180mcuD"))
    )
    for candidate in candidates:
        if (candidate / "libs.tech/ngspice/design.ngspice").exists() and (
            candidate / "libs.tech/ngspice/sm141064.ngspice"
        ).exists():
            return candidate.resolve()
    searched = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(f"GF180MCU PDK ngspice files not found. Searched:\n{searched}")


def vtag(vdd: float) -> str:
    return f"{vdd:.2f}".replace(".", "p")


def deck_header(pdk: Path, bitcell: Path, corner: str, vdd: float) -> str:
    design = pdk / "libs.tech/ngspice/design.ngspice"
    models = pdk / "libs.tech/ngspice/sm141064.ngspice"
    return f"""* Generated 12T 2R2W leaf storage check.
.include {design}
.lib {models} {corner}
.include {bitcell}

.param VDD={vdd:.4g}

VDD vdd 0 {{VDD}}
VSS vss 0 0
"""


def bitcell_instance() -> str:
    return """
XBIT vdd vss wwl0 wbl0 wbr0 wwl1 wbl1 wbr1 rwl0 rbl0 rwl1 rbl1 gf180mcu_3v3_12t_2r2w_bitcell
"""


def write_read_retention_deck(pdk: Path, bitcell: Path, corner: str, vdd: float) -> str:
    return (
        deck_header(pdk, bitcell, corner, vdd)
        + """
VWWL0 wwl0 0 pwl(0n 0 1n 0 1.05n {VDD} 3n {VDD} 3.05n 0 45n 0)
VWBL0 wbl0 0 {VDD}
VWBR0 wbr0 0 0

VWWL1 wwl1 0 pwl(0n 0 21n 0 21.05n {VDD} 23n {VDD} 23.05n 0 45n 0)
VWBL1 wbl1 0 0
VWBR1 wbr1 0 {VDD}

VRWL0 rwl0 0 pwl(0n 0 6n 0 6.05n {VDD} 8n {VDD} 8.05n 0 45n 0)
VRWL1 rwl1 0 pwl(0n 0 30n 0 30.05n {VDD} 32n {VDD} 32.05n 0 45n 0)

CRBL0 rbl0 0 40f ic={VDD}
CRBL1 rbl1 0 40f ic={VDD}
RRBL0 rbl0 vdd 100G
RRBL1 rbl1 vdd 100G
"""
        + bitcell_instance()
        + """
.ic v(XBIT.q)=0 v(XBIT.qb)={VDD} v(rbl0)={VDD} v(rbl1)={VDD}

.tran 2p 45n uic

.measure tran q_after_write1 find v(XBIT.q) at=4n
.measure tran qb_after_write1 find v(XBIT.qb) at=4n
.measure tran q_after_hold1 find v(XBIT.q) at=20n
.measure tran qb_after_hold1 find v(XBIT.qb) at=20n
.measure tran rbl0_after_read1 find v(rbl0) at=8n
.measure tran q_after_write0 find v(XBIT.q) at=25n
.measure tran qb_after_write0 find v(XBIT.qb) at=25n
.measure tran q_after_hold0 find v(XBIT.q) at=42n
.measure tran qb_after_hold0 find v(XBIT.qb) at=42n
.measure tran rbl1_after_read0 find v(rbl1) at=32n

.end
"""
    )


def dual_read_deck(pdk: Path, bitcell: Path, corner: str, vdd: float) -> str:
    return (
        deck_header(pdk, bitcell, corner, vdd)
        + """
VWWL0 wwl0 0 0
VWWL1 wwl1 0 0
VWBL0 wbl0 0 0
VWBR0 wbr0 0 {VDD}
VWBL1 wbl1 0 0
VWBR1 wbr1 0 {VDD}
VRWL0 rwl0 0 pwl(0n 0 1n 0 1.05n {VDD} 5n {VDD} 5.05n 0 8n 0)
VRWL1 rwl1 0 pwl(0n 0 1n 0 1.05n {VDD} 5n {VDD} 5.05n 0 8n 0)
CRBL0 rbl0 0 40f ic={VDD}
CRBL1 rbl1 0 40f ic={VDD}
RRBL0 rbl0 vdd 100G
RRBL1 rbl1 vdd 100G
"""
        + bitcell_instance()
        + """
.ic v(XBIT.q)={VDD} v(XBIT.qb)=0 v(rbl0)={VDD} v(rbl1)={VDD}
.tran 2p 8n uic
.measure tran rbl0_after_dual_read find v(rbl0) at=5n
.measure tran rbl1_after_dual_read find v(rbl1) at=5n
.measure tran q_after_dual_read find v(XBIT.q) at=7n
.measure tran qb_after_dual_read find v(XBIT.qb) at=7n
.end
"""
    )


def disabled_write_deck(pdk: Path, bitcell: Path, corner: str, vdd: float) -> str:
    return (
        deck_header(pdk, bitcell, corner, vdd)
        + """
VWWL0 wwl0 0 0
VWWL1 wwl1 0 0
VWBL0 wbl0 0 pwl(0n {VDD} 1n {VDD} 1.05n 0 6n 0 6.05n {VDD} 12n {VDD})
VWBR0 wbr0 0 pwl(0n 0 1n 0 1.05n {VDD} 6n {VDD} 6.05n 0 12n 0)
VWBL1 wbl1 0 pwl(0n {VDD} 1n {VDD} 1.05n 0 6n 0 6.05n {VDD} 12n {VDD})
VWBR1 wbr1 0 pwl(0n 0 1n 0 1.05n {VDD} 6n {VDD} 6.05n 0 12n 0)
VRWL0 rwl0 0 0
VRWL1 rwl1 0 0
CRBL0 rbl0 0 40f ic={VDD}
CRBL1 rbl1 0 40f ic={VDD}
RRBL0 rbl0 vdd 100G
RRBL1 rbl1 vdd 100G
"""
        + bitcell_instance()
        + """
.ic v(XBIT.q)={VDD} v(XBIT.qb)=0 v(rbl0)={VDD} v(rbl1)={VDD}
.tran 2p 12n uic
.measure tran q_after_disabled_write find v(XBIT.q) at=10n
.measure tran qb_after_disabled_write find v(XBIT.qb) at=10n
.end
"""
    )


def same_data_dual_write_deck(pdk: Path, bitcell: Path, corner: str, vdd: float) -> str:
    return (
        deck_header(pdk, bitcell, corner, vdd)
        + """
VWWL0 wwl0 0 pwl(0n 0 1n 0 1.05n {VDD} 3n {VDD} 3.05n 0 8n 0 8.05n {VDD} 10n {VDD} 10.05n 0 14n 0)
VWWL1 wwl1 0 pwl(0n 0 1n 0 1.05n {VDD} 3n {VDD} 3.05n 0 8n 0 8.05n {VDD} 10n {VDD} 10.05n 0 14n 0)
VWBL0 wbl0 0 pwl(0n {VDD} 3.1n {VDD} 7.9n {VDD} 8n 0 14n 0)
VWBR0 wbr0 0 pwl(0n 0 3.1n 0 7.9n 0 8n {VDD} 14n {VDD})
VWBL1 wbl1 0 pwl(0n {VDD} 3.1n {VDD} 7.9n {VDD} 8n 0 14n 0)
VWBR1 wbr1 0 pwl(0n 0 3.1n 0 7.9n 0 8n {VDD} 14n {VDD})
VRWL0 rwl0 0 0
VRWL1 rwl1 0 0
CRBL0 rbl0 0 40f ic={VDD}
CRBL1 rbl1 0 40f ic={VDD}
RRBL0 rbl0 vdd 100G
RRBL1 rbl1 vdd 100G
"""
        + bitcell_instance()
        + """
.ic v(XBIT.q)=0 v(XBIT.qb)={VDD} v(rbl0)={VDD} v(rbl1)={VDD}
.tran 2p 14n uic
.measure tran q_after_dual_write1 find v(XBIT.q) at=5n
.measure tran qb_after_dual_write1 find v(XBIT.qb) at=5n
.measure tran q_after_dual_write0 find v(XBIT.q) at=12n
.measure tran qb_after_dual_write0 find v(XBIT.qb) at=12n
.end
"""
    )


def conflict_observation_deck(pdk: Path, bitcell: Path, corner: str, vdd: float) -> str:
    return (
        deck_header(pdk, bitcell, corner, vdd)
        + """
VWWL0 wwl0 0 pwl(0n 0 1n 0 1.05n {VDD} 3n {VDD} 3.05n 0 8n 0)
VWWL1 wwl1 0 pwl(0n 0 1n 0 1.05n {VDD} 3n {VDD} 3.05n 0 8n 0)
VWBL0 wbl0 0 {VDD}
VWBR0 wbr0 0 0
VWBL1 wbl1 0 0
VWBR1 wbr1 0 {VDD}
VRWL0 rwl0 0 0
VRWL1 rwl1 0 0
CRBL0 rbl0 0 40f ic={VDD}
CRBL1 rbl1 0 40f ic={VDD}
RRBL0 rbl0 vdd 100G
RRBL1 rbl1 vdd 100G
"""
        + bitcell_instance()
        + """
.ic v(XBIT.q)=0 v(XBIT.qb)={VDD} v(rbl0)={VDD} v(rbl1)={VDD}
.tran 2p 8n uic
.measure tran q_after_conflict find v(XBIT.q) at=5n
.measure tran qb_after_conflict find v(XBIT.qb) at=5n
.end
"""
    )


DECKS = {
    "write_read_retention": write_read_retention_deck,
    "dual_read_disturb": dual_read_deck,
    "disabled_write_hold": disabled_write_deck,
    "same_data_dual_write": same_data_dual_write_deck,
    "same_cell_conflict_observation": conflict_observation_deck,
}


def parse_measures(log_text: str) -> dict[str, float]:
    measures: dict[str, float] = {}
    for line in log_text.splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*([-+0-9.eE]+)", line)
        if match:
            measures[match.group(1).lower()] = float(match.group(2))
    return measures


def is_high(measures: dict[str, float], key: str, vdd: float) -> bool:
    return measures.get(key, -1.0) >= 0.70 * vdd


def is_low(measures: dict[str, float], key: str, vdd: float) -> bool:
    return measures.get(key, vdd + 1.0) <= 0.30 * vdd


def is_read_discharge(measures: dict[str, float], key: str, vdd: float) -> bool:
    return measures.get(key, vdd + 1.0) <= 0.80 * vdd


def is_read_hold_high(measures: dict[str, float], key: str, vdd: float) -> bool:
    return measures.get(key, -1.0) >= 0.90 * vdd


def evaluate(name: str, measures: dict[str, float], vdd: float) -> tuple[str, str]:
    if name == "same_cell_conflict_observation":
        q = measures.get("q_after_conflict")
        qb = measures.get("qb_after_conflict")
        if q is None or qb is None:
            return "FAIL", "missing conflict observation measures"
        return "INFO", f"same-cell opposite dual-write is illegal; observed q={q:.4g} qb={qb:.4g}"
    checks: list[tuple[str, bool]] = []
    if name == "write_read_retention":
        checks = [
            ("write1_q_high", is_high(measures, "q_after_write1", vdd)),
            ("write1_qb_low", is_low(measures, "qb_after_write1", vdd)),
            ("hold1_q_high", is_high(measures, "q_after_hold1", vdd)),
            ("hold1_qb_low", is_low(measures, "qb_after_hold1", vdd)),
            ("read1_rbl0_discharge", is_read_discharge(measures, "rbl0_after_read1", vdd)),
            ("write0_q_low", is_low(measures, "q_after_write0", vdd)),
            ("write0_qb_high", is_high(measures, "qb_after_write0", vdd)),
            ("hold0_q_low", is_low(measures, "q_after_hold0", vdd)),
            ("hold0_qb_high", is_high(measures, "qb_after_hold0", vdd)),
            ("read0_rbl1_high", is_read_hold_high(measures, "rbl1_after_read0", vdd)),
        ]
    elif name == "dual_read_disturb":
        checks = [
            ("rbl0_discharge", is_read_discharge(measures, "rbl0_after_dual_read", vdd)),
            ("rbl1_discharge", is_read_discharge(measures, "rbl1_after_dual_read", vdd)),
            ("q_remains_high", is_high(measures, "q_after_dual_read", vdd)),
            ("qb_remains_low", is_low(measures, "qb_after_dual_read", vdd)),
        ]
    elif name == "disabled_write_hold":
        checks = [
            ("q_remains_high", is_high(measures, "q_after_disabled_write", vdd)),
            ("qb_remains_low", is_low(measures, "qb_after_disabled_write", vdd)),
        ]
    elif name == "same_data_dual_write":
        checks = [
            ("dual_write1_q_high", is_high(measures, "q_after_dual_write1", vdd)),
            ("dual_write1_qb_low", is_low(measures, "qb_after_dual_write1", vdd)),
            ("dual_write0_q_low", is_low(measures, "q_after_dual_write0", vdd)),
            ("dual_write0_qb_high", is_high(measures, "qb_after_dual_write0", vdd)),
        ]
    failed = [label for label, passed in checks if not passed]
    if failed:
        return "FAIL", "failed: " + ", ".join(failed)
    return "PASS", "all thresholds met"


def run_case(name: str, corner: str, vdd: float, pdk: Path, bitcell: Path, out_dir: Path, ngspice: str) -> CaseResult:
    case_dir = out_dir / "spice"
    case_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{name}_{corner}_{vtag(vdd)}v"
    spice = case_dir / f"{stem}.spice"
    log = case_dir / f"{stem}.log"
    spice.write_text(DECKS[name](pdk, bitcell, corner, vdd), encoding="utf-8")
    proc = subprocess.run(
        [ngspice, "-n", "-b", str(spice), "-o", str(log)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.stdout:
        with log.open("a", encoding="utf-8") as handle:
            handle.write("\n* ngspice wrapper output\n")
            handle.write(proc.stdout)
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else proc.stdout
    measures = parse_measures(log_text)
    if proc.returncode != 0:
        return CaseResult(name, corner, vdd, "FAIL", f"ngspice exit {proc.returncode}", str(spice), str(log), measures)
    status, detail = evaluate(name, measures, vdd)
    return CaseResult(name, corner, vdd, status, detail, str(spice), str(log), measures)


def write_reports(results: list[CaseResult], out_dir: Path, pdk: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pass_count = sum(item.status == "PASS" for item in results)
    fail_count = sum(item.status == "FAIL" for item in results)
    info_count = sum(item.status == "INFO" for item in results)
    lines = [
        "# 12T 2R2W Leaf Storage Verification",
        "",
        "This report is a transistor-level leaf/topology check. It does not claim full macro PEX signoff.",
        "",
        "- PDK: GF180MCU ngspice model deck resolved locally by the runner.",
        "- Raw generated decks/logs are written under `verification/results/spice/` and intentionally not committed.",
        f"- PASS: `{pass_count}`",
        f"- FAIL: `{fail_count}`",
        f"- INFO: `{info_count}`",
        "",
        "| Test | Corner | VDD | Status | Detail |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in results:
        lines.append(f"| `{item.name}` | `{item.corner}` | {item.vdd:.2f} | `{item.status}` | {item.detail} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `write_read_retention` checks write-1, hold-1, read-1, write-0, hold-0, and read-0 behavior.",
            "- `dual_read_disturb` checks that both independent read ports can discharge their bitlines without flipping the cell.",
            "- `disabled_write_hold` checks that toggling write data lines with wordlines low does not disturb stored data.",
            "- `same_data_dual_write` checks simultaneous same-data writes through both write ports.",
            "- `same_cell_conflict_observation` is intentionally `INFO`: opposite same-cell dual-write is an illegal operation that must be blocked or arbitrated above the bitcell.",
            "",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    report_results = [
        {
            "name": item.name,
            "corner": item.corner,
            "vdd": item.vdd,
            "status": item.status,
            "detail": item.detail,
            "measures": item.measures,
        }
        for item in results
    ]
    (out_dir / "results.json").write_text(json.dumps(report_results, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gf180-pdk", default=None, help="Path to gf180mcuD PDK root.")
    parser.add_argument("--out-dir", type=Path, default=Path("verification/results"))
    parser.add_argument("--bitcell", type=Path, default=Path("verification/bitcell/gf180mcu_3v3_12t_2r2w_bitcell.spice"))
    parser.add_argument("--ngspice", default="ngspice")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not shutil.which(args.ngspice):
        raise FileNotFoundError(f"ngspice not found: {args.ngspice}")
    pdk = find_gf180_pdk(args.gf180_pdk)
    bitcell = args.bitcell.resolve()
    results: list[CaseResult] = []
    for name in ("write_read_retention", "dual_read_disturb", "disabled_write_hold", "same_data_dual_write"):
        for corner in CORNERS_3V3:
            results.append(run_case(name, corner, 3.30, pdk, bitcell, args.out_dir, args.ngspice))
    for vdd in VDD_SWEEP:
        if vdd == 3.30:
            continue
        results.append(run_case("write_read_retention", "typical", vdd, pdk, bitcell, args.out_dir, args.ngspice))
    results.append(run_case("same_cell_conflict_observation", "typical", 3.30, pdk, bitcell, args.out_dir, args.ngspice))
    write_reports(results, args.out_dir, pdk)
    for item in results:
        print(f"{item.status:4s} {item.name} {item.corner} {item.vdd:.2f}V - {item.detail}")
    return 1 if any(item.status == "FAIL" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
