import uuid
from typing import List, Dict, Optional
from openenv.core.env_server import Environment
from models import FileAction, FileObservation, FileState

class FileOrganizerEnv(Environment):
    def __init__(self):
        super().__init__()
        # Ensure these match your models.py exactly
        self.task_sets = [
            ["invoice_march.pdf", "tax_return_2025.docs", "budget.xlsx"],
            ["project_roadmap.pdf", "meeting_notes.txt", "architecture.png"],
            ["family_photo.jpg", "vacation_itinerary.pdf", "song_backup.mp3"]
        ]
        self.current_task_idx = 0
        self.state_data = None

    def reset(self, episode_id: Optional[str] = None, seed: Optional[int] = None) -> FileObservation:
        try:
            # Select task based on index
            files_for_this_run = self.task_sets[self.current_task_idx % len(self.task_sets)]
            self.current_task_idx += 1
            
            # Initialize State
            self.state_data = FileState(
                unsorted_files=list(files_for_this_run),
                sorted_files=[],
                total_files=len(files_for_this_run)
            )
            
            return FileObservation(
                remaining_files=self.state_data.unsorted_files,
                last_action_status=f"Task {self.current_task_idx} Initialized",
                reward=0.01, 
                done=False
            )
        except Exception as e:
            # Fallback to prevent 500 error
            print(f"Reset Error: {e}")
            return FileObservation(
                remaining_files=[],
                last_action_status="Error during reset",
                reward=0.0,
                done=True
            )

    def step(self, action: FileAction) -> FileObservation:
        try:
            if self.state_data is None:
                self.reset()

            file_name = action.file_name.strip()
            category = action.category.strip()
            
            file_lower = file_name.lower()
            cat_lower = category.lower()

            # Semantic Logic
            is_valid = (
                cat_lower in file_lower or 
                file_lower.startswith(cat_lower[:3]) or 
                cat_lower.rstrip('s') in file_lower or
                any(word in file_lower for word in cat_lower.split())
            )

            step_reward = 0.02 
            if is_valid:
                step_reward = (0.90 / self.state_data.total_files)
                if file_name in self.state_data.unsorted_files:
                    self.state_data.unsorted_files.remove(file_name)
                    self.state_data.sorted_files.append({"file": file_name, "category": category})
                status = f"Accepted: {file_name} -> {category}"
            else:
                status = f"Rejected: {category} invalid"

            done = len(self.state_data.unsorted_files) == 0
            
            return FileObservation(
                remaining_files=self.state_data.unsorted_files,
                last_action_status=status,
                reward=round(float(step_reward), 3),
                done=done
            )
        except Exception as e:
            print(f"Step Error: {e}")
            return FileObservation(
                remaining_files=[],
                last_action_status="Error during step",
                reward=0.0,
                done=True
            )

    @property
    def state(self) -> FileState:
        return self.state_data