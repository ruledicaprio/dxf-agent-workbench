#!/usr/bin/env python3
"""
dxf_three_stage_simplify.py
Three-stage mesh simplification optimized for noisy Meshy5 / AI-generated DXF models
(especially complex industrial objects like FG Wilson genset skids)

Usage:
    python dxf_three_stage_simplify.py input.dxf [target_faces=20000]
"""

import os
import sys
import time
import numpy as np

try:
    import trimesh
except ImportError:
    print("[ERROR] Please install: pip install trimesh numpy")
    sys.exit(1)

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False
    print("[INFO] open3d not found – Stage 0 (vertex clustering) will be skipped")

try:
    import pyfqmr
    HAS_PYFQMR = True
except ImportError:
    HAS_PYFQMR = False
    print("[INFO] pyfqmr not found – will fall back to trimesh for final stage")


def stream_dxf_to_obj(input_path: str, obj_path: str) -> int:
    """Low-RAM extraction of 3DFACE entities into a temporary OBJ"""
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


def three_stage_simplify(mesh: trimesh.Trimesh, target_faces: int = 20000) -> trimesh.Trimesh:
    """
    Stage 0 : Vertex clustering   (very robust on noisy AI meshes)
    Stage 1 : Aggressive quadric  (kill most of the density)
    Stage 2 : Quality pass        (recover better edges / silhouette)
    """
    print(f"[*] Original faces: {len(mesh.faces):,}")

    # Light cleaning
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    print(f"[*] After light cleaning: {len(mesh.faces):,} faces")

    if len(mesh.faces) <= target_faces:
        print("[INFO] Already under target")
        return mesh

    # -------------------------------------------------
    # STAGE 0 – Vertex Clustering (optional but recommended for Meshy)
    # -------------------------------------------------
    if HAS_OPEN3D and len(mesh.faces) > 400_000:
        print("[*] Stage 0: Vertex clustering (robust on noisy Meshy meshes)...")
        extent = float(mesh.extents.max())
        # Smaller voxel = more detail kept. 1/120 ~ 1/180 works well for gensets
        voxel_size = extent / 140.0

        o3d_mesh = o3d.geometry.TriangleMesh(
            o3d.utility.Vector3dVector(mesh.vertices),
            o3d.utility.Vector3iVector(mesh.faces)
        )
        o3d_mesh = o3d_mesh.simplify_vertex_clustering(
            voxel_size=voxel_size,
            contraction=o3d.geometry.SimplificationContraction.Average
        )
        mesh = trimesh.Trimesh(
            vertices=np.asarray(o3d_mesh.vertices),
            faces=np.asarray(o3d_mesh.triangles),
            process=False
        )
        print(f"[*] After Stage 0: {len(mesh.faces):,} faces")

    # -------------------------------------------------
    # STAGE 1 – Aggressive Quadric
    # -------------------------------------------------
    stage1_target = min(140_000, max(target_faces * 5, 60_000))
    if len(mesh.faces) > stage1_target:
        print(f"[*] Stage 1: Aggressive quadric → ~{stage1_target:,} faces (aggression=9)")
        t0 = time.time()
        mesh = mesh.simplify_quadric_decimation(
            face_count=stage1_target,
            aggression=9
        )
        print(f"[*] Stage 1 finished in {time.time()-t0:.1f}s → {len(mesh.faces):,} faces")

    if len(mesh.faces) <= target_faces:
        return mesh

    # -------------------------------------------------
    # STAGE 2 – Quality / Final pass
    # -------------------------------------------------
    print(f"[*] Stage 2: Final quality pass → {target_faces:,} faces")

    if HAS_PYFQMR:
        print("    Using pyfqmr (aggressiveness=7, preserve_border=False)")
        simplifier = pyfqmr.Simplify()
        simplifier.setMesh(mesh.vertices, mesh.faces)

        t0 = time.time()
        simplifier.simplify_mesh(
            target_count=target_faces,
            aggressiveness=7,
            preserve_border=False,      # better for Meshy topology
            verbose=True
        )
        print(f"[*] pyfqmr finished in {time.time()-t0:.1f}s")

        vertices, faces, _ = simplifier.getMesh()
        result = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    else:
        print("    Using trimesh fallback (aggression=7)")
        result = mesh.simplify_quadric_decimation(
            face_count=target_faces,
            aggression=7
        )

    print(f"[INFO] Final faces: {len(result.faces):,}")
    return result


def write_optimized_dxf(mesh: trimesh.Trimesh, output_path: str):
    """Write clean R12-style DXF with 3DFACE entities"""
    header = (
        "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1009\n  0\nENDSEC\n"
        "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  8\n0\n  2\nGENERATOR_MESH\n"
        " 70\n     0\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
    )
    midway = "  0\nENDBLK\n  0\nENDSEC\n  0\nSECTION\n  2\nENTITIES\n"
    insert = "  0\nINSERT\n  8\n0\n  2\nGENERATOR_MESH\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
    footer = "  0\nENDSEC\n  0\nEOF\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)

        for face in mesh.faces:
            f.write("  0\n3DFACE\n  8\n0\n")
            for i in range(4):
                idx = face[i] if i < 3 else face[2]
                v = mesh.vertices[idx]
                f.write(f" 1{i}\n{v[0]:.2f}\n")
                f.write(f" 2{i}\n{v[1]:.2f}\n")
                f.write(f" 3{i}\n{v[2]:.2f}\n")

        f.write(midway)
        f.write(insert)
        f.write(footer)


def main():
    if len(sys.argv) < 2:
        print("Usage: python dxf_three_stage_simplify.py input.dxf [target_faces=20000]")
        sys.exit(1)

    input_path = sys.argv[1]
    target_faces = int(sys.argv[2]) if len(sys.argv) > 2 else 20000

    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    folder, filename = os.path.split(input_path)
    name, _ = os.path.splitext(filename)
    obj_tmp = os.path.join(folder, f"{name}_temp.obj")
    output_path = os.path.join(folder, f"{name}_3STAGE.dxf")

    t_start = time.time()

    print(f"[*] Streaming 3DFACE extraction from {filename}...")
    n_faces = stream_dxf_to_obj(input_path, obj_tmp)
    print(f"[INFO] Extracted {n_faces:,} faces")

    print("[*] Loading mesh...")
    mesh = trimesh.load(obj_tmp, force="mesh", process=False)

    print("[*] Starting three-stage simplification...")
    mesh = three_stage_simplify(mesh, target_faces)

    print("[*] Writing optimized DXF...")
    write_optimized_dxf(mesh, output_path)

    if os.path.exists(obj_tmp):
        os.remove(obj_tmp)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print("\n[+] THREE-STAGE SIMPLIFICATION COMPLETE")
    print(f" |-> Total time     : {time.time() - t_start:.1f} s")
    print(f" |-> Output         : {output_path}")
    print(f" |-> Final size     : {size_mb:.2f} MB")
    print(f" |-> Faces kept     : {len(mesh.faces):,}")


if __name__ == "__main__":
    main()
