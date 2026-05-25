#!/usr/bin/env python3
"""Plan pitch-aware column periphery placement for the GF180MCU 12T SRAM macros.

The generated plan is consumed by the KLayout merge script.  It treats the
current array/control top as the core, but first consumes the already-reserved
top/bottom control bands before growing the wrapper.  Port instances are
row-packed by bit-pitch phase; the macro pinout already separates r0/r1 and
w0/w1 in X, so separate Y rows per port are unnecessary and waste area.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FINAL_MANIFEST = ROOT / "reports" / "final_physical" / "MANIFEST.json"
PERIPHERY_MANIFEST = ROOT / "reports" / "periphery_block_leaves" / "MANIFEST.json"
OUT = ROOT / "reports" / "column_periphery_integration"
UNITS_PER_UM = 200.0
EDGE_MARGIN_UM = 2.0
ROW_GAP_UM = 2.0
READ_PIN_Y_UM = 2.0
PIN_SIZE_UM = 0.64
POWER_RAIL_UM = 1.20
MIN_ROW_GAP_UM = 0.005


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_pins(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise TypeError(f"{path} must contain a pin list")
    return data


def leaf_pin_center_um(pin: dict[str, Any]) -> tuple[float, float]:
    if "rect_um" in pin:
        rect = pin["rect_um"]
        return ((float(rect[0]) + float(rect[2])) / 2.0, (float(rect[1]) + float(rect[3])) / 2.0)
    return (
        (float(pin["xlo"]) + float(pin["xhi"])) / (2.0 * UNITS_PER_UM),
        (float(pin["ylo"]) + float(pin["yhi"])) / (2.0 * UNITS_PER_UM),
    )


def leaf_pin_size_um(pin: dict[str, Any]) -> tuple[float, float]:
    if "rect_um" in pin:
        rect = pin["rect_um"]
        return (float(rect[2]) - float(rect[0]), float(rect[3]) - float(rect[1]))
    return (
        (float(pin["xhi"]) - float(pin["xlo"])) / UNITS_PER_UM,
        (float(pin["yhi"]) - float(pin["ylo"])) / UNITS_PER_UM,
    )


def macro_pin_center(pin: dict[str, Any]) -> tuple[float, float]:
    rect = pin["rect_um"]
    return ((float(rect[0]) + float(rect[2])) / 2.0, (float(rect[1]) + float(rect[3])) / 2.0)


def macro_pin_rect_at(name: str, template: dict[str, Any], x: float, y: float) -> dict[str, Any]:
    half = PIN_SIZE_UM / 2.0
    return {
        "direction": template["direction"],
        "layer": template["layer"],
        "name": name,
        "rect_um": [round(x - half, 6), round(y - half, 6), round(x + half, 6), round(y + half, 6)],
        "use": template["use"],
    }


def shifted_pin(pin: dict[str, Any], dy: float) -> dict[str, Any]:
    rect = pin["rect_um"]
    return {
        **pin,
        "rect_um": [
            round(float(rect[0]), 6),
            round(float(rect[1]) + dy, 6),
            round(float(rect[2]), 6),
            round(float(rect[3]) + dy, 6),
        ],
    }


def write_lef(path: Path, macro: str, width: float, height: float, pins: list[dict[str, Any]]) -> None:
    lines = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        f"MACRO {macro}",
        "  CLASS BLOCK ;",
        f"  FOREIGN {macro} 0.000 0.000 ;",
        "  ORIGIN 0.000 0.000 ;",
        f"  SIZE {width:.6f} BY {height:.6f} ;",
        "  SYMMETRY X Y ;",
    ]
    for pin in pins:
        rect = pin["rect_um"]
        lines.extend(
            [
                f"  PIN {pin['name']}",
                f"    DIRECTION {pin['direction']} ;",
                f"    USE {pin['use']} ;",
                "    PORT",
                f"      LAYER {pin['layer']} ;",
                f"        RECT {rect[0]:.6f} {rect[1]:.6f} {rect[2]:.6f} {rect[3]:.6f} ;",
                "    END",
                f"  END {pin['name']}",
            ]
        )
    lines.extend([f"END {macro}", "END LIBRARY", ""])
    path.write_text("\n".join(lines))


def bit_index(name: str, prefix: str) -> int | None:
    match = re.fullmatch(re.escape(prefix) + r"\[(\d+)\]", name)
    return int(match.group(1)) if match else None


def pin_by_name(pins: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(pin["name"]): pin for pin in pins}


def phase_count(data_pins: list[dict[str, Any]], leaf_width: float) -> int:
    if len(data_pins) < 2:
        return 1
    centers = sorted(macro_pin_center(pin)[0] for pin in data_pins)
    pitch = min(centers[idx + 1] - centers[idx] for idx in range(len(centers) - 1))
    return max(1, math.ceil((leaf_width + 0.10) / pitch))


def assert_row_packing(rows: list[dict[str, Any]], macro: str, block: str) -> None:
    by_row: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if row["block"] == block:
            by_row.setdefault(int(row["row_index"]), []).append(row)
    for row_index, members in by_row.items():
        members = sorted(members, key=lambda item: float(item["x_um"]))
        for left, right in zip(members, members[1:]):
            left_hi = float(left["x_um"]) + float(left["width_um"])
            right_lo = float(right["x_um"])
            if left_hi + MIN_ROW_GAP_UM > right_lo:
                raise RuntimeError(
                    f"{macro}: compact {block} row {row_index} overlaps "
                    f"{left['name']} [{left['x_um']}, {left_hi:.6f}] and "
                    f"{right['name']} [{right_lo:.6f}, {float(right['x_um']) + float(right['width_um']):.6f}]"
                )


def plan() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    final_items = load_json(FINAL_MANIFEST)
    periphery_items = load_json(PERIPHERY_MANIFEST)
    previous_by_macro: dict[str, dict[str, Any]] = {}
    previous_manifest = OUT / "MANIFEST.json"
    if previous_manifest.is_file():
        previous = load_json(previous_manifest)
        previous_by_macro = {item["macro"]: item for item in previous.get("results", [])}
    by_block = {item["block"]: item for item in periphery_items}
    write_leaf = by_block["write_driver"]
    read_leaf = by_block["precharge_sense"]
    write_pins = pin_by_name(load_json(ROOT / write_leaf["pins_json"])["pins"])
    read_pins = pin_by_name(load_json(ROOT / read_leaf["pins_json"])["pins"])
    write_din_x, _ = leaf_pin_center_um(write_pins["din"])
    read_dout_x, _ = leaf_pin_center_um(read_pins["dout"])

    results: list[dict[str, Any]] = []
    all_instances = 0
    all_routes = 0

    for item in sorted(final_items, key=lambda row: (row["rows"], row["data_width"])):
        macro = item["macro"]
        macro_dir = ROOT / "macros" / macro
        abstract_dir = macro_dir / "abstract"
        pins_path = abstract_dir / f"{macro}.pins.json"
        lef_path = abstract_dir / f"{macro}.lef"
        pins = load_pins(pins_path)
        previous = previous_by_macro.get(macro)
        if previous:
            current_top = max(float(pin["rect_um"][3]) for pin in pins if pin["name"] == "VDD")
            if current_top > float(item["height_um"]) + 1.0:
                pins = [
                    pin
                    if pin["name"] in {"VDD", "VSS"} or bit_index(pin["name"], "r0_data") is not None or bit_index(pin["name"], "r1_data") is not None
                    else shifted_pin(pin, -float(previous["core_y_offset_um"]))
                    for pin in pins
                ]
        pins_by_name = pin_by_name(pins)
        data_width = int(item["data_width"])
        old_h = float(item["height_um"])
        control_bottom = float(item.get("control_bottom_um", 0.0))
        control_top = float(item.get("control_top_um", 0.0))
        width = float(item["width_um"])
        w0_pins = [pins_by_name[f"w0_data[{idx}]"] for idx in range(data_width)]
        read_phases = phase_count([pins_by_name[f"r0_data[{idx}]"] for idx in range(data_width)], float(read_leaf["width_um"]))
        write_phases = phase_count(w0_pins, float(write_leaf["width_um"]))
        read_rows = read_phases
        write_rows = write_phases
        bottom_shelf = 2 * EDGE_MARGIN_UM + read_rows * float(read_leaf["height_um"]) + max(0, read_rows - 1) * ROW_GAP_UM
        top_shelf = 2 * EDGE_MARGIN_UM + write_rows * float(write_leaf["height_um"]) + max(0, write_rows - 1) * ROW_GAP_UM
        bottom_extra = max(0.0, bottom_shelf - control_bottom)
        top_extra = max(0.0, top_shelf - control_top)
        core_y = round(bottom_extra, 6)
        new_h = round(bottom_extra + old_h + top_extra, 6)

        out_dir = OUT / macro
        out_dir.mkdir(parents=True, exist_ok=True)
        placement_csv = out_dir / f"{macro}.column_periphery_placement.csv"
        routes_csv = out_dir / f"{macro}.column_periphery_routes.csv"
        placement_rows: list[dict[str, Any]] = []
        routes: list[dict[str, Any]] = []

        def add_instance(
            *,
            port: str,
            bit: int,
            phase: int,
            row_index: int,
            leaf: dict[str, Any],
            align_pin_x: float,
            y: float,
            kind: str,
        ) -> dict[str, Any]:
            name = f"X{port}_bit{bit:02d}_{kind}"
            x = round(align_pin_x, 6)
            row = {
                "name": name,
                "cell": leaf["cell"],
                "block": leaf["block"],
                "port": port,
                "bit": bit,
                "phase": phase,
                "row_index": row_index,
                "x_um": x,
                "y_um": round(y, 6),
                "width_um": leaf["width_um"],
                "height_um": leaf["height_um"],
                "orient": "N",
                "gds": leaf["gds"],
            }
            placement_rows.append(row)
            return row

        # Read periphery at the bottom.  r0/r1 share each phase row because
        # their data pins occupy non-overlapping X windows.
        for port in ("r0", "r1"):
            for phase in range(read_phases):
                read_row_index = phase
                row_y = EDGE_MARGIN_UM + read_row_index * (float(read_leaf["height_um"]) + ROW_GAP_UM)
                for bit in range(phase, data_width, read_phases):
                    pin = pins_by_name[f"{port}_data[{bit}]"]
                    x_center, _ = macro_pin_center(pin)
                    inst = add_instance(
                        port=port,
                        bit=bit,
                        phase=phase,
                        row_index=read_row_index,
                        leaf=read_leaf,
                        align_pin_x=x_center - read_dout_x,
                        y=row_y,
                        kind="precharge_sense",
                    )
                    routes.append({"kind": "read_dout", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_data[{bit}]"})
                    routes.append({"kind": "read_rbl_landing", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_data[{bit}]"})
                    routes.append({"kind": "read_enable", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_en"})
                    routes.append({"kind": "read_precharge_landing", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": "clk"})

        # Write periphery at the top.  First consume the existing top control
        # band in the core, then grow upward only for the remaining rows.
        write_base_y = core_y + old_h - control_top + EDGE_MARGIN_UM
        for port in ("w0", "w1"):
            for phase in range(write_phases):
                write_row_index = phase
                row_y = write_base_y + write_row_index * (float(write_leaf["height_um"]) + ROW_GAP_UM)
                for bit in range(phase, data_width, write_phases):
                    pin = pins_by_name[f"{port}_data[{bit}]"]
                    x_center, _ = macro_pin_center(pin)
                    inst = add_instance(
                        port=port,
                        bit=bit,
                        phase=phase,
                        row_index=write_row_index,
                        leaf=write_leaf,
                        align_pin_x=x_center - write_din_x,
                        y=row_y,
                        kind="write_driver",
                    )
                    routes.append({"kind": "write_din", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_data[{bit}]"})
                    routes.append({"kind": "write_enable", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_en"})
                    routes.append({"kind": "write_wbl_landing", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_data[{bit}]"})
                    routes.append({"kind": "write_wbr_landing", "inst": inst["name"], "port": port, "bit": bit, "macro_pin": f"{port}_data[{bit}]"})

        assert_row_packing(placement_rows, macro, "precharge_sense")
        assert_row_packing(placement_rows, macro, "write_driver")

        with placement_csv.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(placement_rows[0].keys()))
            writer.writeheader()
            writer.writerows(placement_rows)

        with routes_csv.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(routes[0].keys()))
            writer.writeheader()
            writer.writerows(routes)

        right_edge = max(width, max(float(row["x_um"]) + float(row["width_um"]) for row in placement_rows))
        new_w = round(right_edge, 6)

        updated_pins: list[dict[str, Any]] = []
        for pin in pins:
            name = pin["name"]
            if name == "VSS":
                updated_pins.append({**pin, "rect_um": [0.0, 0.0, new_w, POWER_RAIL_UM]})
            elif name == "VDD":
                updated_pins.append({**pin, "rect_um": [0.0, round(new_h - POWER_RAIL_UM, 6), new_w, round(new_h, 6)]})
            elif bit_index(name, "r0_data") is not None or bit_index(name, "r1_data") is not None:
                x, _ = macro_pin_center(pin)
                updated_pins.append(macro_pin_rect_at(name, pin, x, READ_PIN_Y_UM))
            else:
                updated_pins.append(shifted_pin(pin, core_y))

        pins_path.write_text(json.dumps(updated_pins, indent=2) + "\n")
        write_lef(lef_path, macro, new_w, new_h, updated_pins)

        # Keep the report-side abstract copy aligned with the package abstract.
        report_abstract = ROOT / "reports" / "final_physical" / macro / "abstract"
        if report_abstract.is_dir():
            (report_abstract / f"{macro}.pins.json").write_text(json.dumps(updated_pins, indent=2) + "\n")
            write_lef(report_abstract / f"{macro}.lef", macro, new_w, new_h, updated_pins)

        counts = Counter(row["block"] for row in placement_rows)
        result = {
            "macro": macro,
            "status": "PASS",
            "gds": item["gds"],
            "lef": rel(lef_path),
            "pins_json": rel(pins_path),
            "placement_csv": rel(placement_csv),
            "routes_csv": rel(routes_csv),
            "old_width_um": width,
            "old_height_um": old_h,
            "row_edge_total_width_um": round(float(item.get("row_edge_total_width_um", 0.0)), 6),
            "new_width_um": new_w,
            "new_height_um": new_h,
            "core_y_offset_um": core_y,
            "bottom_read_shelf_um": round(bottom_shelf, 6),
            "top_write_shelf_um": round(top_shelf, 6),
            "absorbed_bottom_control_um": round(min(bottom_shelf, control_bottom), 6),
            "absorbed_top_control_um": round(min(top_shelf, control_top), 6),
            "bottom_extra_um": round(bottom_extra, 6),
            "top_extra_um": round(top_extra, 6),
            "core_control_bottom_um": round(control_bottom, 6),
            "core_control_top_um": round(control_top, 6),
            "read_phase_rows": read_phases,
            "write_phase_rows": write_phases,
            "instances": dict(counts),
            "instance_count": len(placement_rows),
            "route_count": len(routes),
            "policy": "compact hybrid wrapper: phase-packed column leaves consume existing core control bands before wrapper growth",
        }
        results.append(result)
        all_instances += len(placement_rows)
        all_routes += len(routes)

    manifest = {
        "package": "gf180mcu-3v3-12t-2r2w-sram-macro",
        "status": "PASS",
        "scope": "pitch-aware column periphery placement plan using existing core control bands plus minimal wrapper growth",
        "final_physical_manifest": rel(FINAL_MANIFEST),
        "periphery_manifest": rel(PERIPHERY_MANIFEST),
        "edge_margin_um": EDGE_MARGIN_UM,
        "row_gap_um": ROW_GAP_UM,
        "read_external_pin_y_um": READ_PIN_Y_UM,
        "total_instances": all_instances,
        "total_routes": all_routes,
        "results": results,
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    lines = [
        "# Column Periphery Integration Plan",
        "",
        "Pitch-aware per-port column periphery placement for the expanded macro wrapper.",
        "",
        "| Macro | Status | New size | Read phase rows | Write phase rows | Instances | Routes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| `{result['macro']}` | `{result['status']}` | "
            f"`{result['new_width_um']:.3f}um x {result['new_height_um']:.3f}um` | "
            f"{result['read_phase_rows']} | {result['write_phase_rows']} | "
            f"{result['instance_count']} | {result['route_count']} |"
        )
    (OUT / "README.md").write_text("\n".join(lines) + "\n")
    return manifest


def main() -> int:
    manifest = plan()
    print(f"GF180MCU 12T SRAM column periphery placement: {manifest['status']}")
    print(rel(OUT / "MANIFEST.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
