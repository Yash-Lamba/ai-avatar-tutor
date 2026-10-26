import os
from pathlib import Path

# Load .env file
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
