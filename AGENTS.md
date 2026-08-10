# Agent Operational Rules

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
