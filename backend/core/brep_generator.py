import json
import logging
import re
import uuid
from typing import Dict, Any, List

from core import config
from core.brep_engine import BRepEngine, BRepEngineError
from services.gemini_service import call_gemini
from utils.logger import setup_logger

logger = setup_logger('synthocad.brep_generator', 'brep_generator.log')

class BRepGenerator:
    def __init__(self):
        self.engine = BRepEngine()

    def _normalize_and_repair_sequence(self, sequence: Any) -> List[Dict[str, Any]]:
        """Dynamically sanitize parsed operations and keep only executable steps."""
        if not isinstance(sequence, list):
            raise ValueError("Parsed sequence is not a list.")

        valid_types = {
            "create_box",
            "create_cylinder",
            "create_cone",
            "create_sphere",
            "boolean_cut",
            "boolean_union",
            "boolean_intersect",
            "fillet_edges",
            "chamfer_edges",
        }

        repaired: List[Dict[str, Any]] = []
        dropped_count = 0

        for idx, op in enumerate(sequence):
            if not isinstance(op, dict):
                dropped_count += 1
                continue

            op_type = op.get("type")
            if not isinstance(op_type, str) or op_type not in valid_types:
                dropped_count += 1
                continue

            fixed_op: Dict[str, Any] = {
                "step_id": len(repaired) + 1,
                "type": op_type,
            }

            if op_type.startswith("create_") or op_type in ("fillet_edges", "chamfer_edges"):
                params = op.get("params", {})
                fixed_op["params"] = params if isinstance(params, dict) else {}
            else:
                tool = op.get("tool", {})
                if not isinstance(tool, dict):
                    tool = {}
                tool_type = tool.get("type")
                tool_params = tool.get("params", {}) if isinstance(tool.get("params", {}), dict) else {}

                if op_type in ("boolean_union", "boolean_cut", "boolean_intersect"):
                    if isinstance(tool_type, str):
                        fixed_op["tool"] = {
                            "type": tool_type,
                            "params": tool_params,
                        }
                    else:
                        dropped_count += 1
                        continue

            repaired.append(fixed_op)

        if dropped_count > 0:
            logger.warning(
                f"[Generator] Dropped {dropped_count} malformed operation(s) during dynamic sequence repair."
            )

        if not repaired:
            raise ValueError("No valid operations remain after dynamic sequence repair.")

        return repaired

    def _salvage_truncated_array(self, text: str) -> List[Dict[str, Any]]:
        """Recover a truncated JSON array by keeping complete objects only."""
        start = text.find('[')
        if start == -1:
            raise ValueError("No JSON array start '[' found for salvage.")

        in_string = False
        escaped = False
        array_depth = 0
        object_depth = 0
        last_complete_object_idx = -1

        for idx in range(start, len(text)):
            ch = text[idx]

            if escaped:
                escaped = False
                continue

            if ch == '\\':
                escaped = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == '[':
                array_depth += 1
            elif ch == ']':
                array_depth -= 1
            elif ch == '{':
                object_depth += 1
            elif ch == '}':
                object_depth -= 1
                if array_depth == 1 and object_depth == 0:
                    last_complete_object_idx = idx

        if last_complete_object_idx == -1:
            raise ValueError("No complete JSON object found to salvage.")

        salvaged = text[start:last_complete_object_idx + 1]
        salvaged = re.sub(r",\s*$", "", salvaged)
        salvaged = f"{salvaged}\n]"

        parsed = json.loads(salvaged)
        if not isinstance(parsed, list) or len(parsed) == 0:
            raise ValueError("Salvaged JSON did not produce a non-empty operation list.")

        return parsed

    def _write_parse_debug_dump(self, response_text: str, error_msg: str) -> str:
        """Write raw LLM response to logs for parse-debugging and return file path."""
        dump_name = f"brep_parse_failure_{uuid.uuid4().hex[:8]}.txt"
        dump_path = config.LOGS_DIR / dump_name
        with open(dump_path, "w", encoding="utf-8") as handle:
            handle.write("B-Rep sequence parse failure\n")
            handle.write(f"error: {error_msg}\n\n")
            handle.write("raw_response:\n")
            handle.write(response_text)
        return str(dump_path)

    def _extract_first_json_array(self, text: str) -> str:
        """Extract the first top-level JSON array from arbitrary text."""
        start = text.find('[')
        if start == -1:
            raise ValueError("No JSON array start '[' found in LLM response.")

        in_string = False
        escaped = False
        depth = 0

        for idx in range(start, len(text)):
            ch = text[idx]

            if escaped:
                escaped = False
                continue

            if ch == '\\':
                escaped = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    return text[start:idx + 1]

        raise ValueError("Unterminated JSON array in LLM response.")

    def _parse_sequence_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse LLM text into a JSON array of operations with light repair."""
        parse_errors: List[str] = []

        def to_sequence(parsed: Any) -> List[Dict[str, Any]]:
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except Exception:
                    pass

            if isinstance(parsed, list):
                return parsed

            if isinstance(parsed, dict):
                for key in ("operations", "sequence", "steps", "data"):
                    value = parsed.get(key)
                    if isinstance(value, list):
                        return value
                    if isinstance(value, str):
                        try:
                            nested = json.loads(value)
                            if isinstance(nested, list):
                                return nested
                        except Exception:
                            continue

            raise ValueError("Expected a JSON array of operations.")

        cleaned = response_text.strip()

        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

        candidates = [cleaned]

        try:
            extracted = self._extract_first_json_array(cleaned)
            if extracted != cleaned:
                candidates.append(extracted)
        except Exception:
            pass

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                sequence = to_sequence(parsed)
                return self._normalize_and_repair_sequence(sequence)
            except json.JSONDecodeError as e:
                snippet_start = max(0, e.pos - 60)
                snippet_end = min(len(candidate), e.pos + 60)
                snippet = candidate[snippet_start:snippet_end].replace("\n", "\\n")
                parse_errors.append(
                    f"json error at line {e.lineno}, col {e.colno}: {e.msg}; around='{snippet}'"
                )
            except Exception as e:
                parse_errors.append(f"parse error: {e}")

            try:
                repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
                parsed = json.loads(repaired)
                sequence = to_sequence(parsed)
                return self._normalize_and_repair_sequence(sequence)
            except json.JSONDecodeError as e:
                snippet_start = max(0, e.pos - 60)
                snippet_end = min(len(repaired), e.pos + 60)
                snippet = repaired[snippet_start:snippet_end].replace("\n", "\\n")
                parse_errors.append(
                    f"repaired json error at line {e.lineno}, col {e.colno}: {e.msg}; around='{snippet}'"
                )
            except Exception as e:
                parse_errors.append(f"repaired parse error: {e}")

        try:
            salvaged_sequence = self._salvage_truncated_array(cleaned)
            salvaged_sequence = self._normalize_and_repair_sequence(salvaged_sequence)
            logger.warning(
                f"[Generator] Recovered truncated LLM response; proceeding with {len(salvaged_sequence)} operations."
            )
            return salvaged_sequence
        except Exception as e:
            parse_errors.append(f"salvage failed: {e}")

        condensed = " | ".join(parse_errors[:4]) if parse_errors else "No JSON parse diagnostics available"
        raise ValueError(f"Unable to parse valid JSON array from LLM response. {condensed}")
        
    def generate_brep_sequence_from_prompt(self, prompt: str) -> List[Dict[str, Any]]:
        system_prompt = """You are an architectural CAD engineer. The user will ask for a 3D model. 
Decompose the model into a sequential list of standard Boundary Representation (B-Rep) operations.

CRITICAL OUTPUT COMPLETENESS RULES:
1. Your entire response MUST be a single valid JSON array and nothing else.
2. The JSON MUST be complete and closed properly (all brackets/braces/strings terminated).
3. Do NOT output partial objects, unfinished keys, comments, markdown, or explanations.
4. If you are near output limits, REDUCE detail and return fewer operations, but always return valid complete JSON.
5. Final character of the response must be `]`.

CRITICAL POSITIONING RULES:
1. `create_box` with origin [X,Y,Z] is centered on X and Y, and extends UPWARDS in Z. 
   - A box at [0,0,0] with length=100, width=50, height=20 spans X:[-50, 50], Y:[-25, 25], Z:[0, 20].
   - Do NOT offset origin to corners. Origin represents the center midpoint of the bottom face.
2. `create_cylinder` with origin [X,Y,Z] is directly centered at X,Y, and extends UPWARDS along its `axis` (Z by default).
   - Its bounding box spans X:[X-R, X+R], Y:[Y-R, Y+R], Z:[Z, Z+height].
3. `boolean_cut` and `boolean_union` tools use the EXACT same origin rules as primitive creation. 
   - To cut a hole in the exact center of a parent box, the cut origin MUST perfectly match the parent origin X and Y coordinates.

OUTPUT EXACTLY ONLY A JSON ARRAY OF OPERATIONS. Do not include markdown fences, just the raw JSON.
Supported types:
- create_box: params: {length, width, height, origin: [x,y,z]}
- create_cylinder: params: {radius, height, origin: [x,y,z], axis: [dx,dy,dz]}
- create_sphere: params: {radius, origin: [x,y,z]}
- boolean_cut: tool: {type (box|cylinder|cone|sphere), params: {...same as create...}}
- boolean_union: tool: {...}

Example creating a box with a hole in the exact dead center:
[
  {
    "step_id": 1,
    "type": "create_box",
    "params": {
      "length": 100.0,
      "width": 50.0,
      "height": 20.0,
      "origin": [0, 0, 0]
    }
  },
  {
    "step_id": 2,
    "type": "boolean_cut",
    "tool": {
      "type": "cylinder",
      "params": {
        "radius": 5.0,
        "height": 20.0,
        "origin": [0, 0, 0],
        "axis": [0, 0, 1]
      }
    }
  }
]
        """
        
        user_prompt = f"Target model description: {prompt}"
        response_text = ""
        
        logger.info("[Generator] Requesting sequence from LLM...")
        try:
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            response_text = call_gemini(
                prompt=combined_prompt,
                temperature=0.2,
                json_mode=True,
                max_tokens=getattr(config, "BREP_GEMINI_MAX_OUTPUT_TOKENS", 65000),
            )
            sequence = self._parse_sequence_response(response_text)
            return sequence
            
        except Exception as e:
            dump_path = ""
            if response_text:
                try:
                    dump_path = self._write_parse_debug_dump(response_text, str(e))
                    logger.error(f"[Generator] Raw LLM response dumped to: {dump_path}")
                except Exception as dump_err:
                    logger.error(f"[Generator] Failed to write parse debug dump: {dump_err}")

            logger.error(f"[Generator] Failed to get valid JSON from LLM: {e}")
            details = f"LLM Generation failed: {str(e)}"
            if dump_path:
                details += f" | debug_dump: {dump_path}"
            raise RuntimeError(details)

    def run_generation_loop(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Generates the sequence once, then executes it.
        Gemini is called only once per request (during initial sequence generation).
        """
        sequence = self.generate_brep_sequence_from_prompt(prompt)
        last_error = None
        history = []
        
        for attempt in range(max_retries):
            logger.info(f"[Generator] Attempt {attempt+1}/{max_retries} to execute sequence")
            try:
                history = self.engine.execute_sequence(sequence)
                logger.info("[Generator] Sequence executed successfully!")
                return {
                    'status': 'success',
                    'history': history,
                    'final_step_file': history[-1]['step_file'],
                    'final_step_url': history[-1]['step_url'],
                    'sequence': sequence
                }
            except BRepEngineError as e:
                last_error = str(e)
                logger.warning(f"[Generator] Engine failed on attempt {attempt+1}. Error: {last_error}")
                # Do not re-call Gemini here to avoid per-attempt rate limit pressure.
                # Retries (if any) execute the same already-generated sequence.
                continue
        
        # If we exit the loop, we failed
        return {
            'status': 'error',
            'error': f"Failed after {max_retries} attempts. Last error: {last_error}",
            'partial_history': history,
            'sequence': sequence
        }
