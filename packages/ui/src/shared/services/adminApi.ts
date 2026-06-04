/**
 * Sprint 61.1: 系统管理面板 API 服务层
 * 
 * ⚠️ 所有路径从 api/paths.ts 导入
 */

import { request } from '../utils/api'
import { ADMIN } from '../api/paths'

export interface AgentAdminInfo {
  id: string
  name: string
  status: string
  capabilities: string[]
  address: string | null
  last_heartbeat: string | null
  registered_at: string | null
  model_name: string
  task_count: number
}

export interface TaskAdminInfo {
  id: string
  title: string
  status: string
  assigned_agent: string | null
  priority: number | string | null
  updated_at: string | null
  created_at: string | null
  category: string | null
}

export interface ReregisterResponse {
  success: boolean
  agent_id: string
  message: string
}

export interface SetStatusResponse {
  success: boolean
  agent_id: string
  old_status: string
  new_status: string
  message: string
}

export interface ResetTaskResponse {
  success: boolean
  task_id: string
  old_status: string
  message: string
}

export interface CleanupResponse {
  success: boolean
  cleaned_count: number
  details: string[]
}

export const adminApi = {
  listAgents: (): Promise<AgentAdminInfo[]> => request(ADMIN.LIST_AGENTS),
  reregisterAgent: (agentId: string): Promise<ReregisterResponse> =>
    request(ADMIN.REREGISTER_AGENT(agentId), { method: 'POST' }),
  setAgentStatus: (agentId: string, status: string): Promise<SetStatusResponse> =>
    request(ADMIN.SET_AGENT_STATUS(agentId), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) }),
  restartAgent: (agentId: string): Promise<ReregisterResponse> =>
    request(ADMIN.RESTART_AGENT(agentId), { method: 'POST' }),
  forceOfflineAgent: (agentId: string): Promise<ReregisterResponse> =>
    request(ADMIN.FORCE_OFFLINE(agentId), { method: 'POST' }),
  listTasks: (params?: { status?: string; agent_id?: string; limit?: number; offset?: number }): Promise<TaskAdminInfo[]> =>
    request(ADMIN.LIST_TASKS, { params: params as Record<string, string | number | boolean | undefined> }),
  resetTask: (taskId: string): Promise<ResetTaskResponse> =>
    request(ADMIN.RESET_TASK(taskId), { method: 'POST' }),
  cleanupZombieTasks: (): Promise<CleanupResponse> =>
    request(ADMIN.CLEANUP_ZOMBIE_TASKS, { method: 'POST' }),
}
