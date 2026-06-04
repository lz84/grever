#!/usr/bin/env python3
"""
Verifier (鉴) — Unified Verification Skill v1.0

Compile check, API testing, file validation, custom scripts, and LLM code review.

Usage:
  python skill.py compile --path path/to/file.ts
  python skill.py api --url http://localhost:8090/api/v1/goals --expect 200
  python skill.py file --path docs/readme.md
  python skill.py custom --script "assert 1+1==2"
  python skill.py llm --content "def foo(): pass"
"""

import sys
import os
import json
import subprocess
from typing import Optional, Dict

# Shared utils
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
if SKILLS_ROOT not in sys.path:
    sys.path.insert(0, SKILLS_ROOT)

from _utils import api_get, HAS_REQUESTS


# ========== 1. Compile Check ==========
def verify_compile(path: str) -> Dict:
    """Verify code syntax: TypeScript compilation or Python py_compile."""
    if not os.path.exists(path):
        return {"passed": False, "type": "compile", "details": f"File not found: {path}"}

    ext = os.path.splitext(path)[1].lower()

    if ext in (".ts", ".tsx"):
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", path],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.dirname(path) or "."
            )
            if result.returncode == 0:
                return {"passed": True, "type": "compile", "details": "TypeScript compiles OK"}
            else:
                errors = result.stderr.strip()[:500]
                return {"passed": False, "type": "compile", "details": errors or result.stdout[:500]}
        except FileNotFoundError:
            return {"passed": False, "type": "compile", "details": "npx not found"}
        except subprocess.TimeoutExpired:
            return {"passed": False, "type": "compile", "details": "Compilation timed out (>60s)"}

    elif ext == ".py":
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return {"passed": True, "type": "compile", "details": "Python syntax OK"}
            else:
                return {"passed": False, "type": "compile", "details": result.stderr.strip()[:500]}
        except Exception as e:
            return {"passed": False, "type": "compile", "details": str(e)}

    else:
        return {"passed": False, "type": "compile", "details": f"Unsupported file type: {ext}"}


# ========== 2. API Check ==========
def verify_api(url: str, expect_status: int = 200, expect_keys: str = None) -> Dict:
    """Verify HTTP API endpoint returns expected status and keys."""
    if not HAS_REQUESTS:
        return {"passed": False, "type": "api", "details": "requests library not installed"}
    try:
        import requests
        r = requests.get(url, timeout=10)
        if r.status_code != expect_status:
            return {"passed": False, "type": "api",
                    "details": f"Expected {expect_status}, got {r.status_code}"}

        if expect_keys:
            try:
                data = r.json()
                keys = [k.strip() for k in expect_keys.split(",")]
                missing = [k for k in keys if k not in data]
                if missing:
                    return {"passed": False, "type": "api",
                            "details": f"Missing keys: {', '.join(missing)}"}
            except json.JSONDecodeError:
                return {"passed": False, "type": "api", "details": "Response is not valid JSON"}

        return {"passed": True, "type": "api",
                "details": f"{url} → {r.status_code} OK"}
    except Exception as e:
        return {"passed": False, "type": "api", "details": str(e)}


# ========== 3. File Check ==========
def verify_file(path: str, expect_content: str = None) -> Dict:
    """Verify file exists and optionally contains expected content."""
    if not os.path.exists(path):
        return {"passed": False, "type": "file", "details": f"File not found: {path}"}

    if not expect_content:
        size = os.path.getsize(path)
        return {"passed": True, "type": "file",
                "details": f"File exists: {path} ({size} bytes)"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if expect_content in content:
            return {"passed": True, "type": "file",
                    "details": "File contains expected content"}
        else:
            return {"passed": False, "type": "file",
                    "details": "File exists but missing expected content"}
    except Exception as e:
        return {"passed": False, "type": "file", "details": str(e)}


# ========== 4. Custom Script ==========
def verify_custom(script: str, cwd: str = None) -> Dict:
    """Execute a custom Python verification script."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30,
            cwd=cwd or "."
        )
        if result.returncode == 0:
            return {"passed": True, "type": "custom",
                    "details": result.stdout.strip()[:500] or "Custom check passed"}
        else:
            return {"passed": False, "type": "custom",
                    "details": result.stderr.strip()[:500]}
    except subprocess.TimeoutExpired:
        return {"passed": False, "type": "custom", "details": "Script timed out (>30s)"}
    except Exception as e:
        return {"passed": False, "type": "custom", "details": str(e)}


# ========== 5. LLM Review ==========
def verify_llm_review(content: str, prompt: str = None) -> Dict:
    """Use LLM to review code/document content."""
    llm_api = os.environ.get("LLM_API", "")
    llm_model = os.environ.get("LLM_MODEL", "qwen3-30b-a3b-fp8")
    llm_key = os.environ.get("LLM_API_KEY", "123")

    if not llm_api:
        return {"passed": False, "type": "llm-review", "details": "LLM_API not set"}

    if not HAS_REQUESTS:
        return {"passed": False, "type": "llm-review", "details": "requests library not installed"}

    system_prompt = prompt or (
        "You are a code reviewer. Review the following content and determine if it meets quality standards. "
        "Reply with 'PASS: <reason>' or 'FAIL: <reason>'."
    )

    try:
        import requests
        r = requests.post(
            f"{llm_api}/chat/completions",
            headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
            json={"model": llm_model, "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ], "max_tokens": 500, "temperature": 0.3},
            timeout=60
        )
        if r.ok:
            reply = r.json()["choices"][0]["message"]["content"]
            passed = reply.upper().startswith("PASS")
            return {"passed": passed, "type": "llm-review", "details": reply[:500]}
        else:
            return {"passed": False, "type": "llm-review", "details": f"LLM API error: HTTP {r.status_code}"}
    except Exception as e:
        return {"passed": False, "type": "llm-review", "details": str(e)}


# ========== CLI Commands ==========

def cmd_compile(args):
    path = None
    for i, a in enumerate(args):
        if a == "--path" and i + 1 < len(args):
            path = args[i + 1]
    if not path:
        print("Usage: skill.py compile --path <file>")
        return
    result = verify_compile(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_api(args):
    url = None
    expect = 200
    keys = None
    for i, a in enumerate(args):
        if a == "--url" and i + 1 < len(args):
            url = args[i + 1]
        elif a == "--expect" and i + 1 < len(args):
            expect = int(args[i + 1])
        elif a == "--keys" and i + 1 < len(args):
            keys = args[i + 1]
    if not url:
        print("Usage: skill.py api --url <url> [--expect 200] [--keys 'id,name,status']")
        return
    result = verify_api(url, expect, keys)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_file(args):
    path = None
    content = None
    for i, a in enumerate(args):
        if a == "--path" and i + 1 < len(args):
            path = args[i + 1]
        elif a == "--contains" and i + 1 < len(args):
            content = args[i + 1]
    if not path:
        print("Usage: skill.py file --path <file> [--contains 'text']")
        return
    result = verify_file(path, content)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_custom(args):
    script = None
    cwd = None
    for i, a in enumerate(args):
        if a == "--script" and i + 1 < len(args):
            script = args[i + 1]
        elif a == "--cwd" and i + 1 < len(args):
            cwd = args[i + 1]
    if not script:
        print("Usage: skill.py custom --script 'assert 1+1==2' [--cwd /path]")
        return
    result = verify_custom(script, cwd)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_llm(args):
    content = None
    prompt = None
    for i, a in enumerate(args):
        if a == "--content" and i + 1 < len(args):
            content = args[i + 1]
        elif a == "--prompt" and i + 1 < len(args):
            prompt = args[i + 1]
    if not content:
        print("Usage: skill.py llm --content 'code or text to review' [--prompt 'custom prompt']")
        return
    result = verify_llm_review(content, prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_help(args):
    print("""
Verifier (鉴) — Unified Verification Skill

Usage: python skill.py <type> [options]

Types:
  compile  --path <file>                Check code syntax (TS/Python)
  api      --url <url> [--expect 200]   Check API endpoint
  file     --path <file> [--contains t] Check file exists/contents
  custom   --script 'code' [--cwd dir]  Run custom verification script
  llm      --content 'text' [--prompt p] LLM code review

Output: JSON with {passed, type, details}

Environment variables:
  LLM_API       LLM API URL (required for llm type)
  LLM_MODEL     LLM model name (default: qwen3-30b-a3b-fp8)
  LLM_API_KEY   LLM API key
""")


COMMANDS = {
    "compile": cmd_compile, "api": cmd_api, "file": cmd_file,
    "custom": cmd_custom, "llm": cmd_llm, "help": cmd_help,
}


def main():
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    handler = COMMANDS.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        cmd_help([])
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
