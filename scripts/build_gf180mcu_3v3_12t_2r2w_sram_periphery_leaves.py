#!/usr/bin/env python3
"""Split the 12T 2W2R periphery slice into LVS-clean physical leaf blocks.

The selected-path slice is useful for timing, but the full macro needs smaller
physical blocks that can be tiled: row decoders/WL drivers per port, column
write drivers, read precharge/sense, and conflict control.  This generator
reuses the same Tim-derived 3.3V MOS primitives and role-to-net contract as the
slice generator, but emits one extractable block per functional region.
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

from build_gf180mcu_3v3_12t_2r2w_sram_periphery_slice import (
    NMOS_SOURCE,
    PMOS_SOURCE,
    UNITS_PER_UM,
    PinShape,
    RouteTerm,
    add_lvs_routing,
    add_pin,
    add_tap,
    block_specs,
    collect_route_terms,
    load_device,
    ordered_route_nets_from_names,
    place_block,
    run_magic,
    to_units,
    trunk_x_for_nets,
    units_to_um,
    write_drc_tcl,
    write_extract_tcl,
    write_lef,
    write_reference_cdl,
)
from build_physical_cells import bbox, dims_um, write_magic


@dataclass(frozen=True)
class BlockLeafResult:
    cell: str
    block: str
    status: str
    width_um: float
    height_um: float
    area_um2: float
    device_count: int
    nmos_count: int
    pmos_count: int
    pin_count: int
    drc_errors: int | None
    lvs_result: str
    disconnected_pins: int | None
    magic: str
    gds: str
    lef: str
    reference_cdl: str
    extracted_spice: str
    extracted_rc_spice: str
    drc_log: str
    extract_log: str
    netgen_lvs_log: str
    pins_json: str
    placements_csv: str


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", name)


def lvs_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    text = path.read_text(errors="ignore")
    if "Result: Circuits match uniquely" in text or "Netlists match uniquely" in text:
        return "match_unique"
    if "Circuits match correctly" in text:
        return "match"
    if "Netlists do not match" in text:
        return "mismatch"
    return "unknown"


def disconnected_pin_count(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(errors="ignore")
    matches = re.findall(r"Circuit contains \d+ nets, and (\d+) disconnected pins", text)
    if matches:
        return max(int(item) for item in matches)
    if "disconnected pins" not in text:
        return 0
    return None


def run_netgen_lvs(
    *,
    cell: str,
    layout_spice: Path,
    reference_cdl: Path,
    netgen_lvs: str,
    netgen_setup: Path,
    log: Path,
    stdout_log: Path,
) -> None:
    proc = subprocess.run(
        [
            netgen_lvs,
            "-batch",
            "lvs",
            f"{layout_spice} {cell}",
            f"{reference_cdl} {cell}",
            str(netgen_setup),
            str(log),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    stdout_log.write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"Netgen LVS failed for {cell}; see {stdout_log}")


def unique_pin_names(block: dict[str, object]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for name in ["VDD", "VSS", *list(block["pins"])]:
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def write_placements_csv(path: Path, placements: list[object]) -> None:
    if not placements:
        path.write_text("")
        return
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(placements[0].__dataclass_fields__.keys()))
        writer.writeheader()
        for placement in placements:
            writer.writerow(asdict(placement))


def build_block(args: argparse.Namespace, block: dict[str, object]) -> BlockLeafResult:
    cell = f"detronyx_12t_{sanitize(str(block['name']))}_rc1"
    block_dir = args.out_dir / cell
    magic_dir = block_dir / "magic"
    layout_dir = block_dir / "layout"
    abstract_dir = block_dir / "abstract"
    for directory in (magic_dir, layout_dir, abstract_dir):
        directory.mkdir(parents=True, exist_ok=True)

    n_kind, nmos_rects, tech, magscale = load_device(args.tim_magic_dir, NMOS_SOURCE, "periphery_nmos")
    p_kind, pmos_rects, p_tech, _p_magscale = load_device(args.tim_magic_dir, PMOS_SOURCE, "periphery_pmos")
    if p_tech != tech:
        raise ValueError(f"primitive tech mismatch: {tech} vs {p_tech}")

    rects: list[object] = []
    labels: list[object] = []
    pins: list[PinShape] = []
    placements: list[object] = []

    pad = to_units(args.edge_margin_um)
    device_gap = to_units(args.device_gap_um)
    row_gap = to_units(args.row_gap_um)
    well_margin = to_units(args.well_margin_um)
    track_pitch = to_units(args.track_pitch_um)
    rail_pitch = to_units(args.rail_pitch_um)
    rail_width = to_units(args.rail_width_um)
    route_width = to_units(args.route_width_um)
    pin_w = to_units(args.pin_width_um)
    pin_h = to_units(args.pin_height_um)

    lower_route_slots = max(len(block["n_roles"]) * 3 + len(block["p_roles"]) + 8, 12)
    lower_track_base_y = to_units(1.4)
    lower_channel_top = lower_track_base_y + lower_route_slots * track_pitch
    block_x = pad
    block_y = lower_channel_top + pad
    block_width, _block_height, _next_index = place_block(
        rects=rects,  # type: ignore[arg-type]
        placements=placements,  # type: ignore[arg-type]
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
        device_index_start=1,
    )

    route_terms = collect_route_terms(placements)  # type: ignore[arg-type]
    _x0, _y0, xhi, yhi = bbox(rects)  # type: ignore[arg-type]
    tap_x = xhi + to_units(1.0)
    rects.append(type(rects[0])("pwell", xhi - to_units(0.4), block_y, tap_x + to_units(1.6), block_y + to_units(5.2)))
    rects.append(type(rects[0])("nwell", xhi - to_units(0.4), yhi - to_units(5.2), tap_x + to_units(1.6), yhi))
    add_tap(rects, route_terms, net="VSS", x=tap_x, y=block_y + to_units(2.4), kind="psub", block=str(block["name"]))  # type: ignore[arg-type]
    add_tap(rects, route_terms, net="VDD", x=tap_x, y=yhi - to_units(2.4), kind="nsub", block=str(block["name"]))  # type: ignore[arg-type]
    _x0, _y0, xhi, yhi = bbox(rects)  # type: ignore[arg-type]

    pin_names = unique_pin_names(block)
    rail_nets = {term.net for term in route_terms} | set(pin_names)
    trunk_base_x = xhi + pad
    trunk_x = trunk_x_for_nets(ordered_route_nets_from_names(rail_nets), trunk_base_x)
    total_width = trunk_base_x + to_units(1.0) + max(len(rail_nets), 1) * to_units(0.70) + pad
    route_base_y = yhi + pad
    rail_top = route_base_y + max(len(rail_nets), 1) * rail_pitch
    expected_terms = len(route_terms) + len(pin_names)
    track_base_y = rail_top + to_units(1.2)
    track_top = track_base_y + max(expected_terms, 1) * track_pitch
    total_height = track_top + pad + to_units(3.0)

    port = 1
    for idx, name in enumerate(pin_names):
        if name == "VDD":
            y = total_height - to_units(2.6)
        elif name == "VSS":
            y = to_units(0.7)
        else:
            y = to_units(0.7) if idx % 2 == 0 else total_height - to_units(1.5)
        x_center = trunk_x[name]
        add_pin(
            rects,  # type: ignore[arg-type]
            labels,  # type: ignore[arg-type]
            pins,
            name=name,
            x=x_center - pin_w // 2,
            y=y,
            w=pin_w,
            h=pin_h if name not in {"VDD", "VSS"} else to_units(1.2),
            port=port,
        )
        route_terms.append(RouteTerm(name, "pin", x_center, y + pin_h // 2, "pin", name, "pin"))
        port += 1

    add_lvs_routing(
        rects,  # type: ignore[arg-type]
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

    cell_bbox = bbox(rects)  # type: ignore[arg-type]
    magic_path = magic_dir / f"{cell}.mag"
    write_magic(
        magic_path,
        cell=cell,
        tech=tech,
        magscale=magscale,
        rects=rects,  # type: ignore[arg-type]
        labels=labels,  # type: ignore[arg-type]
        properties={
            "FIXED_BBOX": f"0 0 {cell_bbox[2]} {cell_bbox[3]}",
            "DETRONYX_PERIPHERY_BLOCK": str(block["name"]),
            "DETRONYX_TRANSISTOR_RESIZE_ALLOWED": "false",
            "DETRONYX_LVS_STATUS": "block_leaf_reference_cdl",
        },
    )

    drc_tcl = magic_dir / "run_block_drc.tcl"
    extract_tcl = magic_dir / "extract_block.tcl"
    write_drc_tcl(drc_tcl)
    write_extract_tcl(extract_tcl)

    drc_log = layout_dir / f"{cell}.drc.log"
    extract_log = layout_dir / f"{cell}.magic.log"
    drc_errors = None
    if args.run_drc:
        drc_text = run_magic(cell=cell, magic_dir=magic_dir, tcl=drc_tcl, log=drc_log, magic=args.magic, magic_rc=args.magic_rc)
        matches = re.findall(r"(?:Total DRC errors found|DRC error count):\s*(\d+)", drc_text)
        drc_errors = int(matches[-1]) if matches else None
    run_magic(cell=cell, magic_dir=magic_dir, tcl=extract_tcl, log=extract_log, magic=args.magic, magic_rc=args.magic_rc)

    gds = layout_dir / f"{cell}.gds"
    lef = abstract_dir / f"{cell}.lef"
    reference = abstract_dir / f"{cell}.reference.cdl"
    pins_json = abstract_dir / f"{cell}.pins.json"
    placements_csv = block_dir / f"{cell}.placements.csv"
    extracted = layout_dir / f"{cell}.current_pdk.spice"
    extracted_rc = layout_dir / f"{cell}.current_pdk_rc.spice"
    lvs_log = layout_dir / f"{cell}.netgen_lvs.log"
    lvs_stdout = layout_dir / f"{cell}.netgen_stdout.log"

    width_um, height_um, area_um2 = dims_um(cell_bbox)
    write_lef(lef, cell=cell, width_um=width_um, height_um=height_um, pins=pins)
    write_reference_cdl(reference, pins, placements, cell=cell)  # type: ignore[arg-type]
    write_placements_csv(placements_csv, placements)
    pins_json.write_text(
        json.dumps(
            {
                "cell": cell,
                "block": block["name"],
                "status": "block_leaf_rc1",
                "pins": [asdict(pin) for pin in pins],
                "route_terms": [asdict(term) for term in route_terms],
                "primitive_sources": {"nmos": asdict(n_kind), "pmos": asdict(p_kind)},
            },
            indent=2,
        )
        + "\n"
    )

    if args.run_lvs:
        run_netgen_lvs(
            cell=cell,
            layout_spice=extracted,
            reference_cdl=reference,
            netgen_lvs=args.netgen_lvs,
            netgen_setup=args.netgen_setup,
            log=lvs_log,
            stdout_log=lvs_stdout,
        )

    return BlockLeafResult(
        cell=cell,
        block=str(block["name"]),
        status="block_leaf_rc1",
        width_um=round(width_um, 6),
        height_um=round(height_um, 6),
        area_um2=round(area_um2, 6),
        device_count=len(placements),
        nmos_count=sum(1 for placement in placements if placement.mos == "nmos"),
        pmos_count=sum(1 for placement in placements if placement.mos == "pmos"),
        pin_count=len(pins),
        drc_errors=drc_errors,
        lvs_result=lvs_status(lvs_log),
        disconnected_pins=disconnected_pin_count(lvs_log),
        magic=str(magic_path),
        gds=str(gds),
        lef=str(lef),
        reference_cdl=str(reference),
        extracted_spice=str(extracted),
        extracted_rc_spice=str(extracted_rc),
        drc_log=str(drc_log),
        extract_log=str(extract_log),
        netgen_lvs_log=str(lvs_log),
        pins_json=str(pins_json),
        placements_csv=str(placements_csv),
    )


def macro_estimates(results: list[BlockLeafResult]) -> list[dict[str, object]]:
    by_block = {result.block: result for result in results}
    out: list[dict[str, object]] = []
    for name, rows, data_width in [
        ("detronyx_12t_2w2r_512x8_macro_shell_rc1", 512, 8),
        ("detronyx_12t_2w2r_512x32_macro_shell_rc1", 512, 32),
        ("detronyx_12t_2w2r_1024x8_macro_shell_rc1", 1024, 8),
        ("detronyx_12t_2w2r_1024x32_macro_shell_rc1", 1024, 32),
    ]:
        write_ports = 2
        read_ports = 2
        row_ports = write_ports + read_ports
        write_row_decode_instances = rows * write_ports
        read_row_decode_instances = rows * read_ports
        row_decode_instances = write_row_decode_instances + read_row_decode_instances
        write_driver_instances = data_width * 2
        precharge_sense_instances = data_width * 2
        conflict_instances = 1
        area_um2 = (
            write_row_decode_instances * by_block["write_row_decode7_wl_driver"].area_um2
            + read_row_decode_instances * by_block["read_row_decode7_wl_driver"].area_um2
            + write_driver_instances * by_block["write_driver"].area_um2
            + precharge_sense_instances * by_block["precharge_sense"].area_um2
            + conflict_instances * by_block["write_conflict"].area_um2
        )
        devices = (
            write_row_decode_instances * by_block["write_row_decode7_wl_driver"].device_count
            + read_row_decode_instances * by_block["read_row_decode7_wl_driver"].device_count
            + write_driver_instances * by_block["write_driver"].device_count
            + precharge_sense_instances * by_block["precharge_sense"].device_count
            + conflict_instances * by_block["write_conflict"].device_count
        )
        row_select_devices = 16
        shared_predecode_devices_per_port = 120
        shared_predecode_devices = (
            rows * row_ports * row_select_devices
            + row_ports * shared_predecode_devices_per_port
        )
        shared_predecode_total_devices = (
            shared_predecode_devices
            + write_driver_instances * by_block["write_driver"].device_count
            + precharge_sense_instances * by_block["precharge_sense"].device_count
            + conflict_instances * by_block["write_conflict"].device_count
        )
        out.append(
            {
                "macro": name,
                "rows": rows,
                "data_width": data_width,
                "write_ports": write_ports,
                "read_ports": read_ports,
                "row_ports": row_ports,
                "write_row_decode_instances": write_row_decode_instances,
                "read_row_decode_instances": read_row_decode_instances,
                "row_decode_instances": row_decode_instances,
                "write_driver_instances": write_driver_instances,
                "precharge_sense_instances": precharge_sense_instances,
                "conflict_instances": conflict_instances,
                "row_select_devices_per_row_port": row_select_devices,
                "shared_predecode_devices_per_port": shared_predecode_devices_per_port,
                "uncompacted_leaf_area_mm2": round(area_um2 / 1_000_000.0, 6),
                "uncompacted_leaf_devices": devices,
                "shared_predecode_device_estimate": shared_predecode_total_devices,
                "shared_predecode_note": "2W2R estimate: four row ports share predecode per port; per-row row-select/WL stages remain per port",
                "note": "upper-bound leaf-placement estimate; do not tile the selected-path row decoder per row in the final macro",
            }
        )
    return out


def write_summary(results: list[BlockLeafResult], estimates: list[dict[str, object]], out_dir: Path) -> None:
    with (out_dir / "summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(BlockLeafResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))
    (out_dir / "MANIFEST.json").write_text(json.dumps([asdict(result) for result in results], indent=2) + "\n")
    (out_dir / "macro_matrix_estimates.json").write_text(json.dumps(estimates, indent=2) + "\n")

    lines = [
        "# 12T Periphery Block Leaves RC1",
        "",
        "These are split, extractable transistor-level periphery leaves built from the",
        "same Tim-derived GF180 3.3V MOS primitives as the selected-path slice.",
        "",
        "| Leaf | Block | Devices | Size | Area | DRC | LVS | Disconnected Pins |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for result in results:
        lines.append(
            f"| `{result.cell}` | `{result.block}` | `{result.device_count}` | "
            f"`{result.width_um:.3f}um x {result.height_um:.3f}um` | "
            f"`{result.area_um2:.3f}um^2` | `{result.drc_errors}` | "
            f"`{result.lvs_result}` | `{result.disconnected_pins}` |"
        )
    lines.extend(
        [
            "",
            "## Macro Matrix Upper-Bound Estimate",
            "",
            "This is a deliberately pessimistic count using un-abutted leaf footprints.",
            "It is not the final area target; the next pass must share predecode, rails,",
            "and taps before full macro DRC/LVS.",
            "",
            "| Macro | Naive row decode leaves | Write driver leaves | Read leaves | Naive devices | Shared-predecode devices | Naive leaf area |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for estimate in estimates:
        lines.append(
            f"| `{estimate['macro']}` | `{estimate['write_row_decode_instances']}W + {estimate['read_row_decode_instances']}R` | "
            f"`{estimate['write_driver_instances']}` | `{estimate['precharge_sense_instances']}` | "
            f"`{estimate['uncompacted_leaf_devices']}` | `{estimate['shared_predecode_device_estimate']}` | "
            f"`{estimate['uncompacted_leaf_area_mm2']:.6f}mm^2` |"
        )
    lines.extend(
        [
            "",
            "## Status",
            "",
            "This closes the block-leaf physical split.  Full macro signoff remains open",
            "until these leaves are tiled, routed to the 12T array, extracted, and checked",
            "with full macro LVS/PEX/antenna/EMIR.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tim-magic-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--magic", default="magic")
    parser.add_argument("--magic-rc", type=Path, required=True)
    parser.add_argument("--netgen-lvs", default="netgen-lvs")
    parser.add_argument("--netgen-setup", type=Path, required=True)
    parser.add_argument("--run-drc", action="store_true")
    parser.add_argument("--run-lvs", action="store_true")
    parser.add_argument("--edge-margin-um", type=float, default=3.0)
    parser.add_argument("--device-gap-um", type=float, default=1.0)
    parser.add_argument("--row-gap-um", type=float, default=3.2)
    parser.add_argument("--well-margin-um", type=float, default=1.0)
    parser.add_argument("--pin-width-um", type=float, default=0.36)
    parser.add_argument("--pin-height-um", type=float, default=0.8)
    parser.add_argument("--rail-pitch-um", type=float, default=0.72)
    parser.add_argument("--track-pitch-um", type=float, default=0.70)
    parser.add_argument("--rail-width-um", type=float, default=0.24)
    parser.add_argument("--route-width-um", type=float, default=0.22)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = [build_block(args, block) for block in block_specs()]
    estimates = macro_estimates(results)
    write_summary(results, estimates, args.out_dir)
    for result in results:
        print(
            f"{result.cell}: {result.width_um:.3f}um x {result.height_um:.3f}um, "
            f"devices={result.device_count}, DRC={result.drc_errors}, LVS={result.lvs_result}, "
            f"disconnected={result.disconnected_pins}"
        )
    return 0 if all(r.drc_errors == 0 and r.lvs_result in {"match", "match_unique"} and r.disconnected_pins == 0 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
