# SynthoCAD - Natural Language to Parametric CAD Pipeline

**Convert natural language descriptions into STEP files via LLM-powered JSON generation.**

## Quick Start

```bash
python backend/llm_cli.py -p "Create a cylinder 10mm radius, 20mm tall"
```

Or interactive mode:
```bash
python backend/llm_cli.py
```

## Architecture

### 7-Step Pipeline

```
1. Prompt Validation          → Checks CAD keywords, length constraints
2. LLM → JSON Generation      → Google Gemini (gemini-2.5-flash) converts to SCL JSON
3. JSON Schema Validation     → Validates against backend/core/scl_schema.json
4. CadQuery Code Generation   → Converts JSON to Python executable
5. STEP File Export           → Subprocess runs Python, outputs .step file
6. Parameter Extraction       → Identifies editable dimensions
7. FreeCAD Integration        → Opens result (optional with --no-freecad)
```

### Directory Structure

```
backend/
├── llm_cli.py                          # Main CLI entry point
├── scl_to_step.py                      # Direct JSON→STEP converter
├── core/
│   ├── main.py                         # SynthoCadPipeline class (orchestrator)
│   ├── scl_schema.json                 # SCL schema (source of truth)
│   └── config.py                       # Path definitions
├── services/
│   ├── gemini_service.py               # Gemini REST API client
│   ├── freecad_instance_generator.py   # FreeCAD launcher
│   ├── parameter_extractor.py          # Extract editable dimensions
│   └── parameter_updater.py            # Update parameters and regenerate
├── validators/
│   ├── prompt_validator.py             # Step 1: Validate user prompt
│   └── json_validator.py               # Step 3: Validate JSON vs schema
├── api/
│   └── app.py                          # Flask REST API (future frontend integration)
└── utils/
    ├── logger.py                       # Logging setup
    └── errors.py                       # Custom error classes

templates/basic/
├── cylinder_10x20.json                 # Concrete dimension example
└── box_50x30x10.json                   # Real-world template

outputs/
├── json/                               # Generated SCL JSON files
├── py/                                 # Generated CadQuery Python code
├── step/                               # Output .step files
└── logs/                               # Pipeline logs
```

## File Roles

| File | Purpose |
|------|---------|
| `backend/llm_cli.py` | Command-line interface - user entry point |
| `backend/core/main.py` | Pipeline orchestrator (SynthoCadPipeline class) |
| `backend/services/gemini_service.py` | LLM API client (40 lines) |
| `backend/core/scl_schema.json` | JSON schema validation source |
| `.env` | API keys and model configuration |

## LLM Integration

**System Prompt Location:** Hardcoded in `backend/core/main.py` (lines 27-82)

**Model:** `gemini-2.5-flash` (from .env)

**What the LLM does:**
- Takes: user prompt + SCL schema + concrete examples
- Returns: valid SCL JSON with proper dimension scaling
- Temperature: 0.2 (balance between consistency and reasoning)
- Max tokens: 8192

**Dimension Formula (Critical):**
```
User input: "10mm radius cylinder, 20mm tall"

Sketch (0-1 normalized):
  Center: [0.5, 0.5], Radius: 0.5

Scale to real:
  sketch_scale = diameter = 2 * radius = 20.0
  extrude_depth = height / sketch_scale = 20 / 20 = 1.0
```

## Configuration

**.env file:**
```
USE_OLLAMA=false
GEMINI_API_KEY=<your-api-key>
GEMINI_MODEL=gemini-2.5-flash
```

**Get API Key:** [Google AI Studio](https://aistudio.google.com/)

## Running the Pipeline

### CLI Mode (Recommended for Testing)
```bash
python backend/llm_cli.py -p "Create a box 50mm x 30mm x 10mm"
python backend/llm_cli.py --no-freecad
```

### Direct JSON→STEP
```bash
python backend/scl_to_step.py outputs/json/sample.json
```

### With Python
```python
from backend.core.main import SynthoCadPipeline

pipeline = SynthoCadPipeline()
result = pipeline.process_from_prompt("Create a cylinder 10mm radius, 20mm tall")
print(result['step_file'])
```

## Output Files

After running, check:
- **JSON:** `outputs/json/Cylinder_10x20.json`
- **Python:** `outputs/py/Cylinder_10x20_generated.py`
- **STEP:** `outputs/step/Cylinder_10x20.step`
- **Logs:** `outputs/logs/pipeline.log`

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| 404 from Gemini | Invalid model name | Check .env GEMINI_MODEL |
| Rate limit (429) | Quota exhausted | Wait 60s or use new API key |
| JSON validation fails | Non-conforming LLM output | Check logs, adjust prompt |
| STEP generation fails | CadQuery errors | Check generated Python code |

## Future Improvements

1. **RAG System** - Vector search over data_set/ for semantic template matching
2. **More Templates** - Expand templates/basic/ with mechanical parts
3. **React Frontend** - 3D viewer + parameter editing UI
4. **MCP/VLM Validation** - Geometric correctness checking
5. **Design Persistence** - Save/load design history

## Requirements

- Python 3.10+
- `cadquery==2.4.0`
- `requests>=2.28.0`
- `python-dotenv>=1.0.0`
- `jsonschema==4.20.0`
- `numpy<2.0` (CadQuery compatibility)
- Google Gemini API key

Install:
```bash
pip install -r backend/requirements.txt
```

## License

Open source - use for learning/research.
