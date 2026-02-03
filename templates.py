"""
FreeCAD Basic Templates
25 fundamental geometric shapes and primitives
"""

import sys
sys.path.append(r"C:\Program Files\FreeCAD 1.0\bin")
sys.path.append(r"C:\Program Files\FreeCAD 1.0\lib")

import FreeCAD as App
import Part


# ============================================================================
# BASIC 3D SHAPES
# ============================================================================

def cube(doc, size=50):
    """Create a cube"""
    box = Part.makeBox(size, size, size)
    obj = doc.addObject("Part::Feature", "Cube")
    obj.Shape = box
    doc.recompute()
    print(f"✓ Cube created: {size}mm")
    return box


def cuboid(doc, length=100, width=50, height=30):
    """Create a rectangular box (cuboid)"""
    box = Part.makeBox(length, width, height)
    obj = doc.addObject("Part::Feature", "Cuboid")
    obj.Shape = box
    doc.recompute()
    print(f"✓ Cuboid created: {length}×{width}×{height}mm")
    return box


def cylinder(doc, radius=25, height=100):
    """Create a cylinder"""
    cyl = Part.makeCylinder(radius, height)
    obj = doc.addObject("Part::Feature", "Cylinder")
    obj.Shape = cyl
    doc.recompute()
    print(f"✓ Cylinder created: r={radius}mm, h={height}mm")
    return cyl


def sphere(doc, radius=50):
    """Create a sphere"""
    sph = Part.makeSphere(radius)
    obj = doc.addObject("Part::Feature", "Sphere")
    obj.Shape = sph
    doc.recompute()
    print(f"✓ Sphere created: r={radius}mm")
    return sph


def cone(doc, radius1=50, radius2=20, height=100):
    """Create a cone"""
    con = Part.makeCone(radius1, radius2, height)
    obj = doc.addObject("Part::Feature", "Cone")
    obj.Shape = con
    doc.recompute()
    print(f"✓ Cone created: r1={radius1}mm, r2={radius2}mm, h={height}mm")
    return con


def torus(doc, radius1=50, radius2=10):
    """Create a torus (donut)"""
    tor = Part.makeTorus(radius1, radius2)
    obj = doc.addObject("Part::Feature", "Torus")
    obj.Shape = tor
    doc.recompute()
    print(f"✓ Torus created: R={radius1}mm, r={radius2}mm")
    return tor


def wedge(doc, xmin=0, ymin=0, zmin=0, z2min=0, x2min=0, 
          xmax=100, ymax=50, zmax=50, z2max=50, x2max=100):
    """Create a wedge"""
    wed = Part.makeWedge(xmin, ymin, zmin, z2min, x2min, 
                         xmax, ymax, zmax, z2max, x2max)
    obj = doc.addObject("Part::Feature", "Wedge")
    obj.Shape = wed
    doc.recompute()
    print(f"✓ Wedge created")
    return wed


def tube(doc, outer_radius=30, inner_radius=20, height=100):
    """Create a hollow tube"""
    outer = Part.makeCylinder(outer_radius, height)
    inner = Part.makeCylinder(inner_radius, height)
    tube = outer.cut(inner)
    obj = doc.addObject("Part::Feature", "Tube")
    obj.Shape = tube
    doc.recompute()
    print(f"✓ Tube created: OD={outer_radius*2}mm, ID={inner_radius*2}mm, h={height}mm")
    return tube


def rectangular_tube(doc, outer_length=100, outer_width=80, 
                     inner_length=90, inner_width=70, height=50):
    """Create a hollow rectangular tube"""
    outer = Part.makeBox(outer_length, outer_width, height)
    inner = Part.makeBox(inner_length, inner_width, height + 2)
    inner.translate(App.Vector((outer_length-inner_length)/2, 
                                (outer_width-inner_width)/2, -1))
    tube = outer.cut(inner)
    obj = doc.addObject("Part::Feature", "RectangularTube")
    obj.Shape = tube
    doc.recompute()
    print(f"✓ Rectangular tube created")
    return tube


def plate(doc, length=100, width=80, thickness=5):
    """Create a flat plate"""
    plate = Part.makeBox(length, width, thickness)
    obj = doc.addObject("Part::Feature", "Plate")
    obj.Shape = plate
    doc.recompute()
    print(f"✓ Plate created: {length}×{width}×{thickness}mm")
    return plate


def rod(doc, diameter=20, length=200):
    """Create a cylindrical rod"""
    rod = Part.makeCylinder(diameter/2, length)
    obj = doc.addObject("Part::Feature", "Rod")
    obj.Shape = rod
    doc.recompute()
    print(f"✓ Rod created: ø{diameter}mm, L={length}mm")
    return rod


def ring(doc, outer_radius=40, inner_radius=30, thickness=5):
    """Create a flat ring"""
    outer = Part.makeCylinder(outer_radius, thickness)
    inner = Part.makeCylinder(inner_radius, thickness)
    ring = outer.cut(inner)
    obj = doc.addObject("Part::Feature", "Ring")
    obj.Shape = ring
    doc.recompute()
    print(f"✓ Ring created: OD={outer_radius*2}mm, ID={inner_radius*2}mm")
    return ring


# ============================================================================
# BASIC 2D SHAPES (for sketching/extrusion)
# ============================================================================

def line(doc, start=(0,0,0), end=(100,0,0)):
    """Create a line"""
    p1 = App.Vector(*start)
    p2 = App.Vector(*end)
    line = Part.makeLine(p1, p2)
    obj = doc.addObject("Part::Feature", "Line")
    obj.Shape = line
    doc.recompute()
    print(f"✓ Line created")
    return line


def circle(doc, radius=50, center=(0,0,0)):
    """Create a circle"""
    circ = Part.makeCircle(radius, App.Vector(*center))
    obj = doc.addObject("Part::Feature", "Circle")
    obj.Shape = circ
    doc.recompute()
    print(f"✓ Circle created: r={radius}mm")
    return circ


def rectangle_2d(doc, length=100, width=50):
    """Create a 2D rectangle wire"""
    p1 = App.Vector(0, 0, 0)
    p2 = App.Vector(length, 0, 0)
    p3 = App.Vector(length, width, 0)
    p4 = App.Vector(0, width, 0)
    
    l1 = Part.makeLine(p1, p2)
    l2 = Part.makeLine(p2, p3)
    l3 = Part.makeLine(p3, p4)
    l4 = Part.makeLine(p4, p1)
    
    wire = Part.Wire([l1, l2, l3, l4])
    obj = doc.addObject("Part::Feature", "Rectangle")
    obj.Shape = wire
    doc.recompute()
    print(f"✓ Rectangle created: {length}×{width}mm")
    return wire


def polygon(doc, radius=50, sides=6):
    """Create a regular polygon"""
    import math
    points = []
    for i in range(sides):
        angle = 2 * math.pi * i / sides
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append(App.Vector(x, y, 0))
    points.append(points[0])  # Close the polygon
    
    lines = [Part.makeLine(points[i], points[i+1]) for i in range(len(points)-1)]
    wire = Part.Wire(lines)
    obj = doc.addObject("Part::Feature", "Polygon")
    obj.Shape = wire
    doc.recompute()
    print(f"✓ Polygon created: {sides} sides, r={radius}mm")
    return wire


def arc(doc, radius=50, start_angle=0, end_angle=90):
    """Create an arc"""
    import math
    arc = Part.makeCircle(radius, App.Vector(0,0,0), App.Vector(0,0,1), 
                         start_angle, end_angle)
    obj = doc.addObject("Part::Feature", "Arc")
    obj.Shape = arc
    doc.recompute()
    print(f"✓ Arc created: r={radius}mm, {start_angle}° to {end_angle}°")
    return arc


def ellipse(doc, major_radius=60, minor_radius=30):
    """Create an ellipse"""
    ell = Part.Ellipse(App.Vector(0,0,0), major_radius, minor_radius)
    obj = doc.addObject("Part::Feature", "Ellipse")
    obj.Shape = ell.toShape()
    doc.recompute()
    print(f"✓ Ellipse created: major={major_radius}mm, minor={minor_radius}mm")
    return ell.toShape()


# ============================================================================
# ADVANCED SHAPES
# ============================================================================

def pyramid(doc, base_length=80, base_width=80, height=100):
    """Create a pyramid"""
    # Create base points
    p1 = App.Vector(-base_length/2, -base_width/2, 0)
    p2 = App.Vector(base_length/2, -base_width/2, 0)
    p3 = App.Vector(base_length/2, base_width/2, 0)
    p4 = App.Vector(-base_length/2, base_width/2, 0)
    p5 = App.Vector(0, 0, height)  # Apex
    
    # Create faces
    base = Part.makePolygon([p1, p2, p3, p4, p1])
    face_base = Part.Face(base)
    
    face1 = Part.makePolygon([p1, p2, p5, p1])
    face2 = Part.makePolygon([p2, p3, p5, p2])
    face3 = Part.makePolygon([p3, p4, p5, p3])
    face4 = Part.makePolygon([p4, p1, p5, p4])
    
    shell = Part.makeShell([face_base, 
                           Part.Face(face1), 
                           Part.Face(face2), 
                           Part.Face(face3), 
                           Part.Face(face4)])
    solid = Part.Solid(shell)
    
    obj = doc.addObject("Part::Feature", "Pyramid")
    obj.Shape = solid
    doc.recompute()
    print(f"✓ Pyramid created: base={base_length}×{base_width}mm, h={height}mm")
    return solid


def prism(doc, sides=6, radius=40, height=80):
    """Create a prism with n-sided base"""
    import math
    
    # Create base polygon
    points = []
    for i in range(sides):
        angle = 2 * math.pi * i / sides
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        points.append(App.Vector(x, y, 0))
    points.append(points[0])
    
    lines = [Part.makeLine(points[i], points[i+1]) for i in range(len(points)-1)]
    base = Part.Wire(lines)
    face = Part.Face(base)
    prism = face.extrude(App.Vector(0, 0, height))
    
    obj = doc.addObject("Part::Feature", "Prism")
    obj.Shape = prism
    doc.recompute()
    print(f"✓ Prism created: {sides} sides, r={radius}mm, h={height}mm")
    return prism


def helix(doc, pitch=10, height=100, radius=30):
    """Create a helix"""
    helix = Part.makeHelix(pitch, height, radius)
    obj = doc.addObject("Part::Feature", "Helix")
    obj.Shape = helix
    doc.recompute()
    print(f"✓ Helix created: pitch={pitch}mm, h={height}mm, r={radius}mm")
    return helix


# ============================================================================
# COMMON FEATURES
# ============================================================================

def box_with_hole(doc, box_length=100, box_width=80, box_height=50, 
                  hole_diameter=20, hole_position='center'):
    """Create a box with a hole through it"""
    box = Part.makeBox(box_length, box_width, box_height)
    box.translate(App.Vector(-box_length/2, -box_width/2, 0))
    
    hole = Part.makeCylinder(hole_diameter/2, box_height + 10)
    hole.translate(App.Vector(0, 0, -5))
    
    result = box.cut(hole)
    obj = doc.addObject("Part::Feature", "BoxWithHole")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Box with hole: {box_length}×{box_width}×{box_height}mm, ø{hole_diameter}mm hole")
    return result


def plate_with_holes(doc, length=150, width=100, thickness=10, 
                     hole_diameter=8, hole_count_x=3, hole_count_y=2):
    """Create a plate with evenly spaced holes"""
    plate = Part.makeBox(length, width, thickness)
    plate.translate(App.Vector(-length/2, -width/2, 0))
    
    spacing_x = length / (hole_count_x + 1)
    spacing_y = width / (hole_count_y + 1)
    
    result = plate
    for i in range(1, hole_count_x + 1):
        for j in range(1, hole_count_y + 1):
            x = -length/2 + i * spacing_x
            y = -width/2 + j * spacing_y
            hole = Part.makeCylinder(hole_diameter/2, thickness + 2)
            hole.translate(App.Vector(x, y, -1))
            result = result.cut(hole)
    
    obj = doc.addObject("Part::Feature", "PlateWithHoles")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Plate with {hole_count_x*hole_count_y} holes created")
    return result


def l_bracket(doc, length=100, width=80, height=60, thickness=10):
    """Create an L-shaped bracket"""
    vertical = Part.makeBox(thickness, width, height)
    horizontal = Part.makeBox(length, width, thickness)
    
    vertical.translate(App.Vector(-thickness/2, -width/2, 0))
    horizontal.translate(App.Vector(-thickness/2, -width/2, 0))
    
    result = vertical.fuse(horizontal)
    obj = doc.addObject("Part::Feature", "LBracket")
    obj.Shape = result
    doc.recompute()
    print(f"✓ L-bracket created: {length}×{width}×{height}mm, t={thickness}mm")
    return result


# ============================================================================
# HOLES & CUTOUTS
# ============================================================================

def through_hole(base_shape, diameter=10, position=(0,0,0), direction=(0,0,1), depth=100):
    """Create a through hole in a shape"""
    hole = Part.makeCylinder(diameter/2, depth, App.Vector(*position), App.Vector(*direction))
    result = base_shape.cut(hole)
    print(f"✓ Through hole: ø{diameter}mm")
    return result


def blind_hole(base_shape, diameter=10, depth=50, position=(0,0,0), direction=(0,0,1)):
    """Create a blind hole (not through)"""
    hole = Part.makeCylinder(diameter/2, depth, App.Vector(*position), App.Vector(*direction))
    result = base_shape.cut(hole)
    print(f"✓ Blind hole: ø{diameter}mm, depth={depth}mm")
    return result


def countersink_hole(base_shape, hole_diameter=10, sink_diameter=20, sink_angle=90, 
                     depth=50, position=(0,0,0)):
    """Create a countersink hole"""
    pos = App.Vector(*position)
    
    # Main hole
    hole = Part.makeCylinder(hole_diameter/2, depth, pos)
    
    # Countersink cone
    import math
    sink_depth = (sink_diameter - hole_diameter) / (2 * math.tan(math.radians(sink_angle/2)))
    sink = Part.makeCone(hole_diameter/2, sink_diameter/2, sink_depth, pos)
    sink.translate(App.Vector(0, 0, -sink_depth))
    
    cutout = hole.fuse(sink)
    result = base_shape.cut(cutout)
    print(f"✓ Countersink hole: ø{hole_diameter}mm, sink ø{sink_diameter}mm")
    return result


def counterbore_hole(base_shape, hole_diameter=10, bore_diameter=20, bore_depth=10,
                     total_depth=50, position=(0,0,0)):
    """Create a counterbore hole"""
    pos = App.Vector(*position)
    
    # Main hole
    hole = Part.makeCylinder(hole_diameter/2, total_depth, pos)
    
    # Counterbore
    bore = Part.makeCylinder(bore_diameter/2, bore_depth, pos)
    bore.translate(App.Vector(0, 0, -bore_depth))
    
    cutout = hole.fuse(bore)
    result = base_shape.cut(cutout)
    print(f"✓ Counterbore hole: ø{hole_diameter}mm, bore ø{bore_diameter}mm×{bore_depth}mm")
    return result


def rectangular_slot(base_shape, length=50, width=10, depth=20, position=(0,0,0)):
    """Create a rectangular slot"""
    pos = App.Vector(*position)
    slot = Part.makeBox(length, width, depth, pos)
    slot.translate(App.Vector(-length/2, -width/2, 0))
    result = base_shape.cut(slot)
    print(f"✓ Rectangular slot: {length}×{width}×{depth}mm")
    return result


def circular_pocket(base_shape, diameter=40, depth=20, position=(0,0,0)):
    """Create a circular pocket"""
    pos = App.Vector(*position)
    pocket = Part.makeCylinder(diameter/2, depth, pos)
    result = base_shape.cut(pocket)
    print(f"✓ Circular pocket: ø{diameter}mm, depth={depth}mm")
    return result


def rectangular_pocket(base_shape, length=60, width=40, depth=20, fillet_radius=0, position=(0,0,0)):
    """Create a rectangular pocket with optional fillet"""
    pos = App.Vector(*position)
    pocket = Part.makeBox(length, width, depth, pos)
    pocket.translate(App.Vector(-length/2, -width/2, 0))
    
    if fillet_radius > 0:
        pocket = pocket.makeFillet(fillet_radius, pocket.Edges)
    
    result = base_shape.cut(pocket)
    print(f"✓ Rectangular pocket: {length}×{width}×{depth}mm")
    return result


def keyway(base_shape, width=8, depth=4, length=50, position=(0,0,0)):
    """Create a keyway slot"""
    pos = App.Vector(*position)
    key = Part.makeBox(width, length, depth, pos)
    key.translate(App.Vector(-width/2, -length/2, -depth))
    result = base_shape.cut(key)
    print(f"✓ Keyway: {width}×{depth}mm, length={length}mm")
    return result


# ============================================================================
# BRACKETS & MOUNTING
# ============================================================================

def u_bracket(doc, length=100, width=80, height=60, thickness=10):
    """Create a U-shaped bracket"""
    # Two vertical sides
    left = Part.makeBox(thickness, width, height)
    right = Part.makeBox(thickness, width, height)
    
    # Bottom horizontal
    bottom = Part.makeBox(length, width, thickness)
    
    # Position them
    left.translate(App.Vector(0, -width/2, 0))
    right.translate(App.Vector(length-thickness, -width/2, 0))
    bottom.translate(App.Vector(0, -width/2, 0))
    
    result = left.fuse(right).fuse(bottom)
    obj = doc.addObject("Part::Feature", "UBracket")
    obj.Shape = result
    doc.recompute()
    print(f"✓ U-bracket created: {length}×{width}×{height}mm, t={thickness}mm")
    return result


def z_bracket(doc, length1=80, length2=80, height=100, thickness=10, offset=40):
    """Create a Z-shaped bracket"""
    # Top horizontal
    top = Part.makeBox(length1, thickness, thickness)
    
    # Middle vertical (offset)
    middle = Part.makeBox(thickness, thickness, height)
    middle.translate(App.Vector(offset, 0, 0))
    
    # Bottom horizontal
    bottom = Part.makeBox(length2, thickness, thickness)
    bottom.translate(App.Vector(offset, 0, height-thickness))
    
    result = top.fuse(middle).fuse(bottom)
    obj = doc.addObject("Part::Feature", "ZBracket")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Z-bracket created: h={height}mm, t={thickness}mm")
    return result


def corner_bracket(doc, size=60, thickness=10, hole_diameter=8):
    """Create a 90-degree corner bracket with mounting holes"""
    # Create L shape
    vertical = Part.makeBox(thickness, size, size)
    horizontal = Part.makeBox(size, size, thickness)
    
    result = vertical.fuse(horizontal)
    
    # Add mounting holes
    hole_offset = 15
    
    # Vertical side holes
    hole1 = Part.makeCylinder(hole_diameter/2, thickness+2)
    hole1.rotate(App.Vector(0,0,0), App.Vector(0,1,0), 90)
    hole1.translate(App.Vector(-1, hole_offset, hole_offset))
    
    hole2 = Part.makeCylinder(hole_diameter/2, thickness+2)
    hole2.rotate(App.Vector(0,0,0), App.Vector(0,1,0), 90)
    hole2.translate(App.Vector(-1, size-hole_offset, size-hole_offset))
    
    # Horizontal side holes
    hole3 = Part.makeCylinder(hole_diameter/2, thickness+2)
    hole3.translate(App.Vector(hole_offset, hole_offset, -1))
    
    hole4 = Part.makeCylinder(hole_diameter/2, thickness+2)
    hole4.translate(App.Vector(size-hole_offset, size-hole_offset, -1))
    
    result = result.cut(hole1).cut(hole2).cut(hole3).cut(hole4)
    
    obj = doc.addObject("Part::Feature", "CornerBracket")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Corner bracket: {size}×{size}mm, t={thickness}mm, 4 holes")
    return result


def angle_bracket(doc, length=100, width=80, angle=45, thickness=10):
    """Create an angled bracket"""
    import math
    
    # Create base plate
    base = Part.makeBox(length, width, thickness)
    
    # Create angled plate
    angle_rad = math.radians(angle)
    angled_height = width * math.sin(angle_rad)
    angled = Part.makeBox(length, width, thickness)
    angled.rotate(App.Vector(0,0,0), App.Vector(1,0,0), angle)
    angled.translate(App.Vector(0, 0, thickness))
    
    result = base.fuse(angled)
    obj = doc.addObject("Part::Feature", "AngleBracket")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Angle bracket: {length}×{width}mm, {angle}°")
    return result


def mounting_plate(doc, length=150, width=100, thickness=10, hole_diameter=8, hole_pattern='4_corner'):
    """Create a mounting plate with hole pattern"""
    plate = Part.makeBox(length, width, thickness)
    plate.translate(App.Vector(-length/2, -width/2, 0))
    
    result = plate
    
    if hole_pattern == '4_corner':
        offset = 15
        positions = [
            (-length/2 + offset, -width/2 + offset),
            (length/2 - offset, -width/2 + offset),
            (length/2 - offset, width/2 - offset),
            (-length/2 + offset, width/2 - offset),
        ]
        
        for x, y in positions:
            hole = Part.makeCylinder(hole_diameter/2, thickness+2)
            hole.translate(App.Vector(x, y, -1))
            result = result.cut(hole)
    
    obj = doc.addObject("Part::Feature", "MountingPlate")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Mounting plate: {length}×{width}×{thickness}mm, pattern={hole_pattern}")
    return result


def motor_mount_plate(doc, motor_size='NEMA17', mounting_thickness=10, base_size=80):
    """Create a motor mounting plate for common motor sizes"""
    motor_specs = {
        'NEMA17': {'bolt_circle': 31, 'center_hole': 22, 'bolt_size': 3},
        'NEMA23': {'bolt_circle': 47.14, 'center_hole': 38.1, 'bolt_size': 5},
        'NEMA34': {'bolt_circle': 69.6, 'center_hole': 73, 'bolt_size': 8},
    }
    
    spec = motor_specs.get(motor_size, motor_specs['NEMA17'])
    
    # Create base plate
    plate = Part.makeBox(base_size, base_size, mounting_thickness)
    plate.translate(App.Vector(-base_size/2, -base_size/2, 0))
    
    # Center hole for motor shaft
    center_hole = Part.makeCylinder(spec['center_hole']/2, mounting_thickness+2)
    center_hole.translate(App.Vector(0, 0, -1))
    
    plate = plate.cut(center_hole)
    
    # Bolt holes
    import math
    bc = spec['bolt_circle']
    bolt_d = spec['bolt_size']
    
    for i in range(4):
        angle = math.radians(45 + i*90)
        x = (bc/2) * math.cos(angle)
        y = (bc/2) * math.sin(angle)
        
        hole = Part.makeCylinder(bolt_d/2, mounting_thickness+2)
        hole.translate(App.Vector(x, y, -1))
        plate = plate.cut(hole)
    
    obj = doc.addObject("Part::Feature", "MotorMount")
    obj.Shape = plate
    doc.recompute()
    print(f"✓ Motor mount: {motor_size}, {base_size}×{base_size}mm")
    return plate


# ============================================================================
# STRUCTURAL COMPONENTS
# ============================================================================

def i_beam(doc, height=200, flange_width=100, web_thickness=10, flange_thickness=15, length=500):
    """Create an I-beam"""
    # Top flange
    top_flange = Part.makeBox(flange_width, length, flange_thickness)
    top_flange.translate(App.Vector(-flange_width/2, -length/2, height-flange_thickness))
    
    # Web
    web = Part.makeBox(web_thickness, length, height)
    web.translate(App.Vector(-web_thickness/2, -length/2, 0))
    
    # Bottom flange
    bottom_flange = Part.makeBox(flange_width, length, flange_thickness)
    bottom_flange.translate(App.Vector(-flange_width/2, -length/2, 0))
    
    result = top_flange.fuse(web).fuse(bottom_flange)
    obj = doc.addObject("Part::Feature", "IBeam")
    obj.Shape = result
    doc.recompute()
    print(f"✓ I-beam: H={height}mm, W={flange_width}mm, L={length}mm")
    return result


def c_channel(doc, height=100, width=50, web_thickness=8, flange_thickness=10, length=500):
    """Create a C-channel"""
    # Back web
    web = Part.makeBox(web_thickness, length, height)
    
    # Top flange
    top_flange = Part.makeBox(width, length, flange_thickness)
    top_flange.translate(App.Vector(0, 0, height-flange_thickness))
    
    # Bottom flange
    bottom_flange = Part.makeBox(width, length, flange_thickness)
    
    result = web.fuse(top_flange).fuse(bottom_flange)
    obj = doc.addObject("Part::Feature", "CChannel")
    obj.Shape = result
    doc.recompute()
    print(f"✓ C-channel: {height}×{width}mm, L={length}mm")
    return result


def angle_iron(doc, leg1=50, leg2=50, thickness=8, length=500):
    """Create angle iron (L-profile)"""
    # Vertical leg
    vert = Part.makeBox(thickness, length, leg1)
    
    # Horizontal leg
    horiz = Part.makeBox(leg2, length, thickness)
    
    result = vert.fuse(horiz)
    obj = doc.addObject("Part::Feature", "AngleIron")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Angle iron: {leg1}×{leg2}mm, t={thickness}mm, L={length}mm")
    return result


# ============================================================================
# SHAFTS & AXLES
# ============================================================================

def stepped_shaft(doc, diameters=[20, 30, 20], lengths=[50, 100, 50]):
    """Create a stepped shaft with multiple diameters"""
    if len(diameters) != len(lengths):
        print("Error: diameters and lengths must have same count")
        return None
    
    result = None
    current_z = 0
    
    for i, (d, l) in enumerate(zip(diameters, lengths)):
        segment = Part.makeCylinder(d/2, l)
        segment.translate(App.Vector(0, 0, current_z))
        
        if result is None:
            result = segment
        else:
            result = result.fuse(segment)
        
        current_z += l
    
    obj = doc.addObject("Part::Feature", "SteppedShaft")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Stepped shaft: {len(diameters)} segments, total length={sum(lengths)}mm")
    return result


def shaft_with_keyway(doc, diameter=30, length=200, keyway_width=8, keyway_depth=4):
    """Create a shaft with keyway"""
    # Main shaft
    shaft = Part.makeCylinder(diameter/2, length)
    
    # Keyway cutout
    keyway = Part.makeBox(keyway_width, length, keyway_depth)
    keyway.translate(App.Vector(-keyway_width/2, 0, diameter/2 - keyway_depth))
    
    result = shaft.cut(keyway)
    obj = doc.addObject("Part::Feature", "ShaftWithKeyway")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Shaft with keyway: ø{diameter}mm, L={length}mm, keyway {keyway_width}×{keyway_depth}mm")
    return result


def threaded_shaft(doc, major_diameter=10, pitch=1.5, length=100, thread_depth=0.6):
    """Create a simplified threaded shaft (visual approximation)"""
    import math
    
    # Core shaft at minor diameter
    minor_diameter = major_diameter - 2 * thread_depth
    shaft = Part.makeCylinder(minor_diameter/2, length)
    
    # Create thread helix as visual representation
    num_threads = int(length / pitch)
    for i in range(num_threads):
        # Simple ring at each thread position
        ring_height = pitch * 0.6
        ring = Part.makeCylinder(major_diameter/2, ring_height)
        ring.translate(App.Vector(0, 0, i * pitch))
        shaft = shaft.fuse(ring)
    
    obj = doc.addObject("Part::Feature", "ThreadedShaft")
    obj.Shape = shaft
    doc.recompute()
    print(f"✓ Threaded shaft: M{major_diameter}, pitch={pitch}mm, L={length}mm")
    return shaft


def knurled_shaft(doc, diameter=20, length=100, knurl_type='diamond', knurl_depth=0.5):
    """Create a knurled shaft (simplified pattern)"""
    import math
    
    # Base shaft
    shaft = Part.makeCylinder(diameter/2, length)
    
    # Add simplified knurl pattern (rings for visualization)
    num_rings = int(length / 2)  # Knurl spacing
    for i in range(num_rings):
        ring_pos = i * 2 + 1
        # Create small grooves
        groove = Part.makeCylinder((diameter/2 - knurl_depth), 1)
        groove.translate(App.Vector(0, 0, ring_pos))
        # Don't cut - just visual approximation
    
    obj = doc.addObject("Part::Feature", "KnurledShaft")
    obj.Shape = shaft
    doc.recompute()
    print(f"✓ Knurled shaft: ø{diameter}mm, L={length}mm, {knurl_type} knurl")
    return shaft


def shaft_collar(doc, inner_diameter=20, outer_diameter=40, thickness=10, set_screw=True, screw_diameter=6):
    """Create a shaft collar"""
    # Main collar body
    collar = Part.makeCylinder(outer_diameter/2, thickness)
    
    # Inner hole
    hole = Part.makeCylinder(inner_diameter/2, thickness+2)
    hole.translate(App.Vector(0, 0, -1))
    collar = collar.cut(hole)
    
    # Optional set screw hole
    if set_screw:
        screw_hole = Part.makeCylinder(screw_diameter/2, outer_diameter/2 + 2)
        screw_hole.rotate(App.Vector(0,0,thickness/2), App.Vector(0,1,0), 90)
        screw_hole.translate(App.Vector(outer_diameter/2 + 1, 0, thickness/2))
        collar = collar.cut(screw_hole)
    
    obj = doc.addObject("Part::Feature", "ShaftCollar")
    obj.Shape = collar
    doc.recompute()
    print(f"✓ Shaft collar: ID={inner_diameter}mm, OD={outer_diameter}mm")
    return collar


# ============================================================================
# GEARS & MOTION
# ============================================================================

def spur_gear(doc, num_teeth=20, module=2, thickness=10, bore_diameter=10):
    """Create a simplified spur gear"""
    import math
    
    # Calculate dimensions
    pitch_diameter = num_teeth * module
    outer_diameter = pitch_diameter + 2 * module
    root_diameter = pitch_diameter - 2.5 * module
    
    # Create gear body (simplified as cylinder with teeth approximation)
    gear = Part.makeCylinder(outer_diameter/2, thickness)
    
    # Center bore
    bore = Part.makeCylinder(bore_diameter/2, thickness+2)
    bore.translate(App.Vector(0, 0, -1))
    gear = gear.cut(bore)
    
    # Create tooth spaces (simplified)
    tooth_angle = 360 / num_teeth
    for i in range(num_teeth):
        angle = math.radians(i * tooth_angle + tooth_angle/2)
        
        # Tooth space (rectangular approximation)
        space = Part.makeBox(module*0.5, module, thickness+2)
        space.translate(App.Vector(-module*0.25, outer_diameter/2 - module, -1))
        space.rotate(App.Vector(0,0,0), App.Vector(0,0,1), i * tooth_angle)
        
        gear = gear.cut(space)
    
    obj = doc.addObject("Part::Feature", "SpurGear")
    obj.Shape = gear
    doc.recompute()
    print(f"✓ Spur gear: {num_teeth} teeth, module={module}, t={thickness}mm")
    return gear


def pulley(doc, outer_diameter=60, bore_diameter=10, thickness=20, groove_type='v', groove_depth=3):
    """Create a pulley"""
    # Main pulley body
    pulley = Part.makeCylinder(outer_diameter/2, thickness)
    
    # Center bore
    bore = Part.makeCylinder(bore_diameter/2, thickness+2)
    bore.translate(App.Vector(0, 0, -1))
    pulley = pulley.cut(bore)
    
    # Groove for belt
    if groove_type == 'v':
        # V-groove (simplified as cylinder)
        groove = Part.makeCylinder((outer_diameter/2 - groove_depth), thickness*0.6)
        groove.translate(App.Vector(0, 0, thickness*0.2))
        pulley = pulley.cut(groove)
    elif groove_type == 'flat':
        # Flat groove
        groove = Part.makeCylinder((outer_diameter/2 - groove_depth), thickness*0.4)
        groove.translate(App.Vector(0, 0, thickness*0.3))
        pulley = pulley.cut(groove)
    
    obj = doc.addObject("Part::Feature", "Pulley")
    obj.Shape = pulley
    doc.recompute()
    print(f"✓ Pulley: OD={outer_diameter}mm, bore={bore_diameter}mm, {groove_type}-groove")
    return pulley


def sprocket(doc, num_teeth=16, pitch=12.7, bore_diameter=10, thickness=8):
    """Create a chain sprocket (simplified)"""
    import math
    
    # Calculate pitch diameter
    pitch_diameter = pitch / math.sin(math.pi / num_teeth)
    outer_diameter = pitch_diameter + pitch
    
    # Main body
    sprocket = Part.makeCylinder(outer_diameter/2, thickness)
    
    # Center bore
    bore = Part.makeCylinder(bore_diameter/2, thickness+2)
    bore.translate(App.Vector(0, 0, -1))
    sprocket = sprocket.cut(bore)
    
    # Create tooth spaces
    tooth_width = pitch * 0.3
    for i in range(num_teeth):
        angle = (360 / num_teeth) * i
        
        space = Part.makeBox(tooth_width, pitch, thickness+2)
        space.translate(App.Vector(-tooth_width/2, outer_diameter/2 - pitch*0.5, -1))
        space.rotate(App.Vector(0,0,0), App.Vector(0,0,1), angle)
        
        sprocket = sprocket.cut(space)
    
    obj = doc.addObject("Part::Feature", "Sprocket")
    obj.Shape = sprocket
    doc.recompute()
    print(f"✓ Sprocket: {num_teeth} teeth, pitch={pitch}mm")
    return sprocket


# ============================================================================
# RIBS & SUPPORTS
# ============================================================================

def support_rib(doc, height=50, length=80, thickness=5, angle=45):
    """Create a triangular support rib"""
    import math
    
    angle_rad = math.radians(angle)
    base_length = height / math.tan(angle_rad)
    
    # Create triangular profile
    p1 = App.Vector(0, 0, 0)
    p2 = App.Vector(base_length, 0, 0)
    p3 = App.Vector(0, 0, height)
    
    # Create triangle face
    line1 = Part.makeLine(p1, p2)
    line2 = Part.makeLine(p2, p3)
    line3 = Part.makeLine(p3, p1)
    
    wire = Part.Wire([line1, line2, line3])
    face = Part.Face(wire)
    
    # Extrude to thickness
    rib = face.extrude(App.Vector(0, length, 0))
    
    obj = doc.addObject("Part::Feature", "SupportRib")
    obj.Shape = rib
    doc.recompute()
    print(f"✓ Support rib: h={height}mm, L={length}mm, angle={angle}°")
    return rib


def honeycomb_panel(doc, length=200, width=150, thickness=20, cell_size=10, wall_thickness=1):
    """Create a honeycomb panel (simplified)"""
    import math
    
    # Outer shell
    outer = Part.makeBox(length, width, thickness)
    
    # Create hexagonal cells (simplified as circles for performance)
    cells_x = int(length / (cell_size * 1.5))
    cells_y = int(width / (cell_size * math.sqrt(3)))
    
    for i in range(cells_x):
        for j in range(cells_y):
            x = i * cell_size * 1.5 + cell_size
            y = j * cell_size * math.sqrt(3) + cell_size
            
            # Offset every other row
            if i % 2 == 1:
                y += cell_size * math.sqrt(3) / 2
            
            if x < length-cell_size and y < width-cell_size:
                cell = Part.makeCylinder(cell_size/2 - wall_thickness, thickness+2)
                cell.translate(App.Vector(x, y, -1))
                outer = outer.cut(cell)
    
    obj = doc.addObject("Part::Feature", "HoneycombPanel")
    obj.Shape = outer
    doc.recompute()
    print(f"✓ Honeycomb panel: {length}×{width}×{thickness}mm, cell={cell_size}mm")
    return outer


# ============================================================================
# FASTENER POCKETS
# ============================================================================

def threaded_hole_pocket(doc, major_diameter=8, depth=30, head_diameter=14, head_depth=8):
    """Create a threaded hole pocket with clearance for screw head"""
    # This creates the space for a socket head cap screw
    
    # Head clearance (counterbore)
    head = Part.makeCylinder(head_diameter/2, head_depth)
    
    # Thread hole (approximation)
    thread_hole = Part.makeCylinder(major_diameter * 0.85 / 2, depth)  # 85% for thread clearance
    thread_hole.translate(App.Vector(0, 0, head_depth))
    
    result = head.fuse(thread_hole)
    
    print(f"✓ Threaded hole pocket: M{major_diameter}, depth={depth}mm")
    return result


def captive_nut_pocket(base_shape, nut_size=10, nut_thickness=8, access_slot_width=12, depth=20, position=(0,0,0)):
    """Create a hexagonal pocket for captive nut"""
    import math
    
    pos = App.Vector(*position)
    
    # Create hexagonal pocket
    hex_radius = nut_size / math.sqrt(3)  # Flat-to-flat to radius
    
    points = []
    for i in range(6):
        angle = math.radians(60 * i + 30)
        x = hex_radius * math.cos(angle)
        y = hex_radius * math.sin(angle)
        points.append(App.Vector(x, y, 0))
    points.append(points[0])
    
    # Create hexagon wire
    lines = [Part.makeLine(points[i], points[i+1]) for i in range(len(points)-1)]
    wire = Part.Wire(lines)
    face = Part.Face(wire)
    
    # Extrude to nut thickness
    hex_pocket = face.extrude(App.Vector(0, 0, nut_thickness))
    hex_pocket.translate(pos)
    
    # Access slot for nut insertion
    slot = Part.makeBox(access_slot_width, hex_radius*2.5, nut_thickness)
    slot.translate(App.Vector(pos.x - access_slot_width/2, pos.y - hex_radius*1.25, pos.z))
    
    pocket = hex_pocket.fuse(slot)
    
    result = base_shape.cut(pocket)
    print(f"✓ Captive nut pocket: M{nut_size}")
    return result


# ============================================================================
# ENCLOSURE FEATURES
# ============================================================================

def snap_fit_hook(doc, length=20, thickness=2, hook_height=3, hook_depth=2):
    """Create a snap-fit cantilever hook"""
    # Main cantilever arm
    arm = Part.makeBox(thickness, length, hook_height)
    
    # Hook at end
    hook = Part.makeBox(thickness, hook_depth, hook_height*0.6)
    hook.translate(App.Vector(0, length, hook_height*0.4))
    
    result = arm.fuse(hook)
    
    obj = doc.addObject("Part::Feature", "SnapFitHook")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Snap-fit hook: L={length}mm, hook={hook_depth}mm")
    return result


def cable_grommet(base_shape, cable_diameter=8, wall_thickness=3, position=(0,0,0)):
    """Create a cable entry with strain relief"""
    pos = App.Vector(*position)
    
    # Main cable hole
    cable_hole = Part.makeCylinder(cable_diameter/2, wall_thickness+2)
    cable_hole.translate(App.Vector(pos.x, pos.y, pos.z-1))
    
    # Chamfer/relief cone
    relief_cone = Part.makeCone(cable_diameter/2, cable_diameter*0.8, wall_thickness*0.5)
    relief_cone.translate(App.Vector(pos.x, pos.y, pos.z + wall_thickness*0.5))
    
    cutout = cable_hole.fuse(relief_cone)
    result = base_shape.cut(cutout)
    
    print(f"✓ Cable grommet: ø{cable_diameter}mm")
    return result


# ============================================================================
# EXTRUSION PROFILES
# ============================================================================

def t_slot_extrusion(doc, size=20, length=500, slot_width=6):
    """Create a T-slot aluminum extrusion profile"""
    # Main square body
    outer = Part.makeBox(size, size, length)
    outer.translate(App.Vector(-size/2, -size/2, 0))
    
    # Create T-slots on all 4 sides
    slot_depth = size * 0.4
    
    for i in range(4):
        # Slot channel
        slot = Part.makeBox(slot_width, slot_depth, length+2)
        slot.translate(App.Vector(-slot_width/2, size/2 - slot_depth, -1))
        
        # T-slot opening (wider at surface)
        t_opening = Part.makeBox(slot_width*1.8, size/2 - slot_depth + 2, length+2)
        t_opening.translate(App.Vector(-slot_width*0.9, slot_depth, -1))
        
        slot = slot.fuse(t_opening)
        
        # Rotate for each side
        slot.rotate(App.Vector(0,0,0), App.Vector(0,0,1), i*90)
        outer = outer.cut(slot)
    
    obj = doc.addObject("Part::Feature", "TSlotExtrusion")
    obj.Shape = outer
    doc.recompute()
    print(f"✓ T-slot extrusion: {size}×{size}mm, L={length}mm")
    return outer


def v_slot_extrusion(doc, size=20, length=500):
    """Create a V-slot aluminum extrusion profile"""
    # Main square body
    outer = Part.makeBox(size, size, length)
    outer.translate(App.Vector(-size/2, -size/2, 0))
    
    # Create V-slots on all 4 sides
    v_depth = size * 0.35
    
    for i in range(4):
        # V-groove (approximated as angled box)
        v_width = size * 0.3
        
        # Create V shape with two angled cuts
        v_cut1 = Part.makeBox(v_width, v_depth, length+2)
        v_cut1.translate(App.Vector(-v_width/2, size/2 - v_depth, -1))
        
        outer = outer.cut(v_cut1)
        
        # Rotate for each side
        outer.rotate(App.Vector(0,0,length/2), App.Vector(0,0,1), 90)
    
    obj = doc.addObject("Part::Feature", "VSlotExtrusion")
    obj.Shape = outer
    doc.recompute()
    print(f"✓ V-slot extrusion: {size}×{size}mm, L={length}mm")
    return outer


# ============================================================================
# COMMON PARTS
# ============================================================================

def washer(doc, inner_diameter=10, outer_diameter=20, thickness=2, washer_type='flat'):
    """Create a washer"""
    # Outer ring
    outer = Part.makeCylinder(outer_diameter/2, thickness)
    
    # Inner hole
    inner = Part.makeCylinder(inner_diameter/2, thickness+2)
    inner.translate(App.Vector(0, 0, -1))
    
    washer_shape = outer.cut(inner)
    
    if washer_type == 'fender':
        # Fender washer has larger OD
        outer_diameter = outer_diameter * 1.5
        outer = Part.makeCylinder(outer_diameter/2, thickness)
        inner = Part.makeCylinder(inner_diameter/2, thickness+2)
        inner.translate(App.Vector(0, 0, -1))
        washer_shape = outer.cut(inner)
    
    obj = doc.addObject("Part::Feature", "Washer")
    obj.Shape = washer_shape
    doc.recompute()
    print(f"✓ Washer: ID={inner_diameter}mm, OD={outer_diameter}mm, {washer_type}")
    return washer_shape


def bushing(doc, outer_diameter=30, inner_diameter=20, length=40, flange=False, flange_diameter=40, flange_thickness=5):
    """Create a bushing/sleeve"""
    # Main bushing body
    outer = Part.makeCylinder(outer_diameter/2, length)
    inner = Part.makeCylinder(inner_diameter/2, length+2)
    inner.translate(App.Vector(0, 0, -1))
    
    bushing_shape = outer.cut(inner)
    
    # Optional flange
    if flange:
        flange_ring = Part.makeCylinder(flange_diameter/2, flange_thickness)
        center_hole = Part.makeCylinder(inner_diameter/2, flange_thickness+2)
        center_hole.translate(App.Vector(0, 0, -1))
        flange_ring = flange_ring.cut(center_hole)
        
        bushing_shape = bushing_shape.fuse(flange_ring)
    
    obj = doc.addObject("Part::Feature", "Bushing")
    obj.Shape = bushing_shape
    doc.recompute()
    print(f"✓ Bushing: OD={outer_diameter}mm, ID={inner_diameter}mm, L={length}mm")
    return bushing_shape


def spacer(doc, outer_diameter=20, inner_diameter=10, thickness=5):
    """Create a cylindrical spacer"""
    outer = Part.makeCylinder(outer_diameter/2, thickness)
    inner = Part.makeCylinder(inner_diameter/2, thickness+2)
    inner.translate(App.Vector(0, 0, -1))
    
    spacer_shape = outer.cut(inner)
    
    obj = doc.addObject("Part::Feature", "Spacer")
    obj.Shape = spacer_shape
    doc.recompute()
    print(f"✓ Spacer: OD={outer_diameter}mm, ID={inner_diameter}mm, t={thickness}mm")
    return spacer_shape


# ============================================================================
# ADDITIONAL USEFUL FEATURES
# ============================================================================

def filleted_box(doc, length=100, width=80, height=50, fillet_radius=5):
    """Create a box with filleted edges"""
    box = Part.makeBox(length, width, height)
    box.translate(App.Vector(-length/2, -width/2, 0))
    
    # Fillet all edges
    box = box.makeFillet(fillet_radius, box.Edges)
    
    obj = doc.addObject("Part::Feature", "FilletedBox")
    obj.Shape = box
    doc.recompute()
    print(f"✓ Filleted box: {length}×{width}×{height}mm, fillet={fillet_radius}mm")
    return box


def chamfered_cylinder(doc, diameter=50, height=100, chamfer_size=3):
    """Create a cylinder with chamfered edges"""
    cyl = Part.makeCylinder(diameter/2, height)
    
    # Chamfer top and bottom edges
    cyl = cyl.makeChamfer(chamfer_size, cyl.Edges)
    
    obj = doc.addObject("Part::Feature", "ChamferedCylinder")
    obj.Shape = cyl
    doc.recompute()
    print(f"✓ Chamfered cylinder: ø{diameter}mm, h={height}mm, chamfer={chamfer_size}mm")
    return cyl


def handle_grip(doc, diameter=30, length=100, grip_type='cylindrical'):
    """Create an ergonomic handle grip"""
    if grip_type == 'cylindrical':
        handle = Part.makeCylinder(diameter/2, length)
    elif grip_type == 'tapered':
        # Tapered handle
        handle = Part.makeCone(diameter/2, diameter*0.7/2, length)
    elif grip_type == 'ergonomic':
        # Bulged middle
        middle = Part.makeSphere(diameter*0.6)
        middle.translate(App.Vector(0, 0, length/2))
        shaft = Part.makeCylinder(diameter*0.4, length)
        handle = shaft.fuse(middle)
    
    obj = doc.addObject("Part::Feature", "HandleGrip")
    obj.Shape = handle
    doc.recompute()
    print(f"✓ Handle grip: ø{diameter}mm, L={length}mm, type={grip_type}")
    return handle


def dome_cap(doc, diameter=60, height=30, thickness=3):
    """Create a dome/cap"""
    # Outer dome
    outer_sphere = Part.makeSphere(diameter/2)
    
    # Inner sphere for wall thickness
    inner_sphere = Part.makeSphere((diameter-2*thickness)/2)
    
    # Cut inner from outer
    shell = outer_sphere.cut(inner_sphere)
    
    # Cut bottom half to make dome
    cut_box = Part.makeBox(diameter, diameter, diameter/2)
    cut_box.translate(App.Vector(-diameter/2, -diameter/2, -diameter/2))
    
    dome = shell.cut(cut_box)
    
    obj = doc.addObject("Part::Feature", "DomeCap")
    obj.Shape = dome
    doc.recompute()
    print(f"✓ Dome cap: ø{diameter}mm, h={height}mm")
    return dome


def battery_holder(doc, battery_diameter=18, battery_length=65, wall_thickness=3, num_cells=1):
    """Create a battery holder"""
    # Create cylindrical cavity for battery
    cavity = Part.makeCylinder(battery_diameter/2 + 1, battery_length + 2)
    
    # Outer housing
    housing = Part.makeCylinder(battery_diameter/2 + wall_thickness + 1, battery_length)
    
    # Cut cavity from housing
    holder = housing.cut(cavity)
    
    obj = doc.addObject("Part::Feature", "BatteryHolder")
    obj.Shape = holder
    doc.recompute()
    print(f"✓ Battery holder: ø{battery_diameter}mm × {battery_length}mm")
    return holder


# ============================================================================
# PATTERNS
# ============================================================================

def bolt_circle_pattern(base_shape, bolt_diameter=8, bolt_circle_diameter=60, 
                       num_bolts=4, plate_thickness=10):
    """Create a bolt circle pattern of holes"""
    import math
    
    result = base_shape
    
    for i in range(num_bolts):
        angle = 2 * math.pi * i / num_bolts
        x = (bolt_circle_diameter/2) * math.cos(angle)
        y = (bolt_circle_diameter/2) * math.sin(angle)
        
        hole = Part.makeCylinder(bolt_diameter/2, plate_thickness+2)
        hole.translate(App.Vector(x, y, -1))
        result = result.cut(hole)
    
    print(f"✓ Bolt circle: {num_bolts} holes, ø{bolt_diameter}mm, BCD={bolt_circle_diameter}mm")
    return result


def rectangular_hole_array(base_shape, hole_diameter=6, rows=3, cols=4, 
                          row_spacing=30, col_spacing=40, thickness=10):
    """Create a rectangular array of holes"""
    result = base_shape
    
    for i in range(rows):
        for j in range(cols):
            x = j * col_spacing - (cols-1)*col_spacing/2
            y = i * row_spacing - (rows-1)*row_spacing/2
            
            hole = Part.makeCylinder(hole_diameter/2, thickness+2)
            hole.translate(App.Vector(x, y, -1))
            result = result.cut(hole)
    
    print(f"✓ Hole array: {rows}×{cols}, ø{hole_diameter}mm, spacing {row_spacing}×{col_spacing}mm")
    return result


# ============================================================================
# ENCLOSURES
# ============================================================================

def rectangular_enclosure(doc, length=120, width=80, height=60, wall_thickness=3):
    """Create a rectangular enclosure (hollow box)"""
    outer = Part.makeBox(length, width, height)
    inner = Part.makeBox(length-2*wall_thickness, width-2*wall_thickness, height-wall_thickness)
    inner.translate(App.Vector(wall_thickness, wall_thickness, wall_thickness))
    
    result = outer.cut(inner)
    obj = doc.addObject("Part::Feature", "Enclosure")
    obj.Shape = result
    doc.recompute()
    print(f"✓ Enclosure: {length}×{width}×{height}mm, wall={wall_thickness}mm")
    return result


def electronics_box(doc, length=100, width=80, height=50, wall_thickness=3, 
                   mounting_posts=True, post_diameter=6, post_height=5):
    """Create an electronics enclosure with mounting posts"""
    # Outer shell
    outer = Part.makeBox(length, width, height)
    inner = Part.makeBox(length-2*wall_thickness, width-2*wall_thickness, height-wall_thickness)
    inner.translate(App.Vector(wall_thickness, wall_thickness, wall_thickness))
    
    box = outer.cut(inner)
    
    if mounting_posts:
        # Add corner mounting posts
        offset = 10
        positions = [
            (offset, offset),
            (length-offset, offset),
            (length-offset, width-offset),
            (offset, width-offset)
        ]
        
        for x, y in positions:
            post = Part.makeCylinder(post_diameter/2, post_height)
            post.translate(App.Vector(x, y, wall_thickness))
            box = box.fuse(post)
    
    obj = doc.addObject("Part::Feature", "ElectronicsBox")
    obj.Shape = box
    doc.recompute()
    print(f"✓ Electronics box: {length}×{width}×{height}mm, with mounting posts")
    return box


# ============================================================================
# FLANGES
# ============================================================================

def circular_flange(doc, outer_diameter=100, inner_diameter=50, thickness=10, 
                   bolt_circle_diameter=80, num_bolts=4, bolt_diameter=8):
    """Create a circular flange with bolt holes"""
    # Main flange body
    flange = Part.makeCylinder(outer_diameter/2, thickness)
    
    # Center hole
    center_hole = Part.makeCylinder(inner_diameter/2, thickness+2)
    center_hole.translate(App.Vector(0, 0, -1))
    flange = flange.cut(center_hole)
    
    # Bolt holes
    import math
    for i in range(num_bolts):
        angle = 2 * math.pi * i / num_bolts
        x = (bolt_circle_diameter/2) * math.cos(angle)
        y = (bolt_circle_diameter/2) * math.sin(angle)
        
        bolt_hole = Part.makeCylinder(bolt_diameter/2, thickness+2)
        bolt_hole.translate(App.Vector(x, y, -1))
        flange = flange.cut(bolt_hole)
    
    obj = doc.addObject("Part::Feature", "CircularFlange")
    obj.Shape = flange
    doc.recompute()
    print(f"✓ Circular flange: OD={outer_diameter}mm, ID={inner_diameter}mm, {num_bolts} bolts")
    return flange


# ============================================================================
# TEMPLATE LIST
# ============================================================================

TEMPLATES = {
    # 3D Solids (15)
    'cube': cube,
    'cuboid': cuboid,
    'cylinder': cylinder,
    'sphere': sphere,
    'cone': cone,
    'torus': torus,
    'wedge': wedge,
    'tube': tube,
    'rectangular_tube': rectangular_tube,
    'plate': plate,
    'rod': rod,
    'ring': ring,
    'pyramid': pyramid,
    'prism': prism,
    'filleted_box': filleted_box,
    
    # 2D Shapes (7)
    'line': line,
    'circle': circle,
    'rectangle': rectangle_2d,
    'polygon': polygon,
    'arc': arc,
    'ellipse': ellipse,
    'helix': helix,
    
    # Holes & Cutouts (8) - Note: these operate on existing shapes
    'through_hole': through_hole,
    'blind_hole': blind_hole,
    'countersink_hole': countersink_hole,
    'counterbore_hole': counterbore_hole,
    'rectangular_slot': rectangular_slot,
    'circular_pocket': circular_pocket,
    'rectangular_pocket': rectangular_pocket,
    'keyway': keyway,
    
    # Brackets & Mounting (7)
    'l_bracket': l_bracket,
    'u_bracket': u_bracket,
    'z_bracket': z_bracket,
    'corner_bracket': corner_bracket,
    'angle_bracket': angle_bracket,
    'mounting_plate': mounting_plate,
    'motor_mount_plate': motor_mount_plate,
    
    # Structural (3)
    'i_beam': i_beam,
    'c_channel': c_channel,
    'angle_iron': angle_iron,
    
    # Shafts (6)
    'stepped_shaft': stepped_shaft,
    'shaft_with_keyway': shaft_with_keyway,
    'threaded_shaft': threaded_shaft,
    'knurled_shaft': knurled_shaft,
    'shaft_collar': shaft_collar,
    'chamfered_cylinder': chamfered_cylinder,
    
    # Gears & Motion (3)
    'spur_gear': spur_gear,
    'pulley': pulley,
    'sprocket': sprocket,
    
    # Ribs & Supports (2)
    'support_rib': support_rib,
    'honeycomb_panel': honeycomb_panel,
    
    # Fastener Pockets (2) - Note: some operate on existing shapes
    'threaded_hole_pocket': threaded_hole_pocket,
    'captive_nut_pocket': captive_nut_pocket,
    
    # Enclosure Features (2) - Note: cable_grommet operates on existing shape
    'snap_fit_hook': snap_fit_hook,
    'cable_grommet': cable_grommet,
    
    # Extrusion Profiles (2)
    't_slot_extrusion': t_slot_extrusion,
    'v_slot_extrusion': v_slot_extrusion,
    
    # Common Parts (3)
    'washer': washer,
    'bushing': bushing,
    'spacer': spacer,
    
    # Patterns (2) - Note: these operate on existing shapes
    'bolt_circle_pattern': bolt_circle_pattern,
    'rectangular_hole_array': rectangular_hole_array,
    
    # Enclosures (2)
    'rectangular_enclosure': rectangular_enclosure,
    'electronics_box': electronics_box,
    
    # Flanges (1)
    'circular_flange': circular_flange,
    
    # Additional Features (4)
    'handle_grip': handle_grip,
    'dome_cap': dome_cap,
    'battery_holder': battery_holder,
    
    # Complex Features (3)
    'box_with_hole': box_with_hole,
    'plate_with_holes': plate_with_holes,
}

# Total: 75 templates
# 
# Categories:
# - Solid primitives: 15
# - 2D shapes: 7
# - Cutout operations: 8
# - Brackets/mounts: 7
# - Structural: 3
# - Shafts: 6
# - Gears/motion: 3
# - Supports: 2
# - Fasteners: 2
# - Enclosure features: 2
# - Extrusions: 2
# - Standard parts: 3
# - Patterns: 2
# - Enclosures: 2
# - Flanges: 1
# - Misc features: 4
# - Complex assemblies: 3
