"""
Main CAD Generator with LLM Integration
Natural language to 3D model generation
"""

import os
import sys
import json
import re
from typing import Dict, List, Any

# OpenRouter API setup
try:
    import requests
except ImportError:
    print("Installing required packages...")
    os.system("pip install requests")
    import requests

# Load .env file if exists
def load_env():
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# Debug check
if GEMINI_API_KEY:
    print(f"[OK] Gemini API Key loaded:")

# Template definitions with parameters
TEMPLATE_CATALOG = {
    # --- Primitive Solids ---
    "cube": {"params": ["size"], "defaults": {"size": 50}},
    "cuboid": {"params": ["length", "width", "height"], "defaults": {"length": 100, "width": 50, "height": 30}},
    "cylinder": {"params": ["radius", "height"], "defaults": {"radius": 25, "height": 100}},
    "sphere": {"params": ["radius"], "defaults": {"radius": 50}},
    "cone": {"params": ["radius1", "radius2", "height"], "defaults": {"radius1": 50, "radius2": 20, "height": 100}},
    "torus": {"params": ["radius1", "radius2"], "defaults": {"radius1": 50, "radius2": 10}},
    "tube": {"params": ["outer_radius", "inner_radius", "height"], "defaults": {"outer_radius": 30, "inner_radius": 20, "height": 100}},
    "rectangular_tube": {"params": ["length", "width", "height", "wall_thickness"], "defaults": {"length": 100, "width": 50, "height": 100, "wall_thickness": 5}},
    "wedge": {"params": ["length", "width", "height"], "defaults": {"length": 50, "width": 50, "height": 50}},
    "prism": {"params": ["sides", "radius", "height"], "defaults": {"sides": 6, "radius": 50, "height": 100}},
    "pyramid": {"params": ["base_length", "base_width", "height", "sides"], "defaults": {"base_length": 100, "base_width": 100, "height": 80, "sides": 4}},
    "filleted_box": {"params": ["length", "width", "height", "fillet_radius"], "defaults": {"length": 100, "width": 80, "height": 50, "fillet_radius": 10}},

    # --- Plates & Bars ---
    "plate": {"params": ["length", "width", "thickness"], "defaults": {"length": 100, "width": 80, "thickness": 10}},
    "rod": {"params": ["diameter", "length"], "defaults": {"diameter": 20, "length": 100}},
    "ring": {"params": ["outer_diameter", "inner_diameter", "thickness"], "defaults": {"outer_diameter": 60, "inner_diameter": 40, "thickness": 10}},

    # --- Structural Profiles ---
    "i_beam": {"params": ["length", "height", "width", "web_thickness", "flange_thickness"], "defaults": {"length": 200, "height": 100, "width": 50, "web_thickness": 5, "flange_thickness": 8}},
    "c_channel": {"params": ["length", "height", "width", "thickness"], "defaults": {"length": 200, "height": 100, "width": 50, "thickness": 5}},
    "angle_iron": {"params": ["length", "leg1_length", "leg2_length", "thickness"], "defaults": {"length": 200, "leg1_length": 50, "leg2_length": 50, "thickness": 5}},
    "t_slot_extrusion": {"params": ["length", "size"], "defaults": {"length": 200, "size": 20}}, # 2020 profile default

    # --- Brackets & Mounting ---
    "l_bracket": {"params": ["length", "width", "height", "thickness"], "defaults": {"length": 80, "width": 60, "height": 50, "thickness": 8}},
    "u_bracket": {"params": ["length", "width", "height", "thickness"], "defaults": {"length": 100, "width": 60, "height": 50, "thickness": 8}},
    "z_bracket": {"params": ["length", "width", "height", "thickness", "offset"], "defaults": {"length": 50, "width": 40, "height": 40, "thickness": 5, "offset": 20}},
    "mounting_plate": {"params": ["length", "width", "thickness", "hole_diameter", "hole_pattern"], "defaults": {"length": 200, "width": 150, "thickness": 10, "hole_diameter": 8, "hole_pattern": "4_corner"}},
    "motor_mount_plate": {"params": ["motor_size", "mounting_thickness", "base_size"], "defaults": {"motor_size": "NEMA23", "mounting_thickness": 10, "base_size": 90}},

    # --- Gears & Motion (Updated with Rack Gear) ---
    "spur_gear": {"params": ["module", "teeth", "thickness"], "defaults": {"module": 1, "teeth": 20, "thickness": 5}},
    "rack_gear": {"params": ["length", "width", "height", "module"], "defaults": {"length": 100, "width": 10, "height": 10, "module": 1}},
    "pulley": {"params": ["diameter", "width", "shaft_diameter"], "defaults": {"diameter": 50, "width": 10, "shaft_diameter": 8}},
    "sprocket": {"params": ["teeth", "pitch", "thickness"], "defaults": {"teeth": 20, "pitch": 12.7, "thickness": 5}},

    # --- Common Parts (Updated with Hex Bolt & Bearing) ---
    "hex_bolt": {"params": ["size", "length"], "defaults": {"size": 6, "length": 30}}, 
    "bearing_radial": {"params": ["inner_dia", "outer_dia", "width"], "defaults": {"inner_dia": 8, "outer_dia": 22, "width": 7}},
    "washer": {"params": ["inner_diameter", "outer_diameter", "thickness"], "defaults": {"inner_diameter": 8, "outer_diameter": 16, "thickness": 1.5}},
    "bushing": {"params": ["inner_diameter", "outer_diameter", "length", "flange_width"], "defaults": {"inner_diameter": 10, "outer_diameter": 14, "length": 20, "flange_width": 2}},
    "spacer": {"params": ["inner_diameter", "outer_diameter", "length"], "defaults": {"inner_diameter": 5, "outer_diameter": 10, "length": 10}},

    # --- Piping (New Category) ---
    "pipe_elbow": {"params": ["inner_dia", "wall_thickness", "bend_radius", "angle"], "defaults": {"inner_dia": 20, "wall_thickness": 3, "bend_radius": 30, "angle": 90}},
    "circular_flange": {"params": ["outer_diameter", "inner_diameter", "thickness", "hole_count"], "defaults": {"outer_diameter": 100, "inner_diameter": 50, "thickness": 10, "hole_count": 6}},

    # --- Enclosures & Electronics ---
    "electronics_box": {"params": ["length", "width", "height", "wall_thickness"], "defaults": {"length": 100, "width": 80, "height": 50, "wall_thickness": 3}},
    "rectangular_enclosure": {"params": ["length", "width", "height", "wall_thickness", "lid_thickness"], "defaults": {"length": 120, "width": 80, "height": 40, "wall_thickness": 2, "lid_thickness": 2}},
    "heatsink_finned": {"params": ["length", "width", "base_height", "fin_height", "fin_count"], "defaults": {"length": 40, "width": 40, "base_height": 2, "fin_height": 10, "fin_count": 10}},
    
    # --- Cutout Operations (Negatives) ---
    "usb_c_cutout": {"params": ["clearance"], "defaults": {"clearance": 0.2}},
    "through_hole": {"params": ["radius"], "defaults": {"radius": 5}},
    "blind_hole": {"params": ["radius", "depth"], "defaults": {"radius": 5, "depth": 10}},
}


def call_llm(messages: List[Dict], model: str = "gemini-1.5-flash"):
    """Call Google Gemini API - FREE with generous limits"""
    if not GEMINI_API_KEY:
        print("\n[WARN] No Gemini API key found!")
        print("Please set GEMINI_API_KEY in .env file")
        print("Get your key from: https://makersuite.google.com/app/apikey")
        sys.exit(1)
    
    # Convert messages to Gemini format
    gemini_contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        if msg["role"] != "system":
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        else:
            # System message goes as first user message
            gemini_contents.insert(0, {
                "role": "user",
                "parts": [{"text": msg["content"]}]
            })
    
    data = {
        "contents": gemini_contents
    }
    
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    
    try:
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] Gemini Error: {e}")
        try:
            error_data = response.json()
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Response text: {response.text if response else 'No response'}")
        return None
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return None


def build_template_prompt() -> str:
    """Build comprehensive template catalog for LLM"""
    prompt = """You are a CAD assistant. User will describe a 3D model in natural language.

Your task:
1. Identify which template(s) match the description
2. Extract any dimensions/parameters mentioned
3. If required parameters are missing, ask for them specifically
4. Once you have all needed info, respond with JSON

Available Templates:
"""
    
    for name, info in TEMPLATE_CATALOG.items():
        params_str = ", ".join([f"{p}" for p in info["params"]])
        defaults_str = ", ".join([f"{k}={v}" for k, v in info["defaults"].items()])
        prompt += f"\n- {name}({params_str}) [defaults: {defaults_str}]"
    
    prompt += """

Response Format (CRITICAL):
If parameters are COMPLETE, respond with ONLY JSON, nothing else:
{
  "ready": true,
  "template": "template_name",
  "params": {"param1": value1, "param2": value2}
}

If parameters are MISSING, respond with ONLY JSON asking for them:
{
  "ready": false,
  "message": "What should the <missing_param> be? (in mm)"
}

IMPORTANT: 
- When ready=true, respond with ONLY the JSON object, no extra text
- Do not add explanations before or after the JSON
- Extract numeric values from text like "50mm" → 50

Examples:
User: "create a cube"
Assistant: {"ready": false, "message": "What size should the cube be? (in mm)"}

User: "50mm"
Assistant: {"ready": true, "template": "cube", "params": {"size": 50}}

User: "make a cylinder radius 30 height 100"
Assistant: {"ready": true, "template": "cylinder", "params": {"radius": 30, "height": 100}}
"""
    
    return prompt


def parse_llm_response(response: str) -> Dict:
    """Parse LLM JSON response"""
    try:
        # Try to find JSON in response - look for complete JSON object
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            parsed = json.loads(json_str)
            # Validate it has required structure
            if 'ready' in parsed:
                return parsed
        
        # Try parsing entire response
        parsed = json.loads(response)
        if 'ready' in parsed:
            return parsed
    except:
        pass
    
    # If not valid JSON, treat as conversational message
    return {"ready": False, "message": response}


def generate_model_script(template: str, params: Dict, headless: bool = False) -> str:
    """Generate Python script to create the model"""
    script = f'''"""
Generated CAD Model: {template}
"""

import sys
import os

# Add parent directory to path to import launcher and templates
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))

freecad_path = r"C:\\Users\\Ashfaq Ahamed A\\AppData\\Local\\Programs\\FreeCAD 1.0\\bin"
if os.path.exists(freecad_path):
    sys.path.insert(0, freecad_path)
    sys.path.insert(0, os.path.join(os.path.dirname(freecad_path), "lib"))

try:
    import FreeCAD as App
except ImportError:
    print("Error: FreeCAD could not be imported.")
    sys.exit(1)

from launcher import create_document, open_gui, export_step, export_stl
from templates import {template}

if __name__ == "__main__":
    doc = create_document("{template.capitalize()}Model")
    
    # Create model
    shape = {template}(doc, {', '.join([f'{k}={repr(v)}' for k, v in params.items()])})
    
    # Export to STEP (Engineering Data)
    export_step(shape, "{template}_model.step")

    # Export to STL (Web Viewer Data)
    export_stl(shape, "{template}_model.stl")
    
    # Open in FreeCAD (Only if not headless)
    if not {headless}:
        open_gui(doc)
'''
    return script


def process_request(description: str, headless: bool = True):
    """Process a request programmatically and return result dict"""
    system_prompt = build_template_prompt()
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": description}
    ]
    
    print(f"Processing: {description}")
    llm_response = call_llm(conversation)
    
    if not llm_response:
        return {"success": False, "error": "LLM failed to respond"}
    
    parsed = parse_llm_response(llm_response)
    
    if not parsed.get("ready"):
        return {
            "success": False, 
            "ready": False, 
            "message": parsed.get("message", llm_response),
            "raw_response": parsed
        }
        
    # Ready to generate
    template = parsed["template"]
    params = parsed["params"]
    
    # Generate script
    script_content = generate_model_script(template, params, headless=headless)
    
    # Create generated_models folder
    gen_models_dir = os.path.join(os.path.dirname(__file__), "generated_models")
    if not os.path.exists(gen_models_dir):
        os.makedirs(gen_models_dir)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_filename = f"{template}_{timestamp}.py"
    script_file = os.path.join(gen_models_dir, script_filename)
    
    with open(script_file, "w") as f:
        f.write(script_content)
        
    # Execute script
    import launcher
    exit_code = launcher.run_with_freecad_python(script_file, headless=headless)
    
    if exit_code != 0:
        return {"success": False, "error": "FreeCAD script execution failed"}
        
    return {
        "success": True,
        "ready": True,
        "template": template,
        "params": params,
        "files": {
            "script": script_filename,
            "step": f"{template}_model.step",
            "stl": f"{template}_model.stl"
        }
    }


def interactive_mode():
    """Interactive conversation with LLM"""
    print("=" * 70)
    print("CAD Generator - Natural Language to 3D Models")
    print("=" * 70)
    print("\nType your model description (or 'quit' to exit)")
    print("Example: 'create a motor mount' or 'make a cube 50mm'\n")
    
    system_prompt = build_template_prompt()
    conversation = [{"role": "system", "content": system_prompt}]
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Add user message to conversation
        conversation.append({"role": "user", "content": user_input})
        
        # Get LLM response
        print("[AI] Thinking...")
        llm_response = call_llm(conversation)
        
        if not llm_response:
            print("[ERROR] Failed to get response from LLM")
            conversation.pop()  # Remove failed message
            continue
        
        # Add assistant response to conversation
        conversation.append({"role": "assistant", "content": llm_response})
        
        # Parse response
        parsed = parse_llm_response(llm_response)
        
        if parsed.get("ready"):
            # Ready to generate!
            template = parsed["template"]
            params = parsed["params"]
            
            print(f"\n[OK] Generating {template} with parameters:")
            for k, v in params.items():
                print(f"  - {k}: {v}")
            
            # Generate script
            script_content = generate_model_script(template, params)
            
            # Create generated_models folder if it doesn't exist
            gen_models_dir = os.path.join(os.path.dirname(__file__), "generated_models")
            if not os.path.exists(gen_models_dir):
                os.makedirs(gen_models_dir)
            
            # Save script with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            script_file = os.path.join(gen_models_dir, f"{template}_{timestamp}.py")
            
            with open(script_file, "w") as f:
                f.write(script_content)
            
            print(f"\n[OK] Script saved: {script_file}")
            print("[OK] Launching FreeCAD...")
            
            # Run the generated script
            freecad_python = r"C:\Program Files\FreeCAD 1.0\bin\python.exe"
            os.system(f'"{freecad_python}" "{script_file}"')
            
            # Reset conversation for next model
            print("\n" + "=" * 70)
            print("Ready for next model!")
            print("=" * 70 + "\n")
            conversation = [{"role": "system", "content": system_prompt}]
            
        else:
            # LLM needs more info
            message = parsed.get("message", llm_response)
            print(f"\n[AI]: {message}\n")


def command_mode(description: str):
    """Single command mode"""
    system_prompt = build_template_prompt()
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": description}
    ]
    
    print(f"Processing: {description}")
    print("[AI] Analyzing...")
    
    llm_response = call_llm(conversation)
    
    if not llm_response:
        print("[ERROR] Failed to get response from LLM")
        return
    
    parsed = parse_llm_response(llm_response)
    
    if parsed.get("ready"):
        template = parsed["template"]
        params = parsed["params"]
        
        print(f"\n[OK] Generating {template}")
        
        # Create generated_models folder
        gen_models_dir = os.path.join(os.path.dirname(__file__), "generated_models")
        if not os.path.exists(gen_models_dir):
            os.makedirs(gen_models_dir)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_file = os.path.join(gen_models_dir, f"{template}_{timestamp}.py")
        
        script_content = generate_model_script(template, params)
        
        with open(script_file, "w") as f:
            f.write(script_content)
        
        print(f"[OK] Script saved: {script_file}")
        print("[OK] Launching FreeCAD...")
        
        freecad_python = r"C:\Program Files\FreeCAD 1.0\bin\python.exe"
        os.system(f'"{freecad_python}" "{script_file}"')
    else:
        print(f"[WARN] Missing information: {parsed.get('message', llm_response)}")
        print("Please provide complete description or use interactive mode")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command mode: python main.py "create a cube 50mm"
        description = " ".join(sys.argv[1:])
        command_mode(description)
    else:
        # Interactive mode
        interactive_mode()