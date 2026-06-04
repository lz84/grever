/**
 * Sprint 68-73: 迭代控制面板
 * 用于 GoalDetail 页面顶部展示迭代状态和控制
 */

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Play, Pause, Zap, CheckCircle, RotateCcw, Loader2,
  ChevronDown, ChevronRight, TrendingUp, Hash, Clock, Target, Star,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card, CardContent } from '@/shared/components/ui/card'
import { solutionsApi, type IterationStatus, type ConstraintHistory, type Solution, type SolutionListResponse } from '@/evo/services/solutions'

// ── 状态映射 ──────────────────────────────────────────────────────────────

const ITERATION_STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  idle: { label: '未启动', color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200' },
  running: { label: '运行中', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  paused: { label: '已暂停', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  converged: { label: '已收敛', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  stopped: { label: '已停止', color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200' },
}

function IterationStatusBadge({ status }: { status: string }) {
  const cfg = ITERATION_STATUS_MAP[status] || ITERATION_STATUS_MAP.stopped
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────

interface IterationControlPanelProps {
  goalId: string
  goalStatus?: string
  onSolutionUpdate?: () => void
}

export default function IterationControlPanel({ goalId, goalStatus, onSolutionUpdate }: IterationControlPanelProps) {
  const [status, setStatus] = useState<IterationStatus | null>(null)
  const [constraints, setConstraints] = useState<ConstraintHistory[]>([])
  const [solutions, setSolutions] = useState<Solution[]>([])
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [showConstraints, setShowConstraints] = useState(false)
  const [showSolutions, setShowSolutions] = useState(false)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [statusData, constraintsData, solutionsData] = await Promise.allSettled([
        solutionsApi.iterationStatus(goalId),
        solutionsApi.constraints(goalId),
        solutionsApi.list(goalId),
      ])
      if (statusData.status === 'fulfilled') setStatus(statusData.value)
      if (constraintsData.status === 'fulfilled') setConstraints(constraintsData.value || [])
      if (solutionsData.status === 'fulfilled') {
        const arr = Array.isArray(solutionsData.value) ? solutionsData.value : (solutionsData.value as SolutionListResponse)?.solutions || []
        setSolutions(arr)
      }
    } catch {
      // 迭代接口可能未实现，静默处理
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [goalId])

  async function handleAction(action: string) {
    setActionLoading(action)
    try {
      switch (action) {
        case 'start':
          await solutionsApi.startIteration(goalId)
          toast.success('迭代已启动')
          break
        case 'next':
          await solutionsApi.iterate(goalId)
          toast.success('已触发下一轮迭代')
          break
        case 'pause':
          await solutionsApi.pauseIteration(goalId)
          toast.success('迭代已暂停')
          break
        case 'converge':
          await solutionsApi.declareConverged(goalId)
          toast.success('已宣布收敛')
          break
      }
      onSolutionUpdate?.()
      fetchData()
    } catch (e: any) {
      toast.error(`${action} 失败：${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <Card className="border-dashed">
        <CardContent className="p-4 flex items-center justify-center">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground mr-2" />
          <span className="text-sm text-muted-foreground">加载迭代状态...</span>
        </CardContent>
      </Card>
    )
  }

  // 如果没有迭代数据，显示启动面板
  // 如果没有迭代数据，显示加载状态
  if (!status) {
    return (
      <Card className="border-dashed border-blue-200 bg-blue-50/50">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
            <span className="text-sm text-muted-foreground">正在加载迭代状态...</span>
          </div>
        </CardContent>
      </Card>
    );
  }


  return (
    <div className="space-y-3">
      {/* 状态条 */}
      <Card className="border-blue-200 bg-blue-50/30">
        <CardContent className="p-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-blue-500" />
                <span className="font-semibold text-sm">迭代控制</span>
              </div>
              <div className="flex items-center gap-2">
                <Hash className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-sm">当前轮次: <strong>{status.current_round}</strong></span>
              </div>
              <IterationStatusBadge status={status.run_status} />
              {status.latest_score != null && (
                <div className="flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-green-600" />
                  <span className="text-sm">最新评分: <strong>{status.latest_score.toFixed(2)}</strong></span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">方案数: {status.total_solutions}</span>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleAction('next')}
                disabled={actionLoading !== null || status.run_status === 'converged'}
              >
                {actionLoading === 'next' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                <span className="ml-1">下一轮</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleAction(status.run_status === 'paused' ? 'start' : 'pause')}
                disabled={actionLoading !== null}
              >
                {actionLoading === 'pause' || actionLoading === 'start' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : status.run_status === 'paused' ? (
                  <Play className="w-3.5 h-3.5 text-green-600" />
                ) : (
                  <Pause className="w-3.5 h-3.5 text-amber-600" />
                )}
                <span className="ml-1">{status.run_status === 'paused' ? '继续' : '暂停'}</span>
              </Button>
              <Button
                size="sm"
                variant="default"
                className="bg-blue-600 hover:bg-blue-700"
                onClick={() => handleAction('converge')}
                disabled={actionLoading !== null || status.run_status === 'converged'}
              >
                {actionLoading === 'converge' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <CheckCircle className="w-3.5 h-3.5" />
                )}
                <span className="ml-1">宣布收敛</span>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 约束历史折叠 */}
      {constraints.length > 0 && (
        <div>
          <Button variant="ghost" size="sm" className="flex items-center gap-1 text-xs text-muted-foreground" onClick={() => setShowConstraints(!showConstraints)}>
            {showConstraints ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            约束历史 ({constraints.length} 轮)
          </Button>
          {showConstraints && (
            <div className="ml-2 space-y-1 mt-1">
              {constraints.map(c => (
                <div key={c.round} className="flex items-start gap-2 text-xs">
                  <Badge variant={c.changed ? 'default' : 'secondary'} className="shrink-0">
                    R{c.round}
                  </Badge>
                  <div className="flex flex-wrap gap-1">
                    {c.constraints.slice(0, 3).map((constraint, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
                        {constraint}
                      </span>
                    ))}
                    {c.constraints.length > 3 && (
                      <span className="text-muted-foreground">+{c.constraints.length - 3}</span>
                    )}
                  </div>
                  <span className="text-muted-foreground ml-auto">
                    {c.timestamp ? new Date(c.timestamp).toLocaleDateString('zh-CN') : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {/* 方案列表折叠 */}
      {solutions.length > 0 && (
        <div>
          <Button variant="ghost" size="sm" className="flex items-center gap-1 text-xs text-muted-foreground" onClick={() => setShowSolutions(!showSolutions)}>
            {showSolutions ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            方案列表 ({solutions.length} 个)
          </Button>
          {showSolutions && (
            <div className="ml-2 space-y-1.5 mt-1">
              {solutions.map(sol => (
                <div key={sol.id} className="flex items-center gap-2 p-2 rounded bg-card border text-xs">
                  <Target className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium truncate">{sol.name}</span>
                      <Badge variant={sol.status === 'optimal' ? 'default' : sol.status === 'compliant' ? 'secondary' : 'destructive'} className="text-[10px] px-1 py-0 h-4">
                        {sol.status === 'optimal' ? '最优' : sol.status === 'compliant' ? '合规' : sol.status === 'non_compliant' ? '不合规' : sol.status}
                      </Badge>
                      <span className="text-muted-foreground">R{sol.round}</span>
                    </div>
                    {sol.score != null && (
                      <div className="flex items-center gap-1 mt-0.5 text-muted-foreground">
                        <Star className="w-3 h-3" />
                        <span>{sol.score.toFixed(2)}</span>
                        {sol.parameters && Object.keys(sol.parameters).length > 0 && (
                          <span className="ml-1">·</span>
                        )}
                        {sol.parameters && Object.entries(sol.parameters).slice(0, 3).map(([k, v]) => (
                          <span key={k} className="px-1 py-0 bg-muted/50 rounded">{k}: {typeof v === 'number' ? v : JSON.stringify(v)}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
