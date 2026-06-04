import { useState, useEffect } from 'react'
import { TRACES } from '../../../shared/api/paths'
import { useParams, Link } from 'react-router-dom'
import { 
  ChevronLeft, CheckCircle, XCircle, PauseCircle, RotateCcw,
  Loader2, FileText, AlertTriangle, Brain, Activity, Clock, ListChecks
} from 'lucide-react'
import { tracesApi, tasksApi } from '../../../shared/utils/api'
import type { Trace, Task } from '../../../shared/utils/api'
import { getTaskStatusText } from '../../../shared/utils/statusMap'
import { getAgentName } from '../../../shared/utils/agentMap'
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Progress } from '@/shared/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'

// 任务状态映射已迁移至 ../shared/utils/statusMap

// 执行状态映射
function mapTraceStatus(trace: Trace): 'running' | 'success' | 'failed' | 'waiting' | 'pending' | 'blocked' {
  if (trace?.task_status === 'pending') return 'pending'
  if (trace?.task_status === 'blocked') return 'blocked'
  if (trace.success === true || trace.success === 1) return 'success'
  if (trace.success === false || trace.success === 0 || trace.success === null || trace.success === undefined) return 'failed'
  if (trace?.final_state === 'completed' || trace?.final_state === 'done') return 'success'
  if (trace?.final_state === 'running' || trace?.final_state === 'active' || !trace?.final_state) return 'running'
  return 'waiting'
}

function getTraceStatusText(status: string): string {
  const map: Record<string, string> = {
    'running': '运行中',
    'success': '成功',
    'failed': '失败',
    'waiting': '等待',
    'pending': '待处理',
    'blocked': '阻塞',
  }
  return map[status] || '未知'
}

function getTraceStatusBadgeVariant(status: string): 'success' | 'destructive' | 'warning' | 'secondary' | 'info' {
  const map: Record<string, 'success' | 'destructive' | 'warning' | 'secondary' | 'info'> = {
    'running': 'info',
    'success': 'success',
    'failed': 'destructive',
    'waiting': 'secondary',
    'pending': 'warning',
    'blocked': 'secondary',
  }
  return map[status] || 'secondary'
}

function getTraceStatusIcon(status: string) {
  const map: Record<string, React.ReactNode> = {
    'running': <Loader2 className="w-4 h-4 animate-spin" />,
    'success': <CheckCircle className="w-4 h-4" />,
    'failed': <XCircle className="w-4 h-4" />,
    'waiting': <PauseCircle className="w-4 h-4" />,
    'pending': <PauseCircle className="w-4 h-4" />,
    'blocked': <AlertTriangle className="w-4 h-4" />,
  }
  return map[status] || <PauseCircle className="w-4 h-4" />
}

// 计算进度（基于 steps）
function calculateProgress(trace: Trace): number {
  if (trace?.success === true || trace?.success === 1) return 100
  if (trace?.final_state === 'completed' || trace?.final_state === 'done') return 100
  if (!trace?.steps || trace?.steps.length === 0) return 0
  const completedSteps = trace!.steps.filter(s => s.type === 'completed').length
  return Math.round((completedSteps / trace!.steps.length) * 100)
}

// 格式化持续时间
function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '--'
  if (ms === 0) return '0秒'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}min`
}

// 格式化时间
function formatTime(iso?: string): string {
  if (!iso) return '--'
  const normalized = iso.replace(' ', 'T')
  const date = new Date(normalized)
  if (isNaN(date.getTime())) return '--'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 提取结果摘要（用于展示）
function extractResultSummary(result: any): string {
  if (!result) return '--'
  if (typeof result === 'string') return result.length > 200 ? result.slice(0, 200) + '...' : result
  if (typeof result === 'object') {
    const str = JSON.stringify(result)
    return str.length > 200 ? str.slice(0, 200) + '...' : str
  }
  return String(result)
}

export default function ExecutionDetail() {
  const { taskId } = useParams<{ taskId: string }>()
  const [trace, setTrace] = useState<Trace | null>(null)
  const [task, setTask] = useState<Task | null>(null)
  const [stepEvents, setStepEvents] = useState<any[]>([])
  const [execLogs, setExecLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function fetchData() {
    if (!taskId) return
    
    try {
      setLoading(true)
      setError('')
      const [traceData, taskData] = await Promise.all([
        tracesApi.get(taskId).catch(() => null),
        tasksApi.get(taskId).catch(() => null),
      ])
      // Sprint 85: 获取原始执行日志
      try {
        const execLogsResp = await fetch(TRACES.GET_EXECUTION_LOGS(taskId))
        if (execLogsResp.ok) {
          const execLogsData = await execLogsResp.json()
          setExecLogs(execLogsData.logs || [])
        }
      } catch {}
      const rawTrace = Array.isArray(traceData) ? (traceData[traceData.length - 1] || null) : traceData
      const traceItem: Trace | null = rawTrace ? {
        task_id: rawTrace.task_id || taskId,
        workflow_id: rawTrace.workflow_id || null,
        task_title: rawTrace.task_title || rawTrace.title || taskData?.title || '未知任务',
        started_at: rawTrace.started_at || null,
        completed_at: rawTrace.completed_at || null,
        final_state: rawTrace.final_state || null,
        success: rawTrace.success,
        result: rawTrace.result || null,
        error_message: rawTrace.error_message || null,
        error_type: undefined,
        cognitions_used: undefined,
        context_size_bytes: undefined,
        total_duration_ms: rawTrace.total_duration_ms || rawTrace.duration_ms || null,
        agent_id: rawTrace.agent_id || taskData?.assigned_agent || null,
        steps: undefined,
        error_stack: undefined,
        cpu_time_ms: undefined,
        memory_peak_mb: undefined,
        io_read_bytes: undefined,
        io_write_bytes: undefined,
        network_bytes: undefined,
        task_status: rawTrace.task_status || rawTrace.status || null,
        retry_count: rawTrace.retry_count ?? taskData?.retry_count ?? 0,
        result_summary: rawTrace.result_summary || null,
      } : null
      setTrace(traceItem)
      setTask(taskData)

      try {
        const stepStatusResponse = await fetch(TRACES.GET_STEP_STATUS(taskId))
        if (stepStatusResponse.ok) {
          const stepStatusData = await stepStatusResponse.json()
          setStepEvents(Array.isArray(stepStatusData.steps) ? stepStatusData.steps : [])
        } else if (stepStatusResponse.status === 404) {
          setStepEvents([])
        } else {
          console.warn(`获取步骤状态失败: ${stepStatusResponse.status}`)
          setStepEvents([])
        }
      } catch (stepErr) {
        console.warn('获取步骤状态时出错:', stepErr)
        setStepEvents([])
      }
    } catch (err: any) {
      setError(err.message || '加载执行详情失败，请检查后端服务是否正常运行')
      setTrace(null)
      setTask(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [taskId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto mb-3" />
          <p className="text-muted-foreground">加载执行详情...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Link 
            to={`/coordination/tasks/${taskId}`} 
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 border rounded-lg hover:bg-muted"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>返回任务详情</span>
          </Link>
        </div>
        <Card className="border-destructive">
          <CardContent className="p-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-destructive" />
            <span className="text-destructive flex-1">{error}</span>
            <Button variant="outline" size="sm" onClick={fetchData}>重试</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!trace && !task) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Link 
            to={`/coordination/tasks/${taskId}`} 
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 border rounded-lg hover:bg-muted"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>返回任务详情</span>
          </Link>
        </div>
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-lg mb-2">未找到执行数据</p>
            <p className="text-sm text-muted-foreground">任务 ID: {taskId}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const effectiveStatus = trace ? mapTraceStatus(trace) : getTaskStatusText(task?.status)
  const progress = trace ? calculateProgress(trace) : (task?.status === 'done' || task?.status === 'completed' ? 100 : 0)
  const retryCount = task?.retry_count ?? trace?.retry_count ?? 0
  const completedAt = trace?.completed_at ?? (task?.completed_at ?? null)
  const resultSummary = trace?.result_summary ?? (task?.result_summary ?? null) ?? (trace?.result ? extractResultSummary(trace!.result) : task?.result_summary ?? '--')
  const taskTitle = trace?.task_title || task?.title || taskId
  const displayTaskId = trace?.task_id || task?.id || taskId

  const progressColor = effectiveStatus === 'success' ? 'bg-green-500' :
    effectiveStatus === 'failed' ? 'bg-red-500' :
    effectiveStatus === 'running' ? 'bg-blue-500' :
    effectiveStatus === 'blocked' ? 'bg-purple-500' :
    'bg-muted-foreground'

  return (
    <div className="space-y-6">
      {/* 返回按钮 */}
      <div className="flex items-center gap-2">
        <Link 
          to={`/coordination/tasks/${taskId}`} 
          className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 border rounded-lg hover:bg-muted"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>返回任务详情</span>
        </Link>
      </div>

      {/* 执行摘要 */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-xl font-bold text-foreground">
                  {taskTitle}
                </h2>
                <Badge variant={getTraceStatusBadgeVariant(effectiveStatus)} className="flex items-center gap-1">
                  {getTraceStatusIcon(effectiveStatus)}
                  {getTraceStatusText(effectiveStatus)}
                </Badge>
                {retryCount > 0 && (
                  <Badge variant="warning" className="flex items-center gap-1">
                    <RotateCcw className="w-3.5 h-3.5" />
                    重试 ×{retryCount}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground font-mono">{displayTaskId}</p>
            </div>
            <div className="text-right space-y-1">
              <div>
                <p className="text-xs text-muted-foreground">开始时间</p>
                <p className="text-sm font-medium text-foreground">{formatTime(trace?.started_at)}</p>
              </div>
              {completedAt && completedAt !== '--' && (
                <div>
                  <p className="text-xs text-muted-foreground">完成时间</p>
                  <p className="text-sm font-medium text-foreground">{formatTime(completedAt)}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">耗时</p>
                <p className="text-sm font-medium text-foreground font-mono">{formatDuration(trace?.total_duration_ms ?? (trace as any)?.duration_ms)}</p>
              </div>
            </div>
          </div>

          {/* 进度条 */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">执行进度</span>
              <span className="font-medium font-mono text-foreground">{progress}%</span>
            </div>
            <Progress value={progress} className={`h-3 ${progressColor}`} />
          </div>
        </CardContent>
      </Card>

      {/* 详情信息 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：基本信息 + 执行详情增强 */}
        <div className="space-y-6">
          {/* 执行详情增强 (MAK-234 §6.3) */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <ListChecks className="w-5 h-5 text-indigo-500" />
                执行详情
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">执行状态</p>
                <p className={`font-medium ${effectiveStatus === 'failed' ? 'text-destructive' : effectiveStatus === 'success' ? 'text-green-600' : 'text-foreground'}`}>
                  {getTraceStatusText(effectiveStatus)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">执行 Agent</p>
                <p className="font-medium">
                  {trace?.agent_id ? getAgentName(trace.agent_id) :
                   task?.assigned_agent ? getAgentName(task.assigned_agent) : (
                    <span className="text-muted-foreground">未分配</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">开始时间</p>
                <p className="font-medium">{formatTime(trace?.started_at)}</p>
              </div>
              {completedAt && completedAt !== '--' && (
                <div>
                  <p className="text-xs text-muted-foreground">完成时间</p>
                  <p className="font-medium">{formatTime(completedAt)}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">重试次数</p>
                <p className={`font-medium ${retryCount > 0 ? 'text-orange-600' : 'text-foreground'}`}>
                  {retryCount > 0 ? `${retryCount} 次` : '无重试'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* 执行者信息 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Brain className="w-5 h-5 text-indigo-500" />
                执行者信息
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Agent</p>
                <p className="font-medium">{getAgentName(trace?.agent_id || task?.assigned_agent || '') || '--'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">工作流</p>
                <p className="font-medium font-mono">{trace?.workflow_id || task?.workflow_step_id || '--'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">最终状态</p>
                <p className="font-medium">{trace?.final_state ? getTraceStatusText(mapTraceStatus(trace!)) : '--'}</p>
              </div>
            </CardContent>
          </Card>

          {/* 资源消耗 */}
          {(trace?.cognitions_used || trace?.context_size_bytes || trace?.memory_peak_mb) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="w-5 h-5 text-emerald-500" />
                  资源消耗
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {trace?.cognitions_used !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">认知次数</p>
                    <p className="font-medium font-mono">{trace!.cognitions_used}</p>
                  </div>
                )}
                {trace?.context_size_bytes !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">上下文大小</p>
                    <p className="font-medium font-mono">{(trace!.context_size_bytes / 1024).toFixed(1)} KB</p>
                  </div>
                )}
                {trace?.memory_peak_mb !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">内存峰值</p>
                    <p className="font-medium font-mono">{trace!.memory_peak_mb.toFixed(1)} MB</p>
                  </div>
                )}
                {trace?.cpu_time_ms !== undefined && (
                  <div>
                    <p className="text-xs text-muted-foreground">CPU 耗时</p>
                    <p className="font-medium font-mono">{formatDuration(trace!.cpu_time_ms)}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 执行结果摘要 (MAK-234 §6.3) */}
          {(resultSummary && resultSummary !== '--') && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  执行结果摘要
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground bg-green-50/50 border border-green-100 rounded-md p-3 max-h-48 overflow-y-auto">
                  <pre className="whitespace-pre-wrap break-all font-mono text-xs leading-relaxed">
                    {resultSummary}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 错误信息 */}
          {trace?.error_message && (
            <Card className="border-destructive bg-destructive/5">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base text-destructive">
                  <AlertTriangle className="w-5 h-5" />
                  错误信息
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center gap-2">
                  {trace?.error_type && (
                    <Badge variant="destructive">{trace!.error_type}</Badge>
                  )}
                  {retryCount > 0 && (
                    <Badge variant="warning">已重试 {retryCount} 次</Badge>
                  )}
                </div>
                <p className="text-sm text-destructive">{trace!.error_message}</p>
                {trace?.error_stack && (
                  <pre className="p-3 bg-destructive/10 rounded text-xs text-destructive overflow-x-auto font-mono max-h-40">
                    {trace!.error_stack}
                  </pre>
                )}
              </CardContent>
            </Card>
          )}

          {/* Sprint 85: 原始执行日志（底层往来消息） */}
          {execLogs.length > 0 && (
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Activity className="w-5 h-5 text-amber-500" />
                  底层往来消息 ({execLogs.length} 条)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 max-h-[600px] overflow-y-auto">
                {execLogs.map((log, idx) => {
                  const isError = log.status === 'failure' || log.action?.includes('fail')
                  const isInput = log.action?.includes('input') || log.action === 'task_start'
                  const isOutput = log.action?.includes('output') || log.action === 'task_complete'
                  return (
                    <div key={idx} className={`rounded-lg border p-3 ${
                      isError ? 'border-red-200 bg-red-50/50' :
                      isInput ? 'border-blue-200 bg-blue-50/30' :
                      isOutput ? 'border-green-200 bg-green-50/30' :
                      'border-slate-200 bg-slate-50/30'
                    }`}>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={isError ? 'destructive' : isInput ? 'info' : isOutput ? 'success' : 'secondary'} className="text-[10px]">
                          {log.action || log.status || 'unknown'}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {log.created_at ? new Date(log.created_at).toLocaleTimeString('zh-CN') : ''}
                        </span>
                        {log.duration_ms > 0 && (
                          <span className="text-[10px] text-muted-foreground">
                            {log.duration_ms < 1000 ? `${log.duration_ms}ms` : `${(log.duration_ms/1000).toFixed(1)}s`}
                          </span>
                        )}
                      </div>
                      {/* 系统发给 Agent 的消息 (input) */}
                      {log.input && Object.keys(log.input).length > 0 && (
                        <div className="mt-1">
                          <p className="text-[10px] font-semibold text-blue-600 mb-0.5">→ 系统发给 Agent</p>
                          <pre className="text-xs text-slate-700 bg-white/70 rounded p-2 max-h-32 overflow-y-auto font-mono leading-relaxed whitespace-pre-wrap break-all">
                            {typeof log.input === 'string' ? log.input : JSON.stringify(log.input, null, 2)}
                          </pre>
                        </div>
                      )}
                      {/* Agent 返回的消息 (output) */}
                      {log.output && Object.keys(log.output).length > 0 && (
                        <div className="mt-1">
                          <p className="text-[10px] font-semibold text-green-600 mb-0.5">← Agent 返回</p>
                          <pre className="text-xs text-slate-700 bg-white/70 rounded p-2 max-h-32 overflow-y-auto font-mono leading-relaxed whitespace-pre-wrap break-all">
                            {typeof log.output === 'string' ? log.output : JSON.stringify(log.output, null, 2)}
                          </pre>
                        </div>
                      )}
                      {/* 错误信息 */}
                      {log.error_message && (
                        <div className="mt-1">
                          <p className="text-[10px] font-semibold text-red-600 mb-0.5">✗ 错误</p>
                          <p className="text-xs text-red-700 bg-red-50 rounded p-2 font-mono">{log.error_message}</p>
                        </div>
                      )}
                      {log.result_summary && !log.output?.result_summary && (
                        <div className="mt-1">
                          <p className="text-[10px] font-semibold text-slate-500 mb-0.5">摘要</p>
                          <pre className="text-xs text-slate-600 bg-white/50 rounded p-2 max-h-24 overflow-y-auto font-mono whitespace-pre-wrap break-all">
                            {log.result_summary}
                          </pre>
                        </div>
                      )}
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          )}
        </div>

        {/* 右侧：执行步骤 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="pb-0">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <CardTitle className="text-base">
                  执行步骤 ({stepEvents?.length || 0})
                </CardTitle>
                <Badge variant="secondary">{progress}% 完成</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {!stepEvents || stepEvents.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                  <p className="text-sm text-muted-foreground">暂无执行步骤数据</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {stepEvents.map((step, i) => {
                    const isCompleted = step.event_type === 'task_completed' || step.type === 'completed'
                    const isFailed = step.event_type === 'task_failed' || step.type === 'failed'
                    const eventType = step.event_type || step.type
                    
                    return (
                      <div key={step.id || i} className="flex gap-4 p-4 bg-muted/50 rounded-lg border relative">
                        {/* 连接线 */}
                        {i < stepEvents.length - 1 && (
                          <div className="absolute left-4 top-12 bottom-0 w-0.5 bg-border -z-10" />
                        )}
                        
                        {/* 序号圆圈 */}
                        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-background border-2 shadow-sm relative">
                          {isCompleted ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : isFailed ? (
                            <XCircle className="w-4 h-4 text-red-500" />
                          ) : (
                            <div className="w-2 h-2 rounded-full bg-muted-foreground" />
                          )}
                          <span className={`absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                            isCompleted ? 'bg-green-500 text-white' :
                            isFailed ? 'bg-red-500 text-white' :
                            'bg-blue-500 text-white animate-pulse'
                          }`}>
                            {i + 1}
                          </span>
                        </div>

                        {/* 步骤信息 */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <h4 className="font-semibold text-foreground text-sm">
                                {step.action || step.event_type || step.type || `步骤 ${i + 1}`}
                              </h4>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {step.timestamp && (
                                  <span className="mr-2">
                                    {new Date(step.timestamp).toLocaleString('zh-CN', {
                                      month: '2-digit',
                                      day: '2-digit',
                                      hour: '2-digit',
                                      minute: '2-digit',
                                      second: '2-digit'
                                    })}
                                  </span>
                                )}
                                {step.agent_id && (
                                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded mr-2">
                                    Agent: {getAgentName(step.agent_id)}
                                  </span>
                                )}
                                {step.duration_ms && (
                                  <span className="text-muted-foreground">
                                    · 耗时: {formatDuration(step.duration_ms)}
                                  </span>
                                )}
                              </p>
                            </div>
                            <Badge variant={
                              eventType === 'task_completed' || eventType === 'completed' ? 'success' :
                              eventType === 'task_failed' || eventType === 'failed' ? 'destructive' :
                              'secondary'
                            }>
                              {eventType === 'task_completed' || eventType === 'completed' ? '已完成' :
                               eventType === 'task_failed' || eventType === 'failed' ? '失败' :
                               eventType === 'task_started' || eventType === 'pending' ? '已开始' :
                               eventType || '进行中'}
                            </Badge>
                          </div>

                          {/* 步骤详情（如果有） */}
                          {(isFailed || step.error_message) && (
                            <p className="text-xs text-destructive mt-2 bg-destructive/10 p-2 rounded">
                              {step.action || eventType} {isFailed ? '执行失败' : ''} {step.error_message || ''}
                            </p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
