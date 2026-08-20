# Agent Operational Rules

## Agent Quick Start

1. Install: `pip install -e .`
2. Entry point: `dxf_agent.export.orthographic:main`
3. Run a test: `dxf-ortho --help`
4. Core modules: `export/orthographic.py` (CLI), `export/ortho_dxf.py` (DXF helpers)

## MCP Server (for Claude / agent tool-calling)

Instead of shelling out to `dxf-ortho`, agents can call this repo as an MCP
server:

1. Install with the mcp extra: `pip install -e ".[mcp]"`
2. Launch: `dxf-ortho-mcp` (stdio transport)
3. Register in your MCP client config, e.g. Claude Code / Claude Desktop:
   ```json
   { "mcpServers": { "dxf-agent-workbench": { "command": "dxf-ortho-mcp" } } }
   ```
4. Tools exposed:
   - `render_orthographic_views(dxf_path, out_dir=None, size=3200, views="top,front,right", max_edges=8000000, max_faces=None)` → JSON summary + PNG paths.

The MCP tool and the `dxf-ortho --json` CLI flag both call `run_pipeline()` in
`src/dxf_agent/export/orthographic.py` — keep them in sync; do not duplicate
pipeline logic in the MCP server.

`src/dxf_agent/agent/local_brain.py` and `scripts/agent_ask.py` are an
unrelated, disconnected experiment (a local-LLM chat client) — not part of
the MCP/CLI agent surface described above.

## Structured CLI output

Run `dxf-ortho input.dxf --json` for a single JSON object on stdout
(status/paths/counts/timings) instead of human-readable logs. Progress logs
always go to stderr, so stdout is safe to parse in both modes.

## When modifying geometry code

1. Read docs/architecture/overview.md and docs/architecture/coordinate-system.md (create if missing).  
2. Identify the coordinate system you are working in.  
3. If changing a transformation, ensure deterministic behaviour.  
4. Run benchmark after change (python scripts/benchmark_corpus.py).  
5. Compare benchmark JSON and generated images with baseline.

## When adding a new algorithm

- Place it in the appropriate src/dxf_agent/<module>/ folder.  
- Provide a minimal CLI entrypoint in scripts/ that exercises the algorithm.  
- Do **not** delete or refactor existing working algorithms until a new one has been benchmarked and approved.

## Commits

- Keep commits small and focused.  
- Use conventional commit prefixes: eat:, ix:, chore:, docs:, perf:, 	est:.  
- Never commit large binary files (DXF, PNG, SVG) to Git; use .gitignore.
