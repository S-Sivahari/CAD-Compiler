import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import logging

sys.path.append(str(Path(__file__).parent.parent))

from validators.prompt_validator import PromptValidator
from validators.json_validator import validate_json, validate_json_detailed, repair_json
from core.cadquery_generator import CadQueryGenerator
from services.parameter_extractor import ParameterExtractor
from services.parameter_updater import ParameterUpdater
from services.freecad_instance_generator import FreeCADInstanceGenerator
from services.gemini_service import call_gemini
from services.error_recovery_service import ErrorRecoveryService, RetryConfig, RetryableError
from services.template_index import TemplateIndex
from utils.errors import *
from utils.logger import pipeline_logger
from core import config


LLM_SYSTEM_PROMPT = """You are an expert parametric CAD engineer. Convert natural language descriptions into valid SCL (SynthoCAD Language) JSON.

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations, no comments
2. Always include "units" field (default: "mm")
3. First part (part_1) MUST use "NewBodyFeatureOperation"
4. Parts numbered sequentially: part_1, part_2, part_3...
5. Each part needs EXACTLY ONE of: sketch+extrusion, revolve_profile+revolve, or hole_feature
6. Sketch coordinates are normalized (0.0-1.0), then sketch_scale converts to real mm

=== DIMENSION FORMULA ===

CYLINDER (e.g., "10mm radius, 20mm tall"):
  sketch: circle Center [0.5, 0.5], Radius 0.5
  sketch_scale = diameter = 2 * 10 = 20.0
  extrude_depth_towards_normal = height / sketch_scale = 20 / 20 = 1.0
  Description: length=20, width=20, height=20

BOX (e.g., "50mm x 30mm x 10mm"):
  sketch: rectangle with aspect ratio preserved
    [0,0] -> [1.0,0] -> [1.0,0.6] -> [0,0.6] -> [0,0]  (30/50=0.6)
  sketch_scale = longest_dimension = 50.0
  extrude_depth = 10 / 50 = 0.2
  Description: length=50, width=30, height=10

HOLLOW CYLINDER / TUBE (e.g., "outer_d=30, inner_d=20, h=40"):
  sketch face_1:
    loop_1 (outer): circle Center [0.5,0.5], Radius 0.5
    loop_2 (inner): circle Center [0.5,0.5], Radius 0.333  (inner_d/outer_d/2 = 20/30/2)
  sketch_scale = outer_diameter = 30.0
  extrude_depth = 40 / 30 = 1.333

PLATE WITH HOLES:
  sketch face_1:
    loop_1 (outer rectangle): 4 lines
    loop_2 (hole 1): circle
    loop_3 (hole 2): circle
  Inner loops (loop_2+) create cutouts automatically

=== MULTI-PART MODELS ===

For complex shapes, decompose into multiple parts with boolean operations:
- part_1: Base body (NewBodyFeatureOperation)
- part_2+: Added features (JoinFeatureOperation) or cuts (CutFeatureOperation)

Example - "Plate with a boss and a hole":
  part_1: Rectangular plate (NewBody)
  part_2: Cylindrical boss on top (Join, translate Z to plate height)
  part_3: Through hole (Cut)

=== COORDINATE SYSTEM ===

Each part has:
- Euler Angles [X, Y, Z]: rotation in degrees (typically multiples of 90)
- Translation Vector [X, Y, Z]: position offset in real mm

Common transformations:
- [0,0,0]: No rotation (feature on XY plane)
- [0,0,-90]: Rotate 90 around Z (feature on side)
- [-90,0,0]: Rotate 90 around X (feature on front/back)
- Translation [0,0,height]: Place feature on top of base

=== HOLE FEATURES ===

For holes, use hole_feature instead of manual circle+cut:
{
  "hole_feature": {
    "hole_type": "Simple",    // or "Counterbore" or "Countersink"
    "diameter": 5.5,
    "depth": 10.0,
    "position": [x, y]
  }
}

For bolt hole patterns, combine hole_feature with pattern:
{
  "hole_feature": { "hole_type": "Simple", "diameter": 5.5, "depth": 10, "position": [30, 0] },
  "pattern": { "type": "polar", "count": 6, "center": [0,0,0], "total_angle": 360 }
}

=== PATTERNS ===

Linear: { "type": "linear", "count": 4, "spacing": 20, "direction": [1,0,0] }
Polar: { "type": "polar", "count": 6, "center": [0,0,0], "total_angle": 360, "axis": [0,0,1] }

=== POST-PROCESSING ===

Fillets and chamfers in post_processing array:
"post_processing": [
  {"radius": 2.0, "edge_selector": ">Z"},     // fillet top edges
  {"distance": 1.0, "edge_selector": "<Z"}     // chamfer bottom edges
]

Edge selectors: "all", ">Z" (top), "<Z" (bottom), ">X", "<X", ">Y", "<Y", "|Z" (parallel to Z)

=== REQUIRED JSON STRUCTURE ===

{
  "final_name": "Part_Name",
  "final_shape": "Shape_Category",
  "units": "mm",
  "parts": {
    "part_1": {
      "coordinate_system": {
        "Euler Angles": [0.0, 0.0, 0.0],
        "Translation Vector": [0.0, 0.0, 0.0]
      },
      "sketch": {
        "face_1": {
          "loop_1": { ... sketch entities ... }
        }
      },
      "extrusion": {
        "extrude_depth_towards_normal": 1.0,
        "extrude_depth_opposite_normal": 0.0,
        "sketch_scale": 20.0,
        "operation": "NewBodyFeatureOperation"
      },
      "description": {
        "name": "Part Name",
        "shape": "Cylinder",
        "length": 20.0,
        "width": 20.0,
        "height": 20.0
      }
    }
  }
}

SKETCH ENTITIES:
- Circle: {"Center": [x, y], "Radius": r}
- Line: {"Start Point": [x1, y1], "End Point": [x2, y2]}
- Arc: {"Start Point": [x1, y1], "Mid Point": [xm, ym], "End Point": [x2, y2]}

LOOPS must be closed: last entity End Point = first entity Start Point
Inner loops (loop_2+) define holes/cutouts in the face

Output ONLY raw JSON starting with { and ending with }"""


class SynthoCadPipeline:

    def __init__(self):
        self.prompt_validator = PromptValidator()
        self.generator = CadQueryGenerator
        self.param_extractor = ParameterExtractor()
        self.param_updater = ParameterUpdater()
        self.freecad = FreeCADInstanceGenerator()
        self.logger = pipeline_logger
        self.template_index = TemplateIndex(config.TEMPLATES_DIR)

        self.error_recovery = ErrorRecoveryService(logger=pipeline_logger)
        self.retry_config = RetryConfig(
            max_attempts=config.RETRY_MAX_ATTEMPTS if hasattr(config, "RETRY_MAX_ATTEMPTS") else 3,
            initial_delay=config.RETRY_INITIAL_DELAY if hasattr(config, "RETRY_INITIAL_DELAY") else 1.0,
            max_delay=config.RETRY_MAX_DELAY if hasattr(config, "RETRY_MAX_DELAY") else 60.0,
            exponential_base=config.RETRY_EXPONENTIAL_BASE if hasattr(config, "RETRY_EXPONENTIAL_BASE") else 2.0,
        )

    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        self.logger.info("Step 1: Validating prompt")
        is_valid, error_msg, metadata = self.prompt_validator.validate(prompt)

        if not is_valid:
            self.logger.error(f"Prompt validation failed: {error_msg}")
            raise PromptValidationError(error_msg or "Validation failed", metadata)

        self.logger.info("Prompt validated successfully")

        prompt_lower = prompt.lower()
        cad_keyword_matches = sum(1 for kw in self.prompt_validator.cad_keywords if kw in prompt_lower)
        confidence = min(0.95, 0.5 + (cad_keyword_matches * 0.1))

        suggestions = self.prompt_validator.suggest_templates(prompt)

        return {
            "valid": True,
            "confidence": round(confidence, 2),
            "suggestions": suggestions,
            "metadata": metadata or {},
        }

    def generate_json_from_prompt(self, prompt: str) -> Dict[str, Any]:
        """Step 2: Generate SCL JSON from natural language using LLM."""
        self.logger.info("Step 2: Generating JSON from prompt via LLM")

        system_prompt = LLM_SYSTEM_PROMPT

        templates = self.template_index.find_relevant_templates(prompt, max_results=3)

        examples_text = ""
        if templates:
            examples_text = "\n\nREFERENCE EXAMPLES (use these as guides for correct structure and scaling):\n"
            for i, t in enumerate(templates[:3], 1):
                clean = {k: v for k, v in t.items() if not k.startswith("_")}
                examples_text += f"\nExample {i}:\n{json.dumps(clean, indent=2)}\n"

        full_prompt = f"{system_prompt}{examples_text}\n\nUSER REQUEST: {prompt}\n\nGenerate the SCL JSON output:"

        try:
            response_text = call_gemini(full_prompt, max_tokens=8192, temperature=0.15)

            cleaned_text = self._strip_markdown_json(response_text)

            json_data = json.loads(cleaned_text)

            json_data, repairs = repair_json(json_data)
            if repairs:
                self.logger.info(f"Auto-repaired JSON: {repairs}")

            validation = validate_json_detailed(json_data)
            if not validation["valid"]:
                self.logger.warning(f"JSON validation issues: {validation['errors']}")

                self.logger.info("Attempting LLM retry with error feedback...")
                retry_prompt = (
                    f"{system_prompt}\n\n"
                    f"USER REQUEST: {prompt}\n\n"
                    f"Your previous output had these errors:\n"
                    + "\n".join(f"- {e}" for e in validation["errors"])
                    + "\n\nFix ALL errors and output corrected JSON:"
                )
                response_text = call_gemini(retry_prompt, max_tokens=8192, temperature=0.1)
                cleaned_text = self._strip_markdown_json(response_text)
                json_data = json.loads(cleaned_text)
                json_data, repairs = repair_json(json_data)

                validation2 = validate_json_detailed(json_data)
                if not validation2["valid"]:
                    self.logger.warning(f"Retry still has errors: {validation2['errors']}")

            if validation.get("warnings"):
                self.logger.info(f"JSON warnings: {validation['warnings']}")

            self.logger.info(f"LLM generated JSON for: {json_data.get('final_name', 'Unknown')}")
            return json_data

        except json.JSONDecodeError as e:
            self.logger.error(f"LLM returned invalid JSON: {e}")
            raise JSONGenerationError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            raise JSONGenerationError(f"LLM generation failed: {str(e)}")

    def _build_llm_system_prompt(self) -> str:
        return LLM_SYSTEM_PROMPT

    def _find_relevant_templates(self, prompt: str) -> list:
        """Load template examples relevant to the user's prompt using template index."""
        return self.template_index.find_relevant_templates(prompt, max_results=3)

    def _strip_markdown_json(self, text: str) -> str:
        """Strip markdown code blocks and extract JSON from LLM response."""
        text = text.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]
            for i, line in enumerate(lines):
                if line.strip() == "```":
                    lines = lines[:i]
                    break
            text = "\n".join(lines).strip()

        if not text.startswith("{"):
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                text = match.group()

        return text

    def validate_json(self, json_data: Dict) -> bool:
        self.logger.info("Step 3: Validating JSON against SCL schema")

        validation = validate_json_detailed(json_data)

        if not validation["valid"]:
            error_msg = "; ".join(validation["errors"][:5])
            self.logger.error(f"JSON validation failed: {error_msg}")
            raise JSONValidationError(f"JSON validation failed: {error_msg}")

        if validation.get("warnings"):
            for w in validation["warnings"]:
                self.logger.warning(f"JSON warning: {w}")

        self.logger.info("JSON validated successfully")
        return True

    def generate_cadquery_code(self, json_data: Dict, output_name: str) -> str:
        """Step 4: Generate CadQuery Python code from SCL JSON."""
        self.logger.info("Step 4: Generating CadQuery Python code")

        try:
            generator = self.generator(json_data, output_name)
            code = generator.generate()

            py_file = config.PY_OUTPUT_DIR / f"{output_name}_generated.py"
            with open(py_file, "w") as f:
                f.write(code)

            self.logger.info(f"Generated Python code: {py_file}")
            return str(py_file)

        except Exception as e:
            raise CodeGenerationError(f"Code generation failed: {str(e)}")

    def execute_cadquery_code(self, py_file: str, output_name: str) -> str:
        """Step 5: Execute CadQuery code with retry logic."""
        self.logger.info("Step 5: Executing CadQuery code to generate STEP")

        def _execute():
            py_path = Path(py_file)
            if not py_path.is_absolute():
                py_path = config.BASE_DIR / py_path

            if not py_path.exists():
                raise ExecutionError(f"Python file not found: {py_file}")

            step_file = config.STEP_OUTPUT_DIR / f"{output_name}.step"

            result = subprocess.run(
                [sys.executable, str(py_path)],
                capture_output=True,
                text=True,
                timeout=config.EXECUTION_TIMEOUT,
                cwd=config.STEP_OUTPUT_DIR,
            )

            if result.returncode != 0:
                self.logger.error(f"Execution failed: {result.stderr}")
                if "temporarily" in result.stderr.lower() or "resource" in result.stderr.lower():
                    raise RetryableError(f"Python execution failed (retryable): {result.stderr}")
                raise ExecutionError(f"Python execution failed: {result.stderr}")

            if not step_file.exists():
                raise ExecutionError("STEP file was not created")

            self.logger.info(f"STEP file generated: {step_file}")
            return str(step_file)

        try:
            if hasattr(config, "RETRY_ENABLED") and config.RETRY_ENABLED:
                return self.error_recovery.execute_with_retry(
                    _execute, config=self.retry_config, operation_name="cadquery_execution"
                )
            else:
                return _execute()

        except subprocess.TimeoutExpired:
            raise ExecutionError(f"Execution timeout ({config.EXECUTION_TIMEOUT}s)")
        except RetryableError as e:
            raise ExecutionError(f"Execution error (retries exhausted): {str(e)}")
        except Exception as e:
            raise ExecutionError(f"Execution error: {str(e)}")

    def extract_parameters(self, py_file: str) -> Dict[str, Any]:
        self.logger.info("Step 6: Extracting editable parameters")

        try:
            params_data = self.param_extractor.extract_from_python(py_file)
            markdown = self.param_extractor.generate_markdown(params_data)

            self.logger.info(f"Extracted {params_data['total_count']} parameters")

            return {
                "parameters": params_data["parameters"],
                "markdown": markdown,
                "total_count": params_data["total_count"],
            }

        except Exception as e:
            self.logger.error(f"Parameter extraction failed: {str(e)}")
            return {
                "parameters": [],
                "markdown": "# No parameters found",
                "total_count": 0,
            }

    def open_in_freecad(self, step_file: str) -> bool:
        self.logger.info("Step 7: Opening STEP file in FreeCAD")

        try:
            self.freecad.open_step_file(step_file, async_mode=True)
            self.logger.info("FreeCAD opened successfully")
            return True

        except Exception as e:
            self.logger.warning(f"FreeCAD open failed: {str(e)}")
            return False

    def update_parameters(self, py_file: str, parameters: Dict[str, float]) -> str:
        self.logger.info(f"Step 8: Updating {len(parameters)} parameters")

        try:
            for param_name, value in parameters.items():
                is_valid, error_msg = self.param_updater.validate_parameter_value(param_name, value)
                if not is_valid:
                    raise ParameterUpdateError(f"Invalid value for {param_name}: {error_msg or 'Invalid value'}")

            self.param_updater.update_python_file(py_file, parameters)
            self.logger.info("Parameters updated successfully")
            return py_file

        except Exception as e:
            self.logger.error(f"Parameter update failed: {str(e)}")
            raise ParameterUpdateError(f"Failed to update parameters: {str(e)}")

    def regenerate_from_updated_python(self, py_file: str, output_name: str, open_freecad: bool = True) -> str:
        self.logger.info("Step 9: Regenerating STEP from updated Python")

        py_path = Path(py_file)
        if not py_path.is_absolute():
            py_path = config.BASE_DIR / py_path

        content = py_path.read_text()
        import re as re_mod
        content = re_mod.sub(
            r"cq\.exporters\.export\(result,\s*['\"][\w.-]+\.step['\"]\)",
            f"cq.exporters.export(result, '{output_name}.step')",
            content,
        )
        py_path.write_text(content)

        step_file = self.execute_cadquery_code(str(py_path), output_name)

        if open_freecad:
            self.freecad.reload_step_file(step_file)

        return step_file

    def process_from_json(self, json_data: Dict, output_name: Optional[str] = None, open_freecad: bool = True) -> Dict[str, Any]:

        try:
            json_data, repairs = repair_json(json_data)
            if repairs:
                self.logger.info(f"Auto-repaired input JSON: {repairs}")

            self.validate_json(json_data)

            if not output_name:
                output_name = json_data.get("final_name", "output")
                if not output_name or output_name.strip() == "":
                    output_name = "output"

            output_name = output_name.replace(" ", "_").replace("/", "_")

            json_file = config.JSON_OUTPUT_DIR / f"{output_name}.json"
            with open(json_file, "w") as f:
                json.dump(json_data, f, indent=2)
            self.logger.info(f"Saved JSON: {json_file}")

            py_file = self.generate_cadquery_code(json_data, output_name)

            step_file = self.execute_cadquery_code(py_file, output_name)

            params_result = self.extract_parameters(py_file)

            if open_freecad:
                freecad_opened = self.open_in_freecad(step_file)
            else:
                freecad_opened = False

            return {
                "status": "success",
                "json_file": str(json_file),
                "py_file": py_file,
                "step_file": step_file,
                "parameters": params_result,
                "freecad_opened": freecad_opened,
            }

        except SynthoCadError as e:
            self.logger.error(f"Pipeline failed: {e.message}")
            return {"status": "error", "error": e.to_dict()}
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return {"status": "error", "error": {"code": "UNKNOWN_ERROR", "message": str(e)}}

    def process_from_prompt(self, prompt: str, open_freecad: bool = True) -> Dict[str, Any]:

        try:
            self.validate_prompt(prompt)

            json_data = self.generate_json_from_prompt(prompt)

            return self.process_from_json(json_data, open_freecad=open_freecad)

        except NotImplementedError as e:
            return {"status": "error", "error": {"code": "NOT_IMPLEMENTED", "message": str(e)}}
        except SynthoCadError as e:
            return {"status": "error", "error": e.to_dict()}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <json_file>")
        sys.exit(1)

    json_file_path = sys.argv[1]

    with open(json_file_path, "r") as f:
        json_data = json.load(f)

    pipeline = SynthoCadPipeline()
    result = pipeline.process_from_json(json_data, open_freecad=False)

    if result["status"] == "success":
        print("[SUCCESS]")
        print(f"  JSON:       {result['json_file']}")
        print(f"  Python:     {result['py_file']}")
        print(f"  STEP:       {result['step_file']}")
        print(f"  Parameters: {result['parameters']['total_count']} found")
    else:
        print(f"[FAILED] {result['error']}")
        sys.exit(1)
