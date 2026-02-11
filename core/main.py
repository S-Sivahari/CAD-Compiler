import json
import sys
import subprocess
from pathlib import Path
from json_validator import validate_json
from cadquery_generator import generate_cadquery_file


def process_json_to_step(json_path, output_dir=None, execute=True):
    json_path = Path(json_path)
    
    if not json_path.exists():
        return False, f"JSON file not found: {json_path}"
    
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    if not validate_json(json_data):
        return False, "JSON validation failed"
    
    if output_dir is None:
        output_dir = json_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    final_name = json_data.get("final_name", json_path.stem)
    if not final_name or final_name.strip() == "":
        final_name = json_path.stem
        
    py_output = output_dir / f"{final_name}_generated.py"
    
    generate_cadquery_file(json_data, py_output)
    
    if execute:
        try:
            result = subprocess.run(
                [sys.executable, str(py_output)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=output_dir
            )
            
            if result.returncode != 0:
                return False, f"Execution failed: {result.stderr}"
                
            step_file = output_dir / f"{final_name}.step"
            if step_file.exists():
                return True, {
                    "python_file": str(py_output),
                    "step_file": str(step_file)
                }
            else:
                return False, "STEP file not created"
                
        except subprocess.TimeoutExpired:
            return False, "Execution timeout"
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    else:
        return True, {"python_file": str(py_output)}


def batch_process(input_dir, output_dir=None, execute=True):
    input_dir = Path(input_dir)
    results = []
    
    json_files = list(input_dir.rglob("*.json"))
    
    for json_file in json_files:
        success, result = process_json_to_step(json_file, output_dir, execute)
        results.append({
            "input": str(json_file),
            "success": success,
            "result": result
        })
        
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <json_file> [output_dir] [--no-execute]")
        sys.exit(1)
        
    json_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    execute = "--no-execute" not in sys.argv
    
    success, result = process_json_to_step(json_path, output_dir, execute)
    
    if success:
        print("Success:")
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {result}")
    else:
        print(f"Failed: {result}")
        sys.exit(1)
