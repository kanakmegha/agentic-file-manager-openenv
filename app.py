from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from pydantic import BaseModel
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from openenv.core.env_server import create_fastapi_app
from models import FileAction, FileObservation
from env import FileOrganizerEnv

load_dotenv()

# Fix: We pass the Class 'FileOrganizerEnv', not the instance 'env_logic'
app = create_fastapi_app(
    FileOrganizerEnv, 
    FileAction, 
    FileObservation
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FileNames(BaseModel):
    files: List[str]

@app.post("/suggest-category")
def suggest_category(payload: FileNames):
    API_BASE_URL = os.environ.get("API_BASE_URL") 
    API_KEY = os.environ.get("API_KEY")
    MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
    
    if not API_KEY or not API_BASE_URL:
        # Fallback if no LLM configured
        fallback = {}
        for f in payload.files:
            fallback[f] = f.split('_')[0].split('.')[0].capitalize()
        return {"suggestions": fallback}
        
    try:
        client = OpenAI(
            base_url=f"{API_BASE_URL}/v1", 
            api_key=API_KEY
        )
        system_prompt = (
            "You are a file management agent. Your goal is to sort files into logical categories. "
            "For each file, create a category name that is a substring of the filename. "
            "Example: 'invoice_march.pdf' -> 'Invoice', 'tax_2025.docs' -> 'Tax'. "
            "Return a JSON object where keys are filenames and values are the categories."
        )
        user_prompt = f"Categorize these files now: {payload.files}"
        
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        return {"suggestions": json.loads(content)}
    except Exception as e:
        print(f"Error suggesting categories: {e}")
        fallback = {}
        for f in payload.files:
            fallback[f] = f.split('_')[0].split('.')[0].capitalize()
        return {"suggestions": fallback}

if __name__ == "__main__":
    import uvicorn
    # 8000 is the standard port for OpenEnv containers
    uvicorn.run(app, host="0.0.0.0", port=8000)