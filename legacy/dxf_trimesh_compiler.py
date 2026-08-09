import os
import sys
import time
try:
    import trimesh
except ImportError:
    print("[ERROR] Trimesh nije pronađen. Pokreni: pip install trimesh ezdxf open3d")
    sys.exit(1)

if len(sys.argv) < 2:
    print("[ERROR] Target file path argument required.")
    sys.exit(1)
    
input_path = sys.argv[1]
if not os.path.exists(input_path):
    print(f"[ERROR] Target path invalid: {input_path}")
    sys.exit(1)

folder, filename = os.path.split(input_path)
name, ext = os.path.splitext(filename)
output_path = os.path.join(folder, f"{name}_SIMPLIFIED{ext}")
temp_obj_file = os.path.join(folder, "temp_mesh_cache.obj")

print(f"[*] Korak 1: Low-RAM ekstrakcija geometrije (Stream Pipeline) za: {filename}...")
start_time = time.time()

# --- LOW-RAM STREAM U OBJ FORMAT ---
# Ovo zaobilazi trimesh-ov DXF loader koji troši 16 GB RAM-a
vertex_count = 1
face_count = 0

with open(input_path, 'r', encoding='utf-8', errors='ignore') as infile, \
     open(temp_obj_file, 'w', encoding='utf-8') as obj_out:
    
    iterator = iter(infile)
    in_3dface = False
    coords = {}
    
    while True:
        try:
            code_line = next(iterator).strip()
            val_line = next(iterator).strip()
        except StopIteration:
            # Završi zadnji face ako postoji
            if in_3dface and coords:
                for i in range(4):
                    obj_out.write(f"v {coords.get(f'1{i}', '0')} {coords.get(f'2{i}', '0')} {coords.get(f'3{i}', '0')}\n")
                obj_out.write(f"f {vertex_count} {vertex_count+1} {vertex_count+2} {vertex_count+3}\n")
            break
            
        if code_line == "0":
            if in_3dface:
                # Upiši izvučene koordinate u OBJ format (v = vertex, f = face)
                for i in range(4):
                    x = coords.get(f"1{i}", "0")
                    y = coords.get(f"2{i}", "0")
                    z = coords.get(f"3{i}", "0")
                    obj_out.write(f"v {x} {y} {z}\n")
                
                obj_out.write(f"f {vertex_count} {vertex_count+1} {vertex_count+2} {vertex_count+3}\n")
                vertex_count += 4
                face_count += 1
                coords.clear()
                in_3dface = False
                
            if val_line == "3DFACE":
                in_3dface = True
                continue
                
        if in_3dface:
            # Kodovi 10,20,30, 11,21,31, 12,22,32, 13,23,33 za XYZ uglove
            if code_line in {"10", "20", "30", "11", "21", "31", "12", "22", "32", "13", "23", "33"}:
                coords[code_line] = val_line

print(f"[INFO] Uspješno izolovano i indeksirano {face_count} 3DFACE entiteta.")

print("[*] Korak 2: Učitavanje geometrije u Trimesh...")
# Trimesh učitava .obj fajlove ekstremno efikasno i brzo
mesh = trimesh.load(temp_obj_file, force='mesh')

print("[*] Korak 3: Geometrijska simplifikacija...")
TARGET_FACES = 5000

try:
    print(f" |-> Pokušavam Quadric Edge Collapse Decimation na {TARGET_FACES} poligona...")
    simplified_mesh = mesh.simplify_quadric_decimation(TARGET_FACES)
    print(f"[INFO] Simplifikacija uspjela! Novi broj poligona: {len(simplified_mesh.faces)}")
except Exception as e:
    print(f"[UPOZORENJE] Decimation nije uspio. Greška: {e}")
    print(" |-> Prebacujem na automatski Convex Hull (3D omotač)...")
    simplified_mesh = mesh.convex_hull
    print(f"[INFO] Convex Hull generisan. Novi broj poligona: {len(simplified_mesh.faces)}")

print(f"[*] Korak 4: Eksportovanje optimizovanog DXF-a...")
dxf_header = (
    "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1009\n  0\nENDSEC\n"
    "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  8\n0\n  2\nGENERATOR_MESH\n 70\n     0\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
)
block_midway = "  0\nENDBLK\n  8\n0\n  0\nENDSEC\n  0\nSECTION\n  2\nENTITIES\n"
block_reference = "  0\nINSERT\n  8\n0\n  2\nGENERATOR_MESH\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
dxf_footer = "  0\nENDSEC\n  0\nEOF\n"

with open(output_path, 'w', encoding='utf-8') as out_dxf:
    out_dxf.write(dxf_header)
    
    # Trimesh lica su obično trouglovi (3 tačke), a 3DFACE u DXF-u traži 4.
    # Pravilo je: ako je trougao, 4. tačka se ponavlja kao 3. tačka.
    for face in simplified_mesh.faces:
        out_dxf.write("  0\n3DFACE\n  8\n0\n")
        for i in range(4):
            v_idx = face[i] if i < 3 else face[2]
            vertex = simplified_mesh.vertices[v_idx]
            out_dxf.write(f" 1{i}\n{vertex[0]:.1f}\n")
            out_dxf.write(f" 2{i}\n{vertex[1]:.1f}\n")
            out_dxf.write(f" 3{i}\n{vertex[2]:.1f}\n")
            
    out_dxf.write(block_midway)
    out_dxf.write(block_reference)
    out_dxf.write(dxf_footer)

if os.path.exists(temp_obj_file):
    os.remove(temp_obj_file)

end_time = time.time()
print("\n[+] HIBRIDNA SIMPLIFIKACIJA ZAVRŠENA!")
print(f" |-> Vrijeme procesiranja : {end_time - start_time:.2f} sekundi")
print(f" |-> Izlazna lokacija     : {output_path}")
print(f" |-> Nova veličina fajla  : {os.path.getsize(output_path) / 1024:.2f} KB") # Prebačeno u KB!