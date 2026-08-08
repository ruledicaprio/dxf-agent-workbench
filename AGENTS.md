## Local Runtime
- Agent Brain: Gemma 12B Q3_K_M running via llama.cpp + Vulkan on Iris GPU.
- Server endpoint: `http://127.0.0.1:8080`
- Client module: `src/dxf_agent/agent/local_brain.py`
- Worktrees share the same brain instance.
