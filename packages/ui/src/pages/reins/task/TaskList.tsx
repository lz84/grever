import { useState, useEffect } from 'react'
import { TASKS } from '../../../shared/api/paths'
import { toast } from "sonner"
import { ConfirmDialog, confirmAction } from "@/shared/utils/notify"
import { Link, useSearchParams } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'
import { tasksApi, goalsApi, projectsApi } from '../../../shared/utils/api'
import type { Task, Project, Goal } from '../../../shared/utils/api'
import { ListTodo, RefreshCw, AlertCircle, Search, Filter, ChevronRight, Loader2, CheckCircle, XCircle, RotateCw, Plus, X, Trash2, FileText, FolderOpen, Edit2 } from 'lucide-react'
import { getTaskStatusText, getTaskStatusBadgeClass } from '../../../shared/utils/statusMap'
import { getAgentName } from '../../../shared/utils/agentMap'
import { Pagination } from '@/shared/components/ui/pagination'
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
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Textarea } from '@/shared/components/ui/textarea'
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

const ITEMS_PER_PAGE = 10

function mapTaskPriority(priority: number | string | null): string {
  if (priority === null || priority === undefined) return '普通'
  const strMap: Record<string, string> = {
    'critical': '紧急', 'high': '高', 'medium': '普通', 'low': '低', 'lowest': '最低',
    '0': '紧急', '1': '高', '2': '普通', '3': '低', '4': '最低',
  }
  const key = typeof priority === 'number' ? String(priority) : String(priority).toLowerCase()
  return strMap[key] || '普通'
}

function getPriorityVariant(priority: number | string | null): string {
  const p = typeof priority === 'number' ? String(priority) : String(priority || '').toLowerCase()
  if (p === 'critical' || p === '0') return 'destructive'
  if (p === 'high' || p === '1') return 'warning'
  if (p === 'low' || p === '3' || p === 'lowest' || p === '4' || p === '5') return 'secondary'
  return 'info'
}

export default function TaskList() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialStatus = searchParams.get('status') || 'all'

  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Filter states
  const [statusFilter, setStatusFilter] = useState<string>(initialStatus)
  const [statusOptions, setStatusOptions] = useState<{value: string; label: string}[]>([])
  const [assignedFilter, setAssignedFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [goalFilter, setGoalFilter] = useState<string>('all')
  const [projectFilter, setProjectFilter] = useState<string>('all')

  // 获取统一状态列表（含 fallback）
  useEffect(() => {
    fetch(TASKS.GET_STATUSES)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          setStatusOptions([
            { value: 'all', label: '全部状态' },
            ...data.filter(s => s.category === 'db').map(s => ({ value: s.value, label: s.label })),
          ]);
        }
      })
      .catch(() => {
        setStatusOptions([
          { value: 'all', label: '全部状态' },
          { value: 'todo', label: '待处理' },
          { value: 'in_progress', label: '进行中' },
          { value: 'done', label: '已完成' },
          { value: 'failed', label: '失败' },
          { value: 'timeout', label: '已超时' },
          { value: 'paused', label: '已暂停' },
        ]);
      });
  }, []);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)

  // Goals and projects for filter dropdown
  const [goals, setGoals] = useState<Goal[]>([])
  const [projects, setProjects] = useState<Project[]>([])

  // Unique agents for filter dropdown
  const [agents, setAgents] = useState<Set<string>>(new Set())

  // Create task modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDesc, setNewTaskDesc] = useState('')
  const [newTaskProject, setNewTaskProject] = useState('all')
  const [newTaskGoal, setNewTaskGoal] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState('medium')
  const [newTaskAgent, setNewTaskAgent] = useState('all')
  const [modalProjects, setModalProjects] = useState<Project[]>([])
  // hook replaced with module-level confirmAction

  // Doc refs & workspace path
  const [newTaskDocRefs, setNewTaskDocRefs] = useState('')
  const [newTaskWorkspacePath, setNewTaskWorkspacePath] = useState('')
  const [overrideWorkspace, setOverrideWorkspace] = useState(false)

  async function fetchTasks() {
    try {
      setLoading(true)
      setError(null)

      const params: Record<string, string> = {}
      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter
      }
      if (assignedFilter && assignedFilter !== 'all') {
        params.assigned_agent = assignedFilter
      }
      if (goalFilter && goalFilter !== 'all') {
        params.goal_id = goalFilter
      }
      if (projectFilter && projectFilter !== 'all') {
        params.project_id = projectFilter
      }

      const data = await tasksApi.list(params)
      setTasks(data)

      const uniqueAgents = new Set<string>()
      const uniqueProjects = new Map<string, string>()
      data.forEach((task: Task) => {
        if (task.assigned_agent) {
          uniqueAgents.add(task.assigned_agent)
        }
        if (task.project_id) {
          if (!uniqueProjects.has(task.project_id)) {
            uniqueProjects.set(task.project_id, task.project_id)
          }
        }
      })
      setAgents(uniqueAgents)
      setProjects(Array.from(uniqueProjects.keys()).map(id => ({ id, name: id } as Project)))

      try {
        const allProjects = await projectsApi.list()
        const projMap = new Map<string, string>()
        allProjects.forEach(p => projMap.set(p.id, p.name))
        setProjects(data => data.map(p => ({
          ...p,
          name: projMap.get(p.id) || p.name
        })))
        setModalProjects(allProjects)
      } catch(e) {
        // API might not work, use task-derived data
      }
    } catch (e: any) {
      setError(e.message || '任务列表加载失败,请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    goalsApi.list().then(setGoals).catch(() => {})
    projectsApi.list().then(setProjects).catch(() => {})
  }, [])

  async function handleCreateTask() {
    if (!newTaskTitle.trim()) return
    try {
      setActionLoading('creating')
      const data: any = { title: newTaskTitle.trim() }
      if (newTaskDesc.trim()) data.description = newTaskDesc.trim()
      if (newTaskProject && newTaskProject !== 'all') data.project_id = newTaskProject
      if (newTaskGoal) data.goal_id = newTaskGoal
      data.priority = newTaskPriority
      if (newTaskAgent && newTaskAgent !== 'all') data.assigned_agent = newTaskAgent

      if (newTaskDocRefs.trim()) {
        data.doc_refs = newTaskDocRefs.trim().split('\n').map((l: string) => l.trim()).filter((l: string) => l.length > 0)
      }
      if (newTaskWorkspacePath.trim()) {
        data.workspace_path = newTaskWorkspacePath.trim()
      }

      await tasksApi.create(data)
      setShowCreateModal(false)
      setNewTaskTitle('')
      setNewTaskDesc('')
      setNewTaskProject('all')
      setNewTaskGoal('')
      setNewTaskPriority('medium')
      setNewTaskAgent('all')
      setNewTaskDocRefs('')
      setNewTaskWorkspacePath('')
      setOverrideWorkspace(false)
      await fetchTasks()
    } catch (e: any) {
      setError(e.message || '创建任务失败')
    } finally {
      setActionLoading(null)
    }
  }

  useEffect(() => {
    setProjectFilter('all')
  }, [goalFilter])

  async function handleCompleteTask(taskId: string) {
    try {
      setActionLoading(taskId)
      await tasksApi.completeTask(taskId, {
        status: 'done',
      })
      await fetchTasks()
    } catch (e: any) {
      setError(e.message || '完成任务失败')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleFailTask(taskId: string) {
    try {
      setActionLoading(taskId)
      await tasksApi.failTask(taskId, {
        error_type: 'user_cancelled',
        error_message: '用户标记为失败',
        retry_count: 0,
        max_retries: 3,
      })
      await fetchTasks()
    } catch (e: any) {
      setError(e.message || '标记任务失败失败')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleRetryTask(taskId: string) {
    try {
      setActionLoading(taskId)
      await tasksApi.retryTask(taskId)
      await fetchTasks()
    } catch (e: any) {
      setError(e.message || '重试任务失败')
    } finally {
      setActionLoading(null)
    }
  }

  async function handleDeleteTask(taskId: string, taskTitle: string | null) {
    if (!(await confirmAction({ title: '删除任务', description: `确定删除任务 "${taskTitle || '未命名任务'}" 吗？`, variant: 'destructive' }))) return
    try {
      setActionLoading(taskId)
      await tasksApi.deleteTask(taskId)
      await fetchTasks()
    } catch (e: any) {
      setError(e.message || '删除任务失败')
    } finally {
      setActionLoading(null)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [statusFilter, assignedFilter, goalFilter, projectFilter])

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = !searchQuery ||
      (task.title && task.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (task.description && task.description.toLowerCase().includes(searchQuery.toLowerCase()))

    let matchesStatus = !statusFilter || statusFilter === 'all'
    if (!matchesStatus && statusFilter) {
      if (statusFilter === 'todo') matchesStatus = task.status === 'todo' || task.status === 'pending'
      else if (statusFilter === 'completed') matchesStatus = task.status === 'completed' || task.status === 'done'
      else matchesStatus = String(task.status || '').toLowerCase() === statusFilter.toLowerCase()
    }

    const matchesAssigned = !assignedFilter || assignedFilter === 'all' ||
      task.assigned_agent === assignedFilter

    return matchesSearch && matchesStatus && matchesAssigned
  }).sort((a, b) => {
    // 按创建日期倒序（最新的在前）
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
    return bTime - aTime
  })

  const isActionable = (status: string | null): boolean => {
    const statusStr = String(status || '').toLowerCase()
    return statusStr === 'pending' || statusStr === 'in_progress'
  }

  const totalPages = Math.ceil(filteredTasks.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const paginatedTasks = filteredTasks.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, statusFilter, assignedFilter, goalFilter, projectFilter])

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载任务列表...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <Button onClick={fetchTasks}>重试</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <ListTodo className="w-5 h-5 text-muted-foreground" />
            任务列表
          </h2>
          <p className="text-muted-foreground text-sm mt-1">共 {filteredTasks.length} 个任务</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => navigate("/coordination/tasks/create")}>
            <Plus className="w-4 h-4" />
            新建任务
          </Button>
          <Button variant="outline" onClick={fetchTasks}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索任务标题或描述..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Goal filter */}
          <Select value={goalFilter} onValueChange={setGoalFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="全部目标" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部目标</SelectItem>
              {goals.map(g => (
                <SelectItem key={g.id} value={g.id}>
                  {(g.title || g.id).slice(0, 15)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Project filter */}
          <Select value={projectFilter} onValueChange={setProjectFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="全部工程" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部工程</SelectItem>
              {projects
                .filter(p => goalFilter === 'all' || p.goal_id === goalFilter)
                .map(proj => (
                  <SelectItem key={proj.id} value={proj.id}>
                    {proj.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>

          {/* Status filter */}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Assigned filter */}
          <Select value={assignedFilter} onValueChange={setAssignedFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="全部分配" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分配</SelectItem>
              {[...agents].sort().map(agent => (
                <SelectItem key={agent} value={agent}>
                  {getAgentName(agent)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Task Table */}
      {filteredTasks.length === 0 ? (
        <div className="text-center py-16 rounded-lg border bg-card">
          <ListTodo className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-lg text-muted-foreground mb-2">
            {searchQuery || statusFilter || assignedFilter ? '没有找到匹配的任务' : '暂无任务'}
          </p>
          <p className="text-sm text-muted-foreground">
            {searchQuery || statusFilter || assignedFilter ? '尝试调整搜索或过滤条件' : '系统会自动创建任务,或在目标详情页中手动创建'}
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-lg border overflow-hidden" style={{ maxHeight: 'calc(100vh - 340px)' }}>
            <div className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 400px)' }}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>任务名称</TableHead>
                  <TableHead>所属工程</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>分配给</TableHead>
                  <TableHead>创建日期</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedTasks.map((task) => {
                  const statusStr = String(task.status || '').toLowerCase()
                  const isCompleted = statusStr.includes('completed') || statusStr === 'done'
                  const isFailed = statusStr.includes('failed')
                  const isActionableTask = isActionable(task.status)

                  return (
                    <TableRow key={task.id} className={isCompleted ? 'opacity-75' : ''}>
                      <TableCell>
                        <Link
                          to={`/coordination/tasks/${task.id}`}
                          className="font-medium text-foreground hover:text-blue-600 transition-colors"
                        >
                          {task.title || '未命名任务'}
                        </Link>
                        {task.description && (
                          <p className="text-sm text-muted-foreground mt-1 line-clamp-2 max-w-xs">
                            {task.description}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        {task.project_id ? (() => {
                          const proj = projects.find(p => p.id === task.project_id)
                          return proj ? (
                            <span className="text-sm text-slate-700 truncate max-w-[160px] block" title={proj.name || proj.id}>
                              {proj.name || proj.id}
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">-</span>
                          )
                        })() : (
                          <span className="text-muted-foreground text-xs">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getPriorityVariant(task.priority) as any}>
                          {mapTaskPriority(task.priority)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge className={getTaskStatusBadgeClass(task.status)}>
                          {getTaskStatusText(task.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {task.assigned_agent ? (
                          <span className="text-sm flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-blue-500" />
                            {getAgentName(task.assigned_agent)}
                          </span>
                        ) : (
                          <span className="text-sm text-muted-foreground">未分配</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-foreground">
                          {formatDate(task.created_at)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {isActionableTask ? (
                            <>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleCompleteTask(task.id)}
                                disabled={actionLoading === task.id}
                                title="任务完成"
                              >
                                <CheckCircle className="w-4 h-4 text-green-600" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleFailTask(task.id)}
                                disabled={actionLoading === task.id}
                                title="标记失败"
                              >
                                <XCircle className="w-4 h-4 text-red-600" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRetryTask(task.id)}
                                disabled={actionLoading === task.id}
                                title="重试任务"
                              >
                                <RotateCw className="w-4 h-4 text-blue-600" />
                              </Button>
                            </>
                          ) : isFailed ? (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRetryTask(task.id)}
                              disabled={actionLoading === task.id}
                              title="快速重试"
                            >
                              <RotateCw className="w-4 h-4 text-blue-600" />
                            </Button>
                          ) : null}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteTask(task.id, task.title)}
                            disabled={actionLoading === task.id}
                            title="删除任务"
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 rounded-lg border bg-card">
              <div className="text-sm text-muted-foreground">
                显示第 {startIndex + 1} - {Math.min(startIndex + ITEMS_PER_PAGE, filteredTasks.length)} 项,共 {filteredTasks.length} 项
              </div>
              <Pagination 
                currentPage={currentPage} 
                totalPages={totalPages} 
                onPageChange={setCurrentPage} 
              />
            </div>
          )}
        </>
      )}

      {/* Create Task Modal */}
      <Dialog open={showCreateModal} onOpenChange={(open) => {
        if (!open) {
          setShowCreateModal(false)
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建任务</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="task-title">任务名称 *</Label>
              <Input 
                id="task-title"
                type="text" 
                value={newTaskTitle} 
                onChange={e => setNewTaskTitle(e.target.value)} 
                placeholder="输入任务名称" 
              />
            </div>
            <div>
              <Label htmlFor="task-desc">描述</Label>
              <Textarea 
                id="task-desc"
                value={newTaskDesc} 
                onChange={e => setNewTaskDesc(e.target.value)} 
                rows={2} 
                placeholder="任务描述" 
              />
            </div>
            <div>
              <Label htmlFor="task-project">所属工程</Label>
              <Select 
                value={newTaskProject} 
                onValueChange={(v) => {
                  setNewTaskProject(v)
                  const proj = modalProjects.find(p => p.id === v)
                  if (proj?.goal_id) {
                    setNewTaskGoal(proj.goal_id)
                  } else {
                    setNewTaskGoal('')
                  }
                }}
              >
                <SelectTrigger id="task-project">
                  <SelectValue placeholder="无" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">无</SelectItem>
                  {modalProjects.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {newTaskGoal && (
              <div>
                <Label>所属目标（由工程自动关联）</Label>
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  {goals.find(g => g.id === newTaskGoal)?.title || newTaskGoal}
                </div>
              </div>
            )}
            <div>
              <Label htmlFor="task-priority">优先级</Label>
              <Select value={newTaskPriority} onValueChange={setNewTaskPriority}>
                <SelectTrigger id="task-priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">P0-紧急</SelectItem>
                  <SelectItem value="high">P1-高</SelectItem>
                  <SelectItem value="medium">P2-中</SelectItem>
                  <SelectItem value="low">P3-低</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="task-agent">分配给</Label>
              <Select value={newTaskAgent} onValueChange={setNewTaskAgent}>
                <SelectTrigger id="task-agent">
                  <SelectValue placeholder="未分配" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">未分配</SelectItem>
                  {[...agents].sort().map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="task-docrefs">文档引用 (doc_refs)</Label>
              <Textarea
                id="task-docrefs"
                value={newTaskDocRefs}
                onChange={e => setNewTaskDocRefs(e.target.value)}
                className="font-mono"
                rows={3}
                placeholder={"每行一个文档路径，如 docs/sprint58-plan.md#Phase0"}
              />
            </div>
            <div>
              <Label htmlFor="task-workspace">工作目录 (workspace_path)</Label>
              {!overrideWorkspace ? (
                <div className="flex gap-2">
                  <Input
                    id="task-workspace"
                    type="text"
                    value={newTaskWorkspacePath || 'D:\\work\\research\\agents-nexus'}
                    disabled
                    className="flex-1 bg-muted font-mono cursor-not-allowed"
                  />
                  <Button type="button" variant="outline" onClick={() => setOverrideWorkspace(true)}>
                    <Edit2 className="w-3.5 h-3.5" />
                    覆盖
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Input
                    id="task-workspace"
                    type="text"
                    value={newTaskWorkspacePath}
                    onChange={e => setNewTaskWorkspacePath(e.target.value)}
                    className="flex-1 font-mono"
                    placeholder="D:\work\research\agents-nexus"
                  />
                  <Button type="button" variant="outline" onClick={() => { setOverrideWorkspace(false); setNewTaskWorkspacePath('') }}>
                    恢复默认
                  </Button>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>取消</Button>
            <Button onClick={handleCreateTask} disabled={!newTaskTitle.trim() || actionLoading === 'creating'}>
              {actionLoading === 'creating' ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <ConfirmDialog />
    </div>
  )
}
