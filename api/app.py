from typing import Any, List, Dict, Optional
# Ensure app is defined globally even before the try block to avoid NameErrors
app = None
FileAction = Any
FileObservation = Any

try:
    import os
    import sys
    # Add the current directory to sys.path for Vercel discovery of local modules
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import json
    import traceback
    from huggingface_hub import InferenceClient
    from dotenv import load_dotenv

    # Local Imports
    import models
    import env as env_module

    load_dotenv(override=True)

    # Standard FastAPI initialization with root_path for Vercel routing
    app = FastAPI(root_path="/api")
    
    print("[Vercel Startup] Booting Semantic File Organizer Backend...")
    # Global persistent environment instance
    env = env_module.FileOrganizerEnv()

    # Convenience aliases for models
    FileAction = models.FileAction
    FileObservation = models.FileObservation

except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import traceback
    
    # Store error details in persistent variables (except variables are cleared in Python 3)
    boot_err_msg = str(e)
    boot_err_trace = traceback.format_exc()
    
    # Redefine app as an emergency debug server
    app = FastAPI()
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def emergency_debug_route(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "boot_error",
                "message": boot_err_msg,
                "traceback": boot_err_trace,
                "hint": "This error happened during the Python import/startup phase in api/app.py."
            }
        )
# -----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.environ.get("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:5173",
        "*" # Fallback for Vercel preview URLs
    ],
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
    import os
    counts = defaultdict(int)
    
    # Pass 1: Aggressive Overlap Filtering and Path Sanitization
    for f, m in files_metadata.items():
        # Handle cases where AI returns a string instead of an object
        if isinstance(m, str):
            path = m.strip("/")
            m = {"path": path, "reason": "AI Recommendation"}
            files_metadata[f] = m
        else:
            path = m.get("path", "").strip("/")
            
        # Target path cleanup
        if path.endswith(f):
            path = os.path.dirname(path)
            
        parts = [p for p in path.split("/") if p]
        
        # Rule: Aggressive Overlap Check
        # If any part of the folder name is similar to the filename, strip it.
        base_name = f.split(".")[0].lower().replace(" ", "").replace("-", "").replace("_", "")
        cleaned_parts = []
        for p in parts:
            p_clean = p.lower().replace(" ", "").replace("-", "").replace("_", "")
            if len(p_clean) > 2 and (p_clean in base_name or base_name in p_clean):
                continue # Skip redundant folders
            cleaned_parts.append(p)
        
        m["path"] = "/".join(cleaned_parts[:2]) if cleaned_parts else "Uncategorized"
        counts[m["path"]] += 1

    # Pass 2: Threshold Grouping (at least 2 files)
    for f, m in files_metadata.items():
        path = m["path"]
        if counts[path] < 2:
            parts = path.split("/")
            if len(parts) > 1:
                m["path"] = parts[0]
                m["reason"] = m.get("reason", "") + " (Flattened: Single-file category)"
        
    return files_metadata

def call_hf_inference(system_prompt: str, user_prompt: str, fallback_files: List[str]) -> dict:
    try:
        MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
        HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY")
        
        if not HF_TOKEN:
            print("[CRITICAL] HF_TOKEN missing in Vercel Settings.")
            return {"error": "API Key missing in Vercel Settings"}
            
        print(f"[Vercel AI] Calling InferenceClient for {MODEL_NAME}...")
        # Set timeout in the constructor
        client = InferenceClient(api_key=HF_TOKEN, timeout=30)
        
        # Add strict JSON instruction to the system prompt
        json_instr = "\nReturn ONLY a raw valid JSON object without any markdown formatting, backticks, or preamble."
        
        max_retries = 3
        current_user_prompt = user_prompt
        
        for attempt in range(max_retries):
            messages = [
                {"role": "system", "content": system_prompt + json_instr},
                {"role": "user", "content": current_user_prompt}
            ]
            
            response = client.chat_completion(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=800,
                temperature=0.1 + (0.1 * attempt) # slight temp increase on retry
            )
            
            text = response.choices[0].message.content
            print(f"[Vercel AI] Attempt {attempt+1} Raw Response: {text[:200]}...")
            
            # Clean potential markdown or noise
            text = text.strip()
            if text.startswith("```"):
                import re
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    text = json_match.group(0)
                
            content = json.loads(text)
            content = _apply_heuristic(content)
            # Validation Check
            if attempt < max_retries - 1:
                banned_names = {"uncategorized", "misc", "other", "general"}
                used_banned = False
                for m in content.values():
                    folder_name = m.get("path", "").strip("/").lower()
                    if folder_name in banned_names:
                        used_banned = True
                        break
                
                if used_banned:
                    print("[Vercel AI] Validation Failed: Used banned catch-all folder name. Retrying...")
                    current_user_prompt += "\n\nCRITICAL FEEDBACK ON PREVIOUS ATTEMPT: You used a banned catch-all folder name like Uncategorized, Misc, Other, or General. This is strictly forbidden. Keep clustering until every file has a real, named home."
                    continue

                if len(fallback_files) > 1:
                    unique_folders = set(m.get("path", "").strip("/") for m in content.values())
                    if len(unique_folders) >= len(fallback_files):
                        print(f"[Vercel AI] Validation Failed: {len(unique_folders)} folders for {len(fallback_files)} files. Retrying...")
                        current_user_prompt += "\n\nCRITICAL FEEDBACK ON PREVIOUS ATTEMPT: Your previous attempt over-normalised by creating too many folders. The number of folders proposed was equal to or greater than the number of files. You MUST use FEWER, BROADER categories. The clusters ARE the folders. Do not create single-file folders."
                        continue
                        
                    # Singleton check
                    from collections import defaultdict
                    counts = defaultdict(int)
                    for m in content.values(): counts[m.get("path", "").strip("/")] += 1
                    
                    has_singletons = any(count == 1 for count in counts.values())
                    if has_singletons and len(fallback_files) >= 10:
                        print("[Vercel AI] Validation Failed: Created singleton folders in a large dataset. Retrying...")
                        current_user_prompt += "\n\nCRITICAL FEEDBACK ON PREVIOUS ATTEMPT: You created folders that contain only 1 file. Since there are 10 or more files, this is not allowed. Group singletons into broader categories."
                        continue
            
            # Post-validation (if attempt passed or max retries reached)
            from collections import defaultdict
            counts = defaultdict(int)
            for m in content.values(): counts[m.get("path", "").strip("/")] += 1
            if len(fallback_files) < 10:
                for f, m in content.items():
                    if counts[m.get("path", "").strip("/")] == 1:
                        m["reason"] = "[WARNING: Singleton category] " + m.get("reason", "")
            
            return content
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Vercel AI Error] {e}")
        # The core bug was here! It was generating singleton folders for every file when the API failed.
        return {f: {"path": "Uncategorized", "reason": f"API Error: {str(e)}"} for f in fallback_files}

@app.get("/")
def health_check():
    print("[Vercel Route] Health Check hit.")
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
    print(f"[Vercel Route] /analyze-structure hit with {len(payload.files)} files.")
    
    system_prompt = """You are an intelligent file organisation agent. Your job is to analyse a set of files and organise them into a folder structure that makes it as easy as possible for a human to find any file by thinking about what it is or what it's for — not by remembering its exact name.

## CORE PHILOSOPHY: SQL Normalisation Applied to Files
- 1NF (No repeating groups): No file stands alone in its own folder. Every folder must hold 2+ related files.
- 2NF (Full dependence): A file lives in a folder only if it genuinely belongs to that category — not just because it's loosely related.
- 3NF (No transitive dependencies): Folders are not nested arbitrarily. A subfolder only exists if its contents are meaningfully distinct from the parent.
- No redundancy: Never create two folders that describe the same concept differently (e.g. Invoices/ and Billing/ should be one).
- Atomic categories: Each folder represents exactly one clear concept. No vague catch-alls like Misc/ or Other/ unless absolutely unavoidable.

## STRICT ANTI-PATTERNS — NEVER DO THESE
- NEVER Create a folder named after a single file
- NEVER Create file1/file1.pdf (Duplicate names)
- NEVER Use banned catch-all names: Uncategorized, Misc, Other, General
- NEVER Nest folders more than 2 levels deep
- NEVER Organise by file extension as primary key (use purpose)
- NEVER Create empty folders (Every folder must contain at least 2 files)

## PRESERVE EXISTING OPTIMAL FOLDERS
If a folder already contains 2+ meaningfully related files and has a purposeful name, you MUST keep those files in that folder. Only fix what is broken.

## GUIDING QUESTION
"If the user forgot the filename entirely and only remembered what the file was FOR — would they be able to find it in under 10 seconds using this folder structure?"

Return ONLY a valid JSON object where keys are filenames and values are objects with 'path' and 'reason'. Do NOT include markdown blocks outside the JSON.
Example output:
{
  "q3_revenue.xlsx": {"path": "Finance", "reason": "quarterly financial data"},
  "invoice_acme_oct.pdf": {"path": "Finance/Invoices", "reason": "invoice"}
}
"""
    # Pre-Evaluate Existing Structure
    from collections import defaultdict
    current_map = {f.name: f.relative_path.strip("/").replace(f.name, "").strip("/") for f in payload.files}
    counts = defaultdict(int)
    for path in current_map.values():
        if path: counts[path] += 1
        
    banned_names = {"uncategorized", "misc", "other", "general"}
    optimal_folders = []
    has_banned_folders = False
    has_singletons = False
    
    for path, count in counts.items():
        if path.lower() in banned_names:
            has_banned_folders = True
        elif count >= 2:
            optimal_folders.append(path)
        else:
            has_singletons = True
            
    # Check if every file is in an optimal folder
    unplaced_files = sum(1 for p in current_map.values() if not p)
    is_fully_optimal = len(optimal_folders) > 0 and not has_banned_folders and not has_singletons and unplaced_files == 0
    
    if is_fully_optimal:
        print("[Vercel AI] Pre-Evaluation: Structure is already optimal. Short-circuiting.")
        return {
            "structure": {f.name: {"path": current_map[f.name], "reason": "Already optimally placed."} for f in payload.files},
            "optimization_possible": False,
            "message": "✅ No changes required. The current folder structure is already optimally organised."
        }
        
    user_prompt = f"Analyze these files: {[{'name': f.name, 'rel': f.relative_path} for f in payload.files]}"
    if optimal_folders:
        user_prompt += f"\n\nCRITICAL INSTRUCTION: The following folders are already optimal and MUST BE PRESERVED: {optimal_folders}. Keep any files currently in those folders exactly where they are."

    file_names = [f.name for f in payload.files]
    result = call_hf_inference(system_prompt, user_prompt, file_names)
    
    # Check for missing API Key return
    if isinstance(result, dict) and "error" in result:
        print("[CRITICAL] Aborting /analyze-structure due to missing API Key.")
        return JSONResponse(status_code=401, content=result)
        
    # Logic to detect optimization possible
    optimization_possible = False
    
    for fname, meta in result.items():
        proposed_path = meta.get("path", "").strip("/")
        current_path = current_map.get(fname, "")
        if proposed_path != current_path:
            optimization_possible = True
            break

    response_data = {
        "structure": result,
        "optimization_possible": optimization_possible
    }

    if not optimization_possible:
        response_data["message"] = "Structure is already optimized. No changes required."

    print(f"[Vercel AI] Successfully resolved structure. Optimization possible: {optimization_possible}")
    return response_data

@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def debug_catch_all(request: Request, path_name: str):
    # This route only hits if no other route matched.
    # It helps us see exactly what FastAPI is receiving.
    return JSONResponse(
        status_code=404,
        content={
            "status": "not_matched",
            "message": "No specific route found for this path.",
            "path_name": path_name,
            "full_url": str(request.url),
            "root_path": request.scope.get("root_path"),
            "fastapi_path": request.scope.get("path")
        }
    )

@app.post("/reevaluate-structure")
def reevaluate_structure(payload: ReevaluatePayload):
    system_prompt = f"""You are an intelligent file organisation agent. The user just manually categorized the file '{payload.override_file}' into the path '{payload.override_path}'.
Re-evaluate the remaining queue to adopt and follow this new categorization pattern where it makes sense.

## CORE PHILOSOPHY: SQL Normalisation Applied to Files
- 1NF (No repeating groups): No file stands alone in its own folder. Every folder must hold 2+ related files.
- 2NF (Full dependence): A file lives in a folder only if it genuinely belongs to that category.
- 3NF (No transitive dependencies): Folders are not nested arbitrarily. A subfolder only exists if its contents are meaningfully distinct from the parent.
- No redundancy: Never create two folders that describe the same concept differently.
- Atomic categories: Each folder represents exactly one clear concept. No vague catch-alls like Misc/ or Other/.

## STRICT ANTI-PATTERNS — NEVER DO THESE
- NEVER Create a folder named after a single file
- NEVER Create file1/file1.pdf (Duplicate names)
- NEVER Use banned catch-all names: Uncategorized, Misc, Other, General
- NEVER Nest folders more than 2 levels deep
- NEVER Organise by file extension as primary key (use purpose)
- NEVER Create empty folders (Every folder must contain at least 2 files)

## PRESERVE EXISTING OPTIMAL FOLDERS
If a folder already contains 2+ meaningfully related files and has a purposeful name, you MUST keep those files in that folder. Only fix what is broken.

## GUIDING QUESTION
"If the user forgot the filename entirely and only remembered what the file was FOR — would they be able to find it in under 10 seconds using this folder structure?"

Return ONLY a valid JSON object where keys are filenames and values are objects with 'path' and 'reason'. Do NOT include markdown blocks outside the JSON.
Example output:
{{
  "q3_revenue.xlsx": {{"path": "Finance", "reason": "quarterly financial data"}},
  "invoice_acme_oct.pdf": {{"path": "Finance/Invoices", "reason": "invoice"}}
}}
"""
    user_prompt = f"Remaining queue: {payload.remaining_files}"
    
    content = call_hf_inference(system_prompt, user_prompt, payload.remaining_files)
    print("[DEBUG reevaluate-structure] Successfully reevaluated.")
    return {"structure": content}

if __name__ == "__main__":
    import uvicorn
    # 8000 is the standard port for OpenEnv containers
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Explicitly expose app for Vercel discovery
application = app