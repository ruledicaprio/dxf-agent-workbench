# AGENTS RUNBOOK

## Local Runtime

- Agent Brain: Gemma 12B Q3_K_M running via llama.cpp + Vulkan on Iris GPU.
- Server endpoint: `http://127.0.0.1:8080`
- Client module: `src/dxf_agent/agent/local_brain.py`
- Worktrees share the same brain instance.

## 🛡️ Code Hygiene & Autonomy

When editing Python files, you are **encouraged** to make these safe, mechanical improvements without asking:

- Convert lists to tuples where a tuple is required (e.g., `add_axes((0,0,1,1))` instead of `[0,0,1,1]`).
- Wrap `ndarray` segments with `list()` when passing to `LineCollection` or similar type‑sensitive functions.
- Fix obvious import order (standard library → third‑party → local).
- Remove unused imports.
- Replace deprecated aliases (e.g., `np.float` → `float`).

If a change is purely syntactic and does not alter behaviour, apply it directly and mention it in a brief note.

**Only stop and ask** if:
- The logic would change.
- A library API would change.
- You are unsure about a dependency.
