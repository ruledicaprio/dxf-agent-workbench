from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(r"C:\Users\Rusmir\dxf-compress")

OUTPUT_ROOT = ROOT / "out" / "ORTHOGRAPHIC_BATCH"

ORTHOGRAPHIC_SCRIPT = ROOT / "dxf_orthographic_snapshots.py"

FILES = [
    ROOT / "P22-6_FG_Wilson.dxf",
    ROOT / "P22-6_FG_Wilson_BLOK.dxf",
    ROOT / "P22-6_FG_Wilson_BLOK_2.dxf",
    ROOT / "P22-6_FG_Wilson_BLOK_2_OPT10MB.dxf",
    ROOT / "P22-6_FG_Wilson_BLOK_3STAGE.dxf",
    ROOT / "P22-6_FG_Wilson_BLOK_OPT10MB.dxf",
    ROOT / "P22-6_FG_Wilson_SIMPLIFIED.dxf",
    ROOT / "P22-6_FG_Wilson.dwg",
]


# ------------------------------------------------------------
# Rendering settings
# ------------------------------------------------------------

IMAGE_SIZE = 2800

MAX_EDGES = 1_500_000

VIEWS = "top,front,right"


# ============================================================
# ODA SEARCH
# ============================================================

def find_oda_converter():
    """
    Try common Windows installation locations.

    If this doesn't find it, the DWG will simply be skipped
    rather than killing the whole batch.
    """

    candidates = [

        # Common ODA locations.
        Path(
            r"C:\Program Files\ODA\ODA File Converter\ODAFileConverter.exe"
        ),

        Path(
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
        ),
        Path(
            r"C:\Program Files\ODA\ODA File Converter 26.9.0\ODAFileConverter.exe"
        ),
    ]

    # Check PATH.
    from_path = shutil.which("ODAFileConverter")

    if from_path:
        return Path(from_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


# ============================================================
# FORMATTING
# ============================================================

def mb(path: Path):
    try:
        return path.stat().st_size / (1024 * 1024)
    except Exception:
        return 0.0


def safe_name(path: Path):
    """
    Folder name without problematic characters.
    """
    return "".join(
        c if c.isalnum() or c in "-_." else "_"
        for c in path.stem
    )


# ============================================================
# DWG -> DXF
# ============================================================

def convert_dwg_with_oda(dwg_path: Path):
    """
    Convert one DWG into a DXF using ODA File Converter.

    The ODA converter operates on directories, so we create
    a temporary source directory containing only this DWG.
    """

    oda = find_oda_converter()

    if oda is None:

        return {
            "success": False,
            "reason": "ODAFileConverter.exe not found",
            "dxf": None,
        }

    print()
    print("-" * 70)
    print("DWG -> DXF")
    print("-" * 70)

    print(f"ODA: {oda}")
    print(f"Input: {dwg_path}")

    work = OUTPUT_ROOT / "_DWG_CONVERSION"

    source_dir = work / "source"
    target_dir = work / "converted"

    source_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Copy only the requested DWG into the source directory.
    isolated_dwg = source_dir / dwg_path.name

    if isolated_dwg.exists():
        isolated_dwg.unlink()

    shutil.copy2(
        dwg_path,
        isolated_dwg,
    )

    # --------------------------------------------------------
    # ODA File Converter CLI
    #
    # Syntax used by the Windows converter:
    #
    # ODAFileConverter
    #   source_directory
    #   target_directory
    #   version
    #   type
    #   recurse
    #   audit
    #   filter
    #
    # We request a modern ASCII DXF.
    # --------------------------------------------------------

    command = [
        str(oda),
        str(source_dir),
        str(target_dir),
        "ACAD2018",
        "DXF",
        "0",
        "1",
        "*.dwg",
    ]

    print()
    print("Running ODA:")
    print(" ".join(f'"{x}"' for x in command))
    print()

    started = time.time()

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60 * 60,
        )

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "reason": "ODA conversion timed out",
            "dxf": None,
        }

    except Exception as exc:

        return {
            "success": False,
            "reason": f"ODA launch error: {exc}",
            "dxf": None,
        }

    elapsed = time.time() - started

    print(
        f"ODA exit code: {result.returncode}"
    )

    print(
        f"ODA time: {elapsed:,.1f} sec"
    )

    if result.stdout:
        print("ODA stdout:")
        print(result.stdout[-4000:])

    if result.stderr:
        print("ODA stderr:")
        print(result.stderr[-4000:])

    # --------------------------------------------------------
    # Find produced DXF
    # --------------------------------------------------------

    produced = list(
        target_dir.glob("*.dxf")
    )

    if not produced:

        return {
            "success": False,
            "reason": (
                "ODA completed but produced no DXF"
            ),
            "dxf": None,
        }

    # Normally there will be exactly one.
    dxf = produced[0]

    print()
    print(
        f"Converted DXF: {dxf}"
    )

    print(
        f"Converted size: {mb(dxf):,.1f} MB"
    )

    return {
        "success": True,
        "reason": None,
        "dxf": dxf,
    }


# ============================================================
# RUN ORTHOGRAPHIC PROCESSOR
# ============================================================

def process_dxf(dxf_path: Path, source_label: str):
    """
    Call the main orthographic renderer as a subprocess.

    Subprocess isolation is intentional: if a huge or malformed
    DXF crashes Python, the batch can continue with the next file.
    """

    folder = OUTPUT_ROOT / safe_name(dxf_path)

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 80)
    print("PROCESSING")
    print("=" * 80)

    print(
        f"Source : {source_label}"
    )

    print(
        f"DXF    : {dxf_path}"
    )

    print(
        f"Size   : {mb(dxf_path):,.1f} MB"
    )

    print(
        f"Output : {folder}"
    )

    command = [
        sys.executable,
        str(ORTHOGRAPHIC_SCRIPT),
        str(dxf_path),
        "--out",
        str(folder),
        "--size",
        str(IMAGE_SIZE),
        "--max-edges",
        str(MAX_EDGES),
        "--views",
        VIEWS,
    ]

    print()
    print(
        "Command:"
    )

    print(
        " ".join(
            f'"{x}"'
            for x in command
        )
    )

    started = time.time()

    try:

        result = subprocess.run(
            command,
            text=True,
        )

    except Exception as exc:

        elapsed = time.time() - started

        return {
            "success": False,
            "source": source_label,
            "dxf": str(dxf_path),
            "output": str(folder),
            "elapsed_seconds": elapsed,
            "reason": f"Could not launch renderer: {exc}",
        }

    elapsed = time.time() - started

    success = result.returncode == 0

    return {
        "success": success,
        "source": source_label,
        "dxf": str(dxf_path),
        "output": str(folder),
        "elapsed_seconds": elapsed,
        "return_code": result.returncode,
        "reason": (
            None
            if success
            else f"Renderer exit code {result.returncode}"
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 80)
    print("DXF / DWG ORTHOGRAPHIC BATCH")
    print("=" * 80)

    print()
    print(f"Root: {ROOT}")
    print(f"Output: {OUTPUT_ROOT}")
    print()

    if not ORTHOGRAPHIC_SCRIPT.exists():

        print(
            "ERROR:"
        )

        print(
            f"Missing renderer:\n{ORTHOGRAPHIC_SCRIPT}"
        )

        sys.exit(1)

    report = {
        "started": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "root": str(ROOT),
        "files": [],
    }

    batch_start = time.time()

    for index, original in enumerate(FILES, start=1):

        print()
        print()
        print("#" * 80)
        print(
            f"FILE {index} / {len(FILES)}"
        )
        print("#" * 80)

        # ----------------------------------------------------
        # Missing file
        # ----------------------------------------------------

        if not original.exists():

            print(
                f"SKIP — file not found:\n{original}"
            )

            report["files"].append({
                "source": str(original),
                "success": False,
                "status": "MISSING",
                "reason": "File not found",
            })

            continue

        extension = original.suffix.lower()

        # ----------------------------------------------------
        # DXF
        # ----------------------------------------------------

        if extension == ".dxf":

            result = process_dxf(
                original,
                str(original),
            )

            result["status"] = (
                "SUCCESS"
                if result["success"]
                else "FAILED"
            )

            report["files"].append(result)

            if result["success"]:

                print()
                print(
                    f"SUCCESS: {original.name}"
                )

            else:

                print()
                print(
                    f"FAILED: {original.name}"
                )

                print(
                    result.get("reason")
                )

            continue

        # ----------------------------------------------------
        # DWG
        # ----------------------------------------------------

        if extension == ".dwg":

            conversion = convert_dwg_with_oda(
                original
            )

            if not conversion["success"]:

                print()
                print(
                    f"SKIP DWG: {original.name}"
                )

                print(
                    conversion["reason"]
                )

                report["files"].append({
                    "source": str(original),
                    "success": False,
                    "status": "DWG_SKIPPED",
                    "reason": conversion["reason"],
                })

                continue

            converted_dxf = conversion["dxf"]

            result = process_dxf(
                converted_dxf,
                str(original),
            )

            result["dwg_conversion"] = True
            result["status"] = (
                "SUCCESS"
                if result["success"]
                else "FAILED_AFTER_DWG_CONVERSION"
            )

            report["files"].append(result)

            continue

        # ----------------------------------------------------
        # Unknown
        # ----------------------------------------------------

        print(
            f"SKIP — unsupported extension: {extension}"
        )

        report["files"].append({
            "source": str(original),
            "success": False,
            "status": "UNSUPPORTED",
            "reason": f"Unsupported extension {extension}",
        })

    # ========================================================
    # FINAL REPORT
    # ========================================================

    elapsed = time.time() - batch_start

    report["finished"] = time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    report["elapsed_seconds"] = elapsed

    report_path = (
        OUTPUT_ROOT /
        "batch_report.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    successful = [
        x for x in report["files"]
        if x.get("success")
    ]

    failed = [
        x for x in report["files"]
        if not x.get("success")
    ]

    print()
    print()
    print("=" * 80)
    print("BATCH COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Successful : {len(successful)}"
    )

    print(
        f"Failed/skipped : {len(failed)}"
    )

    print(
        f"Total time : {elapsed:,.1f} sec"
    )

    print()
    print(
        f"Report:\n{report_path}"
    )

    print()
    print("Results:")

    for item in report["files"]:

        name = Path(
            item["source"]
        ).name

        status = item.get(
            "status",
            "UNKNOWN",
        )

        print(
            f"  {status:30s} {name}"
        )

    print()
    print(
        f"All output is under:\n{OUTPUT_ROOT}"
    )


if __name__ == "__main__":
    main()
