import json
from pathlib import Path

import requests


class LocalAgent:
    def __init__(self, base_url="http://127.0.0.1:8080"):
        self.base_url = base_url
        # Load the project constitution so the local AI knows the rules.
        self.system_prompt = self._load_constitution()

    def _load_constitution(self):
        # Read the CLAUDE.md for project architecture.
        path = Path(__file__).parents[3] / "CLAUDE.md"
        if path.exists():
            return f"You are an AI engineering agent. Follow these rules strictly:\n{path.read_text()}"
        return "You are a DXF engineering assistant."

    def ask(self, user_prompt, context=""):
        payload = {
            "prompt": f"{self.system_prompt}\n\nContext:\n{context}\n\nTask:\n{user_prompt}",
            "n_predict": 2048,
            "temperature": 0.2,  # Low temperature for deterministic DXF work
            "stop": ["</s>", "Task:"]
        }
        response = requests.post(f"{self.base_url}/completion", json=payload)
        return response.json()["content"]
