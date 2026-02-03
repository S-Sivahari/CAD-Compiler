"""
FreeCAD Launcher & Runner
Starts FreeCAD with Python and manages document creation
"""

import sys
import os
import time
import subprocess

# Add FreeCAD to path
sys.path.append(r"C:\Program Files\FreeCAD 1.0\bin")
sys.path.append(r"C:\Program Files\FreeCAD 1.0\lib")

import FreeCAD as App
import Part
import FreeCADGui


def create_document(name="Model"):
    """Create a new FreeCAD document"""
    doc = App.newDocument(name)
    print(f"✓ Document '{name}' created")
    return doc


def open_gui(doc):
    """Open FreeCAD GUI with the document"""
    print("\n✓ Opening FreeCAD GUI...")
    
    # Save to temp file for GUI loading
    import tempfile
    temp_file = os.path.join(tempfile.gettempdir(), "temp_model.FCStd")
    doc.saveAs(temp_file)
    
    # Close backend and open in GUI
    doc_name = doc.Name
    App.closeDocument(doc_name)
    
    FreeCADGui.showMainWindow()
    App.open(temp_file)
    FreeCADGui.updateGui()
    
    time.sleep(1)
    
    if FreeCADGui.activeDocument() and FreeCADGui.activeDocument().activeView():
        view = FreeCADGui.activeDocument().activeView()
        view.viewAxometric()
        view.fitAll()
        print("✓ Model visible in FreeCAD")
    
    FreeCADGui.exec_loop()
    
    # Cleanup
    try:
        os.remove(temp_file)
    except:
        pass


def export_step(shape, filename):
    """Export shape to STEP file in stepfiles folder"""
    stepfiles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stepfiles")
    
    # Create stepfiles directory if it doesn't exist
    if not os.path.exists(stepfiles_dir):
        os.makedirs(stepfiles_dir)
    
    step_file = os.path.join(stepfiles_dir, filename)
    shape.exportStep(step_file)
    print(f"✓ Exported: {step_file}")
    return step_file


def run_with_freecad_python(script_path):
    """Run a Python script with FreeCAD's Python interpreter"""
    freecad_python = r"C:\Program Files\FreeCAD 1.0\bin\python.exe"    
    if not os.path.exists(freecad_python):
        freecad_python = r"C:\Program Files (x86)\FreeCAD 1.0\bin\python.exe"
    
    if not os.path.exists(freecad_python):
        print("FreeCAD Python interpreter not found!")
        print(f"Looked for: {freecad_python}")
        return 1
    
    print(f"Using FreeCAD Python: {freecad_python}")
    print(f"Running: {script_path}\n")

    result = subprocess.run([freecad_python, script_path])
    
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python launcher.py <script.py>")
        sys.exit(1)
    
    script = sys.argv[1]
    
    if not os.path.exists(script):
        print(f"Script not found: {script}")
        sys.exit(1)
    
    exit_code = run_with_freecad_python(os.path.abspath(script))
    sys.exit(exit_code)
