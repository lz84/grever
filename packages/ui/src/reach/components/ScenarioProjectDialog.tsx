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
        setOrderIndex(0)
        setCapabilityTagsInput('')
      }
    }
  }, [open, initialData])

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
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑 Project' : '新建 Project'}</DialogTitle>
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
              <Select value={conditionType} onValueChange={v => setConditionType(v as ConditionType)}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CONDITION_TYPE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

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
