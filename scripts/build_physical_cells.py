#!/usr/bin/env python3
"""Build first extractable Detronyx SRAM physical leaf cells.

This is the layout-assembly path, not a wrapper around Timothy's 6T bitcell.
It reuses Timothy-derived device geometry with fixed W/L and only changes
placement, well enclosure, and pin labels needed by the new 10T/12T cells.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from extreme_compaction_search import LAYER_MAP, Rect, orientation_fns, read_magic
from extract_timothy_primitives import classify_fet, make_local_primitive


UNITS_PER_UM = 200.0
READ_STACK_SOURCE = "nmos_5p04310591302032_3v512x8m81.mag"
STRONG_WRITE_SOURCE = "nmos_5p04310591302010_3v512x8m81.mag"
SIX_T_SEED_CELL = "detronyx_tim_6t_seed_norm"
READ_STACK_CELL = "detronyx_tim_read_stack_0p53_2nfet"
TWELVE_T_SEED_CELL = "detronyx_12t_2w2r_seed"
TWELVE_T_RC1_CELL = "detronyx_12t_2w2r_rc1"
TWELVE_T_RC1_M3FREE_CELL = "detronyx_12t_2w2r_rc1_m3free"
TWELVE_T_RC6_PIN_ACCESS_CELL = "detronyx_12t_2w2r_rc6_pin_access"
TEN_T_SEED_CELL = "detronyx_10t_se_2w2r_seed"
TEN_T_RC1_CELL = "detronyx_10t_se_2w2r_rc1"
PHYSICAL_COMPARE_CELL = "detronyx_physical_seed_compare"

USEFUL_LAYERS = {
    "nfet",
    "pfet",
    "ndiff",
    "pdiff",
    "ndiffc",
    "pdiffc",
    "nsubdiff",
    "psubdiff",
    "nsubdiffcont",
    "psubdiffcont",
    "polysilicon",
    "polycontact",
    "metal1",
    "via1",
    "metal2",
    "via2",
    "metal3",
    "via3",
    "metal4",
    "via4",
    "metal5",
    "nwell",
    "pwell",
}

BASE_6T_LAYERS = {
    "nwell",
    "pwell",
    "nfet",
    "pfet",
    "ndiff",
    "pdiff",
    "ndiffc",
    "pdiffc",
    "polysilicon",
    "polycontact",
    "metal1",
    "via1",
    "metal2",
}


@dataclass(frozen=True)
class Label:
    layer: str
    x: int
    y: int
    text: str
    port: int


@dataclass(frozen=True)
class CellReport:
    cell: str
    source: str
    output_magic: str
    bbox_magic: list[int]
    bbox_um: list[float]
    rules: dict[str, object]
    labels: list[dict[str, object]]


def dims_um(bbox: tuple[int, int, int, int]) -> list[float]:
    xlo, ylo, xhi, yhi = bbox
    width = (xhi - xlo) / UNITS_PER_UM
    height = (yhi - ylo) / UNITS_PER_UM
    return [round(width, 6), round(height, 6), round(width * height, 6)]


def rect_centered(layer: str, x: int, y: int, w: int, h: int) -> Rect:
    return Rect(layer, x - w // 2, y - h // 2, x + (w + 1) // 2, y + (h + 1) // 2)


def translate(rects: list[Rect], dx: int, dy: int) -> list[Rect]:
    return [rect.translate(dx, dy) for rect in rects]


def bbox(rects: list[Rect]) -> tuple[int, int, int, int]:
    return (
        min(rect.xlo for rect in rects),
        min(rect.ylo for rect in rects),
        max(rect.xhi for rect in rects),
        max(rect.yhi for rect in rects),
    )


def shifted_to_origin(rects: list[Rect]) -> list[Rect]:
    xlo, ylo, _xhi, _yhi = bbox(rects)
    return translate(rects, -xlo, -ylo)


def shifted_rects_labels_to_origin(rects: list[Rect], labels: list[Label]) -> tuple[list[Rect], list[Label]]:
    xlo, ylo, _xhi, _yhi = bbox(rects)
    return (
        translate(rects, -xlo, -ylo),
        [Label(label.layer, label.x - xlo, label.y - ylo, label.text, label.port) for label in labels],
    )


def label_dict(label: Label) -> dict[str, object]:
    return {
        "layer": label.layer,
        "x": label.x,
        "y": label.y,
        "text": label.text,
        "port": label.port,
    }


def write_magic(
    path: Path,
    *,
    cell: str,
    tech: str,
    magscale: str,
    rects: list[Rect],
    labels: list[Label],
    properties: dict[str, str],
) -> None:
    by_layer: dict[str, list[Rect]] = {}
    for rect in rects:
        if rect.xlo == rect.xhi or rect.ylo == rect.yhi:
            continue
        by_layer.setdefault(rect.layer, []).append(rect)

    layer_order = [
        "nwell",
        "pwell",
        "nfet",
        "pfet",
        "ndiff",
        "pdiff",
        "ndiffc",
        "pdiffc",
        "nsubdiff",
        "psubdiff",
        "nsubdiffcont",
        "psubdiffcont",
        "polysilicon",
        "polycontact",
        "metal1",
        "via1",
        "metal2",
        "via2",
        "metal3",
        "via3",
        "metal4",
        "via4",
        "metal5",
    ]
    ordered_layers = [layer for layer in layer_order if layer in by_layer]
    ordered_layers.extend(sorted(layer for layer in by_layer if layer not in set(ordered_layers)))

    lines = [
        "magic",
        f"tech {tech}",
        f"magscale {magscale}",
        "timestamp 1780003000",
    ]
    for layer in ordered_layers:
        lines.append(f"<< {layer} >>")
        for rect in sorted(by_layer[layer], key=lambda r: (r.ylo, r.xlo, r.yhi, r.xhi)):
            lines.append(f"rect {rect.xlo} {rect.ylo} {rect.xhi} {rect.yhi}")

    if labels:
        lines.append("<< labels >>")
        for label in labels:
            lines.append(
                f"flabel {label.layer} {label.x} {label.y} {label.x} {label.y} "
                f"0 FreeSans 93 0 0 0 {label.text}"
            )
            lines.append(f"port {label.port} nsew")

    lines.append("<< properties >>")
    for key, value in properties.items():
        lines.append(f"string {key} {value}")
    lines.append("<< end >>")
    path.write_text("\n".join(lines) + "\n")


def make_read_stack_geometry(well_margin: int) -> tuple[list[Rect], list[Label], tuple[int, int, int, int]]:
    source_path = make_read_stack_geometry.tim_magic_dir / READ_STACK_SOURCE
    source = read_magic(source_path, READ_STACK_CELL)

    useful = [
        rect
        for rect in source.rects
        if rect.layer in USEFUL_LAYERS and not rect.layer.startswith("error")
    ]
    if not useful:
        raise ValueError(f"{source_path}: no usable read-stack geometry parsed")

    uxlo, uylo, uxhi, uyhi = bbox(useful)
    useful_width = uxhi - uxlo
    useful_height = uyhi - uylo
    rects = translate(useful, -uxlo + well_margin, -uylo + well_margin)

    total_width = useful_width + 2 * well_margin
    total_height = useful_height + 2 * well_margin
    rects.insert(0, Rect("pwell", 0, 0, total_width, total_height))

    labels = [
        Label("ndiffc", well_margin + 36, well_margin + 97, "RBL", 1),
        Label("ndiffc", well_margin + 196, well_margin + 97, "MID", 2),
        Label("ndiffc", well_margin + 357, well_margin + 97, "VSS", 3),
        Label("polysilicon", well_margin + 116, well_margin + 172, "RWL", 4),
        Label("polysilicon", well_margin + 276, well_margin + 172, "QG", 5),
    ]
    return rects, labels, bbox(rects)


make_read_stack_geometry.tim_magic_dir = Path(".")


def make_strong_write_geometry(well_margin: int) -> tuple[list[Rect], list[Label], tuple[int, int, int, int]]:
    source_path = make_strong_write_geometry.tim_magic_dir / STRONG_WRITE_SOURCE
    source = read_magic(source_path, "detronyx_tim_strong_write_1p055")
    useful = [
        rect
        for rect in source.rects
        if rect.layer in USEFUL_LAYERS and not rect.layer.startswith("error")
    ]
    if not useful:
        raise ValueError(f"{source_path}: no usable strong-write geometry parsed")

    uxlo, uylo, uxhi, uyhi = bbox(useful)
    useful_width = uxhi - uxlo
    useful_height = uyhi - uylo
    rects = translate(useful, -uxlo + well_margin, -uylo + well_margin)
    total_width = useful_width + 2 * well_margin
    total_height = useful_height + 2 * well_margin
    rects.insert(0, Rect("pwell", 0, 0, total_width, total_height))

    # Coordinates from Tim's 1.055um/L=0.28um single NFET after source shift.
    labels = [
        Label("ndiffc", well_margin + 48, well_margin + 149, "WQ", 1),
        Label("ndiffc", well_margin + 184, well_margin + 149, "WBL", 2),
        Label("polysilicon", well_margin + 116, well_margin + 277, "WWL", 3),
    ]
    return rects, labels, bbox(rects)


make_strong_write_geometry.tim_magic_dir = Path(".")


def moved_labels(labels: list[Label], dx: int, dy: int, rename: dict[str, str], port_base: int) -> list[Label]:
    moved: list[Label] = []
    for index, label in enumerate(labels):
        moved.append(
            Label(
                label.layer,
                label.x + dx,
                label.y + dy,
                rename.get(label.text, label.text),
                port_base + index,
            )
        )
    return moved


def transform_rects_and_labels(
    rects: list[Rect],
    labels: list[Label],
    orientation: str,
) -> tuple[list[Rect], list[Label]]:
    transform = orientation_fns()[orientation]
    transformed_rects = [rect.transform(transform) for rect in rects]
    xlo, ylo, _xhi, _yhi = bbox(transformed_rects)
    transformed_rects = translate(transformed_rects, -xlo, -ylo)
    transformed_labels = []
    for label in labels:
        x, y = transform(label.x, label.y)
        transformed_labels.append(Label(label.layer, x - xlo, y - ylo, label.text, label.port))
    return transformed_rects, transformed_labels


def build_read_stack(tim_magic_dir: Path, out_dir: Path, well_margin: int) -> CellReport:
    source_path = tim_magic_dir / READ_STACK_SOURCE
    make_read_stack_geometry.tim_magic_dir = tim_magic_dir
    rects, labels, cell_bbox = make_read_stack_geometry(well_margin)
    source = read_magic(source_path, READ_STACK_CELL)

    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{READ_STACK_CELL}.mag"
    write_magic(
        mag_path,
        cell=READ_STACK_CELL,
        tech=source.tech,
        magscale=source.magscale,
        rects=rects,
        labels=labels,
        properties={
            "DETRONYX_PHYSICAL_CELL": READ_STACK_CELL,
            "DETRONYX_SOURCE": READ_STACK_SOURCE,
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_REPURPOSED_TOPOLOGY": "RBL-RWL-MID-QG-VSS",
        },
    )

    return CellReport(
        cell=READ_STACK_CELL,
        source=str(source_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=dims_um(cell_bbox),
        rules={
            "uses_6t_cell_as_block": False,
            "transistor_resize_allowed": False,
            "source_layers_normalized": LAYER_MAP,
            "dropped_error_layers": True,
            "added_pwell_context": True,
            "well_margin_magic_units": well_margin,
            "topology": "RBL -- [gate=RWL] -- MID -- [gate=QG] -- VSS",
        },
        labels=[label_dict(label) for label in labels],
    )


def build_6t_seed(seed_path: Path, out_dir: Path) -> CellReport:
    source = read_magic(seed_path, SIX_T_SEED_CELL)
    rects = [
        rect
        for rect in source.rects
        if rect.layer in USEFUL_LAYERS and not rect.layer.startswith("error")
    ]
    rects = shifted_to_origin(rects)
    cell_bbox = bbox(rects)

    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{SIX_T_SEED_CELL}.mag"
    write_magic(
        mag_path,
        cell=SIX_T_SEED_CELL,
        tech=source.tech,
        magscale=source.magscale,
        rects=rects,
        labels=[],
        properties={
            "DETRONYX_PHYSICAL_CELL": SIX_T_SEED_CELL,
            "DETRONYX_SOURCE": seed_path.name,
            "DETRONYX_REFERENCE_ONLY": "true",
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
        },
    )

    return CellReport(
        cell=SIX_T_SEED_CELL,
        source=str(seed_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=dims_um(cell_bbox),
        rules={
            "reference_only": True,
            "timothy_6t_seed": True,
            "transistor_resize_allowed": False,
            "source_layers_normalized": LAYER_MAP,
        },
        labels=[],
    )


def trimmed_write_access_poly(rects: list[Rect], poly_stub: int) -> list[Rect]:
    nfets = [rect for rect in rects if rect.layer == "nfet"]
    if len(nfets) != 1:
        raise ValueError(f"expected one write-access NFET, got {len(nfets)}")
    gate = nfets[0]
    out: list[Rect] = []
    for rect in rects:
        if rect.layer != "polysilicon":
            out.append(rect)
            continue
        ylo = max(rect.ylo, gate.ylo)
        yhi = min(rect.yhi, gate.yhi)
        if ylo >= yhi:
            continue
        if rect.xhi <= gate.xlo:
            xlo = max(rect.xlo, gate.xlo - poly_stub)
            xhi = rect.xhi
        elif rect.xlo >= gate.xhi:
            xlo = rect.xlo
            xhi = min(rect.xhi, gate.xhi + poly_stub)
        else:
            xlo = rect.xlo
            xhi = rect.xhi
        if xlo < xhi:
            out.append(Rect("polysilicon", xlo, ylo, xhi, yhi))
    return shifted_to_origin(out)


def write_access_pair_from_tim_seed(
    seed_path: Path,
    margin: int,
    group_gap: int = 40,
    trim_poly_stub: int | None = None,
) -> list[Rect]:
    source = read_magic(seed_path, "tim6t_write_access_source")
    access_layouts = []
    role_index = 0
    for fet in sorted((r for r in source.rects if r.layer == "nfet"), key=lambda r: (r.ylo, r.xlo)):
        role, _model, _spice_w, _spice_l = classify_fet(fet)
        if role != "write_access_nfet":
            continue
        role_index += 1
        access_layouts.append(make_local_primitive("tim", role, role_index, source, fet, margin))
    if len(access_layouts) != 2:
        raise ValueError(f"{seed_path}: expected two write-access NFET primitives, got {len(access_layouts)}")

    rects: list[Rect] = []
    x_cursor = 0
    max_height = 0
    for layout in access_layouts:
        local = [r for r in layout.rects if r.layer in BASE_6T_LAYERS]
        local = shifted_to_origin(local)
        if trim_poly_stub is not None:
            local = trimmed_write_access_poly(local, trim_poly_stub)
        lxlo, lylo, lxhi, lyhi = bbox(local)
        rects.extend(translate(local, x_cursor - lxlo, -lylo))
        x_cursor += (lxhi - lxlo) + group_gap
        max_height = max(max_height, lyhi - lylo)
    rects.insert(0, Rect("pwell", 0, 0, max(x_cursor - group_gap, 0), max_height))
    return rects


def add_write_access_pair_pin_straps(rects: list[Rect]) -> list[Rect]:
    """Add local route-facing straps for the compact differential write pair."""

    return [
        *rects,
        Rect("metal1", 55, 0, 101, 80),
        Rect("metal1", 203, 0, 249, 80),
        Rect("polycontact", 129, 95, 175, 141),
        Rect("metal1", 104, 95, 200, 141),
    ]


def latch_primitives_from_tim_seed(seed_path: Path, margin: int) -> list[tuple[str, list[Rect]]]:
    source = read_magic(seed_path, "tim6t_latch_source")
    wanted = {
        "latch_pulldown_nfet": 0,
        "latch_pullup_pfet": 0,
    }
    out: list[tuple[str, list[Rect]]] = []
    for fet in sorted((r for r in source.rects if r.layer in {"nfet", "pfet"}), key=lambda r: (r.layer, r.ylo, r.xlo)):
        role, _model, _spice_w, _spice_l = classify_fet(fet)
        if role not in wanted:
            continue
        wanted[role] += 1
        layout = make_local_primitive("tim", role, wanted[role], source, fet, margin)
        local = [r for r in layout.rects if r.layer in BASE_6T_LAYERS]
        out.append((role, shifted_to_origin(local)))

    if wanted["latch_pulldown_nfet"] != 2 or wanted["latch_pullup_pfet"] != 2:
        raise ValueError(f"{seed_path}: failed to extract 2 pull-down and 2 pull-up latch primitives")
    return out


def build_10t_seed(
    seed_path: Path,
    tim_magic_dir: Path,
    out_dir: Path,
    well_margin: int,
    gap: int,
) -> CellReport:
    latch = latch_primitives_from_tim_seed(seed_path, margin=80)
    pulldowns = [rects for role, rects in latch if role == "latch_pulldown_nfet"]
    pullups = [rects for role, rects in latch if role == "latch_pullup_pfet"]

    def row_place(groups: list[list[Rect]], x0: int, y0: int, group_gap: int) -> tuple[list[Rect], int, int]:
        placed: list[Rect] = []
        x_cursor = x0
        row_height = 0
        for group in groups:
            gxlo, gylo, gxhi, gyhi = bbox(group)
            placed.extend(translate(group, x_cursor - gxlo, y0 - gylo))
            width = gxhi - gxlo
            row_height = max(row_height, gyhi - gylo)
            x_cursor += width + group_gap
        return placed, x_cursor - group_gap - x0, row_height

    rects: list[Rect] = []
    n_row, n_width, n_height = row_place(pulldowns, 0, 0, gap)
    p_row_y = n_height + gap
    p_row, p_width, p_height = row_place(pullups, 0, p_row_y, gap)
    latch_width = max(n_width, p_width)
    latch_height = p_row_y + p_height
    rects.extend(n_row)
    rects.extend(p_row)
    rects.insert(0, Rect("pwell", 0, 0, latch_width, n_height + well_margin))
    rects.insert(0, Rect("nwell", 0, p_row_y - well_margin, latch_width, latch_height + well_margin))

    make_strong_write_geometry.tim_magic_dir = tim_magic_dir
    write_rects, write_labels, write_bbox = make_strong_write_geometry(well_margin)
    write_width = write_bbox[2] - write_bbox[0]
    write_height = write_bbox[3] - write_bbox[1]

    make_read_stack_geometry.tim_magic_dir = tim_magic_dir
    read_rects, read_labels, read_bbox = make_read_stack_geometry(well_margin)
    read_width = read_bbox[2] - read_bbox[0]
    read_height = read_bbox[3] - read_bbox[1]

    write_x = latch_width + gap
    write_read_gap = max(gap, 40)
    read_x = write_x + write_width + write_read_gap
    write0_y = 0
    write_port_gap = max(gap, 40)
    write1_y = write_height + write_port_gap
    read0_y = 0
    read_port_gap = max(gap, 40)
    read1_y = read_height + read_port_gap

    rects.extend(translate(write_rects, write_x, write0_y))
    rects.extend(translate(write_rects, write_x, write1_y))
    rects.extend(translate(read_rects, read_x, read0_y))
    rects.extend(translate(read_rects, read_x, read1_y))
    rects.append(Rect("metal1", read_x + 374, read0_y + 177, read_x + 420, read1_y + 97))

    labels: list[Label] = []
    labels.extend(
        moved_labels(
            write_labels,
            write_x,
            write0_y,
            {"WQ": "W0_Q", "WBL": "W0_BL", "WWL": "W0_WL"},
            1,
        )
    )
    labels.extend(
        moved_labels(
            write_labels,
            write_x,
            write1_y,
            {"WQ": "W1_Q", "WBL": "W1_BL", "WWL": "W1_WL"},
            8,
        )
    )
    labels.extend(
        moved_labels(
            read_labels,
            read_x,
            read0_y,
            {"RBL": "R0_RBL", "MID": "R0_MID", "RWL": "R0_RWL", "QG": "R0_QG"},
            16,
        )
    )
    labels.extend(
        moved_labels(
            read_labels,
            read_x,
            read1_y,
            {"RBL": "R1_RBL", "MID": "R1_MID", "RWL": "R1_RWL", "QG": "R1_QG"},
            32,
        )
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{TEN_T_SEED_CELL}.mag"
    cell_bbox = bbox(rects)
    write_magic(
        mag_path,
        cell=TEN_T_SEED_CELL,
        tech="gf180mcuD",
        magscale="1 10",
        rects=rects,
        labels=labels,
        properties={
            "DETRONYX_PHYSICAL_CELL": TEN_T_SEED_CELL,
            "DETRONYX_SOURCE": seed_path.name,
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_ROUTING_STATUS": "seed_device_placement_not_final_bitcell",
        },
    )

    width, height, area = dims_um(cell_bbox)
    return CellReport(
        cell=TEN_T_SEED_CELL,
        source=str(seed_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=[width, height, area],
        rules={
            "uses_6t_cell_as_block": False,
            "latch_built_from_tim_device_primitives": True,
            "single_ended_write_devices": 2,
            "strong_write_source": STRONG_WRITE_SOURCE,
            "read_ports_added_from_tim_nf2_read_stack_primitives": 2,
            "transistor_resize_allowed": False,
            "routing_status": "seed device placement; latch/write/read are not final compact routed bitcell yet",
            "gap_magic_units": gap,
            "write_port_gap_magic_units": write_port_gap,
            "write_read_gap_magic_units": write_read_gap,
            "read_port_gap_magic_units": read_port_gap,
            "well_margin_magic_units": well_margin,
            "latch_bbox_um": dims_um((0, 0, latch_width, latch_height)),
            "strong_write_bbox_um": dims_um((0, 0, write_width, write_height)),
            "read_stack_bbox_um": dims_um((0, 0, read_width, read_height)),
        },
        labels=[label_dict(label) for label in labels],
    )


def build_10t_rc1(
    seed_path: Path,
    tim_magic_dir: Path,
    out_dir: Path,
    well_margin: int,
    gap: int,
) -> CellReport:
    """Build the current best 10T release-candidate placement.

    This promotes the DRC-clean search candidate
    `columns_g0_r0_r90_r0`: latch at r0, strong write devices at r90,
    read stacks at r0, with zero inter-block gap by default.
    """

    latch = latch_primitives_from_tim_seed(seed_path, margin=80)
    pulldowns = [rects for role, rects in latch if role == "latch_pulldown_nfet"]
    pullups = [rects for role, rects in latch if role == "latch_pullup_pfet"]

    def row_place(groups: list[list[Rect]], x0: int, y0: int, group_gap: int) -> tuple[list[Rect], int, int]:
        placed: list[Rect] = []
        x_cursor = x0
        row_height = 0
        for group in groups:
            gxlo, gylo, gxhi, gyhi = bbox(group)
            placed.extend(translate(group, x_cursor - gxlo, y0 - gylo))
            width = gxhi - gxlo
            row_height = max(row_height, gyhi - gylo)
            x_cursor += width + group_gap
        return placed, x_cursor - group_gap - x0, row_height

    latch_rects: list[Rect] = []
    n_row, n_width, n_height = row_place(pulldowns, 0, 0, gap)
    p_row_y = n_height + gap
    p_row, p_width, p_height = row_place(pullups, 0, p_row_y, gap)
    latch_width = max(n_width, p_width)
    latch_height = p_row_y + p_height
    latch_rects.extend(n_row)
    latch_rects.extend(p_row)
    latch_rects.insert(0, Rect("pwell", 0, 0, latch_width, n_height + well_margin))
    latch_rects.insert(0, Rect("nwell", 0, p_row_y - well_margin, latch_width, latch_height + well_margin))
    latch_rects = shifted_to_origin(latch_rects)
    lxlo, lylo, lxhi, lyhi = bbox(latch_rects)
    latch_width = lxhi - lxlo
    latch_height = lyhi - lylo

    make_strong_write_geometry.tim_magic_dir = tim_magic_dir
    write_rects, write_labels, _write_bbox = make_strong_write_geometry(well_margin)
    write_rects, write_labels = transform_rects_and_labels(write_rects, write_labels, "r90")
    wxlo, wylo, wxhi, wyhi = bbox(write_rects)
    write_width = wxhi - wxlo
    write_height = wyhi - wylo

    make_read_stack_geometry.tim_magic_dir = tim_magic_dir
    read_rects, read_labels, _read_bbox = make_read_stack_geometry(well_margin)
    read_rects, read_labels = transform_rects_and_labels(read_rects, read_labels, "r0")
    rxlo, rylo, rxhi, ryhi = bbox(read_rects)
    read_width = rxhi - rxlo
    read_height = ryhi - rylo

    write_x = latch_width + gap
    write_read_gap = max(gap, 40)
    read_x = write_x + write_width + write_read_gap
    write0_y = 0
    write_port_gap = max(gap, 40)
    write1_y = write_height + write_port_gap
    read0_y = 0
    read_port_gap = max(gap, 40)
    read1_y = read_height + read_port_gap

    rects: list[Rect] = []
    rects.extend(latch_rects)
    rects.extend(translate(write_rects, write_x, write0_y))
    rects.extend(translate(write_rects, write_x, write1_y))
    rects.extend(translate(read_rects, read_x, read0_y))
    rects.extend(translate(read_rects, read_x, read1_y))
    rects.append(Rect("metal1", read_x + 374, read0_y + 177, read_x + 420, read1_y + 97))

    labels: list[Label] = []
    labels.extend(
        moved_labels(
            write_labels,
            write_x,
            write0_y,
            {"WQ": "W0_Q", "WBL": "W0_BL", "WWL": "W0_WL"},
            1,
        )
    )
    labels.extend(
        moved_labels(
            write_labels,
            write_x,
            write1_y,
            {"WQ": "W1_Q", "WBL": "W1_BL", "WWL": "W1_WL"},
            8,
        )
    )
    labels.extend(
        moved_labels(
            read_labels,
            read_x,
            read0_y,
            {"RBL": "R0_RBL", "MID": "R0_MID", "RWL": "R0_RWL", "QG": "R0_QG"},
            16,
        )
    )
    labels.extend(
        moved_labels(
            read_labels,
            read_x,
            read1_y,
            {"RBL": "R1_RBL", "MID": "R1_MID", "RWL": "R1_RWL", "QG": "R1_QG"},
            32,
        )
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{TEN_T_RC1_CELL}.mag"
    cell_bbox = bbox(rects)
    write_magic(
        mag_path,
        cell=TEN_T_RC1_CELL,
        tech="gf180mcuD",
        magscale="1 10",
        rects=rects,
        labels=labels,
        properties={
            "DETRONYX_PHYSICAL_CELL": TEN_T_RC1_CELL,
            "DETRONYX_SOURCE": seed_path.name,
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_PLACEMENT_PATTERN": "columns_g0_r0_r90_r0",
            "DETRONYX_ROUTING_STATUS": "release_candidate_seed_needs_pin_axis_audit_and_q_routing",
        },
    )

    width, height, area = dims_um(cell_bbox)
    return CellReport(
        cell=TEN_T_RC1_CELL,
        source=str(seed_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=[width, height, area],
        rules={
            "release_candidate": True,
            "uses_6t_cell_as_block": False,
            "latch_orientation": "r0",
            "write_orientation": "r90",
            "read_orientation": "r0",
            "placement_pattern": "columns",
            "single_ended_write_devices": 2,
            "strong_write_source": STRONG_WRITE_SOURCE,
            "read_ports_added_from_tim_nf2_read_stack_primitives": 2,
            "transistor_resize_allowed": False,
            "gap_magic_units": gap,
            "write_port_gap_magic_units": write_port_gap,
            "write_read_gap_magic_units": write_read_gap,
            "read_port_gap_magic_units": read_port_gap,
            "well_margin_magic_units": well_margin,
            "latch_bbox_um": dims_um((0, 0, latch_width, latch_height)),
            "strong_write_rotated_bbox_um": dims_um((0, 0, write_width, write_height)),
            "read_stack_bbox_um": dims_um((0, 0, read_width, read_height)),
        },
        labels=[label_dict(label) for label in labels],
    )


def build_12t_seed(
    seed_path: Path,
    tim_magic_dir: Path,
    out_dir: Path,
    well_margin: int,
    gap: int,
) -> CellReport:
    latch = latch_primitives_from_tim_seed(seed_path, margin=80)
    pulldowns = [rects for role, rects in latch if role == "latch_pulldown_nfet"]
    pullups = [rects for role, rects in latch if role == "latch_pullup_pfet"]

    def row_place(groups: list[list[Rect]], x0: int, y0: int, group_gap: int) -> tuple[list[Rect], int, int]:
        placed: list[Rect] = []
        x_cursor = x0
        row_height = 0
        for group in groups:
            gxlo, gylo, gxhi, gyhi = bbox(group)
            placed.extend(translate(group, x_cursor - gxlo, y0 - gylo))
            width = gxhi - gxlo
            row_height = max(row_height, gyhi - gylo)
            x_cursor += width + group_gap
        return placed, x_cursor - group_gap - x0, row_height

    rects: list[Rect] = []
    n_row, n_width, n_height = row_place(pulldowns, 0, 0, gap)
    p_row_y = n_height + gap
    p_row, p_width, p_height = row_place(pullups, 0, p_row_y, gap)
    latch_width = max(n_width, p_width)
    latch_height = p_row_y + p_height
    rects.extend(n_row)
    rects.extend(p_row)
    rects.insert(0, Rect("pwell", 0, 0, latch_width, n_height + well_margin))
    rects.insert(0, Rect("nwell", 0, p_row_y - well_margin, latch_width, latch_height + well_margin))

    make_read_stack_geometry.tim_magic_dir = tim_magic_dir
    read_rects, read_labels, read_bbox = make_read_stack_geometry(well_margin)
    read_width = read_bbox[2] - read_bbox[0]
    read_height = read_bbox[3] - read_bbox[1]

    write_pair = write_access_pair_from_tim_seed(seed_path, margin=80)
    write_pair = shifted_to_origin(write_pair)
    wxlo, wylo, wxhi, wyhi = bbox(write_pair)
    write_width = wxhi - wxlo
    write_height = wyhi - wylo

    write_x = latch_width + gap
    read_x = write_x + write_width + gap
    write0_y = 0
    write1_y = write_height + gap
    read0_y = 0
    read_port_gap = max(gap, 40)
    read1_y = read_height + read_port_gap

    rects.extend(translate(write_pair, write_x, write0_y))
    rects.extend(translate(write_pair, write_x, write1_y))
    rects.extend(translate(read_rects, read_x, read0_y))
    rects.extend(translate(read_rects, read_x, read1_y))
    # Tie the two added read-stack VSS contacts with real M1 geometry.  This
    # avoids relying on same-name disconnected labels during extraction.
    rects.append(Rect("metal1", read_x + 374, read0_y + 177, read_x + 420, read1_y + 97))

    labels: list[Label] = []
    labels.extend(
        moved_labels(
            read_labels,
            read_x,
            read0_y,
            {"RBL": "R0_RBL", "MID": "R0_MID", "RWL": "R0_RWL", "QG": "R0_QG"},
            1,
        )
    )
    labels.extend(
        moved_labels(
            read_labels,
            read_x,
            read1_y,
            {"RBL": "R1_RBL", "MID": "R1_MID", "RWL": "R1_RWL", "QG": "R1_QG"},
            16,
        )
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{TWELVE_T_SEED_CELL}.mag"
    cell_bbox = bbox(rects)
    write_magic(
        mag_path,
        cell=TWELVE_T_SEED_CELL,
        tech="gf180mcuD",
        magscale="1 10",
        rects=rects,
        labels=labels,
        properties={
            "DETRONYX_PHYSICAL_CELL": TWELVE_T_SEED_CELL,
            "DETRONYX_SOURCE": seed_path.name,
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_ROUTING_STATUS": "seed_device_placement_not_final_bitcell",
        },
    )

    width, height, area = dims_um(cell_bbox)
    return CellReport(
        cell=TWELVE_T_SEED_CELL,
        source=str(seed_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=[width, height, area],
        rules={
            "uses_6t_cell_as_block": False,
            "latch_built_from_tim_device_primitives": True,
            "differential_write_access_devices": 4,
            "write_ports_added_from_tim_access_primitives": 2,
            "read_ports_added_from_tim_nf2_read_stack_primitives": 2,
            "transistor_resize_allowed": False,
            "routing_status": "seed device placement; write1/read gates are not final compact routed bitcell yet",
            "gap_magic_units": gap,
            "read_port_gap_magic_units": read_port_gap,
            "well_margin_magic_units": well_margin,
            "latch_bbox_um": dims_um((0, 0, latch_width, latch_height)),
            "read_stack_bbox_um": dims_um((0, 0, read_width, read_height)),
            "write_pair_bbox_um": dims_um((0, 0, write_width, write_height)),
        },
        labels=[label_dict(label) for label in labels],
    )


def write_access_pair_labels(dx: int, dy: int, prefix: str, port_base: int) -> list[Label]:
    return [
        Label("metal1", dx + 78, dy + 40, f"{prefix}_BL", port_base + 0),
        Label("metal1", dx + 226, dy + 40, f"{prefix}_BR", port_base + 1),
        Label("ndiff", dx + 76, dy + 200, f"{prefix}_Q", port_base + 2),
        Label("ndiff", dx + 228, dy + 200, f"{prefix}_QB", port_base + 3),
        Label("metal1", dx + 152, dy + 118, f"{prefix}_WL", port_base + 4),
    ]


def write_access_pair_blackbox_labels(dx: int, dy: int, prefix: str, port_base: int) -> list[Label]:
    return [
        Label("metal1", dx + 78, dy + 40, f"{prefix}_BL", port_base + 0),
        Label("metal1", dx + 226, dy + 40, f"{prefix}_BR", port_base + 1),
        Label("metal1", dx + 152, dy + 118, f"{prefix}_WL", port_base + 2),
    ]


def add_read_gate_contact_pins(rects: list[Rect], read_x: int, read_y: int) -> list[Rect]:
    """Promote read-stack polysilicon gates to local metal1 pins."""

    return [
        *rects,
        Rect("polysilicon", read_x + 88, read_y + 150, read_x + 144, read_y + 196),
        Rect("polysilicon", read_x + 248, read_y + 150, read_x + 304, read_y + 196),
        Rect("polycontact", read_x + 93, read_y + 150, read_x + 139, read_y + 196),
        Rect("polycontact", read_x + 253, read_y + 150, read_x + 299, read_y + 196),
        Rect("metal1", read_x + 80, read_y + 150, read_x + 152, read_y + 196),
        Rect("metal1", read_x + 240, read_y + 150, read_x + 312, read_y + 196),
    ]


def add_12t_rc1_blackbox_routes(
    rects: list[Rect],
    *,
    write_x: int,
    write0_y: int,
    write1_y: int,
    read_x: int,
    read0_y: int,
    read1_y: int,
    qg_route_style: str = "metal3",
) -> list[Rect]:
    """Route RC1 storage nodes internally and expose only macro-facing pins.

    The right storage node is the routed Q node. The left storage node is QB.
    This keeps the two read-gate routes short and leaves Q/QB/W*_Q/R*_QG off
    the external bitcell interface.
    """

    w0_q = (write_x + 55, write0_y + 174, write_x + 101, write0_y + 220)
    w0_qb = (write_x + 203, write0_y + 174, write_x + 249, write0_y + 220)
    w0_qb_bus = (write_x + 203, write0_y + 220, write_x + 249, write0_y + 266)
    w1_q = (write_x + 55, write1_y + 180, write_x + 101, write1_y + 226)
    w1_qb = (write_x + 203, write1_y + 180, write_x + 249, write1_y + 226)

    q_right_xlo, q_right_xhi = 431, 477
    qb_left_xlo, qb_left_xhi = 7, 53
    q_route_ylo, q_route_yhi = write0_y + 174, write0_y + 220
    qb_route_ylo, qb_route_yhi = write0_y + 174, write0_y + 220
    q1_route_ylo, q1_route_yhi = write1_y + 180, write1_y + 226
    qb1_route_ylo, qb1_route_yhi = write1_y + 180, write1_y + 226

    read0_q_tap = (q_right_xlo, read0_y + 128, q_right_xhi, read0_y + 174)
    read0_qg = (read_x + 253, read0_y + 150, read_x + 299, read0_y + 196)
    read1_qg = (read_x + 253, read1_y + 150, read_x + 299, read1_y + 196)

    routed = [
        *rects,
        # Cross-coupled 4T latch. Middle diffusion/contact islands are rails;
        # left/right edge diffusion islands are the complementary storage nodes.
        Rect("metal1", qb_left_xlo, 128, qb_left_xhi, 512),
        Rect("metal1", q_right_xlo, 128, q_right_xhi, 512),
        Rect("polysilicon", 323, 250, 402, 287),
        Rect("metal1", q_right_xlo, 215, q_right_xhi, 261),
        Rect("metal1", 102, 215, q_right_xhi, 261),
        Rect("metal1", qb_left_xlo, 287, qb_left_xhi, 333),
        Rect("metal1", qb_left_xlo, 287, 382, 333),
        # Local VDD/VSS rails for the blackbox leaf.
        Rect("metal1", 167, 472, 317, 529),
        Rect("metal1", 167, 31, 317, 103),
        Rect("via1", 167, 57, 213, 103),
        Rect("metal2", 167, 57, read_x + 380, 103),
        Rect("metal1", read_x + 334, read0_y + 57, read_x + 380, read1_y + 137),
        Rect("via1", read_x + 334, read0_y + 57, read_x + 380, read0_y + 103),
        # Write-access internal diffusion contacts.
        Rect("ndiffc", *w0_q),
        Rect("metal1", *w0_q),
        Rect("ndiffc", *w0_qb),
        Rect("metal1", w0_qb[0], w0_qb[1], w0_qb[2], w0_qb_bus[3]),
        Rect("ndiffc", *w1_q),
        Rect("metal1", *w1_q),
        Rect("ndiffc", *w1_qb),
        Rect("metal1", *w1_qb),
        # Q to write ports: short right-side metal1 hops.
        Rect("metal1", q_right_xlo, q_route_ylo, w0_q[2], q_route_yhi),
        Rect("metal1", q_right_xlo, q1_route_ylo, w1_q[2], q1_route_yhi),
        # QB to write ports: metal2 hops so it can cross the Q-side M1 hops.
        Rect("via1", qb_left_xlo, w0_qb_bus[1], qb_left_xhi, w0_qb_bus[3]),
        Rect("via1", *w0_qb_bus),
        Rect("metal2", qb_left_xlo, w0_qb_bus[1], w0_qb_bus[2], w0_qb_bus[3]),
        Rect("via1", qb_left_xlo, qb1_route_ylo, qb_left_xhi, qb1_route_yhi),
        Rect("via1", w1_qb[0], qb1_route_ylo, w1_qb[2], qb1_route_yhi),
        Rect("metal2", qb_left_xlo, qb1_route_ylo, w1_qb[2], qb1_route_yhi),
    ]
    if qg_route_style == "metal3":
        routed.extend(
            [
                # Q to both read QG gates. Metal3 avoids accidental shorts across
                # write-data contacts and keeps active bitline/RWL coupling lower.
                Rect("via1", *read0_q_tap),
                Rect("metal2", *read0_q_tap),
                Rect("via2", *read0_q_tap),
                Rect("via1", read0_qg[0], read0_qg[1], read0_qg[2], read0_qg[3]),
                Rect("metal2", read0_qg[0], read0_qg[1], read0_qg[2], read0_qg[3]),
                Rect("via2", read0_qg[0], read0_qg[1], read0_qg[2], read0_qg[3]),
                Rect("metal3", read0_q_tap[0], read0_q_tap[1], read0_qg[2], read0_q_tap[3]),
                Rect("via1", q_right_xlo, read1_qg[1], q_right_xhi, read1_qg[3]),
                Rect("metal2", q_right_xlo, read1_qg[1], q_right_xhi, read1_qg[3]),
                Rect("via2", q_right_xlo, read1_qg[1], q_right_xhi, read1_qg[3]),
                Rect("via1", read1_qg[0], read1_qg[1], read1_qg[2], read1_qg[3]),
                Rect("metal2", read1_qg[0], read1_qg[1], read1_qg[2], read1_qg[3]),
                Rect("via2", read1_qg[0], read1_qg[1], read1_qg[2], read1_qg[3]),
                Rect("metal3", q_right_xlo, read1_qg[1], read1_qg[2], read1_qg[3]),
            ]
        )
    elif qg_route_style == "m3free_m2_spine":
        q_tap = (q_right_xlo, read0_y + 322, q_right_xhi, read0_y + 368)
        qg_bus = (read0_qg[0], read0_qg[1], read0_qg[2], read1_qg[3])
        spine = (q_tap[0], q_tap[1], read1_qg[2], q_tap[3])
        routed.extend(
            [
                # M3-free experiment: move the internal Q-to-read-gate route
                # onto a high M2 spine.  This keeps M3 empty inside the leaf so
                # RC4/RC6 tile straps can use it as the first shared signal
                # routing layer.
                Rect("via1", *q_tap),
                Rect("metal2", *q_tap),
                Rect("metal2", *spine),
                Rect("via1", read0_qg[0], read0_qg[1], read0_qg[2], read0_qg[3]),
                Rect("metal2", read0_qg[0], read0_qg[1], read0_qg[2], read0_qg[3]),
                Rect("via1", read1_qg[0], read1_qg[1], read1_qg[2], read1_qg[3]),
                Rect("metal2", read1_qg[0], read1_qg[1], read1_qg[2], read1_qg[3]),
                Rect("metal2", *qg_bus),
            ]
        )
    else:
        raise ValueError(f"unknown qg_route_style {qg_route_style!r}")
    return routed


def add_compact_m1_to_m3_stack(rects: list[Rect], x: int, y: int, *, landing_m1: bool = True) -> None:
    if landing_m1:
        rects.append(rect_centered("metal1", x, y, 72, 72))
    rects.append(rect_centered("via1", x, y, 44, 44))
    rects.append(rect_centered("metal2", x, y, 66, 66))
    rects.append(rect_centered("via2", x, y, 44, 44))
    rects.append(rect_centered("metal3", x, y, 56, 56))


def add_compact_m2_to_m3_stack(rects: list[Rect], x: int, y: int, *, landing_m2: bool = True) -> None:
    if landing_m2:
        rects.append(rect_centered("metal2", x, y, 66, 66))
    rects.append(rect_centered("via2", x, y, 44, 44))
    rects.append(rect_centered("metal3", x, y, 56, 56))


def add_local_m1_pin_access_to_m3(
    rects: list[Rect],
    *,
    source_x: int,
    source_y: int,
    access_x: int,
    access_y: int,
    source_layer: str = "metal1",
) -> None:
    """Route one leaf pin to a dedicated M3 access point.

    The access point is intentionally outside the dense source-pin label.  This
    avoids dropping via1/metal2 on top of existing RC1 M1/M2 leaf contacts.
    """

    route_w = 46
    if source_layer == "ndiffc":
        rects.append(rect_centered("metal1", source_x, source_y, 74, 74))
    elif source_layer != "metal1":
        raise ValueError(f"unsupported local M1 pin access layer: {source_layer}")
    if source_x != access_x:
        rects.append(Rect("metal1", min(source_x, access_x), source_y - route_w // 2, max(source_x, access_x), source_y + (route_w + 1) // 2))
    if source_y != access_y:
        rects.append(Rect("metal1", access_x - route_w // 2, min(source_y, access_y), access_x + (route_w + 1) // 2, max(source_y, access_y)))
    add_compact_m1_to_m3_stack(rects, access_x, access_y, landing_m1=True)


def add_12t_rc6_pin_access_layer(
    rects: list[Rect],
    *,
    write_x: int,
    write0_y: int,
    write1_y: int,
    read_x: int,
    read0_y: int,
    read1_y: int,
) -> tuple[list[Rect], list[Label]]:
    """Add honest M3 pin-access points to the M3-free RC1 leaf.

    These are not macro routes.  They are leaf-local access cuts placed away
    from dense M1/M2 source labels so the tile router can start from M3 without
    creating hidden shorts through the bitcell internals.
    """

    rects = [*rects]
    specs = [
        ("W0_BL", "metal1", write_x + 78, write0_y + 40, write_x + 78, write0_y - 80, 1),
        ("W0_BR", "metal1", write_x + 226, write0_y + 40, write_x + 226, write0_y - 80, 2),
        ("W0_WL", "metal1", write_x + 152, write0_y + 118, write_x + 152, write0_y + 160, 3),
        ("W1_BL", "metal1", write_x + 78, write1_y + 40, write_x + 61, write1_y + 124, 4),
        ("W1_BR", "metal1", write_x + 226, write1_y + 40, write_x + 266, write1_y + 124, 5),
        ("W1_WL", "metal1", write_x + 152, write1_y + 118, write_x + 152, write1_y + 118, 6),
        ("R0_RBL", "ndiffc", read_x + 36, read0_y + 97, read_x + 36, read0_y - 80, 7),
        ("R0_RWL", "metal1", read_x + 116, read0_y + 172, read_x + 116, read0_y + 220, 8),
        ("R1_RBL", "ndiffc", read_x + 36, read1_y + 97, read_x + 36, read1_y + 276, 9),
        ("R1_RWL", "metal1", read_x + 116, read1_y + 172, read_x + 116, read1_y + 220, 10),
        ("VDD", "metal1", 242, 500, 242, 620, 11),
    ]
    labels: list[Label] = []
    for name, source_layer, source_x, source_y, access_x, access_y, port in specs:
        add_local_m1_pin_access_to_m3(
            rects,
            source_x=source_x,
            source_y=source_y,
            access_x=access_x,
            access_y=access_y,
            source_layer=source_layer,
        )
        labels.append(Label("metal3", access_x, access_y, name, port))

    vss_x = read_x + 357
    vss_y = read0_y + 80
    add_compact_m2_to_m3_stack(rects, vss_x, vss_y, landing_m2=True)
    labels.append(Label("metal3", vss_x, vss_y, "VSS", 12))
    return rects, labels


def add_compact_m3_to_m4_pin(rects: list[Rect], x: int, y: int) -> None:
    rects.append(rect_centered("via3", x, y, 44, 44))
    rects.append(rect_centered("metal4", x, y, 80, 80))


def add_compact_m4_to_m5_pin(rects: list[Rect], x: int, y: int) -> None:
    rects.append(rect_centered("metal4", x, y, 80, 80))
    rects.append(rect_centered("via4", x, y, 44, 44))
    rects.append(rect_centered("metal5", x, y, 96, 64))


def add_m3_escape_to_m4_pin(
    rects: list[Rect],
    *,
    source_x: int,
    source_y: int,
    target_x: int,
    target_y: int,
    source_layer: str,
) -> None:
    """Escape a lower leaf pin to the array M4 track without M4 jog shorts."""

    if source_layer == "metal1":
        add_compact_m1_to_m3_stack(rects, source_x, source_y, landing_m1=True)
    elif source_layer == "metal2":
        add_compact_m2_to_m3_stack(rects, source_x, source_y, landing_m2=True)
    elif source_layer == "ndiffc":
        rects.append(rect_centered("metal1", source_x, source_y, 74, 74))
        add_compact_m1_to_m3_stack(rects, source_x, source_y, landing_m1=False)
    else:
        raise ValueError(f"unsupported source layer for M4 escape: {source_layer}")

    rects.append(Rect("metal3", min(source_x, target_x), source_y - 28, max(source_x, target_x), source_y + 28))
    if source_y != target_y:
        rects.append(Rect("metal3", target_x - 28, min(source_y, target_y), target_x + 28, max(source_y, target_y)))
    add_compact_m3_to_m4_pin(rects, target_x, target_y)


def add_m3_escape_to_m5_pin(
    rects: list[Rect],
    *,
    source_x: int,
    source_y: int,
    escape_y: int,
    track_y: int,
    source_layer: str = "metal1",
    escape_x: int = 50,
) -> None:
    """Escape WL/RWL pins to an M5 row track at the left edge of the cell."""

    if source_layer != "metal1":
        raise ValueError(f"unsupported source layer for M5 escape: {source_layer}")
    rects.append(rect_centered("metal1", source_x, escape_y, 72, 72))
    rects.append(Rect("metal1", source_x - 36, min(source_y, escape_y), source_x + 36, max(source_y, escape_y)))
    add_compact_m1_to_m3_stack(rects, source_x, escape_y, landing_m1=False)
    rects.append(Rect("metal3", escape_x, escape_y - 28, source_x, escape_y + 28))
    add_compact_m3_to_m4_pin(rects, escape_x, escape_y)
    if escape_y != track_y:
        rects.append(Rect("metal4", escape_x - 40, min(escape_y, track_y), escape_x + 40, max(escape_y, track_y)))
    add_compact_m4_to_m5_pin(rects, escape_x, track_y)
    rects.append(Rect("metal5", 0, track_y - 32, escape_x + 96, track_y + 32))


def add_m2_escape_to_m5_pin(
    rects: list[Rect],
    *,
    source_x: int,
    source_y: int,
    escape_y: int,
    track_y: int,
    escape_x: int,
) -> None:
    """Escape a WL/RWL pin through the free M2 channel between local buses."""

    rects.append(rect_centered("metal1", source_x, escape_y, 72, 72))
    rects.append(Rect("metal1", source_x - 36, min(source_y, escape_y), source_x + 36, max(source_y, escape_y)))
    rects.append(rect_centered("via1", source_x, escape_y, 44, 44))
    rects.append(rect_centered("metal2", source_x, escape_y, 52, 52))
    rects.append(Rect("metal2", min(source_x, escape_x), escape_y - 8, max(source_x, escape_x), escape_y + 8))
    rects.append(rect_centered("via2", escape_x, escape_y, 44, 44))
    rects.append(rect_centered("metal3", escape_x, escape_y, 56, 56))
    add_compact_m3_to_m4_pin(rects, escape_x, escape_y)
    if escape_y != track_y:
        rects.append(Rect("metal4", escape_x - 40, min(escape_y, track_y), escape_x + 40, max(escape_y, track_y)))
    add_compact_m4_to_m5_pin(rects, escape_x, track_y)
    rects.append(Rect("metal5", 0, track_y - 32, escape_x + 96, track_y + 32))


def add_ndiff_m2_escape_to_m4_pin(
    rects: list[Rect],
    *,
    source_x: int,
    source_y: int,
    escape_y: int,
    target_x: int,
    target_y: int,
) -> None:
    """Escape a read bitline contact while avoiding the internal VSS M2 rail."""

    rects.append(rect_centered("metal1", source_x, source_y, 74, 74))
    rects.append(Rect("metal1", source_x - 37, min(source_y, escape_y), source_x + 37, max(source_y, escape_y)))
    rects.append(rect_centered("via1", source_x, escape_y, 44, 44))
    rects.append(rect_centered("metal2", source_x, escape_y, 52, 52))
    rects.append(Rect("metal2", min(source_x, target_x), escape_y - 8, max(source_x, target_x), escape_y + 8))
    rects.append(Rect("metal2", target_x - 8, min(escape_y, target_y), target_x + 8, max(escape_y, target_y)))
    rects.append(rect_centered("via2", target_x, target_y, 44, 44))
    rects.append(rect_centered("metal3", target_x, target_y, 56, 56))
    add_compact_m3_to_m4_pin(rects, target_x, target_y)


def add_12t_rc1_upper_pin_escape_and_taps(
    rects: list[Rect],
    *,
    write_x: int,
    write0_y: int,
    write1_y: int,
    read_x: int,
    read0_y: int,
    read1_y: int,
) -> tuple[list[Rect], list[Label]]:
    """Promote the bitcell contract to top routing layers and add body taps."""

    rects = [*rects]
    pin_specs = [
        ("W0_BL", "metal4", write_x + 78, 20, 390, 20, "metal1"),
        ("W0_BR", "metal4", write_x + 226, 20, 650, 20, "metal1"),
        ("W1_BL", "metal4", write_x + 78, write1_y + 40, 520, write1_y + 40, "metal1"),
        ("W1_BR", "metal4", write_x + 226, write1_y + 40, 780, write1_y + 40, "metal1"),
        ("R1_RBL", "metal4", read_x + 36, read1_y + 97, 1030, read1_y + 97, "ndiffc"),
    ]
    for _name, _layer, source_x, source_y, target_x, target_y, source_layer in pin_specs:
        add_m3_escape_to_m4_pin(
            rects,
            source_x=source_x,
            source_y=source_y,
            target_x=target_x,
            target_y=target_y,
            source_layer=source_layer,
        )
    add_ndiff_m2_escape_to_m4_pin(
        rects,
        source_x=read_x + 36,
        source_y=read0_y + 97,
        escape_y=196,
        target_x=910,
        target_y=210,
    )

    wl_m2_specs = [
        ("R0_RWL", read_x + 116, read0_y + 172, 196, 150),
    ]
    wl_m3_specs = [
        ("W0_WL", write_x + 152, write0_y + 118, 96, 50),
        ("W1_WL", write_x + 152, write1_y + 118, 550, 50),
        ("R1_RWL", read_x + 116, read1_y + 172, 470, 150),
    ]
    # W1/R1 final track coordinates are row-local constants, not source-local
    # offsets; this keeps the macro M5 fabric inside the 2.66um row pitch.
    wl_track_y = {"W0_WL": 112, "R0_RWL": 196, "W1_WL": 336, "R1_RWL": 452}
    for name, source_x, source_y, escape_y, escape_x in wl_m2_specs:
        add_m2_escape_to_m5_pin(
            rects,
            source_x=source_x,
            source_y=source_y,
            escape_y=escape_y,
            track_y=wl_track_y[name],
            escape_x=escape_x,
        )
    for name, source_x, source_y, escape_y, escape_x in wl_m3_specs:
        add_m3_escape_to_m5_pin(
            rects,
            source_x=source_x,
            source_y=source_y,
            escape_y=escape_y,
            track_y=wl_track_y[name],
            source_layer="metal1",
            escape_x=escape_x,
        )

    add_m3_escape_to_m4_pin(
        rects,
        source_x=242,
        source_y=550,
        target_x=270,
        target_y=550,
        source_layer="metal1",
    )
    add_m3_escape_to_m4_pin(
        rects,
        source_x=read_x + 357,
        source_y=read0_y + 80,
        target_x=read_x + 357,
        target_y=read0_y + 80,
        source_layer="metal2",
    )

    # GF180 latch-up protection patterns are derived from Timothy's 3.3V SRAM
    # tap cells.  The compact leaf can carry local P-substrate taps on the
    # read-stack VSS rail; N-well taps need row-edge tap cells so they do not
    # collide with the minimum-area latch pull-up diffusion.
    rects.extend(
        [
            Rect("psubdiff", read_x + 334, read0_y + 154, read_x + 380, read0_y + 190),
            Rect("psubdiffcont", read_x + 340, read0_y + 158, read_x + 374, read0_y + 186),
            Rect("psubdiff", read_x + 334, 390, read_x + 380, 426),
            Rect("psubdiffcont", read_x + 340, 394, read_x + 374, 422),
            Rect("metal1", read_x + 334, 371, read_x + 380, 426),
        ]
    )

    labels = [
        Label("metal4", 390, 20, "W0_BL", 1),
        Label("metal4", 650, 20, "W0_BR", 2),
        Label("metal5", 50, 112, "W0_WL", 3),
        Label("metal4", 520, write1_y + 40, "W1_BL", 4),
        Label("metal4", 780, write1_y + 40, "W1_BR", 5),
        Label("metal5", 50, 336, "W1_WL", 6),
        Label("metal4", 910, 210, "R0_RBL", 7),
        Label("metal5", 150, 196, "R0_RWL", 8),
        Label("metal4", 1030, read1_y + 97, "R1_RBL", 9),
        Label("metal5", 150, 452, "R1_RWL", 10),
        Label("metal4", 270, 550, "VDD", 11),
        Label("metal4", read_x + 357, read0_y + 80, "VSS", 12),
    ]
    return rects, labels


def build_12t_rc1(
    seed_path: Path,
    tim_magic_dir: Path,
    out_dir: Path,
    well_margin: int,
    gap: int,
    *,
    cell_name: str = TWELVE_T_RC1_CELL,
    qg_route_style: str = "metal3",
    pin_access_style: str = "lower_labels",
) -> CellReport:
    """Build the first compact 12T candidate with trimmed write WL poly tails."""

    latch = latch_primitives_from_tim_seed(seed_path, margin=80)
    pulldowns = [rects for role, rects in latch if role == "latch_pulldown_nfet"]
    pullups = [rects for role, rects in latch if role == "latch_pullup_pfet"]

    def row_place(groups: list[list[Rect]], x0: int, y0: int, group_gap: int) -> tuple[list[Rect], int, int]:
        placed: list[Rect] = []
        x_cursor = x0
        row_height = 0
        for group in groups:
            gxlo, gylo, gxhi, gyhi = bbox(group)
            placed.extend(translate(group, x_cursor - gxlo, y0 - gylo))
            width = gxhi - gxlo
            row_height = max(row_height, gyhi - gylo)
            x_cursor += width + group_gap
        return placed, x_cursor - group_gap - x0, row_height

    rects: list[Rect] = []
    n_row, n_width, n_height = row_place(pulldowns, 0, 0, gap)
    p_row_y = n_height + gap
    p_row, p_width, p_height = row_place(pullups, 0, p_row_y, gap)
    latch_width = max(n_width, p_width)
    latch_height = p_row_y + p_height
    rects.extend(n_row)
    rects.extend(p_row)
    rects.insert(0, Rect("pwell", 0, 0, latch_width, n_height + well_margin))
    rects.insert(0, Rect("nwell", 0, p_row_y - well_margin, latch_width, latch_height + well_margin))

    write_pair = write_access_pair_from_tim_seed(seed_path, margin=80, group_gap=0, trim_poly_stub=48)
    write_pair = shifted_to_origin(write_pair)
    write_pair = add_write_access_pair_pin_straps(write_pair)
    wxlo, wylo, wxhi, wyhi = bbox(write_pair)
    write_width = wxhi - wxlo
    write_height = wyhi - wylo

    make_read_stack_geometry.tim_magic_dir = tim_magic_dir
    read_rects, read_labels, read_bbox = make_read_stack_geometry(well_margin)
    read_width = read_bbox[2] - read_bbox[0]
    read_height = read_bbox[3] - read_bbox[1]
    read_pair_width = max(read_width, 420)

    write_x = latch_width + gap
    read_x = write_x + write_width + gap
    write0_y = 0
    write_port_gap = max(gap, 40)
    write1_y = write_height + write_port_gap
    read0_y = 0
    read_port_gap = max(gap, 40)
    read1_y = read_height + read_port_gap

    rects.extend(translate(write_pair, write_x, write0_y))
    rects.extend(translate(write_pair, write_x, write1_y))
    read0_rects = add_read_gate_contact_pins(translate(read_rects, read_x, read0_y), read_x, read0_y)
    read1_rects = add_read_gate_contact_pins(translate(read_rects, read_x, read1_y), read_x, read1_y)
    rects.extend(read0_rects)
    rects.extend(read1_rects)
    rects = add_12t_rc1_blackbox_routes(
        rects,
        write_x=write_x,
        write0_y=write0_y,
        write1_y=write1_y,
        read_x=read_x,
        read0_y=read0_y,
        read1_y=read1_y,
        qg_route_style=qg_route_style,
    )
    labels: list[Label] = []
    labels.extend(write_access_pair_blackbox_labels(write_x, write0_y, "W0", 1))
    labels.extend(write_access_pair_blackbox_labels(write_x, write1_y, "W1", 4))
    labels.extend(
        [
            Label("ndiffc", read_x + 36, read0_y + 97, "R0_RBL", 7),
            Label("metal1", read_x + 116, read0_y + 172, "R0_RWL", 8),
            Label("ndiffc", read_x + 36, read1_y + 97, "R1_RBL", 9),
            Label("metal1", read_x + 116, read1_y + 172, "R1_RWL", 10),
            Label("metal1", 242, 500, "VDD", 11),
            Label("metal2", read_x + 357, read0_y + 80, "VSS", 12),
        ]
    )
    if pin_access_style == "rc6_m3":
        rects, labels = add_12t_rc6_pin_access_layer(
            rects,
            write_x=write_x,
            write0_y=write0_y,
            write1_y=write1_y,
            read_x=read_x,
            read0_y=read0_y,
            read1_y=read1_y,
        )
        rects, labels = shifted_rects_labels_to_origin(rects, labels)
    elif pin_access_style != "lower_labels":
        raise ValueError(f"unknown pin_access_style {pin_access_style!r}")

    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{cell_name}.mag"
    cell_bbox = bbox(rects)
    write_magic(
        mag_path,
        cell=cell_name,
        tech="gf180mcuD",
        magscale="1 10",
        rects=rects,
        labels=labels,
        properties={
            "DETRONYX_PHYSICAL_CELL": cell_name,
            "DETRONYX_SOURCE": seed_path.name,
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_WRITE_ACCESS_POLY_TRIM_STUB": "48",
            "DETRONYX_ROUTING_STATUS": (
                "rc6_m3_pin_access_leaf"
                if pin_access_style == "rc6_m3"
                else (
                "rc1_m3free_internal_q_qb_qg_routed_leaf_pins_lower_macro_escape_pending"
                if qg_route_style == "m3free_m2_spine"
                else "rc1_blackbox_internal_q_qb_qg_routed_leaf_pins_lower_macro_escape_pending"
                )
            ),
            "DETRONYX_QG_ROUTE_STYLE": qg_route_style,
            "DETRONYX_PIN_ACCESS_STYLE": pin_access_style,
        },
    )

    width, height, area = dims_um(cell_bbox)
    return CellReport(
        cell=cell_name,
        source=str(seed_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=[width, height, area],
        rules={
            "release_candidate": True,
            "uses_6t_cell_as_block": False,
            "latch_built_from_tim_device_primitives": True,
            "differential_write_access_devices": 4,
            "write_ports_added_from_tim_access_primitives": 2,
            "write_access_poly_trim_stub_magic_units": 48,
            "read_ports_added_from_tim_nf2_read_stack_primitives": 2,
            "transistor_resize_allowed": False,
            "routing_status": (
                "RC6 pin-access leaf; M3 access points are connected inside the leaf and intended for 5-layer tile routing"
                if pin_access_style == "rc6_m3"
                else (
                "RC1 M3-free experiment; Q/QB/write access/read QG routed internally; no metal3 rectangles inside leaf"
                if qg_route_style == "m3free_m2_spine"
                else "RC1 blackbox leaf; Q/QB/write access/read QG routed internally; macro-facing lower pins retained for LVS-clean leaf"
                )
            ),
            "qg_route_style": qg_route_style,
            "pin_access_style": pin_access_style,
            "external_contract": [
                "W0_BL",
                "W0_BR",
                "W0_WL",
                "W1_BL",
                "W1_BR",
                "W1_WL",
                "R0_RBL",
                "R0_RWL",
                "R1_RBL",
                "R1_RWL",
                "VDD",
                "VSS",
            ],
            "internal_storage_assignment": {
                "Q": "right_storage_node",
                "QB": "left_storage_node",
                "R0_QG": "Q",
                "R1_QG": "Q",
            },
            "upper_pin_escape": {
                "status": "pending",
                "reason": "direct leaf escape is DRC-clean but LVS-shorts in the current minimum-pitch RC1; escape must be implemented as a dedicated boundary/tap cell or with extra pitch",
            },
            "latchup_protection": {
                "local_nwell_to_vdd_tap": False,
                "local_psub_to_vss_taps": 0,
                "tap_layers": ["nsubdiff", "nsubdiffcont", "psubdiff", "psubdiffcont"],
                "macro_edge_taps_required": True,
            },
            "gap_magic_units": gap,
            "write_port_gap_magic_units": write_port_gap,
            "read_port_gap_magic_units": read_port_gap,
            "well_margin_magic_units": well_margin,
            "latch_bbox_um": dims_um((0, 0, latch_width, latch_height)),
            "write_pair_bbox_um": dims_um((0, 0, write_width, write_height)),
            "read_stack_bbox_um": dims_um((0, 0, read_width, read_height)),
            "read_pair_with_vss_strap_bbox_um": dims_um((0, 0, read_pair_width, read_height * 2)),
        },
        labels=[label_dict(label) for label in labels],
    )


def build_physical_compare(
    seed_path: Path,
    tim_magic_dir: Path,
    out_dir: Path,
    well_margin: int,
    gap: int,
) -> CellReport:
    six = build_6t_seed(seed_path, out_dir)
    twelve = build_12t_seed(seed_path, tim_magic_dir, out_dir, well_margin, gap)
    ten = build_10t_seed(seed_path, tim_magic_dir, out_dir, well_margin, gap)

    components = [
        (six.cell, read_magic(Path(six.output_magic), six.cell), six.bbox_um),
        (twelve.cell, read_magic(Path(twelve.output_magic), twelve.cell), twelve.bbox_um),
        (ten.cell, read_magic(Path(ten.output_magic), ten.cell), ten.bbox_um),
    ]

    rects: list[Rect] = []
    placements: dict[str, dict[str, object]] = {}
    x_cursor = 0
    for name, layout, bbox_um in components:
        local = shifted_to_origin(layout.rects)
        cxlo, cylo, cxhi, cyhi = bbox(local)
        rects.extend(translate(local, x_cursor - cxlo, -cylo))
        placements[name] = {
            "x_magic": x_cursor,
            "bbox_um": bbox_um,
            "width_um": round((cxhi - cxlo) / UNITS_PER_UM, 6),
            "height_um": round((cyhi - cylo) / UNITS_PER_UM, 6),
        }
        x_cursor += (cxhi - cxlo) + gap

    cell_bbox = bbox(rects)
    out_dir.mkdir(parents=True, exist_ok=True)
    mag_path = out_dir / f"{PHYSICAL_COMPARE_CELL}.mag"
    write_magic(
        mag_path,
        cell=PHYSICAL_COMPARE_CELL,
        tech="gf180mcuD",
        magscale="1 10",
        rects=rects,
        labels=[],
        properties={
            "DETRONYX_PHYSICAL_CELL": PHYSICAL_COMPARE_CELL,
            "DETRONYX_REFERENCE_LAYOUT": "6T_12T_10T_side_by_side",
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
        },
    )

    return CellReport(
        cell=PHYSICAL_COMPARE_CELL,
        source=str(seed_path),
        output_magic=str(mag_path),
        bbox_magic=list(cell_bbox),
        bbox_um=dims_um(cell_bbox),
        rules={
            "reference_only": True,
            "side_by_side_order": [name for name, _layout, _bbox_um in components],
            "component_placements": placements,
            "gap_magic_units": gap,
            "transistor_resize_allowed": False,
        },
        labels=[],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tim-magic-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--seed", type=Path)
    parser.add_argument(
        "--cell",
        choices=[
            "6t-seed",
            "read-stack",
            "12t-seed",
            "12t-rc1",
            "12t-rc1-m3free",
            "12t-rc6-pin-access",
            "10t-seed",
            "10t-rc1",
            "compare",
        ],
        default="read-stack",
    )
    parser.add_argument("--well-margin", type=int, default=40)
    parser.add_argument("--gap", type=int, default=80)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.cell == "6t-seed":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 6t-seed")
        report = build_6t_seed(args.seed, args.out_dir)
    elif args.cell == "read-stack":
        report = build_read_stack(args.tim_magic_dir, args.out_dir, args.well_margin)
    elif args.cell == "12t-seed":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 12t-seed")
        report = build_12t_seed(args.seed, args.tim_magic_dir, args.out_dir, args.well_margin, args.gap)
    elif args.cell == "12t-rc1":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 12t-rc1")
        report = build_12t_rc1(args.seed, args.tim_magic_dir, args.out_dir, args.well_margin, args.gap)
    elif args.cell == "12t-rc1-m3free":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 12t-rc1-m3free")
        report = build_12t_rc1(
            args.seed,
            args.tim_magic_dir,
            args.out_dir,
            args.well_margin,
            args.gap,
            cell_name=TWELVE_T_RC1_M3FREE_CELL,
            qg_route_style="m3free_m2_spine",
        )
    elif args.cell == "12t-rc6-pin-access":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 12t-rc6-pin-access")
        report = build_12t_rc1(
            args.seed,
            args.tim_magic_dir,
            args.out_dir,
            args.well_margin,
            args.gap,
            cell_name=TWELVE_T_RC6_PIN_ACCESS_CELL,
            qg_route_style="m3free_m2_spine",
            pin_access_style="rc6_m3",
        )
    elif args.cell == "10t-seed":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 10t-seed")
        report = build_10t_seed(args.seed, args.tim_magic_dir, args.out_dir, args.well_margin, args.gap)
    elif args.cell == "10t-rc1":
        if args.seed is None:
            raise ValueError("--seed is required for --cell 10t-rc1")
        report = build_10t_rc1(args.seed, args.tim_magic_dir, args.out_dir, args.well_margin, args.gap)
    else:
        if args.seed is None:
            raise ValueError("--seed is required for --cell compare")
        report = build_physical_compare(args.seed, args.tim_magic_dir, args.out_dir, args.well_margin, args.gap)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n")
    width, height, area = report.bbox_um
    print(f"{report.cell}: {width:.3f}um x {height:.3f}um = {area:.3f}um^2")
    print(report.output_magic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
