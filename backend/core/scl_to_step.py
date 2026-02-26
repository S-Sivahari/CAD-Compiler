import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent))

from core.main import SynthoCadPipeline


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/scl_to_step.py <json_file>")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    
    with open(json_file_path, 'r') as f:
        json_data = json.load(f)
    
    from core import config as _cfg
    pipeline = SynthoCadPipeline(rag_provider=_cfg.get_rag_provider())
    result = pipeline.process_from_json(json_data, open_freecad=False)
    
    if result['status'] == 'success':
        print("[SUCCESS]")
        print(f"  JSON:       {result['json_file']}")
        print(f"  Python:     {result['py_file']}")
        print(f"  STEP:       {result['step_file']}")
        print(f"  Parameters: {result['parameters']['total_count']} found")
    else:
        print(f"[FAILED] {result['error']}")
        sys.exit(1)

