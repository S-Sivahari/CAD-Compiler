import re
from typing import Dict, Tuple, Optional


class PromptValidator:

    def __init__(self, min_length: int = 10, max_length: int = 5000):
        self.min_length = min_length
        self.max_length = max_length

        self.cad_keywords = [
            "cylinder", "box", "cube", "sphere", "cone", "tube", "pipe",
            "bracket", "flange", "shaft", "gear", "plate", "rod",
            "hole", "cut", "extrude", "revolve", "fillet", "chamfer",
            "diameter", "radius", "length", "width", "height", "depth", "thick",
            "mm", "cm", "inch", "meter", "millimeter", "centimeter",
            "round", "square", "rectangular", "circular", "hollow",
            "mounting", "base", "top", "bottom", "side", "edge", "face",
            "bolt", "nut", "screw", "washer", "pin", "dowel", "rivet",
            "bearing", "bushing", "coupling", "collar", "pulley",
            "clamp", "gasket", "seal", "ring", "o-ring",
            "elbow", "fitting", "cap", "plug", "cover", "lid",
            "standoff", "spacer", "gusset", "brace", "rib",
            "slot", "groove", "keyway", "notch", "pocket",
            "taper", "draft", "thread", "knurl",
            "hexagonal", "hex", "octagonal", "triangular",
            "wall", "shell", "housing", "enclosure", "case",
            "rail", "channel", "extrusion", "profile",
            "counterbore", "countersink", "tapped",
            "pattern", "array", "symmetric", "mirror",
            "assembly", "part", "component", "feature",
        ]

        self.shape_keywords = {
            "cylinder": ["cylinder", "rod", "shaft", "pipe", "tube", "pin", "bar", "column"],
            "box": ["box", "cube", "block", "plate", "slab", "brick", "beam"],
            "bracket": ["bracket", "l-bracket", "angle", "corner", "mount", "brace"],
            "flange": ["flange", "disk", "plate", "adapter", "ring"],
            "gear": ["gear", "spur", "teeth", "cog", "sprocket"],
            "fastener": ["bolt", "nut", "screw", "washer", "rivet", "pin", "dowel"],
            "bearing": ["bearing", "bushing", "sleeve", "journal"],
            "housing": ["housing", "enclosure", "case", "shell", "box"],
            "fitting": ["elbow", "tee", "coupling", "fitting", "adapter", "connector"],
        }

    def validate(self, prompt: str) -> Tuple[bool, Optional[str], Optional[Dict]]:

        if not prompt or not isinstance(prompt, str):
            return False, "Prompt cannot be empty", None

        prompt_clean = prompt.strip()

        if len(prompt_clean) < self.min_length:
            return False, f"Prompt too short. Minimum {self.min_length} characters required. Please describe the CAD model in more detail.", None

        if len(prompt_clean) > self.max_length:
            return False, f"Prompt too long. Maximum {self.max_length} characters allowed.", None

        if not re.search(r"[a-zA-Z]", prompt_clean):
            return False, "Prompt must contain alphabetic characters.", None

        prompt_lower = prompt_clean.lower()

        has_cad_keyword = any(keyword in prompt_lower for keyword in self.cad_keywords)

        if not has_cad_keyword:
            return False, "Prompt does not describe a CAD model. Please use geometric terms like 'cylinder', 'box', 'bracket', or dimensions like 'mm', 'diameter', etc.", {
                "suggestion": "Try templates",
                "templates": ["cylinder", "box", "l_bracket", "flange"],
            }

        has_dimension = bool(re.search(r"\d+\.?\d*\s*(mm|cm|inch|in|meter|m\b|feet|ft)", prompt_lower))
        has_number = bool(re.search(r"\d", prompt_clean))

        if not has_number:
            return False, "Please include dimensions in your prompt (e.g., '100mm', '5 inches', '2cm diameter').", {
                "suggestion": "Add numerical dimensions"
            }

        suspicious_patterns = [
            r"<script", r"javascript:", r"eval\(", r"exec\(",
            r"__import__", r"system\(", r"popen\(",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, prompt_lower):
                return False, "Invalid input detected. Please describe your CAD model without code or scripts.", None

        keywords_found = [kw for kw in self.cad_keywords if kw in prompt_lower]
        detected_shape = self._detect_shape(prompt_lower)

        metadata = {
            "length": len(prompt_clean),
            "has_dimensions": has_dimension,
            "has_numbers": has_number,
            "cad_keywords_found": keywords_found,
            "detected_shape": detected_shape,
            "complexity_hint": self._estimate_complexity(prompt_lower),
        }

        return True, None, metadata

    def _detect_shape(self, prompt_lower: str) -> str:
        """Detect the primary shape category from the prompt."""
        for shape, keywords in self.shape_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return shape
        return "unknown"

    def _estimate_complexity(self, prompt_lower: str) -> str:
        """Estimate model complexity from prompt."""
        complex_indicators = [
            "pattern", "array", "holes", "bolt circle",
            "assembly", "multiple", "with", "and",
            "counterbore", "countersink", "fillet", "chamfer",
            "thread", "gear teeth",
        ]
        matches = sum(1 for ind in complex_indicators if ind in prompt_lower)

        if matches >= 3:
            return "complex"
        elif matches >= 1:
            return "moderate"
        return "simple"

    def suggest_templates(self, prompt: str) -> list:
        prompt_lower = prompt.lower()
        suggestions = []

        template_keywords = {
            "cylinder": ["cylinder", "rod", "shaft", "circular", "round", "pin"],
            "box": ["box", "cube", "rectangular", "square", "block", "plate"],
            "tube": ["tube", "pipe", "hollow cylinder", "hollow", "bushing", "sleeve"],
            "l_bracket": ["bracket", "l-bracket", "angle", "corner", "mount"],
            "flange": ["flange", "mounting plate", "adapter", "disk", "bolt circle"],
            "shaft": ["shaft", "axle", "spindle", "rod"],
            "hex_bolt": ["bolt", "hex bolt", "hex head", "fastener"],
            "nut": ["nut", "hex nut", "wing nut", "t-nut"],
            "washer": ["washer", "spacer", "shim"],
            "gear": ["gear", "spur gear", "teeth", "cog"],
            "bearing": ["bearing", "ball bearing", "bushing"],
            "standoff": ["standoff", "spacer", "PCB", "circuit board"],
        }

        for template, keywords in template_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                suggestions.append(template)

        return suggestions[:5]
