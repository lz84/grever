"""
API 全覆盖测试 - Conftest

5 层测试依赖链的共享 fixtures。
按测试用例总览 v2.2 定义的顺序执行。

使用方式:
    pytest tests/api/api_coverage/ -v --tb=short
    pytest tests/api/api_coverage/layer0 -v
    pytest tests/api/api_coverage/layer1 -v
"""
import pytest
import sys
import os
import uuid
import time
from pathlib import Path

# Setup path
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from fastapi.testclient import TestClient
from api.server import create_app


# ============================================================================
# Application & Client Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def app():
    """Create FastAPI application for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """TestClient for API calls."""
    return TestClient(app)


# ============================================================================
# Shared Test Data Store
# ============================================================================

class TestData:
    """Shared test data across layers. Populated as tests progress."""
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


@pytest.fixture(scope="session")
def shared_data():
    """Shared test data store across all layers."""
    return TestData()


# ============================================================================
# Helper Functions
# ============================================================================

def gen_id(prefix="test"):
    """Generate unique test ID."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def now_ts():
    """Current unix timestamp."""
    return int(time.time())


def default_capability_tags():
    """Default capability tags for task creation."""
    return {
        "technical": "backend",
        "business": "reach",
        "professional": "industry_pack",
        "management": "self"
    }
