#!/usr/bin/env python3
"""Generate release collateral for Avalon stdcell-backed SRAM control logic.

The package carries two different physical abstractions:

* the published top macro GDS files, which are array/control-corridor hard
  macro abstracts; and
* a structural row/control matrix that can be consumed by an abutted row-edge
  implementation step.

This script binds the structural matrix to real 3.3 V GF180MCU standard-cell
collateral from Avalon for ordinary digital gates.  SRAM-specific row-select
and WL-buffer leaves stay custom, because replacing them with generic logic
without row-pitch/drive closure would make the release package misleading.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


PACKAGE = "gf180mcu-3v3-12t-2r2w-sram-macro"
AVALON = "gf180mcu_as_sc_mcu7t3v3"
AVALON_ROOT = Path("third_party") / AVALON
AVALON_LIB = AVALON_ROOT / "pdk" / "libs.ref" / AVALON
SRC_MATRIX = Path("reports") / "control_matrix"
SRC_ROW_EDGE = Path("reports") / "row_edge_budget"
SRC_CUSTOM = Path("reports") / "control_leaf_library"
OUT = Path("reports") / "stdcell_control_integration"

PUBLIC_MACROS = {
    (512, 8): "gf180mcu_3v3_12t_2r2w_sram_512x8",
    (512, 32): "gf180mcu_3v3_12t_2r2w_sram_512x32",
    (1024, 8): "gf180mcu_3v3_12t_2r2w_sram_1024x8",
    (1024, 32): "gf180mcu_3v3_12t_2r2w_sram_1024x32",
}

REQUIRED_AVALON_FILES = [
    "LICENSE",
    "README.md",
    "README.upstream.md",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/gf180mcu_as_sc_mcu7t3v3__merged.gds",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/cdl/gf180mcu_as_sc_mcu7t3v3.cdl",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/lef/gf180mcu_as_sc_mcu7t3v3.lef",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/lib/gf180mcu_as_sc_mcu7t3v3__ff_n40C_3v60.lib",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/lib/gf180mcu_as_sc_mcu7t3v3__ss_125C_3v00.lib",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/lib/gf180mcu_as_sc_mcu7t3v3__tt_025C_3v30.lib",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/techlef/gf180mcu_as_sc_mcu7t3v3__max.tlef",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/techlef/gf180mcu_as_sc_mcu7t3v3__min.tlef",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/techlef/gf180mcu_as_sc_mcu7t3v3__nom.tlef",
    "pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/verilog/gf180mcu_as_sc_mcu7t3v3.v",
]

AVALON_CELLS = {
    "detronyx_12t_ctrl_inv_rc7": "gf180mcu_as_sc_mcu7t3v3__inv_2",
    "detronyx_12t_ctrl_nand2_rc7": "gf180mcu_as_sc_mcu7t3v3__nand2_2",
    "detronyx_12t_ctrl_nand3_rc7": "gf180mcu_as_sc_mcu7t3v3__nand3_2",
    "detronyx_12t_ctrl_nand4_rc7": "gf180mcu_as_sc_mcu7t3v3__nand4_2",
    "detronyx_12t_ctrl_nor2_rc7": "gf180mcu_as_sc_mcu7t3v3__nor2_2",
}

CUSTOM_ROW_SELECT_CELLS = {
    "detronyx_12t_ctrl_row_select3_wlbuf_rc7",
    "detronyx_12t_ctrl_row_select4_wlbuf_rc7",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(path)


def package_rel(path: Path) -> str:
    return path.as_posix()


def source_matrix_file(entry: dict[str, Any], key: str) -> Path:
    rel = str(entry[key])
    for prefix in (
        "build/rc7_control_matrix/",
        "reports/rc7_control_matrix/",
        "reports/control_matrix/",
    ):
        if rel.startswith(prefix):
            rel = rel[len(prefix) :]
            break
    return SRC_MATRIX / rel


def rewrite_subckt(line: str, public_cell: str) -> str:
    fields = line.split()
    if len(fields) >= 2 and fields[0].lower() == ".subckt":
        fields[1] = public_cell
        return " ".join(fields)
    fields = line.split()
    if len(fields) == 2 and fields[0].lower() == ".ends":
        fields[1] = public_cell
        return " ".join(fields)
    return line


def rewrite_instance(line: str, counts: dict[str, int]) -> str:
    stripped = line.strip()
    if not stripped or not stripped.startswith("X"):
        return line
    toks = stripped.split()
    cell = toks[-1]
    if cell == "detronyx_12t_ctrl_inv_rc7" and len(toks) == 6:
        inst, vdd, vss, a, y, _ = toks
        out = [inst, vdd, vdd, vss, vss, y, a, AVALON_CELLS[cell]]
    elif cell == "detronyx_12t_ctrl_nand2_rc7" and len(toks) == 7:
        inst, vdd, vss, a, b, y, _ = toks
        out = [inst, vdd, vdd, vss, vss, y, b, a, AVALON_CELLS[cell]]
    elif cell == "detronyx_12t_ctrl_nand3_rc7" and len(toks) == 8:
        inst, vdd, vss, a, b, c, y, _ = toks
        out = [inst, vdd, vdd, vss, vss, a, b, c, y, AVALON_CELLS[cell]]
    elif cell == "detronyx_12t_ctrl_nand4_rc7" and len(toks) == 9:
        inst, vdd, vss, a, b, c, d, y, _ = toks
        out = [inst, vdd, vdd, vss, vss, a, b, c, d, y, AVALON_CELLS[cell]]
    elif cell == "detronyx_12t_ctrl_nor2_rc7" and len(toks) == 7:
        inst, vdd, vss, a, b, y, _ = toks
        out = [inst, vdd, vdd, vss, vss, y, b, a, AVALON_CELLS[cell]]
    elif cell in CUSTOM_ROW_SELECT_CELLS:
        counts[cell] = counts.get(cell, 0) + 1
        return line
    else:
        return line

    counts[out[-1]] = counts.get(out[-1], 0) + 1
    return " ".join(out)


def build_avalon_manifest(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for rel in REQUIRED_AVALON_FILES:
        path = root / rel
        require_file(path)
        files.append(
            {
                "path": package_rel(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return {
        "library": AVALON,
        "source_repository": "https://github.com/AvalonSemiconductors/gf180mcu_as_sc_mcu7t3v3",
        "license": "Apache-2.0",
        "role": "GF180MCU 3.3V stdcell collateral for SRAM digital control logic",
        "files": files,
        "required_cells": sorted(set(AVALON_CELLS.values())),
    }


def cdl_header(public_cell: str, *, for_macro_abstract: bool) -> list[str]:
    row_prefix = "../../../reports/control_leaf_library" if for_macro_abstract else "../../control_leaf_library"
    return [
        f"* {public_cell}",
        "* Avalon stdcell-mapped digital control matrix for the release package.",
        f'.include "../../../{AVALON_LIB / "cdl" / (AVALON + ".cdl")}"',
        f'.include "{row_prefix}/detronyx_12t_ctrl_row_select3_wlbuf_rc7/abstract/detronyx_12t_ctrl_row_select3_wlbuf_rc7.reference.cdl"',
        f'.include "{row_prefix}/detronyx_12t_ctrl_row_select4_wlbuf_rc7/abstract/detronyx_12t_ctrl_row_select4_wlbuf_rc7.reference.cdl"',
        "",
    ]


def build_control_matrix(entry: dict[str, Any]) -> dict[str, Any]:
    rows = int(entry["rows"])
    data_width = int(entry["data_width"])
    public_macro = PUBLIC_MACROS[(rows, data_width)]
    public_cell = f"{public_macro}_stdcell_control_matrix"
    out_dir = OUT / public_macro
    out_dir.mkdir(parents=True, exist_ok=True)

    source_cdl = source_matrix_file(entry, "cdl")
    require_file(source_cdl)
    out_cdl = out_dir / f"{public_cell}.cdl"
    macro_cdl = Path("macros") / public_macro / "abstract" / f"{public_macro}.stdcell_control_matrix.cdl"
    macro_cdl.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    body: list[str] = []
    for raw in source_cdl.read_text().splitlines():
        line = rewrite_subckt(raw, public_cell)
        line = rewrite_instance(line, counts)
        body.append(line)

    text = "\n".join(cdl_header(public_cell, for_macro_abstract=False) + body) + "\n"
    macro_text = "\n".join(cdl_header(public_cell, for_macro_abstract=True) + body) + "\n"
    out_cdl.write_text(text)
    macro_cdl.write_text(macro_text)

    sv_source = source_matrix_file(entry, "sv")
    require_file(sv_source)
    out_sv = out_dir / f"{public_cell}.sv"
    sv_text = sv_source.read_text()
    old = f"{entry['macro']}_rc7_control_matrix"
    sv_text = sv_text.replace(old, public_cell)
    out_sv.write_text(sv_text)

    return {
        "macro": public_macro,
        "cell": public_cell,
        "rows": rows,
        "data_width": data_width,
        "addr_bits": int(entry["addr_bits"]),
        "physical_rows": int(entry["physical_rows"]),
        "total_control_gate_instances": int(entry["total_control_gate_instances"]),
        "stdcell_instances": {k: v for k, v in sorted(counts.items()) if k.startswith("gf180mcu_as_sc_mcu7t3v3__")},
        "custom_row_select_instances": {k: v for k, v in sorted(counts.items()) if k.startswith("detronyx_12t_ctrl_row_select")},
        "cdl": package_rel(out_cdl),
        "macro_abstract_cdl": package_rel(macro_cdl),
        "sv": package_rel(out_sv),
        "source_cdl": package_rel(source_cdl),
    }


def write_summary(manifest: dict[str, Any]) -> None:
    rows = manifest["control_matrices"]
    csv_path = OUT / "summary.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "macro",
                "physical_rows",
                "total_control_gate_instances",
                "avalon_stdcell_instances",
                "custom_row_select_instances",
                "cdl",
            ],
        )
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "macro": item["macro"],
                    "physical_rows": item["physical_rows"],
                    "total_control_gate_instances": item["total_control_gate_instances"],
                    "avalon_stdcell_instances": sum(item["stdcell_instances"].values()),
                    "custom_row_select_instances": sum(item["custom_row_select_instances"].values()),
                    "cdl": item["cdl"],
                }
            )

    md = [
        "# Avalon Stdcell Control Integration",
        "",
        "This report binds the SRAM control matrix to real GF180MCU 3.3V",
        "Avalon standard-cell collateral for ordinary digital logic.",
        "SRAM-specific row-select/WL-buffer cells remain custom leaves.",
        "",
        "| Macro | Physical WL Rows | Control Gates | Avalon Gates | Custom Row-Select |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in rows:
        md.append(
            "| `{macro}` | `{physical}` | `{total}` | `{avalon}` | `{custom}` |".format(
                macro=item["macro"],
                physical=item["physical_rows"],
                total=item["total_control_gate_instances"],
                avalon=sum(item["stdcell_instances"].values()),
                custom=sum(item["custom_row_select_instances"].values()),
            )
        )
    md.extend(
        [
            "",
            "Included Avalon collateral:",
            "",
            "- merged GDS",
            "- LEF and min/nom/max tech LEF",
            "- CDL",
            "- Verilog",
            "- TT/SS/FF Liberty corners",
            "",
            "The published top macro GDS files physically contain the placed",
            "Avalon `INV`/`NAND`/`NOR` control stdcells after the GDS merge step.",
            "Custom row-select/WL-buffer and periphery leaves remain separate",
            "until a row-pitch-compatible row-edge integration is generated.",
        ]
    )
    (OUT / "README.md").write_text("\n".join(md) + "\n")


def main() -> None:
    require_file(SRC_MATRIX / "MANIFEST.json")
    require_file(SRC_ROW_EDGE / "MANIFEST.json")
    require_file(SRC_CUSTOM / "MANIFEST.json")
    OUT.mkdir(parents=True, exist_ok=True)

    avalon_manifest = build_avalon_manifest(AVALON_ROOT)
    matrix_manifest = load_json(SRC_MATRIX / "MANIFEST.json")
    matrices = [build_control_matrix(entry) for entry in matrix_manifest]
    manifest = {
        "package": PACKAGE,
        "status": "stdcell_control_collateral_integrated",
        "avalon": avalon_manifest,
        "custom_row_select_library": {
            "path": package_rel(SRC_CUSTOM),
            "manifest": package_rel(SRC_CUSTOM / "MANIFEST.json"),
        },
        "row_edge_budget": {
            "path": package_rel(SRC_ROW_EDGE),
            "manifest": package_rel(SRC_ROW_EDGE / "MANIFEST.json"),
        },
        "control_matrices": matrices,
        "top_macro_gds_note": (
            "Published macro GDS files are array/control-corridor abstracts; "
            "stdcell control matrix placement into top GDS is intentionally gated "
            "separately."
        ),
    }
    (AVALON_ROOT / "MANIFEST.json").write_text(json.dumps(avalon_manifest, indent=2, sort_keys=True) + "\n")
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_summary(manifest)
    print(f"wrote {OUT / 'MANIFEST.json'}")


if __name__ == "__main__":
    main()
