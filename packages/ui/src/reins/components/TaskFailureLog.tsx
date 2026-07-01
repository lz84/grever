import { useState, useEffect } from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { tasksApi } from '@/shared/utils/api'

interface TaskFailureLogProps {
  taskId: string
}

interface FailureEntry {
  id?: string
  error_type?: string
  error_message?: string
  timestamp?: string
  retry_count?: number
  stack_trace?: string
  context?: string
}

export function TaskFailureLog({ taskId }: TaskFailureLogProps) {
  const [logs, setLogs] = useState<FailureEntry[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadLogs() }, [taskId])

  async function loadLogs() {
    try {
      setLoading(true)
      const data = await tasksApi.getFailureLog(taskId)
      // API 返回 {task_id, failures: []}，取 failures 字段
      setLogs(Array.isArray(data) ? data : (data && 'failures' in data) ? data.failures : [])
    } catch {
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
  }

  if (loading) return <div className="text-center py-4"><Loader2 className="w-4 h-4 animate-spin mx-auto" /></div>
  if (logs.length === 0) return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm text-red-500">失败日志</CardTitle></CardHeader>
      <CardContent><p className="text-xs text-slate-400">暂无失败记录</p></CardContent>
    </Card>
  )

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm text-red-500 flex items-center gap-1"><AlertTriangle className="w-4 h-4" />失败日志</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {logs.map((log, i) => (
          <div key={log.id || i} className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="destructive" className="text-xs">{log.error_type || '错误'}</Badge>
              <span className="text-xs text-slate-400 ml-auto">{formatDate(log.timestamp)}</span>
            </div>
            <p className="text-sm text-red-700">{log.error_message || '未知错误'}</p>
            {log.retry_count !== undefined && (
              <p className="text-xs text-red-500 mt-1">重试次数: {log.retry_count}</p>
            )}
            {log.stack_trace && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-red-400 hover:text-red-600">堆栈追踪</summary>
                <pre className="mt-1 p-2 bg-red-100 rounded text-xs overflow-x-auto max-h-32 overflow-y-auto whitespace-pre-wrap">
                  {log.stack_trace}
                </pre>
              </details>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
