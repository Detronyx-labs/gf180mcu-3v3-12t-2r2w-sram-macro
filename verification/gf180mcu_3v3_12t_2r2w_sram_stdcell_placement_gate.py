#!/usr/bin/env python3
"""Gate the packaged Avalon stdcell control placement reports."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("reports/stdcell_control_placement/MANIFEST.json")
DEFAULT_ROW_SELECT_MANIFEST = Path("reports/stdcell_row_select_placement/MANIFEST.json")
DEFAULT_OUT = Path("verification/results/gf180mcu_3v3_12t_2r2w_sram_stdcell_placement_gate")


@dataclass
class Check:
    scope: str
    check: str
    status: str
    evidence: str
    detail: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add(checks: list[Check], scope: str, check: str, status: str, evidence: Path | str, detail: str) -> None:
    checks.append(Check(scope, check, status, str(evidence), detail))


def file_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def run(manifest_path: Path, row_select_manifest_path: Path, out_dir: Path, require_row_select: bool) -> int:
    checks: list[Check] = []
    if not file_ok(manifest_path):
        add(checks, "placement", "manifest exists", "FAIL", manifest_path, "missing placement manifest")
        manifest: dict[str, Any] = {"results": []}
    else:
        manifest = load_json(manifest_path)
        add(checks, "placement", "manifest exists", "PASS", manifest_path, "present")

    row_select_manifest = load_json(row_select_manifest_path) if file_ok(row_select_manifest_path) else {"results": []}
    row_select_by_macro = {str(item.get("macro")): item for item in row_select_manifest.get("results", [])}

    for item in manifest.get("results", []):
        macro = str(item["macro"])
        status = str(item.get("status"))
        add(
            checks,
            macro,
            "placement status",
            "PASS" if status == "PASS" else "FAIL",
            item.get("def", manifest_path),
            f"status={status}, errors={item.get('errors', [])[:3]}",
        )
        add(
            checks,
            macro,
            "footprint unchanged",
            "PASS" if item.get("footprint_unchanged") is True else "FAIL",
            manifest_path,
            f"width={item.get('macro_width_um')} height={item.get('macro_height_um')}",
        )
        expected = int(item.get("stdcell_instances_expected", -1))
        placed = int(item.get("stdcell_instances_placed", -2))
        add(
            checks,
            macro,
            "stdcell placement count",
            "PASS" if expected == placed and placed > 0 else "FAIL",
            item.get("placement_csv", manifest_path),
            f"expected={expected}, placed={placed}",
        )
        def_path = Path(str(item.get("def", "")))
        csv_path = Path(str(item.get("placement_csv", "")))
        add(checks, macro, "DEF exists", "PASS" if file_ok(def_path) else "FAIL", def_path, "non-empty DEF")
        add(checks, macro, "CSV exists", "PASS" if file_ok(csv_path) else "FAIL", csv_path, "non-empty placement CSV")

        max_util = float(item.get("max_row_utilization", 2.0))
        overall = float(item.get("overall_utilization", 2.0))
        add(
            checks,
            macro,
            "row utilization",
            "PASS" if 0.0 < max_util <= 1.0 and 0.0 < overall <= 1.0 else "FAIL",
            item.get("def", manifest_path),
            f"overall={overall}, max_row={max_util}",
        )

        width = float(item.get("macro_width_um", 0.0))
        height = float(item.get("macro_height_um", 0.0))
        row_errors: list[str] = []
        for row in item.get("rows", []):
            x = float(row.get("x_um", 0.0))
            y = float(row.get("y_um", 0.0))
            w = float(row.get("width_um", 0.0))
            h = float(row.get("height_um", 0.0))
            used = float(row.get("used_width_um", 0.0))
            if x < -1e-9 or y < -1e-9 or x + w > width + 1e-9 or y + h > height + 1e-9:
                row_errors.append(f"{row.get('name')}: outside macro")
            if used > w + 1e-9:
                row_errors.append(f"{row.get('name')}: used_width>{w}")
        add(
            checks,
            macro,
            "row geometry inside macro",
            "PASS" if not row_errors else "FAIL",
            item.get("def", manifest_path),
            f"errors={row_errors[:3]}",
        )

        deferred = int(item.get("deferred_row_select_instances", 0))
        row_select_item = row_select_by_macro.get(macro, {})
        row_select_closed = (
            row_select_item.get("status") == "PASS"
            and row_select_item.get("footprint_unchanged") is True
            and int(row_select_item.get("row_select_instances", -1)) == deferred
            and int(row_select_item.get("placed_stdcells", -2)) == deferred * 4
        )
        if row_select_closed:
            status = "PASS"
        elif require_row_select:
            status = "FAIL"
        else:
            status = "OPEN" if deferred > 0 else "PASS"
        add(
            checks,
            macro,
            "row-select/WL-buffer placement",
            status,
            row_select_manifest_path if row_select_closed else manifest_path,
            f"deferred_row_select_instances={deferred}, row_select_closed={row_select_closed}",
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    payload = {"counts": counts, "checks": [asdict(check) for check in checks]}
    (out_dir / "MANIFEST.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# GF180MCU 12T SRAM Stdcell Placement Gate",
        "",
        f"- Counts: `{counts}`",
        "",
        "| Scope | Check | Status | Detail | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(f"| `{check.scope}` | `{check.check}` | `{check.status}` | {check.detail} | `{check.evidence}` |")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"GF180MCU 12T SRAM stdcell placement gate: {counts}")
    print(out_dir / "README.md")
    return 1 if counts.get("FAIL", 0) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--row-select-manifest", type=Path, default=DEFAULT_ROW_SELECT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--require-row-select-placement", action="store_true")
    args = parser.parse_args()
    return run(args.manifest, args.row_select_manifest, args.out_dir, args.require_row_select_placement)


if __name__ == "__main__":
    raise SystemExit(main())
