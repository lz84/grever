import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { tasksApi } from '@/shared/utils/api'

interface TaskContextProps {
  taskId: string
}

export function TaskContext({ taskId }: TaskContextProps) {
  const [context, setContext] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadContext() }, [taskId])

  async function loadContext() {
    try {
      setLoading(true)
      const data = await tasksApi.getContext(taskId)
      setContext(data)
    } catch {
      setContext(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="text-center py-4"><Loader2 className="w-4 h-4 animate-spin mx-auto" /></div>
  if (!context) return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">任务上下文</CardTitle></CardHeader>
      <CardContent><p className="text-xs text-slate-400">暂无上下文数据</p></CardContent>
    </Card>
  )

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">任务上下文</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm">
        {context.context_summary && (
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">摘要</p>
            <p className="text-slate-700 whitespace-pre-wrap">{context.context_summary}</p>
          </div>
        )}
        {context.task_context && (
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">上下文</p>
            <p className="text-slate-700 whitespace-pre-wrap">{context.task_context}</p>
          </div>
        )}
        {context.dependencies && context.dependencies.length > 0 && (
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">依赖</p>
            <ul className="text-slate-700 list-disc list-inside">
              {context.dependencies.map((d: any, i: number) => (
                <li key={i}>{typeof d === 'string' ? d : JSON.stringify(d)}</li>
              ))}
            </ul>
          </div>
        )}
        <details className="text-xs">
          <summary className="cursor-pointer text-slate-400 hover:text-slate-600">查看原始数据</summary>
          <pre className="mt-2 p-2 bg-slate-50 rounded text-xs overflow-x-auto max-h-40 overflow-y-auto">
            {JSON.stringify(context, null, 2)}
          </pre>
        </details>
      </CardContent>
    </Card>
  )
}
