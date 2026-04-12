import os
import requests
import json
from typing import List, Optional, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- MANDATORY CONFIGURATION (Phase 2 Proxy Compliance) ---
# The judges inject these. We MUST use them exactly.
API_BASE_URL = os.getenv("API_BASE_URL") 
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME") or "meta-llama/Llama-3.1-8B-Instruct"

TASK_NAME = "file_sorting"
BENCHMARK = "semantic_organizer_v1"

# CRITICAL: The base_url must point to the proxy URL provided in API_BASE_URL.
# We append /v1 because the LiteLLM proxy follows standard OpenAI routing.
client = OpenAI(
    base_url=f"{API_BASE_URL}/v1" if API_BASE_URL else "https://router.huggingface.co/v1",
    api_key=API_KEY
)

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
    print(f"[END] success={success_val} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

# --- Agentic Logic ---
def get_grouped_decisions(file_list: List[str]) -> Dict[str, str]:
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
    # Use the raw API_BASE_URL for the environment FastAPI calls
    API_BASE_URL_ENV = API_BASE_URL

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    rewards = []
    steps_taken = 0
    success = False
    total_score = 0.0
    
    try:
        # 1. Reset Environment
        reset_resp = requests.post(f"{API_BASE_URL_ENV}/reset", json={"episode_id": "ep001"}).json()
        files = reset_resp.get("observation", {}).get("remaining_files", [])
        
        # 2. Agent decides the grouping
        decision_map = get_grouped_decisions(files)
        
        # 3. Execute actions
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
        
        # 4. Score Calculation (Strictly between 0 and 1)
        total_score = sum(rewards)
        # Clamping to ensure we satisfy Phase 3 requirements
        total_score = min(max(total_score, 0.01), 0.99) 
        success = total_score >= 0.1
        
    except Exception as e:
        print(f"[DEBUG] Execution Error: {e}")
    finally:
        log_end(success=success, steps=steps_taken, score=total_score, rewards=rewards)

if __name__ == "__main__":
    main()