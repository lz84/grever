import { useState, useEffect } from 'react'
import { WORKFLOWS } from '../../shared/api/paths'
import { Search, RefreshCw, AlertCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/shared/components/ui/card'
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
import { Progress } from '@/shared/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/shared/components/ui/pagination'

const STATUS_LABELS: Record<string, string> = {
  running: '运行中', completed: '已完成', failed: '失败', cancelled: '已取消',
}

function getStatusVariant(status: string): any {
  const map: Record<string, any> = {
    running: 'info',
    completed: 'success',
    failed: 'destructive',
    cancelled: 'secondary',
  }
  return map[status] || 'secondary'
}

export default function TraceViewer() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [timeRange, setTimeRange] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalWorkflows, setTotalWorkflows] = useState(0)
  const ITEMS_PER_PAGE = 10

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const params: Record<string, string | number> = {
        limit: ITEMS_PER_PAGE,
        skip: (currentPage - 1) * ITEMS_PER_PAGE,
      }
      if (searchQuery) params.search = searchQuery
      if (timeRange) params.time_range = timeRange

      const res = await fetch(`/api/v1/workflows?${new URLSearchParams(params as any).toString()}`)
      if (!res.ok) throw new Error(`API ${res.status}`)
      const data = await res.json()
      const wfList = Array.isArray(data) ? data : (data.items || [])
      const total = Array.isArray(data) ? wfList.length : (data.total || wfList.length)
      setWorkflows(wfList)
      setTotalWorkflows(total)
    } catch (e: any) {
      console.error('fetchData error:', e)
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, searchQuery, timeRange])

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const totalPages = Math.max(1, Math.ceil(totalWorkflows / ITEMS_PER_PAGE))
  const paginatedWorkflows = workflows.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)

  const pageNumbers: number[] = []
  const maxVisible = 5
  let start = Math.max(1, currentPage - Math.floor(maxVisible / 2))
  const end = Math.min(totalPages, start + maxVisible - 1)
  start = Math.max(1, end - maxVisible + 1)
  for (let i = start; i <= end; i++) {
    pageNumbers.push(i)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <Card className="max-w-md mx-auto">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-10 h-10 text-destructive mb-4" />
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={fetchData}>重试</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>目标追踪</CardTitle>
              <CardDescription>查看所有工作流的执行记录、阶段状态和产出结果</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchData}>
              <RefreshCw className="w-4 h-4 mr-1" />刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1) }}
                placeholder="搜索工作流..."
                className="pl-10"
              />
            </div>
            <Select value={timeRange || 'all'} onValueChange={(v) => { setTimeRange(v); setCurrentPage(1) }}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="全部时间" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部时间</SelectItem>
                <SelectItem value="today">今天</SelectItem>
                <SelectItem value="week">本周</SelectItem>
                <SelectItem value="month">本月</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      {paginatedWorkflows.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Search className="w-10 h-10 text-muted-foreground mb-2" />
            <p className="text-muted-foreground">暂无执行记录</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10"></TableHead>
                  <TableHead>工作流</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>进度</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedWorkflows.map((wf: any) => {
                  const isExpanded = expandedIds.has(wf.id)
                  const label = STATUS_LABELS[wf.status] || wf.status || '未知'
                  const totalSteps = (wf.steps || []).length
                  const completedSteps = (wf.steps || []).filter((s: any) => s.status === 'completed').length
                  const pct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0

                  return (
                    <>
                      <TableRow key={wf.id}>
                        <TableCell>
                          <button onClick={() => toggleExpand(wf.id)} className="p-1 hover:bg-accent rounded">
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                        </TableCell>
                        <TableCell>
                          <span className="font-medium">{wf.name || '未命名'}</span>
                          {wf.description && <p className="text-xs text-muted-foreground mt-0.5">{wf.description}</p>}
                        </TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(wf.status)}>{label}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {wf.started_at ? new Date(wf.started_at).toLocaleString('zh-CN') : '—'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={pct} className="h-2 flex-1" />
                            <span className="text-xs text-muted-foreground w-10 text-right">{pct}%</span>
                          </div>
                        </TableCell>
                      </TableRow>
                      {isExpanded && wf.steps && wf.steps.length > 0 && (
                        <TableRow>
                          <TableCell colSpan={5} className="p-0">
                            <div className="bg-muted p-4">
                              <p className="text-sm font-medium mb-2">步骤详情</p>
                              <Table>
                                <TableHeader>
                                  <TableRow>
                                    <TableHead>步骤</TableHead>
                                    <TableHead>状态</TableHead>
                                    <TableHead>Agent</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {wf.steps.map((step: any) => (
                                    <TableRow key={step.id}>
                                      <TableCell className="text-sm">{step.name || '—'}</TableCell>
                                      <TableCell><Badge variant="secondary">{step.status}</Badge></TableCell>
                                      <TableCell className="text-muted-foreground text-sm">{step.agent_id || '—'}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            显示第 {(currentPage - 1) * ITEMS_PER_PAGE + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, totalWorkflows)} 项，共 {totalWorkflows} 项
          </div>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => setCurrentPage(page)}
          />
        </div>
      )}
    </div>
  )
}
