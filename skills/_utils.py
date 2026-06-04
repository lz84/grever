"""
Nexus Skills Shared Utilities — HTTP client, config, display helpers.

Imported by all skill Python modules. Place at skills/_utils.py.
"""

import json
import sys
import os
from typing import Optional, List, Dict, Any

# ========== Path Resolution ==========
SKILLS_ROOT = os.path.dirname(os.path.abspath(__file__))
NEXUS_ROOT = os.environ.get("NEXUS_ROOT", os.path.join(SKILLS_ROOT, "..", ".."))
SERVER_SRC = os.path.join(NEXUS_ROOT, "packages", "server", "src")
if os.path.isdir(SERVER_SRC) and SERVER_SRC not in sys.path:
    sys.path.insert(0, SERVER_SRC)

# ========== Configuration (all via env vars) ==========
NEXUS_SERVER = os.environ.get("NEXUS_SERVER_URL", "http://localhost:8094")
AGENT_ID = os.environ.get("NEXUS_AGENT_ID", "")
AGENT_NAME = os.environ.get("NEXUS_AGENT_NAME", "")
AGENT_CAPABILITIES = [c.strip() for c in os.environ.get("NEXUS_CAPABILITIES", "").split(",") if c.strip()]
TRIGGER_MODE = os.environ.get("NEXUS_TRIGGER_MODE", "sse")
MAX_LOAD = int(os.environ.get("NEXUS_MAX_LOAD", "5"))
POLL_INTERVAL = int(os.environ.get("NEXUS_POLL_INTERVAL", "30"))

LLM_API = os.environ.get("LLM_API", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3-30b-a3b-fp8")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "123")

# ========== HTTP Client ==========
try:
    import requests as _http
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def api_get(url: str, timeout: int = 10) -> Optional[Any]:
    """Generic GET — returns parsed JSON or None."""
    if not HAS_REQUESTS:
        print("Error: 'requests' library not installed.", file=sys.stderr)
        return None
    try:
        r = _http.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"API GET error: {e}", file=sys.stderr)
        return None


def api_post(url: str, data: Dict, headers: Dict = None, timeout: int = 10) -> tuple:
    """Generic POST — returns (status_code, json_data)."""
    if not HAS_REQUESTS:
        return (0, None)
    try:
        r = _http.post(url, json=data, headers=headers, timeout=timeout)
        return (r.status_code, r.json() if r.text else None)
    except Exception:
        return (0, None)


def api_put(url: str, data: Dict, timeout: int = 10) -> tuple:
    """Generic PUT — returns (status_code, json_data)."""
    if not HAS_REQUESTS:
        return (0, None)
    try:
        r = _http.put(url, json=data, timeout=timeout)
        return (r.status_code, r.json() if r.text else None)
    except Exception:
        return (0, None)


def api_delete(url: str, timeout: int = 10) -> int:
    """Generic DELETE — returns status code."""
    if not HAS_REQUESTS:
        return 0
    try:
        r = _http.delete(url, timeout=timeout)
        return r.status_code
    except Exception:
        return 0


# ========== Display Helpers ==========
def print_table(headers: List[str], rows: List[List[str]]):
    """Print a formatted table."""
    if not rows:
        print("(no data)")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], min(len(str(cell)), 30))
    col_widths = [min(w, 30) for w in col_widths]

    def truncate(s, w):
        s = str(s)
        return s[:w - 1] + "…" if len(s) > w else s

    fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print("-+-".join("-" * w for w in col_widths))
    for row in rows:
        padded = [truncate(row[i] if i < len(row) else "", col_widths[i])
                  for i in range(len(headers))]
        print(fmt.format(*padded))


def parse_kv_args(args: List[str], start: int = 0) -> Dict[str, str]:
    """Parse --key value pairs from arg list."""
    fields = {}
    i = start
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                fields[key] = args[i + 1]
                i += 2
            else:
                fields[key] = "true"
                i += 1
        else:
            i += 1
    return fields
