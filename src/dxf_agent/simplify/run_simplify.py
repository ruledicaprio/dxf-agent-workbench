# test_simplify.py
from pathlib import Path
from dxf_agent.simplify.three_stage import simplify_to_dxf

input_path = Path("C:/Users/Rusmir/Projects/dxf-agent-workbench/corpus/P22-6_FG_Wilson_BLOK.dxf")  # small one
output_path = Path("artifacts/test_simplified.dxf")
simplify_to_dxf(input_path, target_faces=5000, output_path=output_path)
print(f"Done, output size: {output_path.stat().st_size / 1024:.1f} KB")
