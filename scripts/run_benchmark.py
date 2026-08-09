from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from dxf_agent.render.orthographic import render_dxf_view as render_view


# ----------------------------------------------------------------------
# ODA conversion helper (taken from your legacy script)
# ----------------------------------------------------------------------

def find_oda_converter(oda_path: Optional[Path] = None) -> Optional[Path]:
    """Locate ODAFileConverter.exe."""
    if oda_path and oda_path.exists():
        return oda_path
    candidates = [
        Path(r"C:\Program Files\ODA\ODA File Converter\ODAFileConverter.exe"),
        Path(r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"),
        Path(r"C:\Program Files\ODA\ODA File Converter 26.9.0\ODAFileConverter.exe"),
    ]
    from_path = shutil.which("ODAFileConverter")
    if from_path:
        return Path(from_path)
    for c in candidates:
        if c.exists():
            return c
    return None


def oda_convert_to_dxf(dwg_path: Path, oda_path: Optional[Path] = None) -> Optional[Path]:
    """
    Convert a DWG to DXF using ODA File Converter.
    Returns the path to the converted DXF, or None on failure.
    """
    oda = find_oda_converter(oda_path)
    if oda is None:
        print("ODAFileConverter not found; skipping DWG conversion.")
        return None

    work_dir = Path("artifacts/benchmarks/_DWG_CONVERSION")
    source_dir = work_dir / "source"
    target_dir = work_dir / "converted"
    source_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    # isolate the DWG
    isolated = source_dir / dwg_path.name
    if isolated.exists():
        isolated.unlink()
    shutil.copy2(dwg_path, isolated)

    cmd = [
        str(oda),
        str(source_dir),
        str(target_dir),
        "ACAD2018",
        "DXF",
        "0",
        "1",
        "*.dwg",
    ]
    print(f"Running ODA: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        print("ODA timed out.")
        return None
    except Exception as e:
        print(f"ODA launch error: {e}")
        return None

    if result.returncode != 0:
        print(f"ODA exit code {result.returncode}")
        print(result.stderr[-2000:])
        return None

    produced = list(target_dir.glob("*.dxf"))
    if not produced:
        print("ODA produced no DXF.")
        return None

    dxf = produced[0]
    print(f"Converted DXF: {dxf} ({dxf.stat().st_size / 1e6:.1f} MB)")
    return dxf


# ----------------------------------------------------------------------
# Benchmark runner
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Batch orthographic render benchmark")
    parser.add_argument("--manifest", type=Path, help="JSON manifest of files")
    parser.add_argument("--views", default="top,front,right", help="Comma-separated views")
    parser.add_argument("--resolution", type=int, default=2800, help="Output resolution")
    parser.add_argument("--oda-path", type=Path, help="Path to ODAFileConverter.exe")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent  # scripts/ -> repo root
    artifacts_dir = repo_root / "artifacts" / "benchmarks"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    views = [v.strip() for v in args.views.split(",")]

    # Load file list
    if args.manifest:
        with open(args.manifest) as f:
            manifest = json.load(f)
        corpus_root = Path(manifest.get("corpus_root", "."))
        files_data = manifest["files"]
    else:
        # Default fallback: your legacy set (relative to repo root)
        default_files = [
            "corpus/P22-6_FG_Wilson.dxf",
            "corpus/P22-6_FG_Wilson_BLOK.dxf",
            "corpus/P22-6_FG_Wilson_BLOK_2.dxf",
            "corpus/P22-6_FG_Wilson_BLOK_2_OPT10MB.dxf",
            "corpus/P22-6_FG_Wilson_BLOK_3STAGE.dxf",
            "corpus/P22-6_FG_Wilson_BLOK_OPT10MB.dxf",
            "corpus/P22-6_FG_Wilson_SIMPLIFIED.dxf",
            "corpus/P22-6_FG_Wilson.dwg",
        ]
        corpus_root = repo_root / "corpus"
        files_data = [{"path": f, "views": views, "resolution": args.resolution} for f in default_files]

    report = {
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [],
    }

    for idx, entry in enumerate(files_data, start=1):
        rel_path = entry["path"]
        full_path = (corpus_root / rel_path).resolve()
        print(f"\n{'#'*60}\nFile {idx}/{len(files_data)}: {full_path.name}")

        if not full_path.exists():
            report["results"].append({"file": str(full_path), "status": "MISSING"})
            continue

        # DWG conversion if needed
        if full_path.suffix.lower() == ".dwg":
            print("DWG detected, converting...")
            dxf_path = oda_convert_to_dxf(full_path, args.oda_path)
            if dxf_path is None:
                report["results"].append({"file": str(full_path), "status": "DWG_CONVERSION_FAILED"})
                continue
            full_path = dxf_path

        # Ensure we have a DXF
        if full_path.suffix.lower() != ".dxf":
            report["results"].append({"file": str(full_path), "status": "UNSUPPORTED_FORMAT"})
            continue

        # Render each view
        file_views = entry.get("views", views)
        out_dir = artifacts_dir / full_path.stem
        out_dir.mkdir(exist_ok=True)

        for view in file_views:
            out_png = out_dir / f"{view}.png"
            t0 = time.time()
            try:
                render_view(
                    filepath=str(full_path),
                    view=view,
                    output_path=str(out_png),
                    resolution=entry.get("resolution", args.resolution),
                    max_edges=args.max_edges if hasattr(args, 'max_edges') else 8_000_000,
                )
                elapsed = time.time() - t0
                report["results"].append({
                    "file": str(full_path),
                    "view": view,
                    "output": str(out_png),
                    "elapsed_sec": elapsed,
                    "status": "SUCCESS",
                })
                print(f"  {view}: {elapsed:.1f}s -> {out_png}")
            except Exception as e:
                report["results"].append({
                    "file": str(full_path),
                    "view": view,
                    "error": str(e),
                    "status": "FAILED",
                })
                print(f"  {view}: FAILED ({e})")

    # Final report
    report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    report_path = artifacts_dir / "batch_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to {report_path}")

if __name__ == "__main__":
    main()
