import { useState, useEffect } from 'react'
import { AGENTS } from '../../../shared/api/paths'
import { toast } from "sonner"
import { ConfirmDialog, confirmAction } from "@/shared/utils/notify"
import { agentsApi } from '../../../shared/utils/api'
import type { Agent } from '../../../shared/utils/api'
import AgentDetailModal from './AgentDetailModal'
import AgentPlatformRegister from './AgentPlatformRegister'
import { Bot, RefreshCw, AlertCircle, Loader2, UserPlus, Play, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { getAgentStatusText } from '../../../shared/utils/statusMap'
import { Pagination } from '@/shared/components/ui/pagination'
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

const ITEMS_PER_PAGE = 10

function getStatusVariant(mapped: 'online' | 'busy' | 'offline'): string {
  if (mapped === 'online') return 'success'
  if (mapped === 'busy') return 'busy'
  return 'secondary'
}

// Phase 2.4: 负载进度条颜色阈值
function getLoadColor(load: number): string {
  if (load >= 80) return 'bg-red-500'
  if (load >= 41) return 'bg-orange-500'
  return 'bg-green-500'
}

export default function AgentList() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [showRegister, setShowRegister] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  // Phase 2.1: 心跳状态
  const [heartbeatStatus, setHeartbeatStatus] = useState<Record<string, 'testing' | 'ok' | 'warning' | 'error'>>({})
  const [heartbeatFailureCount, setHeartbeatFailureCount] = useState<Record<string, number>>({})
  // Phase: 在线筛选
  const [showOnlineOnly, setShowOnlineOnly] = useState(false)

  async function handleHeartbeat(agent: Agent) {
    setHeartbeatStatus(prev => ({ ...prev, [agent.id]: 'testing' as const }))
    try {
      const res = await agentsApi.heartbeat(agent.id, {
        state: 'working',
        load: 30,
        current_tasks: 0,
        // 心跳时同步上报模型和能力信息
        model_name: agent.model_name || undefined,
        capability_tags: Object.keys(agent.capability_tags || {}).length > 0
          ? agent.capability_tags
          : undefined,
      })
      // Phase 2.2: 心跳成功后无条件刷新列表，重置失败计数
      if (res.success) {
        setHeartbeatStatus(prev => ({ ...prev, [agent.id]: 'ok' as const }))
        setHeartbeatFailureCount(prev => {
          const next = { ...prev }
          delete next[agent.id]
          return next
        })
        fetchData()
      } else {
        setHeartbeatFailureCount(prev => {
          const newCount = (prev[agent.id] || 0) + 1
          const status = newCount >= 3 ? 'error' : 'warning'
          setHeartbeatStatus(prev => ({ ...prev, [agent.id]: status as 'warning' | 'error' }))
          return { ...prev, [agent.id]: newCount }
        })
      }
      setTimeout(() => {
        setHeartbeatStatus(prev => {
          const next = { ...prev }
          delete next[agent.id]
          return next
        })
      }, 3000)
    } catch {
      setHeartbeatFailureCount(prev => {
        const newCount = (prev[agent.id] || 0) + 1
        const status = newCount >= 3 ? 'error' : 'warning'
        setHeartbeatStatus(prev => ({ ...prev, [agent.id]: status as 'warning' | 'error' }))
        return { ...prev, [agent.id]: newCount }
      })
    }
  }

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      let agentsData: Agent[]
      if (showOnlineOnly) {
        agentsData = await agentsApi.getOnline()
      } else {
        agentsData = await agentsApi.list()
      }
      setAgents(Array.isArray(agentsData) ? agentsData : agentsData ? [agentsData] : [])
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteAgent(agentId: string, agentName: string) {
    if (!(await confirmAction({ title: '删除智能体', description: '确定要删除智能体"' + agentName + '"吗？此操作不可撤销。', variant: 'destructive' }))) return
    setDeletingId(agentId)
    try {
      await agentsApi.unregister(agentId)
      toast.success(`已删除智能体 "${agentName}"`)
      fetchData()
    } catch (e: any) {
      toast.error('Delete failed: ' + (e.message || 'unknown error'))
    } finally {
      setDeletingId(null)
    }
  }

  useEffect(() => {
    fetchData()
  }, [showOnlineOnly])

  // Refresh detail modal data when agents list updates
  useEffect(() => {
    if (selectedAgent) {
      const updated = agents.find(a => a.id === selectedAgent.id)
      if (updated) setSelectedAgent(updated)
    }
  }, [agents])

  const totalPages = Math.max(1, Math.ceil(agents.length / ITEMS_PER_PAGE))
  const paginatedAgents = agents.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
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
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Bot className="w-5 h-5 text-muted-foreground" />
            智能体管理
          </h1>
          <p className="text-sm text-muted-foreground mt-1">管理所有智能体的状态与能力</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowRegister(true)}>
            <UserPlus className="w-4 h-4" />
            注册智能体
          </Button>
          <Button
            variant={showOnlineOnly ? "default" : "outline"}
            onClick={() => setShowOnlineOnly(!showOnlineOnly)}
          >
            <CheckCircle2 className="w-4 h-4 mr-1" />
            仅在线
          </Button>
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="w-4 h-4" />
            刷新
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden">
        {agents.length === 0 ? (
          <div className="text-center py-16">
            <Bot className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground">
              {showOnlineOnly ? '暂无在线智能体' : '暂无注册智能体'}
            </p>
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>智能体名称</TableHead>
                  <TableHead>模型</TableHead>
                  <TableHead>能力</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>负载</TableHead>
                  <TableHead>当前任务</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedAgents.map(agent => {
                  const mapped = getAgentStatusText(agent.status)
                  const mappedKey = mapped === '在线' ? 'online' : mapped === '繁忙' ? 'busy' : 'offline'
                  return (
                    <TableRow key={agent.id}>
                      <TableCell>
                        <button
                          onClick={() => setSelectedAgent(agent)}
                          className="font-medium text-foreground hover:text-primary"
                        >
                          {agent.name}
                        </button>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm font-mono text-xs">{agent.model_name || '-'}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-wrap">
                          {(() => {
                            const caps = Object.values(agent.capability_tags || {}).flat()
                            return (
                              <>
                                {caps.slice(0, 3).map((cap, i) => (
                                  <Badge key={i} variant="secondary">{cap}</Badge>
                                ))}
                                {caps.length > 3 && (
                                  <span className="text-xs text-muted-foreground">+{caps.length - 3}</span>
                                )}
                              </>
                            )
                          })()}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusVariant(mappedKey) as any}>
                          {mapped}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                              className={`h-full ${getLoadColor(agent.load)} rounded-full`}
                              style={{ width: `${Math.min(agent.load, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground">{agent.load}%</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-foreground">{agent.current_tasks}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedAgent(agent)}
                          >
                            详情
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleHeartbeat(agent)}
                            disabled={heartbeatStatus[agent.id] === 'testing'}
                            className={
                              heartbeatStatus[agent.id] === 'ok'
                                ? 'border-green-200 text-green-600 bg-green-50'
                                : heartbeatStatus[agent.id] === 'error'
                                ? 'border-red-200 text-red-600 bg-red-50'
                                : heartbeatStatus[agent.id] === 'warning'
                                ? 'border-yellow-200 text-yellow-600 bg-yellow-50'
                                : ''
                            }
                          >
                            {heartbeatStatus[agent.id] === 'testing' ? (
                              <>
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                测试中
                              </>
                            ) : heartbeatStatus[agent.id] === 'ok' ? (
                              <>
                                <CheckCircle2 className="w-3 h-3 mr-1" />
                                连通
                              </>
                            ) : heartbeatStatus[agent.id] === 'warning' ? (
                              <>
                                <AlertTriangle className="w-3 h-3 mr-1" />
                                告警
                              </>
                            ) : heartbeatStatus[agent.id] === 'error' ? (
                              <>
                                <AlertCircle className="w-3 h-3 mr-1" />
                                失败
                              </>
                            ) : (
                              <>
                                <Play className="w-3 h-3 mr-1" />
                                心跳
                              </>
                            )}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteAgent(agent.id, agent.name)}
                            disabled={deletingId !== null}
                            className="border-red-200 text-destructive hover:bg-destructive/10"
                          >
                            {deletingId === agent.id ? '...' : '删除'}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-3 border-t">
                <div className="text-sm text-muted-foreground">
                  显示第 {(currentPage - 1) * ITEMS_PER_PAGE + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, agents.length)} 项，共 {agents.length} 项
                </div>
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                />
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail Modal */}
      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          onClose={() => setSelectedAgent(null)}
          onRefresh={fetchData}
        />
      )}

      {/* Register Modal — 平台选择式注册 */}
      <AgentPlatformRegister
        open={showRegister}
        onClose={() => setShowRegister(false)}
        onSuccess={async () => { await fetchData() }}
      />
      <ConfirmDialog />
    </div>
  )
}
