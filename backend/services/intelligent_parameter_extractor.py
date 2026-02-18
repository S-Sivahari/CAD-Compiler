"""
Intelligent Parameter Extractor - Extracts meaningful design parameters from SCL JSON

Instead of extracting low-level CadQuery code values, this extracts actual design intent
parameters like diameter, height, wall thickness, hole positions, etc.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import math


class IntelligentParameterExtractor:
    """Extracts meaningful design parameters from SCL JSON files"""
    
    def __init__(self):
        self.parameters = []
        
    def extract_from_json(self, json_file_path: str) -> Dict[str, Any]:
        """Extract design parameters from SCL JSON file"""
        
        json_path = Path(json_file_path)
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")
            
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        self.parameters = []
        units = data.get('units', 'mm')
        
        # Extract parameters from each part
        for part_name, part_data in data.get('parts', {}).items():
            part_num = part_name.split('_')[1]
            self._extract_part_parameters(part_data, part_num, units)
        
        return {
            'file': str(json_path),
            'json_data': data,
            'parameters': self.parameters,
            'total_count': len(self.parameters),
            'units': units
        }
    
    def _extract_part_parameters(self, part_data: Dict, part_num: str, units: str):
        """Extract parameters from a single part"""
        
        desc = part_data.get('description', {})
        shape = desc.get('shape', 'Unknown')
        
        # Extract sketch-based parameters
        if 'sketch' in part_data and 'extrusion' in part_data:
            self._extract_extrusion_parameters(part_data, part_num, shape, units)
        
        # Extract revolve parameters
        elif 'revolve_profile' in part_data and 'revolve' in part_data:
            self._extract_revolve_parameters(part_data, part_num, shape, units)
        
        # Extract hole parameters
        elif 'hole_feature' in part_data:
            self._extract_hole_parameters(part_data, part_num, units)
        
        # Extract coordinate system parameters
        if 'coordinate_system' in part_data:
            self._extract_transform_parameters(part_data['coordinate_system'], part_num, units)
        
        # Extract post-processing parameters
        if 'post_processing' in part_data:
            self._extract_postprocess_parameters(part_data['post_processing'], part_num, units)
    
    def _extract_extrusion_parameters(self, part_data: Dict, part_num: str, shape: str, units: str):
        """Extract parameters from sketch + extrusion"""
        
        extrusion = part_data['extrusion']
        sketch = part_data['sketch']
        desc = part_data.get('description', {})
        
        sketch_scale = extrusion.get('sketch_scale', 1.0)
        depth_normal = extrusion.get('extrude_depth_towards_normal', 0.0)
        depth_opposite = extrusion.get('extrude_depth_opposite_normal', 0.0)
        
        # Calculate actual height
        total_height = (depth_normal + depth_opposite) * sketch_scale
        
        # Detect shape type from sketch
        face_1 = sketch.get('face_1', {})
        loop_1 = face_1.get('loop_1', {})
        
        # CYLINDER / CONE - has circle
        if 'circle_1' in loop_1:
            circle = loop_1['circle_1']
            radius_normalized = circle.get('Radius', 0.5)
            actual_radius = radius_normalized * sketch_scale
            actual_diameter = actual_radius * 2
            
            # Check for hollow (multiple loops)
            if 'loop_2' in face_1 and 'circle_1' in face_1['loop_2']:
                # HOLLOW CYLINDER / TUBE
                inner_circle = face_1['loop_2']['circle_1']
                inner_radius_norm = inner_circle.get('Radius', 0.0)
                inner_radius = inner_radius_norm * sketch_scale
                inner_diameter = inner_radius * 2
                wall_thickness = actual_radius - inner_radius
                
                self.parameters.extend([
                    {
                        'name': f'part_{part_num}_outer_diameter',
                        'value': round(actual_diameter, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Outer Diameter',
                        'unit': units,
                        'min': 0.1,
                        'max': 1000.0,
                        'category': 'dimension',
                        'shape': 'Tube',
                        'json_path': f'parts.part_{part_num}.extrusion.sketch_scale'
                    },
                    {
                        'name': f'part_{part_num}_inner_diameter',
                        'value': round(inner_diameter, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Inner Diameter',
                        'unit': units,
                        'min': 0.1,
                        'max': actual_diameter - 0.1,
                        'category': 'dimension',
                        'shape': 'Tube',
                        'json_path': f'parts.part_{part_num}.sketch.face_1.loop_2.circle_1.Radius'
                    },
                    {
                        'name': f'part_{part_num}_wall_thickness',
                        'value': round(wall_thickness, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Wall Thickness',
                        'unit': units,
                        'min': 0.1,
                        'max': actual_radius,
                        'category': 'dimension',
                        'shape': 'Tube',
                        'readonly': True
                    },
                    {
                        'name': f'part_{part_num}_height',
                        'value': round(total_height, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Height',
                        'unit': units,
                        'min': 0.1,
                        'max': 10000.0,
                        'category': 'dimension',
                        'shape': 'Tube',
                        'json_path': f'parts.part_{part_num}.extrusion.extrude_depth_towards_normal'
                    }
                ])
            else:
                # SOLID CYLINDER
                self.parameters.extend([
                    {
                        'name': f'part_{part_num}_diameter',
                        'value': round(actual_diameter, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Diameter',
                        'unit': units,
                        'min': 0.1,
                        'max': 1000.0,
                        'category': 'dimension',
                        'shape': 'Cylinder',
                        'json_path': f'parts.part_{part_num}.extrusion.sketch_scale'
                    },
                    {
                        'name': f'part_{part_num}_radius',
                        'value': round(actual_radius, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Radius',
                        'unit': units,
                        'min': 0.05,
                        'max': 500.0,
                        'category': 'dimension',
                        'shape': 'Cylinder',
                        'readonly': True  # Calculated from diameter
                    },
                    {
                        'name': f'part_{part_num}_height',
                        'value': round(total_height, 3),
                        'type': 'float',
                        'description': f'Part {part_num}: Height',
                        'unit': units,
                        'min': 0.1,
                        'max': 10000.0,
                        'category': 'dimension',
                        'shape': 'Cylinder',
                        'json_path': f'parts.part_{part_num}.extrusion.extrude_depth_towards_normal'
                    }
                ])
        
        # BOX / PLATE - has rectangle (lines)
        elif any(k.startswith('line_') for k in loop_1.keys()):
            # Extract dimensions from description or calculate from sketch
            length = desc.get('length', sketch_scale)
            width = desc.get('width', sketch_scale)
            height = total_height
            
            self.parameters.extend([
                {
                    'name': f'part_{part_num}_length',
                    'value': round(length, 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Length (X)',
                    'unit': units,
                    'min': 0.1,
                    'max': 10000.0,
                    'category': 'dimension',
                    'shape': 'Box',
                    'json_path': f'parts.part_{part_num}.description.length'
                },
                {
                    'name': f'part_{part_num}_width',
                    'value': round(width, 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Width (Y)',
                    'unit': units,
                    'min': 0.1,
                    'max': 10000.0,
                    'category': 'dimension',
                    'shape': 'Box',
                    'json_path': f'parts.part_{part_num}.description.width'
                },
                {
                    'name': f'part_{part_num}_height',
                    'value': round(height, 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Height (Z)',
                    'unit': units,
                    'min': 0.1,
                    'max': 10000.0,
                    'category': 'dimension',
                    'shape': 'Box',
                    'json_path': f'parts.part_{part_num}.extrusion.extrude_depth_towards_normal'
                }
            ])
    
    def _extract_hole_parameters(self, part_data: Dict, part_num: str, units: str):
        """Extract hole feature parameters"""
        
        hole = part_data['hole_feature']
        hole_type = hole.get('hole_type', 'Simple')
        diameter = hole.get('diameter', 5.0)
        depth = hole.get('depth', 10.0)
        position = hole.get('position', [0, 0])
        
        self.parameters.extend([
            {
                'name': f'part_{part_num}_hole_diameter',
                'value': round(diameter, 3),
                'type': 'float',
                'description': f'Part {part_num}: Hole Diameter',
                'unit': units,
                'min': 0.1,
                'max': 100.0,
                'category': 'feature',
                'shape': f'{hole_type} Hole',
                'json_path': f'parts.part_{part_num}.hole_feature.diameter'
            },
            {
                'name': f'part_{part_num}_hole_depth',
                'value': round(depth, 3),
                'type': 'float',
                'description': f'Part {part_num}: Hole Depth',
                'unit': units,
                'min': 0.1,
                'max': 1000.0,
                'category': 'feature',
                'shape': f'{hole_type} Hole',
                'json_path': f'parts.part_{part_num}.hole_feature.depth'
            },
            {
                'name': f'part_{part_num}_hole_position_x',
                'value': round(position[0], 3),
                'type': 'float',
                'description': f'Part {part_num}: Hole X Position',
                'unit': units,
                'min': -1000.0,
                'max': 1000.0,
                'category': 'position',
                'shape': f'{hole_type} Hole',
                'json_path': f'parts.part_{part_num}.hole_feature.position[0]'
            },
            {
                'name': f'part_{part_num}_hole_position_y',
                'value': round(position[1], 3),
                'type': 'float',
                'description': f'Part {part_num}: Hole Y Position',
                'unit': units,
                'min': -1000.0,
                'max': 1000.0,
                'category': 'position',
                'shape': f'{hole_type} Hole',
                'json_path': f'parts.part_{part_num}.hole_feature.position[1]'
            }
        ])
    
    def _extract_transform_parameters(self, coord_system: Dict, part_num: str, units: str):
        """Extract transformation parameters"""
        
        euler = coord_system.get('Euler Angles', [0, 0, 0])
        translation = coord_system.get('Translation Vector', [0, 0, 0])
        
        # Only add if non-zero
        if any(e != 0 for e in euler):
            self.parameters.extend([
                {
                    'name': f'part_{part_num}_rotation_x',
                    'value': round(euler[0], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Rotation X (degrees)',
                    'unit': 'degrees',
                    'min': -360.0,
                    'max': 360.0,
                    'category': 'transform',
                    'json_path': f'parts.part_{part_num}.coordinate_system.Euler Angles[0]'
                },
                {
                    'name': f'part_{part_num}_rotation_y',
                    'value': round(euler[1], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Rotation Y (degrees)',
                    'unit': 'degrees',
                    'min': -360.0,
                    'max': 360.0,
                    'category': 'transform',
                    'json_path': f'parts.part_{part_num}.coordinate_system.Euler Angles[1]'
                },
                {
                    'name': f'part_{part_num}_rotation_z',
                    'value': round(euler[2], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Rotation Z (degrees)',
                    'unit': 'degrees',
                    'min': -360.0,
                    'max': 360.0,
                    'category': 'transform',
                    'json_path': f'parts.part_{part_num}.coordinate_system.Euler Angles[2]'
                }
            ])
        
        if any(t != 0 for t in translation):
            self.parameters.extend([
                {
                    'name': f'part_{part_num}_offset_x',
                    'value': round(translation[0], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: X Offset',
                    'unit': units,
                    'min': -1000.0,
                    'max': 1000.0,
                    'category': 'position',
                    'json_path': f'parts.part_{part_num}.coordinate_system.Translation Vector[0]'
                },
                {
                    'name': f'part_{part_num}_offset_y',
                    'value': round(translation[1], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Y Offset',
                    'unit': units,
                    'min': -1000.0,
                    'max': 1000.0,
                    'category': 'position',
                    'json_path': f'parts.part_{part_num}.coordinate_system.Translation Vector[1]'
                },
                {
                    'name': f'part_{part_num}_offset_z',
                    'value': round(translation[2], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Z Offset',
                    'unit': units,
                    'min': -1000.0,
                    'max': 1000.0,
                    'category': 'position',
                    'json_path': f'parts.part_{part_num}.coordinate_system.Translation Vector[2]'
                }
            ])
    
    def _extract_postprocess_parameters(self, post_processing: List, part_num: str, units: str):
        """Extract fillet and chamfer parameters"""
        
        for idx, proc in enumerate(post_processing, 1):
            if 'radius' in proc:  # Fillet
                self.parameters.append({
                    'name': f'part_{part_num}_fillet_{idx}_radius',
                    'value': round(proc['radius'], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Fillet {idx} Radius',
                    'unit': units,
                    'min': 0.1,
                    'max': 50.0,
                    'category': 'feature',
                    'json_path': f'parts.part_{part_num}.post_processing[{idx-1}].radius'
                })
            
            elif 'distance' in proc:  # Chamfer
                self.parameters.append({
                    'name': f'part_{part_num}_chamfer_{idx}_distance',
                    'value': round(proc['distance'], 3),
                    'type': 'float',
                    'description': f'Part {part_num}: Chamfer {idx} Distance',
                    'unit': units,
                    'min': 0.1,
                    'max': 50.0,
                    'category': 'feature',
                    'json_path': f'parts.part_{part_num}.post_processing[{idx-1}].distance'
                })
    
    def _extract_revolve_parameters(self, part_data: Dict, part_num: str, shape: str, units: str):
        """Extract revolve parameters (for rotation-based shapes)"""
        
        revolve = part_data['revolve']
        angle = revolve.get('angle', 360.0)
        
        self.parameters.append({
            'name': f'part_{part_num}_revolve_angle',
            'value': round(angle, 3),
            'type': 'float',
            'description': f'Part {part_num}: Revolve Angle',
            'unit': 'degrees',
            'min': 0.1,
            'max': 360.0,
            'category': 'feature',
            'shape': 'Revolve',
            'json_path': f'parts.part_{part_num}.revolve.angle'
        })
