# Natural Language CAD Generator with LLM

🤖 Generate 3D CAD models using natural language powered by Google Gemini AI

## ✨ Features

- 🗣️ **Natural Language Input** - Describe your part in plain English
- 🤖 **AI-Powered** - Uses Google Gemini 2.5 Flash (FREE API)
- 📦 **75 Pre-built Templates** - Cubes, cylinders, brackets, gears, and more
- 🔧 **Parametric Design** - All templates are fully parametric
- 🔄 **Multi-Part Assembly** - Combine and position multiple components
- 📤 **STEP Export** - Automatic export to industry-standard STEP format
- 🖥️ **FreeCAD Integration** - Models open directly in FreeCAD GUI

## 📁 Project Structure

```
solidworks_v2/
├── main.py              # LLM interface & conversation handler
├── launcher.py          # FreeCAD initialization & GUI launcher
├── templates.py         # 75 parametric shape templates
├── combiner.py          # Position, transform & combine shapes
├── .env                 # Gemini API key (create from .env.example)
├── .env.example         # API key template
├── .gitignore           # Git exclusions
├── generated_models/    # Generated Python scripts (timestamped)
├── stepfiles/           # Exported STEP files
└── README.md            # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- **FreeCAD 1.0** installed. (Ensure the path in `launcher.py` matches your installation)
- **Python 3.x**
- **Google Gemini API Key** (free from [Google AI Studio](https://makersuite.google.com/app/apikey))

### 2. Setup

1. Clone the repository:
```bash
git clone https://github.com/S-Sivahari/CAD-Compiler.git
cd CAD-Compiler
```

2. Create `.env` file with your Gemini API key:
```bash
GEMINI_API_KEY=your_api_key_here
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the Application

**Option A: Web Interface (Recommended)**
Start the server and web UI:
```bash
python server.py
```
Then open your browser to `http://localhost:8000/static/index.html`.

**Option B: Command Line**
Generate models directly from the terminal:
```bash
python main.py
```

### 4. Create Your Model

```
You: create a motor mount for NEMA23
🤖: {"ready": true, "template": "motor_mount_plate", "params": {...}}
✓ Generating motor_mount_plate...
✓ Script saved: generated_models/motor_mount_plate_20260203_143052.py
✓ Launching FreeCAD...
✓ Exported: stepfiles/motor_mount_plate_model.step
```

## 📚 Available Templates (75 Total)

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

Use `combiner.py` to create multi-part assemblies:

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

## 💡 Example Conversations

### Simple Part
```
You: create a cube 50mm
🤖: {"ready": true, "template": "cube", "params": {"size": 50}}
```

### Part with Missing Info
```
You: I need a cylinder
🤖: {"ready": false, "message": "What should the radius be? (in mm)"}
You: 30mm
🤖: {"ready": false, "message": "What should the height be? (in mm)"}
You: 100mm
🤖: {"ready": true, "template": "cylinder", "params": {"radius": 30, "height": 100}}
```

### Complex Part
```
You: create a motor mount for NEMA23
🤖: {"ready": true, "template": "motor_mount_plate", "params": {...}}
```

## 🎯 How It Works

1. **You describe** the part in natural language
2. **Gemini AI** identifies the matching template and extracts parameters
3. **System generates** Python script calling the template
4. **FreeCAD renders** the model and opens GUI
5. **STEP file** automatically exported to `stepfiles/`

## 📂 Output Files

- **Generated Scripts**: `generated_models/template_YYYYMMDD_HHMMSS.py`
- **STEP Exports**: `stepfiles/template_model.step`

## 🔒 Security

- `.env` file contains your API key - **NEVER commit this to git**
- `.gitignore` is configured to exclude sensitive files
- Use `.env.example` as a template for others

## 🛠️ Technical Details

### Architecture
- **Templates**: Pre-built parametric CAD functions (no code generation needed)
- **LLM Role**: Pattern matching + parameter extraction only
- **Combiner**: Boolean operations and transformations
- **Launcher**: FreeCAD process management

### Why This Works
- ✅ **Reliable**: All geometry code is pre-tested
- ✅ **Fast**: LLM only does simple JSON output
- ✅ **Scalable**: Easy to add new templates
- ✅ **Free**: Gemini API has generous free tier

## 📝 Notes

- All dimensions are in millimeters
- FreeCAD 1.0 required (adjust path in scripts if different version)
- Models only exist in memory until exported
- STEP files are compatible with SolidWorks, Fusion 360, etc.

## 🤝 Contributing

1. Add new templates to `templates.py`
2. Update `TEMPLATE_CATALOG` in `main.py`
3. Test with natural language descriptions
4. Submit pull request

## 📄 License

This project is open source and available for use.

## 🔗 Resources

- [FreeCAD Official Site](https://www.freecad.org/)
- [Google AI Studio](https://makersuite.google.com/app/apikey)
- [STEP File Format](https://en.wikipedia.org/wiki/ISO_10303)

---

**Made with ❤️ using AI + FreeCAD**