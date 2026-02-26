# SynthoCAD - AI-Powered CAD Generation Platform

**Convert natural language descriptions into parametric CAD models with automatic error recovery, cleanup, and FreeCAD integration.**

---

## 🚀 Quick Start

### Command Line
```bash
# Natural language to CAD
python backend/llm_cli.py -p "Create a cylinder 10mm radius, 20mm tall"

# Interactive mode
python backend/llm_cli.py
```

### Web Interface (Recommended)
```bash
# Start the server (serves both frontend and API)
cd backend
python api/app.py

# Open in browser
# http://localhost:5000
```

**Note:** The Flask backend automatically serves the frontend on port 5000. You don't need a separate frontend server.

### Web Interface (Development Mode - Optional)
```bash
# Only needed for frontend development with hot-reload
# Terminal 1: Backend API
cd backend
python api/app.py

# Terminal 2: Frontend dev server
cd frontend
python -m http.server 8000
# Open http://localhost:8000 in browser
# (Frontend will still call API at localhost:5000)
```

---

## ✨ Features

### 🎨 Generation
- **Natural Language Input**: Describe CAD models in plain English
- **JSON Input**: Direct SCL JSON schema support
- **LLM-Powered**: Google Gemini for intelligent conversion
- **Automatic Retry**: Built-in error recovery with exponential backoff
- **FreeCAD Integration**: Automatic model visualization

### ⚙️ Parameter Management
- **Extract Parameters**: Identify editable dimensions from generated code
- **Real-time Editing**: Modify and regenerate models instantly
- **Type Checking**: Validate parameter values before regeneration

### 🧹 Automatic Cleanup
- **Age-based**: Delete files older than X days
- **Count-based**: Keep only N most recent files
- **Storage Monitoring**: Real-time disk usage statistics
- **Safe Dry-run**: Preview deletions before execution

### 🔄 Error Recovery
- **Automatic Retry**: Exponential backoff for transient failures
- **Smart Detection**: Distinguishes retryable vs permanent errors
- **Rate Limit Handling**: Automatic backoff for API limits
- **History Tracking**: Monitor all retry attempts

### 📊 Monitoring
- **Success Rates**: Track generation success/failure
- **Performance Metrics**: Operation timing and statistics
- **Error Diagnostics**: Detailed failure analysis

---

## 📁 Project Structure

```
SynthoCAD/
├── frontend/                           # Web Interface
│   ├── index.html                      # Main UI (5 tabs)
│   ├── README.md                       # Frontend documentation
│   ├── css/
│   │   └── style.css                   # Responsive styling
│   └── js/
│       ├── api.js                      # API client (15+ endpoints)
│       └── app.js                      # Application logic
│
├── backend/                            # Core System
│   ├── llm_cli.py                      # CLI interface
│   ├── scl_to_step.py                  # Direct JSON converter
│   ├── requirements.txt                # Python dependencies
│   │
│   ├── api/                            # REST API
│   │   ├── app.py                      # Flask app
│   │   └── routes/
│   │       ├── generation_routes.py    # Generate endpoints
│   │       ├── parameter_routes.py     # Parameter editing
│   │       ├── viewer_routes.py        # FreeCAD control
│   │       ├── cleanup_routes.py       # Storage management
│   │       └── template_routes.py      # Template access
│   │
│   ├── core/                           # Core Logic
│   │   ├── main.py                     # Pipeline orchestrator
│   │   ├── cadquery_generator.py       # Code generation
│   │   ├── scl_schema.json             # Schema definition
│   │   └── config.py                   # Configuration
│   │
│   ├── services/                       # Business Logic
│   │   ├── gemini_service.py           # LLM integration (with retry)
│   │   ├── freecad_instance_generator.py    # FreeCAD launcher
│   │   ├── freecad_viewer_service.py   # Viewer wrapper
│   │   ├── parameter_extractor.py      # Extract params
│   │   ├── parameter_updater.py        # Update & regenerate
│   │   ├── file_cleanup_service.py     # Storage management
│   │   └── error_recovery_service.py   # Retry logic
│   │
│   ├── validators/                     # Input Validation
│   │   ├── prompt_validator.py         # Prompt checking
│   │   └── json_validator.py           # Schema validation
│   │
│   └── utils/                          # Utilities
│       ├── logger.py                   # Logging
│       └── errors.py                   # Error classes
│
├── templates/                          # SCL Templates
│   ├── basic/
│   │   ├── cylinder_10x20.json
│   │   └── box_50x30x10.json
│   ├── mechanical/
│   └── patterns/
│
├── outputs/                            # Generated Files
│   ├── json/                           # SCL JSON
│   ├── py/                             # Python code
│   ├── step/                           # STEP files
│   └── logs/                           # Log files
│
└── data_set/                           # Training/Reference Data
    └── 0000-0099/                      # CAD model dataset
```

---

## 🛠️ Installation & Setup

### 1. Prerequisites

- **Python 3.10+**
- **Git**
- **FreeCAD** (optional, for visualization)
- **Google Gemini API Key** ([Get one here](https://aistudio.google.com/))

### 2. Clone Repository

```bash
git clone <repository-url>
cd SynthoCAD
```

### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Key Dependencies:**
- `cadquery==2.4.0` - CAD kernel
- `flask>=2.3.0` - REST API
- `flask-cors>=4.0.0` - CORS support
- `requests>=2.28.0` - HTTP client
- `python-dotenv>=1.0.0` - Environment variables
- `jsonschema==4.20.0` - Schema validation
- `numpy<2.0` - CadQuery compatibility

### 4. Configure Environment

Create `.env` file in backend directory:

```env
# LLM Configuration
USE_OLLAMA=false
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Optional: Custom FreeCAD path
FREECAD_PATH=C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe
```

### 5. Start Backend API

```bash
cd backend
python api/app.py
```

Backend will run on `http://localhost:5000`

### 6. Access the Application

**The Flask backend automatically serves the frontend on port 5000. Just open:**

```
http://localhost:5000
```

**Optional: Separate Frontend Server (for development only)**

```bash
cd frontend

# Option 1: Python http server
python -m http.server 8000
# Open http://localhost:8000 (still calls API at :5000)

# Option 2: Node.js serve
npx serve
# Open http://localhost:3000

# Option 3: VS Code Live Server
# Right-click index.html -> "Open with Live Server"
```

---

## 💻 Usage Examples

### Web Interface (Recommended)

1. **Open** `http://localhost:5000` in browser
2. **Generate Tab**: Enter natural language description or JSON
3. **Parameters Tab**: Extract and modify parameters
4. **Cleanup Tab**: Manage storage and cleanup old files
5. **Monitoring Tab**: View system statistics

### Command Line Interface

```bash
# Basic generation
python backend/llm_cli.py -p "Create a box 50mm x 30mm x 10mm"

# Without FreeCAD
python backend/llm_cli.py --no-freecad -p "cylinder 20mm diameter, 50mm tall"

# Interactive mode
python backend/llm_cli.py

# Direct JSON to STEP
python backend/scl_to_step.py outputs/json/sample.json
```

### Python API

```python
from backend.core.main import SynthoCadPipeline

# Initialize pipeline
pipeline = SynthoCadPipeline()

# Generate from natural language
result = pipeline.process_from_prompt(
    "Create a cylinder 10mm radius, 20mm tall",
    open_freecad=True
)
print(f"STEP file: {result['step_file']}")
print(f"Parameters: {result['parameters']['total_count']}")

# Generate from JSON
import json
with open('model.json') as f:
    json_data = json.load(f)
result = pipeline.process_from_json(json_data, open_freecad=True)

# Extract and update parameters
params = pipeline.extract_parameters("output_generated.py")
pipeline.update_parameters("output_generated.py", {"radius": 15.0})
pipeline.regenerate_from_updated_python("output_generated.py", "output")
```

### REST API

```bash
# Generate from prompt
curl -X POST http://localhost:5000/api/v1/generate/from-prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a cylinder 10mm radius, 20mm tall", "open_freecad": true}'

# Extract parameters
curl http://localhost:5000/api/v1/parameters/extract/Cylinder_10x20_generated.py

# Get storage statistics
curl http://localhost:5000/api/v1/cleanup/stats

# Run cleanup (dry run)
curl -X POST http://localhost:5000/api/v1/cleanup/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_days": 30, "dry_run": true}'

# Check system health
curl http://localhost:5000/api/v1/health
```

---

## 📡 API Endpoints

### Generation
```
POST   /api/v1/generate/from-prompt      # Generate from natural language
POST   /api/v1/generate/from-json        # Generate from JSON
POST   /api/v1/generate/validate-prompt  # Validate prompt
```

### Parameters
```
GET    /api/v1/parameters/extract/<file>       # Extract parameters
POST   /api/v1/parameters/update/<file>        # Update parameters
POST   /api/v1/parameters/regenerate/<file>    # Update & regenerate
```

### FreeCAD Viewer
```
GET    /api/v1/viewer/check      # Check FreeCAD installation
POST   /api/v1/viewer/open       # Open STEP in FreeCAD
POST   /api/v1/viewer/reload     # Reload STEP file
```

### Cleanup & Monitoring
```
GET    /api/v1/cleanup/stats              # Storage statistics
POST   /api/v1/cleanup/cleanup            # Run cleanup
POST   /api/v1/cleanup/cleanup/by-age     # Cleanup by age
POST   /api/v1/cleanup/cleanup/by-count   # Cleanup by count
DELETE /api/v1/cleanup/<model>            # Delete specific model
GET    /api/v1/cleanup/retry-stats        # Retry statistics
```

### Templates
```
GET    /api/v1/templates         # List all templates
GET    /api/v1/templates/<name>  # Get specific template
```

### Health
```
GET    /api/v1/health            # API health check
```

---

## ⚙️ Configuration

### Backend Config (`backend/core/config.py`)

```python
# Execution
EXECUTION_TIMEOUT = 60  # seconds

# Cleanup
CLEANUP_ENABLED = True
CLEANUP_MAX_AGE_DAYS = 30
CLEANUP_MAX_FILES_PER_TYPE = 100
CLEANUP_AUTO_RUN = False  # Set True for production

# Retry/Error Recovery
RETRY_ENABLED = True
RETRY_MAX_ATTEMPTS = 3
RETRY_INITIAL_DELAY = 1.0  # seconds
RETRY_MAX_DELAY = 60.0
RETRY_EXPONENTIAL_BASE = 2.0
```

### Frontend Config (`frontend/js/api.js`)

```javascript
const API_BASE_URL = 'http://localhost:5000/api/v1';
```

---

## 🏗️ Architecture

### Complete Pipeline

```
1. Prompt Validation          → CAD keywords, length constraints
2. LLM → JSON Generation      → Google Gemini converts to SCL JSON (with retry)
3. JSON Schema Validation     → Validates against scl_schema.json
4. CadQuery Code Generation   → JSON to executable Python
5. STEP File Export           → Subprocess execution (with retry)
6. Parameter Extraction       → Identify editable dimensions
7. FreeCAD Integration        → Auto-open in viewer
8. Error Recovery             → Automatic retry with backoff
9. Cleanup Management         → Storage optimization
```

### Technology Stack

**Backend:**
- Python 3.10+
- Flask REST API
- Google Gemini API
- CadQuery 2.4.0
- FreeCAD (optional viewer)

**Frontend:**
- Vanilla JavaScript (no frameworks)
- Modern CSS with responsive design
- REST API integration
- Real-time updates

---

## 📊 LLM Integration Details

**Model:** Google Gemini 2.5 Flash

**What it does:**
- Converts natural language → SCL JSON
- Uses schema + concrete examples for guidance
- Temperature: 0.2 (balance consistency/reasoning)
- Max tokens: 8192
- **Automatic retry** on failures with exponential backoff

**Dimension Scaling Formula:**
```
User: "10mm radius cylinder, 20mm tall"

Sketch (normalized 0-1):
  Center: [0.5, 0.5], Radius: 0.5

Scale to real dimensions:
  sketch_scale = diameter = 2 * radius = 20.0
  extrude_depth = height / sketch_scale = 20 / 20 = 1.0

Result dimensions:
  length: 20.0, width: 20.0, height: 20.0
```

**System Prompt Location:** `backend/core/main.py` (lines 27-82)

---

## 📝 Output Files

After generation, check:

```
outputs/
├── json/
│   └── Cylinder_10x20.json         # Generated SCL JSON
├── py/
│   └── Cylinder_10x20_generated.py # CadQuery Python code
├── step/
│   └── Cylinder_10x20.step         # Final STEP file
└── logs/
    ├── pipeline_YYYYMMDD.log       # Pipeline logs
    └── api_YYYYMMDD.log            # API request logs
```

---

## 🔧 Error Handling & Recovery

### Automatic Retry

The system automatically retries on:
- Connection errors
- Timeouts  
- Rate limits (429)
- Server errors (500, 502, 503, 504)
- Temporary resource issues

**Retry Behavior:**
- Attempt 1: Immediate
- Attempt 2: Wait 1.0s
- Attempt 3: Wait 2.0s
- Max attempts: 3 (configurable)

### Manual Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| Backend offline | API not running | Start with `python backend/api/app.py` |
| 404 from Gemini | Invalid model name | Check `.env` GEMINI_MODEL |
| Rate limit (429) | Quota exhausted | Wait or use new API key (auto-retry enabled) |
| JSON validation fails | Non-conforming output | Check logs, adjust prompt |
| STEP generation fails | CadQuery errors | Check generated Python code |
| FreeCAD not opening | Not installed | Install FreeCAD or set FREECAD_PATH |
| CORS errors | Different ports | Backend handles CORS automatically |

**View Logs:**
```bash
tail -f outputs/logs/pipeline_*.log
tail -f outputs/logs/api_*.log
```

**Check Health:**
```bash
curl http://localhost:5000/api/v1/health
curl http://localhost:5000/api/v1/viewer/check
```

---

## 🧪 Testing

### Test Generation
```bash
# Test CLI
python backend/llm_cli.py -p "Create a cylinder 20mm diameter, 50mm tall"

# Test API
python backend/api/app.py &
curl -X POST http://localhost:5000/api/v1/generate/from-prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a box 50x30x10mm"}'
```

### Test Cleanup
```bash
# Dry run (preview only)
curl -X POST http://localhost:5000/api/v1/cleanup/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_days": 7, "dry_run": true}'
```

### Test Error Recovery
```python
from backend.services.error_recovery_service import ErrorRecoveryService

service = ErrorRecoveryService()
stats = service.get_retry_statistics()
print(f"Success rate: {stats['success_rate']}%")
```

---

## 📚 Documentation

- **Frontend Guide**: [frontend/README.md](frontend/README.md) - Complete UI documentation
- **SCL Schema**: [backend/core/scl_schema.json](backend/core/scl_schema.json) - Schema definition
- **API Documentation**: See endpoint descriptions above
- **Templates**: [templates/](templates/) - Example models

---

## 🎯 Features in Detail

### ✅ Completed Features

1. ✅ **Natural Language Generation** - LLM-powered CAD creation
2. ✅ **JSON Schema Validation** - Robust input validation
3. ✅ **Parameter Extraction** - Automatic dimension detection
4. ✅ **Parameter Editing** - Real-time model updates
5. ✅ **FreeCAD Integration** - Automatic visualization
6. ✅ **Web Interface** - Full-featured frontend
7. ✅ **REST API** - Complete backend API
8. ✅ **Automatic Cleanup** - Storage management
9. ✅ **Error Recovery** - Retry with exponential backoff
10. ✅ **Monitoring** - Statistics and diagnostics

### 🚧 Future Enhancements

1. **RAG System** - Vector search over data_set/ for semantic template matching
2. **More Templates** - Expand templates library with mechanical parts
3. **3D Preview** - Browser-based model visualization
4. **MCP/VLM Validation** - Geometric correctness checking
5. **Export Formats** - STL, IGES, BREP, OBJ support
6. **Authentication** - User accounts and API keys
7. **Collaboration** - Real-time multi-user editing
8. **Mobile App** - iOS/Android support
9. **Docker** - Containerized deployment
10. **CI/CD** - Automated testing and deployment

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Template library expansion
- New CAD features
- UI/UX enhancements
- Documentation
- Test coverage
- Performance optimization

---

## 📄 License

Open source - use for learning/research.

---

## 🙏 Acknowledgments

- **CadQuery** - Python CAD kernel
- **FreeCAD** - Open-source CAD platform
- **Google Gemini** - LLM API
- **Flask** - Web framework

---

## 📞 Support & Contact

- **Issues**: Report bugs and feature requests
- **Logs**: Check `outputs/logs/` for debugging
- **Health Check**: `http://localhost:5000/api/v1/health`
- **Application**: `http://localhost:5000`

**System Status Indicators:**
- 🟢 Backend: Online
- 🟢 FreeCAD: Ready
- 🟡 Generating...
- 🔴 Error: Check logs

---

## 🚀 Quick Reference

```bash
# Start server (serves both frontend and API)
cd backend
python api/app.py

# Generate model (CLI)
python backend/llm_cli.py -p "cylinder 20mm x 50mm"

# Generate model (API)
curl -X POST http://localhost:5000/api/v1/generate/from-prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "cylinder 20mm x 50mm"}'

# View stats
curl http://localhost:5000/api/v1/cleanup/stats

# Open browser
# Windows: start http://localhost:5000
# Mac: open http://localhost:5000
# Linux: xdg-open http://localhost:5000
```

---

**Happy CAD Generation! 🔧✨**
