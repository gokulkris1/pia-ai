"""Make ``backend/`` importable so tests can ``from main import app`` etc.,
matching the runtime layout (uvicorn is launched with ``--app-dir backend``).
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
