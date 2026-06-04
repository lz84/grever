/**
 * Sprint 68-73: 方案管理 API 服务层
 * 所有方案相关的后端 API 调用
 */

const API_BASE = '/api/v1'

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>
}

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options

  let url = `${API_BASE}${path}`
  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    const qs = searchParams.toString()
    if (qs) url += `?${qs}`
  }

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
    ...fetchOptions,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `API 请求失败: ${response.status}`)
  }

  if (response.status === 204) return undefined as unknown as T

  return response.json()
}

// ==================== 类型定义 ====================

export interface SolutionListResponse {
  solutions: Solution[]
  total: number
}

export interface Solution {
  id: string
  goal_id: string
  name: string
  round: number
  status: 'compliant' | 'non_compliant' | 'optimal' | 'rejected' | 'pending'
  score: number
  parameters: Record<string, any>
  constraints: string[]
  engineering_tasks: string[]
  project_ids?: string[]  // 关联工程 ID 列表
  task_ids?: string[]     // 关联任务 ID 列表
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
  dimensions?: Record<string, any>
}

export interface CompareResult {
  solutions: Solution[]
  dimensions: string[]
  values: Record<string, Record<string, number | string>>
}

export interface MultiCompareResult {
  solutions: { id: string; name: string }[]
  dimensions: { key: string; label: string; unit?: string; lower_is_better?: boolean }[]
  values: Record<string, Record<string, number>>
}

export interface TrendPoint {
  round: number
  duration: number
  cost: number
  safety: number
  risk: number
}

export interface TrendData {
  goal_id: string
  points: TrendPoint[]
}

export interface IterationStatus {
  goal_id: string
  mode: string
  run_status: 'idle' | 'running' | 'paused' | 'converged'
  current_round: number
  latest_score: number
  latest_solution_id: string | null
  total_solutions: number
  started_at: string
  updated_at: string
}

export interface ConstraintHistory {
  round: number
  constraints: string[]
  changed: boolean
  timestamp: string
}

export interface GoalMode {
  mode: 'normal' | 'exploration' | 'optimization'
  optimization_target?: string
  convergence_threshold?: number
  max_rounds?: number
}

// ==================== Solutions API ====================

export const solutionsApi = {
  /** 查询方案列表 */
  list: (goalId: string, round?: number) =>
    request<SolutionListResponse>('/solutions', { params: { goal_id: goalId, ...(round ? { round } : {}) } }),

  /** 方案详情 */
  get: (id: string) =>
    request<Solution>(`/solutions/${id}`),

  /** 创建方案 */
  create: (data: { goal_id: string; name: string; round?: number; parameters?: Record<string, any>; constraints?: string[] }) =>
    request<Solution>('/solutions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 更新方案 */
  update: (id: string, data: Partial<Solution>) =>
    request<Solution>(`/solutions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** 删除方案 */
  remove: (id: string) =>
    request<void>(`/solutions/${id}`, { method: 'DELETE' }),

  /** 获取比较结果（两两对比） */
  compare: (goalId: string) =>
    request<CompareResult>('/solutions/compare', { params: { goal_id: goalId } }),

  /** 多维度对比 */
  multiCompare: (goalId: string) =>
    request<MultiCompareResult>('/solutions/compare/multi', { params: { goal_id: goalId } }),

  /** 趋势数据 */
  trend: (goalId: string) =>
    request<TrendData>('/solutions/trend', { params: { goal_id: goalId } }),

  /** 启动迭代 */
  startIteration: (goalId: string) =>
    request<IterationStatus>(`/goals/${goalId}/start-iteration`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  /** 迭代状态 */
  iterationStatus: (goalId: string) =>
    request<IterationStatus>(`/goals/${goalId}/iteration-status`, { params: {} }),

  /** 触发下一轮迭代 */
  iterate: (goalId: string) =>
    request<IterationStatus>(`/goals/${goalId}/iterate`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  /** 暂停迭代 */
  pauseIteration: (goalId: string) =>
    request<IterationStatus>(`/goals/${goalId}/pause-iteration`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  /** 宣布收敛 */
  declareConverged: (goalId: string) =>
    request<IterationStatus>(`/goals/${goalId}/converge-iteration`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  /** 约束历史 */
  constraints: (goalId: string) =>
    request<ConstraintHistory[]>(`/goals/${goalId}/constraints`, { params: {} }),

  /** 设置探索模式 */
  setGoalMode: (goalId: string, data: GoalMode) =>
    request<GoalMode>(`/goals/${goalId}/mode`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}

// Types are already exported via interface declarations above
