import { useState, useEffect } from 'react'
import { BarChart3, RefreshCw, AlertCircle, Loader2 } from 'lucide-react'
import { goalsApi, tasksApi, agentsApi } from '../../shared/utils/api'
import { securityApi, type ExecutionTrendItem } from '../../shared/utils/securityApi'
import type { Goal, Task, Agent } from '../../shared/utils/api'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'

function getLoadColor(load: number): string {
  if (load >= 90) return 'bg-red-500'
  if (load >= 70) return 'bg-orange-500'
  return 'bg-green-500'
}

export default function VisualBoard() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [trendData, setTrendData] = useState<ExecutionTrendItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const [goalsData, tasksData, agentsData, trend] = await Promise.all([
        goalsApi.list(),
        tasksApi.list(),
        agentsApi.list(),
        securityApi.getExecutionTrend(7),
      ])
      setGoals(goalsData)
      setTasks(tasksData)
      setAgents(agentsData)
      setTrendData(trend)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const completedGoals = goals.filter(g => g.status === 'completed' || g.status === 'done').length
  const totalGoals = goals.length
  const goalCompletionRate = totalGoals > 0 ? Math.round((completedGoals / totalGoals) * 100) : 0

  const taskStatusCounts = {
    todo: tasks.filter(t => t.status === 'todo' || t.status === 'pending').length,
    in_progress: tasks.filter(t => t.status === 'in_progress' || t.status === 'active').length,
    completed: tasks.filter(t => t.status === 'completed' || t.status === 'done').length,
    blocked: tasks.filter(t => t.status === 'blocked').length,
  }
  const totalTasks = tasks.length
  const maxTrendCount = trendData.length > 0 ? Math.max(...trendData.map(d => d.count), 1) : 1

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-slate-500" />
            数据看板
          </h1>
          <p className="text-sm text-slate-500 mt-1">系统运行数据一览</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="w-4 h-4" />
          刷新
        </Button>
      </div>

      {/* Goal Completion Rate */}
      <Card>
        <CardHeader>
          <CardTitle>目标完成率</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex-1 h-3 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${goalCompletionRate}%` }}
                  />
                </div>
                <span className="text-lg font-bold text-slate-800">{goalCompletionRate}%</span>
              </div>
              <p className="text-sm text-slate-500">
                已完成 {completedGoals} / 总计 {totalGoals}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Task Status Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>任务状态分布</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { key: 'todo', label: '待办', count: taskStatusCounts.todo, color: 'bg-slate-400' },
              { key: 'in_progress', label: '进行中', count: taskStatusCounts.in_progress, color: 'bg-blue-500' },
              { key: 'completed', label: '已完成', count: taskStatusCounts.completed, color: 'bg-green-500' },
              { key: 'blocked', label: '阻塞', count: taskStatusCounts.blocked, color: 'bg-red-500' },
            ].map(item => {
              const pct = totalTasks > 0 ? Math.round((item.count / totalTasks) * 100) : 0
              return (
                <div key={item.key} className="flex items-center gap-4">
                  <span className="w-16 text-sm text-slate-600">{item.label}</span>
                  <div className="flex-1 h-3 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item.color} rounded-full transition-all duration-500`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-sm text-slate-500 w-12 text-right">{pct}%</span>
                  <span className="text-sm text-slate-400 w-8 text-right">({item.count})</span>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Agent Load Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>智能体负载分布</CardTitle>
        </CardHeader>
        <CardContent>
          {agents.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">暂无智能体数据</p>
          ) : (
            <div className="space-y-4">
              {agents.map(agent => (
                <div key={agent.id} className="flex items-center gap-4">
                  <span className="w-16 text-sm font-medium text-slate-700">{agent.name}</span>
                  <div className="flex-1 h-3 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${getLoadColor(agent.load)} rounded-full transition-all duration-500`}
                      style={{ width: `${Math.min(agent.load, 100)}%` }}
                    />
                  </div>
                  <span className="text-sm text-slate-500 w-12 text-right">{agent.load}%</span>
                  <span className="text-xs text-slate-400 w-16">({agent.current_tasks} 任务)</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Execution Trend */}
      <Card>
        <CardHeader>
          <CardTitle>最近 7 天执行趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative h-48 flex items-end gap-2">
            {trendData.map((d) => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-2">
                <span className="text-xs text-slate-500">{d.count}</span>
                <div
                  className="w-full bg-blue-500 rounded-t transition-all duration-300"
                  style={{ height: `${(d.count / maxTrendCount) * 160}px` }}
                />
                <span className="text-xs text-slate-500">{d.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
