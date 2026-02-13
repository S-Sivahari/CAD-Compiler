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
from validators.json_validator import validate_json
from core.cadquery_generator import CadQueryGenerator
from services.parameter_extractor import ParameterExtractor
from services.parameter_updater import ParameterUpdater
from services.freecad_instance_generator import FreeCADInstanceGenerator
from services.gemini_service import call_gemini
from utils.errors import *
from utils.logger import pipeline_logger
from core import config


# LLM SYSTEM PROMPT - Instructions for converting natural language to SCL JSON
LLM_SYSTEM_PROMPT = """You are a CAD design assistant. Convert natural language to valid SCL JSON.

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations
2. Always include "units" field (default: "mm")
3. First operation must use "NewBodyFeatureOperation"
4. Sketch uses normalized 0.0-1.0 coordinates, then sketch_scale converts to real dimensions

DIMENSION FORMULA (IMPORTANT):
User input: "10mm radius cylinder, 20mm tall"

Step 1 - Sketch (normalized 0-1 range):
  Circle: Center [0.5, 0.5], Radius 0.5

Step 2 - Scale to real size:
  sketch_scale = diameter = 2 * radius = 20.0
  extrude_depth_towards_normal = height / sketch_scale = 20 / 20 = 1.0

Step 3 - Description (real dimensions):
  length: 20.0 (diameter)
  width: 20.0 (diameter)
  height: 20.0 (actual height)

ANOTHER EXAMPLE - "50mm x 30mm x 10mm box":

Sketch (normalized, aspect ratio 50:30):
  line_1: [0.0, 0.0] to [1.0, 0.0]
  line_2: [1.0, 0.0] to [1.0, 0.6]  ← 30/50 = 0.6
  line_3: [1.0, 0.6] to [0.0, 0.6]
  line_4: [0.0, 0.6] to [0.0, 0.0]

Scale:
  sketch_scale = 50.0 (longest dimension)
  extrude_depth = 10 / 50 = 0.2

Description:
  length: 50.0, width: 30.0, height: 10.0

REQUIRED JSON STRUCTURE:
{
  "final_name": "PartName",
  "final_shape": "cylinder",
  "units": "mm",
  "parts": {
    "part_1": {
      "coordinate_system": {
        "Euler Angles": [0.0, 0.0, 0.0],
        "Translation Vector": [0.0, 0.0, 0.0]
      },
      "sketch": {
        "face_1": {
          "loop_1": {
            "circle_1": {"Center": [0.5, 0.5], "Radius": 0.5}
          }
        }
      },
      "extrusion": {
        "extrude_depth_towards_normal": 1.0,
        "extrude_depth_opposite_normal": 0.0,
        "sketch_scale": 20.0,
        "operation": "NewBodyFeatureOperation"
      },
      "description": {
        "name": "PartName",
        "shape": "cylinder",
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

Output ONLY raw JSON starting with { and ending with }"""


class SynthoCadPipeline:
    
    def __init__(self):
        self.prompt_validator = PromptValidator()
        self.generator = CadQueryGenerator
        self.param_extractor = ParameterExtractor()
        self.param_updater = ParameterUpdater()
        self.freecad = FreeCADInstanceGenerator()
        self.logger = pipeline_logger
        
    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        self.logger.info(f"Step 1: Validating prompt")
        is_valid, error_msg, metadata = self.prompt_validator.validate(prompt)
        
        if not is_valid:
            self.logger.error(f"Prompt validation failed: {error_msg}")
            raise PromptValidationError(error_msg or "Validation failed", metadata)
            
        self.logger.info(f"Prompt validated successfully")
        
        # Calculate confidence based on prompt quality
        prompt_lower = prompt.lower()
        cad_keyword_matches = sum(1 for kw in self.prompt_validator.cad_keywords if kw in prompt_lower)
        confidence = min(0.95, 0.5 + (cad_keyword_matches * 0.1))
        
        # Check for template suggestions
        suggestions = self.prompt_validator.suggest_templates(prompt)
        
        return {
            'valid': True,
            'confidence': round(confidence, 2),
            'suggestions': suggestions,
            'metadata': metadata or {}
        }
        
    def generate_json_from_prompt(self, prompt: str) -> Dict[str, Any]:
        """Step 2: Generate SCL JSON from natural language using LLM.
        
        Following LLM_INTEGRATION_GUIDE.md:
        - Uses system prompt template
        - Loads relevant templates as examples
        - Calls configured LLM (Gemini by default)
        - Strips markdown and extracts JSON
        """
        self.logger.info("Step 2: Generating JSON from prompt via LLM")
        
        # Build system prompt following LLM_INTEGRATION_GUIDE.md
        system_prompt = self._build_llm_system_prompt()
        
        # Load relevant template examples
        templates = self._find_relevant_templates(prompt)
        
        # Build full prompt
        examples_text = ""
        if templates:
            examples_text = "\n\nWORKING EXAMPLES (study these for correct dimension scaling):\n"
            for i, t in enumerate(templates[:2], 1):
                examples_text += f"\nExample {i}:\n{json.dumps(t, indent=2)}\n"
        
        full_prompt = f"{system_prompt}{examples_text}\n\nUSER REQUEST: {prompt}\n\nJSON output:"
        
        # Call LLM with slightly higher temperature for better reasoning
        try:
            response_text = call_gemini(full_prompt, max_tokens=8192, temperature=0.2)
            
            # Strip markdown code blocks if present
            cleaned_text = self._strip_markdown_json(response_text)
            
            # Parse JSON
            json_data = json.loads(cleaned_text)
            self.logger.info(f"LLM generated JSON for: {json_data.get('final_name', 'Unknown')}")
            return json_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"LLM returned invalid JSON: {e}")
            raise JSONGenerationError(f"LLM returned invalid JSON: {str(e)}")
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            raise JSONGenerationError(f"LLM generation failed: {str(e)}")
    
    def _build_llm_system_prompt(self) -> str:
        """Return the LLM system prompt for JSON generation."""
        return LLM_SYSTEM_PROMPT
    
    def _find_relevant_templates(self, prompt: str) -> list:
        """Load template examples relevant to the user's prompt."""
        templates = []
        prompt_lower = prompt.lower()
        
        # Prefer concrete examples with real dimensions
        template_map = {
            ('cylinder', 'rod', 'pipe', 'round', 'circular'): 'basic/cylinder_10x20.json',
            ('box', 'cube', 'block', 'plate', 'rectangular'): 'basic/box_50x30x10.json',
            ('tube', 'hollow'): 'basic/tube.json',
        }
        
        for keywords, template_file in template_map.items():
            if any(kw in prompt_lower for kw in keywords):
                template_path = config.TEMPLATES_DIR / template_file
                if template_path.exists():
                    with open(template_path, 'r') as f:
                        templates.append(json.load(f))
        
        # Always include at least one concrete example
        if not templates:
            default_template = config.TEMPLATES_DIR / 'basic' / 'cylinder_10x20.json'
            if default_template.exists():
                with open(default_template, 'r') as f:
                    templates.append(json.load(f))
        
        return templates
    
    def _strip_markdown_json(self, text: str) -> str:
        """Strip markdown code blocks and extract JSON from LLM response."""
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith('```'):
            lines = text.split('\n')
            lines = lines[1:]  # Remove first line (```json or ```)
            for i, line in enumerate(lines):
                if line.strip() == '```':
                    lines = lines[:i]
                    break
            text = '\n'.join(lines).strip()
        
        # Try to find JSON object if not starting with {
        if not text.startswith('{'):
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                text = match.group()
        
        return text
        
    def validate_json(self, json_data: Dict) -> bool:
        self.logger.info("Step 3: Validating JSON against SCL schema")
        
        if not validate_json(json_data):
            self.logger.error("JSON validation failed")
            raise JSONValidationError("JSON does not conform to SCL schema")
            
        self.logger.info("JSON validated successfully")
        return True
        
    def generate_cadquery_code(self, json_data: Dict, output_name: str) -> str:
        self.logger.info("Step 4: Generating CadQuery Python code")
        
        try:
            generator = self.generator(json_data, output_name)
            code = generator.generate()
            
            py_file = config.PY_OUTPUT_DIR / f"{output_name}_generated.py"
            with open(py_file, 'w') as f:
                f.write(code)
                
            self.logger.info(f"Generated Python code: {py_file}")
            return str(py_file)
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {str(e)}")
            raise CodeGenerationError(f"Failed to generate CadQuery code: {str(e)}")
            
    def execute_cadquery_code(self, py_file: str, output_name: str) -> str:
        self.logger.info("Step 5: Executing CadQuery code to generate STEP")
        
        py_path = Path(py_file)
        if not py_path.is_absolute():
            py_path = config.BASE_DIR / py_path
            
        if not py_path.exists():
            raise ExecutionError(f"Python file not found: {py_file}")
            
        step_file = config.STEP_OUTPUT_DIR / f"{output_name}.step"
        
        try:
            result = subprocess.run(
                [sys.executable, str(py_path)],
                capture_output=True,
                text=True,
                timeout=config.EXECUTION_TIMEOUT,
                cwd=config.STEP_OUTPUT_DIR
            )
            
            if result.returncode != 0:
                self.logger.error(f"Execution failed: {result.stderr}")
                raise ExecutionError(f"Python execution failed: {result.stderr}")
                
            if not step_file.exists():
                raise ExecutionError("STEP file was not created")
                
            self.logger.info(f"STEP file generated: {step_file}")
            return str(step_file)
            
        except subprocess.TimeoutExpired:
            raise ExecutionError(f"Execution timeout ({config.EXECUTION_TIMEOUT}s)")
        except Exception as e:
            raise ExecutionError(f"Execution error: {str(e)}")
            
    def extract_parameters(self, py_file: str) -> Dict[str, Any]:
        self.logger.info("Step 6: Extracting editable parameters")
        
        try:
            params_data = self.param_extractor.extract_from_python(py_file)
            markdown = self.param_extractor.generate_markdown(params_data)
            
            self.logger.info(f"Extracted {params_data['total_count']} parameters")
            
            return {
                'parameters': params_data['parameters'],
                'markdown': markdown,
                'total_count': params_data['total_count']
            }
            
        except Exception as e:
            self.logger.error(f"Parameter extraction failed: {str(e)}")
            return {
                'parameters': [],
                'markdown': '# No parameters found',
                'total_count': 0
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
            return py_file  # Return the path to the updated file
            
        except Exception as e:
            self.logger.error(f"Parameter update failed: {str(e)}")
            raise ParameterUpdateError(f"Failed to update parameters: {str(e)}")
            
    def regenerate_from_updated_python(self, py_file: str, output_name: str, open_freecad: bool = True) -> str:
        self.logger.info("Step 9: Regenerating STEP from updated Python")
        
        # Update the export filename in the Python file to match output_name
        py_path = Path(py_file)
        if not py_path.is_absolute():
            py_path = config.BASE_DIR / py_path
            
        content = py_path.read_text()
        # Replace the export line with the correct output name
        import re
        content = re.sub(
            r"cq\.exporters\.export\(result,\s*['\"][\w.-]+\.step['\"]\)",
            f"cq.exporters.export(result, '{output_name}.step')",
            content
        )
        py_path.write_text(content)
        
        step_file = self.execute_cadquery_code(str(py_path), output_name)
        
        if open_freecad:
            self.freecad.reload_step_file(step_file)
            
        return step_file
        
    def process_from_json(self, json_data: Dict, output_name: Optional[str] = None, open_freecad: bool = True) -> Dict[str, Any]:
        
        try:
            self.validate_json(json_data)
            
            if not output_name:
                output_name = json_data.get('final_name', 'output')
                if not output_name or output_name.strip() == "":
                    output_name = 'output'
            
            output_name = output_name.replace(' ', '_').replace('/', '_')
            
            json_file = config.JSON_OUTPUT_DIR / f"{output_name}.json"
            with open(json_file, 'w') as f:
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
                'status': 'success',
                'json_file': str(json_file),
                'py_file': py_file,
                'step_file': step_file,
                'parameters': params_result,
                'freecad_opened': freecad_opened
            }
            
        except SynthoCadError as e:
            self.logger.error(f"Pipeline failed: {e.message}")
            return {
                'status': 'error',
                'error': e.to_dict()
            }
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return {
                'status': 'error',
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': str(e)
                }
            }
            
    def process_from_prompt(self, prompt: str, open_freecad: bool = True) -> Dict[str, Any]:
        
        try:
            self.validate_prompt(prompt)
            
            json_data = self.generate_json_from_prompt(prompt)
            
            return self.process_from_json(json_data, open_freecad=open_freecad)
            
        except NotImplementedError as e:
            return {
                'status': 'error',
                'error': {
                    'code': 'NOT_IMPLEMENTED',
                    'message': str(e)
                }
            }
        except SynthoCadError as e:
            return {
                'status': 'error',
                'error': e.to_dict()
            }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <json_file>")
        sys.exit(1)
        
    json_file_path = sys.argv[1]
    
    with open(json_file_path, 'r') as f:
        json_data = json.load(f)
    
    pipeline = SynthoCadPipeline()
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
        print(f"Failed: {result}")
        sys.exit(1)
