import { useState, useEffect } from 'react'
import { toast } from "sonner"
import { Plus, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { tasksApi } from '@/shared/utils/api'

interface TaskSubIssuesProps {
  taskId: string
}

interface SubIssue {
  id: string
  relation_id?: string
  title: string
  description?: string
  status?: string
  created_at?: string
}

export function TaskSubIssues({ taskId }: TaskSubIssuesProps) {
  const [issues, setIssues] = useState<SubIssue[]>([])
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [adding, setAdding] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadIssues() }, [taskId])

  async function loadIssues() {
    try {
      setLoading(true)
      const data = await tasksApi.getSubIssues(taskId)
      setIssues(Array.isArray(data) ? data : [])
    } catch {
      setIssues([])
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd() {
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      await tasksApi.addSubIssue(taskId, { title: newTitle.trim(), description: newDesc.trim() || undefined })
      setNewTitle('')
      setNewDesc('')
      await loadIssues()
      toast.success('子问题已添加')
    } catch (e: any) {
      toast.error('添加失败: ' + e.message)
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(relationId: string) {
    try {
      await tasksApi.deleteSubIssue(taskId, relationId)
      await loadIssues()
      toast.success('子问题已删除')
    } catch (e: any) {
      toast.error('删除失败: ' + e.message)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
  }

  if (loading) return <div className="text-center py-4"><Loader2 className="w-4 h-4 animate-spin mx-auto" /></div>

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">子问题</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Add form */}
        <div className="space-y-2 p-3 bg-slate-50 rounded-lg">
          <Input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder="子问题标题"
            className="h-8 text-sm"
          />
          <Textarea
            value={newDesc}
            onChange={e => setNewDesc(e.target.value)}
            placeholder="描述（可选）"
            className="text-sm"
            rows={2}
          />
          <Button size="sm" onClick={handleAdd} disabled={adding || !newTitle.trim()}>
            {adding ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
            添加子问题
          </Button>
        </div>

        {/* List */}
        {issues.length === 0 ? (
          <p className="text-xs text-slate-400 text-center py-4">暂无子问题</p>
        ) : (
          <div className="space-y-2">
            {issues.map((issue) => (
              <div key={issue.id || issue.relation_id} className="flex items-start justify-between gap-2 p-2 border rounded text-sm">
                <div className="flex-1">
                  <p className="font-medium">{issue.title}</p>
                  {issue.description && <p className="text-xs text-slate-500 mt-1">{issue.description}</p>}
                  <p className="text-xs text-slate-400 mt-1">{formatDate(issue.created_at)}</p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 w-6 p-0 text-slate-400 hover:text-red-500"
                  onClick={() => handleDelete(issue.relation_id || issue.id)}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
