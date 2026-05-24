#!/usr/bin/env python3
"""Build hierarchical GF180MCU 3.3V 12T 2R2W SRAM array macro shells.

This is intentionally an array-shell step.  It follows Timothy's hierarchy
shape (small verified tile, repeated regular array placement, separated pitch)
instead of flattening and routing through the leaf interior.  The generated
macros remain route-contract blackboxes until strap-aware shared routing is
implemented in the tile.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from build_2r2w_macro_arrays import write_behavioral_model, write_decode_contract, write_spice, write_verilog
from build_physical_cells import bbox, dims_um
from extreme_compaction_search import read_magic


UNITS_PER_UM = 200.0
DEFAULT_SPECS = (
    ("detronyx_12t_2w2r_512x8_rc4b_timstyle_array", 512, 8),
    ("detronyx_12t_2w2r_512x32_rc4b_timstyle_array", 512, 32),
)


@dataclass(frozen=True)
class ArrayResult:
    macro: str
    source_tile: str
    rows: int
    data_width: int
    tile_rows: int
    tile_cols: int
    logical_tile_grid_rows: int
    logical_tile_grid_cols: int
    tile_grid_rows: int
    tile_grid_cols: int
    tile_slots: int
    spare_tile_slots: int
    bitcells: int
    tile_width_um: float
    tile_height_um: float
    tile_area_um2: float
    tile_area_per_bit_um2: float
    tile_gap_um: float
    array_width_um: float
    array_height_um: float
    control_left_um: float
    control_right_um: float
    control_bottom_um: float
    control_top_um: float
    width_um: float
    height_um: float
    area_um2: float
    area_mm2: float
    area_per_bit_um2: float
    target_area_mm2: float | None
    max_area_mm2: float | None
    area_budget_status: str
    drc_errors: int | None
    magic: str
    gds: str
    lef: str
    verilog: str
    spice: str
    behavioral_model: str
    decode_contract: str
    summary_md: str
    drc_log: str


def to_units(value_um: float) -> int:
    return int(round(value_um * UNITS_PER_UM))


def parse_drc_count(text: str) -> int | None:
    for pattern in (
        r"Total DRC errors found:\s*([0-9]+)",
        r"DRC error count:\s*([0-9]+)",
        r"([0-9]+)\s+total DRC errors",
    ):
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def parse_magic_power_labels(path: Path) -> dict[str, tuple[int, int]]:
    labels: dict[str, tuple[int, int]] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 13 or parts[0] != "flabel":
            continue
        name = parts[-1]
        if name not in {"VDD", "VSS"}:
            continue
        labels[name] = (int(parts[2]), int(parts[3]))
    if {"VDD", "VSS"} <= set(labels):
        return labels
    return {}


def append_m4_m5_stack(lines: list[str], x: int, y: int) -> None:
    lines.extend(
        [
            "<< metal4 >>",
            f"rect {x - 52} {y - 52} {x + 52} {y + 52}",
            "<< via4 >>",
            f"rect {x - 31} {y - 31} {x + 31} {y + 31}",
            "<< metal5 >>",
            f"rect {x - 58} {y - 58} {x + 58} {y + 58}",
        ]
    )


def write_top_magic(
    path: Path,
    *,
    macro: str,
    tile_cell: str,
    tech: str,
    magscale: str,
    tile_bbox: tuple[int, int, int, int],
    tile_w: int,
    tile_h: int,
    tile_pitch_x: int,
    tile_pitch_y: int,
    tile_grid_rows: int,
    tile_grid_cols: int,
    logical_tile_grid_rows: int,
    logical_tile_grid_cols: int,
    control_left: int,
    control_right: int,
    control_bottom: int,
    control_top: int,
    rows: int,
    data_width: int,
    tile_rows: int,
    tile_cols: int,
    tile_power_pins: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> None:
    xlo, ylo, xhi, yhi = tile_bbox
    lines = [
        "magic",
        f"tech {tech}",
        f"magscale {magscale}",
        "timestamp 1780024000",
    ]
    for tile_row in range(tile_grid_rows):
        for tile_col in range(tile_grid_cols):
            x = control_left + tile_col * tile_pitch_x
            y = control_bottom + tile_row * tile_pitch_y
            inst = f"u_t{tile_row:03d}_{tile_col:03d}"
            lines.extend(
                [
                    f"use {tile_cell} {inst}",
                    "timestamp 1780023000",
                    f"transform 1 0 {x} 0 1 {y}",
                    f"box {xlo} {ylo} {xhi} {yhi}",
                ]
            )
    marker_gap = to_units(0.2)
    if tile_power_pins and control_bottom > marker_gap and control_top > marker_gap:
        top_y = height - max(marker_gap, control_top // 2)
        bottom_y = max(marker_gap, control_bottom // 2)
        m4_w = to_units(0.34)
        vdd_local_x, vdd_local_y = tile_power_pins["VDD"]
        vss_local_x, vss_local_y = tile_power_pins["VSS"]

        for tile_col in range(tile_grid_cols):
            col_x = control_left + tile_col * tile_pitch_x
            vdd_x = col_x + vdd_local_x
            vss_x = col_x + vss_local_x
            vdd_low_y = control_bottom + vdd_local_y
            vss_high_y = control_bottom + (tile_grid_rows - 1) * tile_pitch_y + vss_local_y
            lines.extend(
                [
                    "<< metal4 >>",
                    f"rect {vdd_x - m4_w // 2} {min(vdd_low_y, top_y)} {vdd_x + (m4_w + 1) // 2} {max(vdd_low_y, top_y)}",
                    f"rect {vss_x - m4_w // 2} {min(bottom_y, vss_high_y)} {vss_x + (m4_w + 1) // 2} {max(bottom_y, vss_high_y)}",
                ]
            )
            append_m4_m5_stack(lines, vdd_x, top_y)
            append_m4_m5_stack(lines, vss_x, bottom_y)
            for tile_row in range(tile_grid_rows):
                row_y = control_bottom + tile_row * tile_pitch_y
                append_m4_m5_stack(lines, vdd_x, row_y + vdd_local_y)
                append_m4_m5_stack(lines, vss_x, row_y + vss_local_y)

    if any((control_left, control_right, control_bottom, control_top)):
        lines.append("<< metal3 >>")
        if control_bottom > marker_gap:
            lines.append(f"rect 0 0 {width} {control_bottom - marker_gap}")
        if control_top > marker_gap:
            lines.append(f"rect 0 {height - control_top + marker_gap} {width} {height}")
        if control_left > marker_gap:
            lines.append(f"rect 0 {control_bottom + marker_gap} {control_left - marker_gap} {height - control_top - marker_gap}")
        if control_right > marker_gap:
            lines.append(f"rect {width - control_right + marker_gap} {control_bottom + marker_gap} {width} {height - control_top - marker_gap}")
        lines.append("<< metal4 >>")
        if control_bottom > marker_gap:
            lines.append(f"rect 0 0 {width} {control_bottom - marker_gap}")
        if control_top > marker_gap:
            lines.append(f"rect 0 {height - control_top + marker_gap} {width} {height}")
        lines.append("<< metal5 >>")
        if control_bottom > marker_gap:
            lines.append(f"rect 0 0 {width} {control_bottom - marker_gap}")
        if control_top > marker_gap:
            lines.append(f"rect 0 {height - control_top + marker_gap} {width} {height}")
        if control_bottom > marker_gap or control_top > marker_gap:
            lines.append("<< labels >>")
            port = 1
            if control_top > marker_gap:
                x = width // 2
                y = height - max(marker_gap, control_top // 2)
                lines.append(f"flabel metal5 {x} {y} {x} {y} 0 FreeSans 93 0 0 0 VDD")
                lines.append(f"port {port} nsew")
                port += 1
            if control_bottom > marker_gap:
                x = width // 2
                y = max(marker_gap, control_bottom // 2)
                lines.append(f"flabel metal5 {x} {y} {x} {y} 0 FreeSans 93 0 0 0 VSS")
                lines.append(f"port {port} nsew")
    lines.extend(
        [
            "<< properties >>",
            f"string FIXED_BBOX 0 0 {width} {height}",
            f"string DETRONYX_PHYSICAL_MACRO {macro}",
            f"string DETRONYX_SOURCE_TILE {tile_cell}",
            "string DETRONYX_MACRO_STATUS rc4b_timstyle_array_shell_power_strapped" if tile_power_pins else "string DETRONYX_MACRO_STATUS rc4b_timstyle_array_shell_no_shared_straps",
            "string DETRONYX_ROUTE_STYLE timothy_regular_tile_array_with_m4_m5_power_straps" if tile_power_pins else "string DETRONYX_ROUTE_STYLE timothy_regular_tile_array",
            "string DETRONYX_CONTROL_STATUS footprint_bands_and_power_straps" if tile_power_pins else "string DETRONYX_CONTROL_STATUS footprint_bands_only",
            f"string DETRONYX_ROWS {rows}",
            f"string DETRONYX_DATA_WIDTH {data_width}",
            f"string DETRONYX_TILE_ROWS {tile_rows}",
            f"string DETRONYX_TILE_COLS {tile_cols}",
            f"string DETRONYX_TILE_GRID_ROWS {tile_grid_rows}",
            f"string DETRONYX_TILE_GRID_COLS {tile_grid_cols}",
            f"string DETRONYX_LOGICAL_TILE_GRID_ROWS {logical_tile_grid_rows}",
            f"string DETRONYX_LOGICAL_TILE_GRID_COLS {logical_tile_grid_cols}",
            f"string DETRONYX_TILE_WIDTH_UNITS {tile_w}",
            f"string DETRONYX_TILE_HEIGHT_UNITS {tile_h}",
            f"string DETRONYX_TILE_PITCH_X_UNITS {tile_pitch_x}",
            f"string DETRONYX_TILE_PITCH_Y_UNITS {tile_pitch_y}",
            f"string DETRONYX_CONTROL_LEFT_UNITS {control_left}",
            f"string DETRONYX_CONTROL_RIGHT_UNITS {control_right}",
            f"string DETRONYX_CONTROL_BOTTOM_UNITS {control_bottom}",
            f"string DETRONYX_CONTROL_TOP_UNITS {control_top}",
            "<< end >>",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def write_drc_tcl(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "crashbackups stop",
                "set topcell $::env(MAGIC_TOPCELL)",
                "load $topcell",
                "select top cell",
                "expand",
                "drc on",
                "drc style drc(full)",
                "drc check",
                "drc count total",
                "drc listall why",
                "quit -noprompt",
            ]
        )
        + "\n"
    )


def write_gds_tcl(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "crashbackups stop",
                "drc off",
                "set topcell $::env(MAGIC_TOPCELL)",
                "load $topcell",
                "select top cell",
                "expand",
                "gds write ../layout/$topcell.gds",
                "quit -noprompt",
            ]
        )
        + "\n"
    )


def run_magic(*, macro: str, magic_dir: Path, script: Path, log_path: Path, magic: str, magic_rc: Path) -> int | None:
    env = os.environ.copy()
    env["MAGIC_TOPCELL"] = macro
    proc = subprocess.run(
        [magic, "-dnull", "-noconsole", "-rcfile", str(magic_rc)],
        cwd=magic_dir,
        input=script.read_text(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        check=False,
    )
    log_path.write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"Magic failed for {macro}; see {log_path}")
    return parse_drc_count(proc.stdout)


def write_lef(path: Path, macro: str, width_um: float, height_um: float) -> None:
    power_pin_h_um = min(1.0, max(0.2, height_um / 32.0))
    obs_ylo = power_pin_h_um + 0.2
    obs_yhi = height_um - power_pin_h_um - 0.2
    upper_metal_obs = ""
    if obs_yhi > obs_ylo:
        upper_metal_obs = f"""    LAYER Metal3 ;
      RECT 0.000000 {obs_ylo:.6f} {width_um:.6f} {obs_yhi:.6f} ;
    LAYER Metal4 ;
      RECT 0.000000 {obs_ylo:.6f} {width_um:.6f} {obs_yhi:.6f} ;
    LAYER Metal5 ;
      RECT 0.000000 {obs_ylo:.6f} {width_um:.6f} {obs_yhi:.6f} ;
"""
    path.write_text(
        f"""VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
MACRO {macro}
  CLASS BLOCK ;
  FOREIGN {macro} 0.000 0.000 ;
  ORIGIN 0.000 0.000 ;
  SIZE {width_um:.6f} BY {height_um:.6f} ;
  SYMMETRY X Y ;
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER Metal4 ;
        RECT 0.000000 {height_um - power_pin_h_um:.6f} {width_um:.6f} {height_um:.6f} ;
      LAYER Metal5 ;
        RECT 0.000000 {height_um - power_pin_h_um:.6f} {width_um:.6f} {height_um:.6f} ;
    END
  END VDD
  PIN VSS
    DIRECTION INOUT ;
    USE GROUND ;
    PORT
      LAYER Metal4 ;
        RECT 0.000000 0.000000 {width_um:.6f} {power_pin_h_um:.6f} ;
      LAYER Metal5 ;
        RECT 0.000000 0.000000 {width_um:.6f} {power_pin_h_um:.6f} ;
    END
  END VSS
  OBS
    LAYER Metal1 ;
      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;
    LAYER Metal2 ;
      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;
{upper_metal_obs.rstrip()}
  END
END {macro}
END LIBRARY
"""
    )


def write_summary(result: ArrayResult, out_dir: Path) -> None:
    status = (
        "array shell with tile-to-macro M4/M5 power straps; signal periphery remains abstract"
        if "power_strapped" in result.source_tile
        else "array shell only; no shared straps/periphery yet"
    )
    (out_dir / "summary.json").write_text(json.dumps(asdict(result), indent=2, sort_keys=True) + "\n")
    lines = [
        f"# {result.macro} RC4B Timothy-Style Array",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Source tile | `{result.source_tile}` |",
        f"| Logical shape | `{result.rows} x {result.data_width}` |",
        f"| Logical tile grid | `{result.logical_tile_grid_rows} x {result.logical_tile_grid_cols}` |",
        f"| Physical tile grid | `{result.tile_grid_rows} x {result.tile_grid_cols}` |",
        f"| Spare tile slots | `{result.spare_tile_slots}` |",
        f"| Tile size | `{result.tile_width_um:.3f}um x {result.tile_height_um:.3f}um` |",
        f"| Tile area/bit | `{result.tile_area_per_bit_um2:.3f}um^2/bit` |",
        f"| Inter-tile gap | `{result.tile_gap_um:.3f}um` |",
        f"| Array-only size | `{result.array_width_um:.3f}um x {result.array_height_um:.3f}um` |",
        f"| Control bands | `L={result.control_left_um:.3f}um R={result.control_right_um:.3f}um B={result.control_bottom_um:.3f}um T={result.control_top_um:.3f}um` |",
        f"| Macro size | `{result.width_um:.3f}um x {result.height_um:.3f}um` |",
        f"| Macro area | `{result.area_mm2:.6f}mm^2` |",
        f"| Macro area/bit | `{result.area_per_bit_um2:.3f}um^2/bit` |",
        f"| Target area | `{result.target_area_mm2:.6f}mm^2` |" if result.target_area_mm2 is not None else "| Target area | `unbudgeted` |",
        f"| Max area | `{result.max_area_mm2:.6f}mm^2` |" if result.max_area_mm2 is not None else "| Max area | `unbudgeted` |",
        f"| Area budget | `{result.area_budget_status}` |",
        f"| DRC | `{result.drc_errors}` |",
        f"| Status | `{status}` |",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines))


def write_run_manifest(results: list[ArrayResult], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = [asdict(result) for result in results]
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if results:
        with (out_dir / "summary.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(asdict(results[0]).keys()))
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))
    lines = [
        "# RC4B Timothy-Style Array Run",
        "",
        "| Macro | Logical Shape | Physical Tile Grid | Size | Area | Budget | Area/bit | DRC |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| `{result.macro}` | `{result.rows}x{result.data_width}` | "
            f"`{result.tile_grid_rows}x{result.tile_grid_cols}` | "
            f"`{result.width_um:.3f}um x {result.height_um:.3f}um` | "
            f"`{result.area_mm2:.6f}mm^2` | `{result.area_budget_status}` | "
            f"`{result.area_per_bit_um2:.3f}um^2/bit` | "
            f"`{result.drc_errors}` |"
        )
    lines.extend(
        [
            "",
            "Status: route-contract array shells with explicit control footprint bands.",
            "When generated from `power_strapped_control` tiles, lower-metal tile rails are tied to macro M4/M5 VDD/VSS straps.",
            "Signal periphery, extracted full-macro PEX, and EM/IR remain separate signoff steps.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines))


def build_one(
    args: argparse.Namespace,
    macro: str,
    rows: int,
    data_width: int,
    physical_grid_rows: int | None = None,
    physical_grid_cols: int | None = None,
) -> ArrayResult:
    if rows % args.tile_rows != 0 or data_width % args.tile_cols != 0:
        raise ValueError(f"{macro}: rows/data_width must be divisible by tile dimensions")

    tile_layout = read_magic(args.tile_magic, args.tile_cell)
    tile_power_pins = parse_magic_power_labels(args.tile_magic)
    tile_bbox = bbox(tile_layout.rects)
    tile_w = tile_bbox[2] - tile_bbox[0]
    tile_h = tile_bbox[3] - tile_bbox[1]
    tile_width_um, tile_height_um, tile_area_um2 = dims_um(tile_bbox)
    logical_tile_grid_rows = rows // args.tile_rows
    logical_tile_grid_cols = data_width // args.tile_cols
    logical_tile_slots = logical_tile_grid_rows * logical_tile_grid_cols
    tile_grid_rows = physical_grid_rows if physical_grid_rows is not None else logical_tile_grid_rows
    tile_grid_cols = physical_grid_cols if physical_grid_cols is not None else logical_tile_grid_cols
    tile_slots = tile_grid_rows * tile_grid_cols
    if tile_slots < logical_tile_slots:
        raise ValueError(
            f"{macro}: physical tile grid {tile_grid_rows}x{tile_grid_cols} has {tile_slots} slots; "
            f"need at least {logical_tile_slots}"
        )
    gap = to_units(args.tile_gap_um)
    tile_pitch_x = tile_w + gap
    tile_pitch_y = tile_h + gap
    array_width = tile_grid_cols * tile_w + max(0, tile_grid_cols - 1) * gap
    array_height = tile_grid_rows * tile_h + max(0, tile_grid_rows - 1) * gap
    control_left = to_units(args.control_left_um)
    control_right = to_units(args.control_right_um)
    control_bottom = to_units(args.control_bottom_um)
    control_top = to_units(args.control_top_um)
    width = control_left + array_width + control_right
    height = control_bottom + array_height + control_top
    width_um = width / UNITS_PER_UM
    height_um = height / UNITS_PER_UM
    array_width_um = array_width / UNITS_PER_UM
    array_height_um = array_height / UNITS_PER_UM
    area_um2 = width_um * height_um
    area_mm2 = area_um2 / 1_000_000.0
    target_area_mm2 = args.target_area_budgets.get(macro)
    max_area_mm2 = args.max_area_budgets.get(macro)
    if max_area_mm2 is None:
        area_budget_status = "unbudgeted"
    elif area_mm2 <= max_area_mm2:
        if target_area_mm2 is not None and area_mm2 <= target_area_mm2:
            area_budget_status = "pass_target"
        else:
            area_budget_status = "pass_max"
    else:
        area_budget_status = "fail_max"

    out_dir = args.out_dir / macro
    magic_dir = out_dir / "magic"
    layout_dir = out_dir / "layout"
    abstract_dir = out_dir / "abstract"
    for directory in (magic_dir, layout_dir, abstract_dir):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.copy2(args.tile_magic, magic_dir / args.tile_magic.name)
    top_magic = magic_dir / f"{macro}.mag"
    write_top_magic(
        top_magic,
        macro=macro,
        tile_cell=args.tile_cell,
        tech=tile_layout.tech,
        magscale=tile_layout.magscale,
        tile_bbox=tile_bbox,
        tile_w=tile_w,
        tile_h=tile_h,
        tile_pitch_x=tile_pitch_x,
        tile_pitch_y=tile_pitch_y,
        tile_grid_rows=tile_grid_rows,
        tile_grid_cols=tile_grid_cols,
        logical_tile_grid_rows=logical_tile_grid_rows,
        logical_tile_grid_cols=logical_tile_grid_cols,
        control_left=control_left,
        control_right=control_right,
        control_bottom=control_bottom,
        control_top=control_top,
        rows=rows,
        data_width=data_width,
        tile_rows=args.tile_rows,
        tile_cols=args.tile_cols,
        tile_power_pins=tile_power_pins,
        width=width,
        height=height,
    )

    drc_tcl = magic_dir / "run_drc.tcl"
    gds_tcl = magic_dir / "run_gds.tcl"
    write_drc_tcl(drc_tcl)
    write_gds_tcl(gds_tcl)
    drc_log = layout_dir / f"{macro}.drc.log"
    gds_log = layout_dir / f"{macro}.gds.log"
    drc_errors = run_magic(macro=macro, magic_dir=magic_dir, script=drc_tcl, log_path=drc_log, magic=args.magic, magic_rc=args.magic_rc)
    run_magic(macro=macro, magic_dir=magic_dir, script=gds_tcl, log_path=gds_log, magic=args.magic, magic_rc=args.magic_rc)

    lef = abstract_dir / f"{macro}.lef"
    verilog = abstract_dir / f"{macro}.bb.sv"
    spice = abstract_dir / f"{macro}.spice"
    behavioral = abstract_dir / f"{macro}.behavioral.sv"
    decode = abstract_dir / f"{macro}.decode_contract.sv"
    write_lef(lef, macro, width_um, height_um)
    write_verilog(verilog, macro, rows, data_width)
    write_spice(spice, macro, rows, data_width)
    write_behavioral_model(behavioral, macro, rows, data_width)
    write_decode_contract(decode, macro, rows, data_width)

    bitcells = rows * data_width
    result = ArrayResult(
        macro=macro,
        source_tile=args.tile_cell,
        rows=rows,
        data_width=data_width,
        tile_rows=args.tile_rows,
        tile_cols=args.tile_cols,
        logical_tile_grid_rows=logical_tile_grid_rows,
        logical_tile_grid_cols=logical_tile_grid_cols,
        tile_grid_rows=tile_grid_rows,
        tile_grid_cols=tile_grid_cols,
        tile_slots=tile_slots,
        spare_tile_slots=tile_slots - logical_tile_slots,
        bitcells=bitcells,
        tile_width_um=round(tile_width_um, 6),
        tile_height_um=round(tile_height_um, 6),
        tile_area_um2=round(tile_area_um2, 6),
        tile_area_per_bit_um2=round(tile_area_um2 / (args.tile_rows * args.tile_cols), 6),
        tile_gap_um=args.tile_gap_um,
        array_width_um=round(array_width_um, 6),
        array_height_um=round(array_height_um, 6),
        control_left_um=args.control_left_um,
        control_right_um=args.control_right_um,
        control_bottom_um=args.control_bottom_um,
        control_top_um=args.control_top_um,
        width_um=round(width_um, 6),
        height_um=round(height_um, 6),
        area_um2=round(area_um2, 6),
        area_mm2=round(area_mm2, 9),
        area_per_bit_um2=round(area_um2 / bitcells, 6),
        target_area_mm2=target_area_mm2,
        max_area_mm2=max_area_mm2,
        area_budget_status=area_budget_status,
        drc_errors=drc_errors,
        magic=str(top_magic),
        gds=str(layout_dir / f"{macro}.gds"),
        lef=str(lef),
        verilog=str(verilog),
        spice=str(spice),
        behavioral_model=str(behavioral),
        decode_contract=str(decode),
        summary_md=str(out_dir / "summary.md"),
        drc_log=str(drc_log),
    )
    write_summary(result, out_dir)
    print(
        f"{macro}: {result.width_um:.3f}um x {result.height_um:.3f}um "
        f"= {result.area_mm2:.6f}mm^2, {result.area_per_bit_um2:.3f}um^2/bit, "
        f"budget={result.area_budget_status}, DRC={drc_errors}"
    )
    return result


def parse_specs(values: list[str]) -> list[tuple[str, int, int, int | None, int | None]]:
    if not values:
        return [(name, rows, data_width, None, None) for name, rows, data_width in DEFAULT_SPECS]
    specs = []
    for value in values:
        parts = value.split(":")
        if len(parts) == 3:
            name, rows, data_width = parts
            specs.append((name, int(rows), int(data_width), None, None))
        elif len(parts) == 5:
            name, rows, data_width, tile_grid_rows, tile_grid_cols = parts
            specs.append((name, int(rows), int(data_width), int(tile_grid_rows), int(tile_grid_cols)))
        else:
            raise ValueError("--spec must be name:rows:data_width or name:rows:data_width:tile_grid_rows:tile_grid_cols")
    return specs


def parse_budget(values: list[str], *, with_target: bool = True) -> tuple[dict[str, float], dict[str, float]]:
    max_budgets: dict[str, float] = {}
    target_budgets: dict[str, float] = {}
    for value in values:
        parts = value.split(":")
        if with_target:
            if len(parts) not in {2, 3}:
                raise ValueError("--budget must be name:max_area_mm2 or name:max_area_mm2:target_area_mm2")
            name, max_area = parts[0], parts[1]
            max_budgets[name] = float(max_area)
            if len(parts) == 3:
                target_budgets[name] = float(parts[2])
        else:
            if len(parts) != 2:
                raise ValueError("budget entry must be name:area_mm2")
            name, area = parts
            max_budgets[name] = float(area)
    return max_budgets, target_budgets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tile-magic", type=Path, required=True)
    parser.add_argument("--tile-cell", required=True)
    parser.add_argument("--tile-rows", type=int, default=4)
    parser.add_argument("--tile-cols", type=int, default=4)
    parser.add_argument("--tile-gap-um", type=float, default=0.6)
    parser.add_argument("--control-left-um", type=float, default=0.0)
    parser.add_argument("--control-right-um", type=float, default=0.0)
    parser.add_argument("--control-bottom-um", type=float, default=0.0)
    parser.add_argument("--control-top-um", type=float, default=0.0)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--spec", action="append", default=[], help="name:rows:data_width")
    parser.add_argument(
        "--budget",
        action="append",
        default=[],
        help="Area guardrail as name:max_area_mm2 or name:max_area_mm2:target_area_mm2",
    )
    parser.add_argument("--magic", default="magic")
    parser.add_argument("--magic-rc", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.max_area_budgets, args.target_area_budgets = parse_budget(args.budget)
    results = [build_one(args, *spec) for spec in parse_specs(args.spec)]
    write_run_manifest(results, args.out_dir)
    drc_ok = all(result.drc_errors == 0 for result in results)
    budget_ok = all(result.area_budget_status != "fail_max" for result in results)
    return 0 if drc_ok and budget_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
