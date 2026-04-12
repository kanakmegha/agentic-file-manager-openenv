from fastapi import FastAPI
from openenv.core.env_server import create_fastapi_app
from models import FileAction, FileObservation
from env import FileOrganizerEnv

# The validator wants the CLASS here, not a dictionary
app = create_fastapi_app(
    FileOrganizerEnv, 
    FileAction, 
    FileObservation
)

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()