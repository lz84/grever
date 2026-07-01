// Agent name lookup — single source: DB agents table
// App startup must call setAgentCache() to populate.
// If an agent ID is not found in cache, the raw ID is returned (exposes data issues).

let _agentCache: Record<string, string> = {}

/**
 * Populate agent name cache from DB (call once at app startup).
 * @param agents - Array of agents from GET /api/v1/agents
 */
export function setAgentCache(agents: Array<{ id: string; name: string }>): void {
  _agentCache = {}
  for (const a of agents) {
    if (a.id && a.name) {
      _agentCache[a.id] = a.name
    }
  }
}

/**
 * Get agent display name.
 * Cache miss → raw ID returned (exposes missing agent in DB).
 */
export function getAgentName(agentId: string | null | undefined): string {
  if (!agentId) return '未分配'
  return _agentCache[agentId] ?? agentId
}
