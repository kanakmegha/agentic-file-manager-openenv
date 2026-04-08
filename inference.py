import os
import requests
import textwrap
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
API_BASE_URL_ENV = os.getenv("API_BASE_URL")  # Your HF Space URL
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
TASK_NAME = "file_sorting"
BENCHMARK = "semantic_organizer_v1"

# Client for LLM
client = OpenAI(
    base_url="https://router.huggingface.co/v1/", 
    api_key=HF_TOKEN
)

# --- Logging Helpers (MANDATORY FORMAT) ---
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# --- AI Logic ---
def get_ai_decision(file_name: str) -> str:
    system_prompt = "You are a file classifier. Output ONLY the category name: Finance, Work, or Personal. No explanation."
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Categorize: {file_name}"},
            ],
            temperature=0.0,
            max_tokens=10
        )
        decision = completion.choices[0].message.content.strip().replace(".", "")
        # Basic validation to ensure we only send a single valid category word
        for cat in ["Finance", "Work", "Personal"]:
            if cat.lower() in decision.lower():
                return cat
        return "Work" # Default fallback
    except Exception:
        return "Work"

def main():
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    rewards = []
    steps_taken = 0
    success = False
    
    try:
        # 1. Reset
        reset_resp = requests.post(f"{API_BASE_URL_ENV}/reset", json={"episode_id": "ep001"}).json()
        # Navigate the OpenEnv wrapper response structure
        files = reset_resp.get("observation", {}).get("remaining_files", [])
        
        for i, file_name in enumerate(files):
            step_idx = i + 1
            
            # 2. AI Decision
            category = get_ai_decision(file_name)
            action_str = f"move({file_name},{category})"
            
            # 3. Step
            step_payload = {
                "action": {
                    "file_name": file_name,
                    "category": category
                }
            }
            res = requests.post(f"{API_BASE_URL_ENV}/step", json=step_payload).json()
            
            # 4. Extract Data
            reward = res.get("reward", 0.0)
            done = res.get("done", False)
            obs = res.get("observation", {})
            error = obs.get("last_action_error") # Matches schema in your env.py
            
            rewards.append(reward)
            steps_taken = step_idx
            
            # 5. Log Step (STDOUT)
            log_step(step=step_idx, action=action_str, reward=reward, done=done, error=error)
            
            if done:
                break
        
        total_score = sum(rewards)
        success = total_score >= 0.8 # Define success threshold
        
    except Exception as e:
        print(f"[DEBUG] Execution Error: {e}")
    finally:
        # 6. Log End (STDOUT)
        log_end(success=success, steps=steps_taken, score=sum(rewards), rewards=rewards)

if __name__ == "__main__":
    main()