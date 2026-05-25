#!/usr/bin/env python3
"""Validate packaged 12T 2R2W SRAM periphery leaf DRC/LVS evidence."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_BLOCKS: dict[str, set[str]] = {
    "write_row_decode7_wl_driver": {"VDD", "VSS", "wdecen", "a[0]", "a[1]", "a[2]", "a[3]", "a[4]", "a[5]", "a[6]", "wwl0"},
    "read_row_decode7_wl_driver": {"VDD", "VSS", "ren", "a[0]", "a[1]", "a[2]", "a[3]", "a[4]", "a[5]", "a[6]", "rwl0"},
    "write_driver": {"VDD", "VSS", "din", "wen", "wbl0", "wbr0"},
    "precharge_sense": {"VDD", "VSS", "pchgb", "ren", "rbl0", "dout"},
    "write_conflict": {"VDD", "VSS", "w0_en", "w1_en", "addr_eq", "write_conflict"},
}

X32_TILE_PITCH_UM = 25.95
PITCH_CONSTRAINED_BLOCKS = {"write_driver", "precharge_sense"}


@dataclass(frozen=True)
class PackageReader:
    root: Path

    def read_text(self, rel_path: str) -> str:
        return (self.root / rel_path).read_text()

    def exists(self, rel_path: str) -> bool:
        return (self.root / rel_path).exists()


def open_package(root: Path) -> PackageReader:
    report_dir = root / "reports" / "periphery_block_leaves"
    if report_dir.exists():
        return PackageReader(root=root)
    raise FileNotFoundError("missing reports/periphery_block_leaves periphery report")


def load_json(reader: PackageReader, rel_path: str) -> Any:
    return json.loads(reader.read_text(rel_path))


def check_manifest(reader: PackageReader) -> list[dict[str, str]]:
    manifest = load_json(reader, "reports/periphery_block_leaves/MANIFEST.json")
    if not isinstance(manifest, list):
        raise ValueError("periphery MANIFEST.json must be a list")

    by_block = {str(item.get("block")): item for item in manifest}
    checks: list[dict[str, str]] = []

    for block, required_pins in EXPECTED_BLOCKS.items():
        item = by_block.get(block)
        if item is None:
            checks.append({"block": block, "check": "present", "status": "FAIL", "detail": "missing block"})
            continue

        cell = str(item.get("cell"))
        drc_ok = item.get("drc_errors") == 0
        lvs_ok = item.get("lvs_result") in {"match", "match_unique"}
        pin_ok = item.get("disconnected_pins") == 0
        checks.append({"block": block, "check": "Magic DRC", "status": "PASS" if drc_ok else "FAIL", "detail": f"drc_errors={item.get('drc_errors')}"})
        checks.append({"block": block, "check": "Netgen LVS", "status": "PASS" if lvs_ok else "FAIL", "detail": f"lvs_result={item.get('lvs_result')}"})
        checks.append({"block": block, "check": "Disconnected pins", "status": "PASS" if pin_ok else "FAIL", "detail": f"disconnected_pins={item.get('disconnected_pins')}"})
        if block in PITCH_CONSTRAINED_BLOCKS:
            width_um = float(item.get("width_um", 0.0))
            pitch_ok = width_um <= X32_TILE_PITCH_UM
            checks.append(
                {
                    "block": block,
                    "check": "x32 tile pitch",
                    "status": "PASS" if pitch_ok else "FAIL",
                    "detail": f"width_um={width_um:.3f}, limit_um={X32_TILE_PITCH_UM:.3f}",
                }
            )

        pins_path = f"reports/periphery_block_leaves/{cell}/abstract/{cell}.pins.json"
        if not reader.exists(pins_path):
            checks.append({"block": block, "check": "Pin contract", "status": "FAIL", "detail": f"missing {pins_path}"})
            continue
        pins_json = load_json(reader, pins_path)
        found = {str(pin.get("name")) for pin in pins_json.get("pins", [])}
        missing = sorted(required_pins - found)
        checks.append({"block": block, "check": "Pin contract", "status": "PASS" if not missing else "FAIL", "detail": "all required pins present" if not missing else f"missing={missing}"})

    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path("."))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reader = open_package(args.package_root)
    checks = check_manifest(reader)

    failed = [check for check in checks if check["status"] != "PASS"]
    for check in checks:
        print(f"{check['status']:4} {check['block']}: {check['check']} ({check['detail']})")
    print(json.dumps({"PASS": len(checks) - len(failed), "FAIL": len(failed)}, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
