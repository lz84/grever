/**
 * AgentPlatformRegister - 智能体平台注册弹窗
 * 支持 7 种平台：OpenClaw / Dify / Coze / Claude Code / Codex / GitHub Copilot / Hermes
 * 动态根据平台 schema 渲染注册表单字段
 */

import { useState, useEffect } from 'react'
import { AlertCircle, Loader2, Bot, Plug, Cpu, Globe } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { agentsApi, AgentPlatformInfo, AgentPlatformSchema, Agent } from '@/shared/utils/api'

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: (agent: Agent) => void
}

// 平台图标映射
const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  openclaw: <Bot className="w-8 h-8 text-blue-500" />,
  dify: <Plug className="w-8 h-8 text-emerald-500" />,
  coze: <Cpu className="w-8 h-8 text-purple-500" />,
  claude_code: <Cpu className="w-8 h-8 text-orange-500" />,
  codex: <Cpu className="w-8 h-8 text-green-500" />,
  github_copilot: <Globe className="w-8 h-8 text-gray-600" />,
  hermes: <Bot className="w-8 h-8 text-cyan-500" />,
}

const PLATFORM_DESCRIPTIONS: Record<string, string> = {
  openclaw: 'OpenClaw 本地 AI Agent，通过 CLI 会话派发任务',
  dify: 'Dify SaaS 平台，通过 HTTP API 调用',
  coze: 'Coze 平台，通过 Bot API 调用',
  claude_code: 'Anthropic Claude Code，本地 CLI 调用',
  codex: 'OpenAI Codex，本地 CLI 调用',
  github_copilot: 'GitHub Copilot，本地 CLI 调用',
  hermes: 'Hermes Agent，通过 WebSocket 连接',
}

export default function AgentPlatformRegister({ open, onClose, onSuccess }: Props) {
  const [step, setStep] = useState<'select' | 'form'>('select')
  const [platforms, setPlatforms] = useState<AgentPlatformInfo[]>([])
  const [selectedPlatform, setSelectedPlatform] = useState<AgentPlatformInfo | null>(null)
  const [schema, setSchema] = useState<AgentPlatformSchema | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)
  const [basicInfo, setBasicInfo] = useState({ name: '', agent_id: '' })
  const [formValues, setFormValues] = useState<Record<string, string | boolean>>({})

  // 选择平台并加载 schema
  const selectPlatform = async (platform: AgentPlatformInfo) => {
    setSelectedPlatform(platform)
    setSchemaLoading(true)
    setError(null)
    try {
      const schema = await agentsApi.getPlatformSchema(platform.type)
      setSchema(schema)
      // 填充默认值
      const defaults: Record<string, string | boolean> = {}
      for (const f of schema.fields) {
        if (f.default !== undefined) defaults[f.key] = f.default
      }
      setFormValues(defaults)
      setStep('form')
    } catch (err) {
      setError('加载平台配置失败：' + String(err))
    } finally {
      setSchemaLoading(false)
    }
  }

  // 提交注册
  const handleSubmit = async () => {
    if (!selectedPlatform || !schema) return
    if (!basicInfo.name.trim()) {
      setError('请填写智能体名称')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const platformConfig: Record<string, any> = {}
      for (const field of schema.fields) {
        if (formValues[field.key] !== undefined && formValues[field.key] !== '') {
          platformConfig[field.key] = formValues[field.key]
        }
      }

      const data = {
        name: basicInfo.name.trim(),
        agent_id: basicInfo.agent_id.trim() || `agent-${Date.now()}`,
        capabilities: [],
        capability_tags: { business: [], professional: [], technical: [], management: [] },
        platform_type: selectedPlatform.type,
        platform_config: platformConfig,
      }

      const agent = await agentsApi.register(data)
      onSuccess(agent)
      handleClose()
    } catch (err) {
      setError('注册失败：' + String(err))
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setStep('select')
    setSelectedPlatform(null)
    setSchema(null)
    setFormValues({})
    setBasicInfo({ name: '', agent_id: '' })
    setError(null)
    onClose()
  }

  // 加载平台列表
  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    // 兜底超时：5 秒不返回视为失败，不能让流程卡住
    const timeout = setTimeout(() => {
      setError('加载超时，请检查后端服务是否正常')
      setLoading(false)
    }, 5000)

    agentsApi.listPlatforms()
      .then(data => {
        clearTimeout(timeout)
        if (!data || data.length === 0) {
          setError('平台列表为空，请检查后端适配器注册状态')
          setLoading(false)
          return
        }
        setPlatforms(data)
        setLoading(false)
      })
      .catch(err => {
        clearTimeout(timeout)
        setError('加载平台列表失败：' + String(err))
        setLoading(false)
      })

    return () => clearTimeout(timeout)
  }, [open])

  const retryLoadPlatforms = () => {
    setError(null)
    setLoading(true)
    agentsApi.listPlatforms().then(data => {
      if (!data || data.length === 0) {
        setError('平台列表为空，请检查后端适配器注册状态')
        setLoading(false)
        return
      }
      setPlatforms(data)
      setLoading(false)
    }).catch(err => {
      setError('加载平台列表失败：' + String(err))
      setLoading(false)
    })
  }

  // 对话框标题
  const dialogTitle = step === 'select' ? '注册智能体' : `注册 ${selectedPlatform?.label || ''}`
  const dialogDesc = step === 'select' ? '选择平台类型，然后填写配置' : '填写平台配置信息'

  return (
    <Dialog open={open} onOpenChange={open => !open && handleClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogDescription>{dialogDesc}</DialogDescription>
        </DialogHeader>

        {/* 可滚动内容区 */}
        <div className="overflow-y-auto pr-1" style={{ maxHeight: 'calc(90vh - 12rem)' }}>
          {/*
            兜底原则（用户指令）：
          关键业务路径上不能兜底，错了必须断掉流程。
          三种情况必须显式报错，不走任何默认行为：
          1. error 非空 → 只显示错误+重试，不显示其他任何内容
          2. loading → 只显示加载中，不显示其他任何内容
        */}
        {error ? (
          /* 错误状态：显式阻断，不兜底 */
          <div className="flex flex-col items-center justify-center py-12 text-center gap-4">
            <AlertCircle className="w-12 h-12 text-destructive" />
            <p className="text-sm text-muted-foreground max-w-sm">{error}</p>
            <div className="flex gap-3">
              <button
                onClick={retryLoadPlatforms}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium rounded-md"
              >
                重试
              </button>
              <button onClick={handleClose} className="px-4 py-2 text-muted-foreground hover:text-foreground text-sm">
                关闭
              </button>
            </div>
          </div>
        ) : loading ? (
          /* 加载状态 */
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground mb-3" />
            <span className="text-sm text-muted-foreground">加载平台列表...</span>
          </div>
        ) : step === 'select' ? (
          /* Step 1：平台选择 */
          <div className="grid grid-cols-2 gap-3">
            {platforms
              .filter(p => p.available)
              .map(p => (
                <button
                  key={p.type}
                  onClick={() => selectPlatform(p)}
                  className="group flex items-start gap-3 p-4 border rounded-lg text-left hover:border-primary transition-all"
                >
                  <div className="shrink-0 mt-0.5">
                    {PLATFORM_ICONS[p.type] || <Bot className="w-8 h-8 text-muted-foreground" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{p.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                      {PLATFORM_DESCRIPTIONS[p.type] || `注册 ${p.label} 智能体`}
                    </div>
                    {p.is_session_based && (
                      <div className="mt-1.5">
                        <span className="text-xs px-1.5 py-0.5 bg-muted rounded text-muted-foreground">按会话实例化</span>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            {platforms.filter(p => p.available).length === 0 && (
              <div className="col-span-2 text-center py-8 text-muted-foreground text-sm">
                暂无可用平台，请检查后端适配器注册状态
              </div>
            )}
          </div>
        ) : (
          /* Step 2：表单填写 */
          <div className="space-y-4">
            {/* 返回按钮 */}
            <button
              onClick={() => setStep('select')}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              ← 重新选择平台
            </button>

            {/* 平台信息 */}
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
              <div className="shrink-0">
                {PLATFORM_ICONS[selectedPlatform!.type] || <Bot className="w-6 h-6 text-muted-foreground" />}
              </div>
              <div>
                <div className="font-medium text-sm">{schema!.platform_label}</div>
                <div className="text-xs text-muted-foreground">{PLATFORM_DESCRIPTIONS[selectedPlatform!.type]}</div>
              </div>
            </div>

            {/* 基础信息 */}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  智能体名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={basicInfo.name}
                  onChange={e => setBasicInfo(b => ({ ...b, name: e.target.value }))}
                  placeholder="例如：Claude Code 开发环境"
                  className="w-full px-3 py-2 border rounded-md text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  智能体 ID <span className="text-xs text-muted-foreground ml-1">（留空自动生成）</span>
                </label>
                <input
                  type="text"
                  value={basicInfo.agent_id}
                  onChange={e => setBasicInfo(b => ({ ...b, agent_id: e.target.value }))}
                  placeholder="agent-xxx（UUID）"
                  className="w-full px-3 py-2 border rounded-md text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>

            {/* 平台特有配置 */}
            {schemaLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm font-medium border-b pb-1.5">平台配置</div>
                {schema!.fields.map(field => (
                  <FieldInput
                    key={field.key}
                    field={field}
                    value={formValues[field.key]}
                    onChange={val => setFormValues(v => ({ ...v, [field.key]: val }))}
                  />
                ))}
              </div>
            )}

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
          </div>
        )}
        </div>

        <DialogFooter>
          {step === 'form' && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading || !basicInfo.name.trim()}
                className="flex items-center gap-2 px-5 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 text-sm font-medium rounded-md transition-colors"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? '注册中...' : '注册'}
              </button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// 单个表单字段组件
function FieldInput({
  field,
  value,
  onChange,
}: {
  field: { key: string; label: string; type: string; required: boolean; placeholder?: string; description?: string; options?: string[]; default?: any }
  value: string | boolean | undefined
  onChange: (val: string | boolean) => void
}) {
  const type = field.type

  if (type === 'checkbox') {
    return (
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id={`field-${field.key}`}
          checked={Boolean(value)}
          onChange={e => onChange(e.target.checked)}
          className="w-4 h-4 rounded border-ring text-primary focus:ring-ring"
        />
        <div>
          <label htmlFor={`field-${field.key}`} className="text-sm font-medium cursor-pointer">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </label>
          {field.description && (
            <p className="text-xs text-muted-foreground mt-0.5">{field.description}</p>
          )}
        </div>
      </div>
    )
  }

  if (type === 'select') {
    return (
      <div>
        <label className="block text-sm font-medium mb-1.5">
          {field.label}
          {field.required && <span className="text-red-500 ml-1">*</span>}
        </label>
        <select
          value={String(value || field.default || '')}
          onChange={e => onChange(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">请选择{field.label}</option>
          {field.options?.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
        {field.description && (
          <p className="text-xs text-muted-foreground mt-1">{field.description}</p>
        )}
      </div>
    )
  }

  // text / string / password / url
  return (
    <div>
      <label className="block text-sm font-medium mb-1.5">
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <input
        type={type === 'password' ? 'password' : 'text'}
        value={String(value || '')}
        onChange={e => onChange(e.target.value)}
        placeholder={field.placeholder || `输入 ${field.label}`}
        className="w-full px-3 py-2 border rounded-md text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
      />
      {field.description && (
        <p className="text-xs text-muted-foreground mt-1">{field.description}</p>
      )}
    </div>
  )
}
