import json
import math
from pathlib import Path
from typing import Union, Dict, Any, Tuple, List, Optional
from jsonschema import validate, ValidationError


def validate_json(json_input: Union[str, Dict[str, Any]]) -> bool:
    result = validate_json_detailed(json_input)
    return result["valid"]


def validate_json_detailed(json_input: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Validate JSON against SCL schema with detailed error reporting."""
    schema_path = Path(__file__).parent.parent / "core" / "scl_schema.json"

    with open(schema_path, "r") as f:
        schema = json.load(f)

    if isinstance(json_input, str):
        try:
            json_data = json.loads(json_input)
        except json.JSONDecodeError as e:
            return {"valid": False, "errors": [f"Invalid JSON syntax: {str(e)}"], "warnings": []}
    else:
        json_data = json_input

    errors = []
    warnings = []

    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as e:
        path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        errors.append(f"Schema violation at '{path}': {e.message}")

    structural_errors, structural_warnings = _validate_structural_integrity(json_data)
    errors.extend(structural_errors)
    warnings.extend(structural_warnings)

    geometry_errors, geometry_warnings = _validate_geometry(json_data)
    errors.extend(geometry_errors)
    warnings.extend(geometry_warnings)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "parts_count": len(json_data.get("parts", {})),
        "has_patterns": any(
            "pattern" in p for p in json_data.get("parts", {}).values()
        ),
        "has_holes": any(
            "hole_feature" in p for p in json_data.get("parts", {}).values()
        ),
        "has_revolve": any(
            "revolve_profile" in p for p in json_data.get("parts", {}).values()
        ),
    }


def _validate_structural_integrity(json_data: Dict) -> Tuple[List[str], List[str]]:
    """Validate structural rules beyond JSON schema."""
    errors = []
    warnings = []

    if not json_data.get("final_name"):
        errors.append("Missing 'final_name' field")

    if not json_data.get("final_shape"):
        warnings.append("Missing 'final_shape' field - will default to 'Unknown'")

    parts = json_data.get("parts", {})
    if not parts:
        errors.append("No parts defined")
        return errors, warnings

    expected_nums = []
    for key in parts:
        if not key.startswith("part_"):
            errors.append(f"Invalid part key '{key}' - must be 'part_N'")
            continue
        try:
            num = int(key.split("_")[1])
            expected_nums.append(num)
        except (IndexError, ValueError):
            errors.append(f"Invalid part key '{key}' - must be 'part_N' with integer N")

    if expected_nums:
        expected_nums.sort()
        if expected_nums[0] != 1:
            errors.append(f"Parts must start from part_1, found part_{expected_nums[0]}")

        for i in range(len(expected_nums) - 1):
            if expected_nums[i+1] - expected_nums[i] > 1:
                errors.append(f"Gap in part numbering: part_{expected_nums[i]} to part_{expected_nums[i+1]}")

    first_part = parts.get("part_1")
    if first_part:
        ext = first_part.get("extrusion", {})
        rev = first_part.get("revolve", {})
        op = ext.get("operation") or rev.get("operation")
        if op and op != "NewBodyFeatureOperation":
            errors.append(f"part_1 must use 'NewBodyFeatureOperation', found '{op}'")

    for part_key, part_data in parts.items():
        has_sketch = "sketch" in part_data
        has_revolve = "revolve_profile" in part_data
        has_hole = "hole_feature" in part_data

        feature_count = sum([has_sketch, has_revolve, has_hole])
        if feature_count == 0:
            errors.append(f"{part_key}: No geometry defined (need sketch, revolve_profile, or hole_feature)")
        elif feature_count > 1:
            warnings.append(f"{part_key}: Multiple geometry types defined, only first will be used")

        if has_sketch and "extrusion" not in part_data:
            errors.append(f"{part_key}: Has sketch but missing extrusion")

        if has_revolve and "revolve" not in part_data:
            errors.append(f"{part_key}: Has revolve_profile but missing revolve parameters")

        if has_sketch:
            ext = part_data.get("extrusion", {})
            d1 = ext.get("extrude_depth_towards_normal", 0)
            d2 = ext.get("extrude_depth_opposite_normal", 0)
            if d1 == 0 and d2 == 0:
                errors.append(f"{part_key}: Both extrusion depths are 0")
            if ext.get("sketch_scale", 0) <= 0:
                errors.append(f"{part_key}: sketch_scale must be > 0")

    return errors, warnings


def _validate_geometry(json_data: Dict) -> Tuple[List[str], List[str]]:
    """Validate geometric constraints."""
    errors = []
    warnings = []

    parts = json_data.get("parts", {})
    for part_key, part_data in parts.items():
        if "sketch" in part_data:
            sketch = part_data["sketch"]
            for face_key, face_data in sketch.items():
                for loop_key, loop_data in face_data.items():
                    loop_errors = _validate_loop(part_key, face_key, loop_key, loop_data)
                    errors.extend(loop_errors[0])
                    warnings.extend(loop_errors[1])

        if "revolve_profile" in part_data:
            profile = part_data["revolve_profile"]
            for face_key, face_data in profile.items():
                for loop_key, loop_data in face_data.items():
                    loop_errors = _validate_loop(part_key, face_key, loop_key, loop_data)
                    errors.extend(loop_errors[0])
                    warnings.extend(loop_errors[1])

        if "hole_feature" in part_data:
            hole = part_data["hole_feature"]
            if hole.get("diameter", 0) <= 0:
                errors.append(f"{part_key}: Hole diameter must be > 0")
            if hole.get("depth", 0) < 0:
                errors.append(f"{part_key}: Hole depth must be >= 0")
            if hole.get("hole_type") == "Counterbore":
                cb_d = hole.get("counterbore_diameter", 0)
                if cb_d <= hole.get("diameter", 0):
                    errors.append(f"{part_key}: Counterbore diameter must be > hole diameter")

        if "pattern" in part_data:
            pattern = part_data["pattern"]
            if pattern.get("count", 0) < 2:
                errors.append(f"{part_key}: Pattern count must be >= 2")
            if pattern.get("type") == "linear" and pattern.get("spacing", 0) <= 0:
                errors.append(f"{part_key}: Linear pattern spacing must be > 0")

    return errors, warnings


def _validate_loop(part_key, face_key, loop_key, loop_data) -> Tuple[List[str], List[str]]:
    """Validate a single sketch loop for closure and validity."""
    errors = []
    warnings = []
    prefix = f"{part_key}/{face_key}/{loop_key}"

    circle_keys = [k for k in loop_data if k.startswith("circle_")]
    line_keys = [k for k in loop_data if k.startswith("line_")]
    arc_keys = [k for k in loop_data if k.startswith("arc_")]

    if circle_keys and not line_keys and not arc_keys:
        for ck in circle_keys:
            r = loop_data[ck].get("Radius", 0)
            if r <= 0:
                errors.append(f"{prefix}/{ck}: Circle radius must be > 0")
        return errors, warnings

    items = []
    for k in line_keys:
        items.append((int(k.split("_")[1]), "line", loop_data[k]))
    for k in arc_keys:
        items.append((int(k.split("_")[1]), "arc", loop_data[k]))
    items.sort(key=lambda x: x[0])

    if not items:
        warnings.append(f"{prefix}: Empty loop")
        return errors, warnings

    first_start = None
    last_end = None
    for idx, (num, item_type, item_data) in enumerate(items):
        start = item_data.get("Start Point")
        end = item_data.get("End Point")

        if idx == 0 and start:
            first_start = start
        if end:
            last_end = end

        if item_type == "arc":
            mid = item_data.get("Mid Point")
            if start and mid and end:
                if _points_collinear(start, mid, end):
                    warnings.append(f"{prefix}: Arc has collinear points (Start/Mid/End), may fail")

    if first_start and last_end:
        dist = math.sqrt((first_start[0]-last_end[0])**2 + (first_start[1]-last_end[1])**2)
        if dist > 0.01:
            warnings.append(f"{prefix}: Loop not closed (gap={dist:.4f})")

    return errors, warnings


def _points_collinear(p1, p2, p3, tolerance=0.001):
    """Check if three 2D points are collinear."""
    area = abs((p2[0]-p1[0])*(p3[1]-p1[1]) - (p3[0]-p1[0])*(p2[1]-p1[1]))
    return area < tolerance


def repair_json(json_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Attempt to auto-repair common JSON issues. Returns (repaired_data, repairs_made)."""
    repairs = []
    data = json.loads(json.dumps(json_data))

    if not data.get("final_name"):
        data["final_name"] = "Generated_Model"
        repairs.append("Added missing final_name")

    if not data.get("final_shape"):
        data["final_shape"] = "Model"
        repairs.append("Added missing final_shape")

    if not data.get("units"):
        data["units"] = "mm"
        repairs.append("Added missing units field (default: mm)")

    parts = data.get("parts", {})

    old_keys = sorted(parts.keys())
    needs_renumber = False
    for i, key in enumerate(old_keys, 1):
        expected = f"part_{i}"
        if key != expected:
            needs_renumber = True
            break

    if needs_renumber and old_keys:
        new_parts = {}
        for i, key in enumerate(sorted(old_keys), 1):
            new_key = f"part_{i}"
            new_parts[new_key] = parts[key]
            if key != new_key:
                repairs.append(f"Renumbered {key} -> {new_key}")
        data["parts"] = new_parts
        parts = data["parts"]

    first_part = parts.get("part_1")
    if first_part:
        ext = first_part.get("extrusion", {})
        rev = first_part.get("revolve", {})
        if ext.get("operation") and ext["operation"] != "NewBodyFeatureOperation":
            old_op = ext["operation"]
            ext["operation"] = "NewBodyFeatureOperation"
            repairs.append(f"part_1: Changed operation from '{old_op}' to 'NewBodyFeatureOperation'")
        if rev.get("operation") and rev["operation"] != "NewBodyFeatureOperation":
            old_op = rev["operation"]
            rev["operation"] = "NewBodyFeatureOperation"
            repairs.append(f"part_1: Changed revolve operation from '{old_op}' to 'NewBodyFeatureOperation'")

    for part_key, part_data in parts.items():
        if "coordinate_system" not in part_data:
            part_data["coordinate_system"] = {
                "Euler Angles": [0.0, 0.0, 0.0],
                "Translation Vector": [0.0, 0.0, 0.0]
            }
            repairs.append(f"{part_key}: Added missing coordinate_system")

        if "description" not in part_data:
            part_data["description"] = {
                "name": data.get("final_name", "Part"),
                "shape": data.get("final_shape", "Shape"),
                "length": 1.0,
                "width": 1.0,
                "height": 1.0
            }
            repairs.append(f"{part_key}: Added missing description")

        if "sketch" in part_data and "extrusion" not in part_data:
            part_data["extrusion"] = {
                "extrude_depth_towards_normal": 0.1,
                "extrude_depth_opposite_normal": 0.0,
                "sketch_scale": 1.0,
                "operation": "NewBodyFeatureOperation" if part_key == "part_1" else "JoinFeatureOperation"
            }
            repairs.append(f"{part_key}: Added missing extrusion with defaults")

    return data, repairs
