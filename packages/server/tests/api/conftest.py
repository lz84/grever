"""
Shared conftest for tests/api/ directory.
Session-scoped app + client + test data management.

Usage:
    $env:SQLITE_PATH="D:\work\research\agents-nexus\data\reins.db"
    pytest tests/api/ -v --tb=short
"""
import sys
import os
import uuid
import time
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


@pytest.fixture(scope="session")
def test_data():
    """Shared test data store populated as tests progress."""
    return TestData()


class TestData:
    """Shared test data across test files."""
    agent_id = None
    agent_ids = []
    goal_id = None
    goal_ids = []
    project_id = None
    project_ids = []
    task_id = None
    task_ids = []
    workflow_id = None
    workflow_ids = []
    scenario_id = None
    scenario_ids = []
    solution_id = None
    solution_ids = []
    dispute_id = None
    cognition_id = None
    hitl_id = None
    pack_id = None
    skill_id = None
    knowledge_id = None
    artifact_id = None
    capsule_id = None
    gene_id = None
    role_id = None


def gen_uuid():
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def now_ts():
    """Current unix timestamp."""
    return int(time.time())


def capability_tags():
    """Default capability tags."""
    return {
        "technical": "backend",
        "business": "reach",
        "professional": "industry_pack",
        "management": "self"
    }
