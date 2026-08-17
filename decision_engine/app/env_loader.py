import os
from pathlib import Path
from dotenv import load_dotenv

def load_root_env() -> bool:
    """
    Traverses up the folder hierarchy starting from this file to find and load
    the repository-level `.env` file explicitly. This ensures environment loading
    is completely deterministic regardless of the current working directory from which
    uvicorn or python is started.
    """
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path))
            return True
    
    # Default fallback search
    load_dotenv()
    return False

# Execute on import
load_root_env()
