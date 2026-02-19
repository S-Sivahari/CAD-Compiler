from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"
FREECAD_DIR = BASE_DIR / "freecad"

PY_OUTPUT_DIR = OUTPUT_DIR / "py"
STEP_OUTPUT_DIR = OUTPUT_DIR / "step"
JSON_OUTPUT_DIR = OUTPUT_DIR / "json"
LOGS_DIR = OUTPUT_DIR / "logs"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
PREVIEWS_DIR = OUTPUT_DIR / "previews"

SCHEMA_PATH = BACKEND_DIR / "core" / "scl_schema.json"

for dir_path in [PY_OUTPUT_DIR, STEP_OUTPUT_DIR, JSON_OUTPUT_DIR, LOGS_DIR, UPLOAD_DIR, PREVIEWS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

PROMPT_MIN_LENGTH = 10
PROMPT_MAX_LENGTH = 5000

EXECUTION_TIMEOUT = 60

SUPPORTED_TEMPLATES = [
    "cylinder", "box", "tube", "l_bracket", "flange", "shaft",
    "hex_bolt", "socket_head_cap_screw", "flat_head_screw", "button_head_screw",
    "set_screw", "hex_nut", "wing_nut", "t_nut",
    "flat_washer", "lock_washer", "fender_washer",
    "dowel_pin", "shoulder_bolt", "retaining_ring",
    "ball_bearing", "spur_gear", "threaded_rod",
    "rigid_coupling", "sleeve_bushing", "shaft_collar_split",
    "flanged_bushing", "timing_pulley", "lead_screw",
    "leveling_foot", "swivel_caster", "rigid_caster",
    "angle_bracket", "corner_gusset", "square_tubing",
    "end_cap", "t_slot_extrusion", "din_rail",
    "pcb_standoff", "terminal_block",
    "elbow_fitting", "hose_clamp", "o_ring",
    "linear_array", "bolt_circle",
    "worm_gear_set", "geneva_drive", "cv_joint_housing",
    "helical_gear", "spline_shaft", "ball_screw_nut",
    "hydraulic_manifold_block", "heat_exchanger_tube_sheet",
    "centrifugal_impeller", "venturi_nozzle",
    "plummer_block_housing", "vise_jaw", "indexing_plate",
    "drill_jig_bushing_carrier",
    "nema_motor_mount", "lathe_tailstock_body", "electronics_enclosure_ip67",
    "knuckle_joint", "universal_coupling_yoke", "rod_end_bearing_housing",
]

TEMPLATE_CATEGORIES = {
    "basic": ["cylinder", "box", "tube"],
    "mechanical": ["flange", "l_bracket", "ball_bearing", "spur_gear", "threaded_rod",
                    "rigid_coupling", "sleeve_bushing", "shaft_collar_split", "flanged_bushing",
                    "timing_pulley", "lead_screw", "leveling_foot", "swivel_caster", "rigid_caster"],
    "fasteners": ["hex_bolt", "socket_head_cap_screw", "flat_head_screw", "button_head_screw",
                   "set_screw", "hex_nut", "wing_nut", "t_nut", "flat_washer", "lock_washer",
                   "fender_washer", "dowel_pin", "shoulder_bolt", "retaining_ring"],
    "structural": ["angle_bracket", "corner_gusset", "square_tubing", "end_cap",
                    "t_slot_extrusion", "din_rail"],
    "electrical": ["pcb_standoff", "terminal_block"],
    "piping": ["elbow_fitting", "hose_clamp", "o_ring"],
    "patterns": ["linear_array", "bolt_circle"],
    "power_transmission": ["worm_gear_set", "geneva_drive", "cv_joint_housing",
                           "helical_gear", "spline_shaft", "ball_screw_nut"],
    "fluid_power": ["hydraulic_manifold_block", "heat_exchanger_tube_sheet",
                     "centrifugal_impeller", "venturi_nozzle"],
    "tooling": ["plummer_block_housing", "vise_jaw", "indexing_plate",
                "drill_jig_bushing_carrier"],
    "enclosures": ["nema_motor_mount", "lathe_tailstock_body", "electronics_enclosure_ip67"],
    "linkages": ["knuckle_joint", "universal_coupling_yoke", "rod_end_bearing_housing"],
}

# Cleanup Configuration
CLEANUP_ENABLED = True
CLEANUP_MAX_AGE_DAYS = 30  # Delete files older than 30 days
CLEANUP_MAX_FILES_PER_TYPE = 100  # Keep max 100 files of each type
CLEANUP_AUTO_RUN = False  # Auto cleanup on startup (set True for production)

# LLM Configuration
LLM_PROVIDER = "gemini"  # Options: "gemini", "ollama"
OLLAMA_LLM_MODEL = "qwen2.5:7b"  # Recommended for CPU: qwen2.5:7b, llama3.1:8b
OLLAMA_URL = "http://localhost:11434/api/generate"

# Retry/Error Recovery Configuration
RETRY_ENABLED = True
RETRY_MAX_ATTEMPTS = 3  # Maximum retry attempts for LLM calls
RETRY_INITIAL_DELAY = 1.0  # Initial delay in seconds
RETRY_MAX_DELAY = 60.0  # Maximum delay between retries
RETRY_EXPONENTIAL_BASE = 2.0  # Exponential backoff base
