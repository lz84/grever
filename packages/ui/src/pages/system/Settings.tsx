import { useState, useEffect, useCallback } from 'react'
import { Separator } from '@/shared/components/ui/separator'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { Badge } from '@/shared/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import { Textarea } from '@/shared/components/ui/textarea'
import { toast } from 'sonner'
import { ConfirmDialog, confirmAction } from "@/shared/utils/notify"
import {
  fetchAllSettings as fetchAllSettingsApi,
  batchUpdateSettings as batchUpdateSettingsApi,
  testOpenClawConnection,
  fetchAvailableModels,
  fetchOpenClawSessions,
  fetchAgents as fetchAgentsApi,
  updateAgent,
  registerAgent,
  deregisterAgent,
} from '@/shared/services/settingsApi'
import {
  Brain,
  Users,
  Link,
  Settings as SettingsIcon,
  Shield,
  Save,
  RotateCw,
  Plus,
  Trash2,
  Pencil,
  CheckCircle,
  XCircle,
  Loader2,
  TreePine,
  Globe,
  Key,
  Clock,
  ListChecks,
} from 'lucide-react'

// ============================================================
// Types
// ============================================================

interface ConfigValue {
  value: unknown
  type: string
  description?: string
  updated_at?: string
  updated_by?: string
}

interface SettingsData {
  root_agent?: Record<string, ConfigValue>
  openclaw?: Record<string, ConfigValue>
  system?: Record<string, ConfigValue>
  security?: Record<string, ConfigValue>
}

// ============================================================
// Panel 1: Root Agent (CEO) Config
// ============================================================

function RootAgentPanel({ data, onSave }: { data?: Record<string, ConfigValue>; onSave: () => void }) {
  const [model, setModel] = useState('')
  const [strategy, setStrategy] = useState('capability_match')
  const [heartbeat, setHeartbeat] = useState('300')
  const [timeout, setTimeoutMin] = useState('30')
  const [maxRetries, setMaxRetries] = useState('3')
  const [autoDispatch, setAutoDispatch] = useState(true)
  const [tickSec, setTickSec] = useState('30')
  const [models, setModels] = useState<{ id: string; name?: string }[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setModel(String(data.model?.value ?? 'minimax/MiniMax-M2.7-highspeed'))
    setStrategy(String(data.dispatch_strategy?.value ?? 'capability_match'))
    setHeartbeat(String(data.heartbeat_interval?.value ?? '300'))
    setTimeoutMin(String(data.task_timeout_min?.value ?? '30'))
    setMaxRetries(String(data.max_retries?.value ?? '3'))
    setAutoDispatch(data.auto_dispatch?.value === true)
    setTickSec(String(data.scheduler_tick_sec?.value ?? '30'))
  }, [data])

  useEffect(() => {
    fetchAvailableModels().then(r => setModels(r.models ?? [])).catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await batchUpdateSettingsApi('root_agent', {
        model: `"${model}"`,
        dispatch_strategy: `"${strategy}"`,
        heartbeat_interval: heartbeat,
        task_timeout_min: timeout,
        max_retries: maxRetries,
        auto_dispatch: String(autoDispatch),
        scheduler_tick_sec: tickSec,
      })
      toast.success('根智能体配置已保存')
      onSave()
    } catch (e: unknown) {
      toast.error(`保存失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="w-5 h-5" />
          根智能体（CEO）配置
        </CardTitle>
        <CardDescription>管理刚子（调度器）的行为配置</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>模型</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger><SelectValue placeholder="选择模型" /></SelectTrigger>
              <SelectContent>
                {models.map(m => (
                  <SelectItem key={m.id} value={m.id}>{m.name || m.id}</SelectItem>
                ))}
                {models.length === 0 && (
                  <SelectItem value="minimax/MiniMax-M2.7-highspeed">MiniMax M2.7 Highspeed</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>调度策略</Label>
            <Select value={strategy} onValueChange={setStrategy}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="capability_match">能力匹配</SelectItem>
                <SelectItem value="round_robin">轮询</SelectItem>
                <SelectItem value="least_load">最少负载</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>心跳间隔（秒）</Label>
            <Input type="number" value={heartbeat} onChange={e => setHeartbeat(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>任务超时（分钟）</Label>
            <Input type="number" value={timeout} onChange={e => setTimeoutMin(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>最大重试次数</Label>
            <Input type="number" value={maxRetries} onChange={e => setMaxRetries(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>调度器 Tick 间隔（秒）</Label>
            <Input type="number" value={tickSec} onChange={e => setTickSec(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>自动派发</Label>
            <div className="flex items-center gap-2 mt-2">
              <Switch checked={autoDispatch} onCheckedChange={setAutoDispatch} />
              <span className="text-sm text-slate-500">{autoDispatch ? '已开启' : '已关闭'}</span>
            </div>
          </div>
        </div>
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            保存配置
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Panel 2: Agent Config
// ============================================================

interface AgentInfo {
  id: string
  name: string
  model?: string
  capabilities?: string[]
  status?: string
  trigger_mode?: string
  poll_interval?: number
  max_load?: number
}

function AgentPanel() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [editAgent, setEditAgent] = useState<AgentInfo | null>(null)
  const [registerOpen, setRegisterOpen] = useState(false)
  const [newAgent, setNewAgent] = useState({ name: '', model: 'minimax/MiniMax-M2.7-highspeed', capabilities: '', trigger_mode: 'polling', poll_interval: 30, max_load: 5 })
  const [models, setModels] = useState<{ id: string; name?: string }[]>([])
  const [saving, setSaving] = useState(false)

  const CAPABILITY_OPTIONS = ['coding', 'testing', 'ui_migration', 'data_analysis', 'research', 'ops', 'security', 'nlp']

  const fetchAgents = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchAgentsApi()
      setAgents(data)
    } catch {
      // fallback empty
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAgents() }, [fetchAgents])
  useEffect(() => {
    fetchAvailableModels().then(r => setModels(r.models ?? [])).catch(() => {})
  }, [])

  const handleSaveAgent = async () => {
    if (!editAgent) return
    setSaving(true)
    try {
      const ok = await updateAgent(editAgent.id, {
        model_name: editAgent.model,
        capabilities: editAgent.capabilities,
        trigger_mode: editAgent.trigger_mode,
        poll_interval: editAgent.poll_interval,
        max_load: editAgent.max_load,
      })
      if (ok) {
        toast.success('Agent 配置已更新')
        setEditAgent(null)
        fetchAgents()
      } else {
        toast.error('更新失败')
      }
    } catch {
      toast.error('保存异常')
    } finally {
      setSaving(false)
    }
  }

  const handleRegister = async () => {
    setSaving(true)
    try {
      const ok = await registerAgent({
          agent_id: newAgent.name.toLowerCase().replace(/\s+/g, '_'),
          name: newAgent.name,
          model_name: newAgent.model,
          capabilities: newAgent.capabilities ? newAgent.capabilities.split(',').map(c => c.trim()).filter(Boolean) : [],
          trigger_mode: newAgent.trigger_mode,
          poll_interval: newAgent.poll_interval,
          max_load: newAgent.max_load,
        })
        if (ok) {
          toast.success('Agent 注册成功')
        setRegisterOpen(false)
        setNewAgent({ name: '', model: 'minimax/MiniMax-M2.7-highspeed', capabilities: '', trigger_mode: 'polling', poll_interval: 30, max_load: 5 })
        fetchAgents()
      } else {
        toast.error('注册失败')
      }
    } catch {
      toast.error('注册异常')
    } finally {
      setSaving(false)
    }
  }

  const handleDeregister = async (agentId: string) => {
    if (!(await confirmAction({ title: '注销 Agent', description: `确定要注销 Agent "${agentId}" 吗？`, variant: 'destructive' }))) return
    try {
      const ok = await deregisterAgent(agentId)
      if (ok) {
        toast.success('Agent 已注销')
        fetchAgents()
      } else {
        toast.error('注销失败')
      }
    } catch {
      toast.error('注销异常')
    }
  }

  const toggleCapability = (agent: AgentInfo, cap: string) => {
    const caps = agent.capabilities ?? []
    const newCaps = caps.includes(cap) ? caps.filter(c => c !== cap) : [...caps, cap]
    setEditAgent({ ...agent, capabilities: newCaps })
  }

  const statusColor = (status?: string) => {
    switch (status) {
      case 'online': return 'bg-green-500'
      case 'offline': return 'bg-red-500'
      default: return 'bg-slate-400'
    }
  }

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 animate-spin" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Users className="w-5 h-5" />
            Agent 管理
          </h3>
          <p className="text-sm text-slate-500">共 {agents.length} 个 Agent</p>
        </div>
        <Button onClick={() => setRegisterOpen(true)} size="sm">
          <Plus className="w-4 h-4 mr-1" /> 注册 Agent
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>名称</TableHead>
            <TableHead>模型</TableHead>
            <TableHead>能力标签</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>触发模式</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {agents.map(a => (
            <TableRow key={a.id}>
              <TableCell className="font-medium">{a.name}</TableCell>
              <TableCell className="text-xs">{a.model || '-'}</TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {(a.capabilities ?? []).map(c => (
                    <Badge key={c} variant="secondary" className="text-xs">{c}</Badge>
                  ))}
                  {(!a.capabilities || a.capabilities.length === 0) && <span className="text-slate-400 text-xs">无</span>}
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${statusColor(a.status)}`} />
                  <span className="text-xs">{a.status || 'unknown'}</span>
                </div>
              </TableCell>
              <TableCell className="text-xs">{a.trigger_mode || 'polling'}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => setEditAgent({ ...a })}>
                    <Pencil className="w-3 h-3" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-red-500" onClick={() => handleDeregister(a.id)}>
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
          {agents.length === 0 && (
            <TableRow><TableCell colSpan={6} className="text-center text-slate-400 py-8">暂无 Agent，点击上方"注册 Agent"添加</TableCell></TableRow>
          )}
        </TableBody>
      </Table>

      {/* Edit Dialog */}
      <Dialog open={!!editAgent} onOpenChange={() => setEditAgent(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>编辑 Agent</DialogTitle>
            <DialogDescription>{editAgent?.name}</DialogDescription>
          </DialogHeader>
          {editAgent && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>模型</Label>
                <Select value={editAgent.model || ''} onValueChange={v => setEditAgent({ ...editAgent, model: v })}>
                  <SelectTrigger><SelectValue placeholder="选择模型" /></SelectTrigger>
                  <SelectContent>
                    {models.map(m => (
                      <SelectItem key={m.id} value={m.id}>{m.name || m.id}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>能力标签</Label>
                <div className="flex flex-wrap gap-2">
                  {CAPABILITY_OPTIONS.map(cap => (
                    <Badge
                      key={cap}
                      variant={(editAgent.capabilities ?? []).includes(cap) ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => toggleCapability(editAgent, cap)}
                    >
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label>触发模式</Label>
                <Select value={editAgent.trigger_mode || 'polling'} onValueChange={v => setEditAgent({ ...editAgent, trigger_mode: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="polling">Polling（主动拉取）</SelectItem>
                    <SelectItem value="push">Push（被动接收）</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Poll 间隔（秒）</Label>
                  <Input type="number" value={editAgent.poll_interval || 30} onChange={e => setEditAgent({ ...editAgent, poll_interval: Number(e.target.value) })} />
                </div>
                <div className="space-y-2">
                  <Label>最大负载</Label>
                  <Input type="number" value={editAgent.max_load || 5} onChange={e => setEditAgent({ ...editAgent, max_load: Number(e.target.value) })} />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditAgent(null)}>取消</Button>
            <Button onClick={handleSaveAgent} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Register Dialog */}
      <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>注册新 Agent</DialogTitle>
            <DialogDescription>填写 Agent 基本信息并注册到系统</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Agent 名称</Label>
              <Input value={newAgent.name} onChange={e => setNewAgent({ ...newAgent, name: e.target.value })} placeholder="例如: 小助手" />
            </div>
            <div className="space-y-2">
              <Label>模型</Label>
              <Select value={newAgent.model} onValueChange={v => setNewAgent({ ...newAgent, model: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {models.map(m => (
                    <SelectItem key={m.id} value={m.id}>{m.name || m.id}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>能力标签（逗号分隔）</Label>
              <Input value={newAgent.capabilities} onChange={e => setNewAgent({ ...newAgent, capabilities: e.target.value })} placeholder="coding, testing, ui_migration" />
            </div>
            <div className="space-y-2">
              <Label>触发模式</Label>
              <Select value={newAgent.trigger_mode} onValueChange={v => setNewAgent({ ...newAgent, trigger_mode: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="polling">Polling（主动拉取）</SelectItem>
                  <SelectItem value="push">Push（被动接收）</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRegisterOpen(false)}>取消</Button>
            <Button onClick={handleRegister} disabled={saving || !newAgent.name}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
              注册
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ============================================================
// Panel 3: OpenClaw Integration
// ============================================================

function OpenClawPanel({ data, onSave }: { data?: Record<string, ConfigValue>; onSave: () => void }) {
  const [gatewayUrl, setGatewayUrl] = useState('http://127.0.0.1:8080')
  const [apiToken, setApiToken] = useState('')
  const [sessionMapping, setSessionMapping] = useState('goal_per_session')
  const [reconnectTimeout, setReconnectTimeout] = useState('60')
  const [connStatus, setConnStatus] = useState<'idle' | 'testing' | 'connected' | 'failed'>('idle')
  const [connMessage, setConnMessage] = useState('')
  const [connTime, setConnTime] = useState<number | undefined>()
  const [sessions, setSessions] = useState<unknown[]>([])
  const [showSessions, setShowSessions] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setGatewayUrl(String(data.gateway_url?.value ?? 'http://127.0.0.1:8080'))
    setApiToken(String(data.api_token?.value ?? ''))
    setSessionMapping(String(data.session_mapping?.value ?? 'goal_per_session'))
    setReconnectTimeout(String(data.reconnect_timeout_sec?.value ?? '60'))
  }, [data])

  const handleTest = async () => {
    setConnStatus('testing')
    setConnMessage('')
    try {
      const result = await testOpenClawConnection()
      setConnStatus(result.status === 'connected' ? 'connected' : 'failed')
      setConnMessage(result.message)
      setConnTime(result.response_time_ms)
    } catch (e: unknown) {
      setConnStatus('failed')
      setConnMessage(e instanceof Error ? e.message : '测试失败')
    }
  }

  const handleLoadSessions = async () => {
    try {
      const r = await fetchOpenClawSessions()
      setSessions(r.sessions ?? [])
      setShowSessions(true)
    } catch {
      toast.error('获取 Session 列表失败')
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await batchUpdateSettingsApi('openclaw', {
        gateway_url: `"${gatewayUrl}"`,
        api_token: `"${apiToken}"`,
        session_mapping: `"${sessionMapping}"`,
        reconnect_timeout_sec: reconnectTimeout,
      })
      toast.success('OpenClaw 配置已保存')
      onSave()
    } catch (e: unknown) {
      toast.error(`保存失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link className="w-5 h-5" />
            OpenClaw 集成配置
          </CardTitle>
          <CardDescription>管理 Nexus 与 OpenClaw 的连接参数</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border">
            {connStatus === 'idle' && <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-slate-400" /><span className="text-sm text-slate-500">未测试</span></div>}
            {connStatus === 'testing' && <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin text-blue-500" /><span className="text-sm text-blue-500">测试中...</span></div>}
            {connStatus === 'connected' && <div className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" /><span className="text-sm text-green-600">已连接 {connTime ? `(${connTime}ms)` : ''}</span></div>}
            {connStatus === 'failed' && <div className="flex items-center gap-2"><XCircle className="w-4 h-4 text-red-500" /><span className="text-sm text-red-600">{connMessage || '连接失败'}</span></div>}
            <Button variant="outline" size="sm" onClick={handleTest} disabled={connStatus === 'testing'} className="ml-auto">
              测试连接
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Gateway URL</Label>
              <Input value={gatewayUrl} onChange={e => setGatewayUrl(e.target.value)} placeholder="http://127.0.0.1:8080" />
            </div>
            <div className="space-y-2">
              <Label>API Token</Label>
              <Input type="password" value={apiToken} onChange={e => setApiToken(e.target.value)} placeholder="留空表示未设置" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Session 映射策略</Label>
              <Select value={sessionMapping} onValueChange={setSessionMapping}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="goal_per_session">Goal per Session（每个 Goal 一个 Session）</SelectItem>
                  <SelectItem value="shared">Shared Session（共享 Session）</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>超时重连（秒）</Label>
              <Input type="number" value={reconnectTimeout} onChange={e => setReconnectTimeout(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-between">
            <Button variant="outline" onClick={handleLoadSessions}>
              <ListChecks className="w-4 h-4 mr-2" /> 加载 Session 列表
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
              保存配置
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Session Map Visualization */}
      {showSessions && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TreePine className="w-5 h-5" />
              Session 映射
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sessions.length > 0 ? (
              <div className="space-y-2">
                {sessions.map((s: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm p-2 rounded bg-slate-50">
                    <Globe className="w-4 h-4 text-blue-500" />
                    <span className="font-mono">{s.id || s.name || `session-${i}`}</span>
                    {s.status && <Badge variant="outline" className="text-xs">{s.status}</Badge>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">当前无活跃 Session</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ============================================================
// Panel 4: System Parameters
// ============================================================

function SystemPanel({ data, onSave }: { data?: Record<string, ConfigValue>; onSave: () => void }) {
  const [logLevel, setLogLevel] = useState('INFO')
  const [retentionDays, setRetentionDays] = useState('30')
  const [autoCleanup, setAutoCleanup] = useState(true)
  const [offlineThreshold, setOfflineThreshold] = useState('5')
  const [recoverThreshold, setRecoverThreshold] = useState('15')
  const [taskPriority, setTaskPriority] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setLogLevel(String(data.log_level?.value ?? 'INFO'))
    setRetentionDays(String(data.data_retention_days?.value ?? '30'))
    setAutoCleanup(data.auto_cleanup_zombie?.value === true)
    setOfflineThreshold(String(data.offline_threshold_min?.value ?? '5'))
    setRecoverThreshold(String(data.task_recover_threshold_min?.value ?? '15'))
    setTaskPriority(data.task_priority?.value === true)
  }, [data])

  const handleSave = async () => {
    setSaving(true)
    try {
      await batchUpdateSettingsApi('system', {
        log_level: `"${logLevel}"`,
        data_retention_days: retentionDays,
        auto_cleanup_zombie: String(autoCleanup),
        offline_threshold_min: offlineThreshold,
        task_recover_threshold_min: recoverThreshold,
        task_priority: String(taskPriority),
      })
      toast.success('系统参数已保存')
      onSave()
    } catch (e: unknown) {
      toast.error(`保存失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <SettingsIcon className="w-5 h-5" />
          系统参数
        </CardTitle>
        <CardDescription>Nexus 自身运行参数配置</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label>数据库路径（只读）</Label>
          <Input value="D:\work\research\agents-nexus\data\reins.db" disabled className="bg-slate-50" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>日志级别</Label>
            <Select value={logLevel} onValueChange={setLogLevel}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="DEBUG">DEBUG</SelectItem>
                <SelectItem value="INFO">INFO</SelectItem>
                <SelectItem value="WARNING">WARNING</SelectItem>
                <SelectItem value="ERROR">ERROR</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>数据保留天数</Label>
            <Input type="number" value={retentionDays} onChange={e => setRetentionDays(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>离线阈值（分钟）</Label>
            <Input type="number" value={offlineThreshold} onChange={e => setOfflineThreshold(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>任务回收阈值（分钟）</Label>
            <Input type="number" value={recoverThreshold} onChange={e => setRecoverThreshold(e.target.value)} />
          </div>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>自动清理僵尸任务</Label>
              <p className="text-xs text-slate-400">启动时自动清理超时任务</p>
            </div>
            <Switch checked={autoCleanup} onCheckedChange={setAutoCleanup} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label>任务调度优先级</Label>
              <p className="text-xs text-slate-400">启用基于优先级的任务调度</p>
            </div>
            <Switch checked={taskPriority} onCheckedChange={setTaskPriority} />
          </div>
        </div>
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            保存配置
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ============================================================
// Panel 5: Security Settings
// ============================================================

function SecurityPanel({ data }: { data?: Record<string, ConfigValue> }) {
  const [apiAuth, setApiAuth] = useState(false)
  const [corsOrigins, setCorsOrigins] = useState('http://localhost:5173')
  const [tokens, setTokens] = useState<{ id: string; name: string; created: string }[]>([
    { id: 'tkn-001', name: 'Nexus Frontend', created: '2026-05-01' },
  ])
  const [auditLogs] = useState([
    { time: '2026-05-08 20:00', action: '更新配置', user: 'admin', detail: '修改 log_level' },
    { time: '2026-05-08 19:30', action: '注册 Agent', user: 'admin', detail: '注册 kouzi' },
  ])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!data) return
    setApiAuth(data.api_auth_enabled?.value === true)
    const cors = data.cors_origins?.value
    if (Array.isArray(cors)) setCorsOrigins(cors.join(', '))
    else if (typeof cors === 'string') setCorsOrigins(cors.replace(/[\[\]"]/g, ''))
  }, [data])

  const handleSave = async () => {
    setSaving(true)
    try {
      const origins = corsOrigins.split(',').map(s => s.trim()).filter(Boolean)
      await batchUpdateSettingsApi('security', {
        api_auth_enabled: String(apiAuth),
        cors_origins: JSON.stringify(origins),
      })
      toast.success('安全配置已保存')
    } catch (e: unknown) {
      toast.error(`保存失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            安全设置
          </CardTitle>
          <CardDescription>权限管理和访问控制</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Label>API Token 认证</Label>
              <p className="text-xs text-slate-400">启用后所有 API 请求需携带 Token</p>
            </div>
            <Switch checked={apiAuth} onCheckedChange={setApiAuth} />
          </div>
          <div className="space-y-2">
            <Label>CORS 允许来源</Label>
            <Textarea value={corsOrigins} onChange={e => setCorsOrigins(e.target.value)} placeholder="逗号分隔" rows={2} />
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
              <Key className="w-4 h-4" />
              API Tokens
            </h4>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tokens.map(t => (
                  <TableRow key={t.id}>
                    <TableCell className="font-mono text-xs">{t.id}</TableCell>
                    <TableCell>{t.name}</TableCell>
                    <TableCell className="text-xs">{t.created}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="text-red-500">
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              审计日志
            </h4>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>详情</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.map((log, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-xs">{log.time}</TableCell>
                    <TableCell>{log.action}</TableCell>
                    <TableCell>{log.user}</TableCell>
                    <TableCell className="text-xs">{log.detail}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
              保存配置
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ============================================================
// Main Settings Page
// ============================================================

type PanelKey = 'root_agent' | 'agents' | 'openclaw' | 'system' | 'security'

const panels: { key: PanelKey; label: string; icon: React.ReactNode }[] = [
  { key: 'root_agent', label: '根智能体', icon: <Brain className="w-4 h-4" /> },
  { key: 'agents', label: 'Agent 配置', icon: <Users className="w-4 h-4" /> },
  { key: 'openclaw', label: 'OpenClaw 集成', icon: <Link className="w-4 h-4" /> },
  { key: 'system', label: '系统参数', icon: <SettingsIcon className="w-4 h-4" /> },
  { key: 'security', label: '安全设置', icon: <Shield className="w-4 h-4" /> },
]

export default function Settings() {
  const [activePanel, setActivePanel] = useState<PanelKey>('root_agent')
  const [settings, setSettings] = useState<SettingsData>({})
  const [loading, setLoading] = useState(true)

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchAllSettingsApi()
      setSettings(data)
    } catch (e: unknown) {
      toast.error(`加载配置失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadSettings() }, [loadSettings])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="flex gap-6 min-h-[calc(100vh-8rem)]">
      {/* Left sidebar */}
      <div className="w-52 flex-shrink-0">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">系统设置</CardTitle>
          </CardHeader>
          <CardContent className="p-2">
            <nav className="space-y-1">
              {panels.map(p => (
                <button
                  key={p.key}
                  onClick={() => setActivePanel(p.key)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                    activePanel === p.key
                      ? 'bg-blue-50 text-blue-600 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {p.icon}
                  {p.label}
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>
        <div className="mt-4 text-center">
          <Button variant="ghost" size="sm" onClick={loadSettings} className="text-slate-400">
            <RotateCw className="w-4 h-4 mr-1" /> 刷新
          </Button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1">
        {activePanel === 'root_agent' && <RootAgentPanel data={settings.root_agent} onSave={loadSettings} />}
        {activePanel === 'agents' && <AgentPanel />}
        {activePanel === 'openclaw' && <OpenClawPanel data={settings.openclaw} onSave={loadSettings} />}
        {activePanel === 'system' && <SystemPanel data={settings.system} onSave={loadSettings} />}
        {activePanel === 'security' && <SecurityPanel data={settings.security} />}
      </div>
      <ConfirmDialog />
    </div>
  )
}
