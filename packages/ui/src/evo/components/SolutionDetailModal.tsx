/**
 * Sprint 68-73 + 76d-1: 方案详情弹窗组件
 * 复用位置：SolutionList、ProjectDetail、SolutionCenter、GoalDetail
 * Sprint 76d-1 增强：展开面板显示完整参数 + 关联工程列表 + 关联任务列表
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Separator } from '@/shared/components/ui/separator'
import { ScrollArea } from '@/shared/components/ui/scroll-area'
import {
  CheckCircle, XCircle, Trophy, Ban, Loader2, Trash2, Copy, ExternalLink,
  ChevronDown, ChevronRight, Calendar, Hash, Target, FileText,
  FolderKanban, ListTodo, ArrowUpRight, AlertCircle, CheckCircle2, Clock, XOctagon,
} from 'lucide-react'
import { solutionsApi, type Solution } from '@/evo/services/solutions'
import { projectsApi, tasksApi, type Project, type Task } from '@/shared/utils/api'
import { confirmAction } from '@/shared/utils/notify'

// ── 状态映射 ──────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; icon: React.ReactNode; variant: string }> = {
  compliant: { label: '达标', icon: <CheckCircle className="w-3.5 h-3.5" />, variant: 'success' },
  non_compliant: { label: '不达标', icon: <XCircle className="w-3.5 h-3.5" />, variant: 'destructive' },
  optimal: { label: '最优', icon: <Trophy className="w-3.5 h-3.5" />, variant: 'default' },
  rejected: { label: '否决', icon: <Ban className="w-3.5 h-3.5" />, variant: 'secondary' },
  pending: { label: '待评估', icon: <Loader2 className="w-3.5 h-3.5" />, variant: 'outline' },
}

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return (
    <Badge variant={config.variant as any} className="flex items-center gap-1">
      {config.icon}
      {config.label}
    </Badge>
  )
}

// ── 工程状态标签 ──────────────────────────────────────────────────────────

const PROJECT_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  active: { label: '进行中', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', icon: <Clock className="w-3 h-3" /> },
  completed: { label: '已完成', color: 'text-green-700', bg: 'bg-green-50 border-green-200', icon: <CheckCircle2 className="w-3 h-3" /> },
  failed: { label: '失败', color: 'text-red-700', bg: 'bg-red-50 border-red-200', icon: <XOctagon className="w-3 h-3" /> },
  paused: { label: '已暂停', color: 'text-yellow-700', bg: 'bg-yellow-50 border-yellow-200', icon: <AlertCircle className="w-3 h-3" /> },
}

function ProjectStatusTag({ status }: { status: string }) {
  const cfg = PROJECT_STATUS_CONFIG[status] || { label: status, color: 'text-gray-600', bg: 'bg-gray-50 border-gray-200', icon: null }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

// ── 任务状态标签 ──────────────────────────────────────────────────────────

const TASK_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  done: { label: '已完成', color: 'text-green-700', bg: 'bg-green-50 border-green-200', icon: <CheckCircle2 className="w-3 h-3" /> },
  failed: { label: '失败', color: 'text-red-700', bg: 'bg-red-50 border-red-200', icon: <XOctagon className="w-3 h-3" /> },
  in_progress: { label: '进行中', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', icon: <Clock className="w-3 h-3" /> },
  todo: { label: '待执行', color: 'text-gray-600', bg: 'bg-gray-50 border-gray-200', icon: <AlertCircle className="w-3 h-3" /> },
  timeout: { label: '超时', color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', icon: <AlertCircle className="w-3 h-3" /> },
}

function TaskStatusTag({ status }: { status: string }) {
  const cfg = TASK_STATUS_CONFIG[status] || { label: status || '未知', color: 'text-gray-600', bg: 'bg-gray-50 border-gray-200', icon: null }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}

// ── JSON 展开组件 ──────────────────────────────────────────────────────────

function JsonViewer({ data, label }: { data: Record<string, any>; label: string }) {
  const [expanded, setExpanded] = useState(false)
  const entries = Object.entries(data)

  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">无{label}</p>
  }

  return (
    <div className="space-y-2">
      <button
        className="flex items-center gap-1 text-sm font-medium text-foreground hover:text-blue-600 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        {label} ({entries.length} 项)
      </button>
      {expanded && (
        <div className="ml-4 space-y-1 border-l-2 border-muted pl-3">
          {entries.map(([key, value]) => (
            <div key={key} className="flex items-start gap-2 text-sm">
              <span className="text-muted-foreground font-mono text-xs shrink-0 w-32">{key}</span>
              <span className="text-foreground break-all">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── 解析 ID 列表（支持 JSON 数组或逗号分隔字符串） ─────────────────────────

function parseIdList(raw: unknown): string[] {
  if (!raw) return []
  if (Array.isArray(raw)) return raw.filter(Boolean) as string[]
  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (!trimmed) return []
    try {
      const parsed = JSON.parse(trimmed)
      if (Array.isArray(parsed)) return parsed.filter(Boolean) as string[]
    } catch {
      // 逗号分隔
      return trimmed.split(',').map(s => s.trim()).filter(Boolean)
    }
  }
  return []
}

// ── 关联工程列表 ──────────────────────────────────────────────────────────

function RelatedProjects({ projectIds, goalId }: { projectIds: string[]; goalId: string }) {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (projectIds.length === 0) { setLoading(false); return }
    setLoading(true)
    Promise.all(
      projectIds.map(id => projectsApi.get(id).catch(() => null))
    ).then(results => {
      setProjects(results.filter(Boolean) as Project[])
      setLoading(false)
    })
  }, [projectIds])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        加载关联工程...
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-1">
        <FolderKanban className="w-4 h-4 text-muted-foreground" />
        暂无关联工程
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        <FolderKanban className="w-4 h-4 text-blue-500" />
        关联工程 ({projects.length})
      </div>
      <div className="space-y-1.5">
        {projects.map(project => (
          <button
            key={project.id}
            className="w-full flex items-center justify-between p-2.5 rounded-lg border bg-card hover:bg-accent/50 transition-colors text-left cursor-pointer group"
            onClick={() => navigate(`/projects/${project.id}`)}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm text-foreground truncate">
                  {project.name || project.id}
                </span>
                <ArrowUpRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              {project.description && (
                <p className="text-xs text-muted-foreground truncate mt-0.5">{project.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              <ProjectStatusTag status={project.status} />
              <span className="text-xs text-muted-foreground font-mono">#{project.id.slice(0, 6)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── 关联任务列表 ──────────────────────────────────────────────────────────

function RelatedTasks({ taskIds, goalId }: { taskIds: string[]; goalId: string }) {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (taskIds.length === 0) { setLoading(false); return }
    setLoading(true)
    Promise.all(
      taskIds.map(id => tasksApi.get(id).catch(() => null))
    ).then(results => {
      setTasks(results.filter(Boolean) as Task[])
      setLoading(false)
    })
  }, [taskIds])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        加载关联任务...
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-1">
        <ListTodo className="w-4 h-4 text-muted-foreground" />
        暂无关联任务
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
        <ListTodo className="w-4 h-4 text-purple-500" />
        关联任务 ({tasks.length})
      </div>
      <div className="space-y-1.5">
        {tasks.map(task => (
          <button
            key={task.id}
            className="w-full flex items-center justify-between p-2.5 rounded-lg border bg-card hover:bg-accent/50 transition-colors text-left cursor-pointer group"
            onClick={() => navigate(`/tasks/${task.id}`)}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm text-foreground truncate">
                  {task.title || task.id}
                </span>
                <ArrowUpRight className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              {task.result_summary && (
                <p className="text-xs text-muted-foreground truncate mt-0.5">{task.result_summary}</p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0 ml-3">
              <TaskStatusTag status={task.status || ''} />
              <span className="text-xs text-muted-foreground font-mono">#{task.id.slice(0, 6)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────

interface SolutionDetailModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  solution: Solution | null
  onSuccess?: () => void
}

export default function SolutionDetailModal({ open, onOpenChange, solution, onSuccess }: SolutionDetailModalProps) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<Solution | null>(solution)

  useEffect(() => {
    setDetail(solution)
  }, [solution])

  // 如果传入的是 ID 而非完整对象，加载详情
  useEffect(() => {
    if (open && solution && !solution.name && solution.id) {
      setLoading(true)
      solutionsApi.get(solution.id)
        .then(setDetail)
        .catch(() => toast.error('加载方案详情失败'))
        .finally(() => setLoading(false))
    }
  }, [open, solution])

  async function handleSetOptimal() {
    if (!detail) return
    try {
      await solutionsApi.update(detail.id, { status: 'optimal' })
      toast.success('已标记为最优方案')
      onSuccess?.()
      onOpenChange(false)
    } catch (e: any) {
      toast.error(`操作失败：${e.message}`)
    }
  }

  async function handleReject() {
    if (!detail) return
    if (!(await confirmAction({ title: '否决方案', description: `确定否决方案「${detail.name}」吗？`, variant: 'destructive' }))) return
    try {
      await solutionsApi.update(detail.id, { status: 'rejected' })
      toast.success('已否决该方案')
      onSuccess?.()
      onOpenChange(false)
    } catch (e: any) {
      toast.error(`操作失败：${e.message}`)
    }
  }

  async function handleDelete() {
    if (!detail) return
    if (!(await confirmAction({ title: '删除方案', description: `确定删除方案「${detail.name}」吗？此操作不可恢复。`, variant: 'destructive' }))) return
    try {
      await solutionsApi.remove(detail.id)
      toast.success('方案已删除')
      onSuccess?.()
      onOpenChange(false)
    } catch (e: any) {
      toast.error(`删除失败：${e.message}`)
    }
  }

  if (!detail && !loading) return null

  // 解析关联 ID
  const projectIds = parseIdList(detail?.project_ids)
  const taskIds = parseIdList(detail?.task_ids)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-500" />
            方案详情
          </DialogTitle>
          <DialogDescription>
            {loading ? '加载中...' : `${detail?.name || '未命名'} · #${detail?.id?.slice(0, 8) || ''}`}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          </div>
        ) : detail ? (
          <ScrollArea className="max-h-[65vh] pr-4">
            <div className="space-y-5">
              {/* 基本信息 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">方案名称</span>
                  <p className="font-semibold text-foreground">{detail.name || '未命名'}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">状态</span>
                  <div><StatusBadge status={detail.status} /></div>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Hash className="w-3 h-3" /> 轮次
                  </span>
                  <p className="font-mono text-foreground">Round {detail.round ?? '—'}</p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">综合评分</span>
                  <p className="font-bold text-lg text-foreground">
                    {detail.score != null ? detail.score.toFixed(2) : '—'}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> 创建时间
                  </span>
                  <p className="text-sm text-foreground">
                    {detail.created_at ? new Date(detail.created_at).toLocaleString('zh-CN') : '—'}
                  </p>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">目标 ID</span>
                  <Button
                    variant="link"
                    className="p-0 h-auto font-mono text-xs text-muted-foreground"
                    onClick={() => navigate(`/coordination/goals/${detail.goal_id}`)}
                  >
                    {detail.goal_id || '—'}
                  </Button>
                </div>
              </div>

              <Separator />

              {/* 参数详情 */}
              <JsonViewer data={detail.parameters || {}} label="参数详情" />

              <Separator />

              {/* 约束条件 */}
              {detail.constraints && detail.constraints.length > 0 ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-1 text-sm font-medium">
                    <FileText className="w-4 h-4" /> 约束条件
                  </div>
                  <ul className="ml-4 list-disc space-y-1">
                    {detail.constraints.map((c, i) => (
                      <li key={i} className="text-sm text-muted-foreground">{c}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">无约束条件</p>
              )}

              <Separator />

              {/* 关联工程列表 */}
              <RelatedProjects projectIds={projectIds} goalId={detail.goal_id} />

              <Separator />

              {/* 关联任务列表 */}
              <RelatedTasks taskIds={taskIds} goalId={detail.goal_id} />

              {/* 额外元数据 */}
              {detail.metadata && Object.keys(detail.metadata).length > 0 && (
                <>
                  <Separator />
                  <JsonViewer data={detail.metadata} label="元数据" />
                </>
              )}
            </div>
          </ScrollArea>
        ) : null}

        {/* 操作按钮 */}
        {!loading && detail && (
          <DialogFooter className="flex gap-2 sm:gap-2">
            <Button variant="outline" size="sm" onClick={handleSetOptimal} disabled={detail.status === 'optimal'}>
              <Trophy className="w-3.5 h-3.5 mr-1" /> 标记最优
            </Button>
            <Button variant="outline" size="sm" onClick={handleReject} disabled={detail.status === 'rejected'}>
              <Ban className="w-3.5 h-3.5 mr-1" /> 否决
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete}>
              <Trash2 className="w-3.5 h-3.5 mr-1" /> 删除
            </Button>
            <Button variant="ghost" size="sm" onClick={() => { navigator.clipboard?.writeText(JSON.stringify(detail, null, 2)); toast.success('已复制') }}>
              <Copy className="w-3.5 h-3.5 mr-1" /> 复制 JSON
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
