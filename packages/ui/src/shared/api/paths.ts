/**
 * API Paths Registry - 所有后端 API 路径的唯一注册处
 * 
 * 规则：
 * 1. 所有 API 路径必须在这里定义
 * 2. 其他文件禁止硬编码路径，必须从本文件导入
 * 3. 后端合并/删除端点时，只改这个文件
 */

// ==================== 基础路径 ====================
export const API_V1 = '/api/v1'

// ==================== 1. 工作分解（业务核心+场景库） ====================

// Goals
export const GOALS = {
  LIST: '/goals',
  GET: (id: string | number) => `/goals/${id}`,
  CREATE: '/goals',
  UPDATE: (id: string | number) => `/goals/${id}`,
  UPDATE_STATUS: (id: string | number) => `/goals/${id}/status`,
  REMOVE: (id: string | number) => `/goals/${id}`,
  DECOMPOSE: (id: string | number) => `/goals/${id}/decompose`,
  DECOMPOSE_PREVIEW: (id: string | number) => `/goals/${id}/decompose/preview`,
  AUTO_DECOMPOSE_PREVIEW: (id: string | number) => `/goals/${id}/auto-decompose/preview`,
  SUBMIT_DECOMPOSE: (id: string | number) => `/goals/${id}/decompose/submit`,
  SET_VERIFIER: (id: string | number) => `/goals/${id}/verifier`,
  SET_CONSTRAINTS: (id: string | number) => `/goals/${id}/constraints`,
  SET_MODE: (id: string | number) => `/goals/${id}/mode`,
  START_ITERATION: (id: string | number) => `/goals/${id}/start-iteration`,
  PAUSE_ITERATION: (id: string | number) => `/goals/${id}/pause-iteration`,
  CONVERGE_ITERATION: (id: string | number) => `/goals/${id}/converge-iteration`,
  ITERATE: (id: string | number) => `/goals/${id}/iterate`,
  GET_ITERATION_STATUS: (id: string | number) => `/goals/${id}/iteration-status`,
  GET_ITERATIONS: (id: string | number) => `/goals/${id}/iterations`,
  ITERATION_ANALYSIS: (id: string | number, iterId: string | number) => `/goals/${id}/iterations/${iterId}/analysis`,
  ITERATION_CONSENSUS: (id: string | number, iterId: string | number) => `/goals/${id}/iterations/${iterId}/consensus`,
  ITERATION_DISCUSS: (id: string | number, iterId: string | number) => `/goals/${id}/iterations/${iterId}/discuss`,
  AUTO_ASSIGN: (id: string | number) => `/goals/${id}/auto-assign`,
  ACTIVATE: (id: string | number) => `/goals/${id}/activate`,
  PAUSE: (id: string | number) => `/goals/${id}/pause`,
  RESUME: (id: string | number) => `/goals/${id}/resume`,
  GET_TREE: (id: string | number) => `/goals/${id}/tree`,
  // Workspace
  WORKSPACE_CLONE: (id: string | number) => `/goals/${id}/workspace/clone`,
  WORKSPACE_PULL: (id: string | number) => `/goals/${id}/workspace/pull`,
  WORKSPACE_PUSH: (id: string | number) => `/goals/${id}/workspace/push`,
  WORKSPACE_STATUS: (id: string | number) => `/goals/${id}/workspace/status`,
} as const

// Projects
export const PROJECTS = {
  LIST: '/projects',
  GET: (id: string | number) => `/projects/${id}`,
  CREATE: '/projects',
  UPDATE: (id: string | number) => `/projects/${id}`,
  REMOVE: (id: string | number) => `/projects/${id}`,
  PAUSE: (id: string | number) => `/projects/${id}/pause`,
  RESUME: (id: string | number) => `/projects/${id}/resume`,
  GET_DIAGRAM: (id: string | number) => `/projects/${id}/diagram`,
  GET_TASK_TREE: (id: string | number) => `/projects/${id}/task-tree`,
  SET_VERIFIER: (id: string | number) => `/projects/${id}/verifier`,
  AUTO_ASSIGN: (id: string | number) => `/projects/${id}/auto-assign`,
  UPDATE_STATUS: (id: string | number) => `/projects/${id}/status`,
} as const

// Tasks
export const TASKS = {
  LIST: '/tasks',
  GET: (id: string) => `/tasks/${id}`,
  CREATE: '/tasks',
  UPDATE: (id: string) => `/tasks/${id}`,
  UPDATE_STATUS: (id: string) => `/tasks/${id}/status`,
  REMOVE: (id: string | number) => `/tasks/${id}`,
  ASSIGN: (id: string) => `/tasks/${id}/assign`,
  COMPLETE: (id: string) => `/tasks/${id}/complete`,
  FAIL: (id: string) => `/tasks/${id}/fail`,
  RETRY: (id: string) => `/tasks/${id}/retry`,
  PAUSE: (id: string) => `/tasks/${id}/pause`,
  RESUME: (id: string) => `/tasks/${id}/resume`,
  RESTART: (id: string) => `/tasks/${id}/restart`,
  BLOCK: (id: string) => `/tasks/${id}/block`,
  UNBLOCK: (id: string) => `/tasks/${id}/unblock`,
  TERMINATE: (id: string) => `/tasks/${id}/terminate`,
  TAKEOVER: (id: string) => `/tasks/${id}/takeover`,
  GET_STATUSES: '/tasks/statuses',
  BATCH_UPDATE: '/tasks/batch',
  // Subtasks
  GET_SUBTASKS: (id: string) => `/tasks/${id}/subtasks`,
  GET_PARENT: (id: string) => `/tasks/${id}/parent`,
  // Comments
  GET_COMMENTS: (id: string) => `/tasks/${id}/comments`,
  ADD_COMMENT: (id: string) => `/tasks/${id}/comments`,
  DELETE_COMMENT: (id: string, commentId: string) => `/tasks/${id}/comments/${commentId}`,
  // Labels
  GET_LABELS: (id: string) => `/tasks/${id}/labels`,
  ADD_LABEL: (id: string) => `/tasks/${id}/labels`,
  DELETE_LABEL: (id: string, labelId: string) => `/tasks/${id}/labels/${labelId}`,
  GET_ALL_LABELS: '/tasks/labels/all',
  // Sub-issues
  GET_SUB_ISSUES: (id: string) => `/tasks/${id}/sub-issues`,
  ADD_SUB_ISSUE: (id: string) => `/tasks/${id}/sub-issues`,
  DELETE_SUB_ISSUE: (id: string, relationId: string) => `/tasks/${id}/sub-issues/${relationId}`,
  // Execution
  GET_FAILURE_LOG: (id: string) => `/tasks/${id}/failure-log`,
  GET_EXECUTION_LOGS: (id: string) => `/tasks/${id}/execution-logs`,
  UPDATE_PROGRESS: (id: string) => `/tasks/${id}/progress`,
  // Verification
  GET_VERIFICATIONS: (id: string) => `/tasks/${id}/verifications`,
  VERIFY: (id: string) => `/tasks/${id}/verify`,
  REVIEW: (id: string) => `/tasks/${id}/review`,
  RULING: (id: string) => `/tasks/${id}/ruling`,
  GET_VERIFIER: (id: string) => `/tasks/${id}/verifier`,
  SET_VERIFIER: (id: string) => `/tasks/${id}/verifier`,
  // Context
  GET_CONTEXT: (id: string) => `/tasks/${id}/context`,
  // HITL
  ADD_HITL: (id: string) => `/tasks/${id}/add-hitl`,
  // Activity
  GET_ACTIVITY: (id: string) => `/tasks/${id}/activity`,
} as const

// Scenarios
export const SCENARIOS = {
  LIST: '/scenarios',
  GET: (id: string) => `/scenarios/${id}`,
  CREATE: '/scenarios',
  UPDATE: (id: string) => `/scenarios/${id}`,
  REMOVE: (id: string) => `/scenarios/${id}`,
  GET_STATUS: (id: string) => `/scenarios/${id}/status`,
  UPDATE_STATUS: (id: string) => `/scenarios/${id}/status`,
  REVIEW: (id: string) => `/scenarios/${id}/review`,
  ADD_PROJECT: (id: string) => `/scenarios/${id}/projects`,
  UPDATE_PROJECT: (id: string, projectId: string) => `/scenarios/${id}/projects/${projectId}`,
  REMOVE_PROJECT: (id: string, projectId: string) => `/scenarios/${id}/projects/${projectId}`,
  ADD_TASK: (id: string) => `/scenarios/${id}/tasks`,
  UPDATE_TASK: (id: string, taskId: string) => `/scenarios/${id}/tasks/${taskId}`,
  REMOVE_TASK: (id: string, taskId: string) => `/scenarios/${id}/tasks/${taskId}`,
  GET_FULLSET: (id: string) => `/scenarios/${id}/fullset`,
  UPDATE_FULLSET: (id: string) => `/scenarios/${id}/fullset`,
  CUSTOM_CREATE: '/scenarios/custom-create',
  DERIVE_FROM_EXECUTION: (goalId: string) => `/scenarios/from-execution/${goalId}`,
  DERIVE_FROM_PROJECT_EXECUTION: (projectId: string) => `/scenarios/from-execution/project/${projectId}`,
  GET_VERSIONS: (id: string) => `/scenarios/${id}/versions`,
  FEEDBACK: (id: string) => `/scenarios/${id}/feedback`,
  CREATE_FOR_GOAL: (goalId: string) => `/scenarios/create-for-goal/${goalId}`,
  MATCH_FOR_GOAL: (goalId: string) => `/scenarios/match-for-goal/${goalId}`,
  MATCH_PREVIEW: `/scenarios/match-preview`,
  INSTANTIATE_TO_GOAL: (id: string) => `/scenarios/${id}/instantiate-to-goal`,
  PREVIEW: (id: string) => `/scenarios/${id}/preview`,
  DERIVE_FROM_COGNITIONS: '/scenarios/derive-from-cognitions',
  DERIVE_FROM_COGNITIONS_CONFIRM: '/scenarios/derive-from-cognitions/confirm',
  // Emergency (垂直领域，待删除)
  EMERGENCY_COMMAND_CENTER: `/emergency/command-center`,
  EMERGENCY_STARTUP: `/emergency/startup`,
} as const

// Workflows
export const WORKFLOWS = {
  LIST: `/workflows`,
  GET: (id: string) => `/workflows/${id}`,
  ACTIVATE: (id: string) => `/workflows/${id}/activate`,
  GET_PROGRESS: (id: string) => `/workflows/${id}/progress`,
  GET_DIAGRAM: (id: string) => `/workflows/${id}/diagram`,
  CONFIRM_AND_SPLIT: (id: string) => `/workflows/${id}/confirm-and-split`,
  // DAG
  UPDATE_DAG: (id: string) => `/workflows/${id}/dag`,
  ADD_NODE: (id: string) => `/workflows/${id}/dag/nodes`,
  UPDATE_NODE: (id: string, nodeId: string) => `/workflows/${id}/dag/nodes/${nodeId}`,
  DELETE_NODE: (id: string, nodeId: string) => `/workflows/${id}/dag/nodes/${nodeId}`,
  ADD_EDGE: (id: string) => `/workflows/${id}/dag/edges`,
  DELETE_EDGE: (id: string, source: string, target: string) => `/workflows/${id}/dag/edges/${source}/${target}`,
  REORDER: (id: string) => `/workflows/${id}/dag/reorder`,
  // DAG Chat
  CONVERSE: (id: string) => `/workflows/${id}/dag/converse`,
  GET_CONVERSATION_HISTORY: (id: string) => `/workflows/${id}/dag/conversation/history`,
  RESET_CONVERSATION: (id: string) => `/workflows/${id}/dag/conversation/reset`,
} as const

// ==================== 2. 调度与执行引擎 ====================

export const SCHEDULER = {
  STATS: `/scheduler/stats`,
  AGENTS_HEALTH: `/scheduler/agents/health`,
  LOGS: `/scheduler/logs`,
  TICK: `/scheduler/tick`,
  DEPENDENCIES_UNLOCK: `/scheduler/dependencies/unlock`,
} as const

export const TIMEOUT = {
  CHECK: `/timeout/check`,
  CONFIG: `/timeout/config`,
  CHECK_TASK: (taskId: string) => `/timeout/check-task/${taskId}`,
} as const

export const TRACES = {
  LIST: `/traces`,
  CREATE: `/traces`,
  GET: (taskId: string) => `/traces/${taskId}`,
  COMPLETE: (taskId: string) => `/traces/${taskId}/complete`,
  GET_REPORT: (taskId: string) => `/reports/${taskId}`,
  GET_STEP_STATUS: (taskId: string) => `/traces/${taskId}/step-status`,
  GET_EXECUTION_LOGS: (taskId: string) => `/traces/${taskId}/execution-logs`,
} as const

// ==================== 3. 智能匹配（含能力标签） ====================

export const AGENTS = {
  LIST: '/agents',
  ONLINE: '/agents/online',
  GET: (id: string) => `/agents/${id}`,
  CREATE: '/agents',
  REMOVE: (id: string) => `/agents/${id}`,
  HEARTBEAT: (id: string) => `/agents/${id}/heartbeat`,
  HEARTBEAT_LOGS: (id: string) => `/agents/${id}/heartbeat_logs`,
  GET_LOAD: (id: string) => `/agents/${id}/load`,
  UPDATE_CONFIG: (id: string) => `/agents/${id}/config`,
  UPDATE_TRIGGER_MODE: (id: string) => `/agents/${id}/trigger_mode`,
  GET_EXECUTION_LOGS: (id: string) => `/agents/${id}/execution-logs`,
  GET_PENDING_TASKS: (id: string) => `/agents/${id}/pending-tasks`,
  // Discovery
  DISCOVER: '/discover',
  DISCOVER_BY_ID: (id: string) => `/discover/${id}`,
} as const

export const AGENT_PLATFORMS = {
  LIST: '/agent-platforms',
  SCHEMA: (type: string) => `/agent-platforms/${type}/registration-schema`,
} as const

export const AGENT_MATCHING = {
  MATCH: `/agent-matching/match`,
  GET_TRUST_LEVELS: (scenarioId: string) => `/agent-matching/trust-levels/${scenarioId}`,
  UPDATE_TRUST_LEVELS: `/agent-matching/trust-levels/update`,
  MATCH_MCP: (agentId: string) => `/agents/${agentId}/match-mcp`,
} as const

export const CAPABILITIES = {
  LIST: `/capabilities`,
  SEED: `/capabilities/seed`,
} as const

export const INDUSTRY_TAGS = {
  LIST: `/industry-tags`,
  GET: (tagId: string) => `/industry-tags/${tagId}`,
  CREATE: `/industry-tags`,
  UPDATE: (tagId: string) => `/industry-tags/${tagId}`,
  REMOVE: (tagId: string) => `/industry-tags/${tagId}`,
  GET_REFERENCES: (tagId: string) => `/industry-tags/${tagId}/references`,
  GET_BY_INDUSTRY: (industry: string) => `/industry-tags/_by-industry/${industry}`,
  GET_INDUSTRIES: `/industry-tags/_industries`,
  GET_STATS: `/industry-tags/_stats`,
  AGENT_TAGS: `/industry-tags/agent-tags`,
  AGENT_TAG_RECOMMEND: `/industry-tags/agent-tag-recommend`,
} as const

export const INDUSTRY_PACKS = {
  LIST: `/industry-packs`,
  GET: (packId: string) => `/industry-packs/${packId}`,
  CREATE: `/industry-packs`,
  UPDATE: (packId: string) => `/industry-packs/${packId}`,
  REMOVE: (packId: string) => `/industry-packs/${packId}`,
  ADD_CONTENT: (packId: string) => `/industry-packs/${packId}/contents`,
  REMOVE_CONTENT: (packId: string, contentType: string, contentId: string) => `/industry-packs/${packId}/contents/${contentType}/${contentId}`,
  VERSIONS: (packId: string) => `/industry-packs/${packId}/versions`,
  EXPORT: (packId: string) => `/industry-packs/${packId}/export`,
  IMPORT: `/industry-packs/import`,
  DIFF: (packA: string, packB: string) => `/industry-packs/${packA}/diff/${packB}`,
  VALIDATE: (packId: string) => `/industry-packs/${packId}/validate`,
} as const

export const PROMPT_TEMPLATES = {
  LIST: `/prompt-templates`,
} as const

export const SOPS = {
  LIST: `/sops`,
} as const

export const CHECKLISTS = {
  LIST: `/checklists`,
} as const

export const REFERENCE_DATA = {
  LIST: `/reference-data`,
} as const

// ==================== 4. 人机协同（含争议仲裁） ====================

export const HUMAN_INPUT = {
  LIST_PENDING: `/human-input/pending`,
  GET: (id: string) => `/human-input/${id}`,
  GET_BY_TASK: (taskId: string) => `/human-input/task/${taskId}`,
  GET_BY_SCENARIO: (scenarioId: string) => `/human-input/scenario/${scenarioId}/pending`,
  GET_RECENT: `/human-input/recent`,
  SUBMIT: (id: string) => `/human-input/${id}/submit`,
  REJECT: (id: string) => `/human-input/${id}/reject`,
  GET_STATS: `/human-input/stats`,
  GET_REVIEW_STATS: `/human-input/review-stats`,
  GET_ANALYTICS: (days: number) => `/human-input/analytics?days=${days}`,
} as const

export const HUMAN_REVIEW = {
  LIST_PENDING: `/human-review/pending`,
  GET_STATS: `/human-review/stats`,
  BATCH_RULING: `/human-review/batch-ruling`,
} as const

export const DISPUTES = {
  LIST: `/disputes`,
  GET: (id: string) => `/disputes/${id}`,
  CREATE: `/disputes`,
  RESOLVE: (id: string) => `/disputes/${id}/resolve`,
  ARBITRATE: (id: string) => `/disputes/${id}/arbitrate`,
  DISCUSS: (id: string) => `/disputes/${id}/discuss`,
  GET_DETAIL: (id: string) => `/disputes/${id}/detail`,
  GET_TIMELINE: (id: string) => `/disputes/${id}/timeline`,
  UPDATE_STATUS: (id: string) => `/disputes/${id}/status`,
  GET_STATS: `/disputes/stats`,
} as const

export const SOLUTIONS = {
  LIST: '/solutions',
  GET: (id: string) => `/solutions/${id}`,
  CREATE: '/solutions',
  UPDATE: (id: string) => `/solutions/${id}`,
  REMOVE: (id: string) => `/solutions/${id}`,
  COMPARE: '/solutions/compare',
  COMPARE_MULTI: '/solutions/compare/multi',
  TREND: '/solutions/trend',
  // Iterations
  GET_ITERATIONS: (goalId: string) => `/goals/${goalId}/iterations`,
  ITERATION_ANALYSIS: (goalId: string, iterId: string) => `/goals/${goalId}/iterations/${iterId}/analysis`,
  ITERATION_DISCUSS: (goalId: string, iterId: string) => `/goals/${goalId}/iterations/${iterId}/discuss`,
  CONSENSUS: (goalId: string, iterId: string) => `/goals/${goalId}/iterations/${iterId}/consensus`,
} as const

// ==================== 5. 认知引擎（Grasp） ====================

export const GRASP = {
  COGNITION_ASSESSMENT: (agentId: string) => `/grasp/cognition-assessment/${agentId}`,
  RECOMMEND: '/grasp/recommend',
  COGNITION_LIST: '/grasp/cognition',
  COGNITION_GET: (id: string) => `/grasp/cognition/${id}`,
  COGNITION_CREATE: '/grasp/cognition',
  COGNITION_UPDATE: (id: string) => `/grasp/cognition/${id}`,
  COGNITION_REMOVE: (id: string) => `/grasp/cognition/${id}`,
  KNOWLEDGE_GRAPH: '/grasp/graph',
  KNOWLEDGE_LIST: '/grasp/knowledge',
  // Injection
  INJECT_RULES: `/grasp/inject/rules`,
  INJECT_RULE: (ruleId: string) => `/grasp/inject/rules/${ruleId}`,
  INJECT_STATUS: `/grasp/inject/status`,
} as const

export const CONTEXT = {
  GET: (entity: string, entityId: string) => `/context/${entity}/${entityId}`,
  UPDATE: (entity: string, entityId: string) => `/context/${entity}/${entityId}`,
} as const

export const KNOWLEDGE_INJECTOR = {
  TASK_RESULT: '/knowledge-injector/task-result',
  WORKFLOW_RESULT: '/knowledge-injector/workflow-result',
  DISPUTE_RESULT: '/knowledge-injector/dispute-result',
  STATUS: '/knowledge-injector/status',
} as const

// ==================== 6. 系统扩展 ====================

export const MCP_SERVERS = {
  LIST: `/mcp-servers`,
  GET: (id: string) => `/mcp-servers/${id}`,
  CREATE: `/mcp-servers`,
  UPDATE: (id: string) => `/mcp-servers/${id}`,
  REMOVE: (id: string) => `/mcp-servers/${id}`,
  GET_TOOLS: (id: string) => `/mcp-servers/${id}/tools`,
  LIST_ALL: `/mcp`,
} as const

export const SKILLS = {
  LIST: `/skills`,
  GET: (id: string) => `/skills/${id}`,
  GET_FILES: (id: string) => `/skills/${id}/files`,
  GET_INSTALL_PROMPT: (id: string) => `/skills/${id}/install-prompt`,
  GET_RAW: (id: string, filename: string) => `/skills/${id}/raw/${filename}`,
} as const

export const ATTACHMENTS = {
  UPLOAD: `/attachments/upload`,
  LIST: `/attachments`,
  GET: (id: string) => `/attachments/${id}`,
  DOWNLOAD: (id: string) => `/attachments/${id}/download`,
  REMOVE: (id: string) => `/attachments/${id}`,
  LINK: (id: string) => `/attachments/${id}/link`,
  UNLINK: (id: string, entityType: string, entityId: string) => `/attachments/${id}/link/${entityType}/${entityId}`,
} as const

export const ARTIFACTS = {
  LIST: `/artifacts`,
  GET: (id: string) => `/artifacts/${id}`,
  DOWNLOAD: (id: string) => `/artifacts/${id}/download`,
  CREATE: `/artifacts`,
  UPDATE: (id: string) => `/artifacts/${id}`,
  REMOVE: (id: string) => `/artifacts/${id}`,
} as const

export const REPORTS = {
  GET: (workflowId: string) => `/reports/${workflowId}`,
} as const

// ==================== 7. 系统配置 ====================

export const ADMIN = {
  LIST_AGENTS: `/admin/agents`,
  REREGISTER_AGENT: (agentId: string) => `/admin/agents/${agentId}/reregister`,
  SET_AGENT_STATUS: (agentId: string) => `/admin/agents/${agentId}/set-status`,
  FORCE_OFFLINE: (agentId: string) => `/admin/agents/${agentId}/force-offline`,
  RESTART_AGENT: (agentId: string) => `/admin/agents/${agentId}/restart`,
  LIST_TASKS: `/admin/tasks`,
  RESET_TASK: (taskId: string) => `/admin/tasks/${taskId}/reset`,
  CLEANUP_ZOMBIE_TASKS: `/admin/cleanup/zombie-tasks`,
} as const

export const SETTINGS = {
  LIST: '/settings',
  GET: (category: string) => `/settings/${category}`,
  GET_KEY: (category: string, key: string) => `/settings/${category}/${key}`,
  UPDATE_KEY: (category: string, key: string) => `/settings/${category}/${key}`,
  BATCH_UPDATE: (category: string) => `/settings/${category}/batch`,
  TEST_CONNECTION: '/settings/test-connection',
  LIST_MODELS: '/settings/models',
  LIST_SESSIONS: '/settings/sessions',
} as const

export const SECURITY = {
  AUDIT_LOGS: `/audit/logs`,
  ALERTS: `/alerts`,
  CREATE_ALERT: `/alerts`,
  GET_ALERT: (id: string) => `/alerts/${id}`,
  UPDATE_ALERT: (id: string) => `/alerts/${id}`,
  REMOVE_ALERT: (id: string) => `/alerts/${id}`,
  SECURITY_ALERTS: `/security/alerts`,
  SECURITY_AUDIT_LOGS: `/security/audit/logs`,
} as const

export const DASHBOARD = {
  STATS: `/dashboard/stats`,
} as const

export const SEARCH = {
  GLOBAL: `/search`,
} as const

export const API_DOCS = {
  ENDPOINTS: '/endpoints',
  STATUS: '/status',
  FEATURES: '/features',
} as const

// ==================== 辅助：事件流 ====================
export const EVENTS = {
  STREAM: `/events/stream`,
  PULL: (id: string) => `/events/pull?${id}`,
} as const
