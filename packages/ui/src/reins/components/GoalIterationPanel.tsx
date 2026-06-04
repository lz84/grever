/**
 * 迭代面板组件
 * 显示迭代状态、模式切换、启动/暂停/收敛控制
 * 调用 goalsApi.getIterationStatus / setMode / startIteration / pauseIteration / convergeIteration
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { Play, Pause, Zap, CheckCircle, Loader2, TrendingUp, Hash, Clock } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card, CardContent } from '@/shared/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { goalsApi } from '@/shared/utils/api'

// ── 状态映射 ──────────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  idle: { label: '未启动', color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200' },
  running: { label: '运行中', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  paused: { label: '已暂停', color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  converged: { label: '已收敛', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
  stopped: { label: '已停止', color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200' },
  executing: { label: '执行中', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] || STATUS_MAP.stopped
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────

interface GoalIterationPanelProps {
  goalId: string
  mode?: string
  onStatusChange?: () => void
}

export default function GoalIterationPanel({ goalId, mode, onStatusChange }: GoalIterationPanelProps) {
  const [iterStatus, setIterStatus] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await goalsApi.getIterationStatus(goalId)
      setIterStatus(data)
    } catch {
      // 静默处理，接口可能未实现
    }
  }, [goalId])

  useEffect(() => { fetchStatus() }, [goalId])

  async function handleAction(action: string) {
    setActionLoading(action)
    try {
      switch (action) {
        case 'start':
          await goalsApi.startIteration(goalId)
          toast.success('迭代已启动')
          break
        case 'pause':
          await goalsApi.pauseIteration(goalId)
          toast.success('迭代已暂停')
          break
        case 'converge':
          await goalsApi.convergeIteration(goalId)
          toast.success('已触发收敛')
          break
        case 'resume':
          await goalsApi.startIteration(goalId)
          toast.success('迭代已恢复')
          break
      }
      onStatusChange?.()
      fetchStatus()
    } catch (e: any) {
      toast.error(`${action} 失败：${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleSetMode(newMode: string) {
    try {
      await goalsApi.setMode(goalId, newMode)
      toast.success(`已切换为${modeLabel(newMode)}`)
      onStatusChange?.()
      fetchStatus()
    } catch (e: any) {
      toast.error('切换模式失败: ' + (e.message || '未知错误'))
    }
  }

  function modeLabel(m: string): string {
    return m === 'exploration' ? '探索模式' : m === 'optimization' ? '迭代模式' : '常规模式'
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
  if (!iterStatus) {
    return (
      <Card className="border-dashed border-blue-200 bg-blue-50/50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-blue-500" />
                迭代控制
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {mode ? `当前: ${modeLabel(mode)}` : '启动迭代自动生成方案并对比'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* 模式切换 */}
              <Select onValueChange={handleSetMode} defaultValue={mode || 'normal'}>
                <SelectTrigger className="w-[120px] h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">常规模式</SelectItem>
                  <SelectItem value="exploration">探索模式</SelectItem>
                  <SelectItem value="optimization">迭代模式</SelectItem>
                </SelectContent>
              </Select>
              <Button size="sm" onClick={() => handleAction('start')}>
                <Play className="w-3.5 h-3.5 mr-1" /> 启动迭代
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const runStatus = iterStatus?.run_status || iterStatus?.status || 'idle'
  const currentRound = iterStatus?.current_round ?? iterStatus?.round ?? 0
  const latestScore = iterStatus?.latest_score
  const totalSolutions = iterStatus?.total_solutions ?? 0

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardContent className="p-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-500" />
              <span className="font-semibold text-sm">迭代控制</span>
            </div>

            {/* 模式切换 */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">模式:</span>
              <Select onValueChange={handleSetMode} defaultValue={mode || 'normal'}>
                <SelectTrigger className="w-[110px] h-7 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">常规</SelectItem>
                  <SelectItem value="exploration">探索</SelectItem>
                  <SelectItem value="optimization">迭代</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Hash className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm">轮次: <strong>{currentRound}</strong></span>
            </div>

            <StatusBadge status={runStatus} />

            {latestScore != null && (
              <div className="flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5 text-green-600" />
                <span className="text-sm">评分: <strong>{typeof latestScore === 'number' ? latestScore.toFixed(2) : latestScore}</strong></span>
              </div>
            )}

            <div className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">方案: {totalSolutions}</span>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-1.5">
            {runStatus === 'idle' || runStatus === 'stopped' ? (
              <Button size="sm" onClick={() => handleAction('start')} disabled={actionLoading !== null}>
                <Play className="w-3.5 h-3.5 mr-1" /> 启动
              </Button>
            ) : (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleAction('next')}
                  disabled={actionLoading !== null || runStatus === 'converged'}
                >
                  下一轮
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleAction(runStatus === 'paused' ? 'resume' : 'pause')}
                  disabled={actionLoading !== null}
                >
                  {actionLoading === 'pause' || actionLoading === 'resume' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : runStatus === 'paused' ? (
                    <Play className="w-3.5 h-3.5 text-green-600" />
                  ) : (
                    <Pause className="w-3.5 h-3.5 text-amber-600" />
                  )}
                  <span className="ml-1">{runStatus === 'paused' ? '继续' : '暂停'}</span>
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  className="bg-blue-600 hover:bg-blue-700"
                  onClick={() => handleAction('converge')}
                  disabled={actionLoading !== null || runStatus === 'converged'}
                >
                  {actionLoading === 'converge' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle className="w-3.5 h-3.5" />
                  )}
                  <span className="ml-1">收敛</span>
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
