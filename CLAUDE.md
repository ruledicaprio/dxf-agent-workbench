# DXF Agent Workbench – Project Memory

## For AI Agents
- Start with [AGENTS.md](AGENTS.md) for operational rules.
- See [CLAUDE.md](CLAUDE.md) for architecture decisions.
- Entry point: `dxf_agent.export.orthographic:main`.

## Core Constraints
- Never modify source engineering files (DXF/DWG).
- Rendering must be a pure function of geometry.
- All coordinate systems must remain in engineering units (mm/in).
- Do not discard DXF entities silently; log unknowns.
- Large assets (>1 MB) belong in `.data/`, not Git.
claud
## Before Coding
- Check `git status` and current branch.
- Read relevant docs in `docs/architecture/`.
- Identify tests affected.
- Explain intended changes before making them.

## After Coding
- Run existing tests: `pytest tests/`
- If modifying geometry, run the benchmark corpus.
- Commit small, logical changes with descriptive messages.

## Project Structure
See `docs/architecture/overview.md` for rationale.
