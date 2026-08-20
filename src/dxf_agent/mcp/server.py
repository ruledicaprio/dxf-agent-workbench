"""MCP server exposing DXF orthographic rendering as agent-callable tools.

Shares run_pipeline() with the `dxf-ortho` CLI (src/dxf_agent/export/orthographic.py)
so both surfaces stay behaviorally identical. stdio transport only.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from dxf_agent.export.orthographic import run_pipeline

mcp = FastMCP("dxf-agent-workbench")


@mcp.tool()
def render_orthographic_views(
    dxf_path: str,
    out_dir: str | None = None,
    size: int = 3200,
    views: str = "top,front,right",
    max_edges: int = 8_000_000,
    max_faces: int | None = None,
) -> dict:
    """Render top/front/right (or iso) orthographic PNG snapshots of a DXF file.

    Returns a JSON-serializable summary: output directory, per-view image
    paths, face/vertex/edge counts, and normalization info.
    """
    try:
        result = run_pipeline(
            Path(dxf_path),
            out_dir=Path(out_dir) if out_dir else None,
            size=size,
            views=views,
            max_edges=max_edges,
            max_faces=max_faces,
        )
    except Exception as e:
        raise RuntimeError(f"render_orthographic_views failed: {e}") from e

    return {"status": "ok", **result.to_dict()}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
