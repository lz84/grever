import { useState, useEffect, Fragment } from 'react'
import { Link } from 'react-router-dom'
import { disputesApi, tracesApi, tasksApi, agentsApi } from '../../../shared/utils/api'
import type { Dispute, Trace, Task, Agent } from '../../../shared/utils/api'
import { 
  AlertCircle, Activity, AlertTriangle, CheckCircle, XCircle, RefreshCw,
  Loader2, Eye, FileText, Clock, ListTodo, Users, PlayCircle, PauseCircle, ChevronDown, ChevronRight
} from 'lucide-react'
import { eventStream, type ReinsEvent } from '../../../shared/services/eventStream'
import { getTaskStatusText } from '../../../shared/utils/statusMap'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/components/ui/tabs'

// ==================== Dispute mapping ====================

function mapDispute(dispute: Dispute) {
  const typeMap: Record<string, string> = {
    'resource-competition': 'resource-competition',
    'dependency-block': 'dependency-block',
    'dynamic-response': 'dynamic-response',
  }
  const typeLabelMap: Record<string, string> = {
    'resource-competition': '资源竞争',
    'dependency-block': '依赖阻塞',
    'dynamic-response': '动态响应',
  }
  const severityMap: Record<string, string> = {
    'open': '高',
    'active': '高',
    'resolved': '低',
    'closed': '低',
    'under_review': '中',
    'appealed': '高',
  }
  const statusMap: Record<string, string> = {
    'open': '未处理',
    'active': '处理中',
    'resolved': '已解决',
    'closed': '已解决',
    'under_review': '审核中',
    'appealed': '已上诉',
  }

  return {
    id: dispute.id,
    type: typeMap[dispute.dispute_type || ''] || 'dynamic-response',
    title: typeLabelMap[dispute.dispute_type || ''] || '争议事件',
    description: dispute.description,
    severity: severityMap[dispute.status] || '中',
    status: statusMap[dispute.status] || '未处理',
    affectedTasks: dispute.related_task_id ? [dispute.related_task_id] : [],
    affectedAgents: dispute.involved_agents || [],
    resolution: dispute.resolution || null,
    createdAt: dispute.created_at,
    resolvedAt: dispute.resolved_at,
  }
}

// ==================== Trace helpers ====================

function mapTraceStatus(trace: Trace): 'running' | 'success' | 'failed' | 'waiting' {
  if (trace.success === true) return 'success'
  if (trace.success === false) return 'failed'
  if (trace.final_state === 'running' || !trace.final_state) return 'running'
  return 'waiting'
}

function getTraceStatusText(status: 'running' | 'success' | 'failed' | 'waiting'): string {
  const map: Record<string, string> = {
    'running': '运行中',
    'success': '成功',
    'failed': '失败',
    'waiting': '等待',
  }
  return map[status]
}

function getTraceStatusBadgeVariant(status: 'running' | 'success' | 'failed' | 'waiting'): string {
  const map: Record<string, string> = {
    'running': 'info',
    'success': 'success',
    'failed': 'destructive',
    'waiting': 'secondary',
  }
  return map[status]
}

function getTraceStatusIcon(status: 'running' | 'success' | 'failed' | 'waiting') {
  switch (status) {
    case 'running': return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />
    case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />
    case 'failed': return <XCircle className="w-4 h-4 text-red-500" />
    case 'waiting': return <Clock className="w-4 h-4 text-slate-400" />
  }
}

// ==================== Duration formatter ====================

function formatDuration(durationMs?: number): string {
  if (!durationMs || durationMs <= 0) return '—'
  const seconds = Math.floor(durationMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes > 0) return `${minutes}m ${remainingSeconds}s`
  return `${seconds}s`
}

// ==================== Severity badge ====================

function getSeverityBadgeVariant(severity: string): string {
  if (severity === '高') return 'destructive'
  if (severity === '中') return 'warning'
  return 'secondary'
}

// ==================== Main component ====================

type ActiveTab = 'queue' | 'executions' | 'agents' | 'alerts'

export default function ExecutionMonitoring() {
  const [apiAvailable, setApiAvailable] = useState(false)
  const [conflicts, setConflicts] = useState<any[]>([])
  const [traces, setTraces] = useState<{ running: Trace[]; completed: Trace[] }>({ running: [], completed: [] })
  const [timeline, setTimeline] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<ActiveTab>('queue')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(new Set())

  const [tasks, setTasks] = useState<Task[]>([])
  const [agents, setAgents] = useState<Agent[]>([])

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const [disputesData, tracesData, tasksData, agentsData] = await Promise.all([
        disputesApi.list(),
        tracesApi.list(),
        tasksApi.list(),
        agentsApi.list(),
      ])
      setConflicts(disputesData.map(mapDispute))
      if (Array.isArray(tracesData)) {
        const running = tracesData.filter((t: any) => t.final_state === 'running' || (t.success === null && !t.completed_at))
        const completed = tracesData.filter((t: any) => t.success !== null || t.completed_at)
        setTraces({ running, completed })
      } else {
        setTraces(tracesData)
      }
      setTasks(tasksData)
      setAgents(agentsData)
    } catch (err: any) {
      setError(err.message || '执行监控数据加载失败')
      setConflicts([])
      setTraces({ running: [], completed: [] })
      setTasks([])
      setAgents([])
      setTimeline([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    eventStream.connect()
    const unsubscribe = eventStream.subscribe((event: ReinsEvent) => {
      if (event.event_type === 'connected') {
        setApiAvailable(true)
        return
      }
      const evtType: string = event.event_type
      if (evtType.startsWith('task_') || evtType.startsWith('step_')) {
        tasksApi.list().then(setTasks).catch(() => {})
        if (evtType === 'task_assigned' || evtType === 'step_started') {
          tracesApi.list().then(setTraces).catch(() => {})
        }
      }
      const now = new Date()
      const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      const eventTitleMap: Record<string, string> = {
        step_started: '步骤开始', step_completed: '步骤完成', step_failed: '步骤失败', step_blocked: '步骤阻塞',
        workflow_started: '工作流开始', workflow_completed: '工作流完成', workflow_failed: '工作流失败',
        task_assigned: '任务分配', task_completed: '任务完成', task_failed: '任务失败',
        dispute_created: '冲突创建', dispute_resolved: '冲突解决',
      }
      const eventIconMap: Record<string, React.ReactNode> = {
        step_started: <Activity className="w-4 h-4 text-blue-500" />,
        step_completed: <CheckCircle className="w-4 h-4 text-green-500" />,
        step_failed: <XCircle className="w-4 h-4 text-red-500" />,
        step_blocked: <AlertTriangle className="w-4 h-4 text-purple-500" />,
        workflow_started: <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />,
        workflow_completed: <CheckCircle className="w-4 h-4 text-green-500" />,
        workflow_failed: <XCircle className="w-4 h-4 text-red-500" />,
        task_assigned: <Activity className="w-4 h-4 text-amber-500" />,
        task_completed: <CheckCircle className="w-4 h-4 text-green-500" />,
        task_failed: <XCircle className="w-4 h-4 text-red-500" />,
        dispute_created: <AlertTriangle className="w-4 h-4 text-amber-500" />,
        dispute_resolved: <CheckCircle className="w-4 h-4 text-green-500" />,
      }
      const newEvent = {
        id: event.event_id,
        type: event.event_type,
        title: eventTitleMap[event.event_type] || event.event_type,
        icon: eventIconMap[event.event_type] || <Activity className="w-4 h-4 text-slate-400" />,
        timestamp: timeStr,
        data: event.data || {},
        description: event.data?.message || event.data?.task_title || '发生事件',
      }
      setTimeline((prev) => [newEvent, ...prev].slice(0, 100))
    })
    return () => {
      unsubscribe()
      eventStream.disconnect()
    }
  }, [])

  const allTraces = [...traces.running, ...traces.completed]
  const pendingTasks = tasks.filter(t => t.status === 'pending' || t.status === 'todo')
  const inProgressTasks = tasks.filter(t => t.status?.includes('in_progress'))
  const getAgentTasks = (agentId: string) => tasks.filter(t => t.assigned_agent === agentId && t.status === 'in_progress')
  const queueCount = pendingTasks.length + inProgressTasks.length

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-500" />
            执行监控
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            实时监控执行过程与冲突告警{apiAvailable ? '（SSE 已连接）' : '（SSE 未连接）'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">Live</span>
        </div>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-700 text-sm flex-1">{error}</span>
            <Button size="sm" variant="outline" onClick={fetchData}>重试</Button>
          </CardContent>
        </Card>
      )}

      {/* Tab bar */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ActiveTab)}>
        <TabsList>
          <TabsTrigger value="queue" className="gap-1.5">
            <ListTodo className="w-4 h-4" />
            任务队列
            {queueCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700">{queueCount}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="executions" className="gap-1.5">
            <Activity className="w-4 h-4" />
            执行列表
            {allTraces.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700">{allTraces.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="agents" className="gap-1.5">
            <Users className="w-4 h-4" />
            Agent 状态
            <span className="ml-1 px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-600">{agents.length}</span>
          </TabsTrigger>
          <TabsTrigger value="alerts" className="gap-1.5">
            <AlertTriangle className="w-4 h-4" />
            冲突告警
            {conflicts.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-700">{conflicts.length}</span>
            )}
          </TabsTrigger>
        </TabsList>

        {/* ==================== TAB: 任务队列 ==================== */}
        <TabsContent value="queue" className="space-y-6">
          {/* Pending tasks */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <PauseCircle className="w-4 h-4 text-amber-500" />
              待执行任务 ({pendingTasks.length})
            </h3>
            {pendingTasks.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">暂无待执行任务</p>
            ) : (
              <div className="space-y-2">
                {pendingTasks.map(task => {
                  const p = typeof task.priority === 'string' ? task.priority.toLowerCase() : String(task.priority)
                  const isCritical = p === 'critical' || p === '0' || p === '1'
                  const isHigh = p === 'high' || p === '2'
                  return (
                    <div key={task.id} className="flex items-center justify-between p-3 rounded-lg border border-amber-100 bg-amber-50/50 hover:bg-amber-50 transition-colors">
                      <div className="flex items-center gap-3">
                        {task.status === 'pending' || task.status === 'todo' ? (
                          <PauseCircle className="w-4 h-4 text-amber-500" />
                        ) : (
                          <Clock className="w-4 h-4 text-slate-400" />
                        )}
                        <div>
                          <p className="font-medium text-slate-800 text-sm">{task.title || task.id}</p>
                          <p className="text-xs text-slate-500 font-mono">{task.id}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {task.priority && (
                          <Badge variant={isCritical ? 'destructive' : isHigh ? 'warning' : 'info'}>
                            {isCritical ? '紧急' : isHigh ? '高' : '普通'}
                          </Badge>
                        )}
                        <Badge variant="secondary">{getTaskStatusText(task.status)}</Badge>
                        <Button asChild variant="outline" size="sm">
                          <Link to="/coordination/tasks">
                            <Eye className="w-3 h-3" />
                            查看
                          </Link>
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* In-progress tasks */}
          <div>
            <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <PlayCircle className="w-4 h-4 text-blue-500" />
              执行中任务 ({inProgressTasks.length})
            </h3>
            {inProgressTasks.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">暂无执行中任务</p>
            ) : (
              <div className="space-y-2">
                {inProgressTasks.map(task => (
                  <div key={task.id} className="flex items-center justify-between p-3 rounded-lg border border-blue-100 bg-blue-50/50 hover:bg-blue-50 transition-colors">
                    <div className="flex items-center gap-3">
                      <PlayCircle className="w-4 h-4 text-blue-500 animate-pulse" />
                      <div>
                        <p className="font-medium text-slate-800 text-sm">{task.title || task.id}</p>
                        <p className="text-xs text-slate-500">
                          {task.assigned_agent ? `Agent: ${task.assigned_agent}` : '未分配'}
                          {task.started_at && ` · 开始于 ${new Date(task.started_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {task.retry_count > 0 && (
                        <Badge variant="warning">重试 ×{task.retry_count}</Badge>
                      )}
                      <Badge variant="secondary">{getTaskStatusText(task.status)}</Badge>
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/executions/${task.id}`}>
                          <Eye className="w-3 h-3" />
                          详情
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Agent current execution cards */}
          {agents.length > 0 && (
            <div>
              <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4 text-slate-500" />
                Agent 当前执行
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {agents.map(agent => {
                  const agentTasks = getAgentTasks(agent.id)
                  return (
                    <Card key={agent.id}>
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-3">
                          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center font-bold text-indigo-700 text-sm">
                            {agent.name[0]}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-slate-800 text-sm">{agent.name}</p>
                            <p className="text-xs text-slate-500">{agentTasks.length} 个任务执行中</p>
                          </div>
                          <div className={`w-2 h-2 rounded-full ${
                            agent.status === 'online' || agent.status === 'idle' ? 'bg-green-500' :
                            agent.status === 'busy' ? 'bg-amber-500' : 'bg-slate-400'
                          }`} />
                        </div>
                        {agentTasks.length === 0 ? (
                          <p className="text-xs text-slate-400 text-center py-2">待命中</p>
                        ) : (
                          <div className="space-y-1.5">
                            {agentTasks.slice(0, 3).map(task => (
                              <div key={task.id} className="flex items-center justify-between bg-slate-50 rounded-sm px-2 py-1.5">
                                <span className="text-xs text-slate-700 truncate max-w-[140px]">{task.title || task.id}</span>
                                <Link to={`/executions/${task.id}`} className="text-xs text-blue-600 hover:text-blue-800 ml-2 shrink-0">
                                  查看
                                </Link>
                              </div>
                            ))}
                            {agentTasks.length > 3 && (
                              <p className="text-xs text-slate-400 text-center">还有 {agentTasks.length - 3} 个任务</p>
                            )}
                          </div>
                        )}
                        <div className="mt-3 pt-2 border-t border-slate-100">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${agent.load > 80 ? 'bg-red-500' : agent.load > 50 ? 'bg-amber-500' : 'bg-blue-500'}`}
                                style={{ width: `${Math.min(agent.load, 100)}%` }}
                              />
                            </div>
                            <span className="text-[10px] text-slate-500 font-mono">{agent.load}%</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}
        </TabsContent>

        {/* ==================== TAB: 执行列表 ==================== */}
        <TabsContent value="executions">
          {allTraces.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg mb-2">暂无执行记录</p>
              <p className="text-sm">发起任务执行后，数据将在此显示</p>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead>任务名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>执行者</TableHead>
                    <TableHead>开始时间</TableHead>
                    <TableHead>耗时</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allTraces.map((trace) => {
                    const status = mapTraceStatus(trace)
                    const duration = formatDuration(trace.total_duration_ms)
                    const isExpanded = expandedTraces.has(trace.task_id)
                    const secondaryInfo = (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 border-t border-slate-200 bg-slate-50">
                        <div><span className="font-medium text-slate-600">目标ID:</span> <span className="text-slate-700">{(trace as any).goal_id || '-'}</span></div>
                        <div><span className="font-medium text-slate-600">模型:</span> <span className="text-slate-700">{(trace as any).model_used || '-'}</span></div>
                        <div><span className="font-medium text-slate-600">Token数:</span> <span className="text-slate-700">{(trace as any).token_usage || '-'}</span></div>
                        <div><span className="font-medium text-slate-600">成本:</span> <span className="text-slate-700">{(trace as any).cost || '-'}</span></div>
                        <div><span className="font-medium text-slate-600">结束时间:</span> <span className="text-slate-700">{trace.completed_at ? new Date(trace.completed_at).toLocaleString() : '-'}</span></div>
                        <div className="col-span-3"><span className="font-medium text-slate-600">错误信息:</span> <span className="text-slate-700">{trace.error_message || '-'}</span></div>
                      </div>
                    )
                    return (
                      <Fragment key={trace.task_id}>
                        <TableRow>
                          <TableCell className="p-2">
                            <button
                              onClick={() => {
                                const newExpanded = new Set(expandedTraces)
                                if (newExpanded.has(trace.task_id)) newExpanded.delete(trace.task_id)
                                else newExpanded.add(trace.task_id)
                                setExpandedTraces(newExpanded)
                              }}
                              className="text-slate-400 hover:text-slate-600 p-1"
                            >
                              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            </button>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {getTraceStatusIcon(status)}
                              <span className="font-medium text-slate-800">{trace.task_title || trace.task_id}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant={getTraceStatusBadgeVariant(status) as any}>
                              {getTraceStatusText(status)}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <span className="text-sm text-slate-600 font-mono">
                              {trace.agent_id ? `Agent ${trace.agent_id.slice(-6)}` : '-'}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="text-sm text-slate-500">
                              {trace.started_at ? new Date(trace.started_at).toLocaleTimeString() : '-'}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="text-xs text-slate-500 font-mono">{duration}</span>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button asChild variant="ghost" size="sm">
                              <Link to={`/executions/${trace.task_id}`}>
                                <Eye className="w-3 h-3" />
                                详情
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                        {isExpanded && (
                          <TableRow>
                            <TableCell colSpan={7} className="p-0">
                              {secondaryInfo}
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>

        {/* ==================== TAB: Agent 状态 ==================== */}
        <TabsContent value="agents">
          {agents.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg mb-2">暂无 Agent</p>
              <p className="text-sm">注册 Agent 后将在此显示</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map(agent => {
                const agentTasks = getAgentTasks(agent.id)
                const isOnline = agent.status === 'online' || agent.status === 'idle'
                const isBusy = agent.status === 'busy'
                return (
                  <Card key={agent.id} className={!isOnline ? 'opacity-60 grayscale' : ''}>
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center font-bold text-indigo-700">
                            {agent.name[0]}
                          </div>
                          <div>
                            <CardTitle className="text-sm">{agent.name}</CardTitle>
                            <p className="text-xs text-slate-500">{Object.values(agent.capability_tags || {}).flat().slice(0, 2).join(', ')}</p>
                          </div>
                        </div>
                        <Badge variant={isOnline ? 'success' : isBusy ? 'warning' : 'secondary'}>
                          {isOnline ? '在线' : isBusy ? '繁忙' : '离线'}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="bg-slate-50 p-3 rounded-md mb-3">
                        <div className="flex items-start gap-2">
                          <Clock className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                          <div>
                            <p className="text-xs text-slate-500">当前任务</p>
                            {agentTasks.length === 0 ? (
                              <p className="text-sm font-medium text-slate-400">待命中</p>
                            ) : (
                              <div className="space-y-1 mt-1">
                                {agentTasks.slice(0, 2).map(t => (
                                  <p key={t.id} className="text-xs text-slate-700 truncate" title={t.title || t.id}>
                                    · {t.title || t.id}
                                  </p>
                                ))}
                                {agentTasks.length > 2 && (
                                  <p className="text-xs text-slate-400">还有 {agentTasks.length - 2} 个任务</p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${agent.load > 80 ? 'bg-red-500' : agent.load > 50 ? 'bg-amber-500' : 'bg-blue-500'}`}
                              style={{ width: `${Math.min(agent.load, 100)}%` }}
                            />
                          </div>
                          <span className="font-mono text-[10px] text-slate-500">{agent.load}% LOAD</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-slate-100">
                        <div>
                          <p className="text-[10px] text-slate-500">容量</p>
                          <p className="text-sm font-bold text-slate-700">
                            {agent.load > 80 ? '紧张' : agent.load > 50 ? '中等' : '充裕'}
                          </p>
                        </div>
                        <div>
                          <p className="text-[10px] text-slate-500">任务数</p>
                          <p className="text-sm font-bold text-slate-700">{agent.current_tasks}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </TabsContent>

        {/* ==================== TAB: 冲突告警 ==================== */}
        <TabsContent value="alerts">
          {conflicts.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg mb-2">暂无冲突告警</p>
              <p className="text-sm">所有智能体协同良好</p>
            </div>
          ) : (
            <div className="space-y-3">
              {conflicts.map((conflict) => (
                <Card key={conflict.id} className={`border-l-4 ${
                  conflict.severity === '高' ? 'border-l-red-500' :
                  conflict.severity === '中' ? 'border-l-amber-500' : 'border-l-blue-500'
                }`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-lg">{conflict.title}</span>
                          <Badge variant={getSeverityBadgeVariant(conflict.severity) as any}>
                            {conflict.severity}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-600 mb-2">{conflict.description}</p>
                        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                          {conflict.affectedTasks.length > 0 && (
                            <span>任务: {conflict.affectedTasks.join(', ')}</span>
                          )}
                          {conflict.affectedAgents.length > 0 && (
                            <span>智能体: {conflict.affectedAgents.length}个</span>
                          )}
                        </div>
                      </div>
                      <div className="text-right shrink-0 ml-4">
                        <Badge variant={
                          conflict.status === '已解决' ? 'success' :
                          conflict.status === '处理中' ? 'info' : 'destructive'
                        }>
                          {conflict.status}
                        </Badge>
                        <div className="text-xs text-slate-400 mt-1">创建: {conflict.createdAt}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Execution log stream */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="w-4 h-4" />
              执行日志流
              {apiAvailable && <span className="ml-2 w-2 h-2 bg-green-500 rounded-full" />}
            </CardTitle>
            <span className="text-xs text-slate-400">{timeline.length} 条</span>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {timeline.length === 0 ? (
            <div className="text-center py-6 text-slate-400">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无日志数据，等待事件...</p>
            </div>
          ) : (
            <div className="font-mono text-xs space-y-1 max-h-64 overflow-y-auto">
              {timeline.map((event) => (
                <div key={event.id} className="flex items-start gap-3 py-1 hover:bg-slate-50 rounded-sm px-1">
                  <span className="text-slate-400 shrink-0">{event.timestamp}</span>
                  <span className="shrink-0 mt-0.5">{event.icon}</span>
                  <span className={`font-medium ${
                    event.type.includes('failed') ? 'text-red-600' :
                    event.type.includes('completed') ? 'text-green-600' :
                    event.type.includes('started') ? 'text-blue-600' : 'text-slate-700'
                  }`}>
                    [{event.title}]
                  </span>
                  <span className="text-slate-600 truncate">{event.description}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
