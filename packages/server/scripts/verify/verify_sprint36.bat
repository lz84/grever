@echo off
echo === Sprint 36 API Verification ===
echo.

echo 1. Project DAG API:
curl -s "http://localhost:8090/api/v1/projects/proj-001/diagram"
echo.

echo 2. Project Task Tree API:
curl -s "http://localhost:8090/api/v1/projects/proj-001/task-tree"
echo.

echo 3. Project Pause API (proj-002 -> on_hold):
curl -s -X PATCH "http://localhost:8090/api/v1/projects/proj-002/status?status=on_hold"
echo.

echo 4. Project Activate API (proj-002 -> active):
curl -s -X PATCH "http://localhost:8090/api/v1/projects/proj-002/status?status=active"
echo.

echo 5. Task Trace API (task-bc173c2b):
curl -s "http://localhost:8090/api/v1/traces/task-bc173c2b"
echo.

echo 6. Traces List API (limit 3):
curl -s "http://localhost:8090/api/v1/traces?limit=3"
echo.
