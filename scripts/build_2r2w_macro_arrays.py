#!/usr/bin/env python3
"""Build first 12T 2W2R SRAM array macro candidates.

These macros are physical array candidates assembled from the
`detronyx_12t_2w2r_rc1` leaf.  They intentionally do not include row
decoders, column muxing, precharge, sense amps, write drivers, clocks, or
control logic yet.  The generated LEF/Verilog/SPICE abstracts therefore mark
the hard macro as an array-only blackbox.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from build_physical_cells import bbox, dims_um
from extreme_compaction_search import read_magic


UNITS_PER_UM = 200.0
DEFAULT_SPECS = (
    ("detronyx_12t_2w2r_512x8_array_rc1", 512, 8, 4),
    ("detronyx_12t_2w2r_512x32_array_rc1", 512, 32, 4),
)


@dataclass(frozen=True)
class MacroResult:
    macro: str
    source_cell: str
    rows: int
    data_width: int
    row_banks: int
    rows_per_bank: int
    bitcells: int
    nfets_pfets_total: int
    wordlines_total: int
    vertical_bitlines_total: int
    cell_width_um: float
    cell_height_um: float
    cell_area_um2: float
    width_um: float
    height_um: float
    area_um2: float
    area_mm2: float
    aspect_ratio: float
    magic: str
    gds: str
    lef: str
    verilog: str
    spice: str
    pins_json: str
    decode_contract: str
    behavioral_model: str
    decode_plan_md: str
    drc_errors: int | None
    drc_log: str


def write_top_magic(
    path: Path,
    *,
    macro: str,
    source_cell: str,
    tech: str,
    magscale: str,
    cell_bbox: tuple[int, int, int, int],
    cell_width: int,
    cell_height: int,
    rows: int,
    data_width: int,
    row_banks: int,
) -> None:
    rows_per_bank = rows // row_banks
    lines = [
        "magic",
        f"tech {tech}",
        f"magscale {magscale}",
        "timestamp 1780006000",
    ]

    xlo, ylo, xhi, yhi = cell_bbox
    for bank in range(row_banks):
        bank_x = bank * data_width * cell_width
        for row in range(rows_per_bank):
            y = row * cell_height
            for col in range(data_width):
                x = bank_x + col * cell_width
                inst = f"u_b{bank:02d}_r{row:03d}_c{col:02d}"
                lines.extend(
                    [
                        f"use {source_cell} {inst}",
                        "timestamp 1780003000",
                        f"transform 1 0 {x} 0 1 {y}",
                        f"box {xlo} {ylo} {xhi} {yhi}",
                    ]
                )

    width = row_banks * data_width * cell_width
    height = rows_per_bank * cell_height
    lines.extend(
        [
            "<< properties >>",
            f"string FIXED_BBOX 0 0 {width} {height}",
            f"string DETRONYX_PHYSICAL_MACRO {macro}",
            f"string DETRONYX_SOURCE_CELL {source_cell}",
            "string DETRONYX_CELL_TOPOLOGY 12T_2W2R_RC1",
            "string DETRONYX_MACRO_STATUS array_only_no_periphery",
            f"string DETRONYX_ROWS {rows}",
            f"string DETRONYX_DATA_WIDTH {data_width}",
            f"string DETRONYX_ROW_BANKS {row_banks}",
            f"string DETRONYX_ROWS_PER_BANK {rows_per_bank}",
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


def parse_drc_count(text: str) -> int | None:
    patterns = (
        r"Total DRC errors found:\s*([0-9]+)",
        r"DRC error count:\s*([0-9]+)",
        r"([0-9]+)\s+total DRC errors",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def run_magic(
    *,
    macro: str,
    magic_dir: Path,
    script: Path,
    log_path: Path,
    magic: str,
    magic_rc: Path,
) -> int | None:
    env = dict(**__import__("os").environ)
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
  OBS
    LAYER Metal1 ;
      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;
    LAYER Metal2 ;
      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;
    LAYER Metal3 ;
      RECT 0.000000 0.000000 {width_um:.6f} {height_um:.6f} ;
  END
END {macro}
END LIBRARY
"""
    )


def write_verilog(path: Path, macro: str, rows: int, data_width: int) -> None:
    addr_width = (rows - 1).bit_length()
    path.write_text(
        f"""(* black_box *)
module {macro} (
    input  logic                  clk,
    input  logic                  w0_en,
    input  logic                  w1_en,
    input  logic                  r0_en,
    input  logic                  r1_en,
    input  logic [{addr_width - 1}:0]           w0_addr,
    input  logic [{addr_width - 1}:0]           w1_addr,
    input  logic [{addr_width - 1}:0]           r0_addr,
    input  logic [{addr_width - 1}:0]           r1_addr,
    input  logic [{data_width - 1}:0]          w0_data,
    input  logic [{data_width - 1}:0]          w1_data,
    output logic [{data_width - 1}:0]          r0_data,
    output logic [{data_width - 1}:0]          r1_data,
    inout  wire                   VDD,
    inout  wire                   VSS
);
endmodule
"""
    )


def write_decode_contract(path: Path, macro: str, rows: int, data_width: int) -> None:
    addr_width = (rows - 1).bit_length()
    bank_width = 2
    row_width = addr_width - bank_width
    rows_per_bank = 1 << row_width
    path.write_text(
        f"""// Synthesizable decode/control contract for {macro}.
// External MCU-facing address remains flat addr[{addr_width - 1}:0].
// Internal physical split is bank=addr[{addr_width - 1}:{row_width}], row=addr[{row_width - 1}:0].
module {macro}_periphery_decode_contract #(
    parameter int ROWS = {rows},
    parameter int DATA_WIDTH = {data_width},
    parameter int BANKS = 4,
    parameter int ADDR_WIDTH = {addr_width},
    parameter int BANK_ADDR_WIDTH = {bank_width},
    parameter int ROW_ADDR_WIDTH = {row_width},
    parameter int ROWS_PER_BANK = {rows_per_bank}
) (
    input  logic                         w0_en,
    input  logic                         w1_en,
    input  logic                         r0_en,
    input  logic                         r1_en,
    input  logic [ADDR_WIDTH-1:0]        w0_addr,
    input  logic [ADDR_WIDTH-1:0]        w1_addr,
    input  logic [ADDR_WIDTH-1:0]        r0_addr,
    input  logic [ADDR_WIDTH-1:0]        r1_addr,
    input  logic [DATA_WIDTH-1:0]        w0_data,
    input  logic [DATA_WIDTH-1:0]        w1_data,
    input  logic [DATA_WIDTH-1:0]        r0_sense_data,
    input  logic [DATA_WIDTH-1:0]        r1_sense_data,
    output logic                         w0_fire,
    output logic                         w1_fire,
    output logic                         write_conflict,
    output logic [BANK_ADDR_WIDTH-1:0]   w0_bank,
    output logic [BANK_ADDR_WIDTH-1:0]   w1_bank,
    output logic [BANK_ADDR_WIDTH-1:0]   r0_bank,
    output logic [BANK_ADDR_WIDTH-1:0]   r1_bank,
    output logic [ROW_ADDR_WIDTH-1:0]    w0_row,
    output logic [ROW_ADDR_WIDTH-1:0]    w1_row,
    output logic [ROW_ADDR_WIDTH-1:0]    r0_row,
    output logic [ROW_ADDR_WIDTH-1:0]    r1_row,
    output logic [BANKS-1:0]             w0_bank_oh,
    output logic [BANKS-1:0]             w1_bank_oh,
    output logic [BANKS-1:0]             r0_bank_oh,
    output logic [BANKS-1:0]             r1_bank_oh,
    output logic [ROWS_PER_BANK-1:0]     w0_row_oh,
    output logic [ROWS_PER_BANK-1:0]     w1_row_oh,
    output logic [ROWS_PER_BANK-1:0]     r0_row_oh,
    output logic [ROWS_PER_BANK-1:0]     r1_row_oh,
    output logic [ROWS-1:0]              w0_wordline_oh,
    output logic [ROWS-1:0]              w1_wordline_oh,
    output logic [ROWS-1:0]              r0_wordline_oh,
    output logic [ROWS-1:0]              r1_wordline_oh,
    output logic                         r0_bypass_hit,
    output logic                         r1_bypass_hit,
    output logic [DATA_WIDTH-1:0]        r0_data_muxed,
    output logic [DATA_WIDTH-1:0]        r1_data_muxed
);
    function automatic logic [BANKS-1:0] decode_bank(
        input logic en,
        input logic [BANK_ADDR_WIDTH-1:0] bank
    );
        decode_bank = '0;
        if (en) decode_bank[bank] = 1'b1;
    endfunction

    function automatic logic [ROWS_PER_BANK-1:0] decode_row(
        input logic en,
        input logic [ROW_ADDR_WIDTH-1:0] row
    );
        decode_row = '0;
        if (en) decode_row[row] = 1'b1;
    endfunction

    function automatic logic [ROWS-1:0] decode_wordline(
        input logic en,
        input logic [ADDR_WIDTH-1:0] addr
    );
        decode_wordline = '0;
        if (en) decode_wordline[addr] = 1'b1;
    endfunction

    assign w0_bank = w0_addr[ADDR_WIDTH-1:ROW_ADDR_WIDTH];
    assign w1_bank = w1_addr[ADDR_WIDTH-1:ROW_ADDR_WIDTH];
    assign r0_bank = r0_addr[ADDR_WIDTH-1:ROW_ADDR_WIDTH];
    assign r1_bank = r1_addr[ADDR_WIDTH-1:ROW_ADDR_WIDTH];
    assign w0_row = w0_addr[ROW_ADDR_WIDTH-1:0];
    assign w1_row = w1_addr[ROW_ADDR_WIDTH-1:0];
    assign r0_row = r0_addr[ROW_ADDR_WIDTH-1:0];
    assign r1_row = r1_addr[ROW_ADDR_WIDTH-1:0];

    assign write_conflict = w0_en && w1_en && (w0_addr == w1_addr);
    assign w0_fire = w0_en;
    assign w1_fire = w1_en && !write_conflict;

    assign w0_bank_oh = decode_bank(w0_fire, w0_bank);
    assign w1_bank_oh = decode_bank(w1_fire, w1_bank);
    assign r0_bank_oh = decode_bank(r0_en, r0_bank);
    assign r1_bank_oh = decode_bank(r1_en, r1_bank);
    assign w0_row_oh = decode_row(w0_fire, w0_row);
    assign w1_row_oh = decode_row(w1_fire, w1_row);
    assign r0_row_oh = decode_row(r0_en, r0_row);
    assign r1_row_oh = decode_row(r1_en, r1_row);
    assign w0_wordline_oh = decode_wordline(w0_fire, w0_addr);
    assign w1_wordline_oh = decode_wordline(w1_fire, w1_addr);
    assign r0_wordline_oh = decode_wordline(r0_en, r0_addr);
    assign r1_wordline_oh = decode_wordline(r1_en, r1_addr);

    always_comb begin
        r0_bypass_hit = 1'b0;
        r0_data_muxed = r0_sense_data;
        if (r0_en && w0_fire && (r0_addr == w0_addr)) begin
            r0_bypass_hit = 1'b1;
            r0_data_muxed = w0_data;
        end
        if (r0_en && w1_fire && (r0_addr == w1_addr)) begin
            r0_bypass_hit = 1'b1;
            r0_data_muxed = w1_data;
        end
    end

    always_comb begin
        r1_bypass_hit = 1'b0;
        r1_data_muxed = r1_sense_data;
        if (r1_en && w0_fire && (r1_addr == w0_addr)) begin
            r1_bypass_hit = 1'b1;
            r1_data_muxed = w0_data;
        end
        if (r1_en && w1_fire && (r1_addr == w1_addr)) begin
            r1_bypass_hit = 1'b1;
            r1_data_muxed = w1_data;
        end
    end
endmodule
"""
    )


def write_behavioral_model(path: Path, macro: str, rows: int, data_width: int) -> None:
    addr_width = (rows - 1).bit_length()
    path.write_text(
        f"""// Simulation-only SRAM model matching the intended MCU-facing 2W2R contract.
module {macro}_behavioral_model #(
    parameter int ROWS = {rows},
    parameter int DATA_WIDTH = {data_width},
    parameter int ADDR_WIDTH = {addr_width}
) (
    input  logic                  clk,
    input  logic                  w0_en,
    input  logic                  w1_en,
    input  logic                  r0_en,
    input  logic                  r1_en,
    input  logic [ADDR_WIDTH-1:0] w0_addr,
    input  logic [ADDR_WIDTH-1:0] w1_addr,
    input  logic [ADDR_WIDTH-1:0] r0_addr,
    input  logic [ADDR_WIDTH-1:0] r1_addr,
    input  logic [DATA_WIDTH-1:0] w0_data,
    input  logic [DATA_WIDTH-1:0] w1_data,
    output logic [DATA_WIDTH-1:0] r0_data,
    output logic [DATA_WIDTH-1:0] r1_data,
    output logic                  write_conflict
);
    logic [DATA_WIDTH-1:0] mem [0:ROWS-1];
    logic w0_fire;
    logic w1_fire;

    assign write_conflict = w0_en && w1_en && (w0_addr == w1_addr);
    assign w0_fire = w0_en;
    assign w1_fire = w1_en && !write_conflict;

    always_ff @(posedge clk) begin
        if (w0_fire) mem[w0_addr] <= w0_data;
        if (w1_fire) mem[w1_addr] <= w1_data;
    end

    always_comb begin
        r0_data = r0_en ? mem[r0_addr] : '0;
        if (r0_en && w0_fire && (r0_addr == w0_addr)) r0_data = w0_data;
        if (r0_en && w1_fire && (r0_addr == w1_addr)) r0_data = w1_data;
    end

    always_comb begin
        r1_data = r1_en ? mem[r1_addr] : '0;
        if (r1_en && w0_fire && (r1_addr == w0_addr)) r1_data = w0_data;
        if (r1_en && w1_fire && (r1_addr == w1_addr)) r1_data = w1_data;
    end
endmodule
"""
    )


def write_spice(path: Path, macro: str, rows: int, data_width: int) -> None:
    addr_width = (rows - 1).bit_length()
    pins = ["clk", "w0_en", "w1_en", "r0_en", "r1_en"]
    for prefix in ("w0_addr", "w1_addr", "r0_addr", "r1_addr"):
        pins.extend(f"{prefix}[{idx}]" for idx in range(addr_width))
    for prefix in ("w0_data", "w1_data", "r0_data", "r1_data"):
        pins.extend(f"{prefix}[{idx}]" for idx in range(data_width))
    pins.extend(["VDD", "VSS"])
    path.write_text(
        "* Array-only 12T 2W2R SRAM macro blackbox. Periphery is not included yet.\n"
        f".subckt {macro} {' '.join(pins)}\n"
        f".ends {macro}\n"
    )


def write_pins_json(path: Path, macro: str, rows: int, data_width: int, row_banks: int) -> None:
    addr_width = (rows - 1).bit_length()
    row_addr_width = addr_width - 2
    path.write_text(
        json.dumps(
            {
                "macro": macro,
                "status": "array_only_no_periphery",
                "logical_contract_stub": {
                    "ports": "2W2R",
                    "rows": rows,
                    "data_width": data_width,
                    "address_width": addr_width,
                    "note": "Verilog/SPICE stubs expose the intended SRAM contract; physical pins still need decoder/periphery integration.",
                },
                "recommended_addressing": {
                    "external_mcu_address": f"flat addr[{addr_width - 1}:0]",
                    "internal_bank_bits": f"addr[{addr_width - 1}:{row_addr_width}]",
                    "internal_row_bits": f"addr[{row_addr_width - 1}:0]",
                    "bank_count": row_banks,
                    "rows_per_bank": rows // row_banks,
                    "reason": "MCU/software keeps a linear word address; physical macro uses a 4x128 folded row organization.",
                },
                "conflict_policy": {
                    "same_cycle_two_writes_same_address": "w0 wins, w1 is gated off, write_conflict asserted",
                    "read_during_write_same_address": "digital periphery should bypass accepted write data to read output",
                    "two_reads_same_address": "allowed",
                    "two_writes_different_addresses": "allowed by 2W cell topology",
                },
                "raw_array_internal_lines": {
                    "row_banks": row_banks,
                    "rows_per_bank": rows // row_banks,
                    "write_wordlines": 2 * rows,
                    "read_wordlines": 2 * rows,
                    "write_bitlines": 4 * data_width,
                    "read_bitlines": 2 * data_width,
                    "bitline_note": "Counts are per folded macro, before local bank replication of route segments.",
                },
            },
            indent=2,
        )
        + "\n"
    )


def write_decode_plan_md(path: Path, macro: str, rows: int, data_width: int, row_banks: int) -> None:
    addr_width = (rows - 1).bit_length()
    row_addr_width = addr_width - 2
    lines = [
        f"# {macro} Decode Plan",
        "",
        "## MCU-Facing Contract",
        "",
        f"- Keep a flat word address: `addr[{addr_width - 1}:0]`.",
        f"- Internal physical split: `bank = addr[{addr_width - 1}:{row_addr_width}]`, `row = addr[{row_addr_width - 1}:0]`.",
        f"- Organization: `{row_banks}` banks x `{rows // row_banks}` local rows x `{data_width}` data columns.",
        "- Do not expose bank/row as the primary software-visible contract; let the macro wrapper split the address.",
        "",
        "## Per-Port Decode",
        "",
        "- Four independent address decoders are required: `w0`, `w1`, `r0`, `r1`.",
        "- Each port uses a 2-to-4 bank predecode and a 7-to-128 local row decode.",
        "- The physical wordline segment is selected by `bank_oh[3:0] & row_oh[127:0]`.",
        "",
        "## Conflict Policy",
        "",
        "- If `w0` and `w1` target the same address in one cycle, assert `write_conflict`, fire `w0`, and gate off `w1`.",
        "- Read-during-write to the same accepted address should bypass write data in digital periphery.",
        "- Two reads to the same address are allowed.",
        "- Two writes to different addresses are allowed; the 12T cell has separate write ports.",
        "",
        "## Next Physical Blocks",
        "",
        "- 4x per-port predecoders: bank decode plus local row decode.",
        "- Bank-local WL drivers for `W0_WL`, `W1_WL`, `R0_RWL`, `R1_RWL`.",
        "- Column-side write drivers, read precharge, sense amps, and bank muxing.",
        "- Power straps/ring and pin placement after decoder/sense-amp footprint is known.",
    ]
    path.write_text("\n".join(lines) + "\n")


def build_one(
    *,
    source_mag: Path,
    source_layout,
    source_bbox: tuple[int, int, int, int],
    out_dir: Path,
    macro: str,
    rows: int,
    data_width: int,
    row_banks: int,
    magic: str,
    magic_rc: Path,
    run_drc: bool,
) -> MacroResult:
    if rows % row_banks != 0:
        raise ValueError(f"{macro}: rows={rows} must be divisible by row_banks={row_banks}")

    macro_dir = out_dir / macro
    magic_dir = macro_dir / "magic"
    layout_dir = macro_dir / "layout"
    abstract_dir = macro_dir / "abstract"
    for directory in (magic_dir, layout_dir, abstract_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_cell = source_layout.name
    shutil.copyfile(source_mag, magic_dir / source_mag.name)

    xlo, ylo, xhi, yhi = source_bbox
    if xlo != 0 or ylo != 0:
        raise ValueError(f"{source_mag}: expected origin-normalized bbox, got {source_bbox}")
    cell_width = xhi - xlo
    cell_height = yhi - ylo
    cell_width_um, cell_height_um, cell_area_um2 = dims_um(source_bbox)

    top_mag = magic_dir / f"{macro}.mag"
    write_top_magic(
        top_mag,
        macro=macro,
        source_cell=source_cell,
        tech=source_layout.tech,
        magscale=source_layout.magscale,
        cell_bbox=source_bbox,
        cell_width=cell_width,
        cell_height=cell_height,
        rows=rows,
        data_width=data_width,
        row_banks=row_banks,
    )

    width_um = row_banks * data_width * cell_width_um
    height_um = (rows // row_banks) * cell_height_um
    area_um2 = width_um * height_um

    drc_tcl = magic_dir / "run_macro_drc.tcl"
    gds_tcl = magic_dir / "write_macro_gds.tcl"
    write_drc_tcl(drc_tcl)
    write_gds_tcl(gds_tcl)
    drc_log = layout_dir / f"{macro}.drc.log"
    drc_errors: int | None = None
    if run_drc:
        drc_errors = run_magic(
            macro=macro,
            magic_dir=magic_dir,
            script=drc_tcl,
            log_path=drc_log,
            magic=magic,
            magic_rc=magic_rc,
        )

    gds_log = layout_dir / f"{macro}.gds.log"
    run_magic(
        macro=macro,
        magic_dir=magic_dir,
        script=gds_tcl,
        log_path=gds_log,
        magic=magic,
        magic_rc=magic_rc,
    )

    gds = layout_dir / f"{macro}.gds"
    lef = abstract_dir / f"{macro}.lef"
    verilog = abstract_dir / f"{macro}.blackbox.sv"
    spice = abstract_dir / f"{macro}.blackbox.spice"
    pins_json = abstract_dir / f"{macro}.pins.json"
    decode_contract = abstract_dir / f"{macro}.periphery_decode_contract.sv"
    behavioral_model = abstract_dir / f"{macro}.behavioral_model.sv"
    decode_plan_md = abstract_dir / f"{macro}.decode_plan.md"
    write_lef(lef, macro, width_um, height_um)
    write_verilog(verilog, macro, rows, data_width)
    write_spice(spice, macro, rows, data_width)
    write_pins_json(pins_json, macro, rows, data_width, row_banks)
    write_decode_contract(decode_contract, macro, rows, data_width)
    write_behavioral_model(behavioral_model, macro, rows, data_width)
    write_decode_plan_md(decode_plan_md, macro, rows, data_width, row_banks)

    return MacroResult(
        macro=macro,
        source_cell=source_cell,
        rows=rows,
        data_width=data_width,
        row_banks=row_banks,
        rows_per_bank=rows // row_banks,
        bitcells=rows * data_width,
        nfets_pfets_total=rows * data_width * 12,
        wordlines_total=4 * rows,
        vertical_bitlines_total=6 * data_width,
        cell_width_um=cell_width_um,
        cell_height_um=cell_height_um,
        cell_area_um2=cell_area_um2,
        width_um=round(width_um, 6),
        height_um=round(height_um, 6),
        area_um2=round(area_um2, 6),
        area_mm2=round(area_um2 / 1_000_000.0, 9),
        aspect_ratio=round(width_um / height_um, 6),
        magic=str(top_mag),
        gds=str(gds),
        lef=str(lef),
        verilog=str(verilog),
        spice=str(spice),
        pins_json=str(pins_json),
        decode_contract=str(decode_contract),
        behavioral_model=str(behavioral_model),
        decode_plan_md=str(decode_plan_md),
        drc_errors=drc_errors,
        drc_log=str(drc_log),
    )


def write_summary(results: list[MacroResult], out_dir: Path) -> None:
    with (out_dir / "summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(MacroResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))

    lines = [
        "# 12T 2W2R Macro Array Candidates",
        "",
        "These are array-only physical macro candidates built from `detronyx_12t_2w2r_rc1`.",
        "Decoder, precharge, write-driver, sense-amp, muxing, timing, and power-ring periphery are not included yet.",
        "",
        "| Macro | Rows x Width | Row banks | Bitcells | BBox | Area | DRC |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        drc = result.drc_errors if result.drc_errors is not None else "not run"
        lines.append(
            f"| `{result.macro}` | `{result.rows}x{result.data_width}` | {result.row_banks} | "
            f"{result.bitcells} | `{result.width_um:.3f}um x {result.height_um:.3f}um` | "
            f"`{result.area_mm2:.6f}mm^2` | `{drc}` |"
        )
    lines.extend(
        [
            "",
            "## Routing Line Counts",
            "",
            "| Macro | Wordlines | Vertical bitlines | FETs in raw array |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for result in results:
        lines.append(
            f"| `{result.macro}` | {result.wordlines_total} | "
            f"{result.vertical_bitlines_total} | {result.nfets_pfets_total} |"
        )
    lines.extend(
        [
            "",
            "## Status",
            "",
            "- Physical source leaf is DRC-clean and 2x2 boundary-clean at gap 0.",
            "- These macro GDS files are hierarchical Magic arrays of the RC1 leaf.",
            "- LEF abstracts are pinless blockages; high-level Verilog/SPICE stubs document the intended 2W2R contract only.",
            "- Decode contract artifacts fix the MCU-visible flat address and internal `bank=addr[8:7]`, `row=addr[6:0]` split.",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    (out_dir / "MANIFEST.json").write_text(json.dumps([asdict(r) for r in results], indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--magic", default="magic")
    parser.add_argument("--magic-rc", required=True, type=Path)
    parser.add_argument("--run-drc", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_layout = read_magic(args.source, args.source.stem)
    source_bbox = bbox(source_layout.rects)
    results = []
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for macro, rows, data_width, row_banks in DEFAULT_SPECS:
        result = build_one(
            source_mag=args.source,
            source_layout=source_layout,
            source_bbox=source_bbox,
            out_dir=args.out_dir,
            macro=macro,
            rows=rows,
            data_width=data_width,
            row_banks=row_banks,
            magic=args.magic,
            magic_rc=args.magic_rc,
            run_drc=args.run_drc,
        )
        results.append(result)
        drc = result.drc_errors if result.drc_errors is not None else "not run"
        print(
            f"{result.macro}: {result.width_um:.3f}um x {result.height_um:.3f}um "
            f"= {result.area_mm2:.6f}mm^2, drc={drc}"
        )
    write_summary(results, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
