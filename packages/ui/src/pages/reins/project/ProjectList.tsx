import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi, goalsApi } from '../../../shared/utils/api'
import type { Project, Goal } from '../../../shared/utils/api'
import { FolderKanban, RefreshCw, AlertCircle, Plus, Search, X, Loader2, Trash2 } from 'lucide-react'
import { getProjectStatusText, getProjectStatusBadgeClass } from '../../../shared/utils/statusMap'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import CreateProject from '@/reins/components/CreateProject'

const ITEMS_PER_PAGE = 10

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([])
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Search and filter
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [goalFilter, setGoalFilter] = useState<string>('')
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  
  // Create project modal
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Delete project modal
  const [deleteModal, setDeleteModal] = useState<{ show: boolean; project: Project | null }>({ show: false, project: null })
  const [deleting, setDeleting] = useState(false)

  async function fetchProjects(goalId?: string) {
    try {
      setLoading(true)
      setError(null)
      const data = await projectsApi.list({ goal_id: goalId || undefined })
      setProjects(data)
    } catch (e: any) {
      setError(e.message || '工程列表加载失败，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }

  async function fetchGoals() {
    try {
      const data = await goalsApi.list()
      setGoals(data)
    } catch (e: any) {
      console.error('Failed to load goals:', e.message)
    }
  }

  useEffect(() => {
    fetchProjects()
    fetchGoals()
  }, [])

  // goalFilter 变化时重新请求 API（后端筛选）
  useEffect(() => {
    setCurrentPage(1)
    fetchProjects(goalFilter)
  }, [goalFilter])

  // Filter and search projects (goal 已在后端筛选，status 和 search 在前端)
  const filteredProjects = projects.filter(project => {
    const matchesSearch = !searchQuery || 
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (project.description && project.description.toLowerCase().includes(searchQuery.toLowerCase()))
    
    // "已完成" 同时匹配 completed 和 done
    if (!statusFilter) return matchesSearch
    if (statusFilter === 'completed') return matchesSearch && (project.status === 'completed' || project.status === 'done')
    return matchesSearch && project.status === statusFilter
  })

  // Pagination
  const totalPages = Math.ceil(filteredProjects.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const paginatedProjects = filteredProjects.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  // Reset to page 1 when status/search change (goal 已有独立 useEffect)
  useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery, statusFilter])

  async function handleDeleteProject() {
    if (!deleteModal.project) return
    
    try {
      setDeleting(true)
      await projectsApi.remove(deleteModal.project.id)
      setDeleteModal({ show: false, project: null })
      await fetchProjects()
    } catch (e: any) {
      console.error('Failed to delete project:', e.message)
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载工程列表...</p>
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
          <Button onClick={() => fetchProjects()}>重试</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-muted-foreground" />
            工程列表
          </h2>
          <p className="text-muted-foreground text-sm mt-1">共 {projects.length} 个工程</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => fetchProjects()}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4" />
            新建工程
          </Button>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search by title */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="搜索工程标题或描述..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        
        {/* Goal filter */}
        <Select value={goalFilter} onValueChange={setGoalFilter}>
          <SelectTrigger className="w-full sm:w-56">
            <SelectValue placeholder="全部目标" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部目标</SelectItem>
            {goals.map(goal => (
              <SelectItem key={goal.id} value={goal.id}>
                {goal.title || '未命名目标'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Status filter */}
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="active">进行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Project Table */}
      {filteredProjects.length === 0 ? (
        <div className="text-center py-16 rounded-lg border bg-card">
          <FolderKanban className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-lg text-muted-foreground mb-2">
            {searchQuery || statusFilter || goalFilter ? '没有找到匹配的工程' : '暂无工程'}
          </p>
          <p className="text-sm text-muted-foreground">
            {searchQuery || statusFilter || goalFilter ? '尝试调整搜索或过滤条件' : '点击「新建工程」创建第一个工程'}
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>工程标题</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>所属目标</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedProjects.map((project) => {
                  // Find the related goal
                  const relatedGoal = goals.find(g => g.id === project.goal_id)
                  
                  return (
                    <TableRow key={project.id}>
                      <TableCell>
                        <Link 
                          to={`/coordination/projects/${project.id}`}
                          className="font-medium text-foreground hover:text-blue-600 transition-colors"
                        >
                          {project.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <p className="text-sm text-muted-foreground line-clamp-2 max-w-xs">
                          {project.description || '—'}
                        </p>
                      </TableCell>
                      <TableCell>
                        {relatedGoal ? (
                          <Link 
                            to={`/coordination/goals/${relatedGoal.id}`}
                            className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                          >
                            {relatedGoal.title || '未命名目标'}
                          </Link>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge className={getProjectStatusBadgeClass(project.status)}>
                          {getProjectStatusText(project.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {new Date(project.created_at).toLocaleDateString('zh-CN', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                          })}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleteModal({ show: true, project })}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 rounded-lg border bg-card">
              <div className="text-sm text-muted-foreground">
                显示第 {startIndex + 1} - {Math.min(startIndex + ITEMS_PER_PAGE, filteredProjects.length)} 项，共 {filteredProjects.length} 项
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

      {/* Create Project Dialog */}
      <CreateProject
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        onCreated={() => fetchProjects()}
      />

      {/* Delete Project Confirmation Modal */}
      <Dialog open={deleteModal.show} onOpenChange={(open) => {
        if (!open) setDeleteModal({ show: false, project: null })
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <DialogDescription>
            确定删除工程 <span className="font-medium text-foreground">{deleteModal.project?.name}</span> 吗？
            此操作不可恢复。
          </DialogDescription>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteModal({ show: false, project: null })} disabled={deleting}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteProject} disabled={deleting}>
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
