import { useState, useEffect } from 'react'
import { TRACES, DASHBOARD, HUMAN_REVIEW } from '../../shared/api/paths'
import { Link, useNavigate } from 'react-router-dom'
import { goalsApi, projectsApi, tasksApi, agentsApi, disputesApi } from '../../shared/utils/api'
import { scenariosApi } from '../../shared/utils/scenariosApi'
import { getTaskStatusText, getTaskStatusBadgeClass } from '../../shared/utils/statusMap'
import type { Goal, Project, Task, Agent } from '../../shared/utils/api'
import {
  Target, FolderKanban, ListTodo, Bot, AlertTriangle,
  RefreshCw, AlertCircle, Loader2, PlayCircle, Zap, FileText, Clock
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'

const GOAL_STATUS_LABELS: Record<string, string> = {
  active: '进行中', in_progress: '进行中',
  completed: '已完成', done: '已完成',
  planned: '已计划', draft: '草稿',
  failed: '失败', cancelled: '已取消',
}

const GOAL_STATUS_VARIANTS: Record<string, string> = {
  active: 'info',
  in_progress: 'info',
  completed: 'success',
  done: 'success',
  planned: 'secondary',
  draft: 'secondary',
}

function isToday(d: string | null | undefined): boolean {
  if (!d) return false
  const date = new Date(d)
  const now = new Date()
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()
}

function mapAgentStatus(status: string): 'online' | 'busy' | 'offline' {
  if (status === 'idle' || status === 'online') return 'online'
  if (status === 'busy' || status === 'working') return 'busy'
  return 'offline'
}

function mapAgentStatusText(status: string): string {
  const mapped = mapAgentStatus(status)
  if (mapped === 'online') return '在线'
  if (mapped === 'busy') return '繁忙'
  return '离线'
}

function getAgentStatusVariant(status: string): string {
  const mapped = mapAgentStatus(status)
  if (mapped === 'online') return 'success'
  if (mapped === 'busy') return 'warning'
  return 'secondary'
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
  return `${diffDays} 天前`
}

function formatDuration(ms: number | null): string {
  if (!ms) return '—'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`
  }
  if (minutes > 0) {
    return `${minutes}分钟`
  }
  return `${totalSeconds}秒`
}

function StatCard({ title, value, subtitle, icon: Icon, colorClass, onClick, alertText }: {
  title: string
  value: string | number
  subtitle: string
  icon: React.ElementType
  colorClass: string
  onClick?: () => void
  alertText?: string
}) {
  return (
    <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={onClick}>
      <CardContent className="p-5">
        <div className="flex justify-between items-start mb-2">
          <span className="text-slate-500 text-sm font-medium">{title}</span>
          <div className={`w-8 h-8 ${colorClass} rounded-sm flex items-center justify-center`}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
        <div className="flex items-baseline">
          <span className="text-4xl font-bold">{value}</span>
          <span className="text-sm text-slate-500 ml-2">{subtitle}</span>
        </div>
        {alertText && (
          <p className="text-xs text-blue-600 mt-1">{alertText}</p>
        )}
      </CardContent>
    </Card>
  )
}

function ListPanel({ title, icon: Icon, children, emptyText, emptyIcon: EmptyIcon }: {
  title: string
  icon: React.ElementType
  children: React.ReactNode
  emptyText: string
  emptyIcon: React.ElementType
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Icon className="w-4 h-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {children}
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [goals, setGoals] = useState<Goal[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [disputes, setDisputes] = useState<any[]>([])
  const [workflows, setWorkflows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [stats, setStats] = useState({
    activeTasks: 0,
    completedToday: 0,
    onlineAgents: 0,
    totalScenarios: 0,
    reviewNeeded: 0,
  })

  const [humanReviewStats, setHumanReviewStats] = useState({
    disputed_count: 0,
    waiting_human_count: 0,
    pending_count: 0,
    total: 0,
  })

  const [apiFailures, setApiFailures] = useState({
    goals: false,
    projects: false,
    tasks: false,
    agents: false,
    disputes: false,
    workflows: false,
    human_review: false,
  })

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      
      const [goalsData, projectsData, tasksData, agentsData, disputesData, workflowsData, statsData, humanReviewData, scenariosData] = await Promise.allSettled([
        goalsApi.list(),
        projectsApi.list(),
        tasksApi.list(),
        agentsApi.list(),
        disputesApi.list(),
        fetch(TRACES.LIST + '?limit=5').then(res => res.json()).then(d => Array.isArray(d) ? d : []).catch(() => []),
        fetch(DASHBOARD.STATS).then(res => res.json()).catch(() => null),
        fetch(HUMAN_REVIEW.GET_STATS).then(res => res.json()).catch(() => null),
        scenariosApi.list().catch(() => ({ items: [], total: 0 })),
      ])

      if (goalsData.status === 'fulfilled') {
        setGoals(goalsData.value)
        setApiFailures(prev => ({ ...prev, goals: false }))
      } else {
        setApiFailures(prev => ({ ...prev, goals: true }))
        setGoals([])
      }

      if (projectsData.status === 'fulfilled') {
        setProjects(projectsData.value)
        setApiFailures(prev => ({ ...prev, projects: false }))
      } else {
        setApiFailures(prev => ({ ...prev, projects: true }))
        setProjects([])
      }

      if (tasksData.status === 'fulfilled') {
        setTasks(tasksData.value)
        setApiFailures(prev => ({ ...prev, tasks: false }))
      } else {
        setApiFailures(prev => ({ ...prev, tasks: true }))
        setTasks([])
      }

      if (agentsData.status === 'fulfilled') {
        setAgents(agentsData.value)
        setApiFailures(prev => ({ ...prev, agents: false }))
      } else {
        setApiFailures(prev => ({ ...prev, agents: true }))
        setAgents([])
      }

      if (disputesData.status === 'fulfilled') {
        setDisputes(disputesData.value)
        setApiFailures(prev => ({ ...prev, disputes: false }))
      } else {
        setApiFailures(prev => ({ ...prev, disputes: true }))
        setDisputes([])
      }

      if (workflowsData.status === 'fulfilled') {
        setWorkflows(workflowsData.value)
        setApiFailures(prev => ({ ...prev, workflows: false }))
      } else {
        setApiFailures(prev => ({ ...prev, workflows: true }))
        setWorkflows([])
      }

      const agentsList = agentsData.status === 'fulfilled' ? agentsData.value : []
      const tasksList = tasksData.status === 'fulfilled' ? tasksData.value : []
      const completedTodayCount = tasksList.filter((t: any) => (t.status === 'completed' || t.status === 'done') && isToday(t.completed_at)).length
      const onlineCount = agentsList.filter((a: any) => {
        const s = (a.status || '').toLowerCase()
        return s === 'online' || s === 'idle' || s === 'busy' || s === 'working'
      }).length
      const activeCount = tasksList.filter((t: any) => t.status === 'in_progress' || t.status === 'active').length
      const scenariosTotal = scenariosData.status === 'fulfilled' ? (scenariosData.value.total || 0) : 0
      setStats({
        activeTasks: activeCount,
        completedToday: completedTodayCount,
        onlineAgents: onlineCount,
        totalScenarios: scenariosTotal,
        reviewNeeded: tasksList.filter((t: any) => t.status === 'review_needed').length,
      })

      if (humanReviewData.status === 'fulfilled' && humanReviewData.value) {
        setHumanReviewStats({
          disputed_count: humanReviewData.value.disputed_count || 0,
          waiting_human_count: humanReviewData.value.waiting_human_count || 0,
          pending_count: humanReviewData.value.pending_count || 0,
          total: humanReviewData.value.total || 0,
        })
        setApiFailures(prev => ({ ...prev, human_review: false }))
      } else {
        setApiFailures(prev => ({ ...prev, human_review: true }))
      }

      const allFailed = Object.values({ 
        goals: goalsData.status === 'rejected',
        projects: projectsData.status === 'rejected',
        tasks: tasksData.status === 'rejected',
        agents: agentsData.status === 'rejected',
        disputes: disputesData.status === 'rejected',
        workflows: workflowsData.status === 'rejected',
      }).every(failed => failed)

      if (allFailed) {
        setError('无法加载工作台数据')
      }
    } catch (e: any) {
      setError(e.message || '加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  async function fetchDataSilent() {
    try {
      const [goalsData, tasksData, agentsData, workflowsData, humanReviewData, scenariosData] = await Promise.allSettled([
        goalsApi.list(),
        tasksApi.list(),
        agentsApi.list(),
        fetch(TRACES.LIST + '?limit=5').then(res => res.json()).then(d => Array.isArray(d) ? d : []).catch(() => []),
        fetch(HUMAN_REVIEW.GET_STATS).then(res => res.json()).catch(() => null),
        scenariosApi.list().catch(() => ({ items: [], total: 0 })),
      ])

      if (goalsData.status === 'fulfilled') setGoals(goalsData.value)
      if (tasksData.status === 'fulfilled') setTasks(tasksData.value)
      if (agentsData.status === 'fulfilled') setAgents(agentsData.value)
      if (workflowsData.status === 'fulfilled') setWorkflows(workflowsData.value)

      const agentsList = agentsData.status === 'fulfilled' ? agentsData.value : []
      const tasksList = tasksData.status === 'fulfilled' ? tasksData.value : []
      const completedTodayCount = tasksList.filter((t: any) => (t.status === 'completed' || t.status === 'done') && isToday(t.completed_at)).length
      const onlineCount = agentsList.filter((a: any) => {
        const s = (a.status || '').toLowerCase()
        return s === 'online' || s === 'idle' || s === 'busy' || s === 'working'
      }).length
      const activeCount = tasksList.filter((t: any) => t.status === 'in_progress' || t.status === 'active').length
      const scenariosTotal = scenariosData.status === 'fulfilled' ? (scenariosData.value.total || 0) : 0
      setStats(prev => ({
        ...prev,
        activeTasks: activeCount,
        completedToday: completedTodayCount,
        onlineAgents: onlineCount,
        totalScenarios: scenariosTotal,
      }))

      if (humanReviewData.status === 'fulfilled' && humanReviewData.value) {
        setHumanReviewStats({
          disputed_count: humanReviewData.value.disputed_count || 0,
          waiting_human_count: humanReviewData.value.waiting_human_count || 0,
          pending_count: humanReviewData.value.pending_count || 0,
          total: humanReviewData.value.total || 0,
        })
      }
    } catch (e) {
      // Silent refresh - ignore errors
    }
  }

  useEffect(() => {
    fetchData()
    const intervalId = setInterval(fetchDataSilent, 30000)
    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [])

  const todaysTasks = tasks
    .filter(task => {
      if (!task.updated_at) return false
      const taskDate = new Date(task.updated_at)
      const today = new Date()
      return taskDate.getDate() === today.getDate() &&
             taskDate.getMonth() === today.getMonth() &&
             taskDate.getFullYear() === today.getFullYear()
    })
    .sort((a, b) => {
      const aTime = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const bTime = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return bTime - aTime
    })
    .slice(0, 5)

  const recentGoals = [...goals]
    .filter(g => g.status !== 'completed' && g.status !== 'done')
    .sort((a, b) => {
      const aTime = a.updated_at ? new Date(a.updated_at).getTime() : 0
      const bTime = b.updated_at ? new Date(b.updated_at).getTime() : 0
      return bTime - aTime
    })
    .slice(0, 5)

  const recentWorkflows = (() => {
    const wfs = [...workflows]
      .sort((a, b) => {
        const aTime = a.updated_at ? new Date(a.updated_at).getTime() : 0
        const bTime = b.updated_at ? new Date(b.updated_at).getTime() : 0
        return bTime - aTime
      })
      .slice(0, 5)

    const mappedWfs = wfs.map(w => ({
      id: w.task_id || w.id,
      name: w.task_title || w.title || '未命名任务',
      status: w.status === 'done' || w.status === 'completed' || w.status === 'blocked' ? 'completed' : (w.status === 'in_progress' ? 'in_progress' : 'pending'),
      created_at: w.completed_at || w.started_at || w.updated_at,
      duration: w.duration_ms || w.execution_duration_ms || null,
      workflow_id: w.workflow_id || null,
      steps: w.steps || null,
      total_steps: w.total_steps || null,
      completed_steps: w.completed_steps || null,
    }))

    if (mappedWfs.length === 0) {
      return todaysTasks.map(t => ({
        id: t.id,
        name: t.title || '未命名任务',
        status: t.status === 'done' || t.status === 'completed' || t.status === 'blocked' ? 'completed' : 'in_progress',
        created_at: t.updated_at,
        duration: null,
        workflow_id: null,
        steps: null,
        total_steps: null,
        completed_steps: null,
      }))
    }
    return mappedWfs
  })()

  const taskProgressByGoal: Record<string, { completed: number; total: number }> = {}
  tasks.forEach(t => {
    if (t.goal_id) {
      if (!taskProgressByGoal[t.goal_id]) taskProgressByGoal[t.goal_id] = { completed: 0, total: 0 }
      taskProgressByGoal[t.goal_id].total++
      if (t.status === 'done' || t.status === 'completed') taskProgressByGoal[t.goal_id].completed++
    }
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
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

  const formatTime = (dateStr: string | null): string => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const WORKFLOW_STATUS_LABELS: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    pending: '等待中',
    in_progress: '进行中',
  };

  const WORKFLOW_STATUS_VARIANTS: Record<string, string> = {
    running: 'info',
    completed: 'success',
    failed: 'destructive',
    pending: 'warning',
    in_progress: 'info',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">🏠 工作台</h1>
        <p className="text-sm text-slate-500 mt-1">系统入口，全局概览，快速了解系统运行状态</p>
      </div>

      {/* Stats Cards - First Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="活跃任务"
          value={stats.activeTasks}
          subtitle="进行中"
          icon={ListTodo}
          colorClass="bg-blue-50 text-blue-500"
          onClick={() => navigate('/coordination/tasks')}
        />
        <StatCard
          title="今日完成"
          value={stats.completedToday}
          subtitle="已完成"
          icon={Target}
          colorClass="bg-green-50 text-green-500"
          onClick={() => navigate('/coordination/tasks')}
        />
        <StatCard
          title="在线智能体"
          value={stats.onlineAgents}
          subtitle="在线"
          icon={Bot}
          colorClass="bg-purple-50 text-purple-500"
          onClick={() => navigate('/system/agents')}
        />
        <StatCard
          title="待审核任务"
          value={stats.reviewNeeded}
          subtitle="项待审核"
          icon={AlertCircle}
          colorClass={stats.reviewNeeded > 0 ? "bg-orange-100 text-orange-500" : "bg-orange-50 text-orange-500"}
          onClick={() => navigate('/coordination/tasks?status=review_needed')}
          alertText={stats.reviewNeeded > 0 ? "点击立即审核 →" : undefined}
        />
      </div>

      {/* Stats Cards - Second Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="待裁决"
          value={humanReviewStats.disputed_count}
          subtitle="项争议"
          icon={AlertTriangle}
          colorClass={humanReviewStats.disputed_count > 0 ? "bg-red-100 text-red-500" : "bg-red-50 text-red-500"}
          onClick={() => navigate('/rulings?tab=disputed')}
          alertText={humanReviewStats.disputed_count > 0 ? "点击立即裁决 →" : undefined}
        />
        <StatCard
          title="待审批"
          value={humanReviewStats.waiting_human_count}
          subtitle="项待审批"
          icon={Clock}
          colorClass={humanReviewStats.waiting_human_count > 0 ? "bg-purple-100 text-purple-500" : "bg-purple-50 text-purple-500"}
          onClick={() => navigate('/rulings?tab=approval')}
          alertText={humanReviewStats.waiting_human_count > 0 ? "点击立即审批 →" : undefined}
        />
        <StatCard
          title="待协助"
          value={humanReviewStats.pending_count}
          subtitle="项待协助"
          icon={ListTodo}
          colorClass={humanReviewStats.pending_count > 0 ? "bg-blue-100 text-blue-500" : "bg-blue-50 text-blue-500"}
          onClick={() => navigate('/rulings?tab=assist')}
          alertText={humanReviewStats.pending_count > 0 ? "点击立即协助 →" : undefined}
        />
        <StatCard
          title="场景库"
          value={stats.totalScenarios}
          subtitle="个场景"
          icon={FolderKanban}
          colorClass="bg-amber-50 text-amber-500"
          onClick={() => navigate('/scenarios')}
        />
      </div>

      {/* 2x2 Grid: Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 今日待办 */}
        <ListPanel title="今日待办" icon={ListTodo} emptyText="今日暂无待办任务" emptyIcon={ListTodo}>
          {todaysTasks.length === 0 ? (
            <div className="p-6 text-center text-slate-400">
              <ListTodo className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">今日暂无待办任务</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {todaysTasks.slice(0, 5).map(task => {
                const status = getTaskStatusText(task.status)
                const statusClass = getTaskStatusBadgeClass(task.status)
                return (
                  <div
                    key={task.id}
                    className="py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/coordination/tasks/${task.id}`)}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-slate-800 text-sm truncate">{task.title || '未命名任务'}</span>
                      <Badge className={statusClass}>{status}</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">{task.assigned_agent || '未分配'}</span>
                      <span className="text-xs text-slate-400">{formatTime(task.created_at)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </ListPanel>

        {/* 最近目标 */}
        <ListPanel title="最近目标" icon={Target} emptyText="暂无目标" emptyIcon={Target}>
          {recentGoals.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无目标，点击「新建目标」开始</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {recentGoals.map(goal => {
                const progress = taskProgressByGoal[goal.id]
                const statusLabel = GOAL_STATUS_LABELS[goal.status || ''] || goal.status || '未知'
                const statusVariant = GOAL_STATUS_VARIANTS[goal.status || ''] || 'secondary'
                return (
                  <div
                    key={goal.id}
                    className="py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/coordination/goals/${goal.id}`)}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-slate-800 text-sm">{goal.title || '未命名目标'}</span>
                      <Badge variant={statusVariant as any}>{statusLabel}</Badge>
                    </div>
                    <div className="flex items-center gap-3">
                      {progress && progress.total > 0 ? (
                        <div className="flex items-center gap-2 flex-1">
                          <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{ width: `${(progress.completed / progress.total) * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400">{Math.round((progress.completed / progress.total) * 100)}%</span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">暂无任务</span>
                      )}
                      <span className="text-xs text-slate-400">{formatRelativeTime(goal.updated_at)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </ListPanel>

        {/* 最近执行 */}
        <ListPanel title="最近执行" icon={PlayCircle} emptyText="暂无执行记录" emptyIcon={PlayCircle}>
          {recentWorkflows.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <PlayCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无执行记录，点击「查看执行」开始</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {recentWorkflows.map(workflow => {
                const statusLabel = WORKFLOW_STATUS_LABELS[workflow.status || ''] || workflow.status || '未知'
                const statusVariant = WORKFLOW_STATUS_VARIANTS[workflow.status || ''] || 'secondary'
                let stepProgress = null;
                if (workflow.steps && Array.isArray(workflow.steps)) {
                  const completedSteps = workflow.steps.filter((step: any) => step.status === 'completed').length;
                  stepProgress = `${completedSteps}/${workflow.steps.length}`;
                } else if (workflow.total_steps && workflow.completed_steps) {
                  stepProgress = `${workflow.completed_steps}/${workflow.total_steps}`;
                }
                return (
                  <div
                    key={workflow.id}
                    className="py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => {
                      if (!workflow.workflow_id && workflow.id.startsWith('task-')) {
                        navigate(`/coordination/tasks/${workflow.id}`)
                      } else {
                        navigate(`/coordination/executions/${workflow.id}`)
                      }
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-slate-800 text-sm">{workflow.name || '未命名执行'}</span>
                      <Badge variant={statusVariant as any}>{statusLabel}</Badge>
                    </div>
                    <div className="flex items-center gap-3">
                      {stepProgress ? (
                        <span className="text-xs text-slate-500">步骤: {stepProgress}</span>
                      ) : (
                        <span className="text-xs text-slate-400">暂无步骤信息</span>
                      )}
                      <span className="text-xs text-slate-400">{formatDuration(workflow.duration)}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </ListPanel>

        {/* 智能体状态 */}
        <ListPanel title="智能体状态" icon={Bot} emptyText="暂无注册智能体" emptyIcon={Bot}>
          {agents.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无注册智能体</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {agents.map(agent => {
                const statusLabel = mapAgentStatusText(agent.status)
                const statusVariant = getAgentStatusVariant(agent.status)
                const mapped = mapAgentStatus(agent.status)
                return (
                  <div
                    key={agent.id}
                    className="py-3 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => navigate('/system/agents')}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-slate-800 text-sm">{agent.name}</span>
                      <Badge variant={statusVariant as any}>{statusLabel}</Badge>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${agent.load >= 90 ? 'bg-red-500' : agent.load >= 70 ? 'bg-amber-500' : 'bg-green-500'} rounded-full`}
                          style={{ width: `${Math.min(agent.load, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500">{agent.load}%</span>
                      <span className="text-xs text-slate-400">{agent.current_tasks} 任务</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </ListPanel>
      </div>
    </div>
  )
}
