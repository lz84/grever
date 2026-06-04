import { useState, useEffect, useCallback } from 'react'
import { toast } from "sonner"
import { useConfirmDialog } from "@/shared/utils/notify"
import { adminApi } from '../../shared/services/adminApi'
import type { TaskAdminInfo } from '../../shared/services/adminApi'
import { RefreshCw, Loader2, AlertTriangle, RotateCcw } from 'lucide-react'
import { Card, CardContent } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'

export default function TaskManagement() {
  const [tasks, setTasks] = useState<TaskAdminInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('')
  const { confirm, ConfirmDialog } = useConfirmDialog()

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const params: Record<string, string | number | boolean | undefined> = { limit: 200 }
      if (filterStatus) params.status = filterStatus
      const data = await adminApi.listTasks(params)
      setTasks(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [filterStatus])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const showToast = (msg: string) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(null), 3000)
  }

  async function handleResetTask(task: TaskAdminInfo) {
    setActionLoading(task.id)
    try {
      const res = await adminApi.resetTask(task.id)
      showToast(res.message)
      await fetchData()
    } catch (e: any) {
      showToast(`操作失败: ${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleCleanupZombies() {
    if (!(await confirm({ title: '清理僵尸任务', description: '确定要清理所有僵尸任务吗？', variant: 'destructive' }))) return
    setActionLoading('cleanup')
    try {
      const res = await adminApi.cleanupZombieTasks()
      showToast(`清理完成: ${res.cleaned_count} 个任务已处理。${res.details.join('; ')}`)
      await fetchData()
    } catch (e: any) {
      showToast(`清理失败: ${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  function formatTime(isoStr: string | null): string {
    if (!isoStr) return '—'
    try {
      const d = new Date(isoStr)
      const now = new Date()
      const diffMs = now.getTime() - d.getTime()
      const diffMin = Math.floor(diffMs / 60000)
      if (diffMin < 1) return '刚刚'
      if (diffMin < 60) return `${diffMin} 分钟前`
      const diffHr = Math.floor(diffMin / 60)
      if (diffHr < 24) return `${diffHr} 小时前`
      const diffDay = Math.floor(diffHr / 24)
      return `${diffDay} 天前`
    } catch {
      return isoStr
    }
  }

  function getStatusBadgeVariant(status: string): 'success' | 'warning' | 'destructive' | 'secondary' | 'info' | 'outline' {
    switch (status) {
      case 'done': case 'completed': return 'success'
      case 'todo': case 'pending': return 'info'
      case 'in_progress': return 'warning'
      case 'failed': case 'error': return 'destructive'
      case 'verifying': return 'outline'
      case 'blocked': return 'warning'
      case 'timeout': return 'destructive'
      default: return 'secondary'
    }
  }

  function isStuck(status: string): boolean {
    return ['verifying', 'blocked', 'timeout', 'in_progress', 'failed', 'error'].includes(status)
  }

  // Stats
  const stuckCount = tasks.filter(t => isStuck(t.status)).length
  const doneCount = tasks.filter(t => t.status === 'done' || t.status === 'completed').length
  const todoCount = tasks.filter(t => t.status === 'todo' || t.status === 'pending').length

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 bg-slate-900 text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-sm animate-fade-in">
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground">任务管理</h2>
          <p className="text-sm text-muted-foreground mt-1">重置卡住的任务、清理僵尸任务</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleCleanupZombies}
            disabled={actionLoading === 'cleanup'}
            className="border-amber-200 text-amber-700 hover:bg-amber-50"
          >
            {actionLoading === 'cleanup' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <AlertTriangle className="w-4 h-4 mr-2" />}
            清理僵尸任务
          </Button>
          <Button variant="outline" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">总计</div>
            <div className="text-2xl font-bold text-foreground">{tasks.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">待处理</div>
            <div className="text-2xl font-bold text-blue-600">{todoCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">已完成</div>
            <div className="text-2xl font-bold text-green-600">{doneCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">卡住 ⚠️</div>
            <div className="text-2xl font-bold text-red-600">{stuckCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">状态过滤:</span>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="全部" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            <SelectItem value="todo">todo</SelectItem>
            <SelectItem value="in_progress">in_progress</SelectItem>
            <SelectItem value="done">done</SelectItem>
            <SelectItem value="failed">failed</SelectItem>
            <SelectItem value="verifying">verifying</SelectItem>
            <SelectItem value="blocked">blocked</SelectItem>
            <SelectItem value="timeout">timeout</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Task List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">加载中...</span>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-48">任务 ID</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead className="w-32">状态</TableHead>
                  <TableHead className="w-32">分配 Agent</TableHead>
                  <TableHead className="w-32">更新时间</TableHead>
                  <TableHead className="text-right w-28">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map(task => (
                  <TableRow key={task.id} className={isStuck(task.status) ? 'bg-red-50/30' : ''}>
                    <TableCell>
                      <span className="font-mono text-xs text-muted-foreground" title={task.id}>
                        {task.id.length > 20 ? task.id.substring(0, 20) + '...' : task.id}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-foreground truncate max-w-xs" title={task.title}>
                        {task.title}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(task.status)} className="flex items-center gap-1 w-fit">
                        {isStuck(task.status) && <AlertTriangle className="w-3 h-3" />}
                        {task.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground font-mono">
                        {task.assigned_agent || '—'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {formatTime(task.updated_at)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleResetTask(task)}
                        disabled={actionLoading === task.id}
                        className={
                          isStuck(task.status)
                            ? 'border-amber-200 text-amber-700 hover:bg-amber-50'
                            : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                        }
                        title="重置为 todo"
                      >
                        {actionLoading === task.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
                        <span className="ml-1">重置</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {tasks.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                      暂无任务数据
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      <ConfirmDialog />
    </div>
  )
}
