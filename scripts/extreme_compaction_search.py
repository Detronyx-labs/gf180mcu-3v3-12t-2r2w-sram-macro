#!/usr/bin/env python3
"""Generate and check aggressive GF180 SRAM leaf placement variants.

The script is intentionally layout-first and conservative:

* source Magic geometry is never modified in place;
* transistor/device rectangles are copied exactly; no W/L or rectangle resizing;
* SRAM-special Timothy layers are normalized to public GF180 Magic layers;
* all candidates are written under build/;
* every candidate is gated by Magic drc(full);
* the search reports only DRC-clean bbox wins as usable candidates.

The first use is the Timothy 3.3V 6T seed. The same machinery is meant to drive
the Detronyx 12T/10T leaf once transistor groups are drawn as Magic geometry.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


LAYER_MAP = {
    "sramnfet": "nfet",
    "srampfet": "pfet",
    "sramndiff": "ndiff",
    "srampdiff": "pdiff",
    "sramndc": "ndiffc",
    "srampdc": "pdiffc",
    "nmos": "nfet",
    "pmos": "pfet",
}

DEVICE_LAYERS = {
    "nfet",
    "pfet",
    "ndiff",
    "pdiff",
    "ndiffc",
    "pdiffc",
    "polysilicon",
    "polycontact",
}

MAG_UNITS_PER_UM_DEFAULT = 200.0
RECT_RE = re.compile(r"^rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$")
LAYER_RE = re.compile(r"^<<\s+(.+?)\s+>>$")
DRC_RE = re.compile(r"(?:Total DRC errors found|DRC error count):\s*(\d+)")


@dataclass(frozen=True)
class Rect:
    layer: str
    xlo: int
    ylo: int
    xhi: int
    yhi: int

    def transform(self, fn: Callable[[int, int], tuple[int, int]]) -> "Rect":
        points = [
            fn(self.xlo, self.ylo),
            fn(self.xlo, self.yhi),
            fn(self.xhi, self.ylo),
            fn(self.xhi, self.yhi),
        ]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return Rect(self.layer, min(xs), min(ys), max(xs), max(ys))

    def translate(self, dx: int, dy: int) -> "Rect":
        return Rect(self.layer, self.xlo + dx, self.ylo + dy, self.xhi + dx, self.yhi + dy)

    def width(self) -> int:
        return self.xhi - self.xlo

    def height(self) -> int:
        return self.yhi - self.ylo

    def intersects_area(self, other: "Rect") -> bool:
        return (
            self.layer == other.layer
            and max(self.xlo, other.xlo) < min(self.xhi, other.xhi)
            and max(self.ylo, other.ylo) < min(self.yhi, other.yhi)
        )


@dataclass
class Layout:
    name: str
    tech: str
    magscale: str
    rects: list[Rect]

    def bbox(self) -> tuple[int, int, int, int]:
        if not self.rects:
            return (0, 0, 0, 0)
        return (
            min(r.xlo for r in self.rects),
            min(r.ylo for r in self.rects),
            max(r.xhi for r in self.rects),
            max(r.yhi for r in self.rects),
        )

    def shifted_to_origin(self) -> "Layout":
        xlo, ylo, _xhi, _yhi = self.bbox()
        return Layout(
            name=self.name,
            tech=self.tech,
            magscale=self.magscale,
            rects=[r.translate(-xlo, -ylo) for r in self.rects],
        )

    def assert_no_device_resize(self, reference_dims: dict[str, list[tuple[int, int]]]) -> None:
        current: dict[str, list[tuple[int, int]]] = {}
        for rect in self.rects:
            if rect.layer in DEVICE_LAYERS:
                # A rotated transistor swaps X/Y, but does not change W/L.
                current.setdefault(rect.layer, []).append(tuple(sorted((rect.width(), rect.height()))))
        for layer in current:
            current[layer].sort()

        reference_total = sum(len(values) for values in reference_dims.values())
        current_total = sum(len(values) for values in current.values())
        if reference_total == 0 or current_total == 0 or current_total % reference_total != 0:
            raise ValueError(f"{self.name}: device geometry changed; refusing resized candidate")

        instance_count = current_total // reference_total
        expected: dict[str, list[tuple[int, int]]] = {}
        for layer, dims in reference_dims.items():
            expected[layer] = sorted(dims * instance_count)

        if current != expected:
            raise ValueError(f"{self.name}: device geometry changed; refusing resized candidate")

    def has_device_area_overlap(self) -> bool:
        by_layer: dict[str, list[Rect]] = {}
        for rect in self.rects:
            if rect.layer in DEVICE_LAYERS:
                by_layer.setdefault(rect.layer, []).append(rect)
        for layer_rects in by_layer.values():
            for idx, rect in enumerate(layer_rects):
                for other in layer_rects[idx + 1 :]:
                    if rect.intersects_area(other):
                        return True
        return False

    def transformed(self, name: str, fn: Callable[[int, int], tuple[int, int]]) -> "Layout":
        return Layout(
            name=name,
            tech=self.tech,
            magscale=self.magscale,
            rects=[r.transform(fn) for r in self.rects],
        ).shifted_to_origin()

    def translated(self, name: str, dx: int, dy: int) -> "Layout":
        return Layout(
            name=name,
            tech=self.tech,
            magscale=self.magscale,
            rects=[r.translate(dx, dy) for r in self.rects],
        )


@dataclass
class CandidateResult:
    name: str
    kind: str
    drc_errors: int | None
    rejected_reason: str
    width_um: float
    height_um: float
    area_um2: float
    log: Path

    @property
    def clean(self) -> bool:
        return self.drc_errors == 0


def read_magic(path: Path, name: str) -> Layout:
    tech = "gf180mcuD"
    magscale = "1 10"
    current_layer: str | None = None
    rects: list[Rect] = []

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("tech "):
            tech = line.split(maxsplit=1)[1]
            continue
        if line.startswith("magscale "):
            magscale = line.split(maxsplit=1)[1]
            continue
        match = LAYER_RE.match(line)
        if match:
            current_layer = match.group(1)
            continue
        match = RECT_RE.match(line)
        if match and current_layer and current_layer != "properties":
            layer = LAYER_MAP.get(current_layer, current_layer)
            xlo, ylo, xhi, yhi = [int(v) for v in match.groups()]
            rects.append(Rect(layer, xlo, ylo, xhi, yhi))

    if not rects:
        raise ValueError(f"No rectangles parsed from {path}")

    return Layout(name=name, tech=tech, magscale=magscale, rects=rects).shifted_to_origin()


def write_magic(layout: Layout, path: Path, variant: str) -> None:
    by_layer: dict[str, list[Rect]] = {}
    for rect in layout.rects:
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
        "polysilicon",
        "polycontact",
        "metal1",
        "via1",
        "metal2",
        "via2",
        "metal3",
    ]
    ordered_layers = [layer for layer in layer_order if layer in by_layer]
    ordered_layers.extend(sorted(layer for layer in by_layer if layer not in set(ordered_layers)))

    lines = [
        "magic",
        f"tech {layout.tech}",
        f"magscale {layout.magscale}",
        "timestamp 1780001000",
    ]
    for layer in ordered_layers:
        lines.append(f"<< {layer} >>")
        for rect in sorted(by_layer[layer], key=lambda r: (r.ylo, r.xlo, r.yhi, r.xhi)):
            if rect.xlo == rect.xhi or rect.ylo == rect.yhi:
                continue
            lines.append(f"rect {rect.xlo} {rect.ylo} {rect.xhi} {rect.yhi}")

    xlo, ylo, xhi, yhi = layout.bbox()
    lines.extend(
        [
            "<< properties >>",
            f"string DETRONYX_COMPACTION_VARIANT {variant}",
            f"string DETRONYX_GENERATED_BBOX {xlo} {ylo} {xhi} {yhi}",
            "<< end >>",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def orientation_fns() -> dict[str, Callable[[int, int], tuple[int, int]]]:
    return {
        "r0": lambda x, y: (x, y),
        "r90": lambda x, y: (-y, x),
        "r180": lambda x, y: (-x, -y),
        "r270": lambda x, y: (y, -x),
        "mx": lambda x, y: (x, -y),
        "my": lambda x, y: (-x, y),
    }


def combine(name: str, layouts: Iterable[Layout]) -> Layout:
    layouts = list(layouts)
    if not layouts:
        raise ValueError("combine() needs at least one layout")
    tech = layouts[0].tech
    magscale = layouts[0].magscale
    rects: list[Rect] = []
    for layout in layouts:
        rects.extend(layout.rects)
    return Layout(name=name, tech=tech, magscale=magscale, rects=rects).shifted_to_origin()


def dims_um(layout: Layout, units_per_um: float) -> tuple[float, float, float]:
    xlo, ylo, xhi, yhi = layout.bbox()
    width = (xhi - xlo) / units_per_um
    height = (yhi - ylo) / units_per_um
    return width, height, width * height


def run_magic_drc(layout: Layout, mag_path: Path, args: argparse.Namespace) -> CandidateResult:
    width, height, area = dims_um(layout, args.units_per_um)
    try:
        layout.assert_no_device_resize(args.reference_device_dims)
    except ValueError as exc:
        log_path = args.out_dir / "layout" / f"{layout.name}.reject.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(str(exc) + "\n")
        return CandidateResult(
            name=layout.name,
            kind=args.current_kind,
            drc_errors=None,
            rejected_reason="device-resize",
            width_um=width,
            height_um=height,
            area_um2=area,
            log=log_path,
        )

    if args.reject_device_overlap and layout.has_device_area_overlap():
        log_path = args.out_dir / "layout" / f"{layout.name}.reject.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("candidate rejected: same-layer device geometry area overlap\n")
        return CandidateResult(
            name=layout.name,
            kind=args.current_kind,
            drc_errors=None,
            rejected_reason="device-overlap",
            width_um=width,
            height_um=height,
            area_um2=area,
            log=log_path,
        )

    write_magic(layout, mag_path, layout.name)
    tcl_path = args.out_dir / "run_drc_and_gds.tcl"
    layout_dir = args.out_dir / "layout"
    layout_dir.mkdir(parents=True, exist_ok=True)
    log_path = layout_dir / f"{layout.name}.drc.log"
    gds_rel = f"../layout/{layout.name}.gds"

    tcl_path.write_text(
        "\n".join(
            [
                "crashbackups stop",
                f"load {layout.name}",
                "select top cell",
                "expand",
                "drc on",
                "drc style drc(full)",
                "drc check",
                "drc count total",
                f"gds write {gds_rel}",
                "quit -noprompt",
            ]
        )
        + "\n"
    )

    with tcl_path.open("r") as tcl, log_path.open("w") as log:
        proc = subprocess.run(
            [
                args.magic,
                "-dnull",
                "-noconsole",
                "-rcfile",
                str(args.magic_rc),
            ],
            cwd=args.magic_dir,
            stdin=tcl,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

    drc_errors: int | None = None
    log_text = log_path.read_text(errors="ignore")
    for match in DRC_RE.finditer(log_text):
        drc_errors = int(match.group(1))
    if proc.returncode != 0 and drc_errors is None:
        drc_errors = -1

    return CandidateResult(
        name=layout.name,
        kind=args.current_kind,
        drc_errors=drc_errors,
        rejected_reason="",
        width_um=width,
        height_um=height,
        area_um2=area,
        log=log_path,
    )


def evaluate(layout: Layout, args: argparse.Namespace, kind: str) -> CandidateResult:
    args.current_kind = kind
    mag_path = args.magic_dir / f"{layout.name}.mag"
    result = run_magic_drc(layout, mag_path, args)
    if result.rejected_reason:
        status = f"reject:{result.rejected_reason}"
    else:
        status = "clean" if result.clean else f"drc={result.drc_errors}"
    print(
        f"{result.name:48s} {kind:14s} {status:10s} "
        f"{result.width_um:.3f}um x {result.height_um:.3f}um = {result.area_um2:.3f}um^2"
    )
    return result


def pitch_values(start: int, stop: int, step: int) -> list[int]:
    if step <= 0:
        raise ValueError("--step must be positive")
    values = list(range(start, stop + 1, step))
    if values[-1] != stop:
        values.append(stop)
    return values


def make_pair(
    left: Layout,
    right: Layout,
    axis: str,
    pitch: int,
    name: str,
) -> Layout:
    if axis == "x":
        shifted = right.translated(right.name, pitch, 0)
    elif axis == "y":
        shifted = right.translated(right.name, 0, pitch)
    else:
        raise ValueError(axis)
    return combine(name, [left, shifted])


def run_search(args: argparse.Namespace) -> list[CandidateResult]:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.magic_dir = args.out_dir / "magic"
    args.magic_dir.mkdir(parents=True, exist_ok=True)

    base = read_magic(args.source, "tim6t_norm")
    args.reference_device_dims = {}
    for rect in base.rects:
        if rect.layer in DEVICE_LAYERS:
            args.reference_device_dims.setdefault(rect.layer, []).append(
                tuple(sorted((rect.width(), rect.height())))
            )
    for layer in args.reference_device_dims:
        args.reference_device_dims[layer].sort()
    fns = orientation_fns()
    oriented = {
        name: base.transformed(f"tim6t_{name}", fn)
        for name, fn in fns.items()
    }

    results: list[CandidateResult] = []
    for layout in oriented.values():
        results.append(evaluate(layout, args, "single"))

    pair_orientations = [("r0", "r0"), ("r0", "mx"), ("r0", "my"), ("r0", "r180")]
    if args.mode == "smoke":
        scales = [1.00, 0.95]
        for axis in ["x", "y"]:
            for left_name, right_name in pair_orientations:
                left = oriented[left_name]
                right = oriented[right_name]
                _xlo, _ylo, xhi, yhi = left.bbox()
                nominal = xhi if axis == "x" else yhi
                for scale in scales:
                    pitch = int(math.ceil(nominal * scale))
                    name = f"pair_{axis}_{left_name}_{right_name}_p{pitch}"
                    pair = make_pair(left, right, axis, pitch, name)
                    results.append(evaluate(pair, args, f"pair-{axis}"))
        return results

    if args.mode == "refine":
        refine_specs = [
            ("x", "r0", "mx", 354),
            ("x", "r0", "r180", 354),
            ("y", "r0", "r0", 514),
            ("y", "r0", "my", 514),
        ]
        for axis, left_name, right_name, center in refine_specs:
            left = oriented[left_name]
            right = oriented[right_name]
            start = max(1, center - args.refine_window)
            stop = center + args.refine_window
            best: CandidateResult | None = None
            for pitch in pitch_values(start, stop, args.step):
                name = f"refine_{axis}_{left_name}_{right_name}_p{pitch}"
                pair = make_pair(left, right, axis, pitch, name)
                result = evaluate(pair, args, f"refine-{axis}")
                results.append(result)
                if result.clean and (best is None or result.area_um2 < best.area_um2):
                    best = result
            if best:
                print(
                    f"FINE BEST {axis} {left_name}/{right_name}: {best.name} "
                    f"{best.width_um:.3f}um x {best.height_um:.3f}um = {best.area_um2:.3f}um^2"
                )
            else:
                print(f"FINE BEST {axis} {left_name}/{right_name}: no DRC-clean pitch")
        return results

    for axis in ["x", "y"]:
        for left_name, right_name in pair_orientations:
            left = oriented[left_name]
            right = oriented[right_name]
            _xlo, _ylo, xhi, yhi = left.bbox()
            nominal = xhi if axis == "x" else yhi
            start = max(1, int(math.floor(nominal * args.min_pitch_scale)))
            stop = nominal
            best: CandidateResult | None = None
            for pitch in pitch_values(start, stop, args.step):
                name = f"pair_{axis}_{left_name}_{right_name}_p{pitch}"
                pair = make_pair(left, right, axis, pitch, name)
                result = evaluate(pair, args, f"pair-{axis}")
                results.append(result)
                if result.clean and (best is None or result.area_um2 < best.area_um2):
                    best = result
            if best:
                print(
                    f"BEST {axis} {left_name}/{right_name}: {best.name} "
                    f"{best.width_um:.3f}um x {best.height_um:.3f}um = {best.area_um2:.3f}um^2"
                )
            else:
                print(f"BEST {axis} {left_name}/{right_name}: no DRC-clean pitch")

    return results


def write_summary(results: list[CandidateResult], out_dir: Path) -> None:
    csv_path = out_dir / "summary.csv"
    with csv_path.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["name", "kind", "drc_errors", "width_um", "height_um", "area_um2", "log"])
        for result in results:
            writer.writerow(
                [
                    result.name,
                    result.kind,
                    result.drc_errors,
                    f"{result.width_um:.6f}",
                    f"{result.height_um:.6f}",
                    f"{result.area_um2:.6f}",
                    result.log,
                ]
            )

    clean = [r for r in results if r.clean]
    clean.sort(key=lambda r: r.area_um2)
    md_path = out_dir / "summary.md"
    lines = [
        "# Extreme Compaction Search Summary",
        "",
        f"Candidates checked: {len(results)}",
        f"DRC-clean candidates: {len(clean)}",
        "",
        "| Rank | Name | Kind | Size | Area |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for rank, result in enumerate(clean[:20], start=1):
        lines.append(
            f"| {rank} | `{result.name}` | `{result.kind}` | "
            f"`{result.width_um:.3f}um x {result.height_um:.3f}um` | "
            f"`{result.area_um2:.3f}um^2` |"
        )
    md_path.write_text("\n".join(lines) + "\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Source Magic .mag leaf")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output/build directory")
    parser.add_argument("--magic", default="magic")
    parser.add_argument("--magic-rc", required=True, type=Path)
    parser.add_argument("--mode", choices=["smoke", "search", "refine"], default="smoke")
    parser.add_argument("--step", type=int, default=10, help="Pitch search step in Magic units")
    parser.add_argument("--refine-window", type=int, default=20, help="Refine search window in Magic units")
    parser.add_argument("--min-pitch-scale", type=float, default=0.60)
    parser.add_argument("--units-per-um", type=float, default=MAG_UNITS_PER_UM_DEFAULT)
    parser.add_argument(
        "--allow-device-overlap",
        action="store_false",
        dest="reject_device_overlap",
        help=(
            "Allow same-layer device geometry area overlap. Default rejects it "
            "because overlap can silently change transistor/connectivity geometry."
        ),
    )
    parser.set_defaults(reject_device_overlap=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        results = run_search(args)
        write_summary(results, args.out_dir)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
