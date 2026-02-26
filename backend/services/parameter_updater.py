"""Position-based Parameter Updater for generated CadQuery Python files.

Uses the (lineno, col_offset, end_col) metadata produced by the
AST-based ParameterExtractor to splice new numeric values into the
source text — no fragile regex matching required.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from services.parameter_extractor import ParameterExtractor


class ParameterUpdater:
    """Apply numeric parameter changes to a CadQuery .py file."""

    def __init__(self):
        self._extractor = ParameterExtractor()

    # ── public API (same signature as before) ─────────────────────────────

    def update_python_file(self, py_file_path: str,
                           parameters: Dict[str, float]) -> bool:
        """Update *parameters* (name → new_value) in *py_file_path*.

        Returns True on success.
        """
        py_path = Path(py_file_path)
        if not py_path.exists():
            raise FileNotFoundError(f"Python file not found: {py_file_path}")

        # Re-extract current parameter layout so we have fresh positions
        manifest = self._extractor.extract_from_python(str(py_path))
        param_map: Dict[str, Dict[str, Any]] = {
            p["name"]: p for p in manifest["parameters"]
        }

        # Build a list of (line, col, end_col, new_text) edits
        edits: List[Tuple[int, int, int, str]] = []
        for name, new_value in parameters.items():
            meta = param_map.get(name)
            if meta is None:
                continue
            valid, err = self.validate_parameter_value(
                name, new_value, meta.get("min"), meta.get("max")
            )
            if not valid:
                continue
            new_text = _format_number(new_value)
            edits.append((meta["lineno"], meta["col_offset"],
                          meta["end_col"], new_text))

        if not edits:
            return True   # nothing to change

        # Read source, apply edits (process bottom-up → right-to-left so
        # earlier edits don't shift positions of later ones)
        lines = py_path.read_text(encoding="utf-8").splitlines(keepends=True)
        # Sort descending by (line, col) so we splice from the end
        edits.sort(key=lambda e: (e[0], e[1]), reverse=True)

        for lineno, col, end_col, new_text in edits:
            idx = lineno - 1
            if idx < 0 or idx >= len(lines):
                continue
            line = lines[idx]
            lines[idx] = line[:col] + new_text + line[end_col:]

        py_path.write_text("".join(lines), encoding="utf-8")
        return True

    # ── validation (unchanged) ────────────────────────────────────────────

    @staticmethod
    def validate_parameter_value(param_name: str, value: float,
                                 min_val: Optional[float] = None,
                                 max_val: Optional[float] = None
                                 ) -> Tuple[bool, Optional[str]]:
        if not isinstance(value, (int, float)):
            return False, "Value must be a number"
        if min_val is not None and value < min_val:
            return False, f"Value must be at least {min_val}"
        if max_val is not None and value > max_val:
            return False, f"Value must be at most {max_val}"
        if "radius" in param_name or "depth" in param_name or "diameter" in param_name:
            if value <= 0:
                return False, "Value must be positive"
        return True, None


# ── helpers ───────────────────────────────────────────────────────────────

def _format_number(v: float) -> str:
    """Format a float nicely (drop trailing zeros, keep one decimal)."""
    if v == int(v):
        return f"{int(v)}.0"
    return f"{v:.6f}".rstrip("0").rstrip(".")
