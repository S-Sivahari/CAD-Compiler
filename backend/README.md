# SynthoCAD Backend Structure

## Directory Organization

```
backend/
├── api/
│   ├── routes/
│   │   ├── generation_routes.py    # Prompt & JSON generation endpoints
│   │   ├── parameter_routes.py     # Parameter extraction/update endpoints
│   │   ├── template_routes.py      # Template listing/loading endpoints
│   │   └── edit_routes.py          # STEP upload, preview & editing endpoints
│   ├── middleware/                 # Future: auth, rate limiting
│   └── app.py                      # Flask app initialization & static routes
│
├── core/
│   ├── cadquery_generator.py       # JSON → CadQuery Python converter
│   ├── main.py                     # SynthoCadPipeline orchestrator
│   ├── scl_schema.json             # SCL JSON schema
│   └── config.py                   # Configuration paths (incl. PREVIEWS_DIR)
│
├── step_editor/
│   ├── step_analyzer.py            # Exact geometry extraction (cylinders, planes, cones, bbox)
│   ├── step_renderer.py            # 7-angle annotated PNG renderer
│   └── edit_pipeline.py            # Analyze → LLM → parse → generate STEP
│
├── services/
│   ├── gemini_service.py           # Google Gemini LLM wrapper
│   ├── ollama_service.py           # Local Ollama LLM wrapper
│   ├── parameter_extractor.py      # Extract parameters from Python files
│   └── parameter_updater.py        # Update Python files with new values
│
├── validators/
│   ├── json_validator.py           # Validate JSON against schema
│   └── prompt_validator.py         # Validate user prompts
│
├── rag/                    # RAG System (Vector DB, Ingestion, Query)
│   ├── db.py               # ChromaDB Client
│   ├── ingest.py           # Data Ingestion Script
│   └── query.py            # Retrieval Interface
│
├── scripts/                # Utility Scripts
│   └── description_generator.py  # RAG description generator
│
├── utils/
│   ├── errors.py                   # Custom error classes
│   └── logger.py                   # Logging configuration
│
├── outputs/                # Generated artefacts (git-ignored)
│   ├── step/               # Generated STEP files
│   ├── py/                 # Generated CadQuery Python scripts
│   ├── json/               # Generated SCL JSON files
│   └── previews/           # 7-angle PNG renders (<stem>/<view>.png)
│
└── requirements.txt                # Python dependencies
```

## Workflow

### Standard Generation Pipeline

1. **User Input Validation**
   - `prompt_validator.py` checks prompt quality
   - Returns errors or suggests templates if invalid

2. **JSON Generation** (LLM integration)
   - Converts prompt to SCL JSON
   - Validates with `json_validator.py`
   - If errors, retry with LLM

3. **RAG System Setup (Prerequisite)**
   - **Data**: Extract `batches.zip` to `backend/scripts/`.
   - **Descriptions**: Run `python scripts/description_generator.py`.
   - **Ingestion**: Run `python -m rag.ingest` (Index descriptions & JSONs into ChromaDB).
   - **Query Test**: Run `python -m rag.query "your prompt"` to verify retrieval.

4. **RAG Retrieval**
   - User prompt → `rag/query.py` → Retrieved JSON Template

5. **Code Generation**
   - `cadquery_generator.py` converts JSON → Python
   - Saves to `outputs/py/`

6. **Execution**
   - Executes Python file
   - Generates STEP file in `outputs/step/`

7. **Parameter Management**
   - `parameter_extractor.py` extracts editable values
   - Frontend displays as markdown
   - User changes values
   - `parameter_updater.py` updates Python file
   - Re-execute to generate new STEP

8. **FreeCAD Integration**
   - `freecad_connector.py` opens/reloads STEP files
   - Macros for automation

### STEP Edit Pipeline

1. **Upload** — user uploads an existing `.step` file via `POST /api/v1/edit/preview`
2. **Geometric Analysis** — `step_analyzer.py` extracts cylinders, planes, cones, bounding box, and assigns feature IDs
3. **7-Angle Render** — `step_renderer.render_multiview()` saves 7 labeled PNGs to `outputs/previews/<stem>/`
4. **Edit Request** — user writes a natural-language change referencing feature IDs; frontend posts to `POST /api/v1/edit/from-step`
5. **LLM Synthesis** — `edit_pipeline.py` builds a structured prompt (geometry report + user intent) and calls Gemini or Ollama
6. **SCL Parse** — LLM JSON response is parsed and validated
7. **STEP Generation** — `SynthoCadPipeline.process_from_json()` generates a new STEP file via CadQuery

## API Endpoints

### Generation
- `POST /api/v1/generate/validate-prompt` - Validate user prompt
- `POST /api/v1/generate/from-prompt` - Generate from prompt (LLM + RAG)
- `POST /api/v1/generate/from-json` - Generate from SCL JSON

### Parameters
- `GET /api/v1/parameters/extract/<filename>` - Extract parameters
- `POST /api/v1/parameters/update/<filename>` - Update parameters

### STEP Preview & Editing
- `POST /api/v1/edit/preview` - Upload STEP → analyze geometry + render 7 annotated views
- `POST /api/v1/edit/from-step` - Upload STEP + prompt → generate edited STEP file
- `GET /outputs/previews/<stem>/<view>.png` - Serve rendered view images

### Templates
- `GET /api/v1/templates/list` - List all templates
- `GET /api/v1/templates/<category>/<id>` - Get specific template

### Health
- `GET /api/v1/health` - API health check
