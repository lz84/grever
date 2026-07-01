import React, { useState, useEffect } from 'react'
import { SCENARIOS } from '../../shared/api/paths'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import { Button } from '@/shared/components/ui/button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select'
import { Separator } from '@/shared/components/ui/separator'
import { Plus, Trash2 } from 'lucide-react'
import { request } from '../../shared/utils/api'

// ============================================================================
// Types
// ============================================================================

export type ProjectType = 'mandatory' | 'optional' | 'conditional'
export type ConditionType = 'none' | 'auto_eval' | 'human_decision' | 'human_input'

export interface ScenarioProjectFormData {
  name: string
  description: string
  project_type: ProjectType
  condition_type: ConditionType
  condition_data: Record<string, any> | null
  order_index: number
  capability_tags: string[]
}

export interface ScenarioProjectDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  scenarioId: string
  /**
   * Submit handler. Receives (isEdit, formData).
   * The component itself can also do the API call if `onSubmit` is not provided.
   */
  onSubmit?: (isEdit: boolean, data: ScenarioProjectFormData) => Promise<void>
  /** When provided, dialog is in edit mode and shows "编辑" title */
  initialData?: ScenarioProjectFormData & { id: string }
}

// ============================================================================
// Constants
// ============================================================================

const PROJECT_TYPE_OPTIONS: { value: ProjectType; label: string }[] = [
  { value: 'mandatory', label: '必须 (Mandatory)' },
  { value: 'optional', label: '可选 (Optional)' },
  { value: 'conditional', label: '条件 (Conditional)' },
]

const CONDITION_TYPE_OPTIONS: { value: ConditionType; label: string }[] = [
  { value: 'none', label: '无条件' },
  { value: 'auto_eval', label: '自动评估' },
  { value: 'human_decision', label: '人工决策' },
  { value: 'human_input', label: '人工输入' },
]

const INPUT_TYPE_OPTIONS = [
  { value: 'text', label: '文本' },
  { value: 'number', label: '数字' },
  { value: 'multiline', label: '多行文本' },
]

const TIMEOUT_ACTION_OPTIONS = [
  { value: 'use_default', label: '使用默认值' },
  { value: 'abort', label: '中止' },
  { value: 'retry', label: '重试' },
  { value: 'escalate', label: '上报' },
]

const BRANCH_ACTION_OPTIONS = [
  { value: 'continue', label: '继续' },
  { value: 'skip', label: '跳过' },
  { value: 'retry', label: '重试' },
  { value: 'abort', label: '中止' },
  { value: 'escalate', label: '上报' },
]

// ============================================================================
// Condition Data Editor
// ============================================================================

function ConditionDataEditor({
  conditionType,
  value,
  onChange,
}: {
  conditionType: ConditionType
  value: Record<string, any> | null
  onChange: (v: Record<string, any> | null) => void
}) {
  if (conditionType === 'none') {
    return <p className="text-xs text-muted-foreground italic py-2">选择条件类型后可配置详细条件</p>
  }

  if (conditionType === 'auto_eval') {
    const expr = value?.expr ?? ''
    return (
      <div className="space-y-2 mt-2 bg-muted/30 rounded-lg p-3">
        <label className="text-xs font-medium text-muted-foreground">评估表达式</label>
        <Input
          value={expr}
          onChange={(e) => onChange({ expr: e.target.value })}
          placeholder="例如: risk_level > 3"
          className="font-mono text-sm"
        />
      </div>
    )
  }

  if (conditionType === 'human_decision') {
    const prompt = value?.prompt ?? ''
    const options: string[] = value?.options ?? ['']
    const defaultOpt = value?.default ?? ''
    const timeout = value?.timeout_minutes ?? 30
    const branches: Record<string, string> = value?.branches ?? {}

    const updateOptions = (idx: number, val: string) => {
      const newOpts = [...options]
      newOpts[idx] = val
      const cleanedBranches: Record<string, string> = {}
      newOpts.filter(Boolean).forEach((o) => {
        cleanedBranches[o] = branches[o] ?? 'continue'
      })
      onChange({ ...value, options: newOpts, branches: cleanedBranches })
    }

    const addOption = () => {
      onChange({ ...value, options: [...options, ''] })
    }

    const removeOption = (idx: number) => {
      if (options.length <= 1) return
      const newOpts = options.filter((_, i) => i !== idx)
      const newBranches = { ...branches }
      delete newBranches[options[idx]]
      onChange({ ...value, options: newOpts, branches: newBranches })
    }

    return (
      <div className="space-y-3 mt-2 bg-muted/30 rounded-lg p-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">决策问题</label>
          <Input
            value={prompt}
            onChange={(e) => onChange({ ...value, prompt: e.target.value })}
            placeholder="需要人类决策的问题"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">选项（每行一个）</label>
          {options.map((opt, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <Input
                value={opt}
                onChange={(e) => updateOptions(idx, e.target.value)}
                placeholder={`选项 ${idx + 1}`}
                className="flex-1 text-sm"
              />
              {options.length > 1 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                  onClick={() => removeOption(idx)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addOption} className="text-xs h-7">
            <Plus className="h-3 w-3 mr-1" /> 添加选项
          </Button>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">默认选项</label>
          <Select
            value={defaultOpt}
            onValueChange={(v) => onChange({ ...value, default: v })}
          >
            <SelectTrigger className="h-8">
              <SelectValue placeholder="选择默认选项" />
            </SelectTrigger>
            <SelectContent>
              {options.filter(Boolean).map((opt) => (
                <SelectItem key={opt} value={opt}>
                  {opt}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">超时时间（分钟）</label>
          <Input
            type="number"
            min={1}
            value={timeout}
            onChange={(e) => onChange({ ...value, timeout_minutes: parseInt(e.target.value) || 30 })}
            className="h-8"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">分支动作</label>
          {options.filter(Boolean).map((opt) => (
            <div key={opt} className="flex gap-2 items-center">
              <span className="text-sm min-w-[80px] truncate">{opt}</span>
              <Select
                value={branches[opt] || 'continue'}
                onValueChange={(v) => {
                  onChange({ ...value, branches: { ...branches, [opt]: v } })
                }}
              >
                <SelectTrigger className="h-8 flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BRANCH_ACTION_OPTIONS.map((a) => (
                    <SelectItem key={a.value} value={a.value}>
                      {a.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (conditionType === 'human_input') {
    const prompt = value?.prompt ?? ''
    const inputType = value?.input_type ?? 'text'
    const timeout = value?.timeout_minutes ?? 15
    const timeoutAction = value?.timeout_action ?? 'use_default'
    const defaultValue = value?.default_value ?? ''

    return (
      <div className="space-y-3 mt-2 bg-muted/30 rounded-lg p-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">输入提示</label>
          <Input
            value={prompt}
            onChange={(e) => onChange({ ...value, prompt: e.target.value })}
            placeholder="请提供所需信息"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium">输入类型</label>
            <Select
              value={inputType}
              onValueChange={(v) => onChange({ ...value, input_type: v })}
            >
              <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
              <SelectContent>
                {INPUT_TYPE_OPTIONS.map((t) => (
                  <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium">超时时间（分钟）</label>
            <Input
              type="number"
              min={1}
              value={timeout}
              onChange={(e) => onChange({ ...value, timeout_minutes: parseInt(e.target.value) || 15 })}
              className="h-8"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">超时动作</label>
          <Select
            value={timeoutAction}
            onValueChange={(v) => onChange({ ...value, timeout_action: v })}
          >
            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
            <SelectContent>
              {TIMEOUT_ACTION_OPTIONS.map((a) => (
                <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">默认值</label>
          <Input
            value={defaultValue}
            onChange={(e) => onChange({ ...value, default_value: e.target.value })}
            placeholder="超时时的默认值"
            className="h-8"
          />
        </div>
      </div>
    )
  }

  return null
}

// ============================================================================
// Component
// ============================================================================

export default function ScenarioProjectDialog({
  open,
  onOpenChange,
  scenarioId,
  onSubmit,
  initialData,
}: ScenarioProjectDialogProps) {
  const isEdit = !!initialData

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [projectType, setProjectType] = useState<ProjectType>('mandatory')
  const [conditionType, setConditionType] = useState<ConditionType>('none')
  const [conditionData, setConditionData] = useState<Record<string, any> | null>(null)
  const [orderIndex, setOrderIndex] = useState(0)
  const [capabilityTagsInput, setCapabilityTagsInput] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Reset / populate form when dialog opens
  useEffect(() => {
    if (open) {
      if (initialData) {
        setName(initialData.name)
        setDescription(initialData.description)
        setProjectType(initialData.project_type)
        setConditionType(initialData.condition_type)
        setConditionData(initialData.condition_data ?? null)
        setOrderIndex(initialData.order_index)
        setCapabilityTagsInput(
          Array.isArray(initialData.capability_tags)
            ? initialData.capability_tags.join(', ')
            : '',
        )
      } else {
        setName('')
        setDescription('')
        setProjectType('mandatory')
        setConditionType('none')
        setConditionData(null)
        setOrderIndex(0)
        setCapabilityTagsInput('')
      }
    }
  }, [open, initialData])

  const handleConditionTypeChange = (v: string) => {
    const ct = v as ConditionType
    setConditionType(ct)
    setConditionData(ct === 'none' ? null : {})
  }

  const parseCapabilityTags = (): string[] => {
    return capabilityTagsInput
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    const formData: ScenarioProjectFormData = {
      name: name.trim(),
      description: description.trim(),
      project_type: projectType,
      condition_type: conditionType,
      condition_data: conditionData,
      order_index: orderIndex,
      capability_tags: parseCapabilityTags(),
    }

    // If external onSubmit is provided, delegate to it
    if (onSubmit) {
      await onSubmit(isEdit, formData)
      return
    }

    // Default: call the API directly
    setSubmitting(true)
    try {
      if (isEdit && initialData) {
        await request(
          SCENARIOS.UPDATE_PROJECT(scenarioId, initialData.id),
          {
            method: 'PUT',
            body: JSON.stringify(formData),
          },
        )
      } else {
        await request(
          SCENARIOS.ADD_PROJECT(scenarioId),
          {
            method: 'POST',
            body: JSON.stringify(formData),
          },
        )
      }
      onOpenChange(false)
    } catch (err: any) {
      alert(isEdit ? '更新失败: ' + (err.message || '未知错误') : '创建失败: ' + (err.message || '未知错误'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑工程' : '新建工程'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改场景阶段/项目信息' : '为场景蓝图添加一个新的阶段/项目'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-sm font-medium">名称 *</label>
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="项目名称，如：应急响应"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium">描述</label>
            <Textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="项目描述..."
              rows={3}
            />
          </div>

          {/* Project Type & Condition Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">项目类型</label>
              <Select value={projectType} onValueChange={v => setProjectType(v as ProjectType)}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PROJECT_TYPE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">条件类型</label>
              <Select value={conditionType} onValueChange={handleConditionTypeChange}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CONDITION_TYPE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Condition Data Editor */}
          <ConditionDataEditor
            conditionType={conditionType}
            value={conditionData}
            onChange={setConditionData}
          />

          {/* Order Index */}
          <div>
            <label className="text-sm font-medium">排序序号</label>
            <Input
              type="number"
              min={0}
              value={orderIndex}
              onChange={e => setOrderIndex(parseInt(e.target.value) || 0)}
              className="mt-1"
            />
          </div>

          {/* Capability Tags */}
          <div>
            <label className="text-sm font-medium">能力标签（逗号分隔）</label>
            <Input
              value={capabilityTagsInput}
              onChange={e => setCapabilityTagsInput(e.target.value)}
              placeholder="例如: 搜索, 救援, 医疗"
              className="mt-1"
            />
          </div>

          <Separator />

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
              取消
            </Button>
            <Button type="submit" disabled={submitting || !name.trim()}>
              {isEdit ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
