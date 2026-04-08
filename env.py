import uuid
from typing import List, Dict, Optional
# CRITICAL IMPORT
from openenv.core.env_server import Environment
from models import FileAction, FileObservation, FileState

# Update: Your class now inherits from Environment
class FileOrganizerEnv(Environment):
    def __init__(self):
        # Initialize the base class
        super().__init__()
        
        self.correct_mapping = {
            "invoice_march.pdf": "Finance",
            "tax_return_2025.docs": "Finance",
            "project_roadmap.pdf": "Work",
            "meeting_notes_monday.txt": "Work",
            "family_photo.jpg": "Personal",
            "vacation_itinerary.pdf": "Personal"
        }
        self.state_data = None

    def reset(self, episode_id: Optional[str] = None, seed: Optional[int] = None) -> FileObservation:
        self.state_data = FileState(
            unsorted_files=list(self.correct_mapping.keys()),
            sorted_files=[],
            total_files=len(self.correct_mapping)
        )
        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status="Environment Reset. Start sorting.",
            reward=0.0,
            done=False
        )

    def step(self, action: FileAction) -> FileObservation:
        # Safety Check: If someone calls step before reset
        if self.state_data is None:
            self.reset()

        file_name = action.file_name.strip()
        category = action.category.strip()
        correct_category = self.correct_mapping.get(file_name)
        
        # Initialize reward for this step
        step_reward = 0.0
        
        if correct_category and correct_category.lower() == category.lower():
            # Calculate reward based on progress
            step_reward = 1.0 / len(self.correct_mapping)
            
            if file_name in self.state_data.unsorted_files:
                self.state_data.unsorted_files.remove(file_name)
                self.state_data.sorted_files.append(file_name)
            status = f"Success: Moved {file_name} to {category}"
        else:
            status = f"Incorrect: {file_name} does not belong in {category}"

        done = len(self.state_data.unsorted_files) == 0
        
        # IMPORTANT: Return the FileObservation model
        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status=status,
            reward=step_reward,
            done=done
        )

    # Required by the OpenEnv interface
    @property
    def state(self) -> FileState:
        return self.state_data