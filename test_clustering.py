import os
import sys
from dotenv import load_dotenv

# Load env variables for HF_TOKEN
load_dotenv()

# Add the current directory to sys.path so we can import from api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "api")))

from app import call_hf_inference, AnalyzePayload
from pydantic import BaseModel
from typing import List

class FileEntry(BaseModel):
    name: str
    relative_path: str

# Sample files from user instructions
sample_files = [
    FileEntry(name="RichDadPoorDad.pdf", relative_path="RichDadPoorDad.pdf"),
    FileEntry(name="The Intelligent Investor.pdf", relative_path="The Intelligent Investor.pdf"),
    FileEntry(name="Python-for-Data-Analysis.pdf", relative_path="Python-for-Data-Analysis.pdf"),
    FileEntry(name="TheDip.pdf", relative_path="TheDip.pdf"),
    FileEntry(name="TheDailyStoic.pdf", relative_path="TheDailyStoic.pdf"),
    FileEntry(name="BuildingASecondBrain.pdf", relative_path="BuildingASecondBrain.pdf")
]

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
- NEVER Use vague names like New Folder, Misc, Stuff
- NEVER Nest folders more than 2 levels deep
- NEVER Organise by file extension as primary key (use purpose)
- NEVER Create empty folders (Every folder must contain at least 2 files)

## GUIDING QUESTION
"If the user forgot the filename entirely and only remembered what the file was FOR — would they be able to find it in under 10 seconds using this folder structure?"

Return ONLY a valid JSON object where keys are filenames and values are objects with 'path' and 'reason'. Do NOT include markdown blocks outside the JSON.
Example output:
{
  "q3_revenue.xlsx": {"path": "Finance", "reason": "quarterly financial data"},
  "invoice_acme_oct.pdf": {"path": "Finance/Invoices", "reason": "invoice"}
}
"""

user_prompt = f"Analyze these files: {[{'name': f.name, 'rel': f.relative_path} for f in sample_files]}"
file_names = [f.name for f in sample_files]

print("Running test clustering...")
result = call_hf_inference(system_prompt, user_prompt, file_names)

print("\n--- FINAL CLUSTERING RESULT ---")
import json
print(json.dumps(result, indent=2))
