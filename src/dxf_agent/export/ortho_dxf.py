"""Export projected orthographic edges to a single DXF file."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import ezdxf
import cv2  # <-- added


def export_ortho_views_to_dxf(
    views_segments: dict[str, np.ndarray],  # key: view name, value: (N,2,2) float
    out_path: Path,
    spacing: float = 3.0,
) -> None:
    """Write three orthographic 2D edge sets to a DXF, side-by-side."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    bboxes = {}
    for vname, segs in views_segments.items():
        pts = segs.reshape(-1, 2)
        bboxes[vname] = (pts.min(axis=0), pts.max(axis=0))

    def offset_bbox(bb_min, bb_max):
        return bb_max - bb_min

    top_size = offset_bbox(*bboxes['top'])
    front_size = offset_bbox(*bboxes['front'])
    right_size = offset_bbox(*bboxes['right'])

    top_offset = np.zeros(2)
    front_offset = np.array([top_size[0] + spacing, 0.0])
    right_offset = np.array([0.0, top_size[1] + spacing])

    top_min = bboxes['top'][0]
    front_min = bboxes['front'][0]
    right_min = bboxes['right'][0]

    def write_lines(segments, offset, view_min, layer_name, color_index=7):
        layer = doc.layers.add(name=layer_name)
        layer.color = color_index
        for seg in segments:
            start = seg[0] - view_min + offset
            end = seg[1] - view_min + offset
            msp.add_line(start, end, dxfattribs={"layer": layer_name})

    write_lines(views_segments['top'], top_offset, top_min, "TOP")
    write_lines(views_segments['front'], front_offset, front_min, "FRONT")
    write_lines(views_segments['right'], right_offset, right_min, "RIGHT")

    label_height = 0.5
    label_offset = 1.0
    for vname, off, bb_min in [
        ("TOP", top_offset, top_min),
        ("FRONT", front_offset, front_min),
        ("RIGHT", right_offset, right_min),
    ]:
        text = msp.add_text(
            vname,
            dxfattribs={"layer": "LABELS", "height": label_height},
        )
        text.dxf.insert = (off[0], off[1] - label_offset)

    doc.saveas(str(out_path))
    print(f"[*] DXF exported: {out_path}")


def extract_contour_from_png(png_path: Path, epsilon_factor: float = 0.001) -> np.ndarray:
    """Extract the largest outer contour from a rendered ortho PNG.
    Returns (N,2) pixel‑coordinates of the simplified contour.
    """
    img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read {png_path}")

    _, thresh = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No contour found in image")

    largest = max(contours, key=cv2.contourArea)
    epsilon = epsilon_factor * cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, epsilon, True)
    return approx[:, 0, :].astype(np.float64)   # (N,2)


def export_outline_dxf(
    view_contours: dict[str, np.ndarray],
    view_limits: dict[str, tuple[tuple[float, float], tuple[float, float]]],
    img_size: int,
    view_offsets: dict[str, tuple[float, float]],
    out_path: Path,
) -> None:
    """Write a DXF with one closed LWPOLYLINE per view."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    for view, contour_px in view_contours.items():
        (xmin, xmax), (ymin, ymax) = view_limits[view]
        x_model = xmin + (contour_px[:, 0] / (img_size - 1)) * (xmax - xmin)
        y_model = ymin + ((img_size - 1 - contour_px[:, 1]) / (img_size - 1)) * (ymax - ymin)
        pts_model = np.column_stack((x_model, y_model))

        offset = view_offsets[view]
        pts_model[:, 0] += offset[0]
        pts_model[:, 1] += offset[1]

        pts_closed = np.vstack([pts_model, pts_model[0]])
        msp.add_lwpolyline(pts_closed, dxfattribs={"layer": f"{view.upper()}_OUTLINE"})

    label_height = 0.5
    label_offset = 1.0
    for v, off in view_offsets.items():
        text = msp.add_text(v.upper(), dxfattribs={"layer": "LABELS", "height": label_height})
        text.dxf.insert = (off[0], off[1] - label_offset)

    doc.saveas(str(out_path))
    print(f"[*] Outline DXF exported: {out_path}")
