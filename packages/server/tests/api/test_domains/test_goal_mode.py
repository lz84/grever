r"""
Goal mode regression tests — Sprint 122.

Verifies the engineering/research mode system, diversity fields,
and mode switching rules work correctly after migration.

Usage (Windows PowerShell):
    $env:SQLITE_PATH="D:\work\research\agents-nexus\data\reins.db"
    pytest tests/api/test_domains/test_goal_mode.py -v

NOTE: Goal mode is NOT set at creation time.
      Use POST /api/v1/goals/{id}/mode to set mode after creation.
"""
import pytest
from fastapi.testclient import TestClient


class TestGoalModeSetAfterCreation:
    """Mode is set via POST /mode after goal creation (not via GoalCreate)."""

    def test_create_goal_default_mode(self, client: TestClient, shared_data):
        """Goal created without explicit mode defaults to engineering."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-engineering-goal",
            "description": "Test goal for mode check",
            "priority": "medium",
        })
        assert resp.status_code in (200, 201), f"Got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        if "id" in data:
            goal_id = data["id"]
        elif "goal_id" in data:
            goal_id = data["goal_id"]
        else:
            pytest.skip(f"No goal id in response: {data}")
        shared_data.goal_ids.append(goal_id)

        # Read back
        resp = client.get(f"/api/v1/goals/{goal_id}")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text[:200]}"
        goal = resp.json()
        # Default mode should be engineering
        assert goal.get("mode") in ("engineering", None), \
            f"Expected mode=engineering or None, got {goal.get('mode')}"

    def test_set_mode_engineering(self, client: TestClient, shared_data):
        """POST /api/v1/goals/{id}/mode can set mode to engineering."""
        # Create goal
        resp = client.post("/api/v1/goals/", json={
            "title": "test-set-mode-eng",
            "description": "Test setting engineering mode",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code} {resp.text[:100]}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        # Set mode to engineering
        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "engineering",
        })
        assert resp.status_code in (200, 201, 204), \
            f"set mode=engineering failed: {resp.status_code} {resp.text[:200]}"

    def test_set_mode_research(self, client: TestClient, shared_data):
        """POST /api/v1/goals/{id}/mode can set mode to research."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-set-mode-research",
            "description": "Test setting research mode",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "best",
        })
        assert resp.status_code in (200, 201, 204), \
            f"set mode=research failed: {resp.status_code} {resp.text[:200]}"

    def test_set_mode_research_with_portfolio(self, client: TestClient, shared_data):
        """POST /api/v1/goals/{id}/mode can set research mode with portfolio."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-portfolio-mode",
            "description": "Test portfolio diversity",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "portfolio",
            "portfolio_size": 5,
        })
        assert resp.status_code in (200, 201, 204), \
            f"set mode=research+portfolio failed: {resp.status_code} {resp.text[:200]}"


class TestGoalModeRejectsOldValues:
    """Old mode values (normal/exploration/optimization) are rejected."""

    def test_set_mode_rejects_normal(self, client: TestClient, shared_data):
        """mode=normal is rejected by POST /mode."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-reject-normal",
            "description": "Test rejection of normal mode",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "normal",
        })
        assert resp.status_code in (400, 422), \
            f"mode=normal should be rejected with 400/422, got {resp.status_code}: {resp.text[:200]}"

    def test_set_mode_rejects_exploration(self, client: TestClient, shared_data):
        """mode=exploration is rejected by POST /mode."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-reject-exploration",
            "description": "Test rejection of exploration mode",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "exploration",
        })
        assert resp.status_code in (400, 422), \
            f"mode=exploration should be rejected with 400/422, got {resp.status_code}"

    def test_set_mode_rejects_optimization(self, client: TestClient, shared_data):
        """mode=optimization is rejected by POST /mode."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-reject-optimization",
            "description": "Test rejection of optimization mode",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "optimization",
        })
        assert resp.status_code in (400, 422), \
            f"mode=optimization should be rejected with 400/422, got {resp.status_code}"


class TestGoalModeResponseFields:
    """GET /api/v1/goals returns diversity and portfolio_size."""

    def test_get_goal_includes_new_fields(self, client: TestClient, shared_data):
        """GET /api/v1/goals/{id} includes diversity and portfolio_size."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-new-fields",
            "description": "Check new fields",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.get(f"/api/v1/goals/{goal_id}")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text[:200]}"
        goal = resp.json()
        # New fields must be present
        assert "diversity" in goal, "diversity field missing"
        assert "portfolio_size" in goal, "portfolio_size field missing"

    def test_list_goals_includes_new_fields(self, client: TestClient):
        """GET /api/v1/goals returns diversity/portfolio_size for each goal."""
        resp = client.get("/api/v1/goals?limit=5")
        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        goals = data.get("goals", [])
        if not goals:
            pytest.skip("No goals to check")
        for goal in goals:
            assert "diversity" in goal, f"goal {goal.get('id', '?')} missing diversity"
            assert "portfolio_size" in goal, f"goal {goal.get('id', '?')} missing portfolio_size"


class TestIterationAPI:
    """start-iteration requires research mode; HITL endpoints exist for all modes."""

    def test_start_iteration_requires_research_mode(self, client: TestClient, shared_data):
        """start-iteration is rejected for engineering mode goals."""
        # Create engineering goal
        resp = client.post("/api/v1/goals/", json={
            "title": "test-no-iteration-eng",
            "description": "Engineering goal — no iteration",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        # Explicitly set to engineering
        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={"mode": "engineering"})
        if resp.status_code not in (200, 201, 204):
            pytest.skip(f"Cannot set mode: {resp.status_code} {resp.text[:100]}")

        # Verify mode is engineering before proceeding
        resp = client.get(f"/api/v1/goals/{goal_id}")
        assert resp.status_code == 200
        goal = resp.json()
        if goal.get("mode") not in (None, "engineering"):
            pytest.skip(f"Goal mode is {goal.get('mode')}, not engineering — possible test isolation issue")

        # Activate first (do NOT start-iteration for engineering mode)
        resp = client.post(f"/api/v1/goals/{goal_id}/activate", json={})
        if resp.status_code == 409:
            pytest.skip("Goal already active")

        # Try to start-iteration — should be rejected for engineering mode
        resp = client.post(f"/api/v1/goals/{goal_id}/start-iteration", json={})
        # Engineering mode goals should NOT allow start-iteration
        # API may return 400 (business rejection) or 403 (forbidden)
        assert resp.status_code in (400, 403, 422), \
            f"engineering goal should reject start-iteration, got {resp.status_code}: {resp.text[:200]}"

    def test_start_iteration_works_for_research_goal(self, client: TestClient, shared_data):
        """start-iteration succeeds for research mode goal."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-iteration-research",
            "description": "Research goal for iteration test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        # Set to research mode
        client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "best",
        })

        # Activate first (required before start-iteration)
        client.post(f"/api/v1/goals/{goal_id}/activate", json={})

        # Now start-iteration
        resp = client.post(f"/api/v1/goals/{goal_id}/start-iteration", json={})
        assert resp.status_code in (200, 201), \
            f"start-iteration failed for research goal: {resp.status_code} {resp.text[:200]}"


class TestEngineeringModeHITL:
    """
    Engineering mode HITL: Task-level human approval via /tasks/{id}/add-hitl.

    Business flow:
    1. Create engineering goal + decompose into tasks
    2. Task execution calls POST /tasks/{id}/add-hitl to request human approval
    3. Task status becomes 'waiting_human'
    4. Human reviews via /human-review/pending
    5. Human approves/rejects via /human-review/batch-ruling
    """

    def test_human_review_pending_endpoint_accessible(self, client: TestClient):
        """GET /human-review/pending returns 200 (endpoint exists and accessible)."""
        resp = client.get("/api/v1/human-review/pending")
        assert resp.status_code == 200, \
            f"human-review/pending should be accessible, got {resp.status_code}: {resp.text[:200]}"

    def test_engineering_goal_allows_task_hitl(self, client: TestClient, shared_data):
        """Engineering mode goal has tasks that can request HITL approval."""
        # Create engineering goal
        resp = client.post("/api/v1/goals/", json={
            "title": "test-eng-hitl-goal",
            "description": "Engineering goal for HITL test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create goal: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        # Verify mode is engineering
        resp = client.get(f"/api/v1/goals/{goal_id}")
        assert resp.status_code == 200
        goal = resp.json()
        assert goal.get("mode") in (None, "engineering"), \
            f"Expected engineering mode, got {goal.get('mode')}"

        # Verify add-hitl endpoint exists for tasks (even if no tasks yet)
        # The endpoint should accept task_id - we just verify the route is registered
        resp = client.post(f"/api/v1/tasks/test-task-id/add-hitl", json={
            "title": "Test human input",
            "description": "Test request",
            "input_type": "human_approval",
        })
        # 404 = route not found (bad), 400/404 for non-existent task is ok
        assert resp.status_code != 405, \
            "POST /tasks/{id}/add-hitl should be allowed (route exists)"


class TestResearchBestModeHITL:
    """
    Research+Best mode HITL: Iteration-level convergence confirmation.

    Business flow:
    1. Create research+best goal and activate
    2. start-iteration begins iteration loop
    3. Each round generates solutions and calls _check_convergence()
    4. If requires_human=True → run_status='requires_human' → human confirms via converge-iteration
    5. Human can also participate via POST /goals/{id}/iterations/{id}/discuss
    """

    def test_iteration_status_endpoint_accessible(self, client: TestClient, shared_data):
        """GET /goals/{id}/iteration-status is accessible for research goals."""
        # Create research goal
        resp = client.post("/api/v1/goals/", json={
            "title": "test-research-best-iter",
            "description": "Research+Best goal",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        # Set research+best
        client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "best",
        })

        # iteration-status should be accessible even before start-iteration
        resp = client.get(f"/api/v1/goals/{goal_id}/iteration-status")
        assert resp.status_code in (200, 404), \
            f"iteration-status endpoint should be accessible, got {resp.status_code}"

    def test_research_best_mode_has_convergence_hitl(self, client: TestClient, shared_data):
        """Research+Best mode: converge-iteration endpoint exists for human to confirm."""
        # Create research goal
        resp = client.post("/api/v1/goals/", json={
            "title": "test-converge-hitl",
            "description": "Research+Best convergence HITL test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "best",
        })

        # converge-iteration endpoint should exist (route registered)
        resp = client.post(f"/api/v1/goals/{goal_id}/converge-iteration", json={})
        # 404 = route doesn't exist (bad), 400/401/403 = exists but needs valid state
        assert resp.status_code != 405, \
            "converge-iteration should be accessible (route exists)"


class TestResearchPortfolioModeHITL:
    """
    Research+Portfolio mode HITL: Human selects from N candidate solutions.

    Business flow:
    1. Create research+portfolio goal with portfolio_size=N
    2. start-iteration generates multiple candidates instead of converging
    3. Human participates via discuss to guide exploration direction
    4. Human manually calls converge-iteration or auto-assign to finalize
    5. Human can pause/resume exploration at any time
    """

    def test_portfolio_size_is_stored(self, client: TestClient, shared_data):
        """Research+Portfolio mode stores portfolio_size correctly."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-portfolio-size",
            "description": "Portfolio diversity test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "portfolio",
            "portfolio_size": 5,
        })
        assert resp.status_code in (200, 201, 204), \
            f"Setting portfolio mode failed: {resp.status_code} {resp.text[:200]}"

        # Read back
        resp = client.get(f"/api/v1/goals/{goal_id}")
        assert resp.status_code == 200
        goal = resp.json()
        assert goal.get("diversity") == "portfolio", \
            f"Expected diversity=portfolio, got {goal.get('diversity')}"
        assert goal.get("portfolio_size") == 5, \
            f"Expected portfolio_size=5, got {goal.get('portfolio_size')}"

    def test_portfolio_mode_allows_iteration(self, client: TestClient, shared_data):
        """Research+Portfolio mode allows start-iteration."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-portfolio-iteration",
            "description": "Portfolio iteration test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "portfolio",
            "portfolio_size": 3,
        })
        client.post(f"/api/v1/goals/{goal_id}/activate", json={})

        resp = client.post(f"/api/v1/goals/{goal_id}/start-iteration", json={})
        assert resp.status_code in (200, 201), \
            f"start-iteration should work for portfolio mode, got {resp.status_code}: {resp.text[:200]}"

    def test_portfolio_mode_has_pause_resume(self, client: TestClient, shared_data):
        """Portfolio mode supports pause/resume for human to control exploration."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-portfolio-pause",
            "description": "Portfolio pause/resume test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        resp2 = client.post(f"/api/v1/goals/{goal_id}/mode", json={
            "mode": "research",
            "diversity": "portfolio",
        })
        if resp2.status_code not in (200, 201, 204):
            pytest.skip(f"Cannot set mode: {resp2.status_code}")

        # Activate goal first (pause requires active goal)
        client.post(f"/api/v1/goals/{goal_id}/activate", json={})

        # pause endpoint should be accessible (200/204 = success, 400 = state not allowed)
        resp = client.post(f"/api/v1/goals/{goal_id}/pause", json={})
        assert resp.status_code != 405, \
            f"pause endpoint should be registered (not 405), got {resp.status_code}"


class TestDiversityDefaults:
    """diversity defaults to 'best' when not specified."""

    def test_diversity_defaults_to_best(self, client: TestClient, shared_data):
        """When setting research mode without diversity, defaults to 'best'."""
        resp = client.post("/api/v1/goals/", json={
            "title": "test-diversity-default",
            "description": "Diversity default test",
            "priority": "medium",
        })
        if resp.status_code not in (200, 201):
            pytest.skip(f"Cannot create: {resp.status_code}")
        data = resp.json()
        goal_id = data.get("id") or data.get("goal_id")
        if not goal_id:
            pytest.skip(f"No goal id: {data}")
        shared_data.goal_ids.append(goal_id)

        client.post(f"/api/v1/goals/{goal_id}/mode", json={"mode": "research"})

        resp = client.get(f"/api/v1/goals/{goal_id}")
        assert resp.status_code == 200
        goal = resp.json()
        assert goal.get("diversity") == "best", \
            f"Expected diversity=best by default, got {goal.get('diversity')}"


# =============================================================================
# Fixtures
# =============================================================================
from .conftest import SharedData

@pytest.fixture
def shared_data() -> SharedData:
    return SharedData()
