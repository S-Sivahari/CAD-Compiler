# Natural Language to FreeCAD 3D Model Generator

Complete system for generating 3D CAD models from natural language descriptions.

## 📁 Project Structure

```
solidworks_v2/
├── launcher.py           # FreeCAD initialization & GUI launcher
├── templates.py          # 75 parametric shape templates
├── combiner.py           # Positioning, transforming & combining parts
├── run_with_freecad_python.py  # Execution wrapper
├── example.py            # Basic template usage examples
├── combiner_example.py   # Combiner system examples
├── complex_design.py     # Complex assembly demo
├── requirements.txt      # Python dependencies for NLP
├── .env.example          # API keys template
└── README.md            # This file
```

## 🚀 Quick Start

### Run Basic Example
```bash
python run_with_freecad_python.py example.py
```

### Run Combiner Example
```bash
python run_with_freecad_python.py combiner_example.py
```

### Run Complex Design
```bash
python run_with_freecad_python.py complex_design.py
```

## 📚 Template Library (75 Templates)

### Primitives (15)
- cube, cuboid, cylinder, sphere, cone, torus, wedge
- tube, rectangular_tube, plate, rod, ring
- pyramid, prism, filleted_box

### 2D Shapes (7)
- line, circle, rectangle, polygon, arc, ellipse, helix

### Holes & Cutouts (8)
- through_hole, blind_hole, countersink_hole, counterbore_hole
- rectangular_slot, circular_pocket, rectangular_pocket, keyway

### Brackets & Mounting (7)
- l_bracket, u_bracket, z_bracket, corner_bracket
- angle_bracket, mounting_plate, motor_mount_plate

### Structural (3)
- i_beam, c_channel, angle_iron

### Shafts (6)
- stepped_shaft, shaft_with_keyway, threaded_shaft
- knurled_shaft, shaft_collar, chamfered_cylinder

### Gears & Motion (3)
- spur_gear, pulley, sprocket

### Supports (2)
- support_rib, honeycomb_panel

### Fasteners (2)
- threaded_hole_pocket, captive_nut_pocket

### Enclosures (4)
- rectangular_enclosure, electronics_box, snap_fit_hook, cable_grommet

### Extrusions (2)
- t_slot_extrusion, v_slot_extrusion

### Standard Parts (3)
- washer, bushing, spacer

### Patterns (2)
- bolt_circle_pattern, rectangular_hole_array

### Flanges (1)
- circular_flange

### Features (4)
- handle_grip, dome_cap, battery_holder

### Complex (3)
- box_with_hole, plate_with_holes

## 🔧 Combiner System

### Positioning
```python
translate(shape, x=10, y=20, z=30)
rotate(shape, axis='z', angle=90)
mirror(shape, plane='xy')
scale(shape, factor_x=1.5, factor_y=1.0, factor_z=1.0)
```

### Boolean Operations
```python
combine(shape1, shape2, 'union')      # Fuse
combine(shape1, shape2, 'difference') # Cut
combine(shape1, shape2, 'intersection') # Common
```

### Patterns
```python
linear_pattern(shape, direction=(1,0,0), count=5, spacing=20)
circular_pattern(shape, center=(0,0,0), count=8, angle=360)
grid_pattern(shape, rows=3, cols=4, row_spacing=30, col_spacing=40)
```

### Assembly Builder
```python
assembly = Assembly("MyAssembly")
assembly.add_part(base_plate, "Base")
assembly.add_part(bracket, "Bracket")
result = assembly.combine_all('union')
```

## 🤖 Next Step: LLM Integration

### What You Need to Build:
1. **OpenRouter API Connector**
   - Use Llama 70B model
   - Send natural language input
   - Receive template + parameters

2. **Prompt System**
   - List all 75 templates with parameters
   - Handle dimension extraction
   - Manage conversation for missing params

3. **Execution Pipeline**
   - Parse LLM JSON response
   - Call appropriate templates
   - Use combiner for multi-part designs
   - Generate and open FreeCAD model

### LLM Task (EASY for Llama 70B):
```
Input: "I need a NEMA23 motor mount with 4 M6 bolt holes"

LLM Output:
{
  "templates": [
    {
      "name": "motor_mount_plate",
      "params": {
        "motor_size": "NEMA23",
        "mounting_thickness": 10,
        "base_size": 90
      }
    },
    {
      "name": "bolt_circle_pattern",
      "params": {
        "bolt_diameter": 6.5,
        "bolt_circle_diameter": 50,
        "num_bolts": 4
      },
      "operation": "cut",
      "target": "motor_mount_plate"
    }
  ]
}
```

## 📤 Output Formats

### STEP File (for SolidWorks)
```python
export_step(shape, "my_model.step")
```

All models automatically export to STEP format compatible with SolidWorks.

## 💡 Usage Examples

### Simple Part
```python
from templates import *
from launcher import create_document, open_gui

doc = create_document("Simple")
box = cuboid(doc, length=100, width=80, height=50)
open_gui(doc)
```

### Combined Assembly
```python
from templates import *
from combiner import *
from launcher import create_document, open_gui

doc = create_document("Assembly")

base = plate(doc, length=150, width=100, thickness=10)
bracket = l_bracket(doc, length=80, width=60, height=50, thickness=8)
translate(bracket, x=-60, y=-30, z=10)

assembly = combine(base, bracket, 'union')

part_obj = doc.addObject("Part::Feature", "Assembly")
part_obj.Shape = assembly
doc.recompute()

open_gui(doc)
```

## 🎯 Current Status

- ✅ 75 parametric templates
- ✅ FreeCAD launcher & GUI integration
- ✅ STEP export for SolidWorks
- ✅ Combiner system (positioning, boolean ops, patterns)
- ✅ Assembly builder
- ⏳ **Next: Your LLM integration with OpenRouter**

## 📝 Notes

- FreeCAD must be installed separately
- Templates use FreeCAD's Python API
- All dimensions in millimeters
- Models only exist in memory (no FCStd files unless saved)
- STEP files ready for import to SolidWorks

## 🔗 Resources

- FreeCAD: https://www.freecad.org/
- OpenRouter API: https://openrouter.ai/
- Standard parts: McMaster-Carr, GrabCAD

---

**Ready for LLM integration! The template system is complete and waiting for your natural language input.**
