"""
Pytest configuration for integration tests
"""
import sys

# Increase recursion limit for deep import chains (pydantic + FastAPI)
if sys.getrecursionlimit() < 2000:
    sys.setrecursionlimit(2000)
