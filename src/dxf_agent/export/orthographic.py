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
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
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
DEFAULT_MAX_EDGES = 8_000_000  # much higher than before
DEFAULT_VIEWS = ["top", "front", "right"]
LINE_WIDTH = 0.35
BACKGROUND = "#0f1419"
FOREGROUND = "#e8eef5"
PADDING = 0.06  # relative padding around the model


def _log(*args, **kwargs) -> None:
    """Progress/diagnostic output. Always stderr, so stdout stays parseable."""
    print(*args, file=sys.stderr, **kwargs)


# ============================================================
# UTILITY: safe mesh cleaning
# ============================================================


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Safely clean a mesh, ignoring methods that may not exist in older versions."""
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    if hasattr(mesh, "remove_degenerate_faces"):
        mesh.remove_degenerate_faces()  # type: ignore
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
        _log(f"[*] ezdxf not usable ({e}); falling back to trimesh native loader")
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
                pts = np.array(
                    [
                        (p0.x, p0.y, p0.z),
                        (p1.x, p1.y, p1.z),
                        (p2.x, p2.y, p2.z),
                        (p3.x, p3.y, p3.z),
                    ],
                    dtype=np.float64,
                )
                # Check if last is duplicate
                if np.allclose(pts[0], pts[3]):
                    tri = pts[:3]
                    base = len(vertices)
                    vertices.extend(tri)
                    faces.append([base, base + 1, base + 2])
                    face_count += 1
                else:
                    # Two triangles
                    tri1 = pts[[0, 1, 2]]
                    tri2 = pts[[0, 2, 3]]
                    base = len(vertices)
                    vertices.extend(tri1)
                    vertices.extend(tri2)
                    faces.append([base, base + 1, base + 2])
                    faces.append([base + 3, base + 4, base + 5])
                    face_count += 2

        if not vertices:
            _log("[*] No 3DFACE entities found; falling back to trimesh native loader")
            return _load_with_trimesh(path, max_faces)

        vertices = np.array(vertices, dtype=np.float64)
        faces = np.array(faces, dtype=np.int64)

        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        clean_mesh(mesh)
        _log(f"[*] Loaded {len(mesh.faces):,} faces from 3DFACE entities")
        return mesh

    except Exception as e:
        _log(f"[WARN] ezdxf parser failed: {e}")
        _log("[*] Falling back to trimesh native loader")
        return _load_with_trimesh(path, max_faces)


def _load_with_trimesh(path: Path, max_faces: int | None = None) -> trimesh.Trimesh:
    """
    Fallback loader using trimesh's native DXF importer.
    """
    try:
        mesh = trimesh.load(str(path), force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            # Combine all geometries into one mesh
            meshes = [
                g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)
            ]
            if not meshes:
                raise ValueError("No meshes found in scene")
            mesh = trimesh.util.concatenate(meshes)
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError(f"Loaded object is not a Trimesh: {type(mesh)}")
        clean_mesh(mesh)
        _log(f"[*] Loaded {len(mesh.faces):,} faces via trimesh native loader")
        return mesh
    except Exception as e:
        raise RuntimeError(f"Failed to load mesh: {e}") from e


# ============================================================
# NORMALIZATION
# ============================================================


def normalize_mesh(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    """
    Center the mesh at origin and scale it so the largest dimension ≈ 2.0
    (comfortable size for orthographic rendering).
    """
    _ = clean_mesh(mesh)  # in‑place modification; ignore return

    bounds = mesh.bounds
    center = (bounds[0] + bounds[1]) * 0.5
    extents = bounds[1] - bounds[0]
    max_dim = float(np.max(extents))  # type: ignore

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

    _log(f"[*] Normalized: centered + scaled by {scale:.4f}")
    _log(f"    Original size: {extents}")
    _log(f"    New size     : {mesh.extents}")

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
    _log(f"[*] Unique edges: {n:,}")

    if n > max_edges:
        _log(f"[*] Subsampling edges {n:,} → {max_edges:,}")
        idx = np.random.choice(n, size=max_edges, replace=False)
        segments = segments[idx]

    return segments


# ============================================================
# RENDERING
# ============================================================


def project_view(segments: np.ndarray, view: str) -> np.ndarray:
    """Project 3D edge segments into 2D according to the view."""
    view = view.lower()

    if view == "top":  # looking down -Z
        return segments[:, :, [0, 1]]
    elif view == "front":  # looking along +Y
        return segments[:, :, [0, 2]]
    elif view == "right":  # looking along +X
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
    out_dir: Path,
    image_size: int = 3200,
    line_width: float = LINE_WIDTH,
    compress_level: int = 6,
    suffix: str = "",
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
        0.02,
        0.98,
        view_name.upper(),
        transform=ax.transAxes,
        color="#8ab4f8",
        fontsize=14,
        fontfamily="monospace",
        verticalalignment="top",
        alpha=0.9,
    )

    fig.savefig(
        out_dir / f"{view_name}{suffix}.png",
        dpi=100,
        facecolor=BACKGROUND,
        bbox_inches=None,
        pad_inches=0,
        pil_kwargs={"compress_level": compress_level, "optimize": True},
    )
    plt.close(fig)


# ============================================================
# PIPELINE (shared by CLI and MCP server)
# ============================================================


@dataclass
class PipelineResult:
    """Outcome of one run_pipeline() call. Single source of truth for
    meta.json, `dxf-ortho --json`, and the MCP tool's return value."""

    input_file: Path
    output_dir: Path
    views: list[str]
    faces: int
    vertices: int
    edges_rendered: int
    image_size: int
    image_paths: dict[str, Path]
    normalization: dict[str, Any]
    elapsed_seconds: float
    dxf_out: Path | None = None
    dxf_outline: Path | None = None
    meta_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_file": str(self.input_file),
            "input_size_MB": self.input_file.stat().st_size / (1024 * 1024),
            "output_dir": str(self.output_dir),
            "faces": self.faces,
            "vertices": self.vertices,
            "edges_rendered": self.edges_rendered,
            "views": [v.upper() for v in self.views],
            "image_size": self.image_size,
            "image_paths": {k: str(v) for k, v in self.image_paths.items()},
            "normalization": self.normalization,
            "dxf_out": str(self.dxf_out) if self.dxf_out else None,
            "dxf_outline": str(self.dxf_outline) if self.dxf_outline else None,
            "meta_path": str(self.meta_path) if self.meta_path else None,
            "created_by": "dxf_orthographic_snapshots.py (improved)",
            "elapsed_seconds": self.elapsed_seconds,
        }


def run_pipeline(
    input_path: Path,
    *,
    out_dir: Path | None = None,
    size: int = DEFAULT_SIZE,
    max_edges: int = DEFAULT_MAX_EDGES,
    views: str = "top,front,right",
    max_faces: int | None = None,
    dxf_out: Path | None = None,
    dxf_max_mb: float | None = None,
    max_dxf_edges: int = 200_000,
    dxf_bytes_per_edge: int = 600,
    dxf_outline: Path | None = None,
    png_compress: int = 6,
    suffix: str | None = None,
) -> PipelineResult:
    """Run the full load -> normalize -> extract -> render (+ optional DXF
    export) pipeline and return a PipelineResult. Raises on failure (e.g.
    FileNotFoundError if input_path doesn't exist) rather than exiting."""
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    resolved_out_dir = out_dir or (input_path.parent / f"{input_path.stem}_ORTHO")
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    view_list = [v.strip().lower() for v in views.split(",") if v.strip()]

    t0 = time.time()

    # 1. Load
    mesh = load_dxf_as_mesh(input_path, max_faces=max_faces)

    # 2. Normalize
    mesh, norm_info = normalize_mesh(mesh)

    # 3. Extract edges
    full_segments = extract_edges(mesh, max_edges=max_edges)

    # 4. Render PNGs with auto-suffix, collect 2D data and define limits

    ## 4.1 Build auto-suffix
    suffix_parts = []
    if png_compress != 6:
        suffix_parts.append(f"c{png_compress}")
    if max_edges != DEFAULT_MAX_EDGES:
        suffix_parts.append(f"e{max_edges}")
    if size != DEFAULT_SIZE:
        suffix_parts.append(f"s{size}")

    ## 4.2 Apply suffix to view names
    auto_suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""
    resolved_suffix = suffix if suffix is not None else auto_suffix

    ## 4.3 Render views
    views_segments_2d = {}
    view_limits = {}
    image_paths: dict[str, Path] = {}
    _log(f"[*] Rendering {len(view_list)} view(s) at {size}px ...")
    for view in view_list:
        seg2d = project_view(full_segments, view)
        views_segments_2d[view] = seg2d

        # Compute axis limits (matching render_view)
        all_pts = seg2d.reshape(-1, 2)
        mins = all_pts.min(axis=0)
        maxs = all_pts.max(axis=0)
        span = maxs - mins
        span[span < 1e-9] = 1.0
        pad = span * PADDING
        xlim = (mins[0] - pad[0], maxs[0] + pad[0])
        ylim = (mins[1] - pad[1], maxs[1] + pad[1])
        view_limits[view] = (xlim, ylim)

        # Render the view
        render_view(
            seg2d,
            view,
            resolved_out_dir,
            image_size=size,
            compress_level=png_compress,
            suffix=resolved_suffix,
        )
        image_paths[view] = resolved_out_dir / f"{view}{resolved_suffix}.png"
        _log(f"    → {view}{resolved_suffix}.png")

    # 5. Optional DXF export
    if dxf_out:
        # Determine max edges for DXF
        if dxf_max_mb is not None:
            target_bytes = dxf_max_mb * 1024 * 1024
            resolved_max_dxf_edges = int(target_bytes / dxf_bytes_per_edge)
            _log(
                f"[*] Targeting ~{dxf_max_mb:.1f} MB DXF → {resolved_max_dxf_edges:,} edges (using {dxf_bytes_per_edge} bytes/edge)"
            )
        else:
            resolved_max_dxf_edges = max_dxf_edges

        total_edges = len(full_segments)
        if total_edges > resolved_max_dxf_edges:
            _log(
                f"[*] Subsampling {total_edges:,} edges → {resolved_max_dxf_edges:,} for DXF export"
            )
            rng = np.random.default_rng(42)
            idx = rng.choice(total_edges, size=resolved_max_dxf_edges, replace=False)
            reduced_segments = full_segments[idx]
        else:
            reduced_segments = full_segments

        # Project all views for DXF using the (possibly reduced) segments
        from dxf_agent.export.ortho_dxf import export_ortho_views_to_dxf

        dxf_views = {view: project_view(reduced_segments, view) for view in view_list}
        export_ortho_views_to_dxf(dxf_views, dxf_out)

    # 6. Optional silhouette DXF
    if dxf_outline:
        from dxf_agent.export.ortho_dxf import (
            export_outline_dxf,
            extract_contour_from_png,
        )

        # Compute layout offsets (reuse same logic as wireframe export)
        bboxes = {}
        for vname, segs in views_segments_2d.items():
            pts = segs.reshape(-1, 2)
            bboxes[vname] = (pts.min(axis=0), pts.max(axis=0))

        def offset_bbox(bb_min, bb_max):
            return bb_max - bb_min

        top_size = offset_bbox(*bboxes["top"])
        front_size = offset_bbox(*bboxes["front"])
        right_size = offset_bbox(*bboxes["right"])
        spacing = 3.0
        top_offset = (0.0, 0.0)
        front_offset = (top_size[0] + spacing, 0.0)
        right_offset = (0.0, top_size[1] + spacing)
        view_offsets = {
            "top": top_offset,
            "front": front_offset,
            "right": right_offset,
        }
        # Extract contours from the PNGs we just saved
        contours = {}
        for view in view_list:
            png_file = resolved_out_dir / f"{view}{resolved_suffix}.png"
            contours[view] = extract_contour_from_png(png_file)

        export_outline_dxf(
            contours, view_limits, size, view_offsets, dxf_outline
        )

    elapsed = round(time.time() - t0, 2)

    result = PipelineResult(
        input_file=input_path,
        output_dir=resolved_out_dir,
        views=view_list,
        faces=len(mesh.faces),
        vertices=len(mesh.vertices),
        edges_rendered=len(full_segments),
        image_size=size,
        image_paths=image_paths,
        normalization=norm_info,
        elapsed_seconds=elapsed,
        dxf_out=dxf_out,
        dxf_outline=dxf_outline,
    )

    # 7. Metadata (written to disk for backward compatibility)
    meta_path = resolved_out_dir / "meta.json"
    meta_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    result.meta_path = meta_path

    return result


# ============================================================
# MAIN
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Improved orthographic DXF renderer (centered + normalized)"
    )
    parser.add_argument("input", type=Path, help="Input DXF file")
    parser.add_argument("--out", type=Path, default=None, help="Output folder")
    parser.add_argument(
        "--size", type=int, default=DEFAULT_SIZE, help="Image size in pixels"
    )
    parser.add_argument("--max-edges", type=int, default=DEFAULT_MAX_EDGES)
    parser.add_argument(
        "--views",
        type=str,
        default="top,front,right",
        help="Comma-separated views: top,front,right,iso",
    )
    parser.add_argument(
        "--max-faces",
        type=int,
        default=None,
        help="Limit number of faces loaded to save memory",
    )
    parser.add_argument(
        "--dxf-out",
        type=Path,
        default=None,
        help="Export ortho views to a single DXF file",
    )
    parser.add_argument(
        "--dxf-max-mb",
        type=float,
        default=None,
        help="Target DXF file size in MB (overrides --max-dxf-edges)",
    )
    parser.add_argument(
        "--max-dxf-edges",
        type=int,
        default=200_000,
        help="Max edges in DXF export (ignored if --dxf-max-mb is set)",
    )
    parser.add_argument(
        "--dxf-bytes-per-edge",
        type=int,
        default=600,
        help="Calibration: average bytes per edge in DXF (used with --dxf-max-mb)",
    )
    parser.add_argument(
        "--dxf-outline",
        type=Path,
        default=None,
        help="Export clean outlines (closed polylines) to DXF",
    )
    parser.add_argument("--version", action="version", version="dxf-ortho 0.1.0")
    parser.add_argument(
        "--png-compress",
        type=int,
        default=6,
        choices=range(10),
        help="PNG compression level (0-9, default 6)",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default=None,
        help="Custom suffix for output PNG files (overrides auto-suffix)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON result object to stdout instead of a human-readable summary",
    )
    args = parser.parse_args()

    try:
        result = run_pipeline(
            args.input,
            out_dir=args.out,
            size=args.size,
            max_edges=args.max_edges,
            views=args.views,
            max_faces=args.max_faces,
            dxf_out=args.dxf_out,
            dxf_max_mb=args.dxf_max_mb,
            max_dxf_edges=args.max_dxf_edges,
            dxf_bytes_per_edge=args.dxf_bytes_per_edge,
            dxf_outline=args.dxf_outline,
            png_compress=args.png_compress,
            suffix=args.suffix,
        )
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "error": str(e), "type": type(e).__name__}))
        else:
            print(f"[ERROR] {e}")
        sys.exit(1)

    if args.json:
        print(json.dumps({"status": "ok", **result.to_dict()}))
        return

    print()
    print("=" * 60)
    print("DONE")
    print(f"  Output folder : {result.output_dir}")
    print(f"  Faces         : {result.faces:,}")
    print(f"  Edges drawn   : {result.edges_rendered:,}")
    print(f"  Time          : {result.elapsed_seconds:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
