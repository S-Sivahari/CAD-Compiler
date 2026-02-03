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
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Debug check
if GEMINI_API_KEY:
    print(f"✓ Gemini API Key loaded: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:]}")

# Template definitions with parameters
TEMPLATE_CATALOG = {
    "cube": {"params": ["size"], "defaults": {"size": 50}},
    "cuboid": {"params": ["length", "width", "height"], "defaults": {"length": 100, "width": 50, "height": 30}},
    "cylinder": {"params": ["radius", "height"], "defaults": {"radius": 25, "height": 100}},
    "sphere": {"params": ["radius"], "defaults": {"radius": 50}},
    "cone": {"params": ["radius1", "radius2", "height"], "defaults": {"radius1": 50, "radius2": 20, "height": 100}},
    "torus": {"params": ["radius1", "radius2"], "defaults": {"radius1": 50, "radius2": 10}},
    "tube": {"params": ["outer_radius", "inner_radius", "height"], "defaults": {"outer_radius": 30, "inner_radius": 20, "height": 100}},
    "plate": {"params": ["length", "width", "thickness"], "defaults": {"length": 100, "width": 80, "thickness": 10}},
    "rod": {"params": ["diameter", "length"], "defaults": {"diameter": 20, "length": 100}},
    "ring": {"params": ["outer_diameter", "inner_diameter", "thickness"], "defaults": {"outer_diameter": 60, "inner_diameter": 40, "thickness": 10}},
    "pyramid": {"params": ["base_length", "base_width", "height", "sides"], "defaults": {"base_length": 100, "base_width": 100, "height": 80, "sides": 4}},
    "prism": {"params": ["sides", "radius", "height"], "defaults": {"sides": 6, "radius": 50, "height": 100}},
    "filleted_box": {"params": ["length", "width", "height", "fillet_radius"], "defaults": {"length": 100, "width": 80, "height": 50, "fillet_radius": 10}},
    "l_bracket": {"params": ["length", "width", "height", "thickness"], "defaults": {"length": 80, "width": 60, "height": 50, "thickness": 8}},
    "u_bracket": {"params": ["length", "width", "height", "thickness"], "defaults": {"length": 100, "width": 60, "height": 50, "thickness": 8}},
    "mounting_plate": {"params": ["length", "width", "thickness", "hole_diameter", "hole_pattern"], "defaults": {"length": 200, "width": 150, "thickness": 10, "hole_diameter": 8, "hole_pattern": "4_corner"}},
    "motor_mount_plate": {"params": ["motor_size", "mounting_thickness", "base_size"], "defaults": {"motor_size": "NEMA23", "mounting_thickness": 10, "base_size": 90}},
}


def call_llm(messages: List[Dict], model: str = "gemini-1.5-flash"):
    """Call Google Gemini API - FREE with generous limits"""
    if not GEMINI_API_KEY:
        print("\n⚠️  No Gemini API key found!")
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
        print(f"❌ Gemini Error: {e}")
        try:
            error_data = response.json()
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Response text: {response.text if response else 'No response'}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
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


def generate_model_script(template: str, params: Dict) -> str:
    """Generate Python script to create the model"""
    script = f'''"""
Generated CAD Model: {template}
"""

import sys
import os

freecad_path = r"C:\\Program Files\\FreeCAD 1.0\\bin"
if os.path.exists(freecad_path):
    sys.path.insert(0, freecad_path)
    sys.path.insert(0, os.path.join(os.path.dirname(freecad_path), "lib"))

try:
    import FreeCAD as App
except ImportError:
    print("Error: FreeCAD could not be imported.")
    sys.exit(1)

from launcher import create_document, open_gui, export_step
from templates import {template}

if __name__ == "__main__":
    doc = create_document("{template.capitalize()}Model")
    
    # Create model
    shape = {template}(doc, {', '.join([f'{k}={repr(v)}' for k, v in params.items()])})
    
    # Export to STEP
    export_step(shape, "{template}_model.step")
    
    # Open in FreeCAD
    open_gui(doc)
'''
    return script


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
        print("\n🤖 Thinking...")
        llm_response = call_llm(conversation)
        
        if not llm_response:
            print("❌ Failed to get response from LLM")
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
            
            print(f"\n✓ Generating {template} with parameters:")
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
            
            print(f"\n✓ Script saved: {script_file}")
            print("✓ Launching FreeCAD...")
            
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
            print(f"\n🤖: {message}\n")


def command_mode(description: str):
    """Single command mode"""
    system_prompt = build_template_prompt()
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": description}
    ]
    
    print(f"Processing: {description}")
    print("🤖 Analyzing...")
    
    llm_response = call_llm(conversation)
    
    if not llm_response:
        print("❌ Failed to get response from LLM")
        return
    
    parsed = parse_llm_response(llm_response)
    
    if parsed.get("ready"):
        template = parsed["template"]
        params = parsed["params"]
        
        print(f"\n✓ Generating {template}")
        
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
        
        print(f"✓ Script saved: {script_file}")
        print("✓ Launching FreeCAD...")
        
        freecad_python = r"C:\Program Files\FreeCAD 1.0\bin\python.exe"
        os.system(f'"{freecad_python}" "{script_file}"')
    else:
        print(f"⚠️  Missing information: {parsed.get('message', llm_response)}")
        print("Please provide complete description or use interactive mode")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command mode: python main.py "create a cube 50mm"
        description = " ".join(sys.argv[1:])
        command_mode(description)
    else:
        # Interactive mode
        interactive_mode()
