/**
 * Sprint 68-73: 方案列表页
 * 路由：/goals/:id/solutions
 */

import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { toast } from 'sonner'
import {
  ArrowLeft, RefreshCw, AlertCircle, Loader2, Target, Search, Plus,
  Eye, Trophy, Ban, Trash2, Hash, Star, Filter,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Badge } from '@/shared/components/ui/badge'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/shared/components/ui/table'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select'
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '@/shared/components/ui/dialog'
import { Label } from '@/shared/components/ui/label'
import { Textarea } from '@/shared/components/ui/textarea'
import SolutionDetailModal from '@/evo/components/SolutionDetailModal'
import { solutionsApi, type Solution, type SolutionListResponse } from '@/evo/services/solutions'
import { goalsApi, type Goal } from '@/shared/utils/api'
import { confirmAction } from '@/shared/utils/notify'

// ── 状态标签配置 ──────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; emoji: string; color: string; bg: string }> = {
  compliant: { label: '达标', emoji: '✅', color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  non_compliant: { label: '不达标', emoji: '❌', color: 'text-red-700', bg: 'bg-red-50 border-red-200' },
  optimal: { label: '最优', emoji: '🏆', color: 'text-yellow-700', bg: 'bg-yellow-50 border-yellow-200' },
  rejected: { label: '否决', emoji: '⛔', color: 'text-gray-500', bg: 'bg-gray-50 border-gray-200' },
  pending: { label: '待评估', emoji: '⏳', color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200' },
}

function StatusTag({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      <span>{cfg.emoji}</span>
      <span>{cfg.label}</span>
    </span>
  )
}

// ── 格式化 ────────────────────────────────────────────────────────────────

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

function formatParams(params: Record<string, any> | undefined): string {
  if (!params) return '—'
  const entries = Object.entries(params).slice(0, 3)
  return entries.map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(', ')
}

// ── 新建方案弹窗 ──────────────────────────────────────────────────────────

interface CreateSolutionModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  goalId: string
  onSuccess: () => void
}

function CreateSolutionModal({ open, onOpenChange, goalId, onSuccess }: CreateSolutionModalProps) {
  const [name, setName] = useState('')
  const [round, setRound] = useState('1')
  const [params, setParams] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!name.trim()) { toast.error('请输入方案名称'); return }
    setSubmitting(true)
    try {
      let parsedParams: Record<string, any> = {}
      if (params.trim()) {
        parsedParams = JSON.parse(params)
      }
      await solutionsApi.create({
        goal_id: goalId,
        name: name.trim(),
        round: parseInt(round) || 1,
        parameters: parsedParams,
      })
      toast.success('方案创建成功')
      setName(''); setRound('1'); setParams('')
      onOpenChange(false)
      onSuccess()
    } catch (e: any) {
      toast.error(`创建失败：${e.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="w-4 h-4" /> 新建方案
          </DialogTitle>
          <DialogDescription>为目标创建新的设计方案</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>方案名称</Label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="输入方案名称" />
          </div>
          <div>
            <Label>轮次</Label>
            <Input type="number" value={round} onChange={e => setRound(e.target.value)} min={1} />
          </div>
          <div>
            <Label>参数 (JSON)</Label>
            <Textarea value={params} onChange={e => setParams(e.target.value)} placeholder='{"工期": 30, "成本": 100}' rows={4} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>取消</Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── 主页面 ────────────────────────────────────────────────────────────────

export default function SolutionList() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [goal, setGoal] = useState<Goal | null>(null)
  const [solutions, setSolutions] = useState<Solution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 搜索和筛选
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [roundFilter, setRoundFilter] = useState<string>('all')

  // 弹窗
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailSolution, setDetailSolution] = useState<Solution | null>(null)

  const fetchData = useCallback(async () => {
    if (!id) return
    try {
      setLoading(true)
      setError(null)
      const [goalData, solutionsData] = await Promise.all([
        goalsApi.get(id),
        solutionsApi.list(id),
      ])
      setGoal(goalData)
      // 后端返回 { solutions: [...], total: N }，需要取 .solutions
      const arr = Array.isArray(solutionsData) ? solutionsData : (solutionsData as SolutionListResponse)?.solutions || []
      setSolutions(arr)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { fetchData() }, [fetchData])

  // 筛选
  const filteredSolutions = solutions.filter(s => {
    if (statusFilter !== 'all' && s.status !== statusFilter) return false
    if (roundFilter !== 'all' && String(s.round) !== roundFilter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (s.name || '').toLowerCase().includes(q) ||
        (s.id || '').toLowerCase().includes(q)
    }
    return true
  }).sort((a, b) => {
    // 轮次降序，同轮次按评分降序
    const roundDiff = (b.round || 0) - (a.round || 0)
    if (roundDiff !== 0) return roundDiff
    return (b.score || 0) - (a.score || 0)
  })

  // 获取所有轮次
  const rounds = [...new Set(solutions.map(s => s.round))].sort((a, b) => b - a)

  // 操作
  async function handleViewDetail(solution: Solution) {
    setDetailSolution(solution)
    setDetailOpen(true)
  }

  async function handleSetOptimal(solution: Solution) {
    try {
      await solutionsApi.update(solution.id, { status: 'optimal' })
      toast.success('已标记为最优方案')
      fetchData()
    } catch (e: any) {
      toast.error(`操作失败：${e.message}`)
    }
  }

  async function handleReject(solution: Solution) {
    if (!(await confirmAction({ title: '否决方案', description: `确定否决方案「${solution.name}」吗？`, variant: 'destructive' }))) return
    try {
      await solutionsApi.update(solution.id, { status: 'rejected' })
      toast.success('已否决该方案')
      fetchData()
    } catch (e: any) {
      toast.error(`操作失败：${e.message}`)
    }
  }

  async function handleDelete(solution: Solution) {
    if (!(await confirmAction({ title: '删除方案', description: `确定删除方案「${solution.name}」吗？`, variant: 'destructive' }))) return
    try {
      await solutionsApi.remove(solution.id)
      toast.success('方案已删除')
      fetchData()
    } catch (e: any) {
      toast.error(`删除失败：${e.message}`)
    }
  }

  // ── 渲染 ──────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载方案列表...</p>
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
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" asChild>
            <Link to={`/coordination/goals/${id}`}><ArrowLeft className="w-4 h-4" /></Link>
          </Button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Target className="w-5 h-5 text-muted-foreground" />
              方案列表
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {goal?.title || '未命名目标'} · 共 {solutions.length} 个方案
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate('/solutions')}>
            📊 方案对比
          </Button>
          <Button size="sm" onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4 mr-1" /> 新建方案
          </Button>
          <Button variant="outline" size="icon" onClick={fetchData} title="刷新">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="搜索方案名称或 ID..."
            className="pl-10"
          />
        </div>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
              <SelectItem key={key} value={key}>{cfg.emoji} {cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {rounds.length > 0 && (
          <Select value={roundFilter} onValueChange={setRoundFilter}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="全部轮次" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部轮次</SelectItem>
              {rounds.map(r => (
                <SelectItem key={r} value={String(r)}>Round {r}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {(statusFilter !== 'all' || roundFilter !== 'all' || searchQuery) && (
          <Button variant="ghost" size="sm" onClick={() => { setSearchQuery(''); setStatusFilter('all'); setRoundFilter('all') }}>
            重置
          </Button>
        )}
      </div>

      {/* 表格 */}
      <div className="rounded-lg border bg-card">
        {filteredSolutions.length === 0 ? (
          <div className="text-center py-16">
            <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-2">
              {solutions.length === 0 ? '该目标下暂无方案' : '没有匹配的方案'}
            </p>
            {solutions.length === 0 && (
              <Button variant="link" onClick={() => setShowCreateModal(true)}>
                点击「新建方案」开始
              </Button>
            )}
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16"><Hash className="w-4 h-4" /></TableHead>
                  <TableHead>方案名称</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>核心参数</TableHead>
                  <TableHead className="w-20">评分</TableHead>
                  <TableHead className="w-36">创建时间</TableHead>
                  <TableHead className="w-52">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSolutions.map(solution => (
                  <TableRow key={solution.id}>
                    <TableCell>
                      <span className="text-xs text-muted-foreground font-mono">
                        R{solution.round || 0}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="font-medium text-foreground">{solution.name || '未命名'}</span>
                      <span className="text-xs text-muted-foreground ml-2 font-mono">
                        #{solution.id?.slice(0, 6)}
                      </span>
                    </TableCell>
                    <TableCell><StatusTag status={solution.status} /></TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground max-w-xs truncate block">
                        {formatParams(solution.parameters)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className={`font-bold text-sm ${
                        (solution.score || 0) >= 80 ? 'text-green-600' :
                        (solution.score || 0) >= 60 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {solution.score != null ? solution.score.toFixed(1) : '—'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">{formatTime(solution.created_at)}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleViewDetail(solution)} title="查看详情">
                          <Eye className="w-3.5 h-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleSetOptimal(solution)} disabled={solution.status === 'optimal'} title="标记最优">
                          <Trophy className="w-3.5 h-3.5 text-yellow-600" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleReject(solution)} disabled={solution.status === 'rejected'} title="否决">
                          <Ban className="w-3.5 h-3.5 text-gray-500" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(solution)} title="删除">
                          <Trash2 className="w-3.5 h-3.5 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </div>

      {/* 新建方案弹窗 */}
      <CreateSolutionModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        goalId={id || ''}
        onSuccess={fetchData}
      />

      {/* 方案详情弹窗 */}
      <SolutionDetailModal
        open={detailOpen}
        onOpenChange={setDetailOpen}
        solution={detailSolution}
        onSuccess={fetchData}
      />
    </div>
  )
}
