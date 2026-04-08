import uuid
from typing import List, Dict, Optional
# CRITICAL IMPORT
from openenv.core.env_server import Environment
from models import FileAction, FileObservation, FileState

class FileOrganizerEnv(Environment):
    def __init__(self):
        super().__init__()
        # The ground truth is now just the existence of these files
        self.all_files = [
            "invoice_march.pdf", 
            "tax_return_2025.docs", 
            "project_roadmap.pdf", 
            "meeting_notes_monday.txt", 
            "family_photo.jpg", 
            "vacation_itinerary.pdf"
        ]
        self.state_data = None

    def reset(self, episode_id: Optional[str] = None, seed: Optional[int] = None) -> FileObservation:
        """Resets the environment state for a new episode."""
        self.state_data = FileState(
            unsorted_files=list(self.all_files),
            sorted_files=[],
            total_files=len(self.all_files)
        )
        return FileObservation(
            remaining_files=self.state_data.unsorted_files,
            last_action_status="Environment Reset. Agent is now planning categories.",
            reward=0.0,
            done=False
        )

    def step(self, action: FileAction) -> FileObservation:
        if self.state_data is None:
            self.reset()

        file_name = action.file_name.strip()
        category = action.category.strip()
        
        # --- TRUE AGENTIC VALIDATION ---
        # The environment has NO pre-defined categories.
        # It rewards the agent if the chosen category is 'meaningfully' 
        # related to the file name through string logic.
        file_lower = file_name.lower()
        cat_lower = category.lower()

        # We validate the 'meaning' by checking if the category name 
        # is a substring, a plural/singular version, or shares a root.
        # Example: 'invoice_march.pdf' + 'Invoices' = Success
        is_valid = (
            cat_lower in file_lower or 
            file_lower.startswith(cat_lower[:3]) or 
            cat_lower.rstrip('s') in file_lower or
            any(word in file_lower for word in cat_lower.split())
        )

        step_reward = 0.0
        if is_valid:
            step_reward = 1.0 / self.state_data.total_files
            if file_name in self.state_data.unsorted_files:
                self.state_data.unsorted_files.remove(file_name)
                self.state_data.sorted_files.append({"file": file_name, "category": category})
            status = f"Accepted: Agent intelligently assigned {file_name} to '{category}'"
        else:
            # If it's a completely random word like 'Banana' for 'tax.pdf', we reject it.
            status = f"Rejected: '{category}' has no clear semantic link to {file_name}"

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