import os
import sys
from pathlib import Path

def get_root_dir() -> Path:
    env_root = os.getenv("APP_ROOT")
    if env_root:
        return Path(env_root).resolve()
    
    # Resolve relative to this file
    # file: backend/app/core/paths.py
    # parents[0]=core, [1]=app, [2]=backend, [3]=root
    path = Path(__file__).resolve().parents[3]
    print(f"DEBUG: paths.py resolved ROOT_DIR to: {path}", file=sys.stderr)
    return path

ROOT_DIR = get_root_dir()

BACKEND_DIR = ROOT_DIR / "backend"
SERVICES_DIR = BACKEND_DIR / "services"

# Data directories
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"

# Files
METADATA_FILE = DATA_DIR / "service_metadata.json"
SERVICES_REGISTRY_FILE = BACKEND_DIR / "services_registry.json"

# Example for future pricing DB
PRICING_DB = DATA_DIR / "pricing.db"
print(f"DEBUG: paths.py resolved PRICING_DB to: {PRICING_DB}", file=sys.stderr)

# Ensure essential dirs exist (optional, but good for safety)
# DATA_DIR.mkdir(exist_ok=True)
# RAW_DIR.mkdir(exist_ok=True)
# NORMALIZED_DIR.mkdir(exist_ok=True)
