#!/usr/bin/env python3
"""Benchmark the Wilson DXF."""
import sys, time, json
from pathlib import Path

# make src importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dxf_agent.render.orthographic import load_dxf_as_mesh, normalize_mesh, extract_edges, project_view, render_view

DXF_PATH = Path(__file__).resolve().parents[1] / "corpus" / "P22-6_FG_Wilson.dxf"
OUT_DIR = Path("benchmark_results")  # keep in repo but ignore via .gitignore
OUT_DIR.mkdir(exist_ok=True)

results = {}
t0 = time.time()

mesh = load_dxf_as_mesh(DXF_PATH, max_faces=2_000_000)
mesh, norm = normalize_mesh(mesh)
edges = extract_edges(mesh, max_edges=5_000_000)

for view in ("top", "front", "right"):
    t_view = time.time()
    seg2d = project_view(edges, view)
    out_png = OUT_DIR / f"{view}.png"
    render_view(seg2d, view, out_png, image_size=3200)
    results[view] = {"time_sec": round(time.time() - t_view, 2)}

total = time.time() - t0
results["total_time_sec"] = round(total, 2)
results["faces"] = len(mesh.faces)
results["edges"] = len(edges)

with open(OUT_DIR / "benchmark.json", "w") as f:
    json.dump(results, f, indent=2)

print("Benchmark done:", json.dumps(results, indent=2))
