"""
FreeCAD Launcher & Runner
Starts FreeCAD with Python and manages document creation
"""

import sys
import os
import time
import subprocess

# Add FreeCAD to path
sys.path.append(r"C:\Users\Ashfaq Ahamed A\AppData\Local\Programs\FreeCAD 1.0\bin")
sys.path.append(r"C:\Users\Ashfaq Ahamed A\AppData\Local\Programs\FreeCAD 1.0\lib")

import FreeCAD as App
import Part
import FreeCADGui


def create_document(name="Model"):
    """Create a new FreeCAD document"""
    doc = App.newDocument(name)
    print(f"[OK] Document '{name}' created")
    return doc


def open_gui(doc):
    """Open FreeCAD GUI with the document"""
    print("\n[OK] Opening FreeCAD GUI...")
    
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
        print("[OK] Model visible in FreeCAD")
    
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
    print(f"[OK] Exported: {step_file}")
    return step_file


def export_stl(shape, filename):
    """Export shape to STL file in generated_models folder (for web viewer)"""
    # Use generated_models dir for web assets
    gen_models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_models")
    
    if not os.path.exists(gen_models_dir):
        os.makedirs(gen_models_dir)
    
    stl_file = os.path.join(gen_models_dir, filename)
    
    # STL Export
    shape.exportStl(stl_file)
    print(f"[OK] Exported STL: {stl_file}")
    return stl_file


def run_with_freecad_python(script_path, headless=False):
    """Run a Python script with FreeCAD's Python interpreter"""
    freecad_python = r"C:\Users\Ashfaq Ahamed A\AppData\Local\Programs\FreeCAD 1.0\bin\python.exe"    
    if not os.path.exists(freecad_python):
        # Fallback to standard location just in case or keep user path as primary
        freecad_python = r"C:\Program Files\FreeCAD 1.0\bin\python.exe"
    
    if not os.path.exists(freecad_python):
        print("FreeCAD Python interpreter not found!")
        print(f"Looked for: {freecad_python}")
        return 1
    
    print(f"Using FreeCAD Python: {freecad_python}")
    print(f"Running: {script_path} (Headless: {headless})\n")

    # If headless, we might want to ensure the script doesn't try to open GUI
    # But for now, we rely on the script itself to check context or just not call open_gui
    # The 'run_headless' parameter in server.py will determine if open_gui is called in the generated script
    
    result = subprocess.run([freecad_python, script_path], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] Execution failed with code {result.returncode}")
        print(f"Stderr: {result.stderr}")
    else:
        print(f"Stdout: {result.stdout}")
        
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python launcher.py <script.py> [--headless]")
        sys.exit(1)
    
    script = sys.argv[1]
    headless = "--headless" in sys.argv
    
    if not os.path.exists(script):
        print(f"Script not found: {script}")
        sys.exit(1)
    
    exit_code = run_with_freecad_python(os.path.abspath(script), headless=headless)
    sys.exit(exit_code)
