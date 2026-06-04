import { useState, useEffect } from 'react'
import { toast } from "sonner"
import { Plus, X, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Input } from '@/shared/components/ui/input'
import { tasksApi } from '@/shared/utils/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'

interface TaskLabelsProps {
  taskId: string
}

export function TaskLabels({ taskId }: TaskLabelsProps) {
  const [labels, setLabels] = useState<{ id: string; name: string }[]>([])
  const [newLabel, setNewLabel] = useState('')
  const [adding, setAdding] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadLabels() }, [taskId])

  async function loadLabels() {
    try {
      setLoading(true)
      const data = await tasksApi.getLabels(taskId)
      // API returns string[] or array of objects
      if (Array.isArray(data)) {
        setLabels(data.map((l: any, i) => ({
          id: l.id || `label-${i}`,
          name: typeof l === 'string' ? l : l.name || l.label || String(l),
        })))
      }
    } catch {
      setLabels([])
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd() {
    if (!newLabel.trim()) return
    setAdding(true)
    try {
      await tasksApi.addLabel(taskId, newLabel.trim())
      setNewLabel('')
      await loadLabels()
      toast.success('标签已添加')
    } catch (e: any) {
      toast.error('添加失败: ' + e.message)
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(id: string, name: string) {
    try {
      await tasksApi.deleteLabel(taskId, id)
      await loadLabels()
      toast.success(`标签 "${name}" 已删除`)
    } catch (e: any) {
      toast.error('删除失败: ' + e.message)
    }
  }

  if (loading) return <div className="text-center py-4"><Loader2 className="w-4 h-4 animate-spin mx-auto" /></div>

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">标签管理</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Existing labels */}
        <div className="flex flex-wrap gap-2 mb-3">
          {labels.length === 0 ? (
            <span className="text-xs text-slate-400">暂无标签</span>
          ) : (
            labels.map((l) => (
              <Badge key={l.id} variant="secondary" className="gap-1">
                {l.name}
                <button
                  className="ml-1 hover:text-red-500"
                  onClick={() => handleDelete(l.id, l.name)}
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))
          )}
        </div>

        {/* Add new */}
        <div className="flex gap-2">
          <Input
            value={newLabel}
            onChange={e => setNewLabel(e.target.value)}
            placeholder="新标签名称"
            className="h-8 text-sm"
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
          />
          <Button size="sm" variant="outline" onClick={handleAdd} disabled={adding || !newLabel.trim()}>
            {adding ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
