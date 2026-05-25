#!/usr/bin/env python3
"""Gate Avalon stdcell-backed control collateral in the release package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BASIC_CUSTOM_RE = re.compile(r"detronyx_12t_ctrl_(inv|nand2|nand3|nand4|nor2)_rc7")
AVALON_PREFIX = "gf180mcu_as_sc_mcu7t3v3__"
REQUIRED_AVALON_CELLS = {
    "gf180mcu_as_sc_mcu7t3v3__inv_2",
    "gf180mcu_as_sc_mcu7t3v3__nand2_2",
    "gf180mcu_as_sc_mcu7t3v3__nand3_2",
    "gf180mcu_as_sc_mcu7t3v3__nand4_2",
    "gf180mcu_as_sc_mcu7t3v3__nor2_2",
}
CUSTOM_ROW_SELECT = {
    "detronyx_12t_ctrl_row_select3_wlbuf_rc7",
    "detronyx_12t_ctrl_row_select4_wlbuf_rc7",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def add(checks: list[dict[str, Any]], status: str, area: str, check: str, evidence: Path | str, detail: str) -> None:
    checks.append(
        {
            "status": status,
            "area": area,
            "check": check,
            "evidence": str(evidence),
            "detail": detail,
        }
    )


def resolve_include(cdl: Path, include_line: str) -> Path | None:
    match = re.match(r'\.include\s+"([^"]+)"', include_line.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return (cdl.parent / match.group(1)).resolve()


def bytes_contain(path: Path, needle: str) -> bool:
    return needle.encode("ascii") in path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path("."))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/stdcell_control_integration/MANIFEST.json"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("verification/results/gf180mcu_3v3_12t_2r2w_sram_stdcell_control_gate"),
    )
    parser.add_argument(
        "--row-select-gds-manifest",
        type=Path,
        default=Path("reports/stdcell_row_select_gds_merge/MANIFEST.json"),
    )
    parser.add_argument(
        "--require-macro-gds-instances",
        action="store_true",
        help="Fail unless the published macro GDS files contain stdcell/control leaf instance names.",
    )
    args = parser.parse_args()

    root = args.package_root.resolve()
    manifest_path = (root / args.manifest).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []

    if not file_ok(manifest_path):
        add(checks, "FAIL", "stdcell-control", "manifest exists", manifest_path, "missing manifest")
    else:
        add(checks, "PASS", "stdcell-control", "manifest exists", manifest_path, "present")

    manifest = load_json(manifest_path) if file_ok(manifest_path) else {}
    row_select_gds_path = (root / args.row_select_gds_manifest).resolve()
    row_select_gds = load_json(row_select_gds_path) if file_ok(row_select_gds_path) else {"results": []}
    row_select_by_macro = {str(item.get("macro")): item for item in row_select_gds.get("results", [])}
    avalon = manifest.get("avalon", {})
    avalon_files = avalon.get("files", [])
    for item in avalon_files:
        path = root / str(item["path"])
        add(
            checks,
            "PASS" if file_ok(path) else "FAIL",
            "Avalon stdcell library",
            "required collateral file",
            path,
            f"bytes={path.stat().st_size if path.exists() else 0}",
        )

    required = set(avalon.get("required_cells", [])) or REQUIRED_AVALON_CELLS
    cdl = root / "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/cdl/gf180mcu_as_sc_mcu7t3v3.cdl"
    lef = root / "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/lef/gf180mcu_as_sc_mcu7t3v3.lef"
    verilog = root / "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/verilog/gf180mcu_as_sc_mcu7t3v3.v"
    gds = root / "third_party/gf180mcu_as_sc_mcu7t3v3/pdk/libs.ref/gf180mcu_as_sc_mcu7t3v3/gf180mcu_as_sc_mcu7t3v3__merged.gds"
    for cell in sorted(required):
        cdl_ok = file_ok(cdl) and f".subckt {cell}" in cdl.read_text(encoding="utf-8", errors="replace")
        lef_ok = file_ok(lef) and f"MACRO {cell}" in lef.read_text(encoding="utf-8", errors="replace")
        v_ok = file_ok(verilog) and f"module {cell}" in verilog.read_text(encoding="utf-8", errors="replace")
        gds_ok = file_ok(gds) and bytes_contain(gds, cell)
        status = "PASS" if cdl_ok and lef_ok and v_ok and gds_ok else "FAIL"
        add(checks, status, "Avalon stdcell library", f"{cell} views", cdl, f"cdl={cdl_ok}, lef={lef_ok}, verilog={v_ok}, gds={gds_ok}")

    for cell in sorted(CUSTOM_ROW_SELECT):
        leaf_dir = root / "reports/control_leaf_library" / cell
        required_leaf = [
            leaf_dir / "magic" / f"{cell}.mag",
            leaf_dir / "layout" / f"{cell}.gds",
            leaf_dir / "abstract" / f"{cell}.lef",
            leaf_dir / "abstract" / f"{cell}.reference.cdl",
        ]
        ok = all(file_ok(path) for path in required_leaf)
        add(checks, "PASS" if ok else "FAIL", "custom row-select library", cell, leaf_dir, f"required_files={len(required_leaf)}, present={sum(file_ok(path) for path in required_leaf)}")

    for item in manifest.get("control_matrices", []):
        macro = str(item["macro"])
        cdl_path = root / str(item["cdl"])
        macro_cdl = root / str(item["macro_abstract_cdl"])
        for path in (cdl_path, macro_cdl):
            if not file_ok(path):
                add(checks, "FAIL", macro, "stdcell control CDL exists", path, "missing")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            unmapped = sorted(set(BASIC_CUSTOM_RE.findall(text)))
            avalon_count = sum(text.count(cell) for cell in REQUIRED_AVALON_CELLS)
            row_select_count = sum(text.count(cell) for cell in CUSTOM_ROW_SELECT)
            include_paths = [resolve_include(path, line) for line in text.splitlines() if line.strip().lower().startswith(".include")]
            include_ok = all(p is not None and file_ok(p) for p in include_paths)
            status = "PASS" if not unmapped and avalon_count > 0 and row_select_count > 0 and include_ok else "FAIL"
            add(
                checks,
                status,
                macro,
                "stdcell control CDL mapping",
                path,
                f"avalon_refs={avalon_count}, row_select_refs={row_select_count}, unmapped_basic={unmapped}, include_ok={include_ok}",
            )

        macro_gds = root / "macros" / macro / "layout" / f"{macro}.gds"
        has_stdcell = file_ok(macro_gds) and any(bytes_contain(macro_gds, cell) for cell in REQUIRED_AVALON_CELLS)
        row_select_item = row_select_by_macro.get(macro, {})
        has_row_select_expansion = (
            row_select_item.get("status") == "PASS"
            and row_select_item.get("footprint_unchanged") is True
            and file_ok(macro_gds)
            and bytes_contain(macro_gds, "gf180mcu_as_sc_mcu7t3v3__nand4_2")
            and bytes_contain(macro_gds, "gf180mcu_as_sc_mcu7t3v3__inv_2")
        )
        add(
            checks,
            "PASS" if has_stdcell else "FAIL",
            macro,
            "published macro GDS contains Avalon stdcells",
            macro_gds,
            f"has_avalon_stdcell={has_stdcell}",
        )
        add(
            checks,
            "PASS" if has_row_select_expansion else ("FAIL" if args.require_macro_gds_instances else "OPEN"),
            macro,
            "published macro GDS contains row-select stdcell expansion",
            macro_gds,
            f"row_select_manifest_status={row_select_item.get('status')}, has_row_select_expansion={has_row_select_expansion}",
        )

    counts: dict[str, int] = {}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    result = {"status_counts": counts, "checks": checks}
    (out_dir / "MANIFEST.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# GF180MCU 12T SRAM Stdcell Control Gate",
        "",
        f"- Status counts: `{counts}`",
        "",
        "| Area | Check | Status | Detail | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(
            "| `{area}` | `{check}` | `{status}` | {detail} | `{evidence}` |".format(
                area=check["area"],
                check=check["check"],
                status=check["status"],
                detail=check["detail"].replace("|", "/"),
                evidence=check["evidence"],
            )
        )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"GF180MCU 12T SRAM stdcell control gate: {counts}")
    print(out_dir / "README.md")
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
