# --- EMERGENCY BOOTSTRAP wrapper for Vercel debugging ---
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from typing import List, Dict, Optional, Any
    from pydantic import BaseModel
    import os
    import json
    import traceback
    from huggingface_hub import InferenceClient
    from dotenv import load_dotenv

    # Local Relative Imports
    from .models import FileAction, FileObservation
    from .env import FileOrganizerEnv

    load_dotenv(override=True)

    # Standard FastAPI initialization with root_path for Vercel routing
    app = FastAPI(root_path="/api")
    # Global persistent environment instance
    env = FileOrganizerEnv()

except Exception as boot_err:
    # If the app fails to even LOAD (NameError, ImportError, etc.), 
    # we create this dummy app to show you the error in the browser.
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import traceback
    app = FastAPI()
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def emergency_debug_route(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "boot_error",
                "message": str(boot_err),
                "traceback": traceback.format_exc(),
                "hint": "This error happened during Python import/startup time."
            }
        )
# -----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler to capture 500 errors for debugging
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        print(f"[CRITICAL ERROR] {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(exc),
                "traceback": traceback.format_exc()
            }
        )

class FileEntry(BaseModel):
    name: str
    relative_path: str

class AnalyzePayload(BaseModel):
    files: List[FileEntry]

class ReevaluatePayload(BaseModel):
    remaining_files: List[str]
    override_file: str
    override_path: str

def _apply_heuristic(files_metadata: dict) -> dict:
    from collections import defaultdict
    counts = defaultdict(int)
    for f, m in files_metadata.items():
        path = m.get("path", "").strip("/")
        parts = path.split("/") if path else []
        if parts:
            counts[parts[0]] += 1
            
    for f, m in files_metadata.items():
        path = m.get("path", "").strip("/")
        parts = path.split("/") if path else ["Uncategorized"]
        top = parts[0]
        
        if counts[top] < 3:
            m["path"] = f"{top}"
            m["reason"] = m.get("reason", "") + " (Flattened: <3 files)"
        elif counts[top] > 10 and len(parts) == 1:
            m["path"] = f"{top}/General"
            m["reason"] = m.get("reason", "") + " (Deepened: >10 files)"
        else:
            m["path"] = "/".join(parts)
            
    return files_metadata

def call_hf_inference(system_prompt: str, user_prompt: str, fallback_files: List[str]) -> dict:
    try:
        MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
        HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY")
        
        if not HF_TOKEN:
            print("[DEBUG] HF_TOKEN missing")
            return {f: {"path": f.split('.')[0].capitalize(), "reason": "Environment missing HF_TOKEN or API_KEY"} for f in fallback_files}
            
        # Set timeout in the constructor
        client = InferenceClient(api_key=HF_TOKEN, timeout=30)
        
        # Add strict JSON instruction to the system prompt
        json_instr = "\nReturn ONLY a raw valid JSON object without any markdown formatting, backticks, or preamble."
        
        messages = [
            {"role": "system", "content": system_prompt + json_instr},
            {"role": "user", "content": user_prompt}
        ]
        
        print(f"[DEBUG HF] Calling InferenceClient for {MODEL_NAME} with 30s timeout...")
        response = client.chat_completion(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=800,
            temperature=0.1
        )
        
        text = response.choices[0].message.content
        print(f"[DEBUG HF] Raw Response: {text[:200]}...")
        
        # Clean potential markdown or noise
        text = text.strip()
        if text.startswith("```"):
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group(0)
            
        content = json.loads(text)
        content = _apply_heuristic(content)
        return content
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR HF API] {e}")
        return {f: {"path": f.split('.')[0].capitalize(), "reason": f"API Error: {str(e)}"} for f in fallback_files}

@app.get("/")
def health_check():
    return {"status": "success", "message": "Semantic File Organizer API is running"}

@app.get("/reset")
def reset(episode_id: Optional[str] = None):
    # Standard OpenEnv reset endpoint
    return env.reset()

@app.post("/step")
def step(action: FileAction):
    # Standard OpenEnv step endpoint
    return env.step(action)

@app.post("/analyze-structure")
def analyze_structure(payload: AnalyzePayload):
    print(f"[DEBUG analyze-structure] received {len(payload.files)} files.")
    
    system_prompt = (
        "You are analyzing a nested directory. Your goal is to simplify the hierarchy. "
        "You can move files from deep subfolders to a shallower normalized folder if it improves fetchability. "
        "Follow these rules: "
        "1. 1NF/2NF Logic: Group files into atomic, semantic categories. "
        "2. Avoid generic names like 'Miscellaneous' or 'General'. "
        "Return a JSON object where keys are filenames and values are objects with 'path' (the recommended folder path, e.g., 'Finance/Invoices') and 'reason' (normalization reason)."
    )
    user_prompt = f"Analyze and structure these files. Note their current locations: {[{'name': f.name, 'rel': f.relative_path} for f in payload.files]}"
    
    # We pass the list of names for fallback construction
    file_names = [f.name for f in payload.files]
    content = call_hf_inference(system_prompt, user_prompt, file_names)
    print("[DEBUG analyze-structure] Successfully resolved structure.")
    return {"structure": content}

@app.post("/reevaluate-structure")
def reevaluate_structure(payload: ReevaluatePayload):
    system_prompt = (
        "You are an Agentic Learning file architect. "
        f"The user just manually categorized the file '{payload.override_file}' into the path '{payload.override_path}'. "
        "Re-evaluate the remaining queue to adopt and follow this new categorization pattern where it makes sense. "
        "Return a JSON object where keys are filenames and values are objects with 'path' and 'reason'."
    )
    user_prompt = f"Remaining queue: {payload.remaining_files}"
    
    content = call_hf_inference(system_prompt, user_prompt, payload.remaining_files)
    print("[DEBUG reevaluate-structure] Successfully reevaluated.")
    return {"structure": content}

if __name__ == "__main__":
    import uvicorn
    # 8000 is the standard port for OpenEnv containers
    uvicorn.run(app, host="0.0.0.0", port=8000)