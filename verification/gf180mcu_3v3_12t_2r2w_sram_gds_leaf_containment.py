#!/usr/bin/env python3
"""Audit whether packaged periphery leaf GDS cells are present in macro GDS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


LEAF_CELLS = [
    "detronyx_12t_write_row_decode7_wl_driver_rc1",
    "detronyx_12t_read_row_decode7_wl_driver_rc1",
    "detronyx_12t_write_driver_rc1",
    "detronyx_12t_precharge_sense_rc1",
    "detronyx_12t_write_conflict_rc1",
]


def file_contains(path: Path, text: str) -> bool:
    return text.encode() in path.read_bytes()


def macro_gds_paths(root: Path) -> list[Path]:
    return sorted((root / "macros").glob("*/layout/*.gds"))


def leaf_gds_path(root: Path, cell: str) -> Path:
    return root / "reports" / "periphery_block_leaves" / cell / "layout" / f"{cell}.gds"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path("."))
    parser.add_argument(
        "--require-macro-containment",
        action="store_true",
        help="Fail if the macro GDS files do not instantiate/include all periphery leaf cell names.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.package_root
    checks: list[dict[str, object]] = []
    failed = False

    for cell in LEAF_CELLS:
        gds = leaf_gds_path(root, cell)
        exists = gds.exists()
        contains_self = exists and file_contains(gds, cell)
        status = "PASS" if contains_self else "FAIL"
        failed = failed or status == "FAIL"
        checks.append(
            {
                "scope": "leaf_gds",
                "cell": cell,
                "path": str(gds),
                "status": status,
                "detail": "standalone leaf GDS contains its own top cell" if contains_self else "missing or cell name not found",
            }
        )

    macro_paths = macro_gds_paths(root)
    for macro_gds in macro_paths:
        present = [cell for cell in LEAF_CELLS if file_contains(macro_gds, cell)]
        missing = [cell for cell in LEAF_CELLS if cell not in present]
        integrated = not missing
        if args.require_macro_containment and not integrated:
            status = "FAIL"
            failed = True
        elif present and missing:
            status = "WARN"
        elif integrated:
            status = "PASS"
        else:
            status = "INFO"
        checks.append(
            {
                "scope": "macro_gds",
                "path": str(macro_gds),
                "status": status,
                "present_leaf_cells": present,
                "missing_leaf_cells": missing,
                "detail": "integrated" if integrated else "standalone leaf-level closure only; macro GDS does not contain these periphery leaves",
            }
        )

    for check in checks:
        if check["scope"] == "leaf_gds":
            print(f"{check['status']:4} leaf {check['cell']}: {check['detail']}")
        else:
            print(f"{check['status']:4} macro {check['path']}: {check['detail']}")
    print(json.dumps({"failed": failed, "checks": checks}, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
