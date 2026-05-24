#!/usr/bin/env python3
"""Run the local open-source signoff gate for GF180MCU 12T SRAM macros.

This script intentionally separates tool-backed PASS/FAIL from items that are
only audit proxies in an open-source flow.  It runs/collects:

* Magic DRC evidence from the final physical package;
* Magic PEX extraction with cthresh/rthresh set to zero;
* staged Netgen LVS evidence for transistor-level control leaves;
* final macro abstract pin LVS against the extracted top subckt;
* GF180MCU KLayout antenna and density decks;
* ngspice disturb/conflict and VDD sweep evidence as the current SNM proxy;
* a conservative local EM/IR power-strap audit.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MEASURE_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*([-+0-9.eE]+)")
DRC_RE = re.compile(r"(?:Total DRC errors found|DRC error count):\s*(\d+)")


@dataclass(frozen=True)
class Check:
    area: str
    check: str
    status: str
    evidence: str
    detail: str


def add(checks: list[Check], area: str, check: str, status: str, evidence: Path | str, detail: str) -> None:
    checks.append(Check(area, check, status, str(evidence), detail))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_ok(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def parse_magic_drc(path: Path) -> int | None:
    if not path.exists():
        return None
    matches = DRC_RE.findall(path.read_text(encoding="utf-8", errors="replace"))
    return int(matches[-1]) if matches else None


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
                "extract style ngspice()",
                "extract unique",
                "extract path $::env(EXT_DIR)",
                "extract no all",
                "extract all",
                "ext2sim labels on",
                "ext2sim -p $::env(EXT_DIR) $topcell",
                "extresist threshold 0",
                "extresist tolerance 10",
                "extresist extout on",
                "extresist silent on",
                "if {[info exists ::env(PEX_NETS)] && $::env(PEX_NETS) ne \"\"} {",
                "    eval extresist include $::env(PEX_NETS)",
                "}",
                "extresist all",
                "ext2spice lvs",
                "ext2spice blackbox on",
                "ext2spice -p $::env(EXT_DIR) -o $::env(PEX_LVS_SPICE)",
                "ext2spice cthresh 0",
                "ext2spice rthresh 0",
                "ext2spice extresist on",
                "ext2spice resistor tee on",
                "ext2spice blackbox on",
                "ext2spice -p $::env(EXT_DIR) -o $::env(PEX_RC_SPICE)",
                "quit -noprompt",
            ]
        )
        + "\n"
    )


def tcl_list(items: list[str]) -> str:
    escaped = []
    for item in items:
        escaped.append("{" + item.replace("\\", "\\\\").replace("}", "\\}") + "}")
    return " ".join(escaped)


def run_magic_pex(*, macro: str, magic_dir: Path, out_dir: Path, magic: str, magic_rc: Path, pex_nets: list[str]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ext_dir = out_dir / "extfiles"
    ext_dir.mkdir(parents=True, exist_ok=True)
    tcl = out_dir / "run_extract_pex.tcl"
    log = out_dir / f"{macro}.magic_pex.log"
    lvs_spice = out_dir / f"{macro}.current_pdk.spice"
    rc_spice = out_dir / f"{macro}.current_pdk_rc.spice"
    write_extract_tcl(tcl)
    env = os.environ.copy()
    resolved_magic_rc = magic_rc.resolve()
    if len(resolved_magic_rc.parents) >= 4:
        # gf180mcuD.magicrc expects PDK_ROOT to point at the concrete
        # gf180mcu/versions/<hash> directory, not at the volare root.
        env["PDK_ROOT"] = str(resolved_magic_rc.parents[3])
    env.update(
        {
            "MAGIC_TOPCELL": macro,
            "EXT_DIR": str(ext_dir.resolve()),
            "PEX_LVS_SPICE": str(lvs_spice.resolve()),
            "PEX_RC_SPICE": str(rc_spice.resolve()),
            "PEX_NETS": tcl_list([net for net in ("VDD", "VSS") if net in pex_nets] or pex_nets),
        }
    )
    proc = subprocess.run(
        [magic, "-dnull", "-noconsole", "-rcfile", str(magic_rc)],
        cwd=magic_dir,
        text=True,
        input=tcl.read_text(encoding="utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )
    log.write_text(proc.stdout, encoding="utf-8")
    return {
        "returncode": proc.returncode,
        "log": str(log),
        "lvs_spice": str(lvs_spice),
        "rc_spice": str(rc_spice),
        "lvs_spice_bytes": lvs_spice.stat().st_size if lvs_spice.exists() else 0,
        "rc_spice_bytes": rc_spice.stat().st_size if rc_spice.exists() else 0,
        "spice_stats": spice_stats(rc_spice),
    }


def spice_stats(path: Path) -> dict[str, int]:
    stats = {"subckt": 0, "resistors": 0, "capacitors": 0, "mos": 0, "instances": 0}
    if not path.exists():
        return stats
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith("+"):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            stats["subckt"] += 1
        elif line[0] in {"R", "r"}:
            stats["resistors"] += 1
        elif line[0] in {"C", "c"}:
            stats["capacitors"] += 1
        elif line[0] in {"M", "m"}:
            stats["mos"] += 1
        elif line[0] in {"X", "x"}:
            stats["instances"] += 1
    return stats


def subckt_pins(path: Path, cell: str) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for idx, line in enumerate(lines):
        if not line.startswith(f".subckt {cell} "):
            continue
        parts = [line]
        cursor = idx + 1
        while cursor < len(lines) and lines[cursor].startswith("+"):
            parts.append(lines[cursor][1:])
            cursor += 1
        return " ".join(parts).split()[2:]
    return []


def parse_lyrdb_items(path: Path) -> tuple[int | None, list[str]]:
    if not path.exists():
        return None, []
    root = ET.parse(path).getroot()
    items = None
    for child in root:
        if child.tag == "items":
            items = child
            break
    if items is None:
        return None, []
    categories: list[str] = []
    for item in list(items):
        for sub in list(item):
            if sub.tag == "category":
                categories.append(sub.text or "")
                break
    return len(list(items)), sorted(set(categories))[:12]


def run_klayout_deck(
    *,
    klayout: str,
    deck: Path,
    gds: Path,
    topcell: str,
    report: Path,
    log: Path,
    deck_kind: str,
) -> dict[str, Any]:
    report.parent.mkdir(parents=True, exist_ok=True)
    if report.exists():
        report.unlink()
    if log.exists():
        log.unlink()
    cmd = [
        klayout,
        "-b",
        "-r",
        str(deck),
        "-rd",
        f"input={gds.resolve()}",
        "-rd",
        f"topcell={topcell}",
        "-rd",
        f"report={report.resolve()}",
        "-rd",
        "run_mode=flat",
        "-rd",
        "metal_top=9K",
        "-rd",
        "metal_level=5LM",
        "-rd",
        "thr=1",
    ]
    if deck_kind == "antenna":
        cmd.extend(["-rd", "mim_option=B"])
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log.write_text(proc.stdout, encoding="utf-8")
    items, categories = parse_lyrdb_items(report)
    return {
        "returncode": proc.returncode,
        "report": str(report),
        "log": str(log),
        "violations": items,
        "categories": categories,
    }


def primitive_lvs_summary(path: Path) -> tuple[int, int, list[str]]:
    fails: list[str] = []
    total = 0
    for item in load_json(path):
        total += 1
        lvs = str(item.get("lvs_result", ""))
        pins = int(item.get("disconnected_pins", -1))
        if lvs not in {"match", "match_unique"} or pins != 0:
            fails.append(f"{item.get('primitive')}: lvs={lvs} disconnected={pins}")
    return total, len(fails), fails


def parse_measures(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = MEASURE_RE.match(line)
        if not match:
            continue
        key, raw = match.groups()
        try:
            values[key.lower()] = float(raw)
        except ValueError:
            pass
    return values


def check_vdd_sweep(root: Path) -> tuple[bool, str]:
    corners = ("typical", "ff", "ss")
    vdds = ("1p62", "1p80", "2p50", "3p00", "3p30", "3p60")
    missing: list[str] = []
    bad: list[str] = []
    for corner in corners:
        for vtag in vdds:
            path = root / "build" / f"tb_12t_2w2r_{corner}_{vtag}v.log"
            vals = parse_measures(path)
            if not vals:
                missing.append(path.name)
                continue
            if "q_after_write1" not in vals or "qb_after_write0" not in vals:
                bad.append(f"{path.name}: missing write measures")
                continue
            vdd = float(vtag.replace("p", "."))
            if vals["q_after_write1"] < 0.75 * vdd or vals["qb_after_write0"] < 0.75 * vdd:
                bad.append(f"{path.name}: weak rail write q1={vals['q_after_write1']:.3g} qb0={vals['qb_after_write0']:.3g}")
    ok = not missing and not bad
    return ok, f"missing={missing[:4]} bad={bad[:4]} checked={len(corners) * len(vdds)}"


def check_disturb(root: Path) -> tuple[bool, str]:
    missing: list[str] = []
    bad: list[str] = []
    for corner in ("typical", "ff", "ss"):
        path = root / "build" / f"tb_12t_disturb_conflict_{corner}.log"
        vals = parse_measures(path)
        if not vals:
            missing.append(path.name)
            continue
        for high_key in ("q_after_read_disturb", "q_after_disabled_write", "qb_after_dual_same0", "q_after_dual_same1", "qb_after_conflict"):
            if vals.get(high_key, 0.0) < 2.4:
                bad.append(f"{path.name}:{high_key}={vals.get(high_key)}")
        for low_key in ("qb_after_read_disturb", "qb_after_disabled_write", "q_after_dual_same0", "qb_after_dual_same1", "q_after_conflict"):
            if vals.get(low_key, 9.9) > 0.15:
                bad.append(f"{path.name}:{low_key}={vals.get(low_key)}")
    ok = not missing and not bad
    return ok, f"missing={missing} bad={bad[:6]} checked=3 corners"


def emir_proxy(item: dict[str, Any]) -> tuple[str, str]:
    width = float(item["width_um"])
    bottom = float(item["control_bottom_um"])
    top = float(item["control_top_um"])
    cols = int(item["tile_grid_cols"])
    rows = int(item["tile_grid_rows"])
    # M5 power rails are full macro width; M4 ties repeat per tile column.
    vss_area = width * bottom
    vdd_area = width * top
    if bottom >= 20.0 and top >= 20.0 and cols >= 16 and rows >= 16:
        return "WARN", f"proxy pass: M5 VSS={bottom:.1f}um, VDD={top:.1f}um over {width:.1f}um; {cols} column ties. No solver-grade current map."
    return "FAIL", f"weak proxy rails: M5 VSS={bottom:.1f}um, VDD={top:.1f}um, cols={cols}, rail_area={vdd_area + vss_area:.1f}um2"


def write_outputs(out_dir: Path, checks: list[Check], tool_runs: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    overall = "FAIL" if counts.get("FAIL", 0) else ("WARN" if counts.get("WARN", 0) or counts.get("OPEN", 0) else "PASS")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "status_counts": counts,
        "tool_runs": tool_runs,
        "checks": [asdict(check) for check in checks],
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# GF180MCU 12T SRAM Local Open-Source Signoff",
        "",
        f"- Overall status: `{overall}`",
        f"- Status counts: `{counts}`",
        "",
        "This is the strongest local open-source gate currently available in this tree.",
        "It is not a foundry signoff replacement.",
        "",
        "| Area | Check | Status | Detail | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        detail = check.detail.replace("|", "/")
        lines.append(f"| `{check.area}` | `{check.check}` | `{check.status}` | {detail} | `{check.evidence}` |")
    lines.append("")
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    csv_lines = ["area,check,status,evidence,detail"]
    for check in checks:
        csv_lines.append(
            ",".join(
                json.dumps(field, ensure_ascii=False)
                for field in (check.area, check.check, check.status, check.evidence, check.detail)
            )
        )
    (out_dir / "summary.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--final-manifest", type=Path, required=True)
    parser.add_argument("--open-signoff-manifest", type=Path, required=True)
    parser.add_argument("--primitive-manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--magic", default="magic")
    parser.add_argument("--magic-rc", type=Path, required=True)
    parser.add_argument("--klayout", default="klayout")
    parser.add_argument("--gf180-klayout-drc-dir", type=Path, required=True)
    parser.add_argument("--macro-filter", action="append", default=[], help="Limit the run to matching macro name(s); useful for pin-LVS/PEX iteration.")
    parser.add_argument("--skip-klayout", action="store_true", help="Skip KLayout density/antenna decks; useful for focused pin-LVS/PEX iteration.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    out_dir = args.out_dir
    final_macros = load_json(args.final_manifest)
    if args.macro_filter:
        allowed = set(args.macro_filter)
        final_macros = [item for item in final_macros if str(item["macro"]) in allowed]
        if not final_macros:
            raise SystemExit(f"no final macros matched --macro-filter={sorted(allowed)}")
    open_manifest = load_json(args.open_signoff_manifest)
    checks: list[Check] = []
    tool_runs: dict[str, Any] = {
        "magic_pex": {},
        "klayout_density": {},
        "klayout_antenna": {},
    }

    add(checks, "Open signoff", "Prior staged open signoff", "PASS" if open_manifest.get("overall_status") in {"PASS", "WARN"} else "FAIL", args.open_signoff_manifest, f"counts={open_manifest.get('status_counts')}")

    total_prims, primitive_fails, primitive_details = primitive_lvs_summary(args.primitive_manifest)
    add(
        checks,
        "LVS",
        "RC7 transistor control primitive Netgen LVS",
        "PASS" if primitive_fails == 0 else "FAIL",
        args.primitive_manifest,
        f"checked={total_prims}, fails={primitive_fails}, details={primitive_details[:3]}",
    )

    density_deck = args.gf180_klayout_drc_dir / "rule_decks" / "density.drc"
    antenna_deck = args.gf180_klayout_drc_dir / "rule_decks" / "antenna.drc"
    for item in final_macros:
        macro = str(item["macro"])
        macro_out = out_dir / macro
        gds = root / str(item["gds"])
        magic_file = root / str(item["magic"])
        spice = root / str(item["spice"])
        drc_log = root / str(item["drc_log"])
        drc_raw = item.get("drc_errors")
        parsed_drc = parse_magic_drc(drc_log)
        if drc_raw is None:
            add(checks, macro, "Magic final macro DRC", "OPEN", drc_log, "top-level Magic DRC skipped in final physical rebuild; staged leaf/tile Magic DRC and KLayout decks remain checked")
        else:
            drc = int(drc_raw)
            add(checks, macro, "Magic final macro DRC", "PASS" if drc == 0 and parsed_drc == 0 else "FAIL", drc_log, f"manifest_drc={drc}, parsed_drc={parsed_drc}")

        ref_pins = subckt_pins(spice, macro)
        pex = run_magic_pex(
            macro=macro,
            magic_dir=magic_file.parent,
            out_dir=macro_out / "pex",
            magic=args.magic,
            magic_rc=args.magic_rc,
            pex_nets=ref_pins,
        )
        tool_runs["magic_pex"][macro] = pex
        pex_ok = pex["returncode"] == 0 and pex["rc_spice_bytes"] > 0 and pex["spice_stats"]["subckt"] > 0
        pex_has_rc = pex["spice_stats"]["resistors"] > 0 or pex["spice_stats"]["capacitors"] > 0
        pex_status = "PASS" if pex_ok and pex_has_rc else "FAIL"
        add(
            checks,
            macro,
            "Magic PEX extraction",
            pex_status,
            pex["log"],
            f"rc_spice_bytes={pex['rc_spice_bytes']}, stats={pex['spice_stats']}, has_rc={pex_has_rc}",
        )

        ext_pins = subckt_pins(Path(pex["lvs_spice"]), macro)
        pin_ok = bool(ref_pins) and set(ref_pins) == set(ext_pins)
        add(checks, macro, "Final abstract pin LVS", "PASS" if pin_ok else "FAIL", pex["lvs_spice"], f"ref_pins={len(ref_pins)}, extracted_pins={len(ext_pins)}, missing={sorted(set(ref_pins) - set(ext_pins))[:6]}, extra={sorted(set(ext_pins) - set(ref_pins))[:6]}")
        add(checks, macro, "Full device-expanded macro LVS", "OPEN", args.open_signoff_manifest, "final top GDS is a hard-macro abstract; full row-select/predecode device expansion remains separate from this top-level GDS")

        if args.skip_klayout:
            add(checks, macro, "KLayout GF180 density deck", "OPEN", gds, "skipped by --skip-klayout for focused pin-LVS/PEX iteration")
            add(checks, macro, "KLayout GF180 antenna deck", "OPEN", gds, "skipped by --skip-klayout for focused pin-LVS/PEX iteration")
        else:
            density = run_klayout_deck(
                klayout=args.klayout,
                deck=density_deck,
                gds=gds,
                topcell=macro,
                report=macro_out / "density" / f"{macro}.density.lyrdb",
                log=macro_out / "density" / f"{macro}.density.log",
                deck_kind="density",
            )
            tool_runs["klayout_density"][macro] = density
            add(checks, macro, "KLayout GF180 density deck", "PASS" if density["returncode"] == 0 and density["violations"] == 0 else "FAIL", density["report"], f"returncode={density['returncode']}, violations={density['violations']}, sample_categories={density['categories']}")

            antenna = run_klayout_deck(
                klayout=args.klayout,
                deck=antenna_deck,
                gds=gds,
                topcell=macro,
                report=macro_out / "antenna" / f"{macro}.antenna.lyrdb",
                log=macro_out / "antenna" / f"{macro}.antenna.log",
                deck_kind="antenna",
            )
            tool_runs["klayout_antenna"][macro] = antenna
            add(checks, macro, "KLayout GF180 antenna deck", "PASS" if antenna["returncode"] == 0 and antenna["violations"] == 0 else "FAIL", antenna["report"], f"returncode={antenna['returncode']}, violations={antenna['violations']}, sample_categories={antenna['categories']}")

        status, detail = emir_proxy(item)
        add(checks, macro, "Local EM/IR power strap audit", status, root / str(item["pins_json"]), detail)

    vdd_ok, vdd_detail = check_vdd_sweep(root)
    add(checks, "SNM proxy", "12T VDD sweep ngspice", "PASS" if vdd_ok else "FAIL", root / "build", vdd_detail)
    disturb_ok, disturb_detail = check_disturb(root)
    add(checks, "SNM proxy", "12T disturb/conflict ngspice", "PASS" if disturb_ok else "FAIL", root / "build", disturb_detail)
    add(checks, "SNM", "Butterfly SNM / extracted final RC SNM", "OPEN", root / "build", "current local evidence is VDD sweep and disturb/conflict; butterfly SNM on final extracted RC is not implemented yet")

    write_outputs(out_dir, checks, tool_runs)
    counts: dict[str, int] = {}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    print(f"GF180MCU 12T SRAM local open-source signoff: {counts}")
    print(out_dir / "README.md")
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
