import json
import math
from pathlib import Path
from typing import Optional

class CadQueryGenerator:
    def __init__(self, json_data, output_name: Optional[str] = None):
        if isinstance(json_data, str):
            self.data = json.loads(json_data)
        else:
            self.data = json_data
        self.output_name = output_name
        self.code_lines = []
        self.indent = 0
        
    def add_line(self, line):
        self.code_lines.append("    " * self.indent + line)
        
    def generate(self):
        self.code_lines = []
        self.add_line("import cadquery as cq")
        self.add_line("import math")
        self.add_line("")
        
        parts = self.data.get("parts", {})
        sorted_parts = sorted(parts.items(), key=lambda x: int(x[0].split("_")[1]))
        
        result_var = "result"
        
        for part_name, part_data in sorted_parts:
            part_num = part_name.split("_")[1]
            self.generate_part(part_data, part_num, result_var)
            
        units = self.data.get("units", "mm")
        
        if self.output_name:
            safe_name = self.output_name
        else:
            final_name = self.data.get("final_name", "output")
            if not final_name or final_name.strip() == "":
                final_name = "output"
            safe_name = final_name.replace(' ', '_').replace('/', '_')
        
        self.add_line("")
        self.add_line(f"cq.exporters.export({result_var}, '{safe_name}.step')")
        
        return "\n".join(self.code_lines)
        
    def generate_part(self, part, part_num, result_var):
        coord_sys = part.get("coordinate_system", {})
        euler = coord_sys.get("Euler Angles", [0, 0, 0])
        trans = coord_sys.get("Translation Vector", [0, 0, 0])
        
        has_sketch = "sketch" in part
        has_revolve = "revolve_profile" in part
        has_hole = "hole_feature" in part
        
        if has_sketch:
            self.generate_sketch_extrusion(part, part_num, result_var, euler, trans)
        elif has_revolve:
            self.generate_revolve(part, part_num, result_var, euler, trans)
        elif has_hole:
            self.generate_hole_feature(part, part_num, result_var, euler, trans)
            

            
        if "mirror" in part:
            self.generate_mirror(part["mirror"], result_var)
            
        if "post_processing" in part:
            for proc in part["post_processing"]:
                if "radius" in proc:
                    self.generate_fillet(proc, result_var)
                elif "distance" in proc:
                    self.generate_chamfer(proc, result_var)
                    
    def generate_sketch_extrusion(self, part, part_num, result_var, euler, trans):
        sketch = part["sketch"]
        extrusion = part["extrusion"]
        
        operation = extrusion["operation"]
        scale = extrusion["sketch_scale"]
        depth_normal = extrusion["extrude_depth_towards_normal"]
        depth_opposite = extrusion["extrude_depth_opposite_normal"]
        
        if part_num != "1":
            op_type = self.get_operation_suffix(operation)
            
        rotation_matrix = self.euler_to_matrix(euler[0], euler[1], euler[2])
        transformed_normal = self.transform_vector([0, 0, 1], rotation_matrix)
        
        self.add_line(f"wp = cq.Workplane('XY').transformed(")
        self.add_line(f"    offset=({trans[0]}, {trans[1]}, {trans[2]}),")
        self.add_line(f"    rotate=({euler[0]}, {euler[1]}, {euler[2]})")
        self.add_line(")")
        
        faces = sorted(sketch.items(), key=lambda x: int(x[0].split("_")[1]))
        
        for face_name, face_data in faces:
            loops = sorted(face_data.items(), key=lambda x: int(x[0].split("_")[1]))
            
            for loop_idx, (loop_name, loop_data) in enumerate(loops):
                items = []
                for key in loop_data:
                    if key.startswith("line_"):
                        items.append((int(key.split("_")[1]), "line", loop_data[key]))
                    elif key.startswith("arc_"):
                        items.append((int(key.split("_")[1]), "arc", loop_data[key]))
                    elif key.startswith("circle_"):
                        items.append((int(key.split("_")[1]), "circle", loop_data[key]))
                        
                items.sort(key=lambda x: x[0])
                
                for idx, (num, item_type, item_data) in enumerate(items):
                    if item_type == "circle":
                        center = item_data["Center"]
                        radius = item_data["Radius"]
                        scaled_center = [center[0] * scale, center[1] * scale]
                        scaled_radius = radius * scale
                        self.add_line(f"wp = wp.moveTo({scaled_center[0]}, {scaled_center[1]}).circle({scaled_radius})")
                    elif item_type == "line":
                        if idx == 0:
                            start = item_data["Start Point"]
                            scaled_start = [start[0] * scale, start[1] * scale]
                            self.add_line(f"wp = wp.moveTo({scaled_start[0]}, {scaled_start[1]})")
                        end = item_data["End Point"]
                        scaled_end = [end[0] * scale, end[1] * scale]
                        self.add_line(f"wp = wp.lineTo({scaled_end[0]}, {scaled_end[1]})")
                    elif item_type == "arc":
                        if idx == 0:
                            start = item_data["Start Point"]
                            scaled_start = [start[0] * scale, start[1] * scale]
                            self.add_line(f"wp = wp.moveTo({scaled_start[0]}, {scaled_start[1]})")
                        mid = item_data["Mid Point"]
                        end = item_data["End Point"]
                        scaled_mid = [mid[0] * scale, mid[1] * scale]
                        scaled_end = [end[0] * scale, end[1] * scale]
                        self.add_line(f"wp = wp.threePointArc(({scaled_mid[0]}, {scaled_mid[1]}), ({scaled_end[0]}, {scaled_end[1]}))")
                        
                if loop_idx == 0 and items and items[0][1] != "circle":
                    self.add_line("wp = wp.close()")
                    
        total_depth = depth_normal + depth_opposite
        self.add_line(f"wp = wp.extrude({total_depth})")
        
        if depth_opposite > 0:
            self.add_line(f"wp = wp.translate((0, 0, -{depth_opposite}))")
            
        if "pattern" in part:
            self.generate_pattern(part["pattern"], "wp")
            
        if part_num == "1":
            self.add_line(f"{result_var} = wp")
        else:
            op_map = {
                "NewBodyFeatureOperation": "union",
                "JoinFeatureOperation": "union",
                "CutFeatureOperation": "cut",
                "IntersectFeatureOperation": "intersect"
            }
            op_method = op_map.get(operation, "union")
            self.add_line(f"{result_var} = {result_var}.{op_method}(wp)")
            
    def generate_revolve(self, part, part_num, result_var, euler, trans):
        revolve_profile = part["revolve_profile"]
        revolve = part["revolve"]
        
        operation = revolve["operation"]
        axis = revolve["axis"]
        angle = revolve["angle"]
        origin = revolve["origin"]
        
        self.add_line(f"wp = cq.Workplane('XZ').transformed(")
        self.add_line(f"    offset=({trans[0]}, {trans[1]}, {trans[2]}),")
        self.add_line(f"    rotate=({euler[0]}, {euler[1]}, {euler[2]})")
        self.add_line(")")
        
        faces = sorted(revolve_profile.items(), key=lambda x: int(x[0].split("_")[1]))
        
        for face_name, face_data in faces:
            loops = sorted(face_data.items(), key=lambda x: int(x[0].split("_")[1]))
            
            for loop_idx, (loop_name, loop_data) in enumerate(loops):
                items = []
                for key in loop_data:
                    if key.startswith("line_"):
                        items.append((int(key.split("_")[1]), "line", loop_data[key]))
                    elif key.startswith("arc_"):
                        items.append((int(key.split("_")[1]), "arc", loop_data[key]))
                        
                items.sort(key=lambda x: x[0])
                
                for idx, (num, item_type, item_data) in enumerate(items):
                    if item_type == "line":
                        if idx == 0:
                            start = item_data["Start Point"]
                            self.add_line(f"wp = wp.moveTo({start[0]}, {start[1]})")
                        end = item_data["End Point"]
                        self.add_line(f"wp = wp.lineTo({end[0]}, {end[1]})")
                    elif item_type == "arc":
                        if idx == 0:
                            start = item_data["Start Point"]
                            self.add_line(f"wp = wp.moveTo({start[0]}, {start[1]})")
                        mid = item_data["Mid Point"]
                        end = item_data["End Point"]
                        self.add_line(f"wp = wp.threePointArc(({mid[0]}, {mid[1]}), ({end[0]}, {end[1]}))")
                        
                if items:
                    self.add_line("wp = wp.close()")
                    
        self.add_line(f"wp = wp.revolve({angle}, ({origin[0]}, {origin[1]}, {origin[2]}), ({axis[0]}, {axis[1]}, {axis[2]}))")
        
        if "pattern" in part:
            self.generate_pattern(part["pattern"], "wp")
            
        if part_num == "1":
            self.add_line(f"{result_var} = wp")
        else:
            op_map = {
                "NewBodyFeatureOperation": "union",
                "JoinFeatureOperation": "union",
                "CutFeatureOperation": "cut",
                "IntersectFeatureOperation": "intersect"
            }
            op_method = op_map.get(operation, "union")
            self.add_line(f"{result_var} = {result_var}.{op_method}(wp)")
            
    def generate_hole_feature(self, part, part_num, result_var, euler, trans):
        hole = part["hole_feature"]
        
        hole_type = hole["hole_type"]
        diameter = hole["diameter"]
        depth = hole["depth"]
        position = hole["position"]
        
        self.add_line(f"wp = cq.Workplane('XY').transformed(")
        self.add_line(f"    offset=({trans[0]}, {trans[1]}, {trans[2]}),")
        self.add_line(f"    rotate=({euler[0]}, {euler[1]}, {euler[2]})")
        self.add_line(")")
        
        radius = diameter / 2
        self.add_line(f"wp = wp.moveTo({position[0]}, {position[1]}).circle({radius}).extrude({depth})")
        
        if hole_type == "Counterbore" and "counterbore_diameter" in hole:
            cb_diameter = hole["counterbore_diameter"]
            cb_depth = hole["counterbore_depth"]
            cb_radius = cb_diameter / 2
            self.add_line(f"cb = cq.Workplane('XY').transformed(offset=({trans[0]}, {trans[1]}, {trans[2] + depth - cb_depth}))")
            self.add_line(f"cb = cb.moveTo({position[0]}, {position[1]}).circle({cb_radius}).extrude({cb_depth})")
            self.add_line(f"wp = wp.union(cb)")
            
        elif hole_type == "Countersink" and "countersink_angle" in hole:
            cs_angle = hole.get("countersink_angle", 82)
            cs_depth = diameter / (2 * math.tan(math.radians(cs_angle / 2)))
            cs_radius = diameter / 2
            self.add_line(f"cs = cq.Workplane('XY').transformed(offset=({trans[0]}, {trans[1]}, {trans[2] + depth}))")
            self.add_line(f"cs = cs.moveTo({position[0]}, {position[1]}).circle({cs_radius * 2}).extrude({cs_depth}, taper={-cs_angle/2})")
            self.add_line(f"wp = wp.union(cs)")
            
        self.add_line(f"{result_var} = {result_var}.cut(wp)")
        
    def generate_pattern(self, pattern, result_var):
        pattern_type = pattern["type"]
        count = pattern["count"]
        
        if pattern_type == "linear":
            spacing = pattern["spacing"]
            direction = pattern["direction"]
            mag = math.sqrt(sum(d**2 for d in direction))
            norm_dir = [d/mag for d in direction]
            
            self.add_line(f"original = {result_var}")
            self.add_line(f"for i in range(1, {count}):")
            self.indent += 1
            offset = f"({norm_dir[0]}*{spacing}*i, {norm_dir[1]}*{spacing}*i, {norm_dir[2]}*{spacing}*i)"
            self.add_line(f"copy = original.translate({offset})")
            self.add_line(f"{result_var} = {result_var}.union(copy)")
            self.indent -= 1
            
        elif pattern_type == "polar":
            center = pattern["center"]
            total_angle = pattern["total_angle"]
            axis = pattern.get("axis", [0, 0, 1])
            angle_step = total_angle / (count - 1) if count > 1 else 0
            
            self.add_line(f"original = {result_var}")
            self.add_line(f"for i in range(1, {count}):")
            self.indent += 1
            self.add_line(f"angle = {angle_step} * i")
            self.add_line(f"copy = original.rotate(({center[0]}, {center[1]}, {center[2]}), ({center[0]+axis[0]}, {center[1]+axis[1]}, {center[2]+axis[2]}), angle)")
            self.add_line(f"{result_var} = {result_var}.union(copy)")
            self.indent -= 1
            
    def generate_mirror(self, mirror, result_var):
        plane = mirror["plane"]
        keep_original = mirror.get("keep_original", True)
        
        plane_map = {
            "XY": "XY",
            "XZ": "XZ",
            "YZ": "YZ"
        }
        
        mirror_plane = plane_map.get(plane, "XY")
        self.add_line(f"{result_var} = {result_var}.mirror(mirrorPlane='{mirror_plane}', union={str(keep_original)})")
        
    def generate_fillet(self, fillet, result_var):
        radius = fillet["radius"]
        edge_selector = fillet["edge_selector"]
        
        if edge_selector == "all":
            self.add_line(f"{result_var} = {result_var}.edges().fillet({radius})")
        else:
            self.add_line(f"{result_var} = {result_var}.edges('{edge_selector}').fillet({radius})")
            
    def generate_chamfer(self, chamfer, result_var):
        distance = chamfer["distance"]
        edge_selector = chamfer["edge_selector"]
        
        if edge_selector == "all":
            self.add_line(f"{result_var} = {result_var}.edges().chamfer({distance})")
        else:
            self.add_line(f"{result_var} = {result_var}.edges('{edge_selector}').chamfer({distance})")
            
    def generate_pattern(self, pattern, result_var):
        pattern_type = pattern["type"]
        count = pattern["count"]
        
        if pattern_type == "linear":
            spacing = pattern["spacing"]
            direction = pattern["direction"]
            self.add_line(f"# Linear pattern: {count} instances, spacing {spacing}")
            self.add_line(f"pattern_dir = ({direction[0]}, {direction[1]}, {direction[2]})")
            self.add_line(f"for i in range(1, {count}):")
            self.indent += 1
            self.add_line(f"offset = (pattern_dir[0]*{spacing}*i, pattern_dir[1]*{spacing}*i, pattern_dir[2]*{spacing}*i)")
            self.add_line(f"{result_var} = {result_var}.union({result_var}.translate(offset))")
            self.indent -= 1
        elif pattern_type == "polar":
            center = pattern["center"]
            total_angle = pattern["total_angle"]
            axis = pattern.get("axis", [0, 0, 1])
            if abs(total_angle - 360) < 0.01:
                angle_step = total_angle / count
            else:
                angle_step = total_angle / (count - 1) if count > 1 else 0
            
            self.add_line(f"# Polar pattern: {count} instances around ({center[0]}, {center[1]}, {center[2]})")
            self.add_line(f"for i in range(1, {count}):")
            self.indent += 1
            self.add_line(f"angle = {angle_step} * i")
            self.add_line(f"{result_var} = {result_var}.union({result_var}.rotate(({center[0]}, {center[1]}, {center[2]}), ({axis[0]}, {axis[1]}, {axis[2]}), angle))")
            self.indent -= 1
            
    def get_operation_suffix(self, operation):
        return {
            "NewBodyFeatureOperation": "new",
            "JoinFeatureOperation": "union",
            "CutFeatureOperation": "cut",
            "IntersectFeatureOperation": "intersect"
        }.get(operation, "union")
        
    def euler_to_matrix(self, x, y, z):
        x_rad = math.radians(x)
        y_rad = math.radians(y)
        z_rad = math.radians(z)
        
        cx, sx = math.cos(x_rad), math.sin(x_rad)
        cy, sy = math.cos(y_rad), math.sin(y_rad)
        cz, sz = math.cos(z_rad), math.sin(z_rad)
        
        return [
            [cy*cz, -cy*sz, sy],
            [sx*sy*cz + cx*sz, -sx*sy*sz + cx*cz, -sx*cy],
            [-cx*sy*cz + sx*sz, cx*sy*sz + sx*cz, cx*cy]
        ]
        
    def transform_vector(self, vec, matrix):
        return [
            matrix[0][0]*vec[0] + matrix[0][1]*vec[1] + matrix[0][2]*vec[2],
            matrix[1][0]*vec[0] + matrix[1][1]*vec[1] + matrix[1][2]*vec[2],
            matrix[2][0]*vec[0] + matrix[2][1]*vec[1] + matrix[2][2]*vec[2]
        ]


def generate_cadquery_file(json_input, output_path):
    generator = CadQueryGenerator(json_input)
    code = generator.generate()
    
    with open(output_path, 'w') as f:
        f.write(code)
        
    return output_path
