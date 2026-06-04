/**
 * Nexus API 服务层 - 场景库 API
 * 调用真实后端 API
 * 
 * ⚠️ 所有路径从 api/paths.ts 导入
 */

import { request } from './api'
import { SCENARIOS } from '../api/paths'

// ==================== 类型定义 ====================

export type ConditionType = 'none' | 'auto_eval' | 'human_decision' | 'human_input'

export interface ScenarioTaskTemplate {
  id: string
  scenario_id: string
  phase_name: string
  task_name: string
  task_description: string
  agent_type: string
  required_capabilities: string[]
  dependencies: string[]
  order_in_phase: number
  estimated_hours: number
  priority: string
  condition_type?: ConditionType
  condition_data?: Record<string, any> | null
}

export interface ScenarioStepData {
  name: string
  agent_type: string
  required_capabilities: string[]
  condition_type: ConditionType
  condition_data: Record<string, any> | null
}

export interface ScenarioTaskData {
  name: string
  description: string
  agent_type: string
  required_capabilities: string[]
  dependencies: string[]
  condition_type: ConditionType
  condition_data: Record<string, any> | null
  executor_type?: string
}

export interface ScenarioPhasePayload {
  phase_name: string
  phase_description: string
  tasks: Array<{
    name: string
    description: string
    agent_type: string
    required_capabilities: string[]
    dependencies: string[]
    priority?: string
    estimated_hours?: number
    condition_type?: ConditionType
    condition_data?: Record<string, any> | null
    executor_type?: string
  }>
  depends_on_phases: string[]
}

export interface ScenarioCreateRequest {
  basic: {
    name: string
    category: string
    description?: string
    scenario_desc?: string
    triggers?: string[]
    source?: string
    status?: string
    version?: string
    executor_type?: string
  }
  project_workflow: {
    workflow_name: string
    description: string
    phases: ScenarioPhasePayload[]
  }
  task_templates: ScenarioTaskData[]
}

export interface DeriveFromCognitionsRequest {
  domain: string
  cognition_ids?: number[]
  goal_title?: string
}

export interface Scenario {
  id: string
  name: string
  category: string
  status: 'draft' | 'active' | 'deprecated' | 'archived'
  version: string
  scenario_desc: string
  usage_count: number
  success_rate: number
  avg_duration_ms?: number
  updated_at?: string
  match_score?: number
  level?: string
  description: string | null
  triggers: string[]
  steps: ScenarioStep[]
  task_templates: ScenarioTask[]
  fullset?: Record<string, any>
  // Sprint 85: projects array from scenario_projects
  projects?: ScenarioProject[]
  // Sprint 85c: project count and capability tags preview
  project_count?: number
  goal_capability_tags?: Record<string, string[]>
  // Sprint 89: executor_type for HITL
  executor_type?: string
  // 兼容字段
  title?: string
  priority?: string
  tags?: string[]
}

export interface ScenarioStep {
  id: string
  name: string
  agent_type: string | null
  required_capabilities: string[]
  condition_type: ConditionType
  condition_data: Record<string, any> | null
}

export interface ScenarioProjectTask {
  id: string
  name: string
  description: string | null
  agent_type: string | null
  required_capabilities: string[] | null
  dependencies: string[] | null
  order_in_phase: number
  estimated_hours: number | null
  priority: string
  condition_type: ConditionType
  condition_data: Record<string, any> | null
}

export interface ScenarioProject {
  id: string
  name: string
  description: string | null
  order: number
  agent_type: string | null
  required_capabilities: string[] | null
  condition_type: ConditionType
  condition_data: Record<string, any> | null
  project_type: string
  capability_tags: string[] | Record<string, any>
  next_step: string[] | null
  tasks: ScenarioProjectTask[]
}

export interface ScenarioTask {
  id: string
  name: string
  description: string | null
  agent_type: string | null
  required_capabilities: string[] | null
  dependencies: string[] | null
  condition_type: ConditionType
  condition_data: Record<string, any> | null
  phase_name: string
  order_in_phase: number
  executor_type?: string
}

// ==================== 中文映射函数 ====================

export function executorTypeLabel(executorType?: string): string {
  const map: Record<string, string> = {
    ai: 'AI',
    human: '纯人',
    ai_approval: '审批',
    ai_data: '数据',
    ai_confirm: '确认',
    auto_eval: '自动',
  }
  return executorType ? (map[executorType] || executorType) : '-'
}

// ==================== 场景库 API ====================

export const scenariosApi = {
  list: (params?: {
    source?: string
    category?: string
    status?: string
    q?: string
    skip?: number
    limit?: number
    page?: number
    page_size?: number
  }) => {
    return request<any>(SCENARIOS.LIST, {
      params: params || {},
    }).then(response => {
      if (response.items !== undefined && response.total !== undefined) {
        return response
      }
      if (Array.isArray(response)) {
        return { items: response, total: response.length }
      }
      return { items: [], total: 0 }
    })
  },

  get: (id: string) => {
    return request<Scenario>(SCENARIOS.GET(id))
  },

  create: (data: Partial<Scenario>) => {
    return request<Scenario>(SCENARIOS.CREATE, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  update: (id: string, data: Partial<Scenario>) => {
    return request<Scenario>(SCENARIOS.UPDATE(id), {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  delete: (id: string) => {
    return request(SCENARIOS.REMOVE(id), { method: 'DELETE' })
  },

  updateStatus: (id: string, status: 'draft' | 'active' | 'deprecated') => {
    return request<Scenario>(SCENARIOS.UPDATE_STATUS(id), {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  },

  feedback: (id: string, feedback: { rating: number; comment?: string }) => {
    return request<{ success: boolean }>(SCENARIOS.FEEDBACK(id), {
      method: 'POST',
      body: JSON.stringify(feedback),
    })
  },

  star: (id: string) => {
    try {
      const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}')
      stored[id] = { id, starredAt: new Date().toISOString() }
      localStorage.setItem('nexus_starred_scenarios', JSON.stringify(stored))
      return { success: true }
    } catch {
      return { success: false }
    }
  },

  unstar: (id: string) => {
    try {
      const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}')
      if (stored[id]) {
        delete stored[id]
        localStorage.setItem('nexus_starred_scenarios', JSON.stringify(stored))
      }
      return { success: true }
    } catch {
      return { success: false }
    }
  },

  listStarred: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}')
      const starredIds = Object.keys(stored)
      return {
        total: starredIds.length,
        items: [] as Scenario[],
      }
    } catch {
      return { total: 0, items: [] }
    }
  },

  customCreate: (data: ScenarioCreateRequest) => {
    return request<Scenario>(SCENARIOS.CUSTOM_CREATE, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  fromGoal: (goalId: string) => {
    return request<ScenarioCreateRequest>(SCENARIOS.DERIVE_FROM_EXECUTION(goalId), {
      method: 'POST',
    })
  },

  fromProject: (projectId: string) => {
    return request<ScenarioCreateRequest>(SCENARIOS.DERIVE_FROM_PROJECT_EXECUTION(projectId), {
      method: 'POST',
    })
  },

  deriveFromCognitions: (data: DeriveFromCognitionsRequest) => {
    return request<ScenarioCreateRequest>(SCENARIOS.DERIVE_FROM_COGNITIONS, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  confirmDerive: (data: ScenarioCreateRequest) => {
    return request<Scenario>(SCENARIOS.DERIVE_FROM_COGNITIONS_CONFIRM, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  review: (id: string, data: { review: string; rating?: number }) => {
    return request<Scenario>(SCENARIOS.REVIEW(id), {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  getVersions: (id: string) => {
    return request<any[]>(SCENARIOS.GET_VERSIONS(id))
  },

  instantiate: (id: string, goalData: { goal_title?: string; goal_description?: string; [key: string]: any }) => {
    return request<any>(SCENARIOS.INSTANTIATE_TO_GOAL(id), {
      method: 'POST',
      body: JSON.stringify(goalData),
    })
  },
}
