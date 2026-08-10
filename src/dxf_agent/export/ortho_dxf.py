"""Export projected orthographic edges to a single DXF file."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import ezdxf

def export_ortho_views_to_dxf(
    views_segments: dict[str, np.ndarray],  # key: view name, value: (N,2,2) float
    out_path: Path,
    spacing: float = 3.0,                  # spacing between views in model units
) -> None:
    """Write three orthographic 2D edge sets to a DXF, side-by-side.

    views_segments: {'top': ..., 'front': ..., 'right': ...}
    """
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # Pre-calculate offsets so views don't overlap
    # Determine bounding boxes of each view
    bboxes = {}
    for vname, segs in views_segments.items():
        pts = segs.reshape(-1, 2)
        bboxes[vname] = (pts.min(axis=0), pts.max(axis=0))

    # Layout: Top at origin, Front to the right, Right below Top
    # We'll offset each view so that its lower-left corner sits at the origin
    # after accounting for spacing.

    def offset_bbox(bb_min, bb_max):
        return bb_max - bb_min

    top_size = offset_bbox(*bboxes['top'])
    front_size = offset_bbox(*bboxes['front'])
    right_size = offset_bbox(*bboxes['right'])

    # Offsets (lower-left corner) for each view
    top_offset = np.zeros(2)
    front_offset = np.array([top_size[0] + spacing, 0.0])
    right_offset = np.array([0.0, top_size[1] + spacing])

    # Also shift by the min of each view so they start at the offset
    top_min = bboxes['top'][0]
    front_min = bboxes['front'][0]
    right_min = bboxes['right'][0]

    def write_lines(segments, offset, view_min, layer_name, color_index=7):
        layer = doc.layers.add(name=layer_name)
        layer.color = color_index  # white/black by default
        for seg in segments:
            start = seg[0] - view_min + offset
            end = seg[1] - view_min + offset
            msp.add_line(start, end, dxfattribs={"layer": layer_name})

    write_lines(views_segments['top'], top_offset, top_min, "TOP")
    write_lines(views_segments['front'], front_offset, front_min, "FRONT")
    write_lines(views_segments['right'], right_offset, right_min, "RIGHT")

    # Add view labels
    label_height = 0.5
    label_offset = 0.8          # <-- increase from 0.3 to 0.8
    for vname, off, bb_min in [
        ("TOP", top_offset, top_min),
        ("FRONT", front_offset, front_min),
        ("RIGHT", right_offset, right_min),
    ]:
        text = msp.add_text(
            vname,
            dxfattribs={
                "layer": "LABELS",
                "height": label_height,
            },
        )
        text.dxf.insert = (off[0], off[1] - label_offset)

    doc.saveas(str(out_path))
    print(f"[*] DXF exported: {out_path}")
