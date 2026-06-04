#!/usr/bin/env python3
"""
Pulse (息) — Agent Lifecycle Management v1.0

Agent registration, heartbeat, discovery, and status reporting.

Usage:
  python skill.py connect
  python skill.py disconnect
  python skill.py heartbeat
  python skill.py discover [keyword]
  python skill.py status
"""

import sys
import os
import time
import threading
from typing import Optional, List, Dict

# Shared utils — skills/ is our parent dir
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
if SKILLS_ROOT not in sys.path:
    sys.path.insert(0, SKILLS_ROOT)

from _utils import (
    api_post, api_delete, api_get,
    NEXUS_SERVER, AGENT_ID, AGENT_NAME, AGENT_CAPABILITIES,
    TRIGGER_MODE, MAX_LOAD, POLL_INTERVAL,
    print_table,
)


class NexusConnection:
    """Manages agent registration, heartbeat, and discovery."""

    def __init__(self, base_url: str = None, agent_id: str = None,
                 agent_name: str = None, capabilities: List[str] = None):
        self.base_url = (base_url or NEXUS_SERVER).rstrip("/")
        self.agent_id = agent_id or AGENT_ID
        self.agent_name = agent_name or AGENT_NAME
        self.capabilities = capabilities or AGENT_CAPABILITIES
        self.token: Optional[str] = None
        self._registered = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False

    def connect(self) -> bool:
        """Register to Nexus and start heartbeat loop."""
        if not self.agent_id:
            print("Error: NEXUS_AGENT_ID not set.")
            return False
        if not self.agent_name:
            print("Error: NEXUS_AGENT_NAME not set.")
            return False
        if not self.capabilities:
            print("Error: NEXUS_CAPABILITIES not set.")
            return False

        url = f"{self.base_url}/api/v1/agents"
        payload = {
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "capabilities": self.capabilities,
            "max_load": MAX_LOAD,
            "trigger_mode": TRIGGER_MODE,
        }
        status, data = api_post(url, payload)

        if status in (200, 201):
            self.token = (data or {}).get("token", "")
            self._registered = True
            print(f"✅ Connected to Nexus as {self.agent_name} ({self.agent_id})")
            print(f"   Server: {self.base_url}")
            print(f"   Capabilities: {', '.join(self.capabilities)}")
            self._start_heartbeat()
            return True
        else:
            detail = (data or {}).get("detail", f"HTTP {status}")
            print(f"❌ Registration failed: {detail}")
            return False

    def disconnect(self) -> bool:
        """Unregister from Nexus."""
        self._stop_heartbeat()
        if not self.agent_id:
            print("Not connected.")
            return False
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}"
        status = api_delete(url)
        self._registered = False
        self.token = None
        print(f"✅ Disconnected from Nexus ({self.agent_id})")
        return status in (200, 204)

    def heartbeat(self) -> bool:
        """Send one heartbeat."""
        if not self.agent_id or not self._registered:
            print("Not connected. Run 'connect' first.")
            return False
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/heartbeat"
        payload = {"state": "idle", "load": 10, "current_tasks": 0}
        status, data = api_post(url, payload)
        if status == 200:
            tasks = len((data or {}).get("assigned_tasks", []))
            print(f"✅ Heartbeat OK — assigned tasks: {tasks}")
            return True
        else:
            print(f"❌ Heartbeat failed: HTTP {status}")
            return False

    def discover(self, capability: str = None) -> List[Dict]:
        """Discover online agents."""
        url = f"{self.base_url}/api/v1/agents"
        data = api_get(url)
        if not data or not isinstance(data, list):
            return []
        agents = [a for a in data if a.get("status") in ("online", "idle", "busy")]
        if capability:
            cap_lower = capability.lower()
            agents = [a for a in agents
                      if cap_lower in [c.lower() for c in (a.get("capabilities") or [])]]
        return agents

    def status(self) -> Dict:
        return {
            "connected": self._registered,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "capabilities": self.capabilities,
            "server": self.base_url,
            "heartbeat_active": (self._heartbeat_thread is not None
                                 and self._heartbeat_thread.is_alive()),
        }

    def _heartbeat_loop(self):
        while self._running:
            time.sleep(POLL_INTERVAL)
            if self._running:
                try:
                    self._do_heartbeat()
                except Exception:
                    pass

    def _do_heartbeat(self):
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/heartbeat"
        api_post(url, {"state": "idle", "load": 10, "current_tasks": 0}, timeout=5)

    def _start_heartbeat(self):
        self._running = True
        t = threading.Thread(target=self._heartbeat_loop, daemon=True)
        t.start()
        self._heartbeat_thread = t
        print(f"   Heartbeat started (every {POLL_INTERVAL}s)")

    def _stop_heartbeat(self):
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
            self._heartbeat_thread = None


# ========== CLI Commands ==========

def cmd_connect(args):
    conn = NexusConnection()
    if not conn.connect():
        sys.exit(1)
    print("Hint: heartbeat runs in background. Press Ctrl+C to disconnect.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        conn.disconnect()


def cmd_disconnect(args):
    conn = NexusConnection()
    conn.disconnect()


def cmd_heartbeat(args):
    conn = NexusConnection()
    if not conn.heartbeat():
        sys.exit(1)


def cmd_discover(args):
    conn = NexusConnection()
    capability = args[0] if args else None
    agents = conn.discover(capability)
    if not agents:
        print("No online agents" + (f" (capability: {capability})" if capability else ""))
        return
    rows = []
    for a in agents:
        caps = ", ".join(a.get("capabilities", [])[:3])
        rows.append([
            a.get("name", "unnamed"),
            a["id"][:12] + "…",
            a.get("status", "unknown"),
            caps,
            f"{a.get('load', 0)}%",
            a.get("model_name", "-"),
        ])
    print_table(["Name", "ID", "Status", "Capabilities", "Load", "Model"], rows)


def cmd_status(args):
    conn = NexusConnection()
    s = conn.status()
    for k, v in s.items():
        print(f"  {k}: {v}")


def cmd_help(args):
    print("""
Pulse (息) — Agent Lifecycle Management

Usage: python skill.py <command> [options]

Commands:
  connect                Register to Nexus, start heartbeat
  disconnect             Unregister from Nexus
  heartbeat              Send one manual heartbeat
  discover [keyword]     List online agents
  status                 Show connection state

Environment variables:
  NEXUS_SERVER_URL       Nexus API base (default: http://localhost:8090)
  NEXUS_AGENT_ID         Your agent ID (required for connect)
  NEXUS_AGENT_NAME       Display name (required for connect)
  NEXUS_CAPABILITIES     Capability tags, comma-separated (required for connect)
  NEXUS_TRIGGER_MODE     Task delivery: sse or polling (default: sse)
  NEXUS_POLL_INTERVAL    Heartbeat interval in seconds (default: 30)
  NEXUS_MAX_LOAD         Max concurrent tasks (default: 5)
""")


COMMANDS = {
    "connect": cmd_connect, "disconnect": cmd_disconnect,
    "heartbeat": cmd_heartbeat, "discover": cmd_discover,
    "status": cmd_status, "help": cmd_help,
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
