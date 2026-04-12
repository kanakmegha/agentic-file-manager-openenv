import uuid
from typing import List, Dict, Optional
from openenv.core.env_server import Environment
from models import FileAction, FileObservation, FileState
import random
class FileOrganizerEnv(Environment):
    # Inside env.py -> FileOrganizerEnv class
    def __init__(self):
        super().__init__()
        self.task_sets = [
        ["invoice_march.pdf", "tax_return_2025.docs", "budget.xlsx"],
        ["project_roadmap.pdf", "meeting_notes.txt", "architecture.png"],
        ["family_photo.jpg", "vacation_itinerary.pdf", "song_backup.mp3"]
    ]
    # We will let the app.py instances handle the sets
    self.state_data = None

    # Inside env.py -> FileOrganizerEnv class
    def reset(self, episode_id: Optional[str] = None, seed: Optional[int] = None) -> FileObservation:
        import random
    # Use a seed if provided by the validator, otherwise random
        if seed is not None:
            random.seed(seed)
    
    # Pick a random set from your 3 task_sets defined in __init__
        files_for_this_run = random.choice(self.task_sets)
    
        self.state_data = FileState(
        unsorted_files=list(files_for_this_run),
        sorted_files=[],
        total_files=len(files_for_this_run)
        )
        return FileObservation(
        remaining_files=self.state_data.unsorted_files,
        last_action_status="Task Reset Successful",
        reward=0.01, 
        done=False
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