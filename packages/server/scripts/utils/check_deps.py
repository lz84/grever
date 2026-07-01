#!/usr/bin/env python3
import importlib
for mod in ['uvicorn', 'fastapi', 'sqlalchemy', 'pydantic', 'httpx']:
    try:
        importlib.import_module(mod)
        print(f"{mod} OK")
    except ImportError as e:
        print(f"{mod} MISSING: {e}")