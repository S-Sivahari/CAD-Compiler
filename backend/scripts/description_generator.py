
import os
import json
import time
import requests
import base64
import glob
import zipfile
from pathlib import Path

# --- Configuration ---
BATCHES_ZIP = "../../batches.zip" # Relative to this script in backend/scripts
OUTPUT_DIR = "local_descriptions"
MODEL = "llava-phi3"
OLLAMA_URL = "http://localhost:11434/api/generate"

def setup():
    """Unzip batches if needed."""
    if not os.path.exists("batches"):
        print(f"Unzipping {BATCHES_ZIP}...")
        if not os.path.exists(BATCHES_ZIP):
            # Try looking in current dir just in case
            if os.path.exists("batches.zip"):
                zip_path = "batches.zip"
            else:
                try:
                    # Attempt to find it in the project root if running from backend/scripts
                    root_zip = os.path.abspath(os.path.join(os.getcwd(), "../../batches.zip"))
                    if os.path.exists(root_zip):
                        zip_path = root_zip
                    else:
                         print(f"Error: {BATCHES_ZIP} not found!")
                         return False
                except:
                     print(f"Error: {BATCHES_ZIP} not found!")
                     return False
        else:
            zip_path = BATCHES_ZIP
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
    return True

def encode_image(path):
    if not os.path.exists(path): return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def generate_desc(data, img_path):
    img_b64 = encode_image(img_path)
    if not img_b64: return None

    # DETAILED VISUAL PROMPT
    prompt = f"""
    Act as an expert parametric CAD engineer analysing this 3D engineering drawing for reconstruction.
    
    SYSTEM INSTRUCTION:
    The image may contain a SINGLE part or an ASSEMBLY of MULTIPLE shapes.
    Break down the object into its primitive geometric components and describe their SPATIAL RELATIONSHIPS.
    
    **1. IDENTIFY SHAPES (Use this list):**
    - Primitives: Cube, Block, Cylinder, Sphere, Cone, Tube, Torus, Prism.
    - Profiles: L-Bracket, T-Profile, U-Channel, I-Beam, Hexagon, Octagon.
    - Complex: Gear (Spur/Helical), Flange, Pulley, Bearing Housing, Threaded Rod.
    
    **2. DESCRIBE COMPOSITION (Spatial Logic):**
    - "A [Shape A] is positioned [on top of / adjacent to / intersecting] a [Shape B]."
    - "The base is a [Shape], with a [Shape] protruding from the center."
    - "Two [Shapes] are connected by a [Shape]."
    
    **3. DESCRIBE FEATURES (Critical Details if present):**
    - **Holes**: Round, Countersunk, Counterbored, Hexagonal? Where? (Center, corners, bolt circle?)
    - **Cuts/Slots**: Rectangular slots, keyways, side cutouts, arched cutouts?
    - **Additions**: Bosses, ribs, fillets, chamfers?
    - **Patterns**: Linear array (row of holes), Polar array (circular pattern of holes/spokes)?
    
    **RESPONSE FORMAT**:
    - Start with a high-level summary: "This is a [Function/Name] consisting of..."
    - Describe the BASE geometry.
    - Describe ADDITIONAL parts and their positions relative to the base.
    - List internal features (holes, cuts).
    - Keep it purely geometrical and descriptive. NO specific dimensions (numbers), only usage of relative terms (large, small, centered, equidistant).
    - Ensure that the description is under 125 words.
    """
    
    payload = {
        "model": MODEL, 
        "prompt": prompt, 
        "stream": False,
        "options": {
            "num_ctx": 2048,
            "temperature": 0.2 # Slightly higher to allow flow, but low enough to prevent hallucinations
        }
    }
    payload["images"] = [img_b64]
    
    start_t = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        elapsed = time.time() - start_t
        
        if resp.status_code == 200:
            return resp.json().get("response", "").strip(), elapsed
        else:
            print(f"Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return None, time.time() - start_t

def main():
    if not setup(): return

    # Ensure output dir
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all batches
    batch_dirs = sorted(glob.glob("batches/batch_*"))
    if not batch_dirs:
        print("No batches found in 'batches/' directory.")
        return

    print(f"Found {len(batch_dirs)} batches. Starting LOCAL GENERATION (GPU/CPU)...")
    
    total_imgs = 0
    total_time = 0
    
    # Process ALL batches
    for batch_dir in batch_dirs:
        batch_name = os.path.basename(batch_dir)
        print(f"\n--- Processing {batch_name} ---")
        
        # Create output dir for this batch to match structure
        batch_out_dir = os.path.join(OUTPUT_DIR, batch_name)
        os.makedirs(batch_out_dir, exist_ok=True)

        json_files = glob.glob(os.path.join(batch_dir, "*.json"))
        
        for json_file in json_files:
            base = os.path.splitext(os.path.basename(json_file))[0]
            out_file = os.path.join(batch_out_dir, f"{base}.txt")
            
            # Skip if done
            if os.path.exists(out_file):
                continue
            
            # Find image
            img_path = os.path.join(batch_dir, f"{base}.png")
            if not os.path.exists(img_path):
                 img_path = os.path.join(batch_dir, f"{base}.jpg")
            
            if not os.path.exists(img_path): continue

            with open(json_file, 'r') as f:
                data = json.load(f)

            print(f"[{base}] Generating...", end=" ", flush=True)
            desc, elapsed = generate_desc(data, img_path)
            
            if desc:
                print(f"Done ({elapsed:.2f}s)")
                total_time += elapsed
                total_imgs += 1
                
                with open(out_file, "w") as f:
                    f.write(desc)
            else:
                print("Failed.")
    
    if total_imgs > 0:
        avg = total_time / total_imgs
        print(f"\nJob Complete.")
        print(f"Total Images: {total_imgs}")
        print(f"Average Time: {avg:.2f}s")

if __name__ == "__main__":
    main()
