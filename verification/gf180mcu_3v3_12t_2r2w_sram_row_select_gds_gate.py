#!/usr/bin/env python3
"""Gate the row-select/WL-buffer Avalon stdcell expansion in macro GDS."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


OUT = Path("verification/results/gf180mcu_3v3_12t_2r2w_sram_row_select_gds_gate")
CUSTOM_ROW_SELECT = "detronyx_12t_ctrl_row_select"


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
    parser.add_argument("--placement-manifest", type=Path, default=Path("reports/stdcell_row_select_placement/MANIFEST.json"))
    parser.add_argument("--gds-manifest", type=Path, default=Path("reports/stdcell_row_select_gds_merge/MANIFEST.json"))
    parser.add_argument(
        "--smoke-main-drc",
        type=Path,
        default=Path("reports/stdcell_row_select_gds_merge/gf180mcu_3v3_12t_2r2w_sram_512x8/main_drc.lyrdb"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.package_root
    placement_path = root / args.placement_manifest
    gds_path = root / args.gds_manifest
    smoke_path = root / args.smoke_main_drc
    checks: list[dict[str, object]] = []
    failed = False

    placement = load_json(placement_path) if placement_path.exists() else {"results": []}
    gds = load_json(gds_path) if gds_path.exists() else {"results": [], "status": "missing"}

    add(
        checks,
        "row_select_placement",
        "manifest status",
        "PASS" if placement_path.exists() and placement.get("status") == "PASS" else "FAIL",
        f"status={placement.get('status')}",
        placement_path,
    )
    failed = failed or not placement_path.exists() or placement.get("status") != "PASS"

    add(
        checks,
        "row_select_gds",
        "manifest status",
        "PASS" if gds_path.exists() and gds.get("status") == "PASS" else "FAIL",
        f"status={gds.get('status')}",
        gds_path,
    )
    failed = failed or not gds_path.exists() or gds.get("status") != "PASS"

    placement_by_macro = {item.get("macro"): item for item in placement.get("results", [])}
    for item in gds.get("results", []):
        macro = str(item.get("macro", ""))
        pitem = placement_by_macro.get(macro, {})
        macro_gds = root / str(item.get("gds", ""))
        delta = sum(int(v) for v in item.get("expected_delta_counts", {}).values())
        placed = int(pitem.get("placed_stdcells", -1))
        row_selects = int(pitem.get("row_select_instances", -1))

        add(
            checks,
            macro,
            "GDS merge status",
            "PASS" if item.get("status") == "PASS" else "FAIL",
            f"status={item.get('status')} detail={item.get('detail')}",
            macro_gds,
        )
        failed = failed or item.get("status") != "PASS"

        add(
            checks,
            macro,
            "row-select stdcell count",
            "PASS" if placed == delta and placed == row_selects * 4 and placed > 0 else "FAIL",
            f"row_selects={row_selects} placed={placed} gds_delta={delta}",
            gds_path,
        )
        failed = failed or placed != delta or placed != row_selects * 4 or placed <= 0

        add(
            checks,
            macro,
            "footprint unchanged",
            "PASS" if item.get("footprint_unchanged") is True else "FAIL",
            f"bbox={item.get('bbox_um')}",
            macro_gds,
        )
        failed = failed or item.get("footprint_unchanged") is not True

        required_names = ["gf180mcu_as_sc_mcu7t3v3__inv_2", "gf180mcu_as_sc_mcu7t3v3__nand4_2"]
        missing_names = [name for name in required_names if not macro_gds.exists() or not file_contains(macro_gds, name)]
        add(
            checks,
            macro,
            "row-select stdcell names present",
            "PASS" if not missing_names else "FAIL",
            f"missing={missing_names}",
            macro_gds,
        )
        failed = failed or bool(missing_names)

        expanded_cdl = root / str(pitem.get("macro_expanded_cdl", ""))
        custom_refs = expanded_cdl.exists() and CUSTOM_ROW_SELECT in expanded_cdl.read_text(encoding="utf-8", errors="replace")
        add(
            checks,
            macro,
            "custom row-select leaf removed from full-control CDL",
            "PASS" if expanded_cdl.exists() and not custom_refs else "FAIL",
            f"exists={expanded_cdl.exists()} custom_refs={custom_refs}",
            expanded_cdl,
        )
        failed = failed or not expanded_cdl.exists() or custom_refs

    violations, categories = lyrdb_count(smoke_path)
    add(
        checks,
        "smoke_drc",
        "GF180 main.drc on 512x8 row-select GDS",
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
        "# GF180MCU 12T SRAM Row-Select GDS Gate",
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
    print(f"GF180MCU 12T SRAM row-select GDS gate: {dict(sorted(counts.items()))}")
    print(OUT / "README.md")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
