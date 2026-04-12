import os
import requests
import json
from typing import List, Optional, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- MANDATORY CONFIGURATION (Phase 2 & Phase 3 Compliance) ---
# The validator log specifically asks to use these exact os.environ calls.
API_BASE_URL = os.environ.get("API_BASE_URL") 
API_KEY = os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

TASK_NAME = "file_sorting"
BENCHMARK = "semantic_organizer_v1"

# 1. INITIALIZE OPENAI CLIENT EXACTLY AS REQUESTED
# We append /v1 because the LiteLLM proxy uses standard OpenAI endpoint routing.
client = OpenAI(
    base_url=f"{API_BASE_URL}/v1", 
    api_key=API_KEY
)

# 2. API_BASE_URL_ENV for the environment FastAPI calls
API_BASE_URL_ENV = API_BASE_URL

# --- Logging Helpers (STRICT HACKATHON FORMAT) ---
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    success_val = str(success).lower()
    # Scoring must be strictly within (0, 1) as per Phase 3 requirements
    print(f"[END] success={success_val} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

# --- Agentic Logic: Global Decision Making ---
def get_grouped_decisions(file_list: List[str]) -> Dict[str, str]:
    """
    Agent logic using the LiteLLM proxy to decide categories.
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
        return {f: "Unsorted" for f in file_list}

def main():
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    rewards = []
    steps_taken = 0
    success = False
    
    try:
        # 1. Reset Environment using the provided BASE_URL
        reset_resp = requests.post(f"{API_BASE_URL_ENV}/reset", json={"episode_id": "ep001"}).json()
        files = reset_resp.get("observation", {}).get("remaining_files", [])
        
        # 2. Agent decides grouping
        decision_map = get_grouped_decisions(files)
        
        # 3. Execution
        for i, file_name in enumerate(files):
            step_idx = i + 1
            category = decision_map.get(file_name, "Miscellaneous")
            action_str = f"move({file_name},{category})"
            
            step_payload = {
                "action": {"file_name": file_name, "category": category}
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
        
        # 4. Final Score Logic (Ensuring strictly 0 < score < 1)
        score = sum(rewards)
        # Clamping to ensure we don't hit exactly 1.0 or 0.0
        score = min(max(score, 0.01), 0.99)
        success = score >= 0.1
        
    except Exception as e:
        print(f"[DEBUG] Execution Error: {e}")
        score = 0.01
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    main()