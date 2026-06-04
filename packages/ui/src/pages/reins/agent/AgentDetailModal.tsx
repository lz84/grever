import { useState, useEffect, useCallback } from 'react'
import { INDUSTRY_TAGS } from '../../../shared/api/paths'
import { toast } from "sonner"
import { agentsApi } from '../../../shared/utils/api'
import type { Agent } from '../../../shared/utils/api'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/shared/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Label } from '@/shared/components/ui/label'
import { Loader2, ChevronDown, ChevronRight, Clock, CheckCircle, XCircle, AlertCircle, Save, Settings, Zap, RefreshCw, Activity, ListChecks, Plus, X, Bot, Tag } from 'lucide-react'

function formatDateTime(iso: string): string {
  const d = iso.slice(0, 10)
  const t = iso.slice(11, 16)
  return `${d.slice(5)} ${t}`
}

function formatPayload(val: unknown): string {
  if (typeof val === 'string') {
    try { return JSON.stringify(JSON.parse(val), null, 2) } catch { return val }
  }
  if (typeof val === 'object' && val !== null) {
    return JSON.stringify(val, null, 2)
  }
  return String(val ?? '')
}

interface ExecLog {
  id: string
  task_id: string
  agent_id: string
  action: string
  input: Record<string, any>
  output: Record<string, any>
  status: string
  duration_ms: number
  created_at: string
  error_message?: string
  result_summary?: string
  metadata?: Record<string, any>
}

function getActionLabel(action: string): string {
  const map: Record<string, string> = {
    heartbeat: '心跳',
    task_assign: '任务分配',
    task_execute: '任务执行',
    task_dispatch: '任务派发',
    polling: '轮询',
    sse: 'SSE推送',
    register: '注册',
    heartbeat_success: '心跳成功',
    task_progress: '任务进度',
    task_complete: '任务完成',
    task_failed: '任务失败',
  }
  return map[action] || action
}

function getStatusBadge(status: string) {
  if (status === 'success') return <Badge variant="success" className="text-xs"><CheckCircle className="w-3 h-3 mr-1" />成功</Badge>
  if (status === 'failed') return <Badge variant="destructive" className="text-xs"><XCircle className="w-3 h-3 mr-1" />失败</Badge>
  if (status === 'skipped') return <Badge variant="warning" className="text-xs"><AlertCircle className="w-3 h-3 mr-1" />跳过</Badge>
  return <Badge variant="secondary" className="text-xs">{status}</Badge>
}

function ExecutionLogEntry({ log }: { log: ExecLog }) {
  const [expanded, setExpanded] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const rawJson = {
    id: log.id,
    task_id: log.task_id,
    agent_id: log.agent_id,
    action: log.action,
    input: log.input,
    output: log.output,
    status: log.status,
    duration_ms: log.duration_ms,
    created_at: log.created_at,
    error_message: log.error_message,
    result_summary: log.result_summary,
    metadata: log.metadata,
  }

  const hasRequest = log.input && Object.keys(log.input).length > 0
  const hasResponse = log.output && Object.keys(log.output).length > 0
  const hasError = log.error_message && log.error_message.trim() !== ''
  const hasMetadata = log.metadata && Object.keys(log.metadata).length > 0

  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="flex items-center gap-3 px-3 py-2 hover:bg-slate-50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="text-slate-400 hover:text-slate-600">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <span className="text-xs text-slate-500 font-mono w-[110px] shrink-0">{formatDateTime(log.created_at)}</span>
        <span className={`text-xs font-medium px-1.5 py-0.5 rounded-sm w-20 shrink-0 text-center ${
          log.action === 'task_execute' ? 'bg-purple-50 text-purple-700' :
          log.action === 'task_assign' ? 'bg-blue-50 text-blue-700' :
          log.action === 'task_dispatch' ? 'bg-orange-50 text-orange-700' :
          log.action === 'heartbeat' ? 'bg-green-50 text-green-700' :
          log.action === 'task_complete' ? 'bg-emerald-50 text-emerald-700' :
          log.action === 'task_failed' ? 'bg-red-50 text-red-700' :
          'bg-slate-100 text-slate-700'
        }`}>
          {getActionLabel(log.action)}
        </span>
        {getStatusBadge(log.status)}
        <span className="text-xs text-slate-400 flex items-center gap-1 shrink-0">
          <Clock className="w-3 h-3" />{log.duration_ms}ms
        </span>
        <span className="text-xs text-slate-600 truncate flex-1">
          {log.result_summary || log.error_message || (log.task_id && log.task_id !== '0' ? `任务 ${log.task_id.slice(0, 8)}…` : '—')}
        </span>
        {expanded ? (
          <span className="text-xs text-blue-500 shrink-0">收起</span>
        ) : (
          (hasRequest || hasResponse || hasError) && <span className="text-xs text-slate-400 shrink-0">详情 →</span>
        )}
      </div>
      {expanded && (
        <div className="px-6 py-2 bg-slate-50 border-t border-slate-100 text-xs space-y-3">
          {/* 摘要行 */}
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div><span className="text-slate-500">操作：</span><span className="text-slate-700">{getActionLabel(log.action)}</span></div>
            <div><span className="text-slate-500">耗时：</span><span className="text-slate-700">{log.duration_ms} ms</span></div>
            {log.task_id && log.task_id !== '0' && (
              <div><span className="text-slate-500">任务ID：</span><span className="font-mono text-slate-700">{log.task_id}</span></div>
            )}
            {log.result_summary && <div className="col-span-2"><span className="text-slate-500">摘要：</span><span className="text-slate-700">{log.result_summary}</span></div>}
          </div>

          {/* 错误信息 */}
          {hasError && (
            <div className="bg-red-50 border border-red-200 rounded px-3 py-2">
              <span className="text-red-500 font-medium">✖ 错误：</span>
              <span className="text-red-600">{log.error_message}</span>
            </div>
          )}

          {/* 请求 → */}
          {hasRequest && (
            <div>
              <div className="flex items-center gap-1 mb-1">
                <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px] font-medium">→ 请求</span>
                <span className="text-slate-500 text-[10px]">系统/Worker 发给 Agent 的输入</span>
              </div>
              <pre className="bg-white border border-slate-200 rounded px-3 py-2 overflow-x-auto text-slate-700 leading-relaxed max-h-48">
                {formatPayload(log.input)}
              </pre>
            </div>
          )}

          {/* ← 响应 */}
          {hasResponse && (
            <div>
              <div className="flex items-center gap-1 mb-1">
                <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] font-medium">← 响应</span>
                <span className="text-slate-500 text-[10px]">Agent 返回的处理结果</span>
              </div>
              <pre className="bg-white border border-slate-200 rounded px-3 py-2 overflow-x-auto text-slate-700 leading-relaxed max-h-48">
                {formatPayload(log.output)}
              </pre>
            </div>
          )}

          {/* Metadata */}
          {hasMetadata && (
            <div>
              <div className="flex items-center gap-1 mb-1">
                <span className="bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded text-[10px] font-medium">⚙ Metadata</span>
              </div>
              <pre className="bg-white border border-slate-200 rounded px-3 py-2 overflow-x-auto text-slate-700 leading-relaxed max-h-32">
                {formatPayload(log.metadata)}
              </pre>
            </div>
          )}

          {/* 原始 JSON */}
          <div>
            <button
              onClick={(e) => { e.stopPropagation(); setShowRaw(!showRaw) }}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
            >
              {showRaw ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {showRaw ? '收起原始 JSON' : '查看原始 JSON'}
            </button>
            {showRaw && (
              <pre className="bg-slate-900 text-slate-100 rounded px-3 py-2 mt-2 overflow-x-auto text-xs max-h-64">
                {JSON.stringify(rawJson, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== Heartbeat Log Types ====================

interface HeartbeatLog {
  id: string
  agent_id: string
  timestamp: string
  status: string
  latency_ms: number | null
  load: number | null
  current_tasks: number | null
  metadata?: Record<string, any>
  raw_payload?: string
  request_payload?: string | Record<string, unknown>
  response_payload?: string | Record<string, unknown>
  result_summary?: string
  error_message?: string
  duration_ms?: number
}

function HeartbeatLogEntry({ log }: { log: HeartbeatLog }) {
  const [expanded, setExpanded] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const rawJson = {
    id: log.id,
    agent_id: log.agent_id,
    timestamp: log.timestamp,
    status: log.status,
    latency_ms: log.latency_ms,
    load: log.load,
    current_tasks: log.current_tasks,
    metadata: log.metadata || undefined,
    raw_payload: log.raw_payload || undefined,
    request_payload: log.request_payload || undefined,
    response_payload: log.response_payload || undefined,
    result_summary: log.result_summary || undefined,
    error_message: log.error_message || undefined,
    duration_ms: log.duration_ms || undefined,
  }
  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="flex items-center gap-3 px-3 py-2 hover:bg-slate-50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="text-slate-400 hover:text-slate-600">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <span className="text-xs text-slate-500 font-mono w-[110px] shrink-0">{formatDateTime(log.timestamp)}</span>
        <span className="text-xs font-medium bg-green-50 text-green-700 px-1.5 py-0.5 rounded-sm w-12 shrink-0 text-center">心跳</span>
        <Badge variant={log.status === 'online' ? 'success' : 'secondary'} className="text-xs">{log.status}</Badge>
        <span className="text-xs text-slate-400 flex items-center gap-1 shrink-0">
          延迟: {log.latency_ms ?? '-'}ms
        </span>
        <span className="text-xs text-slate-400 flex items-center gap-1 shrink-0">
          负载: {log.load ?? '-'}%
        </span>
        <span className="text-xs text-slate-400 flex items-center gap-1 shrink-0">
          任务: {log.current_tasks ?? '-'}
        </span>
        {expanded && <span className="text-xs text-blue-500 ml-auto">点击收起</span>}
      </div>
      {expanded && (
        <div className="px-6 py-2 bg-slate-50 border-t border-slate-100 text-xs space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div><span className="text-slate-500">状态：</span><span className="text-slate-700">{log.status}</span></div>
            <div><span className="text-slate-500">延迟：</span><span className="text-slate-700">{log.latency_ms ?? '-'} ms</span></div>
            <div><span className="text-slate-500">负载：</span><span className="text-slate-700">{log.load ?? '-'}%</span></div>
            <div><span className="text-slate-500">当前任务：</span><span className="text-slate-700">{log.current_tasks ?? '-'}</span></div>
            {log.duration_ms && <div><span className="text-slate-500">耗时：</span><span className="text-slate-700">{log.duration_ms} ms</span></div>}
            {log.result_summary && <div className="col-span-2"><span className="text-slate-500">摘要：</span><span className="text-slate-700">{log.result_summary}</span></div>}
          </div>
          {log.request_payload && (
            <div>
              <div className="flex items-center gap-1 mb-1">
                <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px] font-medium">请求 →</span>
                <span className="text-slate-500">系统分配给 Agent 的任务</span>
              </div>
              <pre className="bg-white border border-slate-200 rounded px-3 py-2 overflow-x-auto text-slate-700 leading-relaxed max-h-48">
                {formatPayload(log.request_payload)}
              </pre>
            </div>
          )}
          {log.response_payload && (
            <div>
              <div className="flex items-center gap-1 mb-1">
                <span className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded text-[10px] font-medium">← 回复</span>
                <span className="text-slate-500">Agent 返回的处理结果</span>
              </div>
              <pre className="bg-white border border-slate-200 rounded px-3 py-2 overflow-x-auto text-slate-700 leading-relaxed max-h-48">
                {formatPayload(log.response_payload)}
              </pre>
            </div>
          )}
          {log.error_message && (
            <div><span className="text-red-500">错误：</span><span className="text-red-600">{log.error_message}</span></div>
          )}
          {!log.request_payload && !log.response_payload && log.raw_payload && (
            <div>
              <span className="text-slate-500">原始数据：</span>
              <pre className="bg-slate-900 text-slate-100 rounded px-2 py-2 mt-1 overflow-x-auto text-xs">
                {formatPayload(log.raw_payload)}
              </pre>
            </div>
          )}
          <div>
            <button
              onClick={(e) => { e.stopPropagation(); setShowRaw(!showRaw) }}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
            >
              {showRaw ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {showRaw ? '收起原始 JSON' : '查看原始 JSON'}
            </button>
            {showRaw && (
              <pre className="bg-slate-900 text-slate-100 rounded px-3 py-2 mt-2 overflow-x-auto text-xs max-h-64">
                {JSON.stringify(rawJson, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== Pending Task Type ====================

interface PendingTask {
  id: string
  title?: string
  description?: string
  status?: string
  priority?: number | string
  assigned_at?: string
}

function PendingTaskItem({ task }: { task: PendingTask }) {
  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 last:border-0">
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-slate-700 truncate block">{task.title || task.id}</span>
        {task.description && (
          <span className="text-xs text-slate-400 truncate block">{task.description}</span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-3">
        {task.priority != null && (
          <Badge variant={Number(task.priority) <= 2 ? 'destructive' : 'secondary'} className="text-xs">
            P{task.priority}
          </Badge>
        )}
        <Badge variant="outline" className="text-xs">{task.status || 'pending'}</Badge>
      </div>
    </div>
  )
}

// ==================== Capability Tags Editor ====================

const CAP_DIMENSIONS = [
  { key: 'business', label: '业务能力', color: 'blue' },
  { key: 'professional', label: '专业能力', color: 'purple' },
  { key: 'technical', label: '技术能力', color: 'green' },
  { key: 'management', label: '管理能力', color: 'amber' },
] as const

const COLOR_MAP: Record<string, { bg: string; badge: any }> = {
  blue: { bg: 'bg-blue-50', badge: 'default' },
  purple: { bg: 'bg-purple-50', badge: 'secondary' },
  green: { bg: 'bg-green-50', badge: 'default' },
  amber: { bg: 'bg-amber-50', badge: 'warning' },
}

function CapabilityTagsEditor({ agent, onRefresh }: { agent: Agent; onRefresh: () => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Record<string, string[]>>({})
  const [newTagInput, setNewTagInput] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (editing) {
      setDraft(JSON.parse(JSON.stringify(agent.capability_tags || {})))
      setNewTagInput({})
    }
  }, [editing, agent.capability_tags])

  function addTag(dim: string) {
    const val = (newTagInput[dim] || '').trim()
    if (!val) return
    setDraft(prev => ({
      ...prev,
      [dim]: [...(prev[dim] || []), val],
    }))
    setNewTagInput(prev => ({ ...prev, [dim]: '' }))
  }

  function removeTag(dim: string, index: number) {
    setDraft(prev => ({
      ...prev,
      [dim]: (prev[dim] || []).filter((_, i) => i !== index),
    }))
  }

  async function handleSave() {
    setSaving(true)
    try {
      await agentsApi.updateConfig(agent.id, { capability_tags: draft })
      toast.success('能力标签已更新')
      setEditing(false)
      onRefresh()
    } catch (e: any) {
      toast.error('更新失败: ' + (e.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  if (!editing) {
    const tags = agent.capability_tags || {}
    const allTags = Object.values(tags).flat()
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-slate-700">能力标签</p>
          <Button size="sm" variant="ghost" className="h-6 text-xs px-1" onClick={() => setEditing(true)}>
            ✏️ 编辑
          </Button>
        </div>
        {allTags.length === 0 ? (
          <p className="text-xs text-slate-400">暂无能力标签</p>
        ) : (
          <div className="space-y-2">
            {CAP_DIMENSIONS.map(dim => {
              const items = tags[dim.key] || []
              if (items.length === 0) return null
              const colors = COLOR_MAP[dim.color]
              return (
                <div key={dim.key}>
                  <span className="text-xs text-slate-500 mr-2">{dim.label}:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {items.map((cap, i) => (
                      <Badge key={`${cap}-${i}`} variant={colors.badge as any} className="text-xs">{cap}</Badge>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-700">能力标签编辑</p>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => setEditing(false)} disabled={saving}>取消</Button>
          <Button size="sm" className="h-6 text-xs" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />} 保存
          </Button>
        </div>
      </div>
      {CAP_DIMENSIONS.map(dim => {
        const items = draft[dim.key] || []
        const colors = COLOR_MAP[dim.color]
        return (
          <div key={dim.key} className={`rounded-lg ${colors.bg} p-3`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium text-slate-700">{dim.label}</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {items.length === 0 ? (
                <span className="text-xs text-slate-400">暂无标签</span>
              ) : items.map((cap, i) => (
                <Badge key={`${cap}-${i}`} variant={colors.badge as any} className="text-xs flex items-center gap-1">
                  {cap}
                  <button onClick={() => removeTag(dim.key, i)} className="hover:text-red-500 ml-0.5">
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
            </div>
            <div className="flex gap-1">
              <Input
                className="h-7 text-xs"
                placeholder="输入标签后回车添加"
                value={newTagInput[dim.key] || ''}
                onChange={e => setNewTagInput(prev => ({ ...prev, [dim.key]: e.target.value }))}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(dim.key) } }}
              />
              <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => addTag(dim.key)}>
                <Plus className="w-3 h-3" />
              </Button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ==================== Main Modal ====================

interface AgentDetailModalProps {
  agent: Agent
  onClose: () => void
  onRefresh?: () => void
}

type TabKey = 'config' | 'trigger' | 'heartbeat' | 'load' | 'pending' | 'industry_tags'

export default function AgentDetailModal({ agent, onClose, onRefresh }: AgentDetailModalProps) {
  const [detail, setDetail] = useState<Agent | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Config tab
  const [configMaxTasks, setConfigMaxTasks] = useState<number>(0)
  const [savingConfig, setSavingConfig] = useState(false)

  // Load tab
  const [loadData, setLoadData] = useState<any>(null)
  const [loadingLoad, setLoadingLoad] = useState(false)

  // Pending tasks tab
  const [pendingTasks, setPendingTasks] = useState<PendingTask[]>([])
  const [loadingPending, setLoadingPending] = useState(false)

  // Trigger tab
  const [execLogs, setExecLogs] = useState<ExecLog[]>([])
  const [loadingExecLogs, setLoadingExecLogs] = useState(false)
  const [execLogsPage, setExecLogsPage] = useState(1)
  const [triggerMode, setTriggerMode] = useState<string>('')
  const [savingTrigger, setSavingTrigger] = useState(false)

  // Heartbeat tab
  const [heartbeatLogs, setHeartbeatLogs] = useState<HeartbeatLog[]>([])
  const [loadingHeartbeatLogs, setLoadingHeartbeatLogs] = useState(false)

  // Industry tags tab
  interface IndustryTagInfo { id: string; name: string; dimension: string; source?: string }
  interface AgentTagWithInfo { tagId: string; tagName: string; dimension: string; source: string; lastObserved?: string }
  const [industryTags, setIndustryTags] = useState<AgentTagWithInfo[]>([])
  const [loadingTags, setLoadingTags] = useState(false)
  // Edit dialog state
  const [showTagEdit, setShowTagEdit] = useState(false)
  const [availableTags, setAvailableTags] = useState<{ tag_id: string; tag_name: string; dimension: string }[]>([])
  const [selectedTagIds, setSelectedTagIds] = useState<Set<string>>(new Set())
  const [savingTags, setSavingTags] = useState(false)
  // Tag recommendation dashboard
  interface TagRecommendation { tag_id: string; tag_name: string; dimension: string; score: number; reason: string }
  const [recommendedTags, setRecommendedTags] = useState<TagRecommendation[]>([])
  const [loadingRecommend, setLoadingRecommend] = useState(false)

  const [activeTab, setActiveTab] = useState<TabKey>('config')
  const EXEC_LOG_PAGE_SIZE = 20

  // Fetch agent detail on mount
  useEffect(() => {
    if (!agent?.id) return
    let cancelled = false
    setLoadingDetail(true)
    agentsApi.get(agent.id)
      .then(data => {
        if (!cancelled) {
          setDetail(data)
          setConfigMaxTasks(data.max_concurrent_tasks || 0)
          setTriggerMode(data.trigger_mode || 'polling')
        }
      })
      .catch(e => console.error('fetch agent detail error', e))
      .finally(() => { if (!cancelled) setLoadingDetail(false) })
    return () => { cancelled = true }
  }, [agent?.id])

  // Fetch execution logs for trigger tab
  const fetchExecLogs = useCallback((page: number) => {
    if (!agent?.id) return
    setLoadingExecLogs(true)
    const offset = (page - 1) * EXEC_LOG_PAGE_SIZE
    agentsApi.getExecutionLogs(agent.id, EXEC_LOG_PAGE_SIZE, offset)
      .then(data => {
        const logs = Array.isArray(data) ? data : (data as any).logs || []
        setExecLogs(page === 1 ? logs : prev => [...prev, ...logs])
      })
      .catch(e => console.error('fetch exec logs error', e))
      .finally(() => setLoadingExecLogs(false))
  }, [agent?.id])

  // Fetch heartbeat logs
  const fetchHeartbeatLogs = useCallback(() => {
    if (!agent?.id) return
    setLoadingHeartbeatLogs(true)
    agentsApi.getHeartbeatLogs(agent.id, 50)
      .then(data => {
        const logs = Array.isArray(data) ? data : (data as any).logs || (data as any).heartbeat_logs || []
        setHeartbeatLogs(logs)
      })
      .catch(e => {
        console.error('fetch heartbeat logs error', e)
        setHeartbeatLogs([])
      })
      .finally(() => setLoadingHeartbeatLogs(false))
  }, [agent?.id])

  // Fetch load data
  const fetchLoad = useCallback(() => {
    if (!agent?.id) return
    setLoadingLoad(true)
    agentsApi.getLoad(agent.id)
      .then(data => setLoadData(data))
      .catch(e => {
        console.error('fetch load error', e)
        toast.error('获取负载数据失败')
      })
      .finally(() => setLoadingLoad(false))
  }, [agent?.id])

  // Fetch pending tasks
  const fetchPendingTasks = useCallback(() => {
    if (!agent?.id) return
    setLoadingPending(true)
    agentsApi.getPendingTasks(agent.id)
      .then(data => {
        const tasks = Array.isArray(data) ? data : (data as any).tasks || []
        setPendingTasks(tasks)
      })
      .catch(e => {
        console.error('fetch pending tasks error', e)
        setPendingTasks([])
      })
      .finally(() => setLoadingPending(false))
  }, [agent?.id])

  // Fetch industry tags for the agent
  async function fetchIndustryTags(agentData: Agent) {
    setLoadingTags(true)
    try {
      const res = await fetch(INDUSTRY_TAGS.AGENT_TAGS + `?agent_id=${agentData.id}`)
      if (!res.ok) throw new Error('API error')
      const data = await res.json()
      const results: AgentTagWithInfo[] = [
        ...(data.manual_tags || []).map((t: any) => ({
          tagId: t.tag_id,
          tagName: t.tag_name || t.tag_id,
          dimension: t.dimension || 'professional',
          source: '手动配置' as const,
        })),
        ...(data.inferred_tags || []).map((t: any) => ({
          tagId: t.tag_id,
          tagName: t.tag_name || t.tag_id,
          dimension: t.dimension || 'professional',
          source: '自动推断' as const,
        })),
      ]
      setIndustryTags(results)
    } catch (e) {
      console.error('fetch industry tags error', e)
      setIndustryTags([])
    } finally {
      setLoadingTags(false)
    }
  }

  // Fetch all available industry tags for the multi-select dialog
  async function fetchAvailableTags() {
    try {
      const res = await fetch(INDUSTRY_TAGS.LIST)
      if (res.ok) {
        const data = await res.json()
        const tags: { tag_id: string; tag_name: string; dimension: string }[] = data.items || data.tags || data || []
        setAvailableTags(tags)
      }
    } catch (e) {
      console.error('fetch available tags error', e)
    }
  }

  // Open the tag edit dialog
  function openTagEdit() {
    // Build current selected IDs from industryTags
    const currentIds = new Set(industryTags.map(t => t.tagId))
    setSelectedTagIds(currentIds)
    fetchAvailableTags()
    setShowTagEdit(true)
  }

  // Save selected tags to agent's capability_tags
  async function saveTagSelection() {
    if (!agent?.id) return
    setSavingTags(true)
    try {
      // Build capability_tags object grouped by dimension
      const draft: Record<string, string[]> = {}
      for (const tagId of selectedTagIds) {
        const tag = availableTags.find(t => t.tag_id === tagId)
        if (tag) {
          const dim = tag.dimension || 'professional'
          if (!draft[dim]) draft[dim] = []
          draft[dim].push(tagId)
        }
      }
      await agentsApi.updateConfig(agent.id, { capability_tags: draft })
      toast.success('能力标签已更新')
      setShowTagEdit(false)
      // Refresh
      onRefresh?.()
      if (detail) fetchIndustryTags(detail)
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message || '未知错误'))
    } finally {
      setSavingTags(false)
    }
  }

  function toggleTag(tagId: string) {
    setSelectedTagIds(prev => {
      const next = new Set(prev)
      if (next.has(tagId)) next.delete(tagId)
      else next.add(tagId)
      return next
    })
  }

  // Fetch tag recommendations
  async function fetchTagRecommendations(agentData: Agent) {
    setLoadingRecommend(true)
    try {
      const res = await fetch(INDUSTRY_TAGS.AGENT_TAG_RECOMMEND + `?agent_id=${agentData.id}`)
      if (res.ok) {
        const data = await res.json()
        // API returns {recommended: {dim: [...]}, current: {...}, missing: [...]}
        const currentIds = new Set(industryTags.map(t => t.tagId))
        const recs: TagRecommendation[] = (data.missing || [])
          .filter((tid: string) => !currentIds.has(tid))
          .slice(0, 20)
          .map((tid: string) => ({ tag_id: tid, tag_name: tid, dimension: '', score: 0, reason: '推荐配置' }))
        setRecommendedTags(recs)
      }
    } catch (e) {
      console.error('fetch tag recommendations error', e)
    } finally {
      setLoadingRecommend(false)
    }
  }

  // Lazy-load tab data when tab changes
  useEffect(() => {
    if (activeTab === 'trigger' && execLogs.length === 0) {
      fetchExecLogs(1)
    }
    if (activeTab === 'heartbeat' && heartbeatLogs.length === 0) {
      fetchHeartbeatLogs()
    }
    if (activeTab === 'load' && !loadData) {
      fetchLoad()
    }
    if (activeTab === 'pending' && pendingTasks.length === 0) {
      fetchPendingTasks()
    }
    if (activeTab === 'industry_tags' && detail) {
      if (industryTags.length === 0) fetchIndustryTags(detail)
      if (recommendedTags.length === 0) fetchTagRecommendations(detail)
    }
  }, [activeTab, detail])

  // Handle save config
  async function handleSaveConfig() {
    if (!agent?.id) return
    setSavingConfig(true)
    try {
      await agentsApi.updateConfig(agent.id, { max_concurrent_tasks: configMaxTasks })
      toast.success('配置已更新')
      onRefresh?.()
      // Refresh detail
      const updated = await agentsApi.get(agent.id)
      setDetail(updated)
    } catch (e: any) {
      toast.error('更新配置失败: ' + (e.message || 'unknown'))
    } finally {
      setSavingConfig(false)
    }
  }

  // Handle update trigger mode
  async function handleUpdateTriggerMode(mode: string) {
    if (!agent?.id) return
    setSavingTrigger(true)
    try {
      await agentsApi.updateTriggerMode(agent.id, mode)
      setTriggerMode(mode)
      toast.success(`触发模式已更新为 ${mode === 'polling' ? '轮询' : mode}`)
      onRefresh?.()
    } catch (e: any) {
      toast.error('更新触发模式失败: ' + (e.message || 'unknown'))
    } finally {
      setSavingTrigger(false)
    }
  }

  // Load more execution logs
  function loadMoreExecLogs() {
    const nextPage = execLogsPage + 1
    setExecLogsPage(nextPage)
    fetchExecLogs(nextPage)
  }

  // 触发日志：排除纯心跳噪音，保留派发/执行/完成/失败记录
  const triggerLogs = execLogs.filter(log =>
    !['heartbeat', 'heartbeat_success'].includes(log.action)
  )

  const displayAgent = detail || agent

  return (
    <Dialog open={!!agent} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {displayAgent.name}
            <Badge variant={displayAgent.status === 'online' ? 'success' : displayAgent.status === 'busy' ? 'warning' : 'secondary'}>
              {displayAgent.status}
            </Badge>
            {loadingDetail && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
          </DialogTitle>
          <DialogDescription className="font-mono text-xs">{agent.id}</DialogDescription>
        </DialogHeader>

        {/* Tab bar */}
        <div className="flex items-center gap-1 border-b pb-2">
          {([
            { key: 'config' as TabKey, label: '配置', icon: <Settings className="w-3.5 h-3.5" /> },
            { key: 'trigger' as TabKey, label: '触发日志', icon: <Zap className="w-3.5 h-3.5" /> },
            { key: 'heartbeat' as TabKey, label: '心跳日志', icon: <Activity className="w-3.5 h-3.5" /> },
            { key: 'load' as TabKey, label: '负载', icon: <RefreshCw className="w-3.5 h-3.5" /> },
            { key: 'pending' as TabKey, label: '待处理任务', icon: <ListChecks className="w-3.5 h-3.5" /> },
            { key: 'industry_tags' as TabKey, label: '能力标签', icon: <Tag className="w-3.5 h-3.5" /> },
          ]).map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {icon}
              {label}
              {key === 'heartbeat' && heartbeatLogs.length > 0 && (
                <span className="bg-white/20 px-1.5 py-0.5 rounded-full text-[10px]">{heartbeatLogs.length}</span>
              )}
              {key === 'pending' && pendingTasks.length > 0 && (
                <span className="bg-white/20 px-1.5 py-0.5 rounded-full text-[10px]">{pendingTasks.length}</span>
              )}
            </button>
          ))}
        </div>

        <div className="space-y-4 overflow-y-auto flex-1 pr-1">

          {/* ==================== Config Tab ==================== */}
          {activeTab === 'config' && (
            <div className="space-y-4">
              {/* Basic info */}
              <div className="grid grid-cols-2 gap-2 text-sm bg-slate-50 rounded-lg p-3">
                <div><span className="text-slate-500">Agent ID：</span><span className="font-mono text-xs">{displayAgent.id}</span></div>
                <div><span className="text-slate-500">模型：</span><span className="font-mono text-xs">{displayAgent.model_name || '-'}</span></div>
                <div><span className="text-slate-500">状态：</span><Badge variant={displayAgent.status === 'online' ? 'success' : displayAgent.status === 'busy' ? 'warning' : 'secondary'}>{displayAgent.status}</Badge></div>
                <div><span className="text-slate-500">负载：</span><span>{displayAgent.load}%</span><span className="text-xs text-slate-400 ml-1">（{displayAgent.current_tasks} 个任务）</span></div>
                <div><span className="text-slate-500">触发方式：</span><span>{displayAgent.trigger_mode === 'polling' ? '轮询' : displayAgent.trigger_mode}</span></div>
                <div><span className="text-slate-500">心跳：</span><span className="text-xs">{displayAgent.last_heartbeat}</span></div>
                <div><span className="text-slate-500">地址：</span><span className="font-mono text-xs">{displayAgent.address || '-'}</span></div>
                <div><span className="text-slate-500">注册时间：</span><span className="text-xs">{displayAgent.registered_at}</span></div>
              </div>

              {/* Capabilities (editable) */}
              <CapabilityTagsEditor agent={displayAgent} onRefresh={() => { onRefresh?.(); agentsApi.get(agent.id).then(d => setDetail(d)) }} />

              {/* Update max_concurrent_tasks */}
              <div className="space-y-2">
                <Label htmlFor="maxTasks">最大并发任务数</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="maxTasks"
                    type="number"
                    min={0}
                    value={configMaxTasks}
                    onChange={e => setConfigMaxTasks(Number(e.target.value))}
                    className="w-32"
                  />
                  <Button size="sm" onClick={handleSaveConfig} disabled={savingConfig}>
                    {savingConfig ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    保存
                  </Button>
                </div>
              </div>

              {/* Update trigger mode */}
              <div className="space-y-2">
                <Label>触发模式</Label>
                <div className="flex items-center gap-2">
                  <Select value={triggerMode} onValueChange={handleUpdateTriggerMode} disabled={savingTrigger}>
                    <SelectTrigger className="w-48">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="polling">轮询 (Polling)</SelectItem>
                      <SelectItem value="sse">SSE 推送</SelectItem>
                      <SelectItem value="webhook">Webhook</SelectItem>
                    </SelectContent>
                  </Select>
                  {savingTrigger && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                </div>
              </div>
            </div>
          )}

          {/* ==================== Trigger Logs Tab ==================== */}
          {activeTab === 'trigger' && (
            <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              {loadingExecLogs && execLogs.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : triggerLogs.length === 0 ? (
                <div className="text-center py-6 text-sm text-slate-400">暂无触发日志</div>
              ) : (
                <>
                  {triggerLogs.map(log => (
                    <ExecutionLogEntry key={log.id} log={log} />
                  ))}
                  {execLogs.length >= EXEC_LOG_PAGE_SIZE && triggerLogs.length > 0 && (
                    <div className="flex justify-center py-2 border-t border-slate-100">
                      <Button variant="ghost" size="sm" onClick={loadMoreExecLogs} disabled={loadingExecLogs}>
                        {loadingExecLogs ? <Loader2 className="w-4 h-4 animate-spin" /> : '加载更多'}
                      </Button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ==================== Heartbeat Logs Tab ==================== */}
          {activeTab === 'heartbeat' && (
            <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              {loadingHeartbeatLogs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : heartbeatLogs.length === 0 ? (
                <div className="text-center py-6 text-sm text-slate-400">暂无心跳记录</div>
              ) : (
                heartbeatLogs.map((log) => (
                  <HeartbeatLogEntry key={log.id} log={log} />
                ))
              )}
            </div>
          )}

          {/* ==================== Load Tab ==================== */}
          {activeTab === 'load' && (
            <div className="space-y-3">
              {loadingLoad ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : loadData ? (
                <div className="space-y-3">
                  {/* Current load summary */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-50 rounded-lg p-4 text-center">
                      <p className="text-xs text-slate-500 mb-1">当前负载</p>
                      <p className="text-2xl font-bold text-blue-600">{loadData.load ?? displayAgent.load}%</p>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-4 text-center">
                      <p className="text-xs text-slate-500 mb-1">当前任务数</p>
                      <p className="text-2xl font-bold text-purple-600">{loadData.current_tasks ?? displayAgent.current_tasks}</p>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-4 text-center">
                      <p className="text-xs text-slate-500 mb-1">最大并发</p>
                      <p className="text-2xl font-bold text-green-600">{loadData.max_concurrent_tasks ?? displayAgent.max_concurrent_tasks ?? '-'}</p>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-4 text-center">
                      <p className="text-xs text-slate-500 mb-1">可用槽位</p>
                      <p className="text-2xl font-bold text-orange-600">
                        {loadData.available_slots != null
                          ? loadData.available_slots
                          : ((loadData.max_concurrent_tasks ?? displayAgent.max_concurrent_tasks ?? 0) - (loadData.current_tasks ?? displayAgent.current_tasks))}
                      </p>
                    </div>
                  </div>

                  {/* Additional load details */}
                  {typeof loadData === 'object' && Object.keys(loadData).length > 0 && (
                    <div className="bg-slate-50 rounded-lg p-3">
                      <p className="text-xs text-slate-500 mb-2">详细负载信息</p>
                      <pre className="text-xs text-slate-700 bg-white border border-slate-200 rounded px-3 py-2 overflow-x-auto">
                        {JSON.stringify(loadData, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6 text-sm text-slate-400">暂无负载数据</div>
              )}
            </div>
          )}

          {/* ==================== Pending Tasks Tab ==================== */}
          {activeTab === 'pending' && (
            <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              {loadingPending ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : pendingTasks.length === 0 ? (
                <div className="text-center py-6 text-sm text-slate-400">暂无待处理任务</div>
              ) : (
                pendingTasks.map(task => (
                  <PendingTaskItem key={task.id} task={task} />
                ))
              )}
            </div>
          )}

          {/* ==================== Industry Tags Tab ==================== */}
          {activeTab === 'industry_tags' && (
            <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              {loadingTags && industryTags.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : (
                <div>
                  {/* Header */}
                  <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 bg-slate-50">
                    <span className="text-xs text-slate-500">标签画像 Dashboard</span>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={openTagEdit}>
                      ✏️ 编辑标签
                    </Button>
                  </div>

                  <div className="p-4 space-y-4">
                    {/* Current tags */}
                    <div>
                      <h4 className="text-xs font-semibold text-green-700 mb-2 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-500" />当前标签 ({industryTags.length})
                      </h4>
                      {industryTags.length === 0 ? (
                        <p className="text-xs text-slate-400 pl-3">暂无标签，点击编辑添加</p>
                      ) : (
                        <div className="pl-3 space-y-1">
                          {industryTags.map((tag, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-sm">
                              <span className="font-medium">{tag.tagName}</span>
                              <Badge variant="outline" className="text-[10px]">{tag.dimension}</Badge>
                              <span className="text-xs text-slate-400">{tag.source}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Recommended tags */}
                    <div className="border-t border-slate-100 pt-3">
                      <h4 className="text-xs font-semibold text-blue-700 mb-2 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-500" />推荐标签 ({recommendedTags.length})
                        {loadingRecommend && <Loader2 className="w-3 h-3 animate-spin ml-1" />}
                      </h4>
                      {recommendedTags.length === 0 ? (
                        <p className="text-xs text-slate-400 pl-3">暂无推荐</p>
                      ) : (
                        <div className="pl-3 space-y-1">
                          {recommendedTags.map((tag, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-sm border border-dashed border-blue-200 bg-blue-50/50 rounded px-2 py-1">
                              <span className="font-medium">{tag.tag_name}</span>
                              <Badge variant="outline" className="text-[10px]">{tag.dimension || 'unknown'}</Badge>
                              <button
                                className="ml-auto text-xs text-blue-600 hover:text-blue-800 font-medium"
                                onClick={async () => {
                                  // Add tag to agent
                                  const currentCt = detail?.capability_tags || {}
                                  const dim = (tag.dimension || 'professional') as 'business' | 'professional' | 'technical' | 'management'
                                  const newCt = {
                                    business: currentCt.business ? [...currentCt.business] : [],
                                    professional: currentCt.professional ? [...currentCt.professional] : [],
                                    technical: currentCt.technical ? [...currentCt.technical] : [],
                                    management: currentCt.management ? [...currentCt.management] : [],
                                  }
                                  if (!newCt[dim].includes(tag.tag_id)) {
                                    newCt[dim].push(tag.tag_id)
                                  }
                                  try {
                                    await agentsApi.updateConfig(agent!.id, { capability_tags: newCt })
                                    // Refresh tags
                                    if (detail) fetchIndustryTags(detail)
                                    // Remove from recommended list
                                    setRecommendedTags(prev => prev.filter(t => t.tag_id !== tag.tag_id))
                                    toast.success('标签已添加')
                                  } catch (e) {
                                    console.error('add tag error', e)
                                    toast.error('添加失败')
                                  }
                                }}
                              >
                                + 添加
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Missing tags summary */}
                    <div className="border-t border-slate-100 pt-3">
                      <h4 className="text-xs font-semibold text-amber-700 mb-2 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-amber-500" />缺失标签
                      </h4>
                      {(() => {
                        const allDims = new Set(availableTags.map(t => t.dimension))
                        const currentDims = new Set(industryTags.map(t => t.dimension))
                        const missingDims = [...allDims].filter(d => !currentDims.has(d))
                        return missingDims.length === 0 ? (
                          <p className="text-xs text-slate-400 pl-3">所有维度均已覆盖</p>
                        ) : (
                          <div className="pl-3 space-y-1">
                            {missingDims.map(dim => {
                              const count = availableTags.filter(t => t.dimension === dim).length
                              return (
                                <div key={dim} className="flex items-center gap-2 text-sm">
                                  <span className="font-medium">{dim}</span>
                                  <Badge variant="secondary" className="text-[10px]">{count} 个可用</Badge>
                                </div>
                              )
                            })}
                          </div>
                        )
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end pt-2 border-t">
          <Button variant="outline" onClick={onClose}>关闭</Button>
        </div>
      </DialogContent>

      {/* ==================== Industry Tags Edit Dialog ==================== */}
      <Dialog open={showTagEdit} onOpenChange={(open) => { if (!open) setShowTagEdit(false) }}>
        <DialogContent className="max-w-lg max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>编辑能力标签</DialogTitle>
            <DialogDescription>按维度勾选能力标签，保存后更新到 Agent 的能力标签中</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 overflow-y-auto flex-1">
            {availableTags.length === 0 ? (
              <p className="text-center text-sm text-slate-400 py-4">暂无可用标签</p>
            ) : (
              // Group by dimension
              Object.entries(
                availableTags.reduce((acc, tag) => {
                  const dim = tag.dimension || 'other'
                  if (!acc[dim]) acc[dim] = []
                  acc[dim].push(tag)
                  return acc
                }, {} as Record<string, typeof availableTags>)
              ).map(([dimension, tags]) => (
                <div key={dimension} className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">{dimension}</h4>
                  <div className="grid grid-cols-2 gap-1">
                    {tags.map(tag => {
                      const checked = selectedTagIds.has(tag.tag_id)
                      return (
                        <label
                          key={tag.tag_id}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
                            checked ? 'bg-blue-50 border border-blue-200' : 'bg-slate-50 border border-transparent hover:bg-slate-100'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleTag(tag.tag_id)}
                            className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="truncate">{tag.tag_name || tag.tag_id}</span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="flex justify-between pt-2 border-t">
            <span className="text-xs text-slate-500">
              已选 {selectedTagIds.size} 个标签
            </span>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowTagEdit(false)} disabled={savingTags}>取消</Button>
              <Button onClick={saveTagSelection} disabled={savingTags}>
                {savingTags ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Save className="w-4 h-4 mr-1" />}
                保存
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Dialog>
  )
}
