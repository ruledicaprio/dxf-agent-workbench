import os
import sys
import time

if len(sys.argv) < 2:
    print("[ERROR] Target file path argument required.")
    sys.exit(1)
    
input_path = sys.argv[1]
if not os.path.exists(input_path):
    print(f"[ERROR] Target path invalid: {input_path}")
    sys.exit(1)

folder, filename = os.path.split(input_path)
name, ext = os.path.splitext(filename)
output_path = os.path.join(folder, f"{name}_BLOK{ext}")

print(f"[*] Step 1: Initializing Low-RAM Stream Pipeline for: {filename}...")
start_time = time.time()

dxf_header = (
    "  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1009\n  0\nENDSEC\n"
    "  0\nSECTION\n  2\nBLOCKS\n  0\nBLOCK\n  8\n0\n  2\nGENERATOR_MESH\n 70\n     0\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
)
block_midway = "  0\nENDBLK\n  8\n0\n  0\nENDSEC\n  0\nSECTION\n  2\nENTITIES\n"
block_reference = "  0\nINSERT\n  8\n0\n  2\nGENERATOR_MESH\n 10\n0.0\n 20\n0.0\n 30\n0.0\n"
dxf_footer = "  0\nENDSEC\n  0\nEOF\n"

temp_mesh_file = os.path.join(folder, "temp_mesh_cache.tmp")
face_count = 0

# DXF group kodovi koji drže X, Y, Z koordinate u 3DFACE
coord_codes = {"10", "20", "30", "11", "21", "31", "12", "22", "32", "13", "23", "33"}

with open(input_path, 'r', encoding='utf-8', errors='ignore') as infile, \
     open(temp_mesh_file, 'w', encoding='utf-8') as temp_out:
    
    iterator = iter(infile)
    in_3dface = False
    chunk = []
    
    while True:
        try:
            code_line = next(iterator)
            val_line = next(iterator)
            # Uklanjamo sve razmake odmah!
            code = code_line.strip()
            val = val_line.strip()
        except StopIteration:
            if in_3dface and chunk:
                temp_out.write("".join(chunk))
            break
            
        if code == "0":
            if in_3dface:
                temp_out.write("".join(chunk))
                chunk = []
                in_3dface = False
                
            if val == "3DFACE":
                in_3dface = True
                face_count += 1
                # Zapisujemo bez viška razmaka
                chunk.append("  0\n3DFACE\n")
                continue
                
        if in_3dface:
            # Zapisujemo kod bez razmaka
            chunk.append(f"{code}\n")
            
            if code in coord_codes:
                try:
                    f = float(val)
                    f_rounded = round(f, 1) 
                    
                    if f_rounded.is_integer():
                        chunk.append(f"{int(f_rounded)}\n")
                    else:
                        chunk.append(f"{f_rounded}\n")
                except ValueError:
                    chunk.append(f"{val}\n")
            else:
                chunk.append(f"{val}\n")

print(f"[INFO] Successfully isolated and optimized {face_count} 3DFACE entities.")

if face_count > 0:
    print("[*] Step 3: Compiling optimized geometry map...")
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write(dxf_header)
        with open(temp_mesh_file, 'r', encoding='utf-8') as temp_in:
            for line in temp_in:
                outfile.write(line)
        outfile.write(block_midway)
        outfile.write(block_reference)
        outfile.write(dxf_footer)

if os.path.exists(temp_mesh_file): 
    os.remove(temp_mesh_file)

end_time = time.time()
print("\n[+] STREAM COMPILATION COMPLETED!")
print(f" |-> Processing Time  : {end_time - start_time:.2f} seconds")
print(f" |-> Export Location  : {output_path}")
print(f" |-> Final File Size  : {os.path.getsize(output_path) / (1024*1024):.2f} MB")