#!/usr/bin/env python3
"""Gate top-level stdcell control/predecode signal routing in macro GDS."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


OUT = Path("verification/results/gf180mcu_3v3_12t_2r2w_sram_stdcell_control_routing_gate")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def file_contains(path: Path, text: str) -> bool:
    return text.encode() in path.read_bytes()


def lyrdb_count(path: Path) -> tuple[int | None, list[str]]:
    if not path.exists():
        return None, []
    root = ET.parse(path).getroot()
    items = next((child for child in root if child.tag == "items"), None)
    if items is None:
        return None, []
    categories: list[str] = []
    for item in list(items):
        for sub in list(item):
            if sub.tag == "category":
                categories.append(sub.text or "")
                break
    return len(list(items)), sorted(set(categories))[:12]


def add(checks: list[dict[str, object]], scope: str, check: str, status: str, detail: str, evidence: Path | str) -> None:
    checks.append(
        {
            "scope": scope,
            "check": check,
            "status": status,
            "detail": detail,
            "evidence": str(evidence),
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path("."))
    parser.add_argument(
        "--routing-manifest",
        type=Path,
        default=Path("reports/stdcell_control_signal_routing/MANIFEST.json"),
    )
    parser.add_argument(
        "--smoke-main-drc",
        type=Path,
        default=Path("reports/stdcell_control_signal_routing/gf180mcu_3v3_12t_2r2w_sram_512x8/main_drc.lyrdb"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.package_root
    routing_path = root / args.routing_manifest
    smoke_path = root / args.smoke_main_drc
    checks: list[dict[str, object]] = []
    failed = False

    routing = load_json(routing_path) if routing_path.exists() else {"results": [], "status": "missing"}
    add(
        checks,
        "control_signal_routing",
        "manifest status",
        "PASS" if routing_path.exists() and routing.get("status") == "PASS" else "FAIL",
        f"status={routing.get('status')}",
        routing_path,
    )
    failed = failed or not routing_path.exists() or routing.get("status") != "PASS"

    for item in routing.get("results", []):
        macro = str(item.get("macro", ""))
        macro_gds = root / str(item.get("gds", ""))
        route_cell = str(item.get("route_cell", ""))
        routed_nets = int(item.get("routed_nets", 0))
        routed_endpoints = int(item.get("routed_endpoints", 0))
        row_select_nets = int(item.get("row_select_input_nets", 0))
        macro_pin_nets = int(item.get("macro_pin_nets", 0))

        add(
            checks,
            macro,
            "routing status",
            "PASS" if item.get("status") == "PASS" else "FAIL",
            f"status={item.get('status')} detail={item.get('detail')}",
            routing_path,
        )
        failed = failed or item.get("status") != "PASS"

        add(
            checks,
            macro,
            "route cell present in GDS",
            "PASS" if macro_gds.exists() and route_cell and file_contains(macro_gds, route_cell) else "FAIL",
            f"route_cell={route_cell} gds_exists={macro_gds.exists()}",
            macro_gds,
        )
        failed = failed or not macro_gds.exists() or not route_cell or not file_contains(macro_gds, route_cell)

        add(
            checks,
            macro,
            "routed net/endpoints coverage",
            "PASS" if routed_nets > 0 and routed_endpoints > routed_nets and row_select_nets > 0 and macro_pin_nets > 0 else "FAIL",
            f"routed_nets={routed_nets}, routed_endpoints={routed_endpoints}, row_select_input_nets={row_select_nets}, macro_pin_nets={macro_pin_nets}",
            routing_path,
        )
        failed = failed or not (routed_nets > 0 and routed_endpoints > routed_nets and row_select_nets > 0 and macro_pin_nets > 0)

        add(
            checks,
            macro,
            "footprint unchanged",
            "PASS" if item.get("footprint_unchanged") is True else "FAIL",
            f"bbox_after={item.get('bbox_after_um')}",
            macro_gds,
        )
        failed = failed or item.get("footprint_unchanged") is not True

    violations, categories = lyrdb_count(smoke_path)
    add(
        checks,
        "smoke_drc",
        "GF180 main.drc on 512x8 routed control GDS",
        "PASS" if violations == 0 else "FAIL",
        f"violations={violations} categories={categories}",
        smoke_path,
    )
    failed = failed or violations != 0

    counts = Counter(check["status"] for check in checks)
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"failed": failed, "counts": dict(sorted(counts.items())), "checks": checks}
    (OUT / "MANIFEST.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# GF180MCU 12T SRAM Stdcell Control Routing Gate",
        "",
        f"- Counts: `{dict(sorted(counts.items()))}`",
        "",
        "| Scope | Check | Status | Detail | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(
            f"| `{check['scope']}` | `{check['check']}` | `{check['status']}` | {check['detail']} | `{check['evidence']}` |"
        )
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"GF180MCU 12T SRAM stdcell control routing gate: {dict(sorted(counts.items()))}")
    print(OUT / "README.md")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
