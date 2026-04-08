from fastapi import FastAPI
from openenv.core.env_server import create_fastapi_app
from models import FileAction, FileObservation
from env import FileOrganizerEnv

# Fix: We pass the Class 'FileOrganizerEnv', not the instance 'env_logic'
app = create_fastapi_app(
    FileOrganizerEnv, 
    FileAction, 
    FileObservation
)

if __name__ == "__main__":
    import uvicorn
    # 8000 is the standard port for OpenEnv containers
    uvicorn.run(app, host="0.0.0.0", port=8000)