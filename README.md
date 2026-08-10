---
name: dxf-agent-workbench
version: 0.1.0
description: Orthographic renderer for large DXF meshes
entry_point: dxf_agent.export.orthographic:main
language: python
dependencies: numpy, matplotlib, trimesh, ezdxf, opencv-python
---

# DXF Agent Workbench – Orthographic Renderer

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/v/release/ruledicaprio/dxf-agent-workbench)](https://github.com/ruledicaprio/dxf-agent-workbench/releases)

## 🤖 For AI Agents

This repository is **agent‑friendly**. See:
- [AGENTS.md](AGENTS.md) for operational rules.
- [CLAUDE.md](CLAUDE.md) for architectural decisions.
- [llms.txt](llms.txt) for a concise index.
- [llms-full.txt](llms-full.txt) for a comprehensive context dump.

**Fast, robust orthographic rendering of large 3D DXF meshes** – built for engineering drawings, and high‑poly CAD models.

- ✅ Handles **millions of faces** (tested with 2M+)
- ✅ Automatic centering & scaling
- ✅ Clean TOP / FRONT / RIGHT views (plus isometric optional)
- ✅ PNG output at any resolution (default 3200 px)
- ✅ Optional DXF wireframe and outline exports

---

## Quickstart

```bash
# Install from GitHub
pip install git+https://github.com/ruledicaprio/dxf-agent-workbench.git

# Render all three views (PNG only)
dxf-ortho model.dxf --size 3200 --out ./preview

# Also export a DXF wireframe layout
dxf-ortho model.dxf --dxf-out layout.dxf

# Export simplified outlines (closed polylines)
dxf-ortho model.dxf --dxf-outline outlines.dxf
```
---

## Pipeline

```mermaid
graph LR
    A[DXF File] --> B[Load with ezdxf / trimesh]
    B --> C[Normalize: center + scale]
    C --> D[Extract unique edges]
    D --> E[Project to TOP/FRONT/RIGHT]
    E --> F[Render PNGs]
    E --> G[Export DXF wireframe]
    E --> H[Export outline polylines]
    F & G & H --> I[Output folder]
```

---

## Options

| Argument | Description |
|----------|-------------|
| input | Path to the DXF file |
| --out | Output folder (default: <input>_ORTHO) |
| --size | Image size in pixels (default: 3200) |
| --views | Comma‑separated list: top,front,right,iso (default: all except iso) |
| --max-edges | Cap the number of rendered edges (default: 8,000,000) |
| --max-faces | Limit loaded faces for memory (e.g., --max-faces 1000000) |
| --dxf-out | Save a DXF with all projected views side‑by‑side |
| --dxf-outline | Save a DXF with simplified outer contours (closed polylines) |
| --dxf-max-mb | Target DXF file size (overrides edge count) |

---

## Project Structure

```
dxf-agent-workbench/
├── src/dxf_agent/export/
│   ├── orthographic.py   # main CLI
│   └── ortho_dxf.py      # DXF export helpers
├── corpus/               # example DXF files
├── docs/                 # architecture & research
└── tests/                # unit / integration tests
```

---

## Contributing

Please read AGENTS.md and CLAUDE.md for operational rules.

Keep commits small and conventional (feat:, fix:, docs:).

Run pytest before committing.

Never commit large binaries – use .data/ or .gitignore.

---

##  License

MIT © 2026 Rusmir Skopljak
