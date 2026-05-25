#!/usr/bin/env python3
"""Expand row-select/WL-buffer cells into row-pitch-compatible Avalon stdcells.

The standalone custom row-select leaves are DRC/LVS-clean, but too tall to place
one per physical wordline.  This step expands each selected-row function into a
single standard-cell row:

* row_select4_wlbuf: NAND4 + INV + INV + INV
* row_select3_wlbuf: NAND3 + INV + INV + INV

It emits placement collateral plus an expanded CDL with no custom row-select
subckt references.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(".")
FINAL_MANIFEST = Path("reports/final_physical/MANIFEST.json")
STDCELL_MANIFEST = Path("reports/stdcell_control_integration/MANIFEST.json")
AVALON_LEF = Path(
    "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/"
    "gf180mcu_as_sc_mcu7t3v3/lef/gf180mcu_as_sc_mcu7t3v3.lef"
)
AVALON_TECHLEF = Path(
    "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/"
    "gf180mcu_as_sc_mcu7t3v3/techlef/gf180mcu_as_sc_mcu7t3v3__nom.tlef"
)
OUT = Path("reports/stdcell_row_select_placement")
DBU = 1000
GRID_UM = 0.005

NAND3 = "gf180mcu_as_sc_mcu7t3v3__nand3_2"
NAND4 = "gf180mcu_as_sc_mcu7t3v3__nand4_2"
INV = "gf180mcu_as_sc_mcu7t3v3__inv_2"


@dataclass
class RowSelectInstance:
    original_name: str
    kind: str
    port: str
    row_index: int
    nets: list[str]


@dataclass
class PlacedCell:
    name: str
    original_name: str
    role: str
    cell: str
    port: str
    row_index: int
    x_um: float
    y_um: float
    width_um: float
    height_um: float
    orient: str


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


def round_grid(value: float) -> float:
    return round(round(value / GRID_UM) * GRID_UM, 6)


def dbu(value_um: float) -> int:
    return int(round(value_um * DBU))


def row_select_kind(cell: str) -> str | None:
    if cell.endswith("row_select4_wlbuf_rc7"):
        return "row_select4"
    if cell.endswith("row_select3_wlbuf_rc7"):
        return "row_select3"
    return None


def parse_row_selects(path: Path) -> list[RowSelectInstance]:
    result: list[RowSelectInstance] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("X"):
            continue
        toks = line.split()
        if not toks:
            continue
        kind = row_select_kind(toks[-1])
        if kind is None:
            continue
        name = toks[0]
        match = re.match(r"X(?P<port>w0|w1|r0|r1)_row(?P<row>\d+)_sel", name)
        if not match:
            raise ValueError(f"unsupported row-select instance name in {path}: {name}")
        if kind == "row_select4" and len(toks) != 9:
            raise ValueError(f"unexpected row_select4 token count for {name}: {len(toks)}")
        if kind == "row_select3" and len(toks) != 8:
            raise ValueError(f"unexpected row_select3 token count for {name}: {len(toks)}")
        result.append(
            RowSelectInstance(
                original_name=name,
                kind=kind,
                port=match.group("port"),
                row_index=int(match.group("row")),
                nets=toks[1:-1],
            )
        )
    return result


def port_index(port: str) -> int:
    return {"w0": 0, "w1": 1, "r0": 2, "r1": 3}[port]


def expand_cdl_line(inst: RowSelectInstance) -> list[str]:
    vdd, vss = inst.nets[0], inst.nets[1]
    row_n = f"{inst.original_name[1:]}_row_n"
    buf0 = f"{inst.original_name[1:]}_buf0"
    buf1 = f"{inst.original_name[1:]}_buf1"
    if inst.kind == "row_select4":
        p0, p1, p2, en, wl = inst.nets[2], inst.nets[3], inst.nets[4], inst.nets[5], inst.nets[6]
        return [
            f"{inst.original_name}_nand4 {vdd} {vdd} {vss} {vss} {p0} {p1} {p2} {en} {row_n} {NAND4}",
            f"{inst.original_name}_buf0 {vdd} {vdd} {vss} {vss} {buf0} {row_n} {INV}",
            f"{inst.original_name}_buf1 {vdd} {vdd} {vss} {vss} {buf1} {buf0} {INV}",
            f"{inst.original_name}_buf2 {vdd} {vdd} {vss} {vss} {wl} {buf1} {INV}",
        ]
    p0, p1, p2, wl = inst.nets[2], inst.nets[3], inst.nets[4], inst.nets[5]
    return [
        f"{inst.original_name}_nand3 {vdd} {vdd} {vss} {vss} {p0} {p1} {p2} {row_n} {NAND3}",
        f"{inst.original_name}_buf0 {vdd} {vdd} {vss} {vss} {buf0} {row_n} {INV}",
        f"{inst.original_name}_buf1 {vdd} {vdd} {vss} {vss} {buf1} {buf0} {INV}",
        f"{inst.original_name}_buf2 {vdd} {vdd} {vss} {vss} {wl} {buf1} {INV}",
    ]


def write_expanded_cdl(source: Path, report_path: Path, macro_path: Path, macro: str) -> None:
    out_name = f"{macro}_stdcell_full_control_matrix"
    lines: list[str] = []
    for raw in source.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if "control_leaf_library/detronyx_12t_ctrl_row_select" in stripped:
            continue
        if stripped.startswith(".subckt "):
            parts = stripped.split()
            parts[1] = out_name
            lines.append(" ".join(parts))
            continue
        if stripped.startswith(".ends "):
            lines.append(f".ends {out_name}")
            continue
        if stripped.startswith("X"):
            toks = stripped.split()
            kind = row_select_kind(toks[-1]) if toks else None
            if kind:
                insts = parse_row_selects_from_tokens(source, toks, kind)
                lines.extend(expand_cdl_line(insts))
                continue
        lines.append(line)
    header = [
        f"* {out_name}",
        "* Row-select/WL-buffer functions expanded into Avalon NAND/INV stdcells.",
    ]
    report_path.write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    macro_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")


def parse_row_selects_from_tokens(path: Path, toks: list[str], kind: str) -> RowSelectInstance:
    name = toks[0]
    match = re.match(r"X(?P<port>w0|w1|r0|r1)_row(?P<row>\d+)_sel", name)
    if not match:
        raise ValueError(f"unsupported row-select instance name in {path}: {name}")
    return RowSelectInstance(name, kind, match.group("port"), int(match.group("row")), toks[1:-1])


def place_row_selects(
    *,
    item: dict[str, Any],
    row_selects: list[RowSelectInstance],
    sizes: dict[str, tuple[float, float]],
    site_h: float,
) -> list[PlacedCell]:
    predecode = float(item["predecode_width_um"])
    strip = float(item["port_strip_width_um"])
    control_bottom = float(item["control_bottom_um"])
    control_top = float(item["control_top_um"])
    height = float(item["height_um"])
    physical_rows = int(item["physical_rows"])
    pitch = (height - control_bottom - control_top) / physical_rows
    if pitch < site_h:
        raise ValueError(f"{item['macro']}: row pitch {pitch:.3f}um is smaller than stdcell height {site_h:.3f}um")
    guard_x = 0.56
    placed: list[PlacedCell] = []
    for inst in row_selects:
        y = round_grid(control_bottom + inst.row_index * pitch + (pitch - site_h) / 2.0)
        if y < control_bottom - 1e-6 or y + site_h > height - control_top + 1e-6:
            raise ValueError(f"{item['macro']}: row-select y out of array band for {inst.original_name}: {y}")
        x = round_grid(predecode + port_index(inst.port) * strip + guard_x)
        roles = [("nand4" if inst.kind == "row_select4" else "nand3", NAND4 if inst.kind == "row_select4" else NAND3), ("buf0", INV), ("buf1", INV), ("buf2", INV)]
        cursor = x
        total_w = sum(sizes[cell][0] for _role, cell in roles)
        if cursor + total_w > predecode + (port_index(inst.port) + 1) * strip - guard_x + 1e-6:
            raise ValueError(f"{item['macro']}: row-select chain does not fit strip for {inst.original_name}")
        for role, cell in roles:
            w, h = sizes[cell]
            placed.append(
                PlacedCell(
                    name=f"{inst.original_name}_{role}",
                    original_name=inst.original_name,
                    role=role,
                    cell=cell,
                    port=inst.port,
                    row_index=inst.row_index,
                    x_um=round_grid(cursor),
                    y_um=y,
                    width_um=w,
                    height_um=h,
                    orient="N",
                )
            )
            cursor += w
    return placed


def write_csv(path: Path, placed: list[PlacedCell]) -> None:
    fields = list(PlacedCell.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for cell in placed:
            writer.writerow(asdict(cell))


def write_def(path: Path, macro: str, item: dict[str, Any], placed: list[PlacedCell]) -> None:
    width = float(item["width_um"])
    height = float(item["height_um"])
    lines = [
        "VERSION 5.8 ;",
        'DIVIDERCHAR "/" ;',
        'BUSBITCHARS "[]" ;',
        f"DESIGN {macro}_row_select_stdcell_placement ;",
        f"UNITS DISTANCE MICRONS {DBU} ;",
        f"DIEAREA ( 0 0 ) ( {dbu(width)} {dbu(height)} ) ;",
        "",
        f"COMPONENTS {len(placed)} ;",
    ]
    for cell in placed:
        lines.append(f"  - {cell.name} {cell.cell} + PLACED ( {dbu(cell.x_um)} {dbu(cell.y_um)} ) {cell.orient} ;")
    lines.extend(["END COMPONENTS", "", f"END {macro}_row_select_stdcell_placement", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    final = {item["macro"]: item for item in load_json(FINAL_MANIFEST)}
    std_manifest = load_json(STDCELL_MANIFEST)
    sizes = parse_lef_sizes(AVALON_LEF)
    _site_name, _site_w, site_h = parse_site(AVALON_TECHLEF)
    for cell in (NAND3, NAND4, INV):
        if cell not in sizes:
            raise SystemExit(f"missing LEF size for {cell}")
    OUT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for matrix in std_manifest["control_matrices"]:
        macro = matrix["macro"]
        item = final[macro]
        source = Path(matrix["macro_abstract_cdl"])
        row_selects = parse_row_selects(source)
        out_dir = OUT / macro
        out_dir.mkdir(parents=True, exist_ok=True)
        placed = place_row_selects(item=item, row_selects=row_selects, sizes=sizes, site_h=site_h)
        csv_path = out_dir / f"{macro}.row_select_stdcell_placement.csv"
        def_path = out_dir / f"{macro}.row_select_stdcell_placement.def"
        report_cdl = out_dir / f"{macro}.stdcell_full_control_matrix.cdl"
        macro_cdl = Path("macros") / macro / "abstract" / f"{macro}.stdcell_full_control_matrix.cdl"
        write_csv(csv_path, placed)
        write_def(def_path, macro, item, placed)
        write_expanded_cdl(source, report_cdl, macro_cdl, macro)
        per_cell: dict[str, int] = {}
        for cell in placed:
            per_cell[cell.cell] = per_cell.get(cell.cell, 0) + 1
        pitch = (float(item["height_um"]) - float(item["control_bottom_um"]) - float(item["control_top_um"])) / int(item["physical_rows"])
        results.append(
            {
                "macro": macro,
                "status": "PASS",
                "row_select_instances": len(row_selects),
                "placed_stdcells": len(placed),
                "stdcell_counts": dict(sorted(per_cell.items())),
                "physical_rows": int(item["physical_rows"]),
                "row_pitch_um": round(pitch, 6),
                "stdcell_height_um": site_h,
                "footprint_unchanged": True,
                "placement_csv": csv_path.as_posix(),
                "def": def_path.as_posix(),
                "expanded_cdl": report_cdl.as_posix(),
                "macro_expanded_cdl": macro_cdl.as_posix(),
            }
        )
    manifest = {
        "package": "gf180mcu-3v3-12t-2r2w-sram-macro",
        "status": "PASS",
        "scope": "row-select/WL-buffer expansion into row-pitch-compatible Avalon stdcells",
        "final_physical_manifest": FINAL_MANIFEST.as_posix(),
        "stdcell_control_manifest": STDCELL_MANIFEST.as_posix(),
        "avalon_lef": AVALON_LEF.as_posix(),
        "results": results,
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Row-Select Stdcell Expansion",
        "",
        "Custom row-select/WL-buffer functions are expanded into row-pitch-compatible Avalon stdcells.",
        "",
        "| Macro | Status | Row-selects | Placed stdcells | Row pitch |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for item in results:
        lines.append(f"| `{item['macro']}` | `{item['status']}` | {item['row_select_instances']} | {item['placed_stdcells']} | {item['row_pitch_um']:.3f}um |")
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("GF180MCU 12T SRAM row-select stdcell placement: PASS")
    print(OUT / "MANIFEST.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
