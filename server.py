import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any

# Import our CAD compiler logic
import main

app = FastAPI(title="CAD Compiler API")

# Mount static files
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Mount generated models directory so we can serve the STL/STEP files
gen_models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_models")
if not os.path.exists(gen_models_dir):
    os.makedirs(gen_models_dir)
app.mount("/generated_models", StaticFiles(directory=gen_models_dir), name="generated_models")


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Handle chat messages.
    1. Send to LLM to understand intent
    2. If ready, generate 3D model using headless FreeCAD
    3. Return file paths and parameters
    """
    try:
        # Process request using main.py logic
        # This handles: LLM Analysis -> Param Extraction -> Script Gen -> Headless Execution
        result = main.process_request(request.message, headless=True)
        
        if not result["success"]:
            if "ready" in result and not result["ready"]:
                # This is a conversational response (e.g. asking for more info)
                return {
                    "type": "text",
                    "message": result["message"]
                }
            else:
                # System error
                raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        # Success! Model generated.
        # Construct URLs for the files
        files = result["files"]
        
        return {
            "type": "model",
            "message": f"Generated {result['template']} successfully!",
            "template": result['template'],
            "params": result['params'],
            "files": {
                "step": f"/generated_models/{files['step']}",
                "stl": f"/generated_models/{files['stl']}",
                "script": f"/generated_models/{files['script']}"
            }
        }
        
    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "CAD Compiler API is running. Go to /static/index.html"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
