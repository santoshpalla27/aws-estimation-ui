import os
from pathlib import Path

# Use env var APP_ROOT if set, otherwise compute from this file location
# This file is deep inside backend/app/core/paths.py
# So root is 3 levels up from backend? 
# backend/app/core/paths.py -> parents[0]=core, [1]=app, [2]=backend.
# Wait, ROOT_DIR is the repo root.
# If structure is:
# REPO_ROOT/
#   backend/
#     app/
#       core/
#         paths.py
# Reference:
# backend/app/core/paths.py
# parents[0] = backend/app/core
# parents[1] = backend/app
# parents[2] = backend
# parents[3] = REPO_ROOT

def get_root_dir() -> Path:
    env_root = os.getenv("APP_ROOT")
    if env_root:
        return Path(env_root).resolve()
    
    # Resolve relative to this file
    # file: backend/app/core/paths.py
    return Path(__file__).resolve().parents[3]

ROOT_DIR = get_root_dir()

BACKEND_DIR = ROOT_DIR / "backend"
SERVICES_DIR = BACKEND_DIR / "services"

# Data directories
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"

# Files
METADATA_FILE = BACKEND_DIR / "service_metadata.json"
SERVICES_REGISTRY_FILE = BACKEND_DIR / "services_registry.json"

# Example for future pricing DB
PRICING_DB = DATA_DIR / "pricing.db"

# Ensure essential dirs exist (optional, but good for safety)
# DATA_DIR.mkdir(exist_ok=True)
# RAW_DIR.mkdir(exist_ok=True)
# NORMALIZED_DIR.mkdir(exist_ok=True)
