"""Shared helpers for GF180 12T SRAM LVS verification scripts."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


TILE_CELL = "gf180mcu_3v3_12t_2r2w_sram_4x4_tile"

ROW_PINS = ("W0_WL", "W1_WL", "R0_RWL", "R1_RWL")
COL_PINS = ("W0_BL", "W0_BR", "W1_BL", "W1_BR", "R0_RBL", "R1_RBL")

LEAF_DEVICE_TEMPLATE = [
    ("XP_Q", "q", "qb", "VDD", "NWELL", "pfet_03v3", "w=0.28u l=0.28u"),
    ("XN_Q", "q", "qb", "VSS", "VSUBS", "nfet_03v3", "w=0.45u l=0.28u"),
    ("XP_QB", "qb", "q", "VDD", "NWELL", "pfet_03v3", "w=0.28u l=0.28u"),
    ("XN_QB", "qb", "q", "VSS", "VSUBS", "nfet_03v3", "w=0.45u l=0.28u"),
    ("XW0_Q", "q", "W0_WL", "W0_BL", "VSUBS", "nfet_03v3", "w=0.28u l=0.36u"),
    ("XW0_QB", "qb", "W0_WL", "W0_BR", "VSUBS", "nfet_03v3", "w=0.28u l=0.36u"),
    ("XW1_Q", "q", "W1_WL", "W1_BL", "VSUBS", "nfet_03v3", "w=0.28u l=0.36u"),
    ("XW1_QB", "qb", "W1_WL", "W1_BR", "VSUBS", "nfet_03v3", "w=0.28u l=0.36u"),
    ("XR0_Q", "r0_mid", "q", "VSS", "VSUBS", "nfet_03v3", "w=0.53u l=0.28u"),
    ("XR0_SEL", "r0_mid", "R0_RWL", "R0_RBL", "VSUBS", "nfet_03v3", "w=0.53u l=0.28u"),
    ("XR1_Q", "r1_mid", "q", "VSS", "VSUBS", "nfet_03v3", "w=0.53u l=0.28u"),
    ("XR1_SEL", "r1_mid", "R1_RWL", "R1_RBL", "VSUBS", "nfet_03v3", "w=0.53u l=0.28u"),
]


def pdk_file_from_env(kind: str) -> Path | None:
    env_names = {
        "magic": ("GF180_MAGIC_RC", "MAGIC_RC"),
        "netgen": ("GF180_NETGEN_SETUP", "NETGEN_SETUP"),
    }[kind]
    for name in env_names:
        value = os.environ.get(name)
        if value and Path(value).is_file():
            return Path(value)

    roots: list[Path] = []
    gf180_root = os.environ.get("GF180_PDK_ROOT")
    if gf180_root:
        roots.append(Path(gf180_root))

    pdk_root = os.environ.get("PDK_ROOT")
    pdk_version = os.environ.get("PDK_VERSION")
    if pdk_root and pdk_version:
        roots.append(Path(pdk_root) / "gf180mcu" / "versions" / pdk_version / "gf180mcuD")
        roots.append(Path(pdk_root) / pdk_version / "gf180mcuD")
    if pdk_root:
        roots.append(Path(pdk_root) / "gf180mcuD")

    relative = {
        "magic": "libs.tech/magic/gf180mcuD.magicrc",
        "netgen": "libs.tech/netgen/setup.tcl",
    }[kind]
    for root in roots:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def require_path(path: Path | None, *, description: str, option: str) -> Path:
    if path is not None and path.is_file():
        return path
    raise SystemExit(f"missing {description}; pass {option} or set the matching GF180 env var")


def logical_tile_pins(rows: int, cols: int) -> list[str]:
    pins: list[str] = []
    for col in range(cols):
        for pin in COL_PINS:
            pins.append(f"c{col}_{pin.lower()}")
    for row in range(rows):
        for pin in ROW_PINS:
            pins.append(f"r{row}_{pin.lower()}")
    pins.extend(["VDD", "VSS"])
    return pins


def write_reference_cdl(
    *,
    path: Path,
    tile_cell: str,
    rows: int,
    cols: int,
    leaf_cell: str,
) -> None:
    pins = logical_tile_pins(rows, cols)
    lines = [
        f"* Independent 12T 2R2W {rows}x{cols} tile reference for {tile_cell}",
        "* This is generated from the intended MOS topology, not from layout extraction.",
        "* NFET bodies use the common extracted substrate node VSUBS.",
        "",
        f".subckt {tile_cell} {' '.join(pins)}",
    ]
    for row in range(rows):
        for col in range(cols):
            nets = {
                "W0_BL": f"c{col}_w0_bl",
                "W0_BR": f"c{col}_w0_br",
                "W1_BL": f"c{col}_w1_bl",
                "W1_BR": f"c{col}_w1_br",
                "R0_RBL": f"c{col}_r0_rbl",
                "R1_RBL": f"c{col}_r1_rbl",
                "W0_WL": f"r{row}_w0_wl",
                "W1_WL": f"r{row}_w1_wl",
                "R0_RWL": f"r{row}_r0_rwl",
                "R1_RWL": f"r{row}_r1_rwl",
                "VDD": "VDD",
                "VSS": "VSS",
            }
            prefix = f"r{row}c{col}"

            def resolve(node: str) -> str:
                if node in nets:
                    return nets[node]
                if node == "VSUBS":
                    return "VSUBS"
                return f"{leaf_cell}{prefix}/{node}"

            for name, drain, gate, source, body, model, params in LEAF_DEVICE_TEMPLATE:
                lines.append(
                    " ".join(
                        [
                            f"X{prefix}_{name}",
                            resolve(drain),
                            resolve(gate),
                            resolve(source),
                            resolve(body),
                            model,
                            params,
                        ]
                    )
                )
    lines.append(f".ends {tile_cell}")
    path.write_text("\n".join(lines) + "\n")


def parse_lvs(log: Path, stdout_log: Path) -> tuple[str, int | None, int | None, int | None, int | None]:
    text = ""
    if log.exists():
        text += log.read_text(errors="ignore")
    if stdout_log.exists():
        text += "\n" + stdout_log.read_text(errors="ignore")

    if "Netlists do not match" in text or "Mismatch" in text:
        status = "mismatch"
    elif "Result: Circuits match uniquely" in text or "Netlists match uniquely" in text:
        status = "match_unique"
    elif "Circuits match correctly" in text or "Subcircuits match" in text:
        status = "match"
    else:
        status = "unknown"

    devices = re.findall(
        r"Circuit 1 contains\s+(\d+)\s+devices,\s+Circuit 2 contains\s+(\d+)\s+devices",
        text,
    )
    nets = re.findall(
        r"Circuit 1 contains\s+(\d+)\s+nets,\s+Circuit 2 contains\s+(\d+)\s+nets",
        text,
    )
    return (
        status,
        int(devices[-1][0]) if devices else None,
        int(devices[-1][1]) if devices else None,
        int(nets[-1][0]) if nets else None,
        int(nets[-1][1]) if nets else None,
    )


def run_netgen_lvs(
    *,
    tile_cell: str,
    layout_spice: Path,
    reference_cdl: Path,
    netgen_lvs: str,
    netgen_setup: Path,
    lvs_log: Path,
    stdout_log: Path,
) -> tuple[str, int | None, int | None, int | None, int | None]:
    proc = subprocess.run(
        [
            netgen_lvs,
            "-batch",
            "lvs",
            f"{layout_spice} {tile_cell}",
            f"{reference_cdl} {tile_cell}",
            str(netgen_setup),
            str(lvs_log),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    stdout_log.write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"Netgen LVS failed for {layout_spice}; see {stdout_log}")
    return parse_lvs(lvs_log, stdout_log)
