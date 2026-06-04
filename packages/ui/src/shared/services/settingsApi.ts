/**
 * Settings API 服务层
 * 
 * 封装所有系统设置相关的 API 调用
 * 统一管理 Settings 页面的数据交互
 * 
 * ⚠️ 所有路径从 api/paths.ts 导入
 */

import { API_BASE_URL } from '@/config'
import { SETTINGS, AGENTS } from '../api/paths'

// ============================================================
// Types
// ============================================================

export interface ConfigValue {
  value: unknown
  type: string
  description?: string
  updated_at?: string
  updated_by?: string
}

export interface SettingsData {
  root_agent?: Record<string, ConfigValue>
  openclaw?: Record<string, ConfigValue>
  system?: Record<string, ConfigValue>
  security?: Record<string, ConfigValue>
}

export interface TestConnectionResult {
  status: 'connected' | 'failed'
  message: string
  gateway_url?: string
  response_time_ms?: number
  details?: Record<string, unknown>
}

export interface ModelInfo {
  id: string
  name?: string
  provider?: string
}

export interface ModelListResult {
  models: ModelInfo[]
  source: string
  warning?: string
}

export interface SessionListResult {
  sessions: unknown[]
  error?: string
}

// ============================================================
// Settings CRUD
// ============================================================

/**
 * 获取所有配置（按 category 分组）
 */
export async function fetchAllSettings(): Promise<SettingsData> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.LIST}`)
  if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`)
  return res.json()
}

export async function fetchCategorySettings(category: string): Promise<Record<string, ConfigValue>> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.GET(category)}`)
  if (!res.ok) throw new Error(`Failed to fetch ${category}: ${res.status}`)
  return res.json()
}

export async function fetchSingleSetting(category: string, key: string): Promise<{ key: string; value: unknown; description?: string }> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.GET_KEY(category, key)}`)
  if (!res.ok) throw new Error(`Failed to fetch ${category}/${key}: ${res.status}`)
  return res.json()
}

export async function updateSetting(category: string, key: string, value: string): Promise<{ status: string; category: string; key: string; value: unknown; updated_at: string }> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.UPDATE_KEY(category, key)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value }),
  })
  if (!res.ok) throw new Error(`Failed to update ${category}/${key}: ${res.status}`)
  return res.json()
}

export async function batchUpdateSettings(category: string, configs: Record<string, unknown>): Promise<{ status: string; updated: string[]; errors: { key: string; error: string }[]; count: number }> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.BATCH_UPDATE(category)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ configs }),
  })
  if (!res.ok) throw new Error(`Failed to batch update ${category}: ${res.status}`)
  return res.json()
}

export async function testOpenClawConnection(): Promise<TestConnectionResult> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.TEST_CONNECTION}`, { method: 'POST' })
  return res.json()
}

export async function fetchAvailableModels(): Promise<ModelListResult> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.LIST_MODELS}`)
  return res.json()
}

export async function fetchOpenClawSessions(): Promise<SessionListResult> {
  const res = await fetch(`${API_BASE_URL}${SETTINGS.LIST_SESSIONS}`)
  return res.json()
}

// ============================================================
// Agent Management
// ============================================================

export interface AgentInfo {
  id: string
  name: string
  model?: string
  capabilities?: string[]
  status?: string
  trigger_mode?: string
  poll_interval?: number
  max_load?: number
}

/**
 * 获取 Agent 列表
 */
export async function fetchAgents(): Promise<AgentInfo[]> {
  const res = await fetch(`${API_BASE_URL}${AGENTS.LIST}`)
  if (!res.ok) throw new Error(`Failed to fetch agents: ${res.status}`)
  const data = await res.json()
  return data.agents ?? data ?? []
}

export async function updateAgent(agentId: string, data: { model_name?: string; capabilities?: string[]; trigger_mode?: string; poll_interval?: number; max_load?: number }): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}${AGENTS.GET(agentId)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.ok
}

export async function registerAgent(data: { agent_id: string; name: string; model_name: string; capabilities: string[]; trigger_mode: string; poll_interval: number; max_load: number }): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}${AGENTS.CREATE}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  return res.ok || res.status === 201
}

export async function deregisterAgent(agentId: string): Promise<boolean> {
  const res = await fetch(`${API_BASE_URL}${AGENTS.REMOVE(agentId)}`, { method: 'DELETE' })
  return res.ok
}
