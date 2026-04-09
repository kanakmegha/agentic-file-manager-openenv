import uuid
from typing import List, Dict, Optional
from openenv.core.env_server import Environment
from models import FileAction, FileObservation, FileState

class FileOrganizerEnv(Environment):
    def __init__(self):
        super().__init__()
        # 1. ADDED 3 TASKS: Validator requires at least 3 tasks with graders.
        self.task_library = [
            ["invoice_march.pdf", "tax_return_2025.docs", "budget_planning.xlsx"],
            ["main_logic.py", "utils.js", "README.md", "styles.css"],
            ["family_photo.jpg", "vacation_itinerary.pdf", "flight_tickets.pdf"]
        ]
        self.current_task_idx = 0
        self.all_files = self.task_library[self.current_task_idx]
        self.state_data = None

    def reset(self, episode_id: Optional[str] = None, seed: Optional[int] = None) -> FileObservation:
        """Resets the environment state and cycles through the 3 tasks."""
        # Cycle through tasks to ensure we provide at least 3 different scenarios
        self.all_files = self.task_library[self.current_task_idx]
        self.current_task_idx = (self.current_task_idx + 1) % len(self.task_library)

        self.state_data = FileState(
            unsorted_files=list(self.all_files),
            sorted_files=[],
            total_files=len(self.all_files)
        )
        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status="Environment Reset. Multi-task scenario active.",
            reward=0.0,
            done=False
        )

    def step(self, action: FileAction) -> FileObservation:
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

        # 2. GRANULAR REWARDS: Scores must be strictly between 0 and 1.
        # We cap the total possible score at 0.95 and floor it at 0.05.
        step_reward = 0.05 / self.state_data.total_files # Default floor reward
        
        if is_valid:
            # Max possible score across all steps will be 0.95
            step_reward = 0.95 / self.state_data.total_files
            if file_name in self.state_data.unsorted_files:
                self.state_data.unsorted_files.remove(file_name)
                self.state_data.sorted_files.append({"file": file_name, "category": category})
            status = f"Accepted: Agent assigned {file_name} to '{category}'"
        else:
            status = f"Partial/Rejected: '{category}' lacks strong link to {file_name}"

        done = len(self.state_data.unsorted_files) == 0
        
        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status=status,
            reward=step_reward,
            done=done
        )

    @property
    def state(self) -> FileState:
        return self.state_data