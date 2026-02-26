"""AST-based Parameter Extractor for generated CadQuery Python files.

Extracts every numeric literal passed to a CadQuery method call and
produces a flat parameter list that the frontend can display and the
ParameterUpdater can write back using precise (line, col) positions.

No LLM required — pure Python AST parsing.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


# ── CadQuery method → positional-arg friendly names ──────────────────────
# Methods NOT listed here are still extracted with generic "arg_N" names.
METHOD_ARG_NAMES: Dict[str, List[str]] = {
    "circle":        ["radius"],
    "extrude":       ["depth"],
    "cutBlind":      ["depth"],
    "moveTo":        ["x", "y"],
    "lineTo":        ["x", "y"],
    "line":          ["dx", "dy"],
    "hLine":         ["distance"],
    "vLine":         ["distance"],
    "fillet":        ["radius"],
    "chamfer":       ["distance"],
    "hole":          ["diameter", "depth"],
    "cboreHole":     ["diameter", "depth", "cbore_diameter", "cbore_depth"],
    "cskHole":       ["diameter", "depth", "csk_diameter", "csk_angle"],
    "threePointArc": [],
    "revolve":       ["angle"],
    "rect":          ["width", "height"],
    "box":           ["length", "width", "height"],
    "sphere":        ["radius"],
    "cylinder":      ["height", "radius"],
    "shell":         ["thickness"],
    "transformed":   [],
    "polarArray":    ["radius", "start_angle", "angle", "count"],
    "rarray":        ["x_spacing", "y_spacing", "x_count", "y_count"],
    "twistExtrude":  ["depth", "angle"],
    "offset2D":      ["distance"],
    "mirror":        [],
    "translate":     [],
    "rotate":        [],
    "workplane":     [],
}

# Human-readable descriptions keyed on the short arg name
_DESC: Dict[str, str] = {
    "radius":         "Radius",
    "depth":          "Depth / Height",
    "x":              "X position",
    "y":              "Y position",
    "dx":             "Delta-X",
    "dy":             "Delta-Y",
    "distance":       "Distance",
    "width":          "Width",
    "height":         "Height",
    "length":         "Length",
    "diameter":       "Diameter",
    "angle":          "Angle",
    "thickness":      "Shell thickness",
    "cbore_diameter": "Counter-bore diameter",
    "cbore_depth":    "Counter-bore depth",
    "csk_diameter":   "Counter-sink diameter",
    "csk_angle":      "Counter-sink angle",
    "x_spacing":      "X spacing",
    "y_spacing":      "Y spacing",
    "x_count":        "X count",
    "y_count":        "Y count",
    "start_angle":    "Start angle",
    "count":          "Count",
}

# Args that must be > 0
_POSITIVE_ARGS = {"radius", "depth", "diameter", "thickness",
                  "cbore_diameter", "cbore_depth", "csk_diameter"}


class ParameterExtractor:
    """Extract numeric parameters from a CadQuery .py file via AST."""

    # ── public API (unchanged signature) ──────────────────────────────────

    def extract_from_python(self, py_file_path: str) -> Dict[str, Any]:
        """Parse *py_file_path* and return a parameter manifest."""
        py_path = Path(py_file_path)
        if not py_path.exists():
            raise FileNotFoundError(f"Python file not found: {py_file_path}")

        code = py_path.read_text(encoding="utf-8")
        code_lines = code.splitlines(keepends=True)
        tree = ast.parse(code)

        parameters: List[Dict[str, Any]] = []
        method_counts: Dict[str, int] = {}   # occurrence counter

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            method_name = self._method_name(node)
            if method_name is None:
                continue

            method_counts[method_name] = method_counts.get(method_name, 0) + 1
            idx = method_counts[method_name]
            arg_names = METHOD_ARG_NAMES.get(method_name)

            # ── positional arguments ──────────────────────────────────
            for i, arg_node in enumerate(node.args):
                nums = self._extract_nums(arg_node, code_lines)
                for ni, (val, lineno, col_offset, end_col) in enumerate(nums):
                    if arg_names and i < len(arg_names):
                        short = arg_names[i]
                    else:
                        short = f"arg_{i + 1}"
                    # If the single arg yielded many values (tuple),
                    # append a sub-index
                    if len(nums) > 1:
                        short = f"{short}_{['x','y','z'][ni] if ni < 3 else ni}"
                    pname = f"{method_name}_{idx}_{short}"
                    parameters.append(self._mk(
                        name=pname, value=val, method=method_name,
                        arg_index=i, keyword=None, short=short,
                        lineno=lineno, col_offset=col_offset,
                        end_col=end_col,
                    ))

            # ── keyword arguments ─────────────────────────────────────
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                nums = self._extract_nums(kw.value, code_lines)
                for ni, (val, lineno, col_offset, end_col) in enumerate(nums):
                    if len(nums) == 1:
                        short = kw.arg
                    else:
                        short = f"{kw.arg}_{['x','y','z'][ni] if ni < 3 else ni}"
                    pname = f"{method_name}_{idx}_{short}"
                    parameters.append(self._mk(
                        name=pname, value=val, method=method_name,
                        arg_index=None, keyword=kw.arg, short=short,
                        lineno=lineno, col_offset=col_offset,
                        end_col=end_col,
                    ))

        return {
            "file": str(py_path),
            "parameters": parameters,
            "total_count": len(parameters),
        }

    def generate_markdown(self, parameters_data: Dict[str, Any]) -> str:
        md = [
            "# Model Parameters", "",
            f"**File:** `{Path(parameters_data['file']).name}`",
            f"**Total Parameters:** {parameters_data['total_count']}",
            "", "---", "",
        ]
        if not parameters_data["parameters"]:
            md.append("*No editable parameters found.*")
            return "\n".join(md)
        md.append("## Editable Parameters\n")
        for p in parameters_data["parameters"]:
            md.append(f"### {p['description']}")
            md.append(f"- **Name:** `{p['name']}`")
            md.append(f"- **Value:** {p['value']}")
            md.append(f"- **Unit:** {p['unit']}")
            md.append(f"- **Range:** {p['min']} to {p['max']}")
            md.append("")
        return "\n".join(md)

    # ── private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _method_name(call: ast.Call) -> Optional[str]:
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return None

    @classmethod
    def _extract_nums(cls, node: ast.expr,
                      code_lines: List[str]) -> List[tuple]:
        """Return list of (value, lineno, col_offset, end_col) for numerics."""
        single = cls._single_num(node, code_lines)
        if single is not None:
            return [single]
        if isinstance(node, ast.Tuple):
            out = []
            for elt in node.elts:
                s = cls._single_num(elt, code_lines)
                if s is not None:
                    out.append(s)
            return out
        return []

    @classmethod
    def _single_num(cls, node: ast.expr,
                    code_lines: List[str]) -> Optional[tuple]:
        """Extract (value, line, col, end_col) from a numeric literal node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            val = float(node.value)
            ln = node.lineno
            col = node.col_offset
            end = getattr(node, "end_col_offset", None)
            if end is None:
                end = col + len(cls._text_at(code_lines, ln, col))
            return (val, ln, col, end)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = node.operand
            if isinstance(inner, ast.Constant) and isinstance(inner.value, (int, float)):
                val = -float(inner.value)
                ln = node.lineno
                col = node.col_offset
                end = getattr(inner, "end_col_offset", None)
                if end is None:
                    end = col + 1 + len(cls._text_at(code_lines, inner.lineno, inner.col_offset))
                return (val, ln, col, end)
        return None

    @staticmethod
    def _text_at(lines: List[str], lineno: int, col: int) -> str:
        """Read a numeric token from source starting at (lineno, col)."""
        if lineno < 1 or lineno > len(lines):
            return ""
        rest = lines[lineno - 1][col:]
        m = re.match(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', rest)
        return m.group(0) if m else ""

    @staticmethod
    def _mk(*, name, value, method, arg_index, keyword, short,
            lineno, col_offset, end_col) -> Dict[str, Any]:
        desc_label = _DESC.get(short, short.replace("_", " ").title())
        unit = "degrees" if "angle" in short.lower() else "mm"
        positive = short in _POSITIVE_ARGS
        return {
            "name": name,
            "value": value,
            "type": "float",
            "description": f"{method}() -> {desc_label}",
            "unit": unit,
            "min": 0.001 if positive else -10000.0,
            "max": 10000.0,
            "method": method,
            "arg_index": arg_index,
            "keyword": keyword,
            "lineno": lineno,
            "col_offset": col_offset,
            "end_col": end_col,
        }
