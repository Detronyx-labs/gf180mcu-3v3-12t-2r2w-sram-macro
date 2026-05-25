#!/usr/bin/env python3
"""Place Avalon stdcell control gates inside the existing SRAM macro footprint.

This is a conservative placement stage for the release package.  It places only
the ordinary Avalon INV/NAND/NOR control gates into the already-reserved
top/bottom control bands.  The SRAM-specific row-select/WL-buffer leaves remain
deferred to a row-pitch-aware integration step; placing those large standalone
leaves one-per-wordline would increase the macro footprint dramatically.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(".")
STDCELL_MANIFEST = Path("reports/stdcell_control_integration/MANIFEST.json")
FINAL_MANIFEST = Path("reports/final_physical/MANIFEST.json")
AVALON_LEF = Path(
    "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/"
    "gf180mcu_as_sc_mcu7t3v3/lef/gf180mcu_as_sc_mcu7t3v3.lef"
)
AVALON_TECHLEF = Path(
    "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/"
    "gf180mcu_as_sc_mcu7t3v3/techlef/gf180mcu_as_sc_mcu7t3v3__nom.tlef"
)
OUT = Path("reports/stdcell_control_placement")
DBU = 1000
HORIZONTAL_GUARD_SITES = 1
VERTICAL_GUARD_ROWS = 1


@dataclass
class PlacedInstance:
    name: str
    original_name: str
    cell: str
    x_um: float
    y_um: float
    width_um: float
    height_um: float
    orient: str
    row: str


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_site(path: Path) -> tuple[str, float, float]:
    current_site: str | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("SITE "):
            current_site = line.split()[1]
            continue
        if current_site and line.startswith("SIZE "):
            match = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", line)
            if match:
                return current_site, float(match.group(1)), float(match.group(2))
        if current_site and line.startswith("END "):
            current_site = None
    raise ValueError(f"could not find LEF site size in {path}")


def parse_lef_sizes(path: Path) -> dict[str, tuple[float, float]]:
    sizes: dict[str, tuple[float, float]] = {}
    current_macro: str | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("MACRO "):
            current_macro = line.split()[1]
            continue
        if current_macro and line.startswith("SIZE "):
            match = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", line)
            if match:
                sizes[current_macro] = (float(match.group(1)), float(match.group(2)))
            continue
        if current_macro and line.startswith("END "):
            current_macro = None
    return sizes


def parse_stdcell_instances(path: Path, allowed_cells: set[str]) -> list[tuple[str, str]]:
    instances: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or not line.startswith("X"):
            continue
        toks = line.split()
        if len(toks) < 2:
            continue
        cell = toks[-1]
        if cell in allowed_cells:
            instances.append((toks[0], cell))
    return instances


def count_deferred_row_select(path: Path) -> int:
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("X") and line.split()[-1].startswith("detronyx_12t_ctrl_row_select"):
            count += 1
    return count


def sanitize(name: str, used: set[str]) -> str:
    clean = re.sub(r"[^A-Za-z0-9_$]", "_", name)
    if not clean or clean[0].isdigit():
        clean = f"u_{clean}"
    base = clean
    idx = 1
    while clean in used:
        idx += 1
        clean = f"{base}_{idx}"
    used.add(clean)
    return clean


def dbu(value_um: float) -> int:
    return int(round(value_um * DBU))


def make_rows(width_um: float, height_um: float, bottom_um: float, top_um: float, site: tuple[str, float, float]) -> list[dict[str, Any]]:
    site_name, site_w, site_h = site
    rows: list[dict[str, Any]] = []
    bottom_rows = max(0, int(bottom_um // site_h) - 2 * VERTICAL_GUARD_ROWS)
    top_rows = max(0, int(top_um // site_h) - 2 * VERTICAL_GUARD_ROWS)
    x_origin = HORIZONTAL_GUARD_SITES * site_w
    sites_x = max(0, int(width_um // site_w) - 2 * HORIZONTAL_GUARD_SITES)
    usable_w = sites_x * site_w
    for idx in range(bottom_rows):
        rows.append(
            {
                "name": f"bottom_ctrl_{idx}",
                "site": site_name,
                "x_um": x_origin,
                "y_um": (VERTICAL_GUARD_ROWS + idx) * site_h,
                "width_um": usable_w,
                "height_um": site_h,
                "orient": "N" if idx % 2 == 0 else "FS",
                "sites_x": sites_x,
                "cursor_um": 0.0,
            }
        )
    top_start = height_um - (VERTICAL_GUARD_ROWS + top_rows) * site_h
    for idx in range(top_rows):
        rows.append(
            {
                "name": f"top_ctrl_{idx}",
                "site": site_name,
                "x_um": x_origin,
                "y_um": top_start + idx * site_h,
                "width_um": usable_w,
                "height_um": site_h,
                "orient": "N" if idx % 2 == 0 else "FS",
                "sites_x": sites_x,
                "cursor_um": 0.0,
            }
        )
    return rows


def place_instances(
    instances: list[tuple[str, str]],
    sizes: dict[str, tuple[float, float]],
    rows: list[dict[str, Any]],
) -> tuple[list[PlacedInstance], list[str]]:
    placed: list[PlacedInstance] = []
    errors: list[str] = []
    used_names: set[str] = set()
    ordered = sorted(instances, key=lambda item: sizes[item[1]][0], reverse=True)
    for original, cell in ordered:
        width, height = sizes[cell]
        candidates = [row for row in rows if row["cursor_um"] + width <= row["width_um"] + 1e-9]
        if not candidates:
            errors.append(f"no row capacity for {original} {cell} width={width}")
            continue
        row = min(candidates, key=lambda r: r["cursor_um"] / max(r["width_um"], 1e-9))
        name = sanitize(original, used_names)
        placed.append(
            PlacedInstance(
                name=name,
                original_name=original,
                cell=cell,
                x_um=row["x_um"] + row["cursor_um"],
                y_um=row["y_um"],
                width_um=width,
                height_um=height,
                orient=row["orient"],
                row=row["name"],
            )
        )
        row["cursor_um"] += width
    return placed, errors


def write_def(path: Path, macro: str, item: dict[str, Any], rows: list[dict[str, Any]], placed: list[PlacedInstance]) -> None:
    width = float(item["width_um"])
    height = float(item["height_um"])
    lines = [
        "VERSION 5.8 ;",
        'DIVIDERCHAR "/" ;',
        'BUSBITCHARS "[]" ;',
        f"DESIGN {macro}_stdcell_control_placement ;",
        f"UNITS DISTANCE MICRONS {DBU} ;",
        f"DIEAREA ( 0 0 ) ( {dbu(width)} {dbu(height)} ) ;",
        "",
    ]
    for row in rows:
        lines.append(
            "ROW {name} {site} {x} {y} {orient} DO {nx} BY 1 STEP {step} 0 ;".format(
                name=row["name"],
                site=row["site"],
                x=dbu(row["x_um"]),
                y=dbu(row["y_um"]),
                orient=row["orient"],
                nx=row["sites_x"],
                step=dbu(row["width_um"] / row["sites_x"]),
            )
        )
    lines += ["", f"COMPONENTS {len(placed)} ;"]
    for inst in placed:
        lines.append(
            f"  - {inst.name} {inst.cell} + PLACED ( {dbu(inst.x_um)} {dbu(inst.y_um)} ) {inst.orient} ;"
        )
    lines += ["END COMPONENTS", "", f"END {macro}_stdcell_control_placement", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, placed: list[PlacedInstance]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(placed[0]).keys()) if placed else ["name"])
        writer.writeheader()
        for inst in placed:
            writer.writerow(asdict(inst))


def main() -> int:
    std_manifest = load_json(STDCELL_MANIFEST)
    final_items = {item["macro"]: item for item in load_json(FINAL_MANIFEST)}
    sizes = parse_lef_sizes(AVALON_LEF)
    site = parse_site(AVALON_TECHLEF)
    required = set(std_manifest["avalon"]["required_cells"])
    missing_sizes = sorted(required - set(sizes))
    if missing_sizes:
        raise SystemExit(f"missing LEF sizes for {missing_sizes}")
    OUT.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    overall_errors: list[str] = []
    for matrix in std_manifest["control_matrices"]:
        macro = matrix["macro"]
        item = final_items[macro]
        out_dir = OUT / macro
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = make_rows(
            float(item["width_um"]),
            float(item["height_um"]),
            float(item["control_bottom_um"]),
            float(item["control_top_um"]),
            site,
        )
        instances = parse_stdcell_instances(Path(matrix["cdl"]), required)
        deferred = count_deferred_row_select(Path(matrix["cdl"]))
        placed, errors = place_instances(instances, sizes, rows)
        overall_errors.extend([f"{macro}: {err}" for err in errors])

        def_path = out_dir / f"{macro}.stdcell_control_placement.def"
        csv_path = out_dir / f"{macro}.stdcell_control_placement.csv"
        write_def(def_path, macro, item, rows, placed)
        write_csv(csv_path, placed)

        total_area = sum(inst.width_um * inst.height_um for inst in placed)
        avail_area = sum(row["width_um"] * row["height_um"] for row in rows)
        max_row_util = max((row["cursor_um"] / row["width_um"] for row in rows), default=0.0)
        result = {
            "macro": macro,
            "status": "PASS" if not errors and len(placed) == len(instances) else "FAIL",
            "footprint_unchanged": True,
            "macro_width_um": float(item["width_um"]),
            "macro_height_um": float(item["height_um"]),
            "control_bottom_um": float(item["control_bottom_um"]),
            "control_top_um": float(item["control_top_um"]),
            "site": {"name": site[0], "width_um": site[1], "height_um": site[2]},
            "stdcell_instances_expected": len(instances),
            "stdcell_instances_placed": len(placed),
            "deferred_row_select_instances": deferred,
            "stdcell_area_um2": round(total_area, 6),
            "available_control_band_area_um2": round(avail_area, 6),
            "overall_utilization": round(total_area / avail_area, 6) if avail_area else 0.0,
            "max_row_utilization": round(max_row_util, 6),
            "rows": [
                {
                    "name": row["name"],
                    "x_um": row["x_um"],
                    "y_um": row["y_um"],
                    "width_um": row["width_um"],
                    "height_um": row["height_um"],
                    "orient": row["orient"],
                    "used_width_um": round(row["cursor_um"], 6),
                    "utilization": round(row["cursor_um"] / row["width_um"], 6) if row["width_um"] else 0.0,
                }
                for row in rows
            ],
            "def": def_path.as_posix(),
            "placement_csv": csv_path.as_posix(),
            "errors": errors,
        }
        results.append(result)

    manifest = {
        "package": "gf180mcu-3v3-12t-2r2w-sram-macro",
        "status": "PASS" if not overall_errors else "FAIL",
        "scope": "Avalon stdcell control placement only; row-select/WL-buffer/periphery leaf placement is deferred.",
        "footprint_policy": "do not change macro width_um or height_um from reports/final_physical/MANIFEST.json",
        "gds_guard_band": {
            "horizontal_guard_sites": HORIZONTAL_GUARD_SITES,
            "vertical_guard_rows": VERTICAL_GUARD_ROWS,
        },
        "avalon_lef": AVALON_LEF.as_posix(),
        "avalon_techlef": AVALON_TECHLEF.as_posix(),
        "stdcell_control_manifest": STDCELL_MANIFEST.as_posix(),
        "final_physical_manifest": FINAL_MANIFEST.as_posix(),
        "results": results,
        "errors": overall_errors,
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (OUT / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "macro",
                "status",
                "stdcell_instances_placed",
                "deferred_row_select_instances",
                "overall_utilization",
                "max_row_utilization",
                "def",
            ],
        )
        writer.writeheader()
        for item in results:
            writer.writerow({field: item[field] for field in writer.fieldnames})

    lines = [
        "# Stdcell Control Placement",
        "",
        "This report places only the Avalon stdcell control gates inside the",
        "existing top/bottom control bands. It does not grow macro width or height.",
        "",
        "| Macro | Status | Placed stdcells | Deferred row-select | Overall util | Max row util |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        lines.append(
            f"| `{item['macro']}` | `{item['status']}` | {item['stdcell_instances_placed']} | "
            f"{item['deferred_row_select_instances']} | {item['overall_utilization']:.3f} | "
            f"{item['max_row_utilization']:.3f} |"
        )
    lines += [
        "",
        "Row-select/WL-buffer and periphery leaf placement remains open because the",
        "standalone custom row-select leaf dimensions are not row-pitch-compatible when",
        "instantiated one per wordline.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"GF180MCU 12T SRAM stdcell placement: {manifest['status']}")
    print(OUT / "MANIFEST.json")
    return 0 if not overall_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
