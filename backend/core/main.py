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
from rag.provider import RAGProvider, RAGResult, NullRAGProvider
from utils.errors import *
from utils.logger import pipeline_logger
from core import config
from core.schema_loader import build_generation_prompt


class SynthoCadPipeline:

    def __init__(self, rag_provider: Optional[RAGProvider] = None):
        self.prompt_validator = PromptValidator()
        self.generator = CadQueryGenerator
        self.param_extractor = ParameterExtractor()
        self.param_updater = ParameterUpdater()
        self.freecad = FreeCADInstanceGenerator()
        self.logger = pipeline_logger
        self.template_index = TemplateIndex(config.TEMPLATES_DIR)
        self.rag_provider = rag_provider or NullRAGProvider()

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

        system_prompt = build_generation_prompt()

        # ── Gather examples: keyword templates + RAG results ──────────
        templates = self.template_index.find_relevant_templates(prompt, max_results=3)

        rag_results: list = []
        if self.rag_provider.is_ready():
            try:
                rag_results = self.rag_provider.query(prompt, n_results=3)
                self.logger.info(f"RAG returned {len(rag_results)} results")
            except Exception as exc:
                self.logger.warning(f"RAG query failed (non-fatal): {exc}")

        # Merge & deduplicate (prefer RAG results when names overlap)
        seen_names: set = set()
        merged_examples: list = []

        for rr in rag_results:
            name = rr.json_data.get("final_name", "")
            if name and name in seen_names:
                continue
            seen_names.add(name)
            merged_examples.append(rr.json_data)

        for t in templates:
            name = t.get("final_name", "")
            if name and name in seen_names:
                continue
            seen_names.add(name)
            merged_examples.append(t)

        # Cap at 5 examples to avoid token bloat
        merged_examples = merged_examples[:5]

        examples_text = ""
        if merged_examples:
            examples_text = "\n\nREFERENCE EXAMPLES (use these as guides for correct structure and scaling):\n"
            for i, ex in enumerate(merged_examples, 1):
                clean = {k: v for k, v in ex.items() if not k.startswith("_")}
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
        return build_generation_prompt()

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

    pipeline = SynthoCadPipeline(rag_provider=config.get_rag_provider())
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
