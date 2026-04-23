from typing import List, Dict, Optional, Any
from models import FileAction, FileObservation, FileState

# Global counter to cycle through tasks every time the class is instantiated
_TASK_COUNTER = 0

class FileOrganizerEnv:
    def __init__(self):
        global _TASK_COUNTER
        self.task_sets = [
            ["invoice_march.pdf", "tax_return_2025.docs", "budget.xlsx"],
            ["project_roadmap.pdf", "meeting_notes.txt", "architecture.png"],
            ["family_photo.jpg", "vacation_itinerary.pdf", "song_backup.mp3"]
        ]
        # Pick the set based on the current global count, then increment
        self.task_files = self.task_sets[_TASK_COUNTER % 3]
        _TASK_COUNTER += 1
        self.state_data = None

    def reset(self, episode_id: Optional[str] = None, seed: Optional[int] = None) -> FileObservation:
        self.state_data = FileState(
            unsorted_files=list(self.task_files),
            sorted_files=[],
            total_files=len(self.task_files)
        )
        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status="Reset Successful",
            reward=0.01, 
            done=False
        )

    def step(self, action: FileAction) -> FileObservation:
        # Keep your existing semantic logic here...
        file_name = action.file_name.strip()
        category = action.category.strip()
        
        file_lower = file_name.lower()
        cat_lower = category.lower()
        is_valid = (cat_lower in file_lower or any(word in file_lower for word in cat_lower.split()))

        step_reward = 0.05
        if is_valid:
            step_reward = (0.90 / self.state_data.total_files)
            if file_name in self.state_data.unsorted_files:
                self.state_data.unsorted_files.remove(file_name)
            status = f"Accepted: {file_name}"
        else:
            status = f"Rejected: {category}"

        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status=status,
            reward=round(float(step_reward), 3),
            done=len(self.state_data.unsorted_files) == 0
        )

    @property
    def state(self) -> FileState:
        return self.state_data