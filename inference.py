import os
import requests
import json
from typing import List, Optional, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
API_BASE_URL_ENV = os.getenv("API_BASE_URL")
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
TASK_NAME = "file_sorting"
BENCHMARK = "semantic_organizer_v1"

client = OpenAI(
    base_url="https://router.huggingface.co/v1/", 
    api_key=HF_TOKEN
)

# --- Logging Helpers ---
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# --- Agentic Logic: Global Decision Making ---
def get_grouped_decisions(file_list: List[str]) -> Dict[str, str]:
    """
    The agent looks at ALL files first to decide on the minimum 
    logical categories required to organize them efficiently.
    """
    system_prompt = (
        "You are an expert file organizer. Look at the list of filenames provided. "
        "Decide on the minimum number of logical categories needed to organize them. "
        "Return ONLY a valid JSON object where keys are filenames and values are your chosen categories."
    )
    user_prompt = f"Files to organize: {file_list}"
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[DEBUG] AI Grouping Error: {e}")
        # Fallback to a 1-to-1 mapping if JSON fails
        return {f: "Unsorted" for f in file_list}

def main():
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    rewards = []
    steps_taken = 0
    success = False
    
    try:
        # 1. Reset Environment
        reset_resp = requests.post(f"{API_BASE_URL_ENV}/reset", json={"episode_id": "ep001"}).json()
        files = reset_resp.get("observation", {}).get("remaining_files", [])
        
        # 2. Agent decides the grouping for all files at once
        decision_map = get_grouped_decisions(files)
        
        # 3. Execute actions based on the agent's plan
        for i, file_name in enumerate(files):
            step_idx = i + 1
            
            # Retrieve the category the agent decided for this specific file
            category = decision_map.get(file_name, "Miscellaneous")
            action_str = f"move({file_name},{category})"
            
            # 4. Step
            step_payload = {
                "action": {
                    "file_name": file_name,
                    "category": category
                }
            }
            res = requests.post(f"{API_BASE_URL_ENV}/step", json=step_payload).json()
            
            reward = res.get("reward", 0.0)
            done = res.get("done", False)
            obs = res.get("observation", {})
            error = obs.get("last_action_error")
            
            rewards.append(reward)
            steps_taken = step_idx
            
            log_step(step=step_idx, action=action_str, reward=reward, done=done, error=error)
            
            if done:
                break
        
        total_score = sum(rewards)
        success = total_score >= 0.8
        
    except Exception as e:
        print(f"[DEBUG] Execution Error: {e}")
    finally:
        log_end(success=success, steps=steps_taken, score=sum(rewards), rewards=rewards)

if __name__ == "__main__":
    main()