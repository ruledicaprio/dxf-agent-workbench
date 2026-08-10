<div align="center">

# DXF Agent Workbench
### Agentic Orthographic Renderer for complex 3D DXF Meshes

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Performance](https://img.shields.io/badge/Performance-Tested_2M%2B_Faces-orange.svg)
![Status](https://img.shields.io/badge/Status-Production_Ready-success.svg)



**Fast, agentic_friendly, robust orthographic rendering of large 3D DXF meshes** – built for engineering drawings, and high‑poly CAD models.

- ✅ Handles **millions of faces** (tested with 2M+)
- ✅ Automatic centering & scaling
- ✅ Clean TOP / FRONT / RIGHT views (plus isometric optional)
- ✅ PNG output at any resolution (default 3200 px)
- ✅ Optional DXF wireframe and outline exports
</div>

---

## Summary

The **DXF Agent Workbench** is an agentic-oriented, high-performance, robust orthographic rendering solution specifically engineered for large 3D DXF meshes. Designed primarily for engineering drawings and high-poly Computer-Aided Design (CAD) models, this application ensures rapid processing and precise visual output without compromising geometric integrity.

![Orthographic views](https://raw.githubusercontent.com/ruledicaprio/dxf-agent-workbench/main/examples/orthographic-views.jpg)

---

## Core Capabilities

* **Massive Scale Processing:** Capable of processing and rendering meshes containing millions of faces (empirically tested with over 2,000,000 faces).
* **Intelligent Scaling:** Features automatic centering and dynamic scaling to ensure optimal framing of all geometries.
* **Standardized Projections:** Generates clean, precise TOP, FRONT, and RIGHT orthographic views, with optional isometric projections available.
* **Built-in compression:** Exports compressed PNG images at arbitrary resolutions lvls 0-9 (default=6).
* **Extended DXF Exports:** Provides the option to export simplified wireframe layouts or outline polylines into a newly generated DXF file.
* **Extended DXF Exports:** Provides the option to export simplified wireframe layouts or outline polylines into a newly generated DXF file.

---

## Architecture and Dependencies

This workbench is developed in **Python** and leverages highly optimized libraries for geometric processing and rendering:

| Dependency | Function |
| :--- | :--- |
| **`ezdxf`** | Core parsing and generation of DXF files. |
| **`trimesh`** | 3D mesh loading, manipulation, and analysis. |
| **`numpy`** | High-performance numerical array computations. |
| **`matplotlib`** | Primary orthographic rendering and visualization engine. |
| **`opencv-python`** | Advanced image processing and post-rendering optimizations. |

---

## Quickstart with dxf-ortho

To configure the dxf-agent-benchwork within your local environment, please execute the following commands:

### Fetch and install dxf-ortho cli
```bash
## navigate and clone repo

git clone https://github.com/ruledicaprio/dxf-agent-workbench.git
cd dxf-agent-workbench

# create virtual environment (recommended) and install cli

python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```
### install dependencies
```bash
pip install numpy matplotlib trimesh ezdxf opencv-python
pip install -e .

```
### operational usage (see available flags)
```bash
dxf-ortho examples/FG_Wilson_P_22-6-model.dxf --size 3200 --out examples/ --png-compress 9
```



---

## Gallery

<p align="center">
  <img src="examples/top.png" width="600" alt="TOP view">
  <br><em>TOP view</em>
</p>
<p align="center">
  <img src="examples/front.png" width="600" alt="FRONT view">
  <br><em>FRONT view</em>
</p>
<p align="center">
  <img src="examples/right.png" width="600" alt="RIGHT view">
  <br><em>RIGHT view</em>
</p>

---

## Licensing

This project is distributed under standard open-source licensing. Please refer to the [LICENSE](LICENSE) file for comprehensive details regarding usage, modification, and distribution rights.

---

<div align="center">

**Engineered with precision for the CAD and engineering community.**

</div>
