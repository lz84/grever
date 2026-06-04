/**
 * 统一状态映射中心
 * 
 * 所有页面状态映射只在此文件定义，其他页面统一引用。
 * 新增状态值时只需修改此文件，所有页面自动获得一致的中文映射。
 * 
 * 状态分类原则（详见 DEV-GUIDE.md §状态管理规范）：
 *   - DB_STATUS：持久化到数据库的状态，是唯一真实数据源
 *   - WORKFLOW_STATUS：内存/工作流中间状态，不写 DB，只在前端展示
 * 
 * 使用方式：
 *   import { TASK_STATUS, getTaskStatusText, getTaskStatusBadgeClass } from '../utils/statusMap'
 */

// ─────────────────────────────────────────────────────────────────────────────
// Task 状态
// ─────────────────────────────────────────────────────────────────────────────

export const TASK_STATUS_LABELS: Record<string, string> = {
  // 基础状态
  'todo':         '待处理',
  'pending':       '待处理',
  'backlog':       '待处理',
  'in_progress':   '进行中',
  'in_progress%':  '进行中',  // URL 编码兼容
  'active':        '进行中',
  'in_review':     '审核中',
  'done':          '已完成',
  'completed':     '已完成',
  'cancelled':     '已取消',
  'canceled':      '已取消',
  // 特殊状态
  'review_needed': '待审核',
  'disputed':      '争议中',
  'blocked':       '阻塞中',
  'paused':        '已暂停',
  'waiting':       '等待前置',
  'timeout':       '已超时',
  'failed':        '失败',
}

// ─────────────────────────────────────────────────────────────────────────────
// Task 数据库状态（唯一真实数据源，禁止添加不在此列表的状态）
// 此列表 = 与数据库 tasks.status 字段一一对应
// 所有模块必须只写这些状态到 DB
// ─────────────────────────────────────────────────────────────────────────────
export const TASK_DB_STATUSES = ['todo', 'in_progress', 'done', 'failed', 'timeout'] as const
export type TaskDBStatus = typeof TASK_DB_STATUSES[number]

// ─────────────────────────────────────────────────────────────────────────────
// Task 工作流状态（内存/中间状态，不写数据库，仅前端展示）
// ─────────────────────────────────────────────────────────────────────────────
export const TASK_WORKFLOW_STATUSES = [
  'review_needed',  // 待验证
  'verifying',      // 验证中
  'waiting_human',  // 等待人工介入
  'disputed',       // 争议中
  'blocked',        // 阻塞中
  'paused',         // 已暂停
  'waiting',        // 等待前置任务完成
  'in_review',      // 审核中
  'cancelled',      // 已取消（终态，但不写 DB）
] as const

export const TASK_STATUS_BADGE_CLASS: Record<string, string> = {
  'todo':         'bg-slate-100 text-slate-600',
  'pending':      'bg-slate-100 text-slate-600',
  'backlog':      'bg-slate-100 text-slate-600',
  'in_progress':  'bg-blue-100 text-blue-700',
  'in_progress%': 'bg-blue-100 text-blue-700',
  'active':       'bg-blue-100 text-blue-700',
  'in_review':    'bg-purple-100 text-purple-700',
  'done':         'bg-green-100 text-green-700',
  'completed':    'bg-green-100 text-green-700',
  'cancelled':    'bg-slate-100 text-slate-500 line-through',
  'canceled':     'bg-slate-100 text-slate-500 line-through',
  'review_needed':'bg-orange-100 text-orange-700',
  'disputed':     'bg-red-200 text-red-800',
  'blocked':      'bg-amber-100 text-amber-700',
  'paused':       'bg-purple-100 text-purple-700',
  'waiting':      'bg-cyan-100 text-cyan-700',
  'timeout':      'bg-red-100 text-red-700',
  'failed':       'bg-red-100 text-red-700',
}

// ─────────────────────────────────────────────────────────────────────────────
// Goal 状态
// ─────────────────────────────────────────────────────────────────────────────

export const GOAL_STATUS_LABELS: Record<string, string> = {
  'active':      '进行中',
  'in_progress': '进行中',
  'completed':   '已完成',
  'done':        '已完成',
  'planned':     '已计划',
  'draft':       '草稿',
  'cancelled':   '已取消',
  'failed':      '失败',
}

export const GOAL_STATUS_BADGE_CLASS: Record<string, string> = {
  'active':      'bg-blue-100 text-blue-700',
  'in_progress': 'bg-blue-100 text-blue-700',
  'completed':   'bg-green-100 text-green-700',
  'done':        'bg-green-100 text-green-700',
  'planned':     'bg-slate-100 text-slate-600',
  'draft':       'bg-slate-100 text-slate-600',
  'cancelled':   'bg-slate-100 text-slate-500 line-through',
  'failed':      'bg-red-100 text-red-700',
}

// ─────────────────────────────────────────────────────────────────────────────
// Project 状态
// ─────────────────────────────────────────────────────────────────────────────

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  'active':      '进行中',
  'in_progress': '进行中',
  'completed':   '已完成',
  'done':        '已完成',
  'draft':       '草稿',
  'blocked':     '阻塞中',
  'inactive':    '已停止',
  'archived':    '已归档',
  'on_hold':     '暂停中',
}

export const PROJECT_STATUS_BADGE_CLASS: Record<string, string> = {
  'active':      'bg-blue-100 text-blue-700',
  'in_progress': 'bg-blue-100 text-blue-700',
  'completed':   'bg-green-100 text-green-700',
  'done':        'bg-green-100 text-green-700',
  'draft':       'bg-slate-100 text-slate-600',
  'blocked':     'bg-amber-100 text-amber-700',
  'inactive':    'bg-slate-100 text-slate-600',
  'archived':    'bg-slate-100 text-slate-500',
  'on_hold':     'bg-amber-100 text-amber-700',
}

// ─────────────────────────────────────────────────────────────────────────────
// Dispute 状态
// ─────────────────────────────────────────────────────────────────────────────

export const DISPUTE_STATUS_LABELS: Record<string, string> = {
  'open':         '未处理',
  'active':       '处理中',
  'under_review':  '审核中',
  'resolved':     '已解决',
  'appealed':     '已上诉',
  'closed':       '已关闭',
}

export const DISPUTE_SEVERITY_LABELS: Record<string, string> = {
  'open':         '高',
  'active':       '高',
  'under_review':  '中',
  'resolved':      '低',
  'appealed':      '高',
  'closed':        '低',
}

// ─────────────────────────────────────────────────────────────────────────────
// Workflow 状态
// ─────────────────────────────────────────────────────────────────────────────

export const WORKFLOW_STATUS_LABELS: Record<string, string> = {
  'draft':       '草稿',
  'confirmed':   '已确认',
  'in_progress': '执行中',
  'completed':   '已完成',
  'failed':      '失败',
  'cancelled':   '已取消',
}

// ─────────────────────────────────────────────────────────────────────────────
// Agent 状态
// ─────────────────────────────────────────────────────────────────────────────

export const AGENT_STATUS_LABELS: Record<string, string> = {
  'online':  '在线',
  'idle':    '在线',
  'busy':    '繁忙',
  'working': '繁忙',
  'offline': '离线',
  'unknown': '未知',
}

// ─────────────────────────────────────────────────────────────────────────────
// Trace / Execution 状态
// ─────────────────────────────────────────────────────────────────────────────

export const TRACE_STATUS_LABELS: Record<string, string> = {
  'running':  '运行中',
  'success':  '成功',
  'failed':   '失败',
  'waiting':  '等待',
  'pending':  '等待',
  'blocked':  '阻塞',
}

// ─────────────────────────────────────────────────────────────────────────────
// 辅助函数
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 统一获取任务状态中文文本
 * fallback: 返回原始值而非"未知"
 */
export function getTaskStatusText(status: string | null | undefined): string {
  if (!status) return '待处理'
  return TASK_STATUS_LABELS[status] ?? status
}

/**
 * 统一获取任务状态徽章 className
 * fallback: 默认灰底
 */
export function getTaskStatusBadgeClass(status: string | null | undefined): string {
  if (!status) return TASK_STATUS_BADGE_CLASS['todo']
  return TASK_STATUS_BADGE_CLASS[status] ?? 'bg-slate-100 text-slate-600'
}

/**
 * 统一获取目标状态中文文本
 */
export function getGoalStatusText(status: string | null | undefined): string {
  if (!status) return '草稿'
  return GOAL_STATUS_LABELS[status] ?? status
}

/**
 * 统一获取目标状态徽章 className
 */
export function getGoalStatusBadgeClass(status: string | null | undefined): string {
  if (!status) return GOAL_STATUS_BADGE_CLASS['draft']
  return GOAL_STATUS_BADGE_CLASS[status] ?? 'bg-slate-100 text-slate-600'
}

/**
 * 统一获取工程状态中文文本
 */
export function getProjectStatusText(status: string | null | undefined): string {
  if (!status) return '进行中'
  return PROJECT_STATUS_LABELS[status] ?? status
}

/**
 * 统一获取工程状态徽章 className
 */
export function getProjectStatusBadgeClass(status: string | null | undefined): string {
  if (!status) return PROJECT_STATUS_BADGE_CLASS['active']
  return PROJECT_STATUS_BADGE_CLASS[status] ?? 'bg-slate-100 text-slate-600'
}

/**
 * 统一获取目标状态（含文本+徽章样式）
 * 用于 GoalList 等需要 {text, className} 格式的页面
 */
export function getGoalStatusWithClass(status: string | null | undefined): { text: string; className: string } {
  const text = getGoalStatusText(status)
  const badgeClass = getGoalStatusBadgeClass(status)
  return { text, className: badgeClass }
}

/**
 * 统一获取工程状态（含文本+徽章样式）
 */
export function getProjectStatusWithClass(status: string | null | undefined): { text: string; className: string } {
  const text = getProjectStatusText(status)
  const badgeClass = getProjectStatusBadgeClass(status)
  return { text, className: badgeClass }
}

/**
 * 统一获取任务状态（含文本+徽章样式）
 */
export function getTaskStatusWithClass(status: string | null | undefined): { text: string; className: string } {
  return { text: getTaskStatusText(status), className: getTaskStatusBadgeClass(status) }
}

/**
 * 统一获取智能体状态文本
 */
export function getAgentStatusText(status: string | null | undefined): string {
  if (!status) return '离线'
  return AGENT_STATUS_LABELS[status] ?? '离线'
}

/**
 * 统一获取智能体状态圆点颜色 className
 * 接收 raw agent status: online/idle/busy/working/offline
 */
export function getAgentStatusDotClass(status: string | null | undefined): string {
  if (!status) return 'bg-slate-300'
  if (status === 'online' || status === 'idle') return 'bg-green-500'
  if (status === 'busy' || status === 'working') return 'bg-amber-500'
  return 'bg-slate-300'
}

/**
 * 统一获取智能体状态文字颜色 className
 * 接收 raw agent status: online/idle/busy/working/offline
 */
export function getAgentStatusTextClass(status: string | null | undefined): string {
  if (!status) return 'text-slate-400'
  if (status === 'online' || status === 'idle') return 'text-green-600'
  if (status === 'busy' || status === 'working') return 'text-amber-600'
  return 'text-slate-400'
}
