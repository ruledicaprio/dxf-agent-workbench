#!/usr/bin/env python3
"""
Hybrid DXF 3DFACE compressor → target ~3-10 MB
Usage: python dxf_hybrid_simplify.py input.dxf [target_faces]
"""

import os
import sys
import time
import numpy as np

try:
    import trimesh
except ImportError:
    print("[ERROR] pip install trimesh numpy")
    sys.exit(1)

# Optional: much better quality / speed on large meshes
try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    print("[INFO] open3d not found – falling back to trimesh (still OK)")

def stream_dxf_to_obj(input_path: str, obj_path: str) -> int:
    """Low-RAM extraction of every 3DFACE → temporary OBJ"""
    face_count = 0
    v_idx = 1

    with open(input_path, "r", encoding="utf-8", errors="ignore") as fin, \
         open(obj_path, "w", encoding="utf-8") as fout:

        it = iter(fin)
        in_face = False
        coords = {}

        while True:
            try:
                code = next(it).strip()
                val  = next(it).strip()
            except StopIteration:
                if in_face and coords:
                    # last face
                    for i in range(4):
                        x = coords.get(f"1{i}", "0")
                        y = coords.get(f"2{i}", "0")
                        z = coords.get(f"3{i}", "0")
                        fout.write(f"v {x} {y} {z}\n")
                    fout.write(f"f {v_idx} {v_idx+1} {v_idx+2} {v_idx+3}\n")
                    face_count += 1
                break

            if code == "0":
                if in_face:
                    for i in range(4):
                        x = coords.get(f"1{i}", "0")
                        y = coords.get(f"2{i}", "0")
                        z = coords.get(f"3{i}", "0")
                        fout.write(f"v {x} {y} {z}\n")
                    fout.write(f"f {v_idx} {v_idx+1} {v_idx+2} {v_idx+3}\n")
                    v_idx += 4
                    face_count += 1
                    coords.clear()
                    in_face = False

                if val == "3DFACE":
                    in_face = True
                    continue

            if in_face and code in {"10","20","30","11","21","31","12","22","32","13","23","33"}:
                coords[code] = val

    return face_count

def simplify_mesh(mesh: trimesh.Trimesh, target_faces: int) -> trimesh.Trimesh:
    import pyfqmr
    import time

    print(f"[*] Original faces: {len(mesh.faces):,}")

    # Stronger cleaning for Meshy meshes
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.process(validate=True)
    print(f"[*] After cleaning: {len(mesh.faces):,} faces")

    if len(mesh.faces) <= target_faces:
        return mesh

    # --- Stage 1: Very aggressive first pass (trimesh) ---
    print("[*] Stage 1: Aggressive reduction...")
    mesh = mesh.simplify_quadric_decimation(
        face_count=min(120_000, len(mesh.faces) // 4),
        aggression=9
    )
    print(f"[*] After Stage 1: {len(mesh.faces):,} faces")

    if len(mesh.faces) <= target_faces:
        return mesh

    # --- Stage 2: pyfqmr with more aggressive settings ---
    print(f"[*] Stage 2: pyfqmr (aggressiveness=8, no border preservation)...")

    simplifier = pyfqmr.Simplify()
    simplifier.setMesh(mesh.vertices, mesh.faces)

    t0 = time.time()
    simplifier.simplify_mesh(
        target_count=target_faces,
        aggressiveness=8,          # more aggressive
        preserve_border=False,     # important for Meshy meshes
        verbose=True
    )
    print(f"[*] Stage 2 done in {time.time()-t0:.1f}s")

    vertices, faces, _ = simplifier.getMesh()
    result = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    print(f"[INFO] Final faces: {len(result.faces):,}")
    return result

def write_optimized_dxf(mesh: trimesh.Trimesh, output_path: str, use_block: bool = True):
    """Write clean R12 DXF with 3DFACE + optional BLOCK"""
    header = (
        "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1009\n  0\nENDSEC\n"
    )
    if use_block:
        header += (
            "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  8\n0\n  2\nGENERATOR_MESH\n"
            " 70\n     0\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
        )

    footer_start = "  0\nENDBLK\n  0\nENDSEC\n  0\nSECTION\n  2\nENTITIES\n" if use_block else \
                   "  0\nSECTION\n  2\nENTITIES\n"
    insert = "  0\nINSERT\n  8\n0\n  2\nGENERATOR_MESH\n 10\n0.0\n 20\n0.0\n 30\n0.0\n" if use_block else ""
    footer = "  0\nENDSEC\n  0\nEOF\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)

        # Write faces (triangles → 3DFACE with repeated 4th vertex)
        for face in mesh.faces:
            f.write("  0\n3DFACE\n  8\n0\n")
            for i in range(4):
                idx = face[i] if i < 3 else face[2]
                v = mesh.vertices[idx]
                # 1 decimal place is usually enough and saves a lot of space
                f.write(f" 1{i}\n{v[0]:.1f}\n")
                f.write(f" 2{i}\n{v[1]:.1f}\n")
                f.write(f" 3{i}\n{v[2]:.1f}\n")

        f.write(footer_start)
        f.write(insert)
        f.write(footer)

def main():
    if len(sys.argv) < 2:
        print("Usage: python dxf_hybrid_simplify.py input.dxf [target_faces=40000]")
        sys.exit(1)

    input_path = sys.argv[1]
    target_faces = int(sys.argv[2]) if len(sys.argv) > 2 else 40000

    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    folder, filename = os.path.split(input_path)
    name, _ = os.path.splitext(filename)
    obj_tmp = os.path.join(folder, f"{name}_temp.obj")
    output_path = os.path.join(folder, f"{name}_OPT10MB.dxf")

    t0 = time.time()
    print(f"[*] Streaming 3DFACE extraction from {filename}...")
    n_faces = stream_dxf_to_obj(input_path, obj_tmp)
    print(f"[INFO] Extracted {n_faces:,} faces → temporary OBJ")

    print("[*] Loading mesh...")
    mesh = trimesh.load(obj_tmp, force="mesh", process=False)

    print("[*] Cleaning + simplifying...")
    mesh = simplify_mesh(mesh, target_faces)

    print("[*] Writing optimized DXF...")
    write_optimized_dxf(mesh, output_path, use_block=True)

    if os.path.exists(obj_tmp):
        os.remove(obj_tmp)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print("\n[+] DONE")
    print(f" |-> Time          : {time.time()-t0:.1f} s")
    print(f" |-> Output        : {output_path}")
    print(f" |-> Final size    : {size_mb:.2f} MB")
    print(f" |-> Faces kept    : {len(mesh.faces):,}")

if __name__ == "__main__":
    main()
