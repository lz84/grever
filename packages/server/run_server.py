import os
import sys

os.environ["SQLITE_PATH"] = r"D:\work\research\agents-nexus\data\reins.db"

# Load .env file for NEXUS_BASE_URL and other configs
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass  # python-dotenv not installed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import uvicorn
from reins.api.server import app

uvicorn.run(app, host="0.0.0.0", port=8097)
