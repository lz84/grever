import { useState, useEffect, useCallback } from 'react'
import { toast } from "sonner"
import { useConfirmDialog } from "@/shared/utils/notify"
import { adminApi } from '../../shared/services/adminApi'
import { agentsApi } from '../../shared/utils/api'
import type { Agent } from '../../shared/utils/api'
import { Bot, RefreshCw, PowerOff, Loader2, AlertTriangle, CheckCircle, Clock, Play, Settings2, Plus } from 'lucide-react'
import AgentPlatformRegister from '@/pages/reins/agent/AgentPlatformRegister'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'

type AgentStatus = 'online' | 'busy' | 'offline' | 'idle'

const STATUS_OPTIONS: { value: AgentStatus; label: string; variant: string }[] = [
  { value: 'online', label: '在线', variant: 'success' },
  { value: 'busy', label: '忙碌', variant: 'warning' },
  { value: 'idle', label: '空闲', variant: 'info' },
  { value: 'offline', label: '离线', variant: 'destructive' },
]

export default function AgentManagement() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [toastMsg, setToastMsg] = useState<string | null>(null)
  const [statusMenu, setStatusMenu] = useState<string | null>(null)
  const [registerOpen, setRegisterOpen] = useState(false)
  const { confirm, ConfirmDialog } = useConfirmDialog()

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await agentsApi.list()
      setAgents(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const showToast = (msg: string) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(null), 3000)
  }

  async function handleRestart(agent: Agent) {
    if (!(await confirm({ title: '重启 Agent', description: `确定要重启 Agent "${agent.name}" 吗？其进行中的任务将被回收并重置。`, variant: 'destructive' }))) return
    setActionLoading(`restart-${agent.id}`)
    try {
      const res = await adminApi.restartAgent(agent.id)
      showToast(res.message)
      await fetchData()
    } catch (e: any) {
      showToast(`重启失败: ${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleSetStatus(agent: Agent, status: AgentStatus) {
    setActionLoading(`status-${agent.id}`)
    try {
      const res = await adminApi.setAgentStatus(agent.id, status)
      showToast(res.message)
      await fetchData()
    } catch (e: any) {
      showToast(`设置状态失败: ${e.message}`)
    } finally {
      setActionLoading(null)
      setStatusMenu(null)
    }
  }

  async function handleForceOffline(agent: Agent) {
    if (!(await confirm({ title: '强制下线', description: `确定要将 Agent "${agent.name}" 强制下线吗？其进行中的任务将被回收。`, variant: 'destructive' }))) return
    setActionLoading(agent.id)
    try {
      const res = await adminApi.forceOfflineAgent(agent.id)
      showToast(res.message)
      await fetchData()
    } catch (e: any) {
      showToast(`操作失败: ${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleCleanupAll() {
    if (!(await confirm({ title: '清理僵尸任务', description: '确定要清理所有僵尸任务吗？', variant: 'destructive' }))) return
    setActionLoading('cleanup')
    try {
      const res = await adminApi.cleanupZombieTasks()
      showToast(`清理完成: ${res.cleaned_count} 个任务已处理。详情: ${res.details.join('; ')}`)
      await fetchData()
    } catch (e: any) {
      showToast(`清理失败: ${e.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  function formatTime(isoStr: string | null): string {
    if (!isoStr) return '—'
    try {
      const d = new Date(isoStr)
      const now = new Date()
      const diffMs = now.getTime() - d.getTime()
      const diffMin = Math.floor(diffMs / 60000)
      if (diffMin < 1) return '刚刚'
      if (diffMin < 60) return `${diffMin} 分钟前`
      const diffHr = Math.floor(diffMin / 60)
      if (diffHr < 24) return `${diffHr} 小时前`
      const diffDay = Math.floor(diffHr / 24)
      return `${diffDay} 天前`
    } catch {
      return isoStr
    }
  }

  // Match dashboard status mapping
  function mapAgentStatus(status: string): 'online' | 'busy' | 'offline' {
    if (status === 'online' || status === 'idle') return 'online'
    if (status === 'busy' || status === 'working') return 'busy'
    return 'offline'
  }

  function mapAgentStatusText(status: string): string {
    const mapped = mapAgentStatus(status)
    return mapped === 'online' ? '在线' : mapped === 'busy' ? '忙碌' : '离线'
  }

  function getAgentStatusVariant(status: string): string {
    const mapped = mapAgentStatus(status)
    return mapped === 'online' ? 'success' : mapped === 'busy' ? 'warning' : 'destructive'
  }

  function getStatusIcon(status: string) {
    const mapped = mapAgentStatus(status)
    switch (mapped) {
      case 'online':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'busy':
        return <Clock className="w-4 h-4 text-amber-500" />
      case 'offline':
        return <PowerOff className="w-4 h-4 text-red-500" />
      default:
        return <AlertTriangle className="w-4 h-4 text-muted-foreground" />
    }
  }

  function getStatusBadgeVariant(status: string): 'success' | 'warning' | 'destructive' | 'secondary' | 'info' {
    const variant = getAgentStatusVariant(status)
    return variant as any
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-20 right-6 z-50 bg-slate-900 text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-sm animate-fade-in">
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-foreground">Agent 管理</h2>
          <p className="text-sm text-muted-foreground mt-1">管理系统中的智能体状态和任务分配</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleCleanupAll}
            disabled={actionLoading === 'cleanup'}
            className="border-amber-200 text-amber-700 hover:bg-amber-50"
          >
            {actionLoading === 'cleanup' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <AlertTriangle className="w-4 h-4 mr-2" />}
            清理僵尸任务
          </Button>
          <Button variant="outline" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button onClick={() => setRegisterOpen(true)} className="bg-blue-600 hover:bg-blue-500">
            <Plus className="w-4 h-4 mr-2" />
            注册智能体
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">总计</div>
            <div className="text-2xl font-bold text-foreground">{agents.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">在线</div>
            <div className="text-2xl font-bold text-green-600">{agents.filter(a => mapAgentStatus(a.status) === 'online').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">离线</div>
            <div className="text-2xl font-bold text-red-600">{agents.filter(a => mapAgentStatus(a.status) === 'offline').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">高负载 (&gt;70%)</div>
            <div className="text-2xl font-bold text-amber-600">{agents.filter(a => (a as any).load > 70).length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Agent List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">加载中...</span>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-left">Agent</TableHead>
                  <TableHead className="text-left">平台</TableHead>
                  <TableHead className="text-left">状态</TableHead>
                  <TableHead className="text-left">最后心跳</TableHead>
                  <TableHead className="text-left">模型</TableHead>
                  <TableHead className="text-center">负载</TableHead>
                  <TableHead className="text-center">任务</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map(agent => (
                  <TableRow key={agent.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Bot className="w-4 h-4 text-muted-foreground" />
                        <div>
                          <div className="font-medium text-foreground">{agent.name}</div>
                          <div className="text-xs text-muted-foreground font-mono">{agent.id}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-mono text-xs">
                        {agent.platform_type || 'openclaw'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(agent.status) as any} className="flex items-center gap-1.5 w-fit">
                        {getStatusIcon(agent.status)}
                        {mapAgentStatusText(agent.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs text-muted-foreground">{agent.last_heartbeat || '—'}</div>
                      <div className="text-sm">{formatTime(agent.last_heartbeat)}</div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground font-mono">
                        {agent.model_name || '—'}
                      </span>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden max-w-[80px]">
                          <div
                            className={`h-full ${((agent as any).load || 0) >= 90 ? 'bg-red-500' : ((agent as any).load || 0) >= 70 ? 'bg-amber-500' : 'bg-green-500'} rounded-full`}
                            style={{ width: `${Math.min((agent as any).load || 0, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-500 w-8">{(agent as any).load ?? 0}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className="text-sm text-slate-600">{(agent as any).current_tasks ?? 0}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1.5 flex-wrap">
                        {/* 重启按钮 */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRestart(agent)}
                          disabled={actionLoading === `restart-${agent.id}`}
                          className="border-violet-200 text-violet-700 hover:bg-violet-50"
                          title="重启 Worker：回收任务并重置状态"
                        >
                          {actionLoading === `restart-${agent.id}` ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                          <span className="ml-1">重启</span>
                        </Button>

                        {/* 设置状态下拉 */}
                        <div className="relative">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setStatusMenu(statusMenu === agent.id ? null : agent.id)}
                            disabled={actionLoading?.startsWith(`status-${agent.id}`)}
                            className="border-sky-200 text-sky-700 hover:bg-sky-50"
                            title="手动设置状态"
                          >
                            {actionLoading?.startsWith(`status-${agent.id}`) ? <Loader2 className="w-3 h-3 animate-spin" /> : <Settings2 className="w-3 h-3" />}
                            <span className="ml-1">状态</span>
                          </Button>
                          {statusMenu === agent.id && (
                            <div className="absolute right-0 top-full mt-1 bg-background border border-border rounded-lg shadow-lg z-20 min-w-[100px] p-1">
                              {STATUS_OPTIONS.map(opt => (
                                <button
                                  key={opt.value}
                                  onClick={() => handleSetStatus(agent, opt.value)}
                                  className={`w-full text-left px-3 py-2 text-sm rounded-md hover:bg-muted flex items-center gap-2 ${
                                    mapAgentStatus(agent.status) === opt.value ? 'font-semibold' : ''
                                  }`}
                                >
                                  <span className={`inline-block w-2 h-2 rounded-full ${
                                    opt.value === 'online' ? 'bg-green-500' :
                                    opt.value === 'busy' ? 'bg-amber-500' :
                                    opt.value === 'idle' ? 'bg-blue-500' : 'bg-red-500'
                                  }`} />
                                  {opt.label}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* 下线按钮 */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleForceOffline(agent)}
                          disabled={actionLoading === agent.id || actionLoading?.startsWith(`status-${agent.id}`) || actionLoading === `restart-${agent.id}`}
                          className="border-red-200 text-red-700 hover:bg-red-50"
                        >
                          <PowerOff className="w-3 h-3" />
                          <span className="ml-1">下线</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {agents.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                      暂无 Agent 数据
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      <ConfirmDialog />

      <AgentPlatformRegister
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onSuccess={async (agent) => {
          showToast(`智能体 "${agent.name}" 注册成功`)
          await fetchData()
        }}
      />
    </div>
  )
}
