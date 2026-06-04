import { useState, useEffect } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'
import type { Task } from '@/shared/utils/api'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { getTaskStatusText, getTaskStatusBadgeClass } from '@/shared/utils/statusMap'
import { Play } from 'lucide-react'

// ── Task Edit Modal ─────────────────────────────────────────────────

interface TaskEditModalProps {
  task: Task | null
  agents: { id: string; name: string }[]
  onClose: () => void
  onSave: (taskId: string, status: string, agent: string) => Promise<void>
}

export function TaskEditModal({ task, agents, onClose, onSave }: TaskEditModalProps) {
  const [status, setStatus] = useState(task?.status || 'todo')

  const getInitialAgent = (t: Task | null) => {
    if (!t?.assigned_agent) return ''
    const match = agents.find(a => a.id === t.assigned_agent)
    return match ? match.id : ''
  }
  const [assignedAgent, setAssignedAgent] = useState(getInitialAgent(task))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (task) {
      setStatus(task.status || 'todo')
      const match = agents.find(a => a.id === task.assigned_agent)
      setAssignedAgent(match ? match.id : '')
    }
  }, [task, agents])

  async function handleSave() {
    if (!task) return
    try {
      setSaving(true)
      setError(null)
      await onSave(task.id, status, assignedAgent)
      onClose()
    } catch (e: any) {
      setError(e.message || '保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  if (!task) return null

  return (
    <Dialog open={!!task} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>编辑任务</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-700 mb-1">任务名称</p>
            <p className="text-slate-900 bg-slate-50 rounded-sm px-3 py-2 text-sm">
              {task.title || '未命名任务'}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">状态</label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todo">待办</SelectItem>
                <SelectItem value="in_progress">进行中</SelectItem>
                <SelectItem value="review_needed">待审核</SelectItem>
                <SelectItem value="blocked">阻塞中</SelectItem>
                <SelectItem value="done">已完成</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">分配智能体</label>
            <Select value={assignedAgent} onValueChange={setAssignedAgent}>
              <SelectTrigger>
                <SelectValue placeholder="待分配" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">待分配</SelectItem>
                {agents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {task.due_date && (
            <div>
              <p className="text-sm font-medium text-slate-700 mb-1">截止日期</p>
              <p className="text-slate-900 bg-slate-50 rounded-sm px-3 py-2 text-sm">{task.due_date}</p>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-sm text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {saving ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Task Restart Dialog (重新分配 + 重启) ──────────────────────────────────────────

interface TaskRestartDialogProps {
  task: Task | null
  agents: { id: string; name: string }[]
  onClose: () => void
  onRestart: (taskId: string, agent: string) => Promise<void>
}

export function TaskRestartDialog({ task, agents, onClose, onRestart }: TaskRestartDialogProps) {
  const [assignedAgent, setAssignedAgent] = useState('')
  const [restarting, setRestarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (task) {
      const match = agents.find(a => a.id === task.assigned_agent)
      setAssignedAgent(match ? match.id : (task.assigned_agent || ''))
      setError(null)
    }
  }, [task, agents])

  async function handleRestart() {
    if (!task) return
    if (!assignedAgent) {
      setError('请先选择一个智能体')
      return
    }
    try {
      setRestarting(true)
      setError(null)
      await onRestart(task.id, assignedAgent)
      onClose()
    } catch (e: any) {
      setError(e.message || '重启失败，请重试')
    } finally {
      setRestarting(false)
    }
  }

  if (!task) return null

  return (
    <Dialog open={!!task} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>重新分配并重启任务</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-700 mb-1">任务名称</p>
            <p className="text-slate-900 bg-slate-50 rounded-sm px-3 py-2 text-sm">
              {task.title || '未命名任务'}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700 mb-1">当前状态</p>
            <Badge className={getTaskStatusBadgeClass(task.status)}>
              {getTaskStatusText(task.status)}
            </Badge>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">分配给智能体</label>
            <Select value={assignedAgent} onValueChange={setAssignedAgent}>
              <SelectTrigger>
                <SelectValue placeholder="选择智能体" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">待分配</SelectItem>
                {agents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-sm text-amber-700 text-sm">
            <p className="font-medium mb-1">⚠️ 重启将：</p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>清空任务执行结果和验证历史</li>
              <li>状态重置为 in_progress</li>
              <li>Agent 收到通知后自动领取执行</li>
            </ul>
          </div>
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-sm text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={restarting}>取消</Button>
          <Button onClick={handleRestart} disabled={restarting}>
            {restarting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {restarting ? '重启中...' : '重新分配并重启'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
