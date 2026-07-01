"""
Smoke test conftest - Session-scoped app + client for all endpoint tests.

Usage:
    $env:SQLITE_PATH="D:\work\research\agents-nexus\data\reins.db"
    pytest tests/smoke/ -v --tb=short
"""
import sys
import os
from pathlib import Path

# Add src to path
_src = str(Path(__file__).parent.parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Set default SQLITE_PATH if not set
if not os.environ.get("SQLITE_PATH"):
    os.environ["SQLITE_PATH"] = r"D:\work\research\agents-nexus\data\reins.db"

import pytest
from fastapi.testclient import TestClient
from api.server import create_app


@pytest.fixture(scope="session")
def app():
    """Create FastAPI application once per session."""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """TestClient shared across all tests in session."""
    return TestClient(app, raise_server_exceptions=False)
