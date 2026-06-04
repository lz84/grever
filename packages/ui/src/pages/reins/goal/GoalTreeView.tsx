import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { goalsApi, projectsApi, tasksApi } from '../../../shared/utils/api'
import type { Goal, Project, Task } from '../../../shared/utils/api'
import { ArrowLeft, RefreshCw, Plus, Loader2, AlertCircle, ChevronDown, ChevronRight, Target, FolderKanban, ListTodo, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'

interface TreeNode {
  id: string
  type: 'goal' | 'project' | 'task'
  name: string
  status: string
  goal_id?: string
  project_id?: string
  children?: TreeNode[]
  _collapsed?: boolean
}

function getStatusBadge(status: string) {
  const s = status?.toLowerCase() || ''
  if (s === 'active' || s === 'in_progress') return { variant: 'info' as const, label: '进行中' }
  if (s === 'completed' || s === 'done') return { variant: 'success' as const, label: '已完成' }
  if (s === 'planned' || s === 'todo' || s === 'pending') return { variant: 'secondary' as const, label: '计划中' }
  if (s === 'failed') return { variant: 'destructive' as const, label: '失败' }
  if (s === 'cancelled') return { variant: 'secondary' as const, label: '已取消' }
  return { variant: 'secondary' as const, label: status || '未知' }
}

export default function GoalTreeView() {
  const { id: goalId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [goal, setGoal] = useState<Goal | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')

  const fetchData = useCallback(async () => {
    if (!goalId) return
    try {
      setLoading(true)
      setError(null)
      const [goalsData, projectsData, tasksData] = await Promise.all([
        goalsApi.list(),
        projectsApi.list({ goal_id: goalId }),
        tasksApi.list({ goal_id: goalId }),
      ])
      const currentGoal = goalsData.find((g: Goal) => g.id === goalId) || null
      setGoal(currentGoal)
      setProjects(projectsData)
      setTasks(tasksData)
    } catch (e: any) {
      setError(e.message || '加载失败，请检查后端服务是否正常运行')
    } finally {
      setLoading(false)
    }
  }, [goalId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  function toggleCollapse(id: string) {
    setCollapsed(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function isCollapsed(id: string) {
    return collapsed.has(id)
  }

  function filterNodes(nodes: TreeNode[], query: string): TreeNode[] {
    if (!query) return nodes
    return nodes.filter(n => n.name.toLowerCase().includes(query.toLowerCase()))
      .map(n => ({
        ...n,
        children: n.children ? filterNodes(n.children, query) : undefined,
      }))
      .filter(n => n.name.toLowerCase().includes(query.toLowerCase()) || (n.children && n.children.length > 0))
  }

  // Build tree
  const tree: TreeNode[] = goal ? [{
    id: goal.id,
    type: 'goal',
    name: goal.title || '未命名目标',
    status: goal.status || 'planned',
    children: projects.map(p => ({
      id: p.id,
      type: 'project' as const,
      name: p.name || '未命名项目',
      status: p.status || 'planned',
      goal_id: p.goal_id || undefined,
      children: tasks
        .filter(t => t.project_id === p.id)
        .map(t => ({
          id: t.id,
          type: 'task' as const,
          name: t.title || '未命名任务',
          status: t.status || 'pending',
          project_id: t.project_id || undefined,
        })),
    })),
  }] : []

  const filteredTree = filterNodes(tree, searchQuery)

  function renderNode(node: TreeNode, depth: number = 0) {
    const statusInfo = getStatusBadge(node.status)
    const hasChildren = node.children && node.children.length > 0
    const collapsed = isCollapsed(node.id)
    const filteredChildren = searchQuery && node.children
      ? filterNodes(node.children, searchQuery)
      : node.children

    const indent = depth * 24

    const icons: Record<string, React.ReactNode> = {
      goal: <Target className="w-4 h-4 text-purple-500" />,
      project: <FolderKanban className="w-4 h-4 text-emerald-500" />,
      task: <ListTodo className="w-4 h-4 text-blue-500" />,
    }

    return (
      <div key={node.id}>
        <div
          className="flex items-center gap-2 py-2 px-3 hover:bg-muted/50 rounded-md transition-colors cursor-pointer group"
          style={{ paddingLeft: `${12 + indent}px` }}
          onClick={() => hasChildren && toggleCollapse(node.id)}
        >
          {/* Expand/Collapse icon */}
          <div className="w-4 h-4 flex items-center justify-center">
            {hasChildren ? (
              collapsed ? (
                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              )
            ) : (
              <span className="w-2 h-2 rounded-full bg-muted-foreground/30" />
            )}
          </div>

          {/* Icon */}
          {icons[node.type]}

          {/* Name */}
          <span className="flex-1 text-sm font-medium text-foreground truncate">
            {node.name}
          </span>

          {/* Status Badge */}
          <Badge variant={statusInfo.variant} className="text-xs shrink-0">
            {statusInfo.label}
          </Badge>

          {/* Action buttons */}
          {node.type === 'goal' && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/coordination/goals/${node.id}/decompose`)
                }}
              >
                分解
              </Button>
            </div>
          )}
          {node.type === 'project' && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/coordination/projects/${node.id}`)
                }}
              >
                查看
              </Button>
            </div>
          )}
          {node.type === 'task' && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={(e) => {
                  e.stopPropagation()
                  navigate(`/coordination/tasks/${node.id}`)
                }}
              >
                查看
              </Button>
            </div>
          )}
        </div>

        {/* Children */}
        {hasChildren && !collapsed && filteredChildren?.map(child => renderNode(child, depth + 1))}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载目标分解树...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-4" />
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={fetchData}>重试</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link to={`/coordination/goals/${goalId}`}>
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-500" />
              {goal?.title || '目标分解'}
            </h1>
            {goal?.description && (
              <p className="text-sm text-muted-foreground mt-1">{goal.description}</p>
            )}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder="搜索..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span>{projects.length} 个项目</span>
        <span>·</span>
        <span>{tasks.length} 个任务</span>
        {searchQuery && (
          <>
            <span>·</span>
            <span>搜索结果: {filteredTree.reduce((acc, n) => acc + 1 + (n.children?.length || 0), 0)} 项</span>
          </>
        )}
      </div>

      {/* Tree */}
      <Card>
        <CardContent className="p-0">
          {filteredTree.length === 0 ? (
            <div className="text-center py-12">
              <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
              <p className="text-muted-foreground">
                {searchQuery ? '没有找到匹配的结果' : '暂无分解数据'}
              </p>
            </div>
          ) : (
            <div className="py-2">
              {filteredTree.map(node => renderNode(node))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
