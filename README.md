# 📂 Semantic File Organizer

![Header](header.png)

**Semantic File Organizer** is an AI agent environment and benchmark designed for real-world file categorization. It provides a FastAPI-powered sandbox where autonomous agents can demonstrate their ability to intelligently organize unsorted files into meaningful categories.

## 🚀 Key Features

- **Agentic Environment**: A robust benchmarking platform for file organization tasks.
- **Semantic Validation**: Unlike rigid rule-based systems, it validates actions based on the semantic relationship between filenames and categories.
- **FastAPI Integration**: Simple, standardized API for agent-environment interaction.
- **Container Ready**: Includes a `Dockerfile` for easy deployment and scaling.
- **Automated Validation**: Built-in scripts to verify submission integrity.

## 🛠️ Architecture

The project consists of three main components:

1.  **Environment (`env.py`)**: The core logic that manages file states, rewards agents for logical groupings, and handles episode resets.
2.  **Server (`app.py`)**: A FastAPI wrapper that exposes the environment via REST endpoints (`/step`, `/reset`).
3.  **Agent (`inference.py`)**: A reference implementation of an AI agent that uses LLMs (via Hugging Face) to make high-level categorization decisions.

## 📥 Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd OpenenvRound1
    ```

2.  **Set up a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables**:
    Create a `.env` file with the following:
    ```env
    API_BASE_URL="http://localhost:8000"
    HF_TOKEN="your_huggingface_token"
    MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
    ```

## 🎮 Usage

### Running the Server
Start the FastAPI environment server:
```bash
python3 -m uvicorn app:app --reload
```

### Running the Agent
Execute the agent to start the file organization task:
```bash
python3 inference.py
```

### Validating the Project
Run the validation script to ensure everything is configured correctly:
```bash
./validate-submission.sh <your-endpoint-url>
```

## 🧪 Development

### Directory Structure
- `app.py`: FastAPI entry point.
- `env.py`: Environment logic and reward structures.
- `models.py`: Pydantic data models for API communication.
- `inference.py`: Agentic decision-making and LLM integration.
- `openenv.yaml`: Benchmark configuration.

### Customization
You can modify `env.py` to change the initial file set or refine the semantic validation logic. The current implementation rewards categories that share linguistic roots or semantic meaning with the filenames.

## 📄 License
This project is licensed under the MIT License.
