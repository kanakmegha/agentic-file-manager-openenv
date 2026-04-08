from pydantic import BaseModel, Field
from typing import List, Optional

class FileAction(BaseModel):
    file_name: str = Field(..., description="The name of the file to be moved.")
    category: str = Field(..., description="The target category: Finance, Work, or Personal.")

class FileObservation(BaseModel):
    remaining_files: List[str] = Field(..., description="List of files yet to be organized.")
    last_action_status: str = Field(..., description="Feedback on the last move (e.g., 'Success' or 'Wrong Category').")
    reward: float = Field(..., description="Reward for the last action (0.0 to 1.0).")
    done: bool = Field(default=False, description="Whether all files have been organized.")

class FileState(BaseModel):
    unsorted_files: List[str]
    sorted_files: List[str]
    total_files: int