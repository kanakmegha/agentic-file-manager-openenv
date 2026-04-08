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

def main():
    import uvicorn
    # Make sure this matches your FastAPI variable name (usually 'app')
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()