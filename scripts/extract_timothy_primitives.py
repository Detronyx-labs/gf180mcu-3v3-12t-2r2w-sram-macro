#!/usr/bin/env python3
"""Extract Timothy-derived transistor primitives from the SRAM bitcell layout.

This deliberately does not use the 6T cell as a reusable hard block. It reads
the Magic leaf, normalizes SRAM-special layers, identifies individual FET
rectangles, and emits per-device primitive snippets plus an inventory.

The generated primitives are a placement seed library for Detronyx 10T/12T
work. They are not a replacement for a finished extracted SRAM leaf.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from extreme_compaction_search import LAYER_MAP, Rect, read_magic, write_magic


UNITS_PER_UM = 200.0
LOCAL_DEVICE_LAYERS = {
    "nfet",
    "pfet",
    "ndiff",
    "pdiff",
    "ndiffc",
    "pdiffc",
    "polysilicon",
    "polycontact",
}


@dataclass
class Primitive:
    name: str
    role: str
    model: str
    spice_w_um: float
    spice_l_um: float
    source_file: str
    source_fet_bboxes: list[list[int]]
    fet_count: int
    local_bbox_um: list[float]
    mag_file: str


EXTRA_PRIMITIVE_SOURCES = [
    {
        "name": "tim_periphery_read_nfet_0p53_nf2",
        "role": "read_periphery_nfet_0p53_nf2",
        "model": "nfet_03v3",
        "spice_w_um": 0.53,
        "spice_l_um": 0.28,
        "source_file": "nmos_5p04310591302032_3v512x8m81.mag",
        "note": "Tim SPICE uses W=0.53u L=0.28u nf=2 for this periphery device.",
    },
    {
        "name": "tim_periphery_write_nfet_1p055",
        "role": "single_ended_write_nfet_1p055",
        "model": "nfet_03v3",
        "spice_w_um": 1.055,
        "spice_l_um": 0.28,
        "source_file": "nmos_5p04310591302010_3v512x8m81.mag",
        "note": "Tim periphery 1.055um NFET used as compact write-driver/access seed.",
    },
    {
        "name": "tim_periphery_row_access_nfet_2p115",
        "role": "row_access_strong_nfet_2p115",
        "model": "nfet_03v3",
        "spice_w_um": 2.115,
        "spice_l_um": 0.28,
        "source_file": "nmos_5p04310591302057_3v512x8m81.mag",
        "note": "Tim periphery 2.115um NFET used as strong row/write access seed.",
    },
]


def rect_intersects_window(rect: Rect, window: tuple[int, int, int, int]) -> bool:
    xlo, ylo, xhi, yhi = window
    return max(rect.xlo, xlo) < min(rect.xhi, xhi) and max(rect.ylo, ylo) < min(rect.yhi, yhi)


def classify_fet(rect: Rect) -> tuple[str, str, float, float]:
    width = rect.xhi - rect.xlo
    height = rect.yhi - rect.ylo
    dims = tuple(sorted((width, height)))

    if rect.layer == "nfet" and dims == (56, 90):
        return ("latch_pulldown_nfet", "nfet_03v3", 0.45, 0.28)
    if rect.layer == "nfet" and dims == (56, 72):
        return ("write_access_nfet", "nfet_03v3", 0.28, 0.36)
    if rect.layer == "pfet" and dims == (56, 56):
        return ("latch_pullup_pfet", "pfet_03v3", 0.28, 0.28)

    role = f"unknown_{rect.layer}_{width}x{height}"
    model = "nfet_03v3" if rect.layer == "nfet" else "pfet_03v3"
    return (role, model, width / UNITS_PER_UM, height / UNITS_PER_UM)


def make_local_primitive(source_name: str, role: str, index: int, source, fet: Rect, margin: int):
    window = (fet.xlo - margin, fet.ylo - margin, fet.xhi + margin, fet.yhi + margin)
    local_rects = [
        rect
        for rect in source.rects
        if rect.layer in LOCAL_DEVICE_LAYERS and rect_intersects_window(rect, window)
    ]
    if fet not in local_rects:
        local_rects.append(fet)

    name = f"{source_name}_{role}_{index}"
    from extreme_compaction_search import Layout

    return Layout(name=name, tech=source.tech, magscale=source.magscale, rects=local_rects).shifted_to_origin()


def um_bbox(layout) -> list[float]:
    xlo, ylo, xhi, yhi = layout.bbox()
    return [
        round((xhi - xlo) / UNITS_PER_UM, 6),
        round((yhi - ylo) / UNITS_PER_UM, 6),
        round(((xhi - xlo) * (yhi - ylo)) / (UNITS_PER_UM * UNITS_PER_UM), 6),
    ]


def write_markdown(primitives: list[Primitive], path: Path) -> None:
    role_counts: dict[str, int] = {}
    for primitive in primitives:
        role_counts[primitive.role] = role_counts.get(primitive.role, 0) + 1

    lines = [
        "# Timothy Primitive Inventory",
        "",
        "This inventory is extracted from Timothy 3.3V SRAM Magic geometry.",
        "The 6T cell is not used as a hard block here; only individual bitcell",
        "and periphery device primitives are emitted for later Detronyx 10T/12T",
        "placement.",
        "",
        "## Role Counts",
        "",
        "| Role | Count | Model | W | L |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    seen: set[str] = set()
    for primitive in primitives:
        if primitive.role in seen:
            continue
        seen.add(primitive.role)
        lines.append(
            f"| `{primitive.role}` | {role_counts[primitive.role]} | `{primitive.model}` | "
            f"`{primitive.spice_w_um:.3f}um` | `{primitive.spice_l_um:.3f}um` |"
        )

    lines.extend(
        [
            "",
            "## Primitive Files",
            "",
            "| Name | Role | Local bbox | File |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for primitive in primitives:
        width, height, area = primitive.local_bbox_um
        lines.append(
            f"| `{primitive.name}` | `{primitive.role}` | "
            f"`{width:.3f}um x {height:.3f}um = {area:.3f}um^2` | `{primitive.mag_file}` |"
        )

    path.write_text("\n".join(lines) + "\n")


def fet_rects(layout) -> list[Rect]:
    return [rect for rect in layout.rects if rect.layer in {"nfet", "pfet"}]


def write_extra_primitive(source_root: Path, out_dir: Path, spec: dict) -> Primitive:
    source_path = source_root / spec["source_file"]
    layout = read_magic(source_path, spec["name"])
    mag_path = out_dir / f"{layout.name}.mag"
    write_magic(layout, mag_path, layout.name)
    fets = fet_rects(layout)
    return Primitive(
        name=layout.name,
        role=spec["role"],
        model=spec["model"],
        spice_w_um=spec["spice_w_um"],
        spice_l_um=spec["spice_l_um"],
        source_file=str(source_path),
        source_fet_bboxes=[[fet.xlo, fet.ylo, fet.xhi, fet.yhi] for fet in fets],
        fet_count=len(fets),
        local_bbox_um=um_bbox(layout),
        mag_file=mag_path.name,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--margin", type=int, default=80, help="Local crop margin in Magic units")
    parser.add_argument(
        "--include-periphery",
        action="store_true",
        help="Also extract selected Tim periphery NFET primitives needed by 10T/12T work",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    source = read_magic(args.source, "tim6t_primitive_source")

    fets = [rect for rect in source.rects if rect.layer in {"nfet", "pfet"}]
    primitives: list[Primitive] = []
    role_index: dict[str, int] = {}

    for fet in sorted(fets, key=lambda r: (r.layer, r.ylo, r.xlo)):
        role, model, spice_w, spice_l = classify_fet(fet)
        role_index[role] = role_index.get(role, 0) + 1
        index = role_index[role]
        layout = make_local_primitive("tim", role, index, source, fet, args.margin)
        mag_path = args.out_dir / f"{layout.name}.mag"
        write_magic(layout, mag_path, layout.name)
        primitives.append(
            Primitive(
                name=layout.name,
                role=role,
                model=model,
                spice_w_um=spice_w,
                spice_l_um=spice_l,
                source_file=str(args.source),
                source_fet_bboxes=[[fet.xlo, fet.ylo, fet.xhi, fet.yhi]],
                fet_count=1,
                local_bbox_um=um_bbox(layout),
                mag_file=mag_path.name,
            )
        )

    if args.include_periphery:
        source_root = args.source.parent
        for spec in EXTRA_PRIMITIVE_SOURCES:
            primitives.append(write_extra_primitive(source_root, args.out_dir, spec))

    inventory = {
        "source": str(args.source),
        "normalized_layers": LAYER_MAP,
        "rules": {
            "uses_6t_cell_as_block": False,
            "transistor_resize_allowed": False,
            "primitive_crop_clips_rectangles": False,
            "local_layers": sorted(LOCAL_DEVICE_LAYERS),
            "margin_magic_units": args.margin,
            "include_periphery": args.include_periphery,
            "extra_sources": EXTRA_PRIMITIVE_SOURCES if args.include_periphery else [],
        },
        "primitives": [asdict(primitive) for primitive in primitives],
    }
    (args.out_dir / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    write_markdown(primitives, args.out_dir / "inventory.md")

    for primitive in primitives:
        width, height, area = primitive.local_bbox_um
        print(
            f"{primitive.name:36s} {primitive.role:22s} "
            f"{primitive.model:10s} W={primitive.spice_w_um:.3f}um L={primitive.spice_l_um:.3f}um "
            f"bbox={width:.3f}um x {height:.3f}um = {area:.3f}um^2"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
