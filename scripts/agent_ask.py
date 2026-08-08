from dxf_agent.agent.local_brain import LocalAgent
import sys

if __name__ == "__main__":
    agent = LocalAgent()
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Summarize the architecture of this project."
    print(agent.ask(query))
