/**
 * Grever API 服务层
 * 统一封装所有后端 API 调用
 * 
 * ⚠️ 规则：所有 API 路径必须从 api/paths.ts 导入，禁止硬编码路径
 */

import {
  GOALS, PROJECTS, TASKS, SCENARIOS, WORKFLOWS,
  SCHEDULER, TIMEOUT, TRACES,
  AGENTS, AGENT_SCHEMES, AGENT_MATCHING, AGENT_PLATFORMS, CAPABILITIES, INDUSTRY_TAGS, INDUSTRY_PACKS,
  HUMAN_INPUT, HUMAN_REVIEW, DISPUTES, SOLUTIONS,
  GRASP, CONTEXT, KNOWLEDGE_INJECTOR, KNOWLEDGE,
  MCP_SERVERS, SKILLS, PACK_SKILLS, ATTACHMENTS, ARTIFACTS, REPORTS,
  ADMIN, SETTINGS, SECURITY, DASHBOARD, SEARCH, API_DOCS, EVENTS,
  EVALUATION_DECOMPOSE,
} from '../api/paths'

// ==================== Request 基础函数 ====================

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>
}

export async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options

  let url = path
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

// ==================== 类型定义（保留） ====================

export interface Goal {
  id: string; title: string | null; description: string | null; priority: string | null
  due_date: string | null; status: string | null; created_at: string | null; updated_at: string | null
  project_id: string | null; parent_id: number | null; workspace_type: string | null
  workspace_path: string | null; workspace_status: string | null; workspace_error: string | null
  last_clone_at: string | null; last_pull_at: string | null; last_push_at: string | null
  verifier_agent_id: string | null; main_agent_id?: string | null; mode?: string; optimization_target?: string
  convergence_threshold?: number; max_rounds?: number; capability_tags?: Record<string, string[]>
}

export interface Project {
  id: string; name: string; description: string | null; goal_id: string | null
  status: string; priority?: string; assignee?: string | null; due_date?: string | null
  created_at: string; updated_at: string; verifier_agent_id: string | null
  depends_on?: string[]; next_step?: string[]; workflow_id?: string | null
  phase_order?: number | null; mode?: string; capability_tags?: Record<string, string[]>
}

export interface Task {
  id: string; title: string | null; description: string | null; status: string | null
  priority: number | string | null; capability_tags?: Record<string, string[]>
  due_date: string | null; created_at: string | null; updated_at: string | null
  goal_id: string | null; parent_id: number | null; dependency_ids: number[]
  depends_on?: string[]; next_step?: string[]; project_id: string | null
  assigned_agent: string | null; started_at: string | null; completed_at: string | null
  retry_count: number; result_summary: string | null; error_message: string | null
  max_retries?: number; workflow_step_id?: string; doc_refs?: string[]; workspace_path?: string
  verifier_agent_id: string | null; acceptance_criteria?: string; delivery_criteria?: string
  needs_verification?: boolean
}

export interface Agent {
  id: string; name: string; capability_tags: Record<string, string[]>; status: string
  address: string | null; metadata: any; load: number; current_tasks: number
  max_concurrent_tasks?: number; consecutive_offline_count?: number; health_status?: string
  trigger_mode: string; model_name: string; registered_at: string; last_heartbeat: string
  platform_type?: string; platform_config?: Record<string, any>
  agent_code?: string  // OpenClaw agent code (replaces hardcoded UUID mapping)
}

export interface Dispute {
  id: string; dispute_type: string | null; description: string; involved_agents: string[]
  related_task_id: string | null; status: string; resolution: string | null
  resolved_by: string | null; created_at: string; updated_at: string; resolved_at: string | null
}

export interface Trace {
  task_id: string; workflow_id: string; task_title: string; started_at?: string
  completed_at?: string; final_state?: string; success?: boolean | number; result?: any
  error_message?: string; error_type?: string; cognitions_used?: number; context_size_bytes?: number
  total_duration_ms?: number; agent_id?: string; steps?: TraceStep[]; error_stack?: string
  cpu_time_ms?: number; memory_peak_mb?: number; io_read_bytes?: number; io_write_bytes?: number
  network_bytes?: number; task_status?: string; retry_count?: number; result_summary?: string
}

export interface TraceStep {
  timestamp?: string; action?: string; type?: string; duration_ms?: number; agent_id?: string
}

export interface Workflow {
  id: string; goal_id: string; status: string; name: string; description: string
  dag: { nodes: string[]; edges: string[][] }; workflow_metadata: any
  created_by: string | null; created_at: string; updated_at: string
  started_at: string | null; completed_at: string | null; steps?: WorkflowStep[]
}

export interface WorkflowStep {
  id: string; workflow_id: string; name: string; description?: string; status: string
  dependencies?: string[]; order?: number; agent_id?: string; retry_count?: number; max_retries?: number
}

// MAK-236: LLM 分解出的工程
export interface DecomposedProject {
  id?: string; name: string; description?: string
  priority?: number; category?: string; dependencies?: string[]
}

export interface SubmitDecomposeResult {
  projects: Project[]; goal_id: string
}

// Sprint 6: Verification Report
export interface VerificationReport {
  id: string
  goal_id: string
  report_type: string
  status: string
  round?: number
  verdict?: string
  summary?: string
  findings: any[]
  gaps: any[]
  recommendations: any[]
  remedial_tasks: any[]
  created_at: string
  updated_at: string
}

// ==================== Knowledge Base (Sprint 75 Phase 2) ====================

export interface KnowledgeEntry {
  id: string
  pack_id: string
  name: string
  category: string
  content: string | null
  file_path: string | null
  version: string
  tags: string[]
  created_at: number
}

export interface KnowledgeCreate {
  id?: string
  pack_id: string
  name: string
  category?: string
  content?: string
  file_path?: string
  version?: string
  tags?: string[]
}

export interface KnowledgeUpdate {
  name?: string
  category?: string
  content?: string
  file_path?: string
  version?: string
  tags?: string[]
}

export interface AgentScheme {
  id: string
  pack_id: string
  name: string
  description: string | null
  roles: AgentSchemeRole[]
  created_at: number
}

export interface AgentSchemeRole {
  id: string
  scheme_id: string
  role_name: string
  required_tags: string[]
  priority: number
}

export interface AgentSchemeCreate {
  id?: string
  pack_id: string
  name: string
  description?: string
  roles?: AgentSchemeRole[]
}

export interface AgentSchemeUpdate {
  name?: string
  description?: string
  roles?: AgentSchemeRole[]
}

// ==================== Goals API ====================

export const goalsApi = {
  list: async (params?: { status?: string; project_id?: number; priority?: string }) => {
    const resp = await request<{ goals: Goal[]; total: number; skip: number; limit: number }>(GOALS.LIST, { params: params || {} })
    return resp.goals || []
  },
  get: (id: number | string) => request<Goal>(GOALS.GET(id)),
  create: (data: { title: string; description?: string; parent_id?: number | string; priority?: string; due_date?: string; workspace_type?: string; workspace_path?: string; verifier_agent_id?: string; main_agent_id?: string }) =>
    request<Goal>(GOALS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: number | string, status: string) =>
    request(GOALS.UPDATE_STATUS(id), { method: 'PATCH', body: JSON.stringify({ status }) }),
  update: (id: number | string, data: { verifier_agent_id?: string | null }) =>
    request<Goal>(GOALS.UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: number | string) => request<void>(GOALS.REMOVE(id), { method: 'DELETE' }),
  decompose: (id: number | string, agentId?: string) =>
    request<{ goal_id: number | string; tasks: Task[] }>(GOALS.DECOMPOSE(id), {
      method: 'POST', body: JSON.stringify({ agent_id: agentId }),
    }),
  autoDecompose: (id: number | string) =>
    request<{ goal_id: number | string; projects: DecomposedProject[] }>(GOALS.AUTO_DECOMPOSE_PREVIEW(id), {
      method: 'POST',
    }),
  decomposePreview: (id: number | string, agentId?: string) =>
    request<{ goal_id: number | string; tasks: Task[] }>(GOALS.DECOMPOSE_PREVIEW(id), {
      method: 'POST', body: JSON.stringify({ agent_id: agentId }),
    }),
  autoAssign: (id: number | string) =>
    request<{ ok: boolean; goal_id: string; assigned: number; total: number }>(GOALS.AUTO_ASSIGN(id), {
      method: 'POST',
    }),
  autoDecomposePreview: (id: number | string) =>
    request<{ goal_id: number | string; projects: DecomposedProject[] }>(GOALS.AUTO_DECOMPOSE_PREVIEW(id), {
      method: 'POST',
    }),
  getIterations: (goalId: number | string) => request<any>(GOALS.GET_ITERATIONS(goalId)),
  iterationAnalysis: (goalId: number | string, iterationId: number | string, data?: { human_response?: string; adjustments?: object }) =>
    request<any>(GOALS.ITERATION_ANALYSIS(goalId, iterationId), { method: 'POST', body: JSON.stringify(data || {}) }),
  iterationConsensus: (goalId: number | string, iterationId: number | string, data?: Record<string, any>) =>
    request<any>(GOALS.ITERATION_CONSENSUS(goalId, iterationId), { method: 'POST', body: JSON.stringify(data || {}) }),
  iterationDiscuss: (goalId: number | string, iterationId: number | string, data?: { message?: string; author?: string }) =>
    request<any>(GOALS.ITERATION_DISCUSS(goalId, iterationId), data ? { method: 'POST', body: JSON.stringify(data) } : {}),
  setVerifier: (goalId: number | string, agentId: string) =>
    request<any>(GOALS.SET_VERIFIER(goalId), { method: 'POST', body: JSON.stringify({ verifier_agent_id: agentId }) }),
  setConstraints: (goalId: number | string, constraints: Record<string, any>) =>
    request<any>(GOALS.SET_CONSTRAINTS(goalId), { method: 'POST', body: JSON.stringify(constraints) }),
  setMode: (goalId: number | string, mode: string) =>
    request<any>(GOALS.SET_MODE(goalId), { method: 'POST', body: JSON.stringify({ mode }) }),
  startIteration: (goalId: number | string) =>
    request<any>(GOALS.START_ITERATION(goalId), { method: 'POST' }),
  pauseIteration: (goalId: number | string) =>
    request<any>(GOALS.PAUSE_ITERATION(goalId), { method: 'POST' }),
  convergeIteration: (goalId: number | string) =>
    request<any>(GOALS.CONVERGE_ITERATION(goalId), { method: 'POST' }),
  iterate: (goalId: number | string) =>
    request<any>(GOALS.ITERATE(goalId), { method: 'POST' }),
  getIterationStatus: (goalId: number | string) =>
    request<any>(GOALS.GET_ITERATION_STATUS(goalId), { method: 'POST' }),
  activate: (id: number | string) =>
    request<any>(GOALS.ACTIVATE(id), { method: 'POST' }),
  pause: (id: number | string) =>
    request<any>(GOALS.PAUSE(id), { method: 'POST' }),
  resume: (id: number | string) =>
    request<any>(GOALS.RESUME(id), { method: 'POST' }),
  getTree: (id: number | string) =>
    request<any>(GOALS.GET_TREE(id)),
  // Sprint 6: Verification reports
  getVerificationReports: (id: number | string) =>
    request<VerificationReport[]>(GOALS.GET_VERIFICATION_REPORTS(id)),
  createRemedialTask: (id: number | string, data: { title: string; description?: string; project_id?: string; priority?: string }) =>
    request<Task>(GOALS.CREATE_REMEDIAL_TASK(id), { method: 'POST', body: JSON.stringify(data) }),
  // HITL pending questions
  getPendingQuestions: (id: number | string) =>
    request<Tier0Question[]>(GOALS.GET_PENDING_QUESTIONS(id)),
  submitAnswers: (id: number | string, data: Record<string, string>) =>
    request<any>(GOALS.SUBMIT_ANSWERS(id), { method: 'POST', body: JSON.stringify(data) }),
}

// ==================== Decomposition API (Sprint 1) ====================

export const decompositionApi = {
  getPreview: (goalId: number | string) =>
    request<any>(GOALS.DECOMPOSE_PREVIEW(goalId)),
  evaluateDecompose: (goalId: number | string) =>
    request<any>(GOALS.EVALUATE_DECOMPOSE(goalId), { method: 'POST' }),
  pendingQuestions: (goalId: number | string) =>
    request<Tier0Question[]>(GOALS.GET_PENDING_QUESTIONS(goalId)),
  autoDecomposePreview: (goalId: number | string) =>
    request<any>(GOALS.AUTO_DECOMPOSE_PREVIEW(goalId), { method: 'POST' }),
  submitDecompose: (goalId: number | string, data: any) =>
    request<any>(GOALS.SUBMIT_DECOMPOSE(goalId), { method: 'POST', body: JSON.stringify(data) }),
}

// ==================== Evaluation Decompose API (Sprint 4) ====================

export interface Tier0Question {
  id: string
  question_id: string
  question: string
  question_text: string
  question_type: string
  category: string
  context?: string
  options?: string[]
  answer?: string
  priority?: number
  reason?: string
  impact?: string
}

export const evaluationDecomposeApi = {
  start: (goalId: string, data?: Record<string, any>) =>
    request<any>(EVALUATION_DECOMPOSE.START, { method: 'POST', body: JSON.stringify({ goal_id: goalId, ...data }) }),
  e2: (sessionId: string, data: Record<string, any>) =>
    request<any>(EVALUATION_DECOMPOSE.E2(sessionId), { method: 'POST', body: JSON.stringify(data) }),
  e3: (sessionId: string, data: Record<string, any>) =>
    request<any>(EVALUATION_DECOMPOSE.E3(sessionId), { method: 'POST', body: JSON.stringify(data) }),
  e4: (sessionId: string, data: Record<string, any>) =>
    request<any>(EVALUATION_DECOMPOSE.E4(sessionId), { method: 'POST', body: JSON.stringify(data) }),
  getStatus: (sessionId: string) =>
    request<any>(EVALUATION_DECOMPOSE.STATUS(sessionId)),
  getQuestions: (sessionId: string) =>
    request<Tier0Question[]>(EVALUATION_DECOMPOSE.QUESTIONS(sessionId)),
}

// ==================== Goal HITL API ====================

export const goalHitlApi = {
  getPendingQuestions: (goalId: string) =>
    request<Tier0Question[]>(GOALS.GET_PENDING_QUESTIONS(goalId)),
  submitAnswers: (goalId: string, data: Record<string, string>) =>
    request<any>(GOALS.SUBMIT_ANSWERS(goalId), { method: 'POST', body: JSON.stringify(data) }),
  evaluateDecompose: (goalId: string) =>
    request<any>(GOALS.EVALUATE_DECOMPOSE(goalId), { method: 'POST' }),
}

// ==================== Projects API ====================

export const projectsApi = {
  list: async (params?: { status?: string; goal_id?: number | string }) => {
    const resp = await request<{projects: Project[]; total: number}>(PROJECTS.LIST, { params: params || {} })
    return resp.projects || []
  },
  get: (id: number | string) => request<Project>(PROJECTS.GET(id)),
  create: (data: { name: string; description?: string; goal_id?: number | string; verifier_agent_id?: string; priority?: string; depends_on?: string[] }) =>
    request<Project>(PROJECTS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  getProgress: (id: number | string) =>
    request<{ project_id: number | string; progress: any }>(`/projects/${id}/progress`),
  remove: (id: number | string) => request<void>(PROJECTS.REMOVE(id), { method: 'DELETE' }),
  update: (id: number | string, data: { name?: string; verifier_agent_id?: string | null; goal_id?: string | null }) =>
    request<Project>(PROJECTS.UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  pause: (id: number | string) => request<any>(PROJECTS.PAUSE(id), { method: 'POST' }),
  resume: (id: number | string) => request<any>(PROJECTS.RESUME(id), { method: 'POST' }),
  getDiagram: (id: number | string) => request<any>(PROJECTS.GET_DIAGRAM(id)),
  getTaskTree: (id: number | string) => request<any>(PROJECTS.GET_TASK_TREE(id)),
  setVerifier: (id: number | string, agentId: string) =>
    request<any>(PROJECTS.SET_VERIFIER(id), { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
  updateDependsOn: (id: string, dependsOn: string[]) =>
    request<Project>(PROJECTS.UPDATE(id), { method: 'PATCH', body: JSON.stringify({ depends_on: dependsOn }) }),
  autoAssign: (id: number | string) =>
    request<{ ok: boolean; project_id: string; assigned: number; total: number }>(PROJECTS.AUTO_ASSIGN(id), { method: 'POST' }),
  updateStatus: (id: number | string, status: string) =>
    request<any>(PROJECTS.UPDATE_STATUS(id), { method: 'PATCH', body: JSON.stringify({ status }) }),
  countByGoal: (goalId?: string) => {
    const params = goalId ? `?goal_id=${goalId}` : ''
    return request<Record<string, number> | { goal_id: string; count: number }>(`/api/v1/projects/count${params}`)
  },
}

// ==================== Tasks API ====================

export const tasksApi = {
  list: async (params?: { status?: string; project_id?: number | string; assigned_agent?: string; goal_id?: number | string }) => {
    const resp = await request<{tasks: Task[]; total: number}>(TASKS.LIST, { params: params || {} })
    return resp.tasks || []
  },
  get: (id: string) => request<Task>(TASKS.GET(id)),
  create: (data: { title: string; description?: string; project_id?: string; goal_id?: string; assigned_agent?: string; priority?: number | string; category?: string; estimated_hours?: number; doc_refs?: string | string[]; workspace_path?: string; depends_on?: string[]; acceptance_criteria?: string; capability_tags?: Record<string, any> }) =>
    request<Task>(TASKS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: { title?: string; description?: string; status?: string; priority?: number | string; assigned_agent?: string; doc_refs?: string[] | null; workspace_path?: string | null; verifier_agent_id?: string | null; depends_on?: string[] }) =>
    request<Task>(TASKS.UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: string) =>
    request<Task>(TASKS.UPDATE_STATUS(id), { method: 'PATCH', body: JSON.stringify({ status }) }),
  assign: (id: string, agentId: string) =>
    request<Task>(TASKS.ASSIGN(id), { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
  getSubtasks: (id: string) => request<{ task_id: string; subtasks: Task[] }>(TASKS.GET_SUBTASKS(id)),
  getParent: (id: string) => request<{ task_id: string; parent: Task | null }>(TASKS.GET_PARENT(id)),
  submitDecomposed: (goalId: number | string, projects: DecomposedProject[]) =>
    request<SubmitDecomposeResult>(GOALS.SUBMIT_DECOMPOSE(goalId), {
      method: 'POST',
      body: JSON.stringify({ projects: projects.map(p => ({ name: p.name, description: p.description || '', priority: p.priority ?? 3 })) }),
    }),
  completeTask: (taskId: string, data: { status: 'done' | 'failed'; result?: string; artifacts?: string[]; duration_ms?: number }) =>
    request<{ success: boolean; task_id: string }>(TASKS.COMPLETE(taskId), { method: 'POST', body: JSON.stringify(data) }),
  failTask: (taskId: string, data: { error_type: string; error_message: string; retry_count: number; max_retries: number }) =>
    request<{ success: boolean; task_id: string; should_retry: boolean }>(TASKS.FAIL(taskId), { method: 'POST', body: JSON.stringify(data) }),
  retryTask: (taskId: string, data?: { reason?: string }) =>
    request<{ success: boolean; task_id: string; status: string }>(TASKS.RETRY(taskId), { method: 'POST', body: JSON.stringify(data || {}) }),
  deleteTask: (taskId: string) => request<void>(TASKS.REMOVE(taskId), { method: 'DELETE' }),
  pauseTask: (taskId: string) => request<{ success: boolean; task_id: string }>(TASKS.PAUSE(taskId), { method: 'POST' }),
  resumeTask: (taskId: string) => request<{ success: boolean; task_id: string }>(TASKS.RESUME(taskId), { method: 'POST' }),
  countByGoal: (goalId?: string, projectId?: string) => {
    const params = new URLSearchParams()
    if (goalId) params.set('goal_id', goalId)
    if (projectId) params.set('project_id', projectId)
    const qs = params.toString()
    return request<Record<string, { completed: number; total: number }> | { goal_id: string; completed: number; total: number }>(`/api/v1/tasks/count${qs ? '?' + qs : ''}`)
  },
  restartTask: (taskId: string) => request<{ success: boolean; task_id: string }>(TASKS.RESTART(taskId), { method: 'POST' }),
  blockTask: (taskId: string, reason?: string) => request<{ success: boolean; task_id: string }>(TASKS.BLOCK(taskId), { method: 'PATCH', body: JSON.stringify({ reason }) }),
  unblockTask: (taskId: string) => request<{ success: boolean; task_id: string }>(TASKS.UNBLOCK(taskId), { method: 'PATCH' }),
  // Comments
  getComments: (taskId: string) => request<any[]>(TASKS.GET_COMMENTS(taskId)),
  addComment: (taskId: string, content: string, author?: string) =>
    request<any>(TASKS.ADD_COMMENT(taskId), { method: 'POST', body: JSON.stringify({ content, author }) }),
  deleteComment: (taskId: string, commentId: string) => request<void>(TASKS.DELETE_COMMENT(taskId, commentId), { method: 'DELETE' }),
  // Attachments (use unified attachmentsApi)
  getAttachments: (taskId: string) => attachmentsApi.list('task', taskId).then(data => {
    if (Array.isArray(data)) return data
    if (data && typeof data === 'object' && 'attachments' in data) return (data as any).attachments
    return []
  }),
  uploadAttachment: (taskId: string, file: File) => attachmentsApi.upload(file, 'task', taskId),
  downloadAttachment: (taskId: string, attachmentId: string) => attachmentsApi.download(attachmentId),
  deleteAttachment: (taskId: string, attachmentId: string) => attachmentsApi.delete(attachmentId),
  // Labels
  getLabels: (taskId: string) => request<string[]>(TASKS.GET_LABELS(taskId)),
  addLabel: (taskId: string, label: string) => request<{ success: boolean }>(TASKS.ADD_LABEL(taskId), { method: 'POST', body: JSON.stringify({ label }) }),
  deleteLabel: (taskId: string, labelId: string) => request<void>(TASKS.DELETE_LABEL(taskId, labelId), { method: 'DELETE' }),
  getAllLabels: () => request<string[]>(TASKS.GET_ALL_LABELS),
  // Sub-issues
  getSubIssues: (taskId: string) => request<any[]>(TASKS.GET_SUB_ISSUES(taskId)),
  addSubIssue: (taskId: string, data: { title: string; description?: string }) =>
    request<any>(TASKS.ADD_SUB_ISSUE(taskId), { method: 'POST', body: JSON.stringify(data) }),
  deleteSubIssue: (taskId: string, relationId: string) => request<void>(TASKS.DELETE_SUB_ISSUE(taskId, relationId), { method: 'DELETE' }),
  // Context / Logs / Progress
  getContext: (taskId: string) => request<any>(TASKS.GET_CONTEXT(taskId)),
  getFailureLog: (taskId: string) => request<{ task_id: string; failures: any[] }>(TASKS.GET_FAILURE_LOG(taskId)),
  updateProgress: (taskId: string, data: { progress?: number; notes?: string }) =>
    request<{ success: boolean }>(TASKS.UPDATE_PROGRESS(taskId), { method: 'POST', body: JSON.stringify(data) }),
  getExecutionLogs: (taskId: string, limit?: number) =>
    request<any>(TASKS.GET_EXECUTION_LOGS(taskId), { params: { limit: limit || 50 } }),
  // Verification / Review / Ruling
  getVerifications: (taskId: string) => request<any[]>(TASKS.GET_VERIFICATIONS(taskId)),
  resubmitVerification: (taskId: string, data?: { result?: string; passed?: boolean }) =>
    request<{ success: boolean }>(TASKS.VERIFY(taskId), { method: 'POST', body: JSON.stringify(data || {}) }),
  verifyTask: (taskId: string, data?: { result?: string; passed?: boolean }) =>
    request<{ success: boolean }>(TASKS.VERIFY(taskId), { method: 'POST', body: JSON.stringify(data || {}) }),
  reviewTask: (taskId: string, data: { review: string; decision?: string }) =>
    request<{ success: boolean }>(TASKS.REVIEW(taskId), { method: 'POST', body: JSON.stringify(data) }),
  rulingTask: (taskId: string, data: { ruling: string; reason?: string }) =>
    request<{ success: boolean }>(TASKS.RULING(taskId), { method: 'POST', body: JSON.stringify(data) }),
  getVerifier: (taskId: string) => request<any>(TASKS.GET_VERIFIER(taskId)),
  // Batch
  batchUpdate: (data: { task_ids: string[]; updates: Record<string, any> }) =>
    request<{ success: boolean }>(TASKS.BATCH_UPDATE, { method: 'PATCH', body: JSON.stringify(data) }),
  remove: (id: number | string) => request<void>(TASKS.REMOVE(id), { method: 'DELETE' }),
  getStatuses: () => request<any>(TASKS.GET_STATUSES),
  getActivity: (taskId: string) => request<any>(TASKS.GET_ACTIVITY(taskId)),
}

// ==================== Agents API ====================

export const agentsApi = {
  list: () => request<Agent[]>(AGENTS.LIST),
  register: (data: { agent_id: string; name: string; capabilities: string[]; address?: string; metadata?: any; capability_tags?: Record<string, string[]> }) =>
    request<Agent>(AGENTS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  unregister: (id: string, reason?: string) =>
    request<{ success: boolean }>(AGENTS.REMOVE(id), { method: 'DELETE', params: reason ? { reason } : {} }),
  heartbeat: (id: string, status?: any) =>
    request<{ success: boolean }>(AGENTS.HEARTBEAT(id), { method: 'POST', body: JSON.stringify({ status }) }),
  discover: (params?: { capabilities?: string; status?: string; max_load?: number }) =>
    request<Agent[]>(AGENTS.DISCOVER, { params: params || {} }),
  find: (id: string) => request<Agent>(AGENTS.DISCOVER_BY_ID(id)),
  updateSettings: (id: string, settings: { max_concurrent_tasks?: number; trigger_mode?: string }) =>
    request<{ success: boolean; agent: Agent }>(`/agents/${id}/settings`, { method: 'PATCH', body: JSON.stringify(settings) }),
  get: (id: string) => request<Agent>(AGENTS.GET(id)),
  updateConfig: (id: string, config: Record<string, any>) =>
    request<any>(AGENTS.UPDATE_CONFIG(id), { method: 'PUT', body: JSON.stringify(config) }),
  getLoad: (id: string) => request<any>(AGENTS.GET_LOAD(id)),
  matchMcp: (id: string, data?: { mcp_server?: string }) =>
    request<any>(AGENT_MATCHING.MATCH_MCP(id), { method: 'POST', body: JSON.stringify(data || {}) }),
  getPendingTasks: (id: string) => request<any[]>(AGENTS.GET_PENDING_TASKS(id)),
  updateTriggerMode: (id: string, trigger_mode: string) =>
    request<any>(AGENTS.UPDATE_TRIGGER_MODE(id), { method: 'PATCH', body: JSON.stringify({ trigger_mode }) }),
  getOnline: () => request<Agent[]>(AGENTS.ONLINE),
  getExecutionLogs: (id: string, limit?: number, offset?: number) =>
    request<any[]>(AGENTS.GET_EXECUTION_LOGS(id), { params: { limit: limit || 50, offset: offset || 0 } }),
  getHeartbeatLogs: (id: string, limit?: number) =>
    request<any[]>(AGENTS.HEARTBEAT_LOGS(id), { params: { limit: limit || 50 } }),
  // Agent Platforms
  listPlatforms: () => request<AgentPlatformInfo[]>(AGENT_PLATFORMS.LIST),
  getPlatformSchema: (type: string) => request<AgentPlatformSchema>(AGENT_PLATFORMS.SCHEMA(type)),
}

// ==================== Agent Platform Types ====================

export interface AgentPlatformInfo {
  type: string
  label: string
  available: boolean
  is_session_based: boolean
}

export interface AgentPlatformField {
  key: string
  label: string
  type: string
  required: boolean
  placeholder?: string
  description?: string
  options?: string[]
  default?: any
}

export interface AgentPlatformSchema {
  platform_type: string
  platform_label: string
  is_session_based: boolean
  fields: AgentPlatformField[]
}

// ==================== Disputes API ====================

export const disputesApi = {
  list: (status?: string, goalId?: string) => {
    const params: Record<string, string> = {}
    if (status) params.status = status
    if (goalId) params.goal_id = goalId
    return request<Dispute[]>(DISPUTES.LIST, { params }).then(items => {
      if (Array.isArray(items)) return items
      if (items && typeof items === 'object' && 'disputes' in items) return (items as any).disputes
      return []
    })
  },
  get: (id: string) => request<Dispute>(DISPUTES.GET(id)),
  create: (data: { dispute_type: string; description: string; involved_agents: string[]; related_task_id?: string; goal_id?: string }) =>
    request<Dispute>(DISPUTES.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  resolve: (id: string, resolution: string, resolvedBy?: string) =>
    request<Dispute>(DISPUTES.RESOLVE(id), { method: 'PATCH', body: JSON.stringify({ resolution, resolved_by: resolvedBy }) }),
  arbitrate: (id: string, data: { decision: string; reason?: string; arbitrator?: string }) =>
    request<Dispute>(DISPUTES.ARBITRATE(id), { method: 'POST', body: JSON.stringify(data) }),
  discuss: (id: string, data: { message: string; author?: string }) =>
    request<{ success: boolean; messages: any[] }>(DISPUTES.DISCUSS(id), { method: 'POST', body: JSON.stringify(data) }),
  getDetail: (id: string) => request<any>(DISPUTES.GET_DETAIL(id)),
  getTimeline: (id: string) => request<any[]>(DISPUTES.GET_TIMELINE(id)),
  updateStatus: (id: string, status: string) =>
    request<Dispute>(DISPUTES.UPDATE_STATUS(id), { method: 'PATCH', body: JSON.stringify({ status }) }),
  getStats: () => request<any>(DISPUTES.GET_STATS),
}

// ==================== Traces API ====================

export const tracesApi = {
  start: (taskId: string, workflowId: string, taskTitle: string) =>
    request(TRACES.CREATE, { method: 'POST', body: JSON.stringify({ task_id: taskId, workflow_id: workflowId, task_title: taskTitle }) }),
  complete: (taskId: string, data: { final_state: string; success: boolean; result?: any; error_message?: string; cognitions_used?: number; context_size_bytes?: number }) =>
    request(TRACES.COMPLETE(taskId), { method: 'PATCH', body: JSON.stringify(data) }),
  get: (taskId: string) => request<Trace>(TRACES.GET(taskId)),
  list: () => request<any>(TRACES.LIST),
  getReport: (taskId: string) => request(TRACES.GET_REPORT(taskId)),
  getExecutionLogs: (taskId: string, limit?: number) =>
    request<any>(TRACES.GET_EXECUTION_LOGS(taskId), { params: { limit: limit || 50 } }),
  getStepStatus: (taskId: string) =>
    request<any>(TRACES.GET_STEP_STATUS(taskId)),
}

// ==================== Workflows API ====================

export const workflowsApi = {
  createFromGoal: (goalId: string, createdBy?: string) =>
    request<Workflow>(`/workflows/from-goal`, { method: 'POST', params: { goal_id: goalId, created_by: createdBy || '' } }),
  get: (id: string) => request<Workflow>(WORKFLOWS.GET(id)),
  list: (params?: { status?: string; goal_id?: string; task_id?: string; page?: number; page_size?: number; search?: string; time_range?: string }) =>
    request<Workflow[]>(WORKFLOWS.LIST, { params: params || {} }).then(items => {
      if (Array.isArray(items)) return items
      if (items && typeof items === 'object' && 'items' in items) return (items as any).items
      return []
    }),
  execute: (workflowId: string) =>
    request<{ workflow_id: string; execution_result: any; sse_stream: string }>(`/workflows/${workflowId}/execute`, { method: 'POST' }),
  addStep: (workflowId: string, stepData: { name: string; description?: string; capabilities?: string[]; input_data?: Record<string, any>; max_retries?: number; timeout_seconds?: number }, dependencies?: string[], insertPosition: string = 'append') =>
    request<any>(`/workflows/${workflowId}/steps`, {
      method: 'POST', body: JSON.stringify({ ...stepData, insert_position: insertPosition, dependencies: dependencies || [] }),
    }),
  activate: (workflowId: string) => request<{ success: boolean; workflow_id: string }>(WORKFLOWS.ACTIVATE(workflowId), { method: 'POST' }),
  updateDag: (workflowId: string, dag: { nodes: any[]; edges: any[] }) =>
    request<any>(WORKFLOWS.UPDATE_DAG(workflowId), { method: 'PATCH', body: JSON.stringify({ dag }) }),
  addNode: (workflowId: string, node: any) =>
    request<any>(WORKFLOWS.ADD_NODE(workflowId), { method: 'POST', body: JSON.stringify({ node }) }),
  updateNode: (workflowId: string, nodeId: string, node: any) =>
    request<any>(WORKFLOWS.UPDATE_NODE(workflowId, nodeId), { method: 'PATCH', body: JSON.stringify({ node }) }),
  deleteNode: (workflowId: string, nodeId: string) =>
    request<void>(WORKFLOWS.DELETE_NODE(workflowId, nodeId), { method: 'DELETE' }),
  addEdge: (workflowId: string, source: string, target: string) =>
    request<any>(WORKFLOWS.ADD_EDGE(workflowId), { method: 'POST', body: JSON.stringify({ source, target }) }),
  deleteEdge: (workflowId: string, source: string, target: string) =>
    request<void>(WORKFLOWS.DELETE_EDGE(workflowId, source, target), { method: 'DELETE' }),
  reorderNodes: (workflowId: string, order: string[]) =>
    request<any>(WORKFLOWS.REORDER(workflowId), { method: 'POST', body: JSON.stringify({ order }) }),
  getConversationHistory: (workflowId: string) => request<any[]>(WORKFLOWS.GET_CONVERSATION_HISTORY(workflowId)),
  resetConversation: (workflowId: string) => request<void>(WORKFLOWS.RESET_CONVERSATION(workflowId), { method: 'POST' }),
  converse: (workflowId: string, message: string) =>
    request<any>(WORKFLOWS.CONVERSE(workflowId), { method: 'POST', body: JSON.stringify({ message }) }),
  getProgress: (workflowId: string) => request<any>(WORKFLOWS.GET_PROGRESS(workflowId)),
  getEdges: (workflowId: string) => request<any[]>(WORKFLOWS.ADD_EDGE(workflowId)),
  getDiagram: (workflowId: string) => request<any>(WORKFLOWS.GET_DIAGRAM(workflowId)),
  confirmAndSplit: (workflowId: string) => request<any>(WORKFLOWS.CONFIRM_AND_SPLIT(workflowId), { method: 'POST' }),
}

// ==================== Agent Matching API ====================

export interface AgentMatchResult {
  agent_id: string; agent_name: string; score: number; match_reasons: string[]; capabilities: string[]; status: string
}

export interface AgentMatchingResponse {
  scenario_id: string; trust_level: number; trust_factors: { factor: string; weight: number; score: number; description: string }[]; matched_agents: AgentMatchResult[]
}

export const agentMatchingApi = {
  match: (scenarioId: string) =>
    request<AgentMatchingResponse>(AGENT_MATCHING.MATCH, { method: 'POST', body: JSON.stringify({ scenario_id: scenarioId }) }),
}

// ==================== Workspace API ====================

export const workspaceApi = {
  clone: (goalId: string) => request(GOALS.WORKSPACE_CLONE(goalId), { method: 'POST' }),
  pull: (goalId: string) => request(GOALS.WORKSPACE_PULL(goalId), { method: 'POST' }),
  push: (goalId: string, commit_msg?: string) => request(GOALS.WORKSPACE_PUSH(goalId), { method: 'POST', body: JSON.stringify({ commit_msg: commit_msg || "Auto-commit from Grever" }) }),
  status: (goalId: string) => request(GOALS.WORKSPACE_STATUS(goalId)),
}

// ==================== Attachments API ====================

export const attachmentsApi = {
  upload: async (file: File, entityType: string, entityId: string, createdBy?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('entity_type', entityType)
    formData.append('entity_id', entityId)
    if (createdBy) formData.append('created_by', createdBy)
    const resp = await fetch(ATTACHMENTS.UPLOAD, { method: 'POST', body: formData })
    return resp.json()
  },
  download: (id: string, forceDownload?: boolean) => {
    const url = forceDownload ? `${ATTACHMENTS.DOWNLOAD(id)}?download=1` : ATTACHMENTS.DOWNLOAD(id)
    return fetch(url)
  },
  delete: async (id: string, force?: boolean) => {
    const resp = await fetch(force ? `${ATTACHMENTS.REMOVE(id)}?force=true` : ATTACHMENTS.REMOVE(id), { method: 'DELETE' })
    return resp
  },
  link: async (id: string, entityType: string, entityId: string) => {
    const resp = await fetch(ATTACHMENTS.LINK(id), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ entity_type: entityType, entity_id: entityId }) })
    return resp.json()
  },
  unlink: async (id: string, entityType: string, entityId: string) => {
    const resp = await fetch(ATTACHMENTS.UNLINK(id, entityType, entityId), { method: 'DELETE' })
    return resp.json()
  },
  list: async (entityType: string, entityId: string) => {
    const resp = await fetch(`${ATTACHMENTS.LIST}?entity_type=${entityType}&entity_id=${entityId}`)
    return resp.json()
  },
  head: async (id: string) => {
    const resp = await fetch(ATTACHMENTS.GET(id), { method: 'HEAD' })
    if (!resp.ok) throw new Error(`附件不存在: ${id}`)
    return {
      filename: resp.headers.get('X-Attachment-Filename'),
      size: parseInt(resp.headers.get('X-Attachment-Size') || '0'),
      mime: resp.headers.get('X-Attachment-MIME') || '',
      hash: resp.headers.get('X-Attachment-Hash'),
      createdAt: resp.headers.get('X-Attachment-CreatedAt'),
      createdBy: resp.headers.get('X-Attachment-CreatedBy'),
    }
  },
}

// ==================== Industry Pack Extended API ====================

export interface PackVersion {
  id: string
  pack_id: string
  version: string
  action: string
  operation?: string  // alias for action (for backward compat)
  created_at: number
  notes?: string
  created_by?: string
}

export interface PackExportOptions {
  format: 'grever-pack' | 'json'
  include_resources?: boolean
}

export interface PackImportOptions {
  strategy: 'create' | 'upsert' | 'force'
  auto_install_deps?: boolean
}

export interface PackImportResult {
  success: boolean
  pack_id?: string
  message?: string
  errors?: string[]
}

export interface PackValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export const industryPacksExtendedApi = {
  versions: (packId: string) =>
    request<{ pack_id: string; versions: PackVersion[]; total: number }>(INDUSTRY_PACKS.VERSIONS(packId)).then(
      (res) => ({ items: res.versions || [], total: res.total || 0 }),
    ),
  exportPack: (packId: string, options: PackExportOptions) =>
    request<Blob>(INDUSTRY_PACKS.EXPORT(packId), {
      method: 'POST',
      body: JSON.stringify(options),
      headers: { 'Content-Type': 'application/json' },
    }),
  importPack: (formData: FormData, options: PackImportOptions) =>
    request<PackImportResult>(INDUSTRY_PACKS.IMPORT, {
      method: 'POST',
      body: formData,
    }),
  diffPacks: (packA: string, packB: string) =>
    request<any>(INDUSTRY_PACKS.DIFF(packA, packB)),
  validatePack: (packId: string) =>
    request<PackValidationResult>(INDUSTRY_PACKS.VALIDATE(packId), { method: 'POST' }),
}

// Removed: PromptTemplate, SOP, Checklist, ReferenceData interfaces and APIs (orphaned)

// ==================== Re-export ====================

export * from './securityApi'
export * from './scenariosApi'

// ==================== 复合 API ====================

export async function getGoalWithDetails(goalId: string | number) {
  const [goal, projects, tasks, disputes] = await Promise.all([
    goalsApi.get(goalId), projectsApi.list(), tasksApi.list(), disputesApi.list(),
  ])
  return { goal, projects, tasks, disputes }
}

export async function getDashboardData() {
  const [goals, agents, tasks, disputes]: [Goal[], Agent[], Task[], Dispute[]] = await Promise.all([
    goalsApi.list(), agentsApi.list(), tasksApi.list(), disputesApi.list(),
  ])
  const runningTasks = tasks.filter((t: Task) => t.status === 'in_progress').length
  const pendingTasks = tasks.filter((t: Task) => t.status === 'todo' || t.status === 'pending').length
  const openDisputes = disputes.filter((d: Dispute) => d.status === 'open' || d.status === 'active').length
  const completedTasks = tasks.filter((t) => t.status === 'done' || t.status === 'completed').length
  return { goals, agents, tasks, disputes, stats: { runningTasks, pendingTasks, openDisputes, completedTasks } }
}

// ==================== Scenario Match/Instantiate ====================

export interface ScenarioMatchResponse {
  goal_id: string; goal_title: string; matches: Array<{ scenario_id: string; name: string; category: string; level: string; match_score: number; trust_level: string; usage_count: number; description: string; phase_count: number }>; threshold_met: boolean; threshold: number
}

export interface InstantiateWorkflowResponse {
  workflow_id: string; scenario_id: string; goal_id: string; name: string; status: string; phase_count: number; dag: any; workflow?: { id: string; name: string; steps?: any[] }; scenario?: { id: string; name: string; description?: string }
}

export interface CreateScenarioResponse {
  scenario_id: string; name: string; category: string; description: string; phase_count: number
}

export async function matchScenarioForGoal(goalId: string): Promise<ScenarioMatchResponse> {
  const resp = await fetch(SCENARIOS.MATCH_FOR_GOAL(goalId), { method: 'POST', headers: { 'Content-Type': 'application/json' } })
  if (!resp.ok) throw new Error(`场景匹配失败: ${resp.status}`)
  return resp.json()
}

export async function createScenarioFromGoal(goalId: string): Promise<CreateScenarioResponse> {
  const resp = await fetch(SCENARIOS.CREATE_FOR_GOAL(goalId), { method: 'POST', headers: { 'Content-Type': 'application/json' } })
  if (!resp.ok) throw new Error(`创建场景失败: ${resp.status}`)
  return resp.json()
}

// ==================== GrASP API ====================

export const graspApi = {
  cognitionAssessment: (agentId: string) => request<any>(GRASP.COGNITION_ASSESSMENT(agentId)),
  recommend: (params?: { capabilities?: string }) => request<any>(GRASP.RECOMMEND, { params: params || {} }),
  cognitionList: () => request<any[]>(GRASP.COGNITION_LIST),
  cognitionGet: (id: string) => request<any>(GRASP.COGNITION_GET(id)),
  cognitionCreate: (data: any) => request<any>(GRASP.COGNITION_CREATE, { method: 'POST', body: JSON.stringify(data) }),
  cognitionUpdate: (id: string, data: any) => request<any>(GRASP.COGNITION_UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  cognitionRemove: (id: string) => request<void>(GRASP.COGNITION_REMOVE(id), { method: 'DELETE' }),
  knowledgeGraph: () => request<any>(GRASP.KNOWLEDGE_GRAPH),
  knowledgeList: () => request<any[]>(GRASP.KNOWLEDGE_LIST),
  injectRules: () => request<any>(GRASP.INJECT_RULES),
  injectRule: (ruleId: string) => request<any>(GRASP.INJECT_RULE(ruleId)),
  injectStatus: () => request<any>(GRASP.INJECT_STATUS),
  injectLogs: (page: number, pageSize: number) =>
    request<any>(GRASP.INJECT_RULES + `/logs?page=${page}&page_size=${pageSize}`),
}

// ==================== MCP Servers API ====================

export const mcpServersApi = {
  list: () => request<{ servers: any[]; total: number }>(MCP_SERVERS.LIST),
  get: (id: string) => request<any>(MCP_SERVERS.GET(id)),
  create: (data: any) => request<any>(MCP_SERVERS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: any) => request<any>(MCP_SERVERS.UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) => request<void>(MCP_SERVERS.REMOVE(id), { method: 'DELETE' }),
  getTools: (id: string) => request<{ tools: any[] }>(MCP_SERVERS.GET_TOOLS(id)),
}

// ==================== Skills API ====================

export const skillsApi = {
  list: () => request<{ skills: any[]; total: number }>(SKILLS.LIST),
  get: (id: string) => request<any>(SKILLS.GET(id)),
  getFiles: (id: string) => request<any>(SKILLS.GET_FILES(id)),
  getInstallPrompt: (id: string) => request<any>(SKILLS.GET_INSTALL_PROMPT(id)),
  getRaw: (id: string, filename: string) => request<any>(SKILLS.GET_RAW(id, filename)),
}

// Sprint 116: Pack Skills API (DB-backed industry pack skills)

export interface PackSkill {
  id: string
  pack_id: string
  name: string
  description: string | null
  input_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
  required_tags: string[]
  tool_dependency: string | null
  created_at: number
  updated_at: number | null
}

export const packSkillsApi = {
  list: (packId?: string) => {
    const params = packId ? `?pack_id=${packId}` : ''
    return request<{ skills: PackSkill[]; total: number }>(`/api/v1/pack-skills${params}`)
  },
  listByPack: (packId: string) =>
    request<{ skills: PackSkill[]; total: number }>(PACK_SKILLS.BY_PACK(packId)),
  byPack: (packId: string) =>
    request<{ skills: PackSkill[]; total: number }>(PACK_SKILLS.BY_PACK(packId)),
  get: (id: string) => request<PackSkill>(PACK_SKILLS.GET(id)),
}

// ==================== Human Input API ====================

export const humanInputApi = {
  listPending: (params?: Record<string, string>) => request<any>(HUMAN_INPUT.LIST_PENDING, { params: params || {} }),
  get: (id: string) => request<any>(HUMAN_INPUT.GET(id)),
  getByTask: (taskId: string) => request<any>(HUMAN_INPUT.GET_BY_TASK(taskId)),
  getByScenario: (scenarioId: string) => request<any>(HUMAN_INPUT.GET_BY_SCENARIO(scenarioId)),
  getRecent: () => request<any[]>(HUMAN_INPUT.GET_RECENT),
  submit: (id: string, data: any) => request<any>(HUMAN_INPUT.SUBMIT(id), { method: 'POST', body: JSON.stringify(data) }),
  reject: (id: string, data?: any) => request<any>(HUMAN_INPUT.REJECT(id), { method: 'POST', body: JSON.stringify(data || {}) }),
  getStats: () => request<any>(HUMAN_INPUT.GET_STATS),
  getReviewStats: () => request<any>(HUMAN_INPUT.GET_REVIEW_STATS),
  getAnalytics: (days: number) => request<any>(HUMAN_INPUT.GET_ANALYTICS(days)),
}

// ==================== Human Review API ====================

export const humanReviewApi = {
  listPending: () => request<any[]>(HUMAN_REVIEW.LIST_PENDING),
  getStats: () => request<any>(HUMAN_REVIEW.GET_STATS),
  batchRuling: (data: any) => request<any>(HUMAN_REVIEW.BATCH_RULING, { method: 'POST', body: JSON.stringify(data) }),
}

// ==================== Dashboard API ====================

export const dashboardApi = {
  stats: () => request<any>(DASHBOARD.STATS),
}

// ==================== Industry Tags API ====================

export const industryTagsApi = {
  list: () => request<any>(INDUSTRY_TAGS.LIST),
  get: (tagId: string) => request<any>(INDUSTRY_TAGS.GET(tagId)),
  create: (data: any) => request<any>(INDUSTRY_TAGS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (tagId: string, data: any) => request<any>(INDUSTRY_TAGS.UPDATE(tagId), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (tagId: string) => request<void>(INDUSTRY_TAGS.REMOVE(tagId), { method: 'DELETE' }),
  getReferences: (tagId: string) => request<any>(INDUSTRY_TAGS.GET_REFERENCES(tagId)),
  getByIndustry: (industry: string) => request<any>(INDUSTRY_TAGS.GET_BY_INDUSTRY(industry)),
  getIndustries: () => request<any>(INDUSTRY_TAGS.GET_INDUSTRIES),
  getStats: () => request<any>(INDUSTRY_TAGS.GET_STATS),
  agentTags: (agentId: string) => request<any>(INDUSTRY_TAGS.AGENT_TAGS + `?agent_id=${agentId}`),
  agentTagRecommend: (agentId: string) => request<any>(INDUSTRY_TAGS.AGENT_TAG_RECOMMEND + `?agent_id=${agentId}`),
}

export const AttachmentUploaderApi = attachmentsApi

// ==================== Knowledge API (Sprint 75 Phase 2) ====================

export const knowledgeApi = {
  list: (params?: { pack_id?: string; category?: string; search?: string; page?: number; page_size?: number }) =>
    request<{ items: KnowledgeEntry[]; total: number; page: number; page_size: number }>(KNOWLEDGE.LIST, { params: params || {} }),
  get: (id: string) => request<KnowledgeEntry>(KNOWLEDGE.GET(id)),
  create: (data: KnowledgeCreate) => request<KnowledgeEntry>(KNOWLEDGE.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: KnowledgeUpdate) => request<KnowledgeEntry>(KNOWLEDGE.UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) => request<{ success: boolean; id: string }>(KNOWLEDGE.REMOVE(id), { method: 'DELETE' }),
}

export const agentSchemesApi = {
  list: (params?: { pack_id?: string; page?: number; page_size?: number }) =>
    request<{ items: AgentScheme[]; total: number; page: number; page_size: number }>(AGENT_SCHEMES.LIST, { params: params || {} }),
  get: (id: string) => request<AgentScheme>(AGENT_SCHEMES.GET(id)),
  create: (data: AgentSchemeCreate) => request<AgentScheme>(AGENT_SCHEMES.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: AgentSchemeUpdate) => request<AgentScheme>(AGENT_SCHEMES.UPDATE(id), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) => request<{ success: boolean; id: string }>(AGENT_SCHEMES.REMOVE(id), { method: 'DELETE' }),
  listRoles: (schemeId: string) =>
    request<{ items: AgentSchemeRole[]; total: number }>(AGENT_SCHEMES.LIST_ROLES(schemeId)),
  createRole: (schemeId: string, data: { role_name: string; required_tags: string[]; priority?: number }) =>
    request<AgentSchemeRole>(AGENT_SCHEMES.CREATE_ROLE(schemeId), { method: 'POST', body: JSON.stringify(data) }),
  removeRole: (schemeId: string, roleId: string) =>
    request<{ success: boolean; id: string }>(AGENT_SCHEMES.REMOVE_ROLE(schemeId, roleId), { method: 'DELETE' }),
}
