import React, { useState, useEffect, useMemo } from 'react'
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
import { request } from '../../shared/utils/api'
import { industryTagsApi, IndustryTag } from '../../shared/utils/industryTagsApi'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/shared/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/components/ui/popover'
import { Badge } from '@/shared/components/ui/badge'
import { Check, ChevronDown, Trash2, Plus } from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'
export type TaskConditionType = 'none' | 'auto_eval' | 'human_decision' | 'human_input'

export interface ScenarioProjectRef {
  id: string
  name: string
}

export interface ScenarioTaskRef {
  id: string
  name: string
  project_id: string
}

export interface ScenarioTaskFormData {
  title: string
  description: string
  project_id: string
  priority: TaskPriority
  capability_tags: string[]
  depends_on: string[]
  condition_type: TaskConditionType
  condition_data: Record<string, any> | null
}

export interface ScenarioTaskDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  scenarioId: string
  onSubmit?: (isEdit: boolean, data: ScenarioTaskFormData) => Promise<void>
  initialData?: ScenarioTaskFormData & { id: string }
  projects: ScenarioProjectRef[]
  tasks: ScenarioTaskRef[]
}

// ============================================================================
// Constants
// ============================================================================

const PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'critical', label: '紧急' },
]

// ============================================================================
// Capability Tags Combobox (Multi-select)
// ============================================================================

function CapabilityTagsCombobox({
  selected,
  onChange,
  tags,
}: {
  selected: string[]
  onChange: (ids: string[]) => void
  tags: IndustryTag[]
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!search.trim()) return tags
    const q = search.toLowerCase()
    return tags.filter(t =>
      t.tag_name.toLowerCase().includes(q) ||
      t.industry.toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q)
    )
  }, [tags, search])

  const selectedLabels = useMemo(() => {
    return tags.filter(t => selected.includes(t.id)).map(t => t.tag_name)
  }, [tags, selected])

  const toggle = (tagId: string) => {
    if (selected.includes(tagId)) {
      onChange(selected.filter(id => id !== tagId))
    } else {
      onChange([...selected, tagId])
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          className="w-full justify-between h-auto min-h-[42px] py-1.5 px-3 text-sm overflow-hidden"
        >
          {selected.length === 0 ? (
            <span className="text-muted-foreground">选择能力标签...</span>
          ) : (
            <div className="flex flex-wrap gap-1">
              {selectedLabels.slice(0, 3).map((name, i) => (
                <Badge key={i} variant="secondary" className="text-xs px-1.5 py-0">{name}</Badge>
              ))}
              {selectedLabels.length > 3 && (
                <Badge variant="secondary" className="text-xs px-1.5 py-0">+{selectedLabels.length - 3}</Badge>
              )}
            </div>
          )}
          <ChevronDown className="ml-1 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[480px] p-0" align="start">
        <Command>
          <CommandInput placeholder="搜索能力标签..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>未找到匹配的能力标签</CommandEmpty>
            <CommandGroup>
              {filtered.map(tag => (
                <CommandItem
                  key={tag.id}
                  value={tag.id}
                  onSelect={() => toggle(tag.id)}
                  className="cursor-pointer"
                >
                  <Check
                    className={`mr-2 h-4 w-4 ${selected.includes(tag.id) ? 'opacity-100' : 'opacity-0'}`}
                  />
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm">{tag.tag_name}</span>
                    <span className="text-xs text-muted-foreground">{tag.industry} · {tag.dimension}</span>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
        {selected.length > 0 && (
          <div className="border-t p-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs w-full"
              onClick={() => onChange([])}
            >
              清除全部
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

// ============================================================================
// Condition Type Options
// ============================================================================

const TASK_CONDITION_OPTIONS: { value: TaskConditionType; label: string }[] = [
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

function TaskConditionEditor({
  conditionType,
  value,
  onChange,
}: {
  conditionType: TaskConditionType
  value: Record<string, any> | null
  onChange: (v: Record<string, any> | null) => void
}) {
  if (conditionType === 'none') {
    return <p className="text-xs text-muted-foreground italic py-2">选择条件类型后可配置详细条件</p>
  }

  if (conditionType === 'auto_eval') {
    return (
      <div className="space-y-2 mt-2 bg-muted/30 rounded-lg p-3">
        <label className="text-xs font-medium text-muted-foreground">评估表达式</label>
        <Input
          value={value?.expr ?? ''}
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

    return (
      <div className="space-y-3 mt-2 bg-muted/30 rounded-lg p-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">决策问题</label>
          <Input value={prompt} onChange={(e) => onChange({ ...value, prompt: e.target.value })} placeholder="需要人类决策的问题" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">选项</label>
          {options.map((opt, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <Input value={opt} onChange={(e) => updateOptions(idx, e.target.value)} placeholder={`选项 ${idx + 1}`} className="flex-1 text-sm" />
              {options.length > 1 && (
                <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive" onClick={() => {
                  const newOpts = options.filter((_, i) => i !== idx)
                  const newBranches = { ...branches }
                  delete newBranches[options[idx]]
                  onChange({ ...value, options: newOpts, branches: newBranches })
                }}><Trash2 className="h-3.5 w-3.5" /></Button>
              )}
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => onChange({ ...value, options: [...options, ''] })} className="text-xs h-7">
            <Plus className="h-3 w-3 mr-1" /> 添加选项
          </Button>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">默认选项</label>
          <Select value={defaultOpt} onValueChange={(v) => onChange({ ...value, default: v })}>
            <SelectTrigger className="h-8"><SelectValue placeholder="选择默认选项" /></SelectTrigger>
            <SelectContent>
              {options.filter(Boolean).map((opt) => (
                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">超时时间（分钟）</label>
          <Input type="number" min={1} value={timeout} onChange={(e) => onChange({ ...value, timeout_minutes: parseInt(e.target.value) || 30 })} className="h-8" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">分支动作</label>
          {options.filter(Boolean).map((opt) => (
            <div key={opt} className="flex gap-2 items-center">
              <span className="text-sm min-w-[80px] truncate">{opt}</span>
              <Select value={branches[opt] || 'continue'} onValueChange={(v) => onChange({ ...value, branches: { ...branches, [opt]: v } })}>
                <SelectTrigger className="h-8 flex-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {BRANCH_ACTION_OPTIONS.map((a) => (
                    <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
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
          <Input value={prompt} onChange={(e) => onChange({ ...value, prompt: e.target.value })} placeholder="请提供所需信息" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium">输入类型</label>
            <Select value={inputType} onValueChange={(v) => onChange({ ...value, input_type: v })}>
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
            <Input type="number" min={1} value={timeout} onChange={(e) => onChange({ ...value, timeout_minutes: parseInt(e.target.value) || 15 })} className="h-8" />
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">超时动作</label>
          <Select value={timeoutAction} onValueChange={(v) => onChange({ ...value, timeout_action: v })}>
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
          <Input value={defaultValue} onChange={(e) => onChange({ ...value, default_value: e.target.value })} placeholder="超时时的默认值" className="h-8" />
        </div>
      </div>
    )
  }

  return null
}

export default function ScenarioTaskDialog({
  open,
  onOpenChange,
  scenarioId,
  onSubmit,
  initialData,
  projects,
  tasks,
}: ScenarioTaskDialogProps) {
  const isEdit = !!initialData

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [projectId, setProjectId] = useState('')
  const [priority, setPriority] = useState<TaskPriority>('medium')
  const [capabilityTags, setCapabilityTags] = useState<string[]>([])
  const [dependsOn, setDependsOn] = useState<string[]>([])
  const [allTags, setAllTags] = useState<IndustryTag[]>([])
  const [submitting, setSubmitting] = useState(false)

  // Load capability tags once
  useEffect(() => {
    if (open && allTags.length === 0) {
      industryTagsApi.list({ page_size: 100 }).then(res => {
        setAllTags(res.items || [])
      }).catch(() => {})
    }
  }, [open])

  // Reset / populate form when dialog opens
  useEffect(() => {
    if (open) {
      if (initialData) {
        setTitle(initialData.title)
        setDescription(initialData.description)
        setProjectId(initialData.project_id)
        setPriority(initialData.priority)
        setCapabilityTags(initialData.capability_tags || [])
        setDependsOn(initialData.depends_on)
      } else {
        setTitle('')
        setDescription('')
        setProjectId('')
        setPriority('medium')
        setCapabilityTags([])
        setDependsOn([])
      }
    }
  }, [open, initialData])

  // Filter dependencies to current project tasks only
  const projectTasks = useMemo(() => {
    if (!projectId) return []
    return tasks.filter(t => t.project_id === projectId && t.id !== initialData?.id)
  }, [tasks, projectId, initialData?.id])

  const toggleDependsOn = (taskId: string) => {
    setDependsOn(prev =>
      prev.includes(taskId) ? prev.filter(id => id !== taskId) : [...prev, taskId]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    if (!projectId) {
      alert('请选择所属工程')
      return
    }

    const formData: ScenarioTaskFormData = {
      title: title.trim(),
      description: description.trim(),
      project_id: projectId,
      priority,
      capability_tags: capabilityTags,
      depends_on: dependsOn,
      condition_type: 'none',
      condition_data: null,
    }

    if (onSubmit) {
      await onSubmit(isEdit, formData)
      return
    }

    setSubmitting(true)
    try {
      const body: Record<string, any> = {
        name: formData.title,
        description: formData.description,
        project_id: formData.project_id,
        priority: formData.priority,
        required_capabilities: formData.capability_tags,
        dependencies: formData.depends_on,
        condition_type: 'none',
        condition_data: null,
      }
      if (isEdit && initialData) {
        await request(
          SCENARIOS.UPDATE_TASK(scenarioId, initialData.id),
          { method: 'PUT', body: JSON.stringify(body) },
        )
      } else {
        await request(
          SCENARIOS.ADD_TASK(scenarioId),
          { method: 'POST', body: JSON.stringify(body) },
        )
      }
      onOpenChange(false)
    } catch (err: any) {
      alert((isEdit ? '更新失败: ' : '创建失败: ') + (err.message || '未知错误'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑任务' : '新建任务'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改场景任务模板信息' : '为场景蓝图添加一个新的任务模板'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Title */}
          <div>
            <label className="text-sm font-medium">标题 *</label>
            <Input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="任务标题"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium">描述</label>
            <Textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="任务描述..."
              rows={2}
            />
          </div>

          {/* Project & Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">所属工程 *</label>
              <Select value={projectId} onValueChange={setProjectId}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="-- 选择工程 --" /></SelectTrigger>
                <SelectContent>
                  {projects.map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">优先级</label>
              <Select value={priority} onValueChange={v => setPriority(v as TaskPriority)}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PRIORITY_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Capability Tags - full width */}
          <div>
            <label className="text-sm font-medium">能力需求标签</label>
            <p className="text-xs text-muted-foreground mb-1.5">选择该任务需要的能力标签</p>
            <CapabilityTagsCombobox
              selected={capabilityTags}
              onChange={setCapabilityTags}
              tags={allTags}
            />
          </div>

          {/* Dependencies */}
          <div>
            <label className="text-sm font-medium mb-1.5 block">
              依赖任务（同一工程下的其他任务）
            </label>
            {!projectId ? (
              <p className="text-xs text-muted-foreground p-2 border rounded-md">
                请先选择所属工程
              </p>
            ) : projectTasks.length === 0 ? (
              <p className="text-xs text-muted-foreground p-2 border rounded-md">
                该工程下暂无其他任务可选
              </p>
            ) : (
              <>
                <div className="border rounded-md p-2 max-h-40 overflow-y-auto space-y-1">
                  {projectTasks.map(t => (
                    <label
                      key={t.id}
                      className="flex items-center gap-2 text-sm p-1 hover:bg-muted/50 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={dependsOn.includes(t.id)}
                        onChange={() => toggleDependsOn(t.id)}
                        className="rounded border-gray-300"
                      />
                      <span className="truncate text-xs">{t.name || t.id}</span>
                    </label>
                  ))}
                </div>
                {dependsOn.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    已选择 {dependsOn.length} 个依赖
                  </p>
                )}
              </>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
              取消
            </Button>
            <Button type="submit" disabled={submitting || !title.trim() || !projectId}>
              {isEdit ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
