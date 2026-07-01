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
  LIST: '/api/v1/goals',
  GET: (id: string | number) => `/api/v1/goals/${id}`,
  CREATE: '/api/v1/goals',
  UPDATE: (id: string | number) => `/api/v1/goals/${id}`,
  UPDATE_STATUS: (id: string | number) => `/api/v1/goals/${id}/status`,
  REMOVE: (id: string | number) => `/api/v1/goals/${id}`,
  DECOMPOSE: (id: string | number) => `/api/v1/goals/${id}/decompose`,
  DECOMPOSE_PREVIEW: (id: string | number) => `/api/v1/goals/${id}/decompose/preview`,
  AUTO_DECOMPOSE_PREVIEW: (id: string | number) => `/api/v1/goals/${id}/auto-decompose/preview`,
  SUBMIT_DECOMPOSE: (id: string | number) => `/api/v1/goals/${id}/decompose/submit`,
  SET_VERIFIER: (id: string | number) => `/api/v1/goals/${id}/verifier`,
  SET_CONSTRAINTS: (id: string | number) => `/api/v1/goals/${id}/constraints`,
  SET_MODE: (id: string | number) => `/api/v1/goals/${id}/mode`,
  START_ITERATION: (id: string | number) => `/api/v1/goals/${id}/start-iteration`,
  PAUSE_ITERATION: (id: string | number) => `/api/v1/goals/${id}/pause-iteration`,
  CONVERGE_ITERATION: (id: string | number) => `/api/v1/goals/${id}/converge-iteration`,
  ITERATE: (id: string | number) => `/api/v1/goals/${id}/iterate`,
  GET_ITERATION_STATUS: (id: string | number) => `/api/v1/goals/${id}/iteration-status`,
  GET_ITERATIONS: (id: string | number) => `/api/v1/goals/${id}/iterations`,
  ITERATION_ANALYSIS: (id: string | number, iterId: string | number) => `/api/v1/goals/${id}/iterations/${iterId}/analysis`,
  ITERATION_CONSENSUS: (id: string | number, iterId: string | number) => `/api/v1/goals/${id}/iterations/${iterId}/consensus`,
  ITERATION_DISCUSS: (id: string | number, iterId: string | number) => `/api/v1/goals/${id}/iterations/${iterId}/discuss`,
  AUTO_ASSIGN: (id: string | number) => `/api/v1/goals/${id}/auto-assign`,
  ACTIVATE: (id: string | number) => `/api/v1/goals/${id}/activate`,
  PAUSE: (id: string | number) => `/api/v1/goals/${id}/pause`,
  RESUME: (id: string | number) => `/api/v1/goals/${id}/resume`,
  GET_TREE: (id: string | number) => `/api/v1/goals/${id}/tree`,
  // Sprint 6: Verification reports
  GET_VERIFICATION_REPORTS: (id: string | number) => `/api/v1/goals/${id}/verification-reports`,
  CREATE_REMEDIAL_TASK: (id: string | number) => `/api/v1/goals/${id}/remedial-tasks`,
  // HITL
  GET_PENDING_QUESTIONS: (id: string | number) => `/api/v1/goals/${id}/pending-questions`,
  SUBMIT_ANSWERS: (id: string | number) => `/api/v1/goals/${id}/submit-answers`,
  // Evaluation decompose
  EVALUATE_DECOMPOSE: (id: string | number) => `/api/v1/goals/${id}/evaluate-decompose`,
  // Workspace
  WORKSPACE_CLONE: (id: string | number) => `/api/v1/goals/${id}/workspace/clone`,
  WORKSPACE_PULL: (id: string | number) => `/api/v1/goals/${id}/workspace/pull`,
  WORKSPACE_PUSH: (id: string | number) => `/api/v1/goals/${id}/workspace/push`,
  WORKSPACE_STATUS: (id: string | number) => `/api/v1/goals/${id}/workspace/status`,
} as const

// Projects
export const PROJECTS = {
  LIST: '/api/v1/projects',
  GET: (id: string | number) => `/api/v1/projects/${id}`,
  CREATE: '/api/v1/projects',
  UPDATE: (id: string | number) => `/api/v1/projects/${id}`,
  REMOVE: (id: string | number) => `/api/v1/projects/${id}`,
  PAUSE: (id: string | number) => `/api/v1/projects/${id}/pause`,
  RESUME: (id: string | number) => `/api/v1/projects/${id}/resume`,
  GET_DIAGRAM: (id: string | number) => `/api/v1/projects/${id}/diagram`,
  GET_TASK_TREE: (id: string | number) => `/api/v1/projects/${id}/task-tree`,
  SET_VERIFIER: (id: string | number) => `/api/v1/projects/${id}/verifier`,
  AUTO_ASSIGN: (id: string | number) => `/api/v1/projects/${id}/auto-assign`,
  UPDATE_STATUS: (id: string | number) => `/api/v1/projects/${id}/status`,
} as const

// Tasks
export const TASKS = {
  LIST: '/api/v1/tasks',
  GET: (id: string) => `/api/v1/tasks/${id}`,
  CREATE: '/api/v1/tasks',
  UPDATE: (id: string) => `/api/v1/tasks/${id}`,
  UPDATE_STATUS: (id: string) => `/api/v1/tasks/${id}/status`,
  REMOVE: (id: string | number) => `/api/v1/tasks/${id}`,
  ASSIGN: (id: string) => `/api/v1/tasks/${id}/assign`,
  COMPLETE: (id: string) => `/api/v1/tasks/${id}/complete`,
  FAIL: (id: string) => `/api/v1/tasks/${id}/fail`,
  RETRY: (id: string) => `/api/v1/tasks/${id}/retry`,
  PAUSE: (id: string) => `/api/v1/tasks/${id}/pause`,
  RESUME: (id: string) => `/api/v1/tasks/${id}/resume`,
  RESTART: (id: string) => `/api/v1/tasks/${id}/restart`,
  BLOCK: (id: string) => `/api/v1/tasks/${id}/block`,
  UNBLOCK: (id: string) => `/api/v1/tasks/${id}/unblock`,
  TERMINATE: (id: string) => `/api/v1/tasks/${id}/terminate`,
  TAKEOVER: (id: string) => `/api/v1/tasks/${id}/takeover`,
  GET_STATUSES: '/api/v1/tasks/statuses',
  BATCH_UPDATE: '/api/v1/tasks/batch',
  // Subtasks
  GET_SUBTASKS: (id: string) => `/api/v1/tasks/${id}/subtasks`,
  GET_PARENT: (id: string) => `/api/v1/tasks/${id}/parent`,
  // Comments
  GET_COMMENTS: (id: string) => `/api/v1/tasks/${id}/comments`,
  ADD_COMMENT: (id: string) => `/api/v1/tasks/${id}/comments`,
  DELETE_COMMENT: (id: string, commentId: string) => `/api/v1/tasks/${id}/comments/${commentId}`,
  // Labels
  GET_LABELS: (id: string) => `/api/v1/tasks/${id}/labels`,
  ADD_LABEL: (id: string) => `/api/v1/tasks/${id}/labels`,
  DELETE_LABEL: (id: string, labelId: string) => `/api/v1/tasks/${id}/labels/${labelId}`,
  GET_ALL_LABELS: '/api/v1/tasks/labels/all',
  // Sub-issues
  GET_SUB_ISSUES: (id: string) => `/api/v1/tasks/${id}/sub-issues`,
  ADD_SUB_ISSUE: (id: string) => `/api/v1/tasks/${id}/sub-issues`,
  DELETE_SUB_ISSUE: (id: string, relationId: string) => `/api/v1/tasks/${id}/sub-issues/${relationId}`,
  // Execution
  GET_FAILURE_LOG: (id: string) => `/api/v1/tasks/${id}/failure-log`,
  GET_EXECUTION_LOGS: (id: string) => `/api/v1/tasks/${id}/execution-logs`,
  UPDATE_PROGRESS: (id: string) => `/api/v1/tasks/${id}/progress`,
  // Verification
  GET_VERIFICATIONS: (id: string) => `/api/v1/tasks/${id}/verifications`,
  VERIFY: (id: string) => `/api/v1/tasks/${id}/verify`,
  REVIEW: (id: string) => `/api/v1/tasks/${id}/review`,
  RULING: (id: string) => `/api/v1/tasks/${id}/ruling`,
  GET_VERIFIER: (id: string) => `/api/v1/tasks/${id}/verifier`,
  SET_VERIFIER: (id: string) => `/api/v1/tasks/${id}/verifier`,
  // Context
  GET_CONTEXT: (id: string) => `/api/v1/tasks/${id}/context`,
  // HITL
  ADD_HITL: (id: string) => `/api/v1/tasks/${id}/add-hitl`,
  // Activity
  GET_ACTIVITY: (id: string) => `/api/v1/tasks/${id}/activity`,
} as const

// Scenarios
export const SCENARIOS = {
  LIST: '/api/v1/scenarios',
  GET: (id: string) => `/api/v1/scenarios/${id}`,
  CREATE: '/api/v1/scenarios',
  UPDATE: (id: string) => `/api/v1/scenarios/${id}`,
  REMOVE: (id: string) => `/api/v1/scenarios/${id}`,
  GET_STATUS: (id: string) => `/api/v1/scenarios/${id}/status`,
  UPDATE_STATUS: (id: string) => `/api/v1/scenarios/${id}/status`,
  REVIEW: (id: string) => `/api/v1/scenarios/${id}/review`,
  ADD_PROJECT: (id: string) => `/api/v1/scenarios/${id}/projects`,
  UPDATE_PROJECT: (id: string, projectId: string) => `/api/v1/scenarios/${id}/projects/${projectId}`,
  REMOVE_PROJECT: (id: string, projectId: string) => `/api/v1/scenarios/${id}/projects/${projectId}`,
  ADD_TASK: (id: string) => `/api/v1/scenarios/${id}/tasks`,
  UPDATE_TASK: (id: string, taskId: string) => `/api/v1/scenarios/${id}/tasks/${taskId}`,
  REMOVE_TASK: (id: string, taskId: string) => `/api/v1/scenarios/${id}/tasks/${taskId}`,
  GET_FULLSET: (id: string) => `/api/v1/scenarios/${id}/fullset`,
  UPDATE_FULLSET: (id: string) => `/api/v1/scenarios/${id}/fullset`,
  CUSTOM_CREATE: '/api/v1/scenarios/custom-create',
  DERIVE_FROM_EXECUTION: (goalId: string) => `/api/v1/scenarios/from-execution/${goalId}`,
  DERIVE_FROM_PROJECT_EXECUTION: (projectId: string) => `/api/v1/scenarios/from-execution/project/${projectId}`,
  GET_VERSIONS: (id: string) => `/api/v1/scenarios/${id}/versions`,
  FEEDBACK: (id: string) => `/api/v1/scenarios/${id}/feedback`,
  CREATE_FOR_GOAL: (goalId: string) => `/api/v1/scenarios/create-for-goal/${goalId}`,
  MATCH_FOR_GOAL: (goalId: string) => `/api/v1/scenarios/match-for-goal/${goalId}`,
  MATCH_PREVIEW: `/api/v1/scenarios/match-preview`,
  INSTANTIATE_TO_GOAL: (id: string) => `/api/v1/scenarios/${id}/instantiate-to-goal`,
  PREVIEW: (id: string) => `/api/v1/scenarios/${id}/preview`,
  DERIVE_FROM_COGNITIONS: '/api/v1/scenarios/derive-from-cognitions',
  DERIVE_FROM_COGNITIONS_CONFIRM: '/api/v1/scenarios/derive-from-cognitions/confirm',
  // Emergency (垂直领域，待删除)
  EMERGENCY_COMMAND_CENTER: `/api/v1/emergency/command-center`,
  EMERGENCY_STARTUP: `/api/v1/emergency/startup`,
} as const

// Workflows
export const WORKFLOWS = {
  LIST: `/api/v1/workflows`,
  GET: (id: string) => `/api/v1/workflows/${id}`,
  ACTIVATE: (id: string) => `/api/v1/workflows/${id}/activate`,
  GET_PROGRESS: (id: string) => `/api/v1/workflows/${id}/progress`,
  GET_DIAGRAM: (id: string) => `/api/v1/workflows/${id}/diagram`,
  CONFIRM_AND_SPLIT: (id: string) => `/api/v1/workflows/${id}/confirm-and-split`,
  // DAG
  UPDATE_DAG: (id: string) => `/api/v1/workflows/${id}/dag`,
  ADD_NODE: (id: string) => `/api/v1/workflows/${id}/dag/nodes`,
  UPDATE_NODE: (id: string, nodeId: string) => `/api/v1/workflows/${id}/dag/nodes/${nodeId}`,
  DELETE_NODE: (id: string, nodeId: string) => `/api/v1/workflows/${id}/dag/nodes/${nodeId}`,
  ADD_EDGE: (id: string) => `/api/v1/workflows/${id}/dag/edges`,
  DELETE_EDGE: (id: string, source: string, target: string) => `/api/v1/workflows/${id}/dag/edges/${source}/${target}`,
  REORDER: (id: string) => `/api/v1/workflows/${id}/dag/reorder`,
  // DAG Chat
  CONVERSE: (id: string) => `/api/v1/workflows/${id}/dag/converse`,
  GET_CONVERSATION_HISTORY: (id: string) => `/api/v1/workflows/${id}/dag/conversation/history`,
  RESET_CONVERSATION: (id: string) => `/api/v1/workflows/${id}/dag/conversation/reset`,
} as const

// ==================== 2. 调度与执行引擎 ====================

export const SCHEDULER = {
  STATS: `/api/v1/scheduler/stats`,
  AGENTS_HEALTH: `/api/v1/scheduler/agents/health`,
  LOGS: `/api/v1/scheduler/logs`,
  TICK: `/api/v1/scheduler/tick`,
  DEPENDENCIES_UNLOCK: `/api/v1/scheduler/dependencies/unlock`,
} as const

export const TIMEOUT = {
  CHECK: `/api/v1/timeout/check`,
  CONFIG: `/api/v1/timeout/config`,
  CHECK_TASK: (taskId: string) => `/api/v1/timeout/check-task/${taskId}`,
} as const

export const TRACES = {
  LIST: `/api/v1/traces`,
  CREATE: `/api/v1/traces`,
  GET: (taskId: string) => `/api/v1/traces/${taskId}`,
  COMPLETE: (taskId: string) => `/api/v1/traces/${taskId}/complete`,
  GET_REPORT: (taskId: string) => `/api/v1/reports/${taskId}`,
  GET_STEP_STATUS: (taskId: string) => `/api/v1/traces/${taskId}/step-status`,
  GET_EXECUTION_LOGS: (taskId: string) => `/api/v1/traces/${taskId}/execution-logs`,
} as const

// ==================== 3. 智能匹配（含能力标签） ====================

export const AGENTS = {
  LIST: '/api/v1/agents',
  ONLINE: '/api/v1/agents/online',
  GET: (id: string) => `/api/v1/agents/${id}`,
  CREATE: '/api/v1/agents',
  REMOVE: (id: string) => `/api/v1/agents/${id}`,
  HEARTBEAT: (id: string) => `/api/v1/agents/${id}/heartbeat`,
  HEARTBEAT_LOGS: (id: string) => `/api/v1/agents/${id}/heartbeat_logs`,
  GET_LOAD: (id: string) => `/api/v1/agents/${id}/load`,
  UPDATE_CONFIG: (id: string) => `/api/v1/agents/${id}/config`,
  UPDATE_TRIGGER_MODE: (id: string) => `/api/v1/agents/${id}/trigger_mode`,
  GET_EXECUTION_LOGS: (id: string) => `/api/v1/agents/${id}/execution-logs`,
  GET_PENDING_TASKS: (id: string) => `/api/v1/agents/${id}/pending-tasks`,
  // Discovery
  DISCOVER: '/api/v1/discover',
  DISCOVER_BY_ID: (id: string) => `/api/v1/discover/${id}`,
} as const

export const AGENT_PLATFORMS = {
  LIST: '/api/v1/agent-platforms',
  SCHEMA: (type: string) => `/api/v1/agent-platforms/${type}/registration-schema`,
} as const

export const AGENT_MATCHING = {
  MATCH: `/api/v1/agent-matching/match`,
  GET_TRUST_LEVELS: (scenarioId: string) => `/api/v1/agent-matching/trust-levels/${scenarioId}`,
  UPDATE_TRUST_LEVELS: `/api/v1/agent-matching/trust-levels/update`,
  MATCH_MCP: (agentId: string) => `/api/v1/agents/${agentId}/match-mcp`,
} as const

export const CAPABILITIES = {
  LIST: `/api/v1/capabilities`,
  SEED: `/api/v1/capabilities/seed`,
} as const

export const INDUSTRY_TAGS = {
  LIST: `/api/v1/industry-tags`,
  GET: (tagId: string) => `/api/v1/industry-tags/${tagId}`,
  CREATE: `/api/v1/industry-tags`,
  UPDATE: (tagId: string) => `/api/v1/industry-tags/${tagId}`,
  REMOVE: (tagId: string) => `/api/v1/industry-tags/${tagId}`,
  GET_REFERENCES: (tagId: string) => `/api/v1/industry-tags/${tagId}/references`,
  GET_BY_INDUSTRY: (industry: string) => `/api/v1/industry-tags/_by-industry/${industry}`,
  GET_INDUSTRIES: `/api/v1/industry-tags/_industries`,
  GET_STATS: `/api/v1/industry-tags/_stats`,
  AGENT_TAGS: `/api/v1/industry-tags/agent-tags`,
  AGENT_TAG_RECOMMEND: `/api/v1/industry-tags/agent-tag-recommend`,
} as const

export const INDUSTRY_PACKS = {
  LIST: `/api/v1/industry-packs`,
  GET: (packId: string) => `/api/v1/industry-packs/${packId}`,
  CREATE: `/api/v1/industry-packs`,
  UPDATE: (packId: string) => `/api/v1/industry-packs/${packId}`,
  REMOVE: (packId: string) => `/api/v1/industry-packs/${packId}`,
  ADD_CONTENT: (packId: string) => `/api/v1/industry-packs/${packId}/contents`,
  REMOVE_CONTENT: (packId: string, contentType: string, contentId: string) => `/api/v1/industry-packs/${packId}/contents/${contentType}/${contentId}`,
  VERSIONS: (packId: string) => `/api/v1/industry-packs/${packId}/versions`,
  EXPORT: (packId: string) => `/api/v1/industry-packs/${packId}/export`,
  IMPORT: `/api/v1/industry-packs/import`,
  DIFF: (packA: string, packB: string) => `/api/v1/industry-packs/${packA}/diff/${packB}`,
  VALIDATE: (packId: string) => `/api/v1/industry-packs/${packId}/validate`,
} as const

// Removed: PROMPT_TEMPLATES, SOPS, CHECKLISTS, REFERENCE_DATA (orphaned APIs)

// ==================== 4. 人机协同（含争议仲裁） ====================

export const HUMAN_INPUT = {
  LIST_PENDING: `/api/v1/human-input/pending`,
  GET: (id: string) => `/api/v1/human-input/${id}`,
  GET_BY_TASK: (taskId: string) => `/api/v1/human-input/task/${taskId}`,
  GET_BY_SCENARIO: (scenarioId: string) => `/api/v1/human-input/scenario/${scenarioId}/pending`,
  GET_RECENT: `/api/v1/human-input/recent`,
  SUBMIT: (id: string) => `/api/v1/human-input/${id}/submit`,
  REJECT: (id: string) => `/api/v1/human-input/${id}/reject`,
  GET_STATS: `/api/v1/human-input/stats`,
  GET_REVIEW_STATS: `/api/v1/human-input/review-stats`,
  GET_ANALYTICS: (days: number) => `/api/v1/human-input/analytics?days=${days}`,
} as const

export const HUMAN_REVIEW = {
  LIST_PENDING: `/api/v1/human-review/pending`,
  GET_STATS: `/api/v1/human-review/stats`,
  BATCH_RULING: `/api/v1/human-review/batch-ruling`,
} as const

export const DISPUTES = {
  LIST: `/api/v1/disputes`,
  GET: (id: string) => `/api/v1/disputes/${id}`,
  CREATE: `/api/v1/disputes`,
  RESOLVE: (id: string) => `/api/v1/disputes/${id}/resolve`,
  ARBITRATE: (id: string) => `/api/v1/disputes/${id}/arbitrate`,
  DISCUSS: (id: string) => `/api/v1/disputes/${id}/discuss`,
  GET_DETAIL: (id: string) => `/api/v1/disputes/${id}/detail`,
  GET_TIMELINE: (id: string) => `/api/v1/disputes/${id}/timeline`,
  UPDATE_STATUS: (id: string) => `/api/v1/disputes/${id}/status`,
  GET_STATS: `/api/v1/disputes/stats`,
} as const

export const SOLUTIONS = {
  LIST: '/api/v1/solutions',
  GET: (id: string) => `/api/v1/solutions/${id}`,
  CREATE: '/api/v1/solutions',
  UPDATE: (id: string) => `/api/v1/solutions/${id}`,
  REMOVE: (id: string) => `/api/v1/solutions/${id}`,
  COMPARE: '/api/v1/solutions/compare',
  COMPARE_MULTI: '/api/v1/solutions/compare/multi',
  TREND: '/api/v1/solutions/trend',
  // Iterations
  GET_ITERATIONS: (goalId: string) => `/api/v1/goals/${goalId}/iterations`,
  ITERATION_ANALYSIS: (goalId: string, iterId: string) => `/api/v1/goals/${goalId}/iterations/${iterId}/analysis`,
  ITERATION_DISCUSS: (goalId: string, iterId: string) => `/api/v1/goals/${goalId}/iterations/${iterId}/discuss`,
  CONSENSUS: (goalId: string, iterId: string) => `/api/v1/goals/${goalId}/iterations/${iterId}/consensus`,
} as const

// ==================== 5. 认知引擎（Grasp） ====================

export const GRASP = {
  COGNITION_ASSESSMENT: (agentId: string) => `/api/v1/grasp/cognition-assessment/${agentId}`,
  RECOMMEND: '/api/v1/grasp/recommend',
  COGNITION_LIST: '/api/v1/grasp/cognition',
  COGNITION_GET: (id: string) => `/api/v1/grasp/cognition/${id}`,
  COGNITION_CREATE: '/api/v1/grasp/cognition',
  COGNITION_UPDATE: (id: string) => `/api/v1/grasp/cognition/${id}`,
  COGNITION_REMOVE: (id: string) => `/api/v1/grasp/cognition/${id}`,
  KNOWLEDGE_GRAPH: '/api/v1/grasp/graph',
  KNOWLEDGE_LIST: '/api/v1/grasp/knowledge',
  // Injection
  INJECT_RULES: `/api/v1/grasp/inject/rules`,
  INJECT_RULE: (ruleId: string) => `/api/v1/grasp/inject/rules/${ruleId}`,
  INJECT_STATUS: `/api/v1/grasp/inject/status`,
} as const

export const CONTEXT = {
  GET: (entity: string, entityId: string) => `/api/v1/context/${entity}/${entityId}`,
  UPDATE: (entity: string, entityId: string) => `/api/v1/context/${entity}/${entityId}`,
} as const

export const KNOWLEDGE_INJECTOR = {
  TASK_RESULT: '/api/v1/knowledge-injector/task-result',
  WORKFLOW_RESULT: '/api/v1/knowledge-injector/workflow-result',
  DISPUTE_RESULT: '/api/v1/knowledge-injector/dispute-result',
  STATUS: '/api/v1/knowledge-injector/status',
} as const

// Sprint 75 Phase 2: 知识库
export const KNOWLEDGE = {
  LIST: '/api/v1/knowledge',
  GET: (id: string) => `/api/v1/knowledge/${id}`,
  CREATE: '/api/v1/knowledge',
  UPDATE: (id: string) => `/api/v1/knowledge/${id}`,
  REMOVE: (id: string) => `/api/v1/knowledge/${id}`,
} as const

// Sprint 75 Phase 3: Agent方案
export const AGENT_SCHEMES = {
  LIST: '/api/v1/agent-schemes',
  GET: (id: string) => `/api/v1/agent-schemes/${id}`,
  CREATE: '/api/v1/agent-schemes',
  UPDATE: (id: string) => `/api/v1/agent-schemes/${id}`,
  REMOVE: (id: string) => `/api/v1/agent-schemes/${id}`,
  LIST_ROLES: (schemeId: string) => `/api/v1/agent-schemes/${schemeId}/roles`,
  CREATE_ROLE: (schemeId: string) => `/api/v1/agent-schemes/${schemeId}/roles`,
  REMOVE_ROLE: (schemeId: string, roleId: string) => `/api/v1/agent-schemes/${schemeId}/roles/${roleId}`,
} as const

// ==================== 6. 系统扩展 ====================

export const MCP_SERVERS = {
  LIST: `/api/v1/mcp-servers`,
  GET: (id: string) => `/api/v1/mcp-servers/${id}`,
  CREATE: `/api/v1/mcp-servers`,
  UPDATE: (id: string) => `/api/v1/mcp-servers/${id}`,
  REMOVE: (id: string) => `/api/v1/mcp-servers/${id}`,
  GET_TOOLS: (id: string) => `/api/v1/mcp-servers/${id}/tools`,
  LIST_ALL: `/api/v1/mcp`,
} as const

export const SKILLS = {
  LIST: `/api/v1/skills`,
  GET: (id: string) => `/api/v1/skills/${id}`,
  GET_FILES: (id: string) => `/api/v1/skills/${id}/files`,
  GET_INSTALL_PROMPT: (id: string) => `/api/v1/skills/${id}/install-prompt`,
  GET_RAW: (id: string, filename: string) => `/api/v1/skills/${id}/raw/${filename}`,
} as const

// Sprint 116: Pack Skills (DB-backed industry pack skills)
export const PACK_SKILLS = {
  LIST: `/api/v1/pack-skills`,
  LIST_BY_PACK: (packId: string) => `/api/v1/pack-skills?pack_id=${packId}`,
  BY_PACK: (packId: string) => `/api/v1/pack-skills/by-pack/${packId}`,
  GET: (id: string) => `/api/v1/pack-skills/${id}`,
} as const

export const ATTACHMENTS = {
  UPLOAD: `/api/v1/attachments/upload`,
  LIST: `/api/v1/attachments`,
  GET: (id: string) => `/api/v1/attachments/${id}`,
  DOWNLOAD: (id: string) => `/api/v1/attachments/${id}/download`,
  REMOVE: (id: string) => `/api/v1/attachments/${id}`,
  LINK: (id: string) => `/api/v1/attachments/${id}/link`,
  UNLINK: (id: string, entityType: string, entityId: string) => `/api/v1/attachments/${id}/link/${entityType}/${entityId}`,
} as const

export const ARTIFACTS = {
  LIST: `/api/v1/artifacts`,
  GET: (id: string) => `/api/v1/artifacts/${id}`,
  DOWNLOAD: (id: string) => `/api/v1/artifacts/${id}/download`,
  CREATE: `/api/v1/artifacts`,
  UPDATE: (id: string) => `/api/v1/artifacts/${id}`,
  REMOVE: (id: string) => `/api/v1/artifacts/${id}`,
} as const

export const REPORTS = {
  GET: (workflowId: string) => `/api/v1/reports/${workflowId}`,
} as const

// ==================== 7. 系统配置 ====================

export const ADMIN = {
  LIST_AGENTS: `/api/v1/admin/agents`,
  REREGISTER_AGENT: (agentId: string) => `/api/v1/admin/agents/${agentId}/reregister`,
  SET_AGENT_STATUS: (agentId: string) => `/api/v1/admin/agents/${agentId}/set-status`,
  FORCE_OFFLINE: (agentId: string) => `/api/v1/admin/agents/${agentId}/force-offline`,
  RESTART_AGENT: (agentId: string) => `/api/v1/admin/agents/${agentId}/restart`,
  LIST_TASKS: `/api/v1/admin/tasks`,
  RESET_TASK: (taskId: string) => `/api/v1/admin/tasks/${taskId}/reset`,
  CLEANUP_ZOMBIE_TASKS: `/api/v1/admin/cleanup/zombie-tasks`,
} as const

export const SETTINGS = {
  LIST: '/api/v1/settings',
  GET: (category: string) => `/api/v1/settings/${category}`,
  GET_KEY: (category: string, key: string) => `/api/v1/settings/${category}/${key}`,
  UPDATE_KEY: (category: string, key: string) => `/api/v1/settings/${category}/${key}`,
  BATCH_UPDATE: (category: string) => `/api/v1/settings/${category}/batch`,
  TEST_CONNECTION: '/api/v1/settings/test-connection',
  LIST_MODELS: '/api/v1/settings/models',
  LIST_SESSIONS: '/api/v1/settings/sessions',
} as const

export const SECURITY = {
  AUDIT_LOGS: `/api/v1/audit/logs`,
  ALERTS: `/api/v1/alerts`,
  CREATE_ALERT: `/api/v1/alerts`,
  GET_ALERT: (id: string) => `/api/v1/alerts/${id}`,
  UPDATE_ALERT: (id: string) => `/api/v1/alerts/${id}`,
  REMOVE_ALERT: (id: string) => `/api/v1/alerts/${id}`,
  SECURITY_ALERTS: `/api/v1/security/alerts`,
  SECURITY_AUDIT_LOGS: `/api/v1/security/audit/logs`,
} as const

export const DASHBOARD = {
  STATS: `/api/v1/dashboard/stats`,
} as const

export const SEARCH = {
  GLOBAL: `/api/v1/search`,
} as const

export const API_DOCS = {
  ENDPOINTS: '/api/v1/endpoints',
  STATUS: '/api/v1/status',
  FEATURES: '/api/v1/features',
} as const

// ==================== 评估分解（Evaluation Decompose） ====================
export const EVALUATION_DECOMPOSE = {
  START: '/evaluation-decompose/start',
  E2: (sessionId: string) => `/evaluation-decompose/e2`,
  E3: (sessionId: string) => `/evaluation-decompose/e3`,
  E4: (sessionId: string) => `/evaluation-decompose/e4`,
  STATUS: (sessionId: string) => `/evaluation-decompose/status/${sessionId}`,
  QUESTIONS: (sessionId: string) => `/evaluation-decompose/questions/${sessionId}`,
} as const

// ==================== 辅助：事件流 ====================
export const EVENTS = {
  STREAM: `/api/v1/events/stream`,
  PULL: (id: string) => `/api/v1/events/pull?${id}`,
} as const
