import { useState, useEffect, useMemo } from 'react'
import { toast } from "sonner"
import { ConfirmDialog, confirmAction } from "@/shared/utils/notify"
import { Link, useNavigate } from 'react-router-dom'
import { goalsApi, projectsApi, tasksApi } from '../../../shared/utils/api'
import type { Goal } from '../../../shared/utils/api'
import { Target, RefreshCw, AlertCircle, Search, Plus, Loader2, Trash2, GitBranch } from 'lucide-react'
import { getGoalStatusWithClass } from '../../../shared/utils/statusMap'
import { getModeLabel, getDiversityLabel } from '../../../shared/utils/modeDisplay'
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/shared/components/ui/pagination'
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
import CreateGoal from './CreateGoal'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'

const ITEMS_PER_PAGE = 10

function mapPriority(priority: string | null): { text: string; variant: string } {
  const map: Record<string, { text: string; variant: string }> = {
    'P0': { text: 'P0-紧急', variant: 'destructive' },
    'P1': { text: 'P1-高', variant: 'warning' },
    'P2': { text: 'P2-中', variant: 'info' },
    'P3': { text: 'P3-低', variant: 'secondary' },
    'critical': { text: 'P0-紧急', variant: 'destructive' },
    'high': { text: 'P1-高', variant: 'warning' },
    'medium': { text: 'P2-中', variant: 'info' },
    'low': { text: 'P3-低', variant: 'secondary' },
  }
  return map[priority || ''] || { text: priority || '—', variant: 'secondary' }
}

function mapStatusVariant(status: string | null | undefined): string {
  const map: Record<string, string> = {
    'active': 'info',
    'in_progress': 'info',
    'completed': 'success',
    'done': 'success',
    'planned': 'secondary',
    'draft': 'secondary',
    'cancelled': 'secondary',
    'failed': 'destructive',
  }
  return map[status || ''] || 'secondary'
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffHours < 24) return `${diffHours} 小时前`
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays} 天前`
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

export default function GoalList() {
  const navigate = useNavigate()
  const [goals, setGoals] = useState<Goal[]>([])
  const [projectCountByGoal, setProjectCountByGoal] = useState<Record<string, number>>({})
  const [taskProgressByGoal, setTaskProgressByGoal] = useState<Record<string, { completed: number; total: number }>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Search and filter
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [priorityFilter, setPriorityFilter] = useState<string>('')
  const [modeFilter, setModeFilter] = useState<string>('')

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)

  // Create goal modal
  const [showCreateModal, setShowCreateModal] = useState(false)

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const [goalsData, projectStats, taskStats] = await Promise.all([
        goalsApi.list(),
        projectsApi.countByGoal(),
        tasksApi.countByGoal(),
      ])
      setGoals(goalsData)
      // Normalize project stats: handle both Record and array formats
      const projMap: Record<string, number> = {}
      if (Array.isArray(projectStats)) {
        projectStats.forEach((item: any) => { projMap[item.goal_id] = item.count })
      } else {
        Object.entries(projectStats).forEach(([k, v]) => { projMap[k] = (v as any).count ?? v })
      }
      setProjectCountByGoal(projMap)
      // Normalize task stats: handle both Record and array formats
      const taskMap: Record<string, { completed: number; total: number }> = {}
      if (Array.isArray(taskStats)) {
        taskStats.forEach((item: any) => { taskMap[item.goal_id] = { completed: item.completed, total: item.total } })
      } else {
        Object.entries(taskStats).forEach(([k, v]) => {
          const val = v as any
          taskMap[k] = { completed: val.completed ?? 0, total: val.total ?? 0 }
        })
      }
      setTaskProgressByGoal(taskMap)
    } catch (e: any) {
      setError(e.message || '加载失败，请检查后端服务')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Filter
  const filteredGoals = useMemo(() => {
    let result = goals
    if (statusFilter) {
      result = result.filter(g => g.status === statusFilter)
    }
    if (priorityFilter) {
      result = result.filter(g => g.priority === priorityFilter)
    }
    if (modeFilter) {
      result = result.filter(g => g.mode === modeFilter)
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(g =>
        (g.title || '').toLowerCase().includes(q) ||
        (g.description || '').toLowerCase().includes(q)
      )
    }
    return result.sort((a, b) => {
      const aTime = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const bTime = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return bTime - aTime
    })
  }, [goals, statusFilter, priorityFilter, modeFilter, searchQuery])

  const totalPages = Math.max(1, Math.ceil(filteredGoals.length / ITEMS_PER_PAGE))
  const paginatedGoals = filteredGoals.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)

  const handleReset = () => {
    setSearchQuery('')
    setStatusFilter('')
    setPriorityFilter('')
    setModeFilter('')
    setCurrentPage(1)
  }

  const handleDeleteGoal = async (goal: Goal) => {
    const title = goal.title || '未命名目标'
    if (!(await confirmAction({ title: '删除目标', description: `确定删除目标「${title}」吗？`, variant: 'destructive' }))) return
    try {
      await goalsApi.remove(goal.id)
      setGoals(prev => prev.filter(g => g.id !== goal.id))
    } catch (e: any) {
      toast.error(`删除失败：${e.message}`)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载中...</p>
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
          <Button onClick={fetchData}>重试</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Target className="w-5 h-5 text-muted-foreground" />
            目标管理
          </h1>
          <p className="text-sm text-muted-foreground mt-1">管理所有业务目标</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4" />
          新建目标
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1) }}
            placeholder="搜索目标..."
            className="pl-10"
          />
        </div>

        <Select value={statusFilter || 'all'} onValueChange={(v) => { setStatusFilter(v === 'all' ? '' : v); setCurrentPage(1) }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="active">进行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="planned">已计划</SelectItem>
            <SelectItem value="cancelled">已取消</SelectItem>
          </SelectContent>
        </Select>

        <Select value={priorityFilter || 'all'} onValueChange={(v) => { setPriorityFilter(v === 'all' ? '' : v); setCurrentPage(1) }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部优先级" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部优先级</SelectItem>
            <SelectItem value="P0">P0-紧急</SelectItem>
            <SelectItem value="P1">P1-高</SelectItem>
            <SelectItem value="P2">P2-中</SelectItem>
            <SelectItem value="P3">P3-低</SelectItem>
          </SelectContent>
        </Select>

        <Select value={modeFilter || 'all'} onValueChange={(v) => { setModeFilter(v === 'all' ? '' : v); setCurrentPage(1) }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部模式" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部模式</SelectItem>
            <SelectItem value="engineering">🔧 工程模式</SelectItem>
            <SelectItem value="research">🔬 研究模式</SelectItem>
          </SelectContent>
        </Select>

        {(statusFilter || priorityFilter || modeFilter || searchQuery) && (
          <Button variant="ghost" size="sm" onClick={handleReset}>
            重置筛选
          </Button>
        )}

        <Button variant="outline" size="icon" onClick={fetchData} title="刷新">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card">
        {filteredGoals.length === 0 ? (
          <div className="text-center py-16">
            <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-2">暂无目标</p>
            <Button variant="link" onClick={() => setShowCreateModal(true)}>
              点击「新建目标」开始
            </Button>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>目标名称</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>模式</TableHead>
                  <TableHead>工程数</TableHead>
                  <TableHead>任务进度</TableHead>
                  <TableHead>更新时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedGoals.map(goal => {
                  const statusInfo = getGoalStatusWithClass(goal.status)
                  const priorityInfo = mapPriority(goal.priority)
                  return (
                    <TableRow
                      key={goal.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/coordination/goals/${goal.id}`)}
                    >
                      <TableCell>
                        <span className="font-medium text-foreground hover:text-blue-600">
                          {goal.title || '未命名目标'}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={priorityInfo.variant as any}>
                          {priorityInfo.text}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={mapStatusVariant(goal.status) as any}>
                          {statusInfo.text}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {(() => {
                          const label = getModeLabel(goal.mode || 'engineering')
                          const diversity = goal.diversity ? `（${getDiversityLabel(goal.diversity)}）` : ''
                          return <span>{label}{diversity}</span>
                        })()}
                      </TableCell>
                      <TableCell>
                        {projectCountByGoal[goal.id] > 0 ? (
                          <span className="text-foreground">{projectCountByGoal[goal.id]}</span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {taskProgressByGoal[goal.id] && taskProgressByGoal[goal.id].total > 0 ? (
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-blue-500 rounded-full"
                                style={{ width: `${(taskProgressByGoal[goal.id].completed / taskProgressByGoal[goal.id].total) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground">{taskProgressByGoal[goal.id].completed}/{taskProgressByGoal[goal.id].total}</span>
                          </div>
                        ) : <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell>
                        <span className="text-muted-foreground text-xs">
                          {formatRelativeTime(goal.updated_at)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="任务分解与流程"
                            onClick={() => navigate(`/goals/${goal.id}/tree`)}
                          >
                            <GitBranch className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteGoal(goal)}
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

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-3 border-t">
                <div className="text-sm text-muted-foreground">
                  显示第 {(currentPage - 1) * ITEMS_PER_PAGE + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, filteredGoals.length)} 项，共 {filteredGoals.length} 项
                </div>
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={(page) => setCurrentPage(page)}
                />
              </div>
            )}
          </>
        )}
      </div>
      {/* Create Goal Dialog */}
      <CreateGoal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        onCreated={() => { fetchData() }}
      />

      <ConfirmDialog />
    </div>
  )
}
