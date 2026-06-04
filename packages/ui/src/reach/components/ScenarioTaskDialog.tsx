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

// ============================================================================
// Types
// ============================================================================

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

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
  name: string
  description: string
  project_id: string
  phase_name: string
  agent_type: string
  priority: TaskPriority
  estimated_hours: number
  dependencies: string[]
}

export interface ScenarioTaskDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  scenarioId: string
  /**
   * Submit handler. Receives (isEdit, formData).
   * If not provided, the component calls the API directly.
   */
  onSubmit?: (isEdit: boolean, data: ScenarioTaskFormData) => Promise<void>
  /** When provided, dialog is in edit mode */
  initialData?: ScenarioTaskFormData & { id: string }
  /** Available projects for the dropdown */
  projects: ScenarioProjectRef[]
  /** Available tasks for dependency selection */
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
// Component
// ============================================================================

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

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [projectId, setProjectId] = useState('')
  const [phaseName, setPhaseName] = useState('')
  const [agentType, setAgentType] = useState('')
  const [priority, setPriority] = useState<TaskPriority>('medium')
  const [estimatedHours, setEstimatedHours] = useState(0)
  const [dependencies, setDependencies] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  // Reset / populate form when dialog opens
  useEffect(() => {
    if (open) {
      if (initialData) {
        setName(initialData.name)
        setDescription(initialData.description)
        setProjectId(initialData.project_id)
        setPhaseName(initialData.phase_name)
        setAgentType(initialData.agent_type)
        setPriority(initialData.priority)
        setEstimatedHours(initialData.estimated_hours)
        setDependencies(initialData.dependencies)
      } else {
        setName('')
        setDescription('')
        setProjectId('')
        setPhaseName('')
        setAgentType('')
        setPriority('medium')
        setEstimatedHours(0)
        setDependencies([])
      }
    }
  }, [open, initialData])

  // When project changes, auto-set phase_name from selected project and filter dependencies
  const handleProjectChange = (newProjectId: string) => {
    setProjectId(newProjectId)
    // Auto-fill phase_name from project name
    const selectedProject = projects.find(p => p.id === newProjectId)
    setPhaseName(selectedProject?.name || '')
    // Clear dependencies that don't belong to the selected project
    if (newProjectId) {
      const projTaskIds = new Set(
        tasks.filter(t => t.project_id === newProjectId).map(t => t.id)
      )
      setDependencies(prev => prev.filter(id => projTaskIds.has(id)))
    } else {
      setDependencies([])
    }
  }

  // Tasks belonging to the currently selected project (for dependency selection)
  const projectTasks = useMemo(() => {
    if (!projectId) return []
    return tasks.filter(t => t.project_id === projectId && t.id !== initialData?.id)
  }, [tasks, projectId, initialData?.id])

  // Project name lookup for dependency display
  const projectMap = useMemo(() => {
    const map = new Map<string, string>()
    projects.forEach(p => map.set(p.id, p.name))
    return map
  }, [projects])

  const toggleDependency = (taskId: string) => {
    setDependencies(prev =>
      prev.includes(taskId) ? prev.filter(id => id !== taskId) : [...prev, taskId]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    if (!projectId) {
      alert('请选择所属项目')
      return
    }

    const formData: ScenarioTaskFormData = {
      name: name.trim(),
      description: description.trim(),
      project_id: projectId,
      phase_name: phaseName.trim(),
      agent_type: agentType.trim(),
      priority,
      estimated_hours: estimatedHours,
      dependencies,
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
          SCENARIOS.UPDATE_TASK(scenarioId, initialData.id),
          {
            method: 'PUT',
            body: JSON.stringify(formData),
          },
        )
      } else {
        await request(
          SCENARIOS.ADD_TASK(scenarioId),
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
          <DialogTitle>{isEdit ? '编辑 Task' : '新建 Task'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改场景任务模板信息' : '为场景蓝图添加一个新的任务模板'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-sm font-medium">名称 *</label>
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="任务名称"
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

          {/* Project & Phase */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">所属 Project *</label>
              <Select value={projectId} onValueChange={handleProjectChange}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="-- 选择项目 --" /></SelectTrigger>
                <SelectContent>
                  {projects.map(p => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">阶段名称</label>
              <Input
                value={phaseName}
                onChange={e => setPhaseName(e.target.value)}
                placeholder="所属阶段名"
                className="mt-1"
              />
            </div>
          </div>

          {/* Agent Type & Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">执行 Agent 类型</label>
              <Input
                value={agentType}
                onChange={e => setAgentType(e.target.value)}
                placeholder="例如: command, rescue"
                className="mt-1"
              />
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

          {/* Estimated Hours */}
          <div>
            <label className="text-sm font-medium">预估工时（小时）</label>
            <Input
              type="number"
              min={0}
              step={0.5}
              value={estimatedHours}
              onChange={e => setEstimatedHours(parseFloat(e.target.value) || 0)}
              className="mt-1"
            />
          </div>

          {/* Dependencies */}
          <div>
            <label className="text-sm font-medium mb-1 block">
              依赖任务（同项目下的其他任务）
            </label>
            {!projectId ? (
              <p className="text-xs text-muted-foreground p-2 border rounded-md">
                请先选择所属项目
              </p>
            ) : projectTasks.length === 0 ? (
              <p className="text-xs text-muted-foreground p-2 border rounded-md">
                该项目下暂无其他任务可选
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
                        checked={dependencies.includes(t.id)}
                        onChange={() => toggleDependency(t.id)}
                        className="rounded border-gray-300"
                      />
                      <span className="truncate text-xs">{t.name || t.id}</span>
                    </label>
                  ))}
                </div>
                {dependencies.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    已选择 {dependencies.length} 个依赖
                  </p>
                )}
              </>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
              取消
            </Button>
            <Button type="submit" disabled={submitting || !name.trim() || !projectId}>
              {isEdit ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
