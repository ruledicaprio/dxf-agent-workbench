<div align="center">

# DXF Agent Workbench
### Advanced Orthographic Renderer for Large 3D DXF Meshes

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Performance](https://img.shields.io/badge/Performance-Tested_2M%2B_Faces-orange.svg)
![Status](https://img.shields.io/badge/Status-Production_Ready-success.svg)

</div>

---

## Summary

The **DXF Agent Workbench** is a high-performance, robust orthographic rendering solution specifically engineered for large 3D DXF meshes. Designed primarily for engineering drawings and high-poly Computer-Aided Design (CAD) models, this application ensures rapid processing and precise visual output without compromising geometric integrity.

![Orthographic views](https://raw.githubusercontent.com/ruledicaprio/dxf-agent-workbench/main/examples/orthographic-views.jpg)

---

## Core Capabilities

* **Massive Scale Processing:** Capable of processing and rendering meshes containing millions of faces (empirically tested with over 2,000,000 faces).
* **Intelligent Scaling:** Features automatic centering and dynamic scaling to ensure optimal framing of all geometries.
* **Standardized Projections:** Generates clean, precise TOP, FRONT, and RIGHT orthographic views, with optional isometric projections available.
* **High-Resolution Output:** Exports high-fidelity PNG images at arbitrary resolutions (defaulting to an ultra-crisp 3200 px).
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

## Installation Guide

To configure the workbench within your local environment, please execute the following commands:

```bash
# Clone the repository
git clone https://github.com/ruledicaprio/dxf-agent-workbench.git

# Navigate to the project directory
cd dxf-agent-workbench

# (Recommended) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install the required dependencies
pip install numpy matplotlib trimesh ezdxf opencv-python
```

---

## Operational Usage

*(Please adjust the following command to reflect your application's primary entry point)*

```bash
python renderer.py --input path/to/model.dxf --output path/to/output.png --view TOP --resolution 3200
```

---

## Licensing

This project is distributed under standard open-source licensing. Please refer to the [LICENSE](LICENSE) file for comprehensive details regarding usage, modification, and distribution rights.

---

<div align="center">

**Engineered with precision for the CAD and engineering community.**

</div>