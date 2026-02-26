import json
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("template_index")


TEMPLATE_KEYWORD_MAP = {
    "basic/cylinder.json": {
        "keywords": ["cylinder", "rod", "shaft", "pin", "round", "circular", "disk", "disc"],
        "category": "basic",
        "complexity": "simple",
        "features": ["circle", "extrusion"],
        "description": "Simple solid cylinder"
    },
    "basic/cylinder_10x20.json": {
        "keywords": ["cylinder", "rod", "shaft", "pin", "round", "circular"],
        "category": "basic",
        "complexity": "simple",
        "features": ["circle", "extrusion"],
        "description": "Cylinder with radius 10mm, height 20mm"
    },
    "basic/box.json": {
        "keywords": ["box", "cube", "block", "plate", "rectangular", "square", "prism"],
        "category": "basic",
        "complexity": "simple",
        "features": ["rectangle", "extrusion"],
        "description": "Simple rectangular box"
    },
    "basic/box_50x30x10.json": {
        "keywords": ["box", "cube", "block", "plate", "rectangular", "square"],
        "category": "basic",
        "complexity": "simple",
        "features": ["rectangle", "extrusion"],
        "description": "Box 50x30x10mm"
    },
    "basic/tube.json": {
        "keywords": ["tube", "pipe", "hollow", "cylinder", "bushing", "sleeve", "ring", "annular"],
        "category": "basic",
        "complexity": "simple",
        "features": ["concentric_circles", "extrusion"],
        "description": "Hollow cylinder / tube"
    },
    "mechanical/flange.json": {
        "keywords": ["flange", "mounting", "plate", "adapter", "circular", "disk", "bolt", "holes"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["circle", "holes", "pattern", "chamfer"],
        "description": "Circular flange with center hole and bolt pattern",
        "alt_format": True
    },
    "mechanical/l_bracket.json": {
        "keywords": ["bracket", "l-bracket", "angle", "corner", "support", "mount", "right angle"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["rectangle", "multi_part", "holes"],
        "description": "L-shaped mounting bracket"
    },
    "mechanical/ball_bearing.json": {
        "keywords": ["bearing", "ball bearing", "roller", "rotating", "inner ring", "outer ring"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["concentric_circles", "revolve"],
        "description": "Ball bearing with inner and outer race"
    },
    "mechanical/spur_gear.json": {
        "keywords": ["gear", "spur gear", "teeth", "cog", "sprocket", "drive", "mesh"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["arcs", "pattern", "circle"],
        "description": "Spur gear with involute teeth"
    },
    "mechanical/threaded_rod.json": {
        "keywords": ["threaded", "rod", "stud", "bolt", "thread", "screw", "M thread"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["helix", "cylinder"],
        "description": "Threaded rod/stud"
    },
    "mechanical/rigid_coupling.json": {
        "keywords": ["coupling", "connector", "shaft coupler", "join", "rigid"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["cylinder", "holes", "pattern"],
        "description": "Rigid shaft coupling"
    },
    "mechanical/sleeve_bushing.json": {
        "keywords": ["bushing", "sleeve", "bearing", "liner", "insert", "spacer"],
        "category": "mechanical",
        "complexity": "simple",
        "features": ["concentric_circles", "extrusion"],
        "description": "Cylindrical sleeve bushing"
    },
    "mechanical/shaft_collar_split.json": {
        "keywords": ["collar", "shaft collar", "clamp", "split", "set", "lock"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["cylinder", "cut", "holes"],
        "description": "Split shaft collar with clamping screw"
    },
    "mechanical/flanged_bushing.json": {
        "keywords": ["bushing", "flanged", "flange bushing", "thrust", "step"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["concentric_circles", "multi_part"],
        "description": "Flanged bushing with collar"
    },
    "mechanical/timing_pulley.json": {
        "keywords": ["pulley", "timing", "belt", "drive", "wheel", "teeth", "sheave"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["circle", "pattern", "cut"],
        "description": "Timing belt pulley"
    },
    "mechanical/timing_belt_pulley.json": {
        "keywords": ["pulley", "timing belt", "belt drive", "sheave", "idler"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["circle", "groove", "pattern"],
        "description": "Timing belt pulley with teeth"
    },
    "mechanical/lead_screw.json": {
        "keywords": ["lead screw", "screw", "acme", "trapezoidal", "linear motion"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["helix", "thread", "cylinder"],
        "description": "Lead screw for linear motion"
    },
    "mechanical/leveling_foot.json": {
        "keywords": ["leveling", "foot", "adjustable", "pad", "base", "support", "leg"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["circle", "thread", "multi_part"],
        "description": "Adjustable leveling foot"
    },
    "mechanical/swivel_caster.json": {
        "keywords": ["caster", "swivel", "wheel", "roller", "furniture", "cart"],
        "category": "mechanical",
        "complexity": "complex",
        "features": ["multi_part", "revolve", "holes"],
        "description": "Swivel caster wheel"
    },
    "mechanical/rigid_caster.json": {
        "keywords": ["caster", "rigid", "wheel", "fixed", "furniture"],
        "category": "mechanical",
        "complexity": "moderate",
        "features": ["multi_part", "holes"],
        "description": "Fixed/rigid caster wheel"
    },
    "Fasteners/hex_head_bolt.json": {
        "keywords": ["bolt", "hex", "hex bolt", "fastener", "screw", "M10", "thread"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["hexagon", "cylinder", "multi_part"],
        "description": "Hex head bolt M10x50"
    },
    "Fasteners/socket_head_cap_screw.json": {
        "keywords": ["screw", "socket head", "cap screw", "allen", "hex socket", "SHCS"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["cylinder", "hexagon", "multi_part"],
        "description": "Socket head cap screw"
    },
    "Fasteners/flat_head_screw.json": {
        "keywords": ["screw", "flat head", "countersunk", "CSK", "flathead"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["cone", "cylinder"],
        "description": "Flat/countersunk head screw"
    },
    "Fasteners/button_head_screw.json": {
        "keywords": ["screw", "button head", "dome", "round head", "pan head"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["dome", "cylinder"],
        "description": "Button head screw"
    },
    "Fasteners/set_screw.json": {
        "keywords": ["set screw", "grub screw", "headless", "locking"],
        "category": "fastener",
        "complexity": "simple",
        "features": ["cylinder", "hexagon"],
        "description": "Headless set/grub screw"
    },
    "Fasteners/hex_nut.json": {
        "keywords": ["nut", "hex nut", "fastener", "threaded"],
        "category": "fastener",
        "complexity": "simple",
        "features": ["hexagon", "hole"],
        "description": "Hexagonal nut"
    },
    "Fasteners/wing_nut.json": {
        "keywords": ["wing nut", "butterfly", "hand tighten", "thumb"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["multi_part", "wing"],
        "description": "Wing/butterfly nut"
    },
    "Fasteners/t_nut.json": {
        "keywords": ["t-nut", "tee nut", "slot", "channel"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["multi_part", "rectangle"],
        "description": "T-slot nut"
    },
    "Fasteners/flat_washer.json": {
        "keywords": ["washer", "flat washer", "spacer", "shim"],
        "category": "fastener",
        "complexity": "simple",
        "features": ["concentric_circles", "extrusion"],
        "description": "Flat washer"
    },
    "Fasteners/lock_washer.json": {
        "keywords": ["lock washer", "spring washer", "split washer", "locking"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["helix", "circle"],
        "description": "Split lock washer"
    },
    "Fasteners/fender_washer.json": {
        "keywords": ["fender washer", "penny washer", "large washer", "oversize"],
        "category": "fastener",
        "complexity": "simple",
        "features": ["concentric_circles"],
        "description": "Fender/penny washer (large OD)"
    },
    "Fasteners/dowel_pin.json": {
        "keywords": ["dowel", "pin", "alignment", "locating", "cylindrical pin"],
        "category": "fastener",
        "complexity": "simple",
        "features": ["cylinder"],
        "description": "Cylindrical dowel pin"
    },
    "Fasteners/shoulder_bolt.json": {
        "keywords": ["shoulder bolt", "stripper bolt", "stepped", "shoulder"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["multi_diameter", "cylinder", "hexagon"],
        "description": "Shoulder bolt with stepped shaft"
    },
    "Fasteners/retaining_ring.json": {
        "keywords": ["retaining ring", "snap ring", "circlip", "c-clip", "e-clip"],
        "category": "fastener",
        "complexity": "moderate",
        "features": ["ring", "cut"],
        "description": "Retaining/snap ring"
    },
    "Structural/angle_bracket.json": {
        "keywords": ["angle bracket", "L bracket", "corner", "brace", "support", "90 degree"],
        "category": "structural",
        "complexity": "moderate",
        "features": ["rectangle", "multi_part", "holes"],
        "description": "90-degree angle bracket with holes"
    },
    "Structural/corner_gusset.json": {
        "keywords": ["gusset", "corner", "reinforcement", "brace", "triangle"],
        "category": "structural",
        "complexity": "moderate",
        "features": ["triangle", "multi_part"],
        "description": "Corner gusset plate"
    },
    "Structural/square_tubing.json": {
        "keywords": ["square tube", "box section", "rectangular tube", "hollow section", "HSS"],
        "category": "structural",
        "complexity": "simple",
        "features": ["nested_rectangles", "extrusion"],
        "description": "Square/rectangular hollow section"
    },
    "Structural/end_cap.json": {
        "keywords": ["end cap", "cover", "plug", "cap", "closure", "lid"],
        "category": "structural",
        "complexity": "simple",
        "features": ["rectangle", "extrusion"],
        "description": "End cap/cover plate"
    },
    "Structural/t_slot_extrusion.json": {
        "keywords": ["t-slot", "extrusion", "aluminum extrusion", "profile", "80/20", "rail"],
        "category": "structural",
        "complexity": "complex",
        "features": ["complex_profile", "extrusion"],
        "description": "T-slot aluminum extrusion profile"
    },
    "Structural/din_rail.json": {
        "keywords": ["din rail", "rail", "mounting rail", "electrical", "panel"],
        "category": "structural",
        "complexity": "moderate",
        "features": ["profile", "extrusion"],
        "description": "DIN rail mounting track"
    },
    "Electrical/pcb_standoff.json": {
        "keywords": ["standoff", "spacer", "PCB", "circuit board", "electronic", "hex standoff"],
        "category": "electrical",
        "complexity": "simple",
        "features": ["hexagon", "hole", "cylinder"],
        "description": "PCB hex standoff/spacer"
    },
    "Electrical/terminal_block.json": {
        "keywords": ["terminal", "block", "connector", "wire", "electrical", "terminal block"],
        "category": "electrical",
        "complexity": "moderate",
        "features": ["rectangle", "holes", "multi_part"],
        "description": "Electrical terminal block"
    },
    "Piping/elbow_fitting.json": {
        "keywords": ["elbow", "fitting", "pipe fitting", "bend", "90 degree", "pipe bend"],
        "category": "piping",
        "complexity": "complex",
        "features": ["revolve", "tube"],
        "description": "Pipe elbow fitting"
    },
    "Piping/hose_clamp.json": {
        "keywords": ["clamp", "hose clamp", "band clamp", "jubilee", "hose"],
        "category": "piping",
        "complexity": "moderate",
        "features": ["ring", "band"],
        "description": "Hose/band clamp"
    },
    "Piping/o_ring.json": {
        "keywords": ["o-ring", "seal", "gasket", "rubber ring", "torus"],
        "category": "piping",
        "complexity": "moderate",
        "features": ["torus", "revolve"],
        "description": "O-ring seal"
    },
    "patterns/linear_array.json": {
        "keywords": ["array", "linear array", "pattern", "repeat", "row", "grid"],
        "category": "pattern",
        "complexity": "moderate",
        "features": ["pattern", "linear"],
        "description": "Linear array/pattern example"
    },
    "patterns/bolt_circle.json": {
        "keywords": ["bolt circle", "bolt pattern", "PCD", "polar pattern", "hole pattern", "circular array"],
        "category": "pattern",
        "complexity": "moderate",
        "features": ["pattern", "polar", "holes"],
        "description": "Circular bolt hole pattern"
    },

    # ── Power Transmission & Motion ──
    "power_transmission/worm_gear_set.json": {
        "keywords": ["worm gear", "worm", "worm wheel", "worm shaft", "gear set", "right angle drive", "speed reducer", "self-locking"],
        "category": "power_transmission",
        "complexity": "complex",
        "features": ["cylinder", "pattern", "multi_part", "linear_pattern"],
        "description": "Worm gear set with worm shaft and worm wheel"
    },
    "power_transmission/geneva_drive.json": {
        "keywords": ["geneva", "geneva drive", "intermittent", "indexing", "slot", "mechanism", "step motion", "star wheel"],
        "category": "power_transmission",
        "complexity": "complex",
        "features": ["circle", "cut", "polar_pattern", "multi_part"],
        "description": "4-slot Geneva drive intermittent motion mechanism"
    },
    "power_transmission/cv_joint_housing.json": {
        "keywords": ["cv joint", "constant velocity", "drive shaft", "bell housing", "joint housing", "axle", "automotive"],
        "category": "power_transmission",
        "complexity": "complex",
        "features": ["revolve", "flange", "bolt_pattern", "holes"],
        "description": "Bell-shaped CV joint outer housing with bolt flange"
    },
    "power_transmission/helical_gear.json": {
        "keywords": ["helical gear", "helical", "gear", "helix", "angled teeth", "transmission", "mesh"],
        "category": "power_transmission",
        "complexity": "complex",
        "features": ["circle", "polar_pattern", "multi_part", "chamfer"],
        "description": "Helical gear with 20-degree helix angle and hub"
    },
    "power_transmission/spline_shaft.json": {
        "keywords": ["spline", "spline shaft", "involute spline", "shaft", "torque transfer", "keyed", "serrated"],
        "category": "power_transmission",
        "complexity": "complex",
        "features": ["cylinder", "polar_pattern", "rectangle", "multi_part"],
        "description": "8-tooth involute spline shaft with bearing journals"
    },
    "power_transmission/ball_screw_nut.json": {
        "keywords": ["ball screw", "screw nut", "ball nut", "linear actuator", "precision motion", "lead", "CNC"],
        "category": "power_transmission",
        "complexity": "complex",
        "features": ["cylinder", "flange", "bolt_pattern", "holes", "chamfer"],
        "description": "Flanged ball screw nut with mounting flange and ball return holes"
    },

    # ── Fluid Power & Heat Transfer ──
    "fluid_power/hydraulic_manifold_block.json": {
        "keywords": ["manifold", "hydraulic", "valve block", "hydraulic block", "port", "gallery", "fluid power", "D03"],
        "category": "fluid_power",
        "complexity": "complex",
        "features": ["rectangle", "holes", "linear_pattern", "multi_part"],
        "description": "D03 hydraulic manifold block with valve stations and internal galleries"
    },
    "fluid_power/heat_exchanger_tube_sheet.json": {
        "keywords": ["heat exchanger", "tube sheet", "tube plate", "shell and tube", "boiler", "condenser", "tube bundle"],
        "category": "fluid_power",
        "complexity": "complex",
        "features": ["circle", "polar_pattern", "holes", "groove"],
        "description": "Shell and tube heat exchanger tube sheet with 3-ring tube pattern"
    },
    "fluid_power/centrifugal_impeller.json": {
        "keywords": ["impeller", "centrifugal", "pump", "vane", "blade", "fan", "turbine", "rotor", "propeller"],
        "category": "fluid_power",
        "complexity": "complex",
        "features": ["circle", "polar_pattern", "multi_part", "cut"],
        "description": "Closed centrifugal pump impeller with radial vanes"
    },
    "fluid_power/venturi_nozzle.json": {
        "keywords": ["venturi", "nozzle", "flow meter", "orifice", "convergent", "divergent", "throat", "differential pressure"],
        "category": "fluid_power",
        "complexity": "complex",
        "features": ["revolve", "flange", "bolt_pattern", "holes"],
        "description": "Venturi flow measurement nozzle with flanged ends and pressure taps"
    },

    # ── Precision Tooling & Fixturing ──
    "tooling/plummer_block_housing.json": {
        "keywords": ["plummer block", "pillow block", "bearing housing", "pedestal", "bearing support", "SN510"],
        "category": "tooling",
        "complexity": "complex",
        "features": ["rectangle", "cylinder", "holes", "multi_part", "fillet"],
        "description": "Split plummer block bearing housing with oil hole"
    },
    "tooling/vise_jaw.json": {
        "keywords": ["vise", "jaw", "clamp", "vice", "workholding", "fixture", "serrated", "v-groove"],
        "category": "tooling",
        "complexity": "moderate",
        "features": ["rectangle", "cut", "linear_pattern", "holes"],
        "description": "Hardened vise jaw with V-groove, step and serrations"
    },
    "tooling/indexing_plate.json": {
        "keywords": ["indexing", "dividing", "plate", "division plate", "rotary", "hole circle", "angular"],
        "category": "tooling",
        "complexity": "complex",
        "features": ["circle", "polar_pattern", "holes", "keyway"],
        "description": "Precision indexing plate with 3 concentric rings (12/24/36 holes)"
    },
    "tooling/drill_jig_bushing_carrier.json": {
        "keywords": ["drill jig", "jig", "bushing", "fixture", "production", "carrier", "drilling", "guide"],
        "category": "tooling",
        "complexity": "complex",
        "features": ["rectangle", "multi_part", "holes", "linear_pattern"],
        "description": "Drill jig bushing carrier with support legs and locating pins"
    },

    # ── Advanced Structural & Enclosures ──
    "enclosures/nema_motor_mount.json": {
        "keywords": ["motor mount", "NEMA", "motor bracket", "stepper", "servo", "motor plate", "NEMA34", "NEMA23"],
        "category": "enclosures",
        "complexity": "complex",
        "features": ["rectangle", "circle", "holes", "multi_part", "gusset"],
        "description": "NEMA 34 integrated motor mounting bracket with gusset ribs"
    },
    "enclosures/lathe_tailstock_body.json": {
        "keywords": ["tailstock", "lathe", "quill", "morse taper", "dead center", "live center", "machine tool"],
        "category": "enclosures",
        "complexity": "complex",
        "features": ["rectangle", "cylinder", "multi_part", "cut", "fillet"],
        "description": "Lathe tailstock body casting with quill bore and taper"
    },
    "enclosures/electronics_enclosure_ip67.json": {
        "keywords": ["enclosure", "electronics", "IP67", "waterproof", "junction box", "housing", "case", "box", "PCB", "cable gland"],
        "category": "enclosures",
        "complexity": "complex",
        "features": ["rectangle", "cut", "multi_part", "holes", "linear_pattern", "gasket"],
        "description": "IP67-rated electronics enclosure with PCB standoffs and cable glands"
    },

    # ── Linkages & Joints ──
    "linkages/knuckle_joint.json": {
        "keywords": ["knuckle", "knuckle joint", "toggle", "eye", "fork", "pin joint", "clevis", "articulated"],
        "category": "linkages",
        "complexity": "complex",
        "features": ["cylinder", "multi_part", "holes", "circle"],
        "description": "Knuckle joint assembly with eye, fork, and pin"
    },
    "linkages/universal_coupling_yoke.json": {
        "keywords": ["universal joint", "U-joint", "cardan", "coupling", "yoke", "cross", "drive shaft", "gimbal"],
        "category": "linkages",
        "complexity": "complex",
        "features": ["cylinder", "rectangle", "multi_part", "holes", "keyway"],
        "description": "Universal joint coupling yoke with hub, keyway and cross-pin holes"
    },
    "linkages/rod_end_bearing_housing.json": {
        "keywords": ["rod end", "heim joint", "rose joint", "spherical", "bearing housing", "tie rod", "linkage", "control rod"],
        "category": "linkages",
        "complexity": "complex",
        "features": ["cylinder", "multi_part", "holes", "rectangle"],
        "description": "Rod end bearing housing M12 with threaded shank and wrench flats"
    },
}


class TemplateIndex:
    """Index of all templates with keyword matching for RAG retrieval."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.index = TEMPLATE_KEYWORD_MAP
        self._loaded_cache = {}

    def find_relevant_templates(self, prompt: str, max_results: int = 3) -> List[Dict]:
        """Find most relevant templates for a given prompt using keyword scoring."""
        prompt_lower = prompt.lower()
        prompt_words = set(re.findall(r'\b[a-z]+\b', prompt_lower))

        scores = []
        for template_path, meta in self.index.items():
            score = 0

            for keyword in meta["keywords"]:
                kw_lower = keyword.lower()
                if kw_lower in prompt_lower:
                    word_count = len(kw_lower.split())
                    score += 3 * word_count

                kw_words = set(kw_lower.split())
                matching_words = kw_words & prompt_words
                if matching_words:
                    score += len(matching_words)

            if meta.get("category") and meta["category"] in prompt_lower:
                score += 2

            if score > 0:
                scores.append((template_path, score, meta))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        seen_categories = set()

        for template_path, score, meta in scores[:max_results * 2]:
            if len(results) >= max_results:
                break

            if meta.get("alt_format"):
                continue

            full_path = self.templates_dir / template_path
            if not full_path.exists():
                continue

            template_data = self._load_template(full_path)
            if template_data is None:
                continue

            if not self._is_scl_format(template_data):
                continue

            results.append(template_data)
            seen_categories.add(meta.get("category", ""))

        if not results:
            default_path = self.templates_dir / "basic" / "cylinder_10x20.json"
            if default_path.exists():
                template_data = self._load_template(default_path)
                if template_data:
                    results.append(template_data)

        return results

    def get_template_by_name(self, name: str) -> Optional[Dict]:
        """Load a specific template by partial name match."""
        name_lower = name.lower().replace(" ", "_")

        for template_path in self.index:
            if name_lower in template_path.lower():
                full_path = self.templates_dir / template_path
                if full_path.exists():
                    return self._load_template(full_path)

        for json_file in self.templates_dir.rglob("*.json"):
            if name_lower in json_file.stem.lower():
                return self._load_template(json_file)

        return None

    def list_all_templates(self) -> List[Dict[str, str]]:
        """List all available templates with metadata."""
        result = []
        for template_path, meta in self.index.items():
            full_path = self.templates_dir / template_path
            result.append({
                "path": template_path,
                "description": meta.get("description", ""),
                "category": meta.get("category", ""),
                "complexity": meta.get("complexity", ""),
                "exists": full_path.exists(),
                "scl_format": not meta.get("alt_format", False)
            })
        return result

    def _load_template(self, path: Path) -> Optional[Dict]:
        """Load and cache a template file."""
        str_path = str(path)
        if str_path in self._loaded_cache:
            return self._loaded_cache[str_path]

        try:
            with open(path, "r") as f:
                data = json.load(f)
            self._loaded_cache[str_path] = data
            return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load template {path}: {e}")
            return None

    def _is_scl_format(self, data: Dict) -> bool:
        """Check if template uses SCL format (vs alternative formats)."""
        parts = data.get("parts", {})
        if not parts:
            return False

        has_any_geometry = False
        for part_key, part_data in parts.items():
            if not part_key.startswith("part_"):
                return False
            if not isinstance(part_data, dict):
                return False
            has_geometry = (
                "sketch" in part_data
                or "revolve_profile" in part_data
                or "hole_feature" in part_data
                or "post_processing" in part_data
            )
            if has_geometry:
                has_any_geometry = True

        return has_any_geometry

    def get_complexity_examples(self, target_complexity: str = "moderate") -> List[Dict]:
        """Get templates matching a complexity level."""
        results = []
        for template_path, meta in self.index.items():
            if meta.get("complexity") == target_complexity and not meta.get("alt_format"):
                full_path = self.templates_dir / template_path
                if full_path.exists():
                    data = self._load_template(full_path)
                    if data and self._is_scl_format(data):
                        results.append(data)
        return results

    def get_template_names(self) -> set:
        """Return a set of all known template ``final_name`` values.

        Useful for deduplication when merging keyword results with RAG
        results in the pipeline.
        """
        names = set()
        for template_path, meta in self.index.items():
            full_path = self.templates_dir / template_path
            if full_path.exists():
                data = self._load_template(full_path)
                if data:
                    name = data.get("final_name", "")
                    if name:
                        names.add(name)
        return names
