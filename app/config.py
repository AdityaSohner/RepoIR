import os
from pathlib import Path

DEFAULT_USER_ID = "user_local_001"

# Persistent Data Directory (HF Spaces mounts persistent storage at /data)
DATA_DIR_PATH = os.getenv("DATA_DIR")
if DATA_DIR_PATH:
    DATA_DIR = Path(DATA_DIR_PATH)
elif os.path.exists("/data"):
    DATA_DIR = Path("/data")
else:
    DATA_DIR = Path("data")

DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "users").mkdir(parents=True, exist_ok=True)
