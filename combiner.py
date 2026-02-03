"""
Combiner System
Tools for combining, positioning, and transforming template parts
"""

import sys
sys.path.append(r"C:\Program Files\FreeCAD 1.0\bin")
sys.path.append(r"C:\Program Files\FreeCAD 1.0\lib")

import FreeCAD as App
import Part


# ============================================================================
# POSITIONING & TRANSFORMATION
# ============================================================================

def translate(shape, x=0, y=0, z=0):
    """Move a shape in 3D space"""
    shape.translate(App.Vector(x, y, z))
    return shape


def rotate(shape, axis='z', angle=90, center=(0,0,0)):
    """Rotate a shape around an axis"""
    center_vec = App.Vector(*center)
    
    if axis.lower() == 'x':
        axis_vec = App.Vector(1, 0, 0)
    elif axis.lower() == 'y':
        axis_vec = App.Vector(0, 1, 0)
    else:  # z
        axis_vec = App.Vector(0, 0, 1)
    
    shape.rotate(center_vec, axis_vec, angle)
    return shape


def mirror(shape, plane='xy'):
    """Mirror a shape across a plane"""
    if plane.lower() == 'xy':
        normal = App.Vector(0, 0, 1)
    elif plane.lower() == 'xz':
        normal = App.Vector(0, 1, 0)
    else:  # yz
        normal = App.Vector(1, 0, 0)
    
    base = App.Vector(0, 0, 0)
    mirrored = shape.mirror(base, normal)
    return mirrored


def scale(shape, factor_x=1.0, factor_y=1.0, factor_z=1.0):
    """Scale a shape"""
    import Part
    matrix = App.Matrix()
    matrix.scale(App.Vector(factor_x, factor_y, factor_z))
    scaled = shape.transformGeometry(matrix)
    return scaled


# ============================================================================
# BOOLEAN OPERATIONS
# ============================================================================

def combine(shape1, shape2, operation='union'):
    """Combine two shapes using boolean operation
    
    Args:
        shape1: First shape
        shape2: Second shape
        operation: 'union', 'difference', 'intersection'
    """
    if operation.lower() == 'union' or operation.lower() == 'fuse':
        result = shape1.fuse(shape2)
        print(f"✓ Union operation completed")
    elif operation.lower() == 'difference' or operation.lower() == 'cut':
        result = shape1.cut(shape2)
        print(f"✓ Difference operation completed")
    elif operation.lower() == 'intersection' or operation.lower() == 'common':
        result = shape1.common(shape2)
        print(f"✓ Intersection operation completed")
    else:
        print(f"❌ Unknown operation: {operation}")
        return shape1
    
    return result


def fuse_multiple(shapes):
    """Fuse multiple shapes together"""
    if not shapes:
        return None
    
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    
    print(f"✓ Fused {len(shapes)} shapes together")
    return result


# ============================================================================
# PATTERN OPERATIONS
# ============================================================================

def linear_pattern(shape, direction=(1,0,0), count=5, spacing=20):
    """Create a linear pattern of shapes"""
    import copy
    
    patterns = []
    dir_vec = App.Vector(*direction)
    
    for i in range(count):
        new_shape = shape.copy()
        offset = dir_vec * (spacing * i)
        new_shape.translate(offset)
        patterns.append(new_shape)
    
    print(f"✓ Linear pattern: {count} instances, spacing={spacing}mm")
    return patterns


def circular_pattern(shape, center=(0,0,0), axis=(0,0,1), count=8, angle=360):
    """Create a circular pattern of shapes"""
    import copy
    import math
    
    patterns = []
    center_vec = App.Vector(*center)
    axis_vec = App.Vector(*axis)
    angle_step = angle / count
    
    for i in range(count):
        new_shape = shape.copy()
        new_shape.rotate(center_vec, axis_vec, angle_step * i)
        patterns.append(new_shape)
    
    print(f"✓ Circular pattern: {count} instances around {angle}°")
    return patterns


def grid_pattern(shape, rows=3, cols=4, row_spacing=30, col_spacing=40):
    """Create a 2D grid pattern of shapes"""
    import copy
    
    patterns = []
    
    for i in range(rows):
        for j in range(cols):
            new_shape = shape.copy()
            x_offset = j * col_spacing - (cols-1)*col_spacing/2
            y_offset = i * row_spacing - (rows-1)*row_spacing/2
            new_shape.translate(App.Vector(x_offset, y_offset, 0))
            patterns.append(new_shape)
    
    print(f"✓ Grid pattern: {rows}×{cols}, spacing {row_spacing}×{col_spacing}mm")
    return patterns


# ============================================================================
# ALIGNMENT & POSITIONING HELPERS
# ============================================================================

def align_to_face(shape, target_shape, face='top'):
    """Align shape to a face of target shape"""
    bbox = target_shape.BoundBox
    
    if face.lower() == 'top':
        z_offset = bbox.ZMax
        shape.translate(App.Vector(0, 0, z_offset))
    elif face.lower() == 'bottom':
        z_offset = bbox.ZMin - shape.BoundBox.ZMax
        shape.translate(App.Vector(0, 0, z_offset))
    elif face.lower() == 'left':
        x_offset = bbox.XMin - shape.BoundBox.XMax
        shape.translate(App.Vector(x_offset, 0, 0))
    elif face.lower() == 'right':
        x_offset = bbox.XMax
        shape.translate(App.Vector(x_offset, 0, 0))
    elif face.lower() == 'front':
        y_offset = bbox.YMin - shape.BoundBox.YMax
        shape.translate(App.Vector(0, y_offset, 0))
    elif face.lower() == 'back':
        y_offset = bbox.YMax
        shape.translate(App.Vector(0, y_offset, 0))
    
    print(f"✓ Aligned to {face} face")
    return shape


def center_on_shape(shape, target_shape):
    """Center shape on target shape's center"""
    target_bbox = target_shape.BoundBox
    shape_bbox = shape.BoundBox
    
    x_offset = target_bbox.Center.x - shape_bbox.Center.x
    y_offset = target_bbox.Center.y - shape_bbox.Center.y
    
    shape.translate(App.Vector(x_offset, y_offset, 0))
    print(f"✓ Centered on target shape")
    return shape


# ============================================================================
# ASSEMBLY BUILDER
# ============================================================================

class Assembly:
    """Helper class to build complex assemblies"""
    
    def __init__(self, name="Assembly"):
        self.name = name
        self.parts = []
        print(f"✓ Assembly '{name}' initialized")
    
    def add_part(self, shape, name=None):
        """Add a part to the assembly"""
        self.parts.append({
            'shape': shape,
            'name': name or f"Part{len(self.parts)+1}"
        })
        print(f"  + Added {name or 'part'} to assembly")
        return self
    
    def combine_all(self, operation='union'):
        """Combine all parts in the assembly"""
        if not self.parts:
            print("❌ No parts in assembly")
            return None
        
        result = self.parts[0]['shape']
        
        for i, part in enumerate(self.parts[1:], 1):
            if operation.lower() == 'union':
                result = result.fuse(part['shape'])
            elif operation.lower() == 'difference':
                result = result.cut(part['shape'])
            elif operation.lower() == 'intersection':
                result = result.common(part['shape'])
        
        print(f"✓ Combined {len(self.parts)} parts using {operation}")
        return result
    
    def get_part_shapes(self):
        """Get list of all part shapes"""
        return [p['shape'] for p in self.parts]
    
    def info(self):
        """Print assembly information"""
        print(f"\nAssembly: {self.name}")
        print(f"  Parts: {len(self.parts)}")
        for i, part in enumerate(self.parts, 1):
            bbox = part['shape'].BoundBox
            print(f"  {i}. {part['name']} - Size: {bbox.XLength:.1f}×{bbox.YLength:.1f}×{bbox.ZLength:.1f}mm")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_bounding_box(shape):
    """Get bounding box dimensions"""
    bbox = shape.BoundBox
    return {
        'length': bbox.XLength,
        'width': bbox.YLength,
        'height': bbox.ZLength,
        'center': (bbox.Center.x, bbox.Center.y, bbox.Center.z),
        'min': (bbox.XMin, bbox.YMin, bbox.ZMin),
        'max': (bbox.XMax, bbox.YMax, bbox.ZMax)
    }


def simplify_shape(shape):
    """Attempt to simplify a shape (remove redundant faces)"""
    try:
        simplified = shape.removeSplitter()
        print("✓ Shape simplified")
        return simplified
    except:
        print("⚠ Could not simplify shape")
        return shape


def check_valid(shape):
    """Check if a shape is valid"""
    if shape.isValid():
        print("✓ Shape is valid")
        return True
    else:
        print("❌ Shape is invalid!")
        return False
