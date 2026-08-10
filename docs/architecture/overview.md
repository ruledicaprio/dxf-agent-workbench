# Architecture Overview

## Layers

1. **Ingest** – DXF/DWG → raw geometry (3DFACE, lines, etc.)  
2. **Geometry** – canonical model (trimesh, bounds, transforms)  
3. **Render** – orthographic / isometric projections → PNG/SVG  
4. **Simplify** – mesh simplification (three-stage, hybrid, stream)  
5. **Agent** – tools for Claude: inspect, snapshot, query  

## Coordinate System

- All coordinates are in **millimetres** (source DXF units).  
- Normalisation (scale~2.0) is for rendering only; it does **not** change the metric model.  
- Orthographic projections drop one axis: top (drop Z), front (drop Y), right (drop X).

## Rendering Pipeline

load_dxf_as_mesh() → normalize_mesh() → extract_edges() → project_view() → render_view()

- Edges are **unique topological edges**, not per-face edges.  
- Subsampling is random but seed-fixed for reproducibility.

## Data Separation

| Class | Location | Git? |
|-------|----------|------|
| Source code | `src/` | ✔ |
| Tests | `tests/` | ✔ |
| Docs | `docs/` | ✔ |
| Small fixtures | `tests/fixtures/` | ✔ (small) |
| Large engineering data | `corpus/`, `.data/` | ❌ (ignored) |
| Generated artifacts | `artifacts/`, `benchmark_results/` | ❌ (ignored) |
