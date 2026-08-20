"""Regression tests for 3DFACE -> triangle conversion in load_dxf_as_mesh()."""

import sys
from pathlib import Path

import ezdxf
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from dxf_agent.export.orthographic import load_dxf_as_mesh  # noqa: E402

TRI = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
QUAD = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]


def _write(tmp_path, faces):
    doc = ezdxf.new("R2000")
    msp = doc.modelspace()
    for corners in faces:
        msp.add_3dface(corners)
    path = tmp_path / "fixture.dxf"
    doc.saveas(path)
    return path


def _areas(mesh):
    return np.asarray(mesh.area_faces)


def test_triangular_3dface_emits_one_triangle(tmp_path):
    """A triangular 3DFACE repeats its last corner; it describes one triangle.

    ezdxf stores add_3dface([a, b, c]) with vtx3 == vtx2, which is the DXF R12
    convention. Splitting it as a quad yields (0,1,2) plus a zero-area (0,2,3).
    """
    mesh = load_dxf_as_mesh(_write(tmp_path, [TRI]))
    assert len(mesh.faces) == 1
    assert _areas(mesh)[0] == pytest.approx(0.5)


def test_quad_3dface_still_emits_two_triangles(tmp_path):
    mesh = load_dxf_as_mesh(_write(tmp_path, [QUAD]))
    assert len(mesh.faces) == 2
    assert _areas(mesh).sum() == pytest.approx(1.0)


def test_no_degenerate_faces_in_a_triangular_corpus(tmp_path):
    """The defect at scale: half of every triangular model was zero-area."""
    mesh = load_dxf_as_mesh(_write(tmp_path, [TRI] * 50))
    degenerate = int((_areas(mesh) == 0).sum())
    assert degenerate == 0, f"{degenerate} of {len(mesh.faces)} faces have zero area"
    assert len(mesh.faces) == 50


def test_fourth_corner_repeating_the_first_is_also_a_triangle(tmp_path):
    """Some writers close the loop with vtx3 == vtx0 rather than vtx3 == vtx2."""
    path = tmp_path / "vtx0.dxf"
    doc = ezdxf.new("R2000")
    doc.modelspace().add_3dface([TRI[0], TRI[1], TRI[2], TRI[0]])
    doc.saveas(path)
    mesh = load_dxf_as_mesh(path)
    assert len(mesh.faces) == 1
