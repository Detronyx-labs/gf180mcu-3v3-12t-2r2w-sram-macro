#!/usr/bin/env python3
"""Build a first physical 12T 2W2R SRAM periphery selected-path slice.

This is the layout counterpart for `detronyx_gf180_12t_2w2r_periphery_rc1.spice`.
It deliberately starts as a selected-path leaf, not the full 128-row decoder
matrix.  The flow copies Tim Edwards' 3.3V-converted GF180 SRAM MOS primitives
without resizing them, places them into functional groups, adds well context,
power rails, and route-facing pins, then emits Magic/GDS/LEF/blackbox SPICE.

The current RC1 layout is DRC/extraction oriented.  Internal signal routing is
reserved with labeled pins and guide straps; final LVS-exact routing/sizing is a
follow-up pass once the placement dimensions stop moving.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from build_physical_cells import Label, USEFUL_LAYERS, bbox, dims_um, translate, write_magic
from extreme_compaction_search import Rect, read_magic


UNITS_PER_UM = 200.0
CELL_NAME = "detronyx_12t_2w2r_periphery_slice_rc1"

NMOS_SOURCE = "nmos_5p04310591302010_3v512x8m81.mag"
PMOS_SOURCE = "pmos_5p04310591302038_3v512x8m81.mag"


@dataclass(frozen=True)
class DeviceKind:
    name: str
    source: str
    width_units: int
    height_units: int
    rect_count: int


@dataclass(frozen=True)
class DevicePlacement:
    index: int
    block: str
    mos: str
    role: str
    x_units: int
    y_units: int
    x_um: float
    y_um: float


@dataclass(frozen=True)
class PinShape:
    name: str
    direction: str
    use: str
    layer: str
    xlo: int
    ylo: int
    xhi: int
    yhi: int


@dataclass(frozen=True)
class RouteTerm:
    net: str
    kind: str
    x: int
    y: int
    block: str
    role: str
    terminal: str


@dataclass(frozen=True)
class LayoutResult:
    cell: str
    status: str
    width_um: float
    height_um: float
    area_um2: float
    device_count: int
    nmos_count: int
    pmos_count: int
    pin_count: int
    magic: str
    gds: str
    lef: str
    spice: str
    pins_json: str
    reference_cdl: str
    placements_csv: str
    summary_md: str
    drc_errors: int | None
    drc_log: str
    extract_log: str
    netgen_lvs_log: str
    extracted_spice: str
    extracted_rc_spice: str


def to_units(value_um: float) -> int:
    return int(round(value_um * UNITS_PER_UM))


def units_to_um(value: int) -> float:
    return value / UNITS_PER_UM


def shifted_to_origin(rects: list[Rect]) -> list[Rect]:
    xlo, ylo, _xhi, _yhi = bbox(rects)
    return translate(rects, -xlo, -ylo)


def load_device(tim_magic_dir: Path, source_name: str, name: str) -> tuple[DeviceKind, list[Rect], str, str]:
    source_path = tim_magic_dir / source_name
    source = read_magic(source_path, f"detronyx_tim_{name}")
    rects = [
        rect
        for rect in source.rects
        if rect.layer in USEFUL_LAYERS and not rect.layer.startswith("error")
    ]
    if not rects:
        raise ValueError(f"{source_path}: no useful rectangles parsed")
    rects = shifted_to_origin(rects)
    xlo, ylo, xhi, yhi = bbox(rects)
    kind = DeviceKind(
        name=name,
        source=source_name,
        width_units=xhi - xlo,
        height_units=yhi - ylo,
        rect_count=len(rects),
    )
    return kind, rects, source.tech, source.magscale


def pin_direction(name: str) -> tuple[str, str]:
    if name == "VDD":
        return "INOUT", "POWER"
    if name == "VSS":
        return "INOUT", "GROUND"
    if name in {"dout", "write_conflict", "wwl0", "rwl0"}:
        return "OUTPUT", "SIGNAL"
    return "INPUT", "SIGNAL"


def add_pin(
    rects: list[Rect],
    labels: list[Label],
    pins: list[PinShape],
    *,
    name: str,
    x: int,
    y: int,
    w: int,
    h: int,
    port: int,
) -> None:
    xlo = x
    ylo = y
    xhi = x + w
    yhi = y + h
    rects.append(Rect("metal3", xlo, ylo, xhi, yhi))
    labels.append(Label("metal3", (xlo + xhi) // 2, (ylo + yhi) // 2, name, port))
    direction, use = pin_direction(name)
    pins.append(PinShape(name, direction, use, "metal3", xlo, ylo, xhi, yhi))


def add_raw_pin(
    labels: list[Label],
    pins: list[PinShape],
    *,
    name: str,
    xlo: int,
    ylo: int,
    xhi: int,
    yhi: int,
    port: int,
) -> None:
    labels.append(Label("metal3", (xlo + xhi) // 2, (ylo + yhi) // 2, name, port))
    direction, use = pin_direction(name)
    pins.append(PinShape(name, direction, use, "metal3", xlo, ylo, xhi, yhi))


def block_specs() -> list[dict[str, object]]:
    return [
        {
            "name": "write_row_decode7_wl_driver",
            "description": "write-port 3+2+2 selected-row decode, row gate, WWL driver chain",
            "n_roles": [
                "pre0_n_pull_a0",
                "pre0_n_pull_a1",
                "pre0_n_pull_a2",
                "pre1_n_pull_a3",
                "pre1_n_pull_a4",
                "pre2_n_pull_a5",
                "pre2_n_pull_a6",
                "pre2_n_pull_en",
                "row_n_pull_pre0",
                "row_n_pull_pre1",
                "row_n_pull_pre2",
                "pre0_inv_n",
                "pre1_inv_n",
                "pre2_inv_n",
                "row_inv_n",
                "wl_drv0_n",
                "wl_drv1_n",
                "wl_drv2_n",
                "wl_drv3_n",
            ],
            "p_roles": [
                "pre0_n_pullup_a0",
                "pre0_n_pullup_a1",
                "pre0_n_pullup_a2",
                "pre1_n_pullup_a3",
                "pre1_n_pullup_a4",
                "pre2_n_pullup_a5",
                "pre2_n_pullup_a6",
                "pre2_n_pullup_en",
                "row_n_pullup_pre0",
                "row_n_pullup_pre1",
                "row_n_pullup_pre2",
                "pre0_inv_p",
                "pre1_inv_p",
                "pre2_inv_p",
                "row_inv_p",
                "wl_drv0_p",
                "wl_drv1_p",
                "wl_drv2_p",
                "wl_drv3_p",
            ],
            "pins": ["wdecen", "a[0]", "a[1]", "a[2]", "a[3]", "a[4]", "a[5]", "a[6]", "wwl0"],
        },
        {
            "name": "read_row_decode7_wl_driver",
            "description": "read-port 3+2+2 selected-row decode, row gate, RWL driver chain",
            "n_roles": [
                "pre0_n_pull_a0",
                "pre0_n_pull_a1",
                "pre0_n_pull_a2",
                "pre1_n_pull_a3",
                "pre1_n_pull_a4",
                "pre2_n_pull_a5",
                "pre2_n_pull_a6",
                "pre2_n_pull_en",
                "row_n_pull_pre0",
                "row_n_pull_pre1",
                "row_n_pull_pre2",
                "pre0_inv_n",
                "pre1_inv_n",
                "pre2_inv_n",
                "row_inv_n",
                "wl_drv0_n",
                "wl_drv1_n",
                "wl_drv2_n",
                "wl_drv3_n",
            ],
            "p_roles": [
                "pre0_n_pullup_a0",
                "pre0_n_pullup_a1",
                "pre0_n_pullup_a2",
                "pre1_n_pullup_a3",
                "pre1_n_pullup_a4",
                "pre2_n_pullup_a5",
                "pre2_n_pullup_a6",
                "pre2_n_pullup_en",
                "row_n_pullup_pre0",
                "row_n_pullup_pre1",
                "row_n_pullup_pre2",
                "pre0_inv_p",
                "pre1_inv_p",
                "pre2_inv_p",
                "row_inv_p",
                "wl_drv0_p",
                "wl_drv1_p",
                "wl_drv2_p",
                "wl_drv3_p",
            ],
            "pins": ["ren", "a[0]", "a[1]", "a[2]", "a[3]", "a[4]", "a[5]", "a[6]", "rwl0"],
        },
        {
            "name": "write_driver",
            "description": "din inverter, gated complementary write bitline drivers",
            "n_roles": [
                "dinb_inv_n",
                "wbl_up_nand_n0",
                "wbl_up_nand_n1",
                "wbl_dn_nand_n0",
                "wbl_dn_nand_n1",
                "wbl_dn_inv_n",
                "wbl_pull_down",
                "wbr_up_nand_n0",
                "wbr_up_nand_n1",
                "wbr_dn_nand_n0",
                "wbr_dn_nand_n1",
                "wbr_dn_inv_n",
                "wbr_pull_down",
            ],
            "p_roles": [
                "dinb_inv_p",
                "wbl_up_nand_p0",
                "wbl_up_nand_p1",
                "wbl_dn_nand_p0",
                "wbl_dn_nand_p1",
                "wbl_dn_inv_p",
                "wbl_pull_up",
                "wbr_up_nand_p0",
                "wbr_up_nand_p1",
                "wbr_dn_nand_p0",
                "wbr_dn_nand_p1",
                "wbr_dn_inv_p",
                "wbr_pull_up",
            ],
            "pins": ["din", "wen", "wbl0", "wbr0"],
        },
        {
            "name": "precharge_sense",
            "description": "RBL precharge PMOS and three-stage single-ended sense chain",
            "n_roles": ["sense0_n", "sense1_n", "sense2_n"],
            "p_roles": ["rbl_precharge_p", "sense0_p", "sense1_p", "sense2_p"],
            "pins": ["pchgb", "ren", "rbl0", "dout"],
        },
        {
            "name": "write_conflict",
            "description": "w0_en & w1_en & address-equal selected-path detector",
            "n_roles": [
                "both_nand_n0",
                "both_nand_n1",
                "both_inv_n",
                "conflict_nand_n0",
                "conflict_nand_n1",
                "conflict_inv_n",
            ],
            "p_roles": [
                "both_nand_p0",
                "both_nand_p1",
                "both_inv_p",
                "conflict_nand_p0",
                "conflict_nand_p1",
                "conflict_inv_p",
            ],
            "pins": ["w0_en", "w1_en", "addr_eq", "write_conflict"],
        },
    ]


def inv_role_nets(role: str, mos: str, input_net: str, output_net: str) -> tuple[str, str, str]:
    if mos == "pmos":
        return output_net, input_net, "VDD"
    return output_net, input_net, "VSS"


def nand2_role_nets(role: str, mos: str, a: str, b: str, y: str, mid: str) -> tuple[str, str, str]:
    suffix = role.rsplit("_", 1)[-1]
    if mos == "pmos":
        gate = a if suffix.endswith("0") else b
        return y, gate, "VDD"
    if suffix.endswith("0"):
        return y, a, mid
    return mid, b, "VSS"


def nand3_role_nets(
    role: str,
    mos: str,
    a: str,
    b: str,
    c: str,
    y: str,
    mid0: str,
    mid1: str,
) -> tuple[str, str, str]:
    suffix = role.rsplit("_", 1)[-1]
    if mos == "pmos":
        if suffix.endswith("a0") or suffix.endswith("0"):
            gate = a
        elif suffix.endswith("a1") or suffix.endswith("1"):
            gate = b
        else:
            gate = c
        return y, gate, "VDD"
    if suffix.endswith("a0") or suffix.endswith("0"):
        return y, a, mid0
    if suffix.endswith("a1") or suffix.endswith("1"):
        return mid0, b, mid1
    return mid1, c, "VSS"


def role_terminal_nets(block: str, mos: str, role: str) -> tuple[str, str, str]:
    """Return drain/gate/source nets for the placed role.

    Netgen's GF180 setup permits source/drain permutation, but the internal
    series nodes are still made explicit so the reference CDL has the intended
    CMOS topology.
    """

    if block in {"row_decode7_wl_driver", "write_row_decode7_wl_driver", "read_row_decode7_wl_driver"}:
        if block == "read_row_decode7_wl_driver":
            ns = "rdec"
            enable_net = "ren"
            wl_net = "rwl0"
        elif block == "write_row_decode7_wl_driver":
            ns = "wdec"
            enable_net = "wdecen"
            wl_net = "wwl0"
        else:
            ns = "dec"
            enable_net = "wdecen"
            wl_net = "wwl0"

        def local(net: str) -> str:
            if net in {"VDD", "VSS"} or net.startswith("a["):
                return net
            return f"{ns}_{net}"

        if role.startswith("pre0_n_pullup"):
            gate = role.removeprefix("pre0_n_pullup_")
            gate_net = {"a0": "a[0]", "a1": "a[1]", "a2": "a[2]"}[gate]
            return local("pre0_n"), gate_net, "VDD"
        if role.startswith("pre0_n_pull_"):
            gate = role.removeprefix("pre0_n_pull_")
            if gate == "a0":
                return local("pre0_n"), "a[0]", local("pre0_s0")
            if gate == "a1":
                return local("pre0_s0"), "a[1]", local("pre0_s1")
            return local("pre0_s1"), "a[2]", "VSS"
        if role.startswith("pre1_n_pullup"):
            gate = role.removeprefix("pre1_n_pullup_")
            gate_net = {"a3": "a[3]", "a4": "a[4]"}[gate]
            return local("pre1_n"), gate_net, "VDD"
        if role.startswith("pre1_n_pull_"):
            gate = role.removeprefix("pre1_n_pull_")
            if gate == "a3":
                return local("pre1_n"), "a[3]", local("pre1_s0")
            return local("pre1_s0"), "a[4]", "VSS"
        if role.startswith("pre2_n_pullup"):
            gate = role.removeprefix("pre2_n_pullup_")
            gate_net = {"a5": "a[5]", "a6": "a[6]", "en": "wdecen"}[gate]
            if gate == "en":
                gate_net = enable_net
            return local("pre2_n"), gate_net, "VDD"
        if role.startswith("pre2_n_pull_"):
            gate = role.removeprefix("pre2_n_pull_")
            if gate == "a5":
                return local("pre2_n"), "a[5]", local("pre2_s0")
            if gate == "a6":
                return local("pre2_s0"), "a[6]", local("pre2_s1")
            return local("pre2_s1"), enable_net, "VSS"
        if role.startswith("row_n_pullup"):
            gate = role.removeprefix("row_n_pullup_")
            return local("row_n"), local(gate), "VDD"
        if role.startswith("row_n_pull_"):
            gate = role.removeprefix("row_n_pull_")
            if gate == "pre0":
                return local("row_n"), local("pre0"), local("row_s0")
            if gate == "pre1":
                return local("row_s0"), local("pre1"), local("row_s1")
            return local("row_s1"), local("pre2"), "VSS"
        inverter_map = {
            "pre0_inv": (local("pre0_n"), local("pre0")),
            "pre1_inv": (local("pre1_n"), local("pre1")),
            "pre2_inv": (local("pre2_n"), local("pre2")),
            "row_inv": (local("row_n"), local("row_sel")),
            "wl_drv0": (local("row_sel"), local("wl_b0")),
            "wl_drv1": (local("wl_b0"), local("wl_s1")),
            "wl_drv2": (local("wl_s1"), local("wl_b2")),
            "wl_drv3": (local("wl_b2"), wl_net),
        }
        for prefix, (input_net, output_net) in inverter_map.items():
            if role.startswith(prefix):
                return inv_role_nets(role, mos, input_net, output_net)

    if block == "write_driver":
        if role.startswith("dinb_inv"):
            return inv_role_nets(role, mos, "din", "din_b")
        nand_map = {
            "wbl_up_nand": ("din", "wen", "wbl_up_n", "wbl_up_mid"),
            "wbl_dn_nand": ("din_b", "wen", "wbl_dn_n", "wbl_dn_mid"),
            "wbr_up_nand": ("din_b", "wen", "wbr_up_n", "wbr_up_mid"),
            "wbr_dn_nand": ("din", "wen", "wbr_dn_n", "wbr_dn_mid"),
        }
        for prefix, args in nand_map.items():
            if role.startswith(prefix):
                return nand2_role_nets(role, mos, *args)
        if role.startswith("wbl_dn_inv"):
            return inv_role_nets(role, mos, "wbl_dn_n", "wbl_dn")
        if role.startswith("wbr_dn_inv"):
            return inv_role_nets(role, mos, "wbr_dn_n", "wbr_dn")
        if role == "wbl_pull_down":
            return "wbl0", "wbl_dn", "VSS"
        if role == "wbl_pull_up":
            return "wbl0", "wbl_up_n", "VDD"
        if role == "wbr_pull_down":
            return "wbr0", "wbr_dn", "VSS"
        if role == "wbr_pull_up":
            return "wbr0", "wbr_up_n", "VDD"

    if block == "precharge_sense":
        if role == "rbl_precharge_p":
            return "rbl0", "pchgb", "VDD"
        if role.startswith("sense0"):
            return inv_role_nets(role, mos, "rbl0", "sense0")
        if role.startswith("sense1"):
            return inv_role_nets(role, mos, "sense0", "sense1")
        if role.startswith("sense2"):
            return inv_role_nets(role, mos, "sense1", "dout")

    if block == "write_conflict":
        if role.startswith("both_nand"):
            return nand2_role_nets(role, mos, "w0_en", "w1_en", "both_n", "both_mid")
        if role.startswith("both_inv"):
            return inv_role_nets(role, mos, "both_n", "both")
        if role.startswith("conflict_nand"):
            return nand2_role_nets(role, mos, "both", "addr_eq", "conflict_n", "conflict_mid")
        if role.startswith("conflict_inv"):
            return inv_role_nets(role, mos, "conflict_n", "write_conflict")

    raise ValueError(f"unmapped role: {block} {mos} {role}")


def term_points(placement: DevicePlacement) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    if placement.mos == "nmos":
        left = (placement.x_units + 36, placement.y_units + 149)
        gate = (placement.x_units + 116, placement.y_units + 280)
        right = (placement.x_units + 196, placement.y_units + 149)
    else:
        left = (placement.x_units + 122, placement.y_units + 142)
        gate = (placement.x_units + 202, placement.y_units + 220)
        right = (placement.x_units + 282, placement.y_units + 142)
    return left, gate, right


def collect_route_terms(placements: list[DevicePlacement]) -> list[RouteTerm]:
    terms: list[RouteTerm] = []
    for placement in placements:
        drain, gate, source = role_terminal_nets(placement.block, placement.mos, placement.role)
        left, gate_pt, right = term_points(placement)
        terms.append(RouteTerm(drain, "diff", left[0], left[1], placement.block, placement.role, "drain"))
        terms.append(RouteTerm(gate, "gate", gate_pt[0], gate_pt[1], placement.block, placement.role, "gate"))
        terms.append(RouteTerm(source, "diff", right[0], right[1], placement.block, placement.role, "source"))
    return terms


def rect_centered(layer: str, x: int, y: int, w: int, h: int) -> Rect:
    return Rect(layer, x - w // 2, y - h // 2, x + (w + 1) // 2, y + (h + 1) // 2)


def add_via1_stack(rects: list[Rect], x: int, y: int) -> None:
    rects.append(rect_centered("metal1", x, y, 65, 92))
    rects.append(rect_centered("via1", x, y, 52, 52))
    rects.append(rect_centered("metal2", x, y, 65, 92))


def add_via2_stack(rects: list[Rect], x: int, y: int) -> None:
    rects.append(rect_centered("metal2", x, y, 65, 92))
    rects.append(rect_centered("via2", x, y, 57, 57))
    rects.append(rect_centered("metal3", x, y, 65, 92))


def add_gate_contact(rects: list[Rect], x: int, y: int) -> None:
    rects.append(rect_centered("polysilicon", x, y, 56, 60))
    rects.append(rect_centered("polycontact", x, y, 46, 46))
    rects.append(rect_centered("metal1", x, y, 65, 65))
    add_via1_stack(rects, x, y)


def add_diff_contact_plate(rects: list[Rect], x: int, y: int) -> None:
    rects.append(rect_centered("metal1", x, y, 46, 190))
    add_via1_stack(rects, x, y)


def add_tap(rects: list[Rect], terms: list[RouteTerm], *, net: str, x: int, y: int, kind: str, block: str) -> None:
    if kind == "psub":
        rects.append(rect_centered("psubdiff", x, y, 150, 210))
        rects.append(rect_centered("psubdiffcont", x, y, 46, 146))
    elif kind == "nsub":
        rects.append(rect_centered("nsubdiff", x, y, 210, 120))
        rects.append(rect_centered("nsubdiffcont", x, y, 146, 46))
    else:
        raise ValueError(kind)
    rects.append(rect_centered("metal1", x, y, 230, 230))
    add_via1_stack(rects, x, y)
    terms.append(RouteTerm(net, "diff", x, y, block, f"{kind}_tap", "tap"))


def ordered_route_nets_from_names(names: set[str]) -> list[str]:
    priority = {"VSS": -2, "VDD": -1}
    return sorted(names, key=lambda n: (priority.get(n, 0), n))


def trunk_x_for_nets(nets: list[str], base_x: int | None = None) -> dict[str, int]:
    x_start = to_units(2.0) if base_x is None else base_x
    trunk_pitch = to_units(0.70)
    return {net: x_start + to_units(1.0) + idx * trunk_pitch for idx, net in enumerate(nets)}


def add_lvs_routing(
    rects: list[Rect],
    terms: list[RouteTerm],
    *,
    total_width: int,
    route_base_y: int,
    lower_track_base_y: int,
    rail_pitch: int,
    track_base_y: int,
    track_pitch: int,
    trunk_base_x: int,
    rail_width: int,
    route_width: int,
    via2_size: int,
) -> dict[str, int]:
    # Keep rails with heavy fanout near the bottom of the route channel.
    nets = ordered_route_nets_from_names({term.net for term in terms})
    rail_y = {net: route_base_y + idx * rail_pitch for idx, net in enumerate(nets)}

    x_start = to_units(2.0)
    x_stop = total_width - to_units(2.0)
    trunk_x = trunk_x_for_nets(nets, trunk_base_x)
    for net, y in rail_y.items():
        rects.append(Rect("metal2", x_start, y, x_stop, y + rail_width))

    device_terms = [term for term in terms if term.kind != "pin" and term.y < route_base_y]
    if device_terms:
        split_y = (min(term.y for term in device_terms) + max(term.y for term in device_terms)) // 2
    else:
        split_y = route_base_y

    lower_idx = 0
    upper_idx = 0
    for term in terms:
        rail = rail_y[term.net] + rail_width // 2
        net_x = trunk_x[term.net]

        if term.kind == "pin":
            if term.y <= split_y:
                track_y = lower_track_base_y + lower_idx * track_pitch
                lower_idx += 1
            else:
                track_y = track_base_y + upper_idx * track_pitch
                upper_idx += 1

            ylo = min(term.y, track_y)
            yhi = max(term.y, track_y)
            rects.append(Rect("metal3", term.x - route_width // 2, ylo, term.x + route_width // 2, yhi))
            add_via2_stack(rects, term.x, track_y)

            xlo = min(term.x, net_x)
            xhi = max(term.x, net_x)
            rects.append(Rect("metal2", xlo, track_y - route_width // 2, xhi, track_y + route_width // 2))
            add_via2_stack(rects, net_x, track_y)

            ylo = min(track_y, rail)
            yhi = max(track_y, rail)
            rects.append(Rect("metal3", net_x - route_width // 2, ylo, net_x + route_width // 2, yhi))
            add_via2_stack(rects, net_x, rail)
            continue

        if term.y <= split_y:
            track_y = lower_track_base_y + lower_idx * track_pitch
            lower_idx += 1
        else:
            track_y = track_base_y + upper_idx * track_pitch
            upper_idx += 1
        term_x = term.x

        if term.kind == "gate":
            add_gate_contact(rects, term.x, term.y)
        else:
            add_diff_contact_plate(rects, term.x, term.y)

        add_via2_stack(rects, term_x, term.y)

        # Split NMOS/PMOS escapes into lower/upper channels.  This avoids the
        # long overlapping M3 columns that otherwise short near-identical X
        # coordinates from the two transistor rows.
        ylo = min(term.y, track_y)
        yhi = max(term.y, track_y)
        rects.append(Rect("metal3", term_x - route_width // 2, ylo, term_x + route_width // 2, yhi))
        add_via2_stack(rects, term_x, track_y)

        xlo = min(term_x, net_x)
        xhi = max(term_x, net_x)
        rects.append(Rect("metal2", xlo, track_y - route_width // 2, xhi, track_y + route_width // 2))
        add_via2_stack(rects, net_x, track_y)

        ylo = min(track_y, rail)
        yhi = max(track_y, rail)
        rects.append(Rect("metal3", net_x - route_width // 2, ylo, net_x + route_width // 2, yhi))
        add_via2_stack(rects, net_x, rail)

    return rail_y


def write_reference_cdl(path: Path, pins: list[PinShape], placements: list[DevicePlacement], *, cell: str = CELL_NAME) -> None:
    pin_order = " ".join(pin.name for pin in pins)
    lines = [
        f"* Independent intended-topology CDL for {cell}",
        "* Generated from the periphery RC1 role map.",
        f".subckt {cell} {pin_order}",
    ]
    for placement in placements:
        drain, gate, source = role_terminal_nets(placement.block, placement.mos, placement.role)
        body = "VDD" if placement.mos == "pmos" else "VSS"
        model = "pfet_03v3" if placement.mos == "pmos" else "nfet_03v3"
        width = "0.56u" if placement.mos == "pmos" else "1.055u"
        lines.append(
            f"X{placement.index}_{placement.role} {drain} {gate} {source} {body} "
            f"{model} w={width} l=0.28u"
        )
    lines.append(f".ends {cell}")
    path.write_text("\n".join(lines) + "\n")


def place_block(
    *,
    rects: list[Rect],
    placements: list[DevicePlacement],
    block: dict[str, object],
    block_x: int,
    block_y: int,
    nmos_rects: list[Rect],
    pmos_rects: list[Rect],
    n_kind: DeviceKind,
    p_kind: DeviceKind,
    device_gap: int,
    row_gap: int,
    well_margin: int,
    device_index_start: int,
) -> tuple[int, int, int]:
    n_roles = list(block["n_roles"])
    p_roles = list(block["p_roles"])
    n_count = len(n_roles)
    p_count = len(p_roles)
    count = max(n_count, p_count)
    block_width = max(
        n_count * n_kind.width_units + max(n_count - 1, 0) * device_gap,
        p_count * p_kind.width_units + max(p_count - 1, 0) * device_gap,
    )
    n_y = block_y + well_margin
    p_y = n_y + n_kind.height_units + row_gap
    block_height = well_margin + n_kind.height_units + row_gap + p_kind.height_units + well_margin

    rects.append(Rect("pwell", block_x, block_y, block_x + block_width, n_y + n_kind.height_units + well_margin))
    rects.append(Rect("nwell", block_x, p_y - well_margin, block_x + block_width, p_y + p_kind.height_units + well_margin))

    # Power rails are wide enough to make the physical intent visible in KLayout
    # while remaining outside the copied primitive source/drain geometry.
    rail_h = to_units(0.9)
    rects.append(Rect("metal2", block_x, block_y + 10, block_x + block_width, block_y + 10 + rail_h))
    rects.append(Rect("metal2", block_x, block_y + block_height - 10 - rail_h, block_x + block_width, block_y + block_height - 10))

    device_index = device_index_start
    for idx, role in enumerate(n_roles):
        x = block_x + idx * (n_kind.width_units + device_gap)
        rects.extend(translate(nmos_rects, x, n_y))
        placements.append(
            DevicePlacement(
                device_index,
                str(block["name"]),
                "nmos",
                role,
                x,
                n_y,
                round(units_to_um(x), 6),
                round(units_to_um(n_y), 6),
            )
        )
        device_index += 1

    for idx, role in enumerate(p_roles):
        x = block_x + idx * (p_kind.width_units + device_gap)
        rects.extend(translate(pmos_rects, x, p_y))
        placements.append(
            DevicePlacement(
                device_index,
                str(block["name"]),
                "pmos",
                role,
                x,
                p_y,
                round(units_to_um(x), 6),
                round(units_to_um(p_y), 6),
            )
        )
        device_index += 1

    # Metal1 guide stubs per transistor group.  These are not the final LVS
    # signal nets; they give DRC-visible route channels and stable pin targets.
    strap_h = to_units(0.28)
    for idx in range(count):
        sx = block_x + idx * (max(n_kind.width_units, p_kind.width_units) + device_gap)
        rects.append(Rect("metal1", sx, n_y + n_kind.height_units + to_units(0.2), min(sx + to_units(1.1), block_x + block_width), n_y + n_kind.height_units + to_units(0.2) + strap_h))

    return block_width, block_height, device_index


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


def write_extract_tcl(path: Path) -> None:
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
                "extract style ngspice()",
                "extract unique",
                "extract path extfiles",
                "extract no all",
                "extract all",
                "ext2spice lvs",
                "ext2spice -p extfiles -o ../layout/$topcell.current_pdk.spice",
                "ext2spice cthresh 0",
                "ext2spice rthresh 0",
                "ext2spice -p extfiles -o ../layout/$topcell.current_pdk_rc.spice",
                "quit -noprompt",
            ]
        )
        + "\n"
    )


DRC_RE = re.compile(r"(?:Total DRC errors found|DRC error count):\s*(\d+)")


def parse_drc_count(text: str) -> int | None:
    matches = DRC_RE.findall(text)
    if not matches:
        return None
    return int(matches[-1])


def run_magic(
    *,
    cell: str,
    magic_dir: Path,
    tcl: Path,
    log: Path,
    magic: str,
    magic_rc: Path,
) -> str:
    env = os.environ.copy()
    env["MAGIC_TOPCELL"] = cell
    resolved_magic_rc = magic_rc.resolve()
    if len(resolved_magic_rc.parents) >= 4:
        env.setdefault("PDK", resolved_magic_rc.parents[2].name)
        env.setdefault("PDK_ROOT", str(resolved_magic_rc.parents[3]))
    proc = subprocess.run(
        [magic, "-dnull", "-noconsole", "-rcfile", str(magic_rc)],
        cwd=magic_dir,
        input=tcl.read_text(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        check=False,
    )
    log.write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"Magic failed for {cell}; see {log}")
    return proc.stdout


def write_lef(path: Path, *, cell: str, width_um: float, height_um: float, pins: list[PinShape]) -> None:
    lines = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        f"MACRO {cell}",
        "  CLASS BLOCK ;",
        f"  FOREIGN {cell} 0.000 0.000 ;",
        "  ORIGIN 0.000 0.000 ;",
        f"  SIZE {width_um:.6f} BY {height_um:.6f} ;",
        "  SYMMETRY X Y ;",
    ]
    for pin in pins:
        lines.extend(
            [
                f"  PIN {pin.name}",
                f"    DIRECTION {pin.direction} ;",
                f"    USE {pin.use} ;",
                "    PORT",
                "      LAYER Metal3 ;",
                f"        RECT {pin.xlo / UNITS_PER_UM:.6f} {pin.ylo / UNITS_PER_UM:.6f} "
                f"{pin.xhi / UNITS_PER_UM:.6f} {pin.yhi / UNITS_PER_UM:.6f} ;",
                "    END",
                f"  END {pin.name}",
            ]
        )
    lines.extend(
        [
            "  OBS",
            "    LAYER Metal1 ;",
            f"      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;",
            "    LAYER Metal2 ;",
            f"      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;",
            "  END",
            f"END {cell}",
            "END LIBRARY",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def write_blackbox_spice(path: Path, cell: str, pins: list[PinShape]) -> None:
    pin_order = " ".join(pin.name for pin in pins)
    path.write_text(
        "\n".join(
            [
                f"* Blackbox SPICE contract for {cell}",
                f"* RC1 physical selected-path periphery slice; extracted transistor netlist is emitted separately.",
                f".subckt {cell} {pin_order}",
                f".ends {cell}",
            ]
        )
        + "\n"
    )


def write_summary(result: LayoutResult, out_dir: Path, blocks: list[dict[str, object]], devices: list[DevicePlacement]) -> None:
    lines = [
        f"# {result.cell} Physical Periphery Slice RC1",
        "",
        f"- Status: `{result.status}`.",
        f"- Footprint: `{result.width_um:.3f}um x {result.height_um:.3f}um` = `{result.area_um2:.3f}um^2`.",
        f"- Devices placed: `{result.device_count}` (`{result.nmos_count}` NMOS, `{result.pmos_count}` PMOS).",
        f"- Pins: `{result.pin_count}` route-facing Metal3 pins.",
        f"- DRC errors: `{result.drc_errors if result.drc_errors is not None else 'not parsed'}`.",
        "",
        "## Blocks",
        "",
        "| Block | Intent | NMOS | PMOS |",
        "| --- | --- | ---: | ---: |",
    ]
    for block in blocks:
        lines.append(
            f"| `{block['name']}` | {block['description']} | "
            f"{len(block['n_roles'])} | {len(block['p_roles'])} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Magic: `{result.magic}`",
            f"- GDS: `{result.gds}`",
            f"- LEF: `{result.lef}`",
            f"- Blackbox SPICE: `{result.spice}`",
            f"- Reference CDL: `{result.reference_cdl}`",
            f"- Extracted SPICE: `{result.extracted_spice}`",
            f"- Extracted RC SPICE: `{result.extracted_rc_spice}`",
            f"- Pins JSON: `{result.pins_json}`",
            f"- Placements CSV: `{result.placements_csv}`",
            f"- DRC log: `{result.drc_log}`",
            f"- Extract log: `{result.extract_log}`",
            f"- Netgen LVS log: `{result.netgen_lvs_log}`",
            "",
            "## Signoff Status",
            "",
            "This RC2 slice is physical placement plus generated two-sided route trunks. It is",
            "Magic DRC clean and checked with `make check-12t-periphery-slice-layout-lvs`",
            "against the generated reference CDL.",
            "Transistor W/L is not edited.",
        ]
    )
    Path(result.summary_md).write_text("\n".join(lines) + "\n")
    (out_dir / "MANIFEST.json").write_text(json.dumps(asdict(result), indent=2) + "\n")


def write_placements_csv(path: Path, placements: list[DevicePlacement]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(DevicePlacement.__dataclass_fields__.keys()))
        writer.writeheader()
        for placement in placements:
            writer.writerow(asdict(placement))


def build(args: argparse.Namespace) -> LayoutResult:
    out_dir = args.out_dir
    magic_dir = out_dir / "magic"
    layout_dir = out_dir / "layout"
    abstract_dir = out_dir / "abstract"
    for directory in (magic_dir, layout_dir, abstract_dir):
        directory.mkdir(parents=True, exist_ok=True)

    n_kind, nmos_rects, tech, magscale = load_device(args.tim_magic_dir, NMOS_SOURCE, "periphery_nmos")
    p_kind, pmos_rects, p_tech, _p_magscale = load_device(args.tim_magic_dir, PMOS_SOURCE, "periphery_pmos")
    if p_tech != tech:
        raise ValueError(f"primitive tech mismatch: {tech} vs {p_tech}")

    blocks = block_specs()
    rects: list[Rect] = []
    labels: list[Label] = []
    pins: list[PinShape] = []
    placements: list[DevicePlacement] = []

    pad = to_units(args.edge_margin_um)
    block_gap = to_units(args.block_gap_um)
    device_gap = to_units(args.device_gap_um)
    row_gap = to_units(args.row_gap_um)
    well_margin = to_units(args.well_margin_um)
    pin_w = to_units(args.pin_width_um)
    pin_h = to_units(args.pin_height_um)
    track_pitch = to_units(args.track_pitch_um)

    block_x = pad
    lower_route_slots = sum(len(block["n_roles"]) * 3 for block in blocks) + len(blocks) + 8
    lower_track_base_y = to_units(1.6)
    lower_channel_top = lower_track_base_y + max(lower_route_slots, 1) * track_pitch
    block_y = lower_channel_top + pad
    port = 1
    device_index = 1
    block_bboxes: list[dict[str, object]] = []
    for block in blocks:
        width, height, device_index = place_block(
            rects=rects,
            placements=placements,
            block=block,
            block_x=block_x,
            block_y=block_y,
            nmos_rects=nmos_rects,
            pmos_rects=pmos_rects,
            n_kind=n_kind,
            p_kind=p_kind,
            device_gap=device_gap,
            row_gap=row_gap,
            well_margin=well_margin,
            device_index_start=device_index,
        )
        block_bboxes.append(
            {
                "name": block["name"],
                "xlo": block_x,
                "ylo": block_y,
                "xhi": block_x + width,
                "yhi": block_y + height,
                "bbox_um": [
                    round(units_to_um(block_x), 6),
                    round(units_to_um(block_y), 6),
                    round(units_to_um(block_x + width), 6),
                    round(units_to_um(block_y + height), 6),
                ],
            }
        )
        block_x += width + block_gap

    route_terms = collect_route_terms(placements)
    for block_box in block_bboxes:
        tap_x = int(block_box["xhi"]) + max(to_units(1.2), block_gap // 2)
        tap_xlo = int(block_box["xhi"]) - to_units(0.4)
        tap_xhi = tap_x + to_units(1.6)
        block_y0 = int(block_box["ylo"])
        block_y1 = int(block_box["yhi"])
        lower_top = block_y0 + to_units(5.2)
        upper_bot = block_y1 - to_units(5.2)
        rects.append(Rect("pwell", tap_xlo, block_y0, tap_xhi, lower_top))
        rects.append(Rect("nwell", tap_xlo, upper_bot, tap_xhi, block_y1))
        add_tap(rects, route_terms, net="VSS", x=tap_x, y=block_y0 + to_units(2.4), kind="psub", block=str(block_box["name"]))
        add_tap(rects, route_terms, net="VDD", x=tap_x, y=block_y1 - to_units(2.4), kind="nsub", block=str(block_box["name"]))

    _xlo, _ylo, xhi, yhi = bbox(rects)

    pin_names: list[str] = []
    for block in blocks:
        pin_names.extend(list(block["pins"]))
    seen: set[str] = set()
    ordered_pin_names = []
    for name in pin_names:
        if name not in seen:
            ordered_pin_names.append(name)
            seen.add(name)

    # Reserve rail space before pins are placed, so the signal pins can be
    # routed into the same M2 rail field.
    rail_nets = {term.net for term in route_terms} | {"VDD", "VSS"} | set(ordered_pin_names)
    trunk_base_x = xhi + pad
    trunk_pitch = to_units(0.70)
    trunk_x = trunk_x_for_nets(ordered_route_nets_from_names(rail_nets), trunk_base_x)
    total_width = trunk_base_x + to_units(1.0) + max(len(rail_nets), 1) * trunk_pitch + pad
    route_base_y = yhi + pad
    rail_pitch = to_units(args.rail_pitch_um)
    rail_width = to_units(args.rail_width_um)
    route_width = to_units(args.route_width_um)
    rail_top = route_base_y + max(len(rail_nets), 1) * rail_pitch
    expected_route_terms = len(route_terms) + 2 + len(ordered_pin_names)
    track_base_y = rail_top + to_units(1.2)
    track_top = track_base_y + max(expected_route_terms, 1) * track_pitch
    total_height = track_top + pad + to_units(5.0)

    add_pin(
        rects,
        labels,
        pins,
        name="VDD",
        x=trunk_x["VDD"] - pin_w // 2,
        y=total_height - to_units(2.7),
        w=pin_w,
        h=to_units(1.2),
        port=port,
    )
    route_terms.append(RouteTerm("VDD", "pin", trunk_x["VDD"], total_height - to_units(2.1), "pin", "VDD", "pin"))
    port += 1
    add_pin(rects, labels, pins, name="VSS", x=trunk_x["VSS"] - pin_w // 2, y=to_units(1.0), w=pin_w, h=to_units(1.2), port=port)
    route_terms.append(RouteTerm("VSS", "pin", trunk_x["VSS"], to_units(1.6), "pin", "VSS", "pin"))
    port += 1

    for idx, name in enumerate(ordered_pin_names):
        center = trunk_x[name]
        y = to_units(0.55) if idx % 2 == 0 else total_height - to_units(1.15)
        add_pin(
            rects,
            labels,
            pins,
            name=name,
            x=max(0, center - pin_w // 2),
            y=y,
            w=pin_w,
            h=pin_h,
            port=port,
        )
        route_terms.append(RouteTerm(name, "pin", max(0, center - pin_w // 2) + pin_w // 2, y + pin_h // 2, "pin", name, "pin"))
        port += 1

    add_lvs_routing(
        rects,
        route_terms,
        total_width=total_width,
        route_base_y=route_base_y,
        lower_track_base_y=lower_track_base_y,
        rail_pitch=rail_pitch,
        track_base_y=track_base_y,
        track_pitch=track_pitch,
        trunk_base_x=trunk_base_x,
        rail_width=rail_width,
        route_width=route_width,
        via2_size=to_units(0.285),
    )

    cell_bbox = bbox(rects)
    mag_path = magic_dir / f"{CELL_NAME}.mag"
    write_magic(
        mag_path,
        cell=CELL_NAME,
        tech=tech,
        magscale=magscale,
        rects=rects,
        labels=labels,
        properties={
            "FIXED_BBOX": f"0 0 {cell_bbox[2]} {cell_bbox[3]}",
            "DETRONYX_PHYSICAL_CELL": CELL_NAME,
            "DETRONYX_SOURCE_NMOS": NMOS_SOURCE,
            "DETRONYX_SOURCE_PMOS": PMOS_SOURCE,
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_PERIPHERY_STATUS": "selected_path_physical_routing_rc2",
            "DETRONYX_LVS_STATUS": "netgen_lvs_clean_against_reference_cdl",
        },
    )

    drc_tcl = magic_dir / "run_periphery_slice_drc.tcl"
    extract_tcl = magic_dir / "extract_periphery_slice.tcl"
    write_drc_tcl(drc_tcl)
    write_extract_tcl(extract_tcl)

    drc_log = layout_dir / f"{CELL_NAME}.drc.log"
    extract_log = layout_dir / f"{CELL_NAME}.magic.log"
    netgen_lvs_log = layout_dir / f"{CELL_NAME}.netgen_lvs.log"
    drc_errors = None
    if args.run_drc:
        drc_text = run_magic(
            cell=CELL_NAME,
            magic_dir=magic_dir,
            tcl=drc_tcl,
            log=drc_log,
            magic=args.magic,
            magic_rc=args.magic_rc,
        )
        drc_errors = parse_drc_count(drc_text)

    run_magic(
        cell=CELL_NAME,
        magic_dir=magic_dir,
        tcl=extract_tcl,
        log=extract_log,
        magic=args.magic,
        magic_rc=args.magic_rc,
    )

    gds = layout_dir / f"{CELL_NAME}.gds"
    lef = abstract_dir / f"{CELL_NAME}.lef"
    spice = abstract_dir / f"{CELL_NAME}.blackbox.spice"
    pins_json = abstract_dir / f"{CELL_NAME}.pins.json"
    reference_cdl = abstract_dir / f"{CELL_NAME}.reference.cdl"
    placements_csv = out_dir / f"{CELL_NAME}.placements.csv"
    summary_md = out_dir / "summary.md"
    extracted_spice = layout_dir / f"{CELL_NAME}.current_pdk.spice"
    extracted_rc_spice = layout_dir / f"{CELL_NAME}.current_pdk_rc.spice"

    width_um, height_um, area_um2 = dims_um(cell_bbox)
    write_lef(lef, cell=CELL_NAME, width_um=width_um, height_um=height_um, pins=pins)
    write_blackbox_spice(spice, CELL_NAME, pins)
    write_reference_cdl(reference_cdl, pins, placements, cell=CELL_NAME)
    write_placements_csv(placements_csv, placements)
    pins_json.write_text(
        json.dumps(
            {
                "cell": CELL_NAME,
                "status": "selected_path_physical_routing_rc2",
                "pins": [asdict(pin) for pin in pins],
                "blocks": block_bboxes,
                "route_terms": [asdict(term) for term in route_terms],
                "primitive_sources": {
                    "nmos": asdict(n_kind),
                    "pmos": asdict(p_kind),
                },
            },
            indent=2,
        )
        + "\n"
    )

    result = LayoutResult(
        cell=CELL_NAME,
        status="selected_path_physical_routing_rc2",
        width_um=width_um,
        height_um=height_um,
        area_um2=area_um2,
        device_count=len(placements),
        nmos_count=sum(1 for p in placements if p.mos == "nmos"),
        pmos_count=sum(1 for p in placements if p.mos == "pmos"),
        pin_count=len(pins),
        magic=str(mag_path),
        gds=str(gds),
        lef=str(lef),
        spice=str(spice),
        pins_json=str(pins_json),
        reference_cdl=str(reference_cdl),
        placements_csv=str(placements_csv),
        summary_md=str(summary_md),
        drc_errors=drc_errors,
        drc_log=str(drc_log),
        extract_log=str(extract_log),
        netgen_lvs_log=str(netgen_lvs_log),
        extracted_spice=str(extracted_spice),
        extracted_rc_spice=str(extracted_rc_spice),
    )
    write_summary(result, out_dir, blocks, placements)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tim-magic-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--magic", default="magic")
    parser.add_argument("--magic-rc", type=Path, required=True)
    parser.add_argument("--run-drc", action="store_true")
    parser.add_argument("--edge-margin-um", type=float, default=4.0)
    parser.add_argument("--block-gap-um", type=float, default=6.0)
    parser.add_argument("--device-gap-um", type=float, default=1.2)
    parser.add_argument("--row-gap-um", type=float, default=4.0)
    parser.add_argument("--well-margin-um", type=float, default=1.2)
    parser.add_argument("--pin-width-um", type=float, default=0.36)
    parser.add_argument("--pin-height-um", type=float, default=0.8)
    parser.add_argument("--rail-pitch-um", type=float, default=0.78)
    parser.add_argument("--track-pitch-um", type=float, default=0.75)
    parser.add_argument("--rail-width-um", type=float, default=0.24)
    parser.add_argument("--route-width-um", type=float, default=0.22)
    args = parser.parse_args()

    result = build(args)
    print(
        f"{result.cell}: {result.width_um:.3f}um x {result.height_um:.3f}um, "
        f"{result.device_count} devices, DRC={result.drc_errors}"
    )


if __name__ == "__main__":
    main()
