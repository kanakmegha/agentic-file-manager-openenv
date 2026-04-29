import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "api")))

from app import analyze_structure, AnalyzePayload
from pydantic import BaseModel
from typing import List

class FileEntry(BaseModel):
    name: str
    relative_path: str
    size: int = 100
    last_modified: int = 123456

# Test files with partial structure:
# Investment is optimal (2 files)
# Uncategorized is banned (3 files)
# Singleton folder (1 file)
test_payload = AnalyzePayload(files=[
    {"name":"RichDadPoorDad.pdf", "relative_path":"Investment/RichDadPoorDad.pdf", "size":100, "last_modified":123},
    {"name":"The Intelligent Investor.pdf", "relative_path":"Investment/The Intelligent Investor.pdf", "size":100, "last_modified":123},
    {"name":"Python-for-Data-Analysis.pdf", "relative_path":"Technology/Python-for-Data-Analysis.pdf", "size":100, "last_modified":123},
    {"name":"TheDip.pdf", "relative_path":"Business/TheDip.pdf", "size":100, "last_modified":123},
    {"name":"BuildingASecondBrain.pdf", "relative_path":"Business/BuildingASecondBrain.pdf", "size":100, "last_modified":123},
    {"name":"TheDailyStoic.pdf", "relative_path":"Technology/TheDailyStoic.pdf", "size":100, "last_modified":123}
])

print("Running analyze_structure...")
result = analyze_structure(test_payload)

print("\n--- FINAL CLUSTERING RESULT ---")
import json
print(json.dumps(result, indent=2))
