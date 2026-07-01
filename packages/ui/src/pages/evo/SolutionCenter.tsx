/**
 * Sprint 68-73: 方案对比中心
 * 路由：/solutions
 *
 * 功能：
 * - 目标筛选器（下拉选择）
 * - 多维度对比表格（最优值高亮，最优方案金色边框）
 * - 收敛趋势图（SVG 折线图，工期/成本/安全评分）
 */

import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  RefreshCw, AlertCircle, Loader2, BarChart3, TrendingUp,
  Target, Eye, ChevronDown, ChevronRight, ArrowUp, ArrowDown, Minus,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select'
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '@/shared/components/ui/card'
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/shared/components/ui/tabs'
import SolutionDetailModal from '@/evo/components/SolutionDetailModal'
import { solutionsApi, type Solution, type MultiCompareResult, type TrendData, type SolutionListResponse } from '@/evo/services/solutions'
import { goalsApi, type Goal } from '@/shared/utils/api'

// ── 状态标签 ──────────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, { label: string; emoji: string; variant: string }> = {
  compliant: { label: '达标', emoji: '✅', variant: 'default' },
  non_compliant: { label: '不达标', emoji: '❌', variant: 'destructive' },
  optimal: { label: '最优', emoji: '🏆', variant: 'default' },
  rejected: { label: '否决', emoji: '⛔', variant: 'secondary' },
  pending: { label: '待评估', emoji: '⏳', variant: 'outline' },
}

function StatusTag({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] || STATUS_MAP.pending
  return (
    <Badge variant={cfg.variant as any} className="flex items-center gap-1">
      {cfg.emoji} {cfg.label}
    </Badge>
  )
}

// ── SVG 趋势图 ────────────────────────────────────────────────────────────

interface TrendChartProps {
  data: TrendData
  width?: number
  height?: number
}

function TrendChart({ data, width = 600, height = 300 }: TrendChartProps) {
  const padding = { top: 30, right: 30, bottom: 40, left: 50 }
  const chartW = width - padding.left - padding.right
  const chartH = height - padding.top - padding.bottom

  const lines = [
    { key: 'duration' as const, label: '工期', color: '#3b82f6', dataKey: 'duration' },
    { key: 'cost' as const, label: '成本', color: '#f59e0b', dataKey: 'cost' },
    { key: 'safety' as const, label: '安全评分', color: '#10b981', dataKey: 'safety' },
  ]

  if (!data.points || data.points.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width, height }}>
        <p className="text-muted-foreground text-sm">暂无趋势数据</p>
      </div>
    )
  }

  const points = data.points

  // 计算所有数据的范围
  let allValues: number[] = []
  lines.forEach(line => {
    points.forEach(p => {
      const val = p[line.dataKey as keyof typeof p] as number
      if (val != null) allValues.push(val)
    })
  })
  if (allValues.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width, height }}>
        <p className="text-muted-foreground text-sm">暂无有效数据</p>
      </div>
    )
  }

  const minVal = Math.min(...allValues)
  const maxVal = Math.max(...allValues)
  const range = maxVal - minVal || 1

  const xScale = (round: number) => {
    const rounds = points.map(p => p.round)
    const minRound = Math.min(...rounds)
    const maxRound = Math.max(...rounds)
    const roundRange = maxRound - minRound || 1
    return padding.left + ((round - minRound) / roundRange) * chartW
  }

  const yScale = (val: number) => {
    return padding.top + chartH - ((val - minVal) / range) * chartH
  }

  // Y 轴刻度
  const yTicks = 5
  const yTickValues = Array.from({ length: yTicks + 1 }, (_, i) => minVal + (range * i) / yTicks)

  // X 轴标签
  const rounds = [...new Set(points.map(p => p.round))].sort((a, b) => a - b)

  return (
    <svg width={width} height={height} className="w-full" viewBox={`0 0 ${width} ${height}`}>
      {/* 网格线 */}
      {yTickValues.map((val, i) => (
        <g key={i}>
          <line
            x1={padding.left} y1={yScale(val)}
            x2={width - padding.right} y2={yScale(val)}
            stroke="#e2e8f0" strokeWidth={1} strokeDasharray="4,4"
          />
          <text
            x={padding.left - 8} y={yScale(val) + 4}
            textAnchor="end" fontSize={11} fill="#94a3b8"
          >
            {val.toFixed(1)}
          </text>
        </g>
      ))}

      {/* X 轴标签 */}
      {rounds.map((round, i) => (
        <text
          key={i}
          x={xScale(round)} y={height - padding.bottom + 20}
          textAnchor="middle" fontSize={11} fill="#94a3b8"
        >
          R{round}
        </text>
      ))}

      {/* 轴线 */}
      {lines.map(line => {
        const linePoints = points.map(p => ({
          x: xScale(p.round),
          y: yScale((p as any)[line.dataKey] ?? 0),
        }))

        if (linePoints.length < 2) return null

        const pathD = linePoints.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`).join(' ')

        return (
          <g key={line.key}>
            <path
              d={pathD}
              fill="none"
              stroke={line.color}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {linePoints.map((pt, i) => (
              <circle key={i} cx={pt.x} cy={pt.y} r={3.5} fill={line.color} stroke="white" strokeWidth={1.5} />
            ))}
          </g>
        )
      })}

      {/* 图例 */}
      {lines.map((line, i) => (
        <g key={line.key}>
          <line
            x1={padding.left + i * 100} y1={8}
            x2={padding.left + i * 100 + 20} y2={8}
            stroke={line.color} strokeWidth={2.5}
          />
          <text
            x={padding.left + i * 100 + 24} y={12}
            fontSize={12} fill="#475569"
          >
            {line.label}
          </text>
        </g>
      ))}
    </svg>
  )
}

// ── 主页面 ────────────────────────────────────────────────────────────────

export default function SolutionCenter() {
  const navigate = useNavigate()

  const [goals, setGoals] = useState<Goal[]>([])
  const [selectedGoalId, setSelectedGoalId] = useState<string>('')

  const [solutions, setSolutions] = useState<Solution[]>([])
  const [compareData, setCompareData] = useState<MultiCompareResult | null>(null)
  const [trendData, setTrendData] = useState<TrendData | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailSolution, setDetailSolution] = useState<Solution | null>(null)

  // 加载目标列表（只保留探索模式）
  useEffect(() => {
    goalsApi.list()
      .then(data => {
        const allGoals = Array.isArray(data) ? data : []
        const researchGoals = allGoals.filter(g => g.mode === 'research')
        setGoals(researchGoals)
        if (researchGoals.length > 0) setSelectedGoalId(researchGoals[0].id)
      })
      .catch(() => {})
  }, [])

  // 加载方案数据
  useEffect(() => {
    if (!selectedGoalId) return
    setLoading(true)
    setError(null)
    Promise.allSettled([
      solutionsApi.list(selectedGoalId),
      solutionsApi.multiCompare(selectedGoalId),
      solutionsApi.trend(selectedGoalId),
    ]).then(([sRes, cRes, tRes]) => {
      if (sRes.status === 'fulfilled') {
        const res = sRes.value as any
        const arr = Array.isArray(res) ? res : (res?.solutions || [])
        setSolutions(arr)
      }
      if (cRes.status === 'fulfilled') setCompareData(cRes.value)
      if (tRes.status === 'fulfilled') setTrendData(tRes.value)
      setLoading(false)
    }).catch(() => {
      setError('加载方案数据失败')
      setLoading(false)
    })
  }, [selectedGoalId])

  const handleViewDetail = (solution: Solution) => {
    setDetailSolution(solution)
    setDetailOpen(true)
  }

  // ── 对比表格 ──────────────────────────────────────────────────────────

  const renderCompareTable = useMemo(() => {
    const hasCompareData = compareData && Array.isArray(compareData.dimensions) && compareData.dimensions.length > 0 && compareData.values
    if (!hasCompareData) {
      // Fallback: 直接用 solutions 数据展示
      const safeFallback = Array.isArray(solutions) ? solutions : []
      if (safeFallback.length === 0) return null
      return renderFallbackTable(safeFallback)
    }

    const { dimensions, values, solutions: solList } = compareData
    if (!solList || solList.length === 0) return null

    // 找出每维度的最优方案
    const bestByDim: Record<string, string> = {}
    dimensions.forEach(dim => {
      let bestVal: number | null = null
      let bestSolId: string | null = null
      solList.forEach(sol => {
        const solValues = values?.[sol.id] || {}
        const val = solValues[dim.key]
        if (val == null) return
        const lowerIsBetter = dim.lower_is_better ?? false
        if (bestVal === null || (lowerIsBetter ? val < bestVal : val > bestVal)) {
          bestVal = val
          bestSolId = sol.id
        }
      })
      if (bestSolId) bestByDim[dim.key] = bestSolId
    })

    // 找出整体最优方案（拥有最多最优维度）
    const dimCount: Record<string, number> = {}
    Object.values(bestByDim).forEach(solId => {
      dimCount[solId] = (dimCount[solId] || 0) + 1
    })
    const bestOverallId = Object.entries(dimCount).sort((a, b) => b[1] - a[1])[0]?.[0]

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-3 px-4 font-semibold text-muted-foreground w-32">维度</th>
              {solList.map(sol => {
                const isBest = sol.id === bestOverallId
                return (
                  <th
                    key={sol.id}
                    className={`py-3 px-4 text-center font-semibold ${
                      isBest ? 'text-yellow-700' : 'text-foreground'
                    }`}
                  >
                    <div className="flex flex-col items-center gap-1">
                      {isBest && <span className="text-lg">🏆</span>}
                      <span>{sol.name}</span>
                      {solList.length <= 4 && (
                        <Button variant="ghost" size="sm" className="h-5 px-1 text-xs" onClick={() => handleViewDetail(sol as any)}>
                          <Eye className="w-3 h-3" />
                        </Button>
                      )}
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {dimensions.map(dim => (
              <tr key={dim.key} className="border-b hover:bg-muted/30">
                <td className="py-2.5 px-4 font-medium text-foreground">
                  {dim.label}
                  {dim.unit && <span className="text-muted-foreground text-xs ml-1">({dim.unit})</span>}
                </td>
                {solList.map(sol => {
                  const solValues = values[sol.id] || {}
                  const val = solValues[dim.key]
                  const isBest = bestByDim[dim.key] === sol.id
                  const isOverallBest = sol.id === bestOverallId
                  return (
                    <td
                      key={sol.id}
                      className={`py-2.5 px-4 text-center font-mono ${
                        isBest
                          ? 'bg-green-50 text-green-700 font-bold rounded'
                          : 'text-foreground'
                      }`}
                      style={isOverallBest ? { borderLeft: '3px solid #eab308', borderRight: '3px solid #eab308' } : {}}
                    >
                      {val != null ? val.toFixed(2) : '—'}
                      {isBest && <span className="ml-1 text-green-600">✓</span>}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }, [compareData, solutions])

  function renderFallbackTable(fallbackSolutions: Solution[]) {
    const safeArr = fallbackSolutions || []
    if (safeArr.length === 0) return null

    // 提取所有参数 key 作为维度
    const paramKeys = new Set<string>()
    safeArr.forEach(s => {
      if (s?.parameters) Object.keys(s.parameters).forEach(k => paramKeys.add(k))
    })
    const dims = [...paramKeys].slice(0, 8)

    // 找每维度最优值
    const bestByDim: Record<string, string> = {}
    dims.forEach(key => {
      let bestVal: number | null = null
      let bestId: string | null = null
      safeArr.forEach(s => {
        const val = s?.parameters?.[key]
        if (typeof val !== 'number') return
        if (bestVal === null || val > bestVal) {
          bestVal = val
          bestId = s.id
        }
      })
      if (bestId) bestByDim[key] = bestId
    })

    // 预计算最大评分
    const maxScore = safeArr.length > 0 ? Math.max(...safeArr.map(s => s?.score || 0)) : 0

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-3 px-4 font-semibold text-muted-foreground w-32">维度</th>
              {safeArr.map(sol => (
                <th key={sol.id} className="py-3 px-4 text-center font-semibold">
                  <div className="flex flex-col items-center gap-1">
                    <span>{sol?.name || ''}</span>
                    <StatusTag status={sol?.status || 'pending'} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* 评分行 */}
            <tr className="border-b hover:bg-muted/30">
              <td className="py-2.5 px-4 font-medium text-foreground">综合评分</td>
              {safeArr.map(sol => {
                const isBest = sol?.score === maxScore && sol?.score != null
                return (
                  <td key={sol.id} className={`py-2.5 px-4 text-center font-bold ${isBest ? 'bg-green-50 text-green-700' : ''}`}>
                    {sol?.score != null ? sol.score.toFixed(2) : '—'}
                  </td>
                )
              })}
            </tr>
            {/* 参数行 */}
            {dims.map(key => (
              <tr key={key} className="border-b hover:bg-muted/30">
                <td className="py-2.5 px-4 font-medium text-foreground">{key}</td>
                {safeArr.map(sol => {
                  const val = sol?.parameters?.[key]
                  const isBest = bestByDim[key] === sol.id
                  return (
                    <td key={sol.id} className={`py-2.5 px-4 text-center ${isBest ? 'bg-green-50 text-green-700 font-bold' : ''}`}>
                      {typeof val === 'number' ? val.toFixed(2) : val != null ? String(val) : '—'}
                      {isBest && ' ✓'}
                    </td>
                  )
                })}
              </tr>
            ))}
            {/* 轮次 */}
            <tr className="border-b hover:bg-muted/30">
              <td className="py-2.5 px-4 font-medium text-foreground">轮次</td>
              {safeArr.map(sol => (
                <td key={sol.id} className="py-2.5 px-4 text-center text-muted-foreground">
                  R{sol?.round || 0}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    )
  }

  // ── 渲染 ──────────────────────────────────────────────────────────────

  const safeSolutions = Array.isArray(solutions) ? solutions : []
  const safeGoals = Array.isArray(goals) ? goals : []
  const safeCompareData = compareData || null
  const safeTrendData = trendData || null
  const trendPoints = (safeTrendData as any)?.points || []

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  if (error && safeSolutions.length === 0 && !safeCompareData) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <Button onClick={() => window.location.reload()}>重试</Button>
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
            <BarChart3 className="w-5 h-5 text-muted-foreground" />
            方案对比中心
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">多维度对比方案 · 分析收敛趋势</p>
        </div>
        <div className="flex gap-2">
          <Select value={selectedGoalId} onValueChange={setSelectedGoalId}>
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder="选择目标" />
            </SelectTrigger>
            <SelectContent>
              {safeGoals.map(g => (
                <SelectItem key={g.id} value={g.id}>{g.title || '未命名目标'}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={() => {
            if (selectedGoalId) {
              setLoading(true)
              Promise.allSettled([
                solutionsApi.list(selectedGoalId),
                solutionsApi.multiCompare(selectedGoalId),
                solutionsApi.trend(selectedGoalId),
              ]).then(([sRes, cRes, tRes]) => {
                if (sRes.status === 'fulfilled') {
                  const arr = Array.isArray(sRes.value) ? sRes.value : (sRes.value as SolutionListResponse)?.solutions || []
                  setSolutions(arr)
                }
                if (cRes.status === 'fulfilled') setCompareData(cRes.value)
                if (tRes.status === 'fulfilled') setTrendData(tRes.value)
                setLoading(false)
              })
            }
          }} title="刷新">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* 方案数量概览 */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">方案总数</p>
            <p className="text-2xl font-bold">{safeSolutions.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">达标方案</p>
            <p className="text-2xl font-bold text-green-600">
              {safeSolutions.filter(s => s.status === 'compliant' || s.status === 'optimal').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">最优方案</p>
            <p className="text-2xl font-bold text-yellow-600">
              {safeSolutions.filter(s => s.status === 'optimal').length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">最高评分</p>
            <p className="text-2xl font-bold text-blue-600">
              {safeSolutions.length > 0 ? Math.max(...safeSolutions.map(s => s.score || 0)).toFixed(1) : '—'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="compare">
        <TabsList>
          <TabsTrigger value="compare" className="flex items-center gap-1">
            <BarChart3 className="w-3.5 h-3.5" /> 多维对比
          </TabsTrigger>
          <TabsTrigger value="trend" className="flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5" /> 收敛趋势
          </TabsTrigger>
          <TabsTrigger value="list" className="flex items-center gap-1">
            <Target className="w-3.5 h-3.5" /> 方案列表
          </TabsTrigger>
        </TabsList>

        {/* 多维对比 */}
        <TabsContent value="compare" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>多维度对比</CardTitle>
              <CardDescription>
                绿色标记最优值，金色边框为整体最优方案
              </CardDescription>
            </CardHeader>
            <CardContent>
              {safeSolutions.length === 0 ? (
                <div className="text-center py-12">
                  <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground">该目标下暂无方案</p>
                </div>
              ) : (
                <>
                  {renderCompareTable}
                  <div className="mt-4 flex flex-wrap gap-2">
                    {safeSolutions.map(sol => (
                      <Button key={sol.id} variant="outline" size="sm" onClick={() => handleViewDetail(sol)}>
                        <Eye className="w-3.5 h-3.5 mr-1" /> {sol.name}
                      </Button>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 收敛趋势 */}
        <TabsContent value="trend" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4" /> 收敛趋势图
              </CardTitle>
              <CardDescription>
                展示各轮次核心指标变化趋势（工期、成本、安全评分）
              </CardDescription>
            </CardHeader>
            <CardContent>
              {safeTrendData && (safeTrendData as any).points && (safeTrendData as any).points.length > 0 ? (
                <div className="flex justify-center">
                  <TrendChart data={safeTrendData} width={700} height={320} />
                </div>
              ) : (
                <div className="text-center py-12">
                  <TrendingUp className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground">
                    {safeSolutions.length === 0 ? '暂无方案数据，无法生成趋势图' : '暂缺少趋势数据'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 方案列表 */}
        <TabsContent value="list" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>方案列表</CardTitle>
            </CardHeader>
            <CardContent>
              {safeSolutions.length === 0 ? (
                <div className="text-center py-12">
                  <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                  <p className="text-muted-foreground">暂无方案</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {safeSolutions.map(sol => (
                    <div
                      key={sol.id}
                      className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                      onClick={() => handleViewDetail(sol)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold">{sol.name}</span>
                        <StatusTag status={sol.status} />
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>R{sol.round || 0}</span>
                        <span>评分: {sol.score != null ? sol.score.toFixed(1) : '—'}</span>
                      </div>
                      {sol.parameters && Object.keys(sol.parameters).length > 0 && (
                        <div className="mt-2 text-xs text-muted-foreground">
                          {Object.entries(sol.parameters).slice(0, 3).map(([k, v]) => (
                            <span key={k} className="mr-2">{k}: {typeof v === 'object' ? JSON.stringify(v) : v}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 方案详情弹窗 */}
      <SolutionDetailModal
        open={detailOpen}
        onOpenChange={setDetailOpen}
        solution={detailSolution}
        onSuccess={() => {
          if (selectedGoalId) {
            solutionsApi.list(selectedGoalId).then(res => {
              const arr = Array.isArray(res) ? res : (res as SolutionListResponse)?.solutions || []
              setSolutions(arr)
            }).catch(() => {})
          }
        }}
      />
    </div>
  )
}
