#!/usr/bin/env python3
"""
dxf_orthographic_snapshots.py
Improved orthographic renderer for large / noisy DXF meshes (Meshy5, gensets, etc.)

Features:
- Proper model centering
- Automatic scale normalization (model is scaled to a comfortable size)
- High edge limit (configurable)
- Clean TOP / FRONT / RIGHT views
- Robust against broken / non-manifold meshes

Usage:
    python dxf_orthographic_snapshots.py input.dxf
    python dxf_orthographic_snapshots.py input.dxf --out ./preview --size 3200 --max-edges 8000000
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
except ImportError:
    print("[ERROR] matplotlib is required: pip install matplotlib")
    sys.exit(1)

try:
    import trimesh
except ImportError:
    print("[ERROR] trimesh is required: pip install trimesh")
    sys.exit(1)

# ============================================================
# CONFIG DEFAULTS
# ============================================================

DEFAULT_SIZE = 3200
DEFAULT_MAX_EDGES = 8_000_000          # much higher than before
DEFAULT_VIEWS = ["top", "front", "right"]
LINE_WIDTH = 0.35
BACKGROUND = "#0f1419"
FOREGROUND = "#e8eef5"
PADDING = 0.06                         # relative padding around the model


# ============================================================
# UTILITY: safe mesh cleaning
# ============================================================

def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Safely clean a mesh, ignoring methods that may not exist in older versions."""
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    if hasattr(mesh, "remove_degenerate_faces"):
        mesh.remove_degenerate_faces()
    return mesh


# ============================================================
# DXF → MESH (robust loader using ezdxf)
# ============================================================

def load_dxf_as_mesh(path: Path, max_faces: int | None = None) -> trimesh.Trimesh:
    """
    Load a DXF file, extracting 3DFACE entities and converting them to a trimesh.
    Falls back to trimesh native loader if ezdxf is unavailable or readfile fails.
    """
    try:
        import ezdxf
        if not hasattr(ezdxf, "readfile"):
            raise AttributeError("ezdxf.readfile not found")
    except (ImportError, AttributeError) as e:
        print(f"[*] ezdxf not usable ({e}); falling back to trimesh native loader")
        return _load_with_trimesh(path, max_faces)

    try:
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        vertices = []
        faces = []
        face_count = 0

        for entity in msp:
            if max_faces is not None and face_count >= max_faces:
                break

            if entity.dxftype() == "3DFACE":
                # Correct vertex access
                p0 = entity.dxf.vtx0
                p1 = entity.dxf.vtx1
                p2 = entity.dxf.vtx2
                p3 = entity.dxf.vtx3
                pts = np.array([(p0.x, p0.y, p0.z),
                                (p1.x, p1.y, p1.z),
                                (p2.x, p2.y, p2.z),
                                (p3.x, p3.y, p3.z)], dtype=np.float64)
                # Check if last is duplicate
                if np.allclose(pts[0], pts[3]):
                    tri = pts[:3]
                    base = len(vertices)
                    vertices.extend(tri)
                    faces.append([base, base+1, base+2])
                    face_count += 1
                else:
                    # Two triangles
                    tri1 = pts[[0,1,2]]
                    tri2 = pts[[0,2,3]]
                    base = len(vertices)
                    vertices.extend(tri1)
                    vertices.extend(tri2)
                    faces.append([base, base+1, base+2])
                    faces.append([base+3, base+4, base+5])
                    face_count += 2

        if not vertices:
            print("[*] No 3DFACE entities found; falling back to trimesh native loader")
            return _load_with_trimesh(path, max_faces)

        vertices = np.array(vertices, dtype=np.float64)
        faces = np.array(faces, dtype=np.int64)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        clean_mesh(mesh)
        print(f"[*] Loaded {len(mesh.faces):,} faces from 3DFACE entities")
        return mesh

    except Exception as e:
        print(f"[WARN] ezdxf parser failed: {e}")
        print("[*] Falling back to trimesh native loader")
        return _load_with_trimesh(path, max_faces)


def _load_with_trimesh(path: Path, max_faces: int | None = None) -> trimesh.Trimesh:
    """
    Fallback loader using trimesh's native DXF importer.
    """
    try:
        mesh = trimesh.load(str(path), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            # Combine all geometries into one mesh
            meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if not meshes:
                raise ValueError("No meshes found in scene")
            mesh = trimesh.util.concatenate(meshes)
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError(f"Loaded object is not a Trimesh: {type(mesh)}")
        clean_mesh(mesh)
        print(f"[*] Loaded {len(mesh.faces):,} faces via trimesh native loader")
        return mesh
    except Exception as e:
        raise RuntimeError(f"Failed to load mesh: {e}") from e


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_mesh(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict]:
    """
    Center the mesh at origin and scale it so the largest dimension ≈ 2.0
    (comfortable size for orthographic rendering).
    """
    clean_mesh(mesh)

    bounds = mesh.bounds
    center = (bounds[0] + bounds[1]) * 0.5
    extents = bounds[1] - bounds[0]
    max_dim = float(np.max(extents))

    if max_dim < 1e-9:
        max_dim = 1.0

    scale = 2.0 / max_dim
    mesh.vertices = (mesh.vertices - center) * scale

    info = {
        "original_center": center.tolist(),
        "original_extents": extents.tolist(),
        "original_max_dim": max_dim,
        "applied_scale": scale,
        "new_bounds": mesh.bounds.tolist(),
    }

    print(f"[*] Normalized: centered + scaled by {scale:.4f}")
    print(f"    Original size: {extents}")
    print(f"    New size     : {mesh.extents}")

    return mesh, info


# ============================================================
# EDGE EXTRACTION (with limit)
# ============================================================

def extract_edges(mesh: trimesh.Trimesh, max_edges: int) -> np.ndarray:
    """
    Return unique edges as (N, 2, 3) array.
    If there are too many edges we randomly subsample (keeps visual density).
    """
    edges = mesh.edges_unique
    segments = mesh.vertices[edges]

    n = len(segments)
    print(f"[*] Unique edges: {n:,}")

    if n > max_edges:
        print(f"[*] Subsampling edges {n:,} → {max_edges:,}")
        idx = np.random.choice(n, size=max_edges, replace=False)
        segments = segments[idx]

    return segments


# ============================================================
# RENDERING
# ============================================================

def project_view(segments: np.ndarray, view: str) -> np.ndarray:
    """Project 3D edge segments into 2D according to the view."""
    view = view.lower()

    if view == "top":       # looking down -Z
        return segments[:, :, [0, 1]]
    elif view == "front":   # looking along +Y
        return segments[:, :, [0, 2]]
    elif view == "right":   # looking along +X
        return segments[:, :, [1, 2]]
    elif view == "iso":
        x = segments[:, :, 0]
        y = segments[:, :, 1]
        z = segments[:, :, 2]
        px = x - y
        py = (x + y) * 0.5 + z
        return np.stack([px, py], axis=-1)
    else:
        raise ValueError(f"Unknown view: {view}")


def render_view(
    segments_2d: np.ndarray,
    view_name: str,
    out_path: Path,
    image_size: int = 3200,
    line_width: float = LINE_WIDTH,
):
    """Render one orthographic view to PNG."""
    fig = plt.figure(
        figsize=(image_size / 100, image_size / 100),
        dpi=100,
        facecolor=BACKGROUND,
    )
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_facecolor(BACKGROUND)
    ax.set_aspect("equal")
    ax.axis("off")

    lc = LineCollection(
        list(segments_2d),
        colors=FOREGROUND,
        linewidths=line_width,
        alpha=0.92,
    )
    ax.add_collection(lc)

    all_pts = segments_2d.reshape(-1, 2)
    mins = all_pts.min(axis=0)
    maxs = all_pts.max(axis=0)
    span = maxs - mins
    span[span < 1e-9] = 1.0

    pad = span * PADDING
    ax.set_xlim(mins[0] - pad[0], maxs[0] + pad[0])
    ax.set_ylim(mins[1] - pad[1], maxs[1] + pad[1])

    ax.text(
        0.02, 0.98, view_name.upper(),
        transform=ax.transAxes,
        color="#8ab4f8",
        fontsize=14,
        fontfamily="monospace",
        verticalalignment="top",
        alpha=0.9,
    )

    fig.savefig(
        out_path,
        dpi=100,
        facecolor=BACKGROUND,
        bbox_inches=None,
        pad_inches=0,
    )
    plt.close(fig)
    print(f"    → {out_path.name}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Improved orthographic DXF renderer (centered + normalized)"
    )
    parser.add_argument("input", type=Path, help="Input DXF file")
    parser.add_argument("--out", type=Path, default=None, help="Output folder")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="Image size in pixels")
    parser.add_argument("--max-edges", type=int, default=DEFAULT_MAX_EDGES)
    parser.add_argument("--views", type=str, default="top,front,right", help="Comma-separated views: top,front,right,iso")
    parser.add_argument("--max-faces", type=int, default=None, help="Limit number of faces loaded to save memory")
    args = parser.parse_args()

    input_path: Path = args.input
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    out_dir = args.out or (input_path.parent / f"{input_path.stem}_ORTHO")
    out_dir.mkdir(parents=True, exist_ok=True)

    views = [v.strip().lower() for v in args.views.split(",") if v.strip()]

    t0 = time.time()

    # 1. Load
    mesh = load_dxf_as_mesh(input_path, max_faces=args.max_faces)

    # 2. Normalize
    mesh, norm_info = normalize_mesh(mesh)

    # 3. Extract edges
    segments = extract_edges(mesh, max_edges=args.max_edges)

    # 4. Render
    print(f"[*] Rendering {len(views)} view(s) at {args.size}px ...")
    for view in views:
        try:
            seg2d = project_view(segments, view)
            out_file = out_dir / f"{view}.png"
            render_view(seg2d, view, out_file, image_size=args.size)
        except Exception as e:
            print(f"[WARN] Failed to render {view}: {e}")

    # 5. Metadata
    meta = {
        "input_file": str(input_path),
        "input_size_MB": input_path.stat().st_size / (1024 * 1024),
        "faces": len(mesh.faces),
        "vertices": len(mesh.vertices),
        "edges_rendered": len(segments),
        "views": [v.upper() for v in views],
        "image_size": args.size,
        "normalization": norm_info,
        "created_by": "dxf_orthographic_snapshots.py (improved)",
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print()
    print("=" * 60)
    print("DONE")
    print(f"  Output folder : {out_dir}")
    print(f"  Faces         : {len(mesh.faces):,}")
    print(f"  Edges drawn   : {len(segments):,}")
    print(f"  Time          : {time.time() - t0:.1f}s")
    print("=" * 60)


def render_dxf_view(
    filepath: str,
    view: str,
    output_path: str,
    resolution: int = 3200,
    max_edges: int = DEFAULT_MAX_EDGES,
    max_faces: int | None = None,
) -> dict:
    """
    High‑level entry point for benchmarks: load a DXF, normalize,
    extract edges, project a single view, and save the PNG.
    Returns a metadata dict.
    """
    path = Path(filepath)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    mesh = load_dxf_as_mesh(path, max_faces=max_faces)
    mesh, norm = normalize_mesh(mesh)
    segs = extract_edges(mesh, max_edges=max_edges)
    seg2d = project_view(segs, view)
    render_view(seg2d, view, out, image_size=resolution)

    elapsed = time.time() - t0
    meta = {
        "faces": len(mesh.faces),
        "edges_rendered": len(segs),
        "normalization": norm,
        "elapsed_sec": round(elapsed, 2),
    }
    meta_path = out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    main()
