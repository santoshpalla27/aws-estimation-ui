import os
import pytest
from pathlib import Path
from backend.app.core import paths

def test_root_dir_resolution():
    # Test that ROOT_DIR resolves to the repository root
    # We assume setup.cfg or .git or requirements.txt exists in root
    assert (paths.ROOT_DIR / "backend").exists()
    assert (paths.ROOT_DIR / "docker-compose.yml").exists()

def test_env_var_override(monkeypatch):
    # Set a fake APP_ROOT
    fake_root = Path("/tmp/fake_root")
    monkeypatch.setenv("APP_ROOT", str(fake_root))
    
    # Reload module to pick up env var
    import importlib
    importlib.reload(paths)
    
    assert paths.ROOT_DIR == fake_root
    assert paths.BACKEND_DIR == fake_root / "backend"

def test_directory_structure():
    # Verify computed paths match expected structure
    importlib.reload(paths) # Reset to default
    
    assert paths.BACKEND_DIR.name == "backend"
    assert paths.SERVICES_DIR.name == "services"
    assert paths.DATA_DIR.name == "data"
    assert paths.RAW_DIR.name == "raw"
    assert paths.NORMALIZED_DIR.name == "normalized"

import importlib
