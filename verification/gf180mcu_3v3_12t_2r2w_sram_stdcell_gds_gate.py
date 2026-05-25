#!/usr/bin/env python3
"""Gate that placed Avalon stdcell control geometry is present in macro GDS."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


OUT = Path("verification/results/gf180mcu_3v3_12t_2r2w_sram_stdcell_gds_gate")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def file_contains(path: Path, text: str) -> bool:
    return text.encode() in path.read_bytes()


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
    parser.add_argument("--manifest", type=Path, default=Path("reports/stdcell_control_gds_merge/MANIFEST.json"))
    parser.add_argument("--placement-manifest", type=Path, default=Path("reports/stdcell_control_placement/MANIFEST.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.package_root
    manifest_path = root / args.manifest
    placement_path = root / args.placement_manifest
    checks: list[dict[str, object]] = []
    failed = False

    if not manifest_path.exists():
        add(checks, "gds_merge", "manifest exists", "FAIL", "missing", manifest_path)
        failed = True
        manifest = {"results": []}
    else:
        manifest = load_json(manifest_path)
        add(
            checks,
            "gds_merge",
            "manifest status",
            "PASS" if manifest.get("status") == "PASS" else "FAIL",
            f"status={manifest.get('status')}",
            manifest_path,
        )
        failed = failed or manifest.get("status") != "PASS"

    placement = load_json(placement_path) if placement_path.exists() else {"results": []}
    expected_by_macro = {item["macro"]: int(item["stdcell_instances_placed"]) for item in placement.get("results", [])}
    all_required_cells = sorted(
        {
            cell
            for item in manifest.get("results", [])
            for cell in item.get("direct_avalon_instance_counts", {}).keys()
        }
    )

    for item in manifest.get("results", []):
        macro = item.get("macro", "")
        gds = root / str(item.get("gds", ""))
        expected = expected_by_macro.get(macro)
        actual = sum(int(v) for v in item.get("direct_avalon_instance_counts", {}).values())
        if item.get("status") != "PASS":
            add(checks, macro, "merge status", "FAIL", f"status={item.get('status')} detail={item.get('detail')}", gds)
            failed = True
        else:
            add(checks, macro, "merge status", "PASS", "PASS", gds)
        add(
            checks,
            macro,
            "footprint unchanged",
            "PASS" if item.get("footprint_unchanged") is True else "FAIL",
            f"bbox={item.get('bbox_um')}",
            gds,
        )
        failed = failed or item.get("footprint_unchanged") is not True
        add(
            checks,
            macro,
            "placed stdcell count",
            "PASS" if expected == actual and actual > 0 else "FAIL",
            f"expected={expected} actual={actual}",
            manifest_path,
        )
        failed = failed or expected != actual or actual <= 0
        missing_names = [cell for cell in all_required_cells if not gds.exists() or not file_contains(gds, cell)]
        add(
            checks,
            macro,
            "stdcell GDS names present",
            "PASS" if not missing_names else "FAIL",
            f"missing={missing_names}",
            gds,
        )
        failed = failed or bool(missing_names)

    counts = Counter(check["status"] for check in checks)
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"failed": failed, "counts": dict(sorted(counts.items())), "checks": checks}
    (OUT / "MANIFEST.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# GF180MCU 12T SRAM Stdcell GDS Gate",
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
    print(f"GF180MCU 12T SRAM stdcell GDS gate: {dict(sorted(counts.items()))}")
    print(OUT / "README.md")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
