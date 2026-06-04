import { useState, useEffect } from 'react'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { tasksApi } from '@/shared/utils/api'

interface TaskVerificationsProps {
  taskId: string
}

interface Verification {
  id?: string
  result?: string
  passed?: boolean
  verifier_id?: string
  verified_at?: string
  notes?: string
  cycle?: number
}

export function TaskVerifications({ taskId }: TaskVerificationsProps) {
  const [verifications, setVerifications] = useState<Verification[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadVerifications() }, [taskId])

  async function loadVerifications() {
    try {
      setLoading(true)
      const data = await tasksApi.getVerifications(taskId)
      setVerifications(Array.isArray(data) ? data : [])
    } catch {
      setVerifications([])
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
  }

  if (loading) return <div className="text-center py-4"><Loader2 className="w-4 h-4 animate-spin mx-auto" /></div>
  if (verifications.length === 0) return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">验证记录</CardTitle></CardHeader>
      <CardContent><p className="text-xs text-slate-400">暂无验证记录</p></CardContent>
    </Card>
  )

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">验证记录</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {verifications.map((v, i) => (
          <div key={v.id || i} className={`p-3 rounded-lg border ${v.passed ? 'bg-green-50 border-green-200' : v.passed === false ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200'}`}>
            <div className="flex items-center gap-2 mb-1">
              {v.passed === true
                ? <CheckCircle className="w-4 h-4 text-green-500" />
                : v.passed === false
                  ? <XCircle className="w-4 h-4 text-red-500" />
                  : <Badge variant="outline" className="text-xs">待验证</Badge>
              }
              <Badge variant="secondary" className="text-xs">
                {v.passed === true ? '通过' : v.passed === false ? '未通过' : '验证中'}
              </Badge>
              {v.cycle && <span className="text-xs text-slate-400">轮次 {v.cycle}</span>}
              <span className="text-xs text-slate-400 ml-auto">{formatDate(v.verified_at)}</span>
            </div>
            {v.result && <p className="text-sm text-slate-700 mt-1">{v.result}</p>}
            {v.notes && <p className="text-xs text-slate-500 mt-1">{v.notes}</p>}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
