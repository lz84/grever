import { useState, useEffect } from "react"
import { BarChart3, TrendingUp, Clock, CheckCircle, XCircle, Loader2, AlertTriangle, History } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import { Button } from "@/shared/components/ui/button"
import { Input } from "@/shared/components/ui/input"
import { Label } from "@/shared/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/components/ui/table"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs"

interface HistoryItem {
  id: string
  task_id: string
  title: string
  description: string | null
  input_type: string
  status: string
  submitted_by: string | null
  submitted_at: string | null
  created_at: string
  context: any
  approval_reason: string | null
  executor_type: string | null
}

interface DailyStat {
  date: string
  total: number
  approved: number
  rejected: number
  avg_duration_minutes: number
}

interface AgentStat {
  agent_id: string
  name: string
  total_requests: number
  approved: number
  rejected: number
  avg_duration_minutes: number
}

export function HumanInputAnalytics() {
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<{
    total_requests: number
    approved: number
    rejected: number
    pending: number
    avg_duration_minutes: number
  }>({
    total_requests: 0,
    approved: 0,
    rejected: 0,
    pending: 0,
    avg_duration_minutes: 0,
  })
  const [dailyStats, setDailyStats] = useState<DailyStat[]>([])
  const [agentStats, setAgentStats] = useState<AgentStat[]>([])
  const [historyRequests, setHistoryRequests] = useState<HistoryItem[]>([])
  const [dateRange, setDateRange] = useState("7d")

  useEffect(() => {
    loadData()
  }, [dateRange])

  const loadData = async () => {
    setLoading(true)
    try {
      const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : 90
      const res = await fetch(`/api/v1/human-input/analytics?days=${days}`)
      if (res.ok) {
        const data = await res.json()
        setStats(data.summary || {
          total_requests: 0,
          approved: 0,
          rejected: 0,
          pending: 0,
          avg_duration_minutes: 0,
        })
        setDailyStats(data.daily || [])
        setAgentStats(data.by_agent || [])
      }
    } catch {
      setStats({ total_requests: 0, approved: 0, rejected: 0, pending: 0, avg_duration_minutes: 0 })
      setDailyStats([])
      setAgentStats([])
    } finally {
      setLoading(false)
    }

    // Fetch history (Sprint 92 F92-3)
    try {
      const historyRes = await fetch(`/api/v1/human-input/recent?limit=50`)
      if (historyRes.ok) {
        const historyData = await historyRes.json()
        setHistoryRequests(Array.isArray(historyData) ? historyData : (historyData.requests || []))
      }
    } catch {
      setHistoryRequests([])
    }
  }

  const approvalRate = stats.total_requests > 0
    ? ((stats.approved / stats.total_requests) * 100).toFixed(1)
    : "0.0"

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <BarChart3 className="h-8 w-8" />
            人工输入分析
          </h1>
          <p className="text-muted-foreground mt-1">
            人工输入请求的处理效率和质量分析
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">最近7天</SelectItem>
              <SelectItem value="30d">最近30天</SelectItem>
              <SelectItem value="90d">最近90天</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={loadData} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BarChart3 className="mr-2 h-4 w-4" />}
            刷新
          </Button>
        </div>
      </div>

      {/* Stats overview */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总请求数</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_requests}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">通过</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.approved}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">驳回</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.rejected}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均处理时长</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.avg_duration_minutes.toFixed(1)} min
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">通过率</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{approvalRate}%</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="daily" className="space-y-4">
        <TabsList>
          <TabsTrigger value="daily">每日趋势</TabsTrigger>
          <TabsTrigger value="agents">按Agent统计</TabsTrigger>
          <TabsTrigger value="history">审批历史</TabsTrigger>
        </TabsList>

        <TabsContent value="daily">
          <Card>
            <CardHeader>
              <CardTitle>每日处理量</CardTitle>
              <CardDescription>每天的人工输入请求处理情况</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : dailyStats.length === 0 ? (
                <p className="text-center py-12 text-muted-foreground">暂无数据</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日期</TableHead>
                      <TableHead className="text-right">总请求</TableHead>
                      <TableHead className="text-right">通过</TableHead>
                      <TableHead className="text-right">驳回</TableHead>
                      <TableHead className="text-right">平均处理时长</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dailyStats.map((day) => (
                      <TableRow key={day.date}>
                        <TableCell className="font-medium">{day.date}</TableCell>
                        <TableCell className="text-right">{day.total}</TableCell>
                        <TableCell className="text-right text-green-600">{day.approved}</TableCell>
                        <TableCell className="text-right text-red-600">{day.rejected}</TableCell>
                        <TableCell className="text-right">{day.avg_duration_minutes.toFixed(1)} min</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents">
          <Card>
            <CardHeader>
              <CardTitle>按Agent统计</CardTitle>
              <CardDescription>各Agent处理人工输入请求的情况</CardDescription>
            </CardHeader>
            <CardContent>
              {agentStats.length === 0 ? (
                <p className="text-center py-12 text-muted-foreground">暂无数据</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Agent</TableHead>
                      <TableHead className="text-right">总请求</TableHead>
                      <TableHead className="text-right">通过</TableHead>
                      <TableHead className="text-right">驳回</TableHead>
                      <TableHead className="text-right">通过率</TableHead>
                      <TableHead className="text-right">平均处理时长</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {agentStats.map((agent) => {
                      const rate = agent.total_requests > 0
                        ? ((agent.approved / agent.total_requests) * 100).toFixed(1)
                        : "0.0"
                      return (
                        <TableRow key={agent.agent_id}>
                          <TableCell className="font-medium">{agent.name || agent.agent_id}</TableCell>
                          <TableCell className="text-right">{agent.total_requests}</TableCell>
                          <TableCell className="text-right text-green-600">{agent.approved}</TableCell>
                          <TableCell className="text-right text-red-600">{agent.rejected}</TableCell>
                          <TableCell className="text-right">
                            <Badge variant={parseFloat(rate) >= 80 ? "default" : "secondary"}>
                              {rate}%
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">{agent.avg_duration_minutes.toFixed(1)} min</TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sprint 92 F92-3: 审批历史 Tab */}
        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>审批历史</CardTitle>
              <CardDescription>所有人工输入请求的处理记录</CardDescription>
            </CardHeader>
            <CardContent>
              {historyRequests.length === 0 ? (
                <p className="text-center py-12 text-muted-foreground">暂无历史记录</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>提交人</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>任务</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>提交时间</TableHead>
                      <TableHead>审批理由</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historyRequests.map((req) => (
                      <TableRow key={req.id}>
                        <TableCell className="font-medium">
                          {req.submitted_by || '—'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {req.input_type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                          {req.task_id?.slice(0, 16)}...
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              req.status === 'submitted' ? 'default' :
                              req.status === 'rejected' ? 'destructive' :
                              req.status === 'pending' ? 'secondary' : 'outline'
                            }
                            className="text-xs"
                          >
                            {req.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {req.submitted_at ? new Date(req.submitted_at).toLocaleString('zh-CN') : '—'}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                          {req.approval_reason || '—'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
