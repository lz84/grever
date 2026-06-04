import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { scenariosApi, type ConditionType, type ScenarioCreateRequest } from "@/shared/utils/scenariosApi"
import { Button } from "@/shared/components/ui/button"
import { Input } from "@/shared/components/ui/input"
import { Label } from "@/shared/components/ui/label"
import { Textarea } from "@/shared/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/shared/components/ui/dialog"
import { Separator } from "@/shared/components/ui/separator"
import { Plus, Trash2, ChevronDown, ChevronUp, Settings } from "lucide-react"
import HITLConfigDialog from '@/shared/components/HITLConfigDialog'

// ==================== 类型定义 ====================

const CONDITION_TYPES: ConditionType[] = ["none", "auto_eval", "human_decision", "human_input"]
const CATEGORIES = ["earthquake", "fire", "chemical", "flood", "software", "general"]
const AGENT_TYPES = ["coordinator", "analyst", "executor", "observer", "verifier", "any"]
const INPUT_TYPES = ["text", "number", "multiline"]
const TIMEOUT_ACTIONS = ["use_default", "abort", "retry", "escalate"]
const BRANCH_ACTIONS = ["continue", "skip", "retry", "abort", "escalate"]

interface TaskData {
  id: string
  name: string
  description: string
  agent_type: string
  required_capabilities: string
  dependencies: string[]
  condition_type: ConditionType
  condition_data: Record<string, any> | null
  executor_type?: string
}

interface StepData {
  id: string
  name: string
  agent_type: string
  required_capabilities: string
  condition_type: ConditionType
  condition_data: Record<string, any> | null
  tasks: TaskData[]
  collapsed: boolean
}

function genId() {
  return Math.random().toString(36).slice(2, 10)
}

function makeDefaultConditionData(type: ConditionType): Record<string, any> | null {
  if (type === "none") return null
  if (type === "auto_eval") return { expr: "" }
  if (type === "human_decision") return {
    prompt: "",
    options: [""],
    default: "",
    timeout_minutes: 30,
    branches: {} as Record<string, string>,
  }
  if (type === "human_input") return {
    prompt: "",
    input_type: "text",
    timeout_minutes: 15,
    timeout_action: "use_default",
    default_value: "",
  }
  return null
}

function makeEmptyTask(): TaskData {
  return {
    id: genId(),
    name: "",
    description: "",
    agent_type: "any",
    required_capabilities: "",
    dependencies: [],
    condition_type: "none",
    condition_data: null,
    executor_type: "ai",
  }
}

function makeEmptyStep(): StepData {
  return {
    id: genId(),
    name: "",
    agent_type: "any",
    required_capabilities: "",
    condition_type: "none",
    condition_data: null,
    tasks: [],
    collapsed: false,
  }
}

// ==================== Condition Data Editor ====================

function ConditionDataEditor({
  conditionType,
  value,
  onChange,
}: {
  conditionType: ConditionType
  value: Record<string, any> | null
  onChange: (v: Record<string, any> | null) => void
}) {
  if (conditionType === "none") {
    return <p className="text-sm text-muted-foreground italic">无条件</p>
  }

  if (conditionType === "auto_eval") {
    const expr = value?.expr ?? ""
    return (
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">评估表达式</Label>
        <Input
          value={expr}
          onChange={(e) => onChange({ expr: e.target.value })}
          placeholder="例如: risk_level > 3"
          className="font-mono text-sm"
        />
      </div>
    )
  }

  if (conditionType === "human_decision") {
    const prompt = value?.prompt ?? ""
    const options: string[] = value?.options ?? [""]
    const defaultOpt = value?.default ?? ""
    const timeout = value?.timeout_minutes ?? 30
    const branches: Record<string, string> = value?.branches ?? {}

    const updateOptions = (idx: number, val: string) => {
      const newOpts = [...options]
      newOpts[idx] = val
      const newBranches = { ...branches }
      // rebuild branches
      const filteredOpts = newOpts.filter(Boolean)
      // keep existing branch values for matching options
      const cleanedBranches: Record<string, string> = {}
      filteredOpts.forEach((o) => {
        cleanedBranches[o] = newBranches[o] || "continue"
      })
      onChange({ ...value, options: newOpts, branches: cleanedBranches })
    }

    const addOption = () => {
      const newOpts = [...options, ""]
      onChange({ ...value, options: newOpts })
    }

    const removeOption = (idx: number) => {
      if (options.length <= 1) return
      const newOpts = options.filter((_, i) => i !== idx)
      const newBranches = { ...branches }
      delete newBranches[options[idx]]
      onChange({ ...value, options: newOpts, branches: newBranches })
    }

    return (
      <div className="space-y-3 bg-muted/30 rounded-lg p-3">
        <div className="space-y-1">
          <Label className="text-xs">决策问题</Label>
          <Input
            value={prompt}
            onChange={(e) => onChange({ ...value, prompt: e.target.value })}
            placeholder="需要人类决策的问题"
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">选项（每行一个）</Label>
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
          <Label className="text-xs">默认选项</Label>
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
          <Label className="text-xs">超时时间（分钟）</Label>
          <Input
            type="number"
            value={timeout}
            onChange={(e) =>
              onChange({ ...value, timeout_minutes: parseInt(e.target.value) || 30 })
            }
            className="h-8"
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">分支动作</Label>
          {options.filter(Boolean).map((opt) => (
            <div key={opt} className="flex gap-2 items-center">
              <span className="text-sm min-w-[80px] truncate">{opt}</span>
              <Select
                value={branches[opt] || "continue"}
                onValueChange={(v) => {
                  const newBranches = { ...branches, [opt]: v }
                  onChange({ ...value, branches: newBranches })
                }}
              >
                <SelectTrigger className="h-8 flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BRANCH_ACTIONS.map((a) => (
                    <SelectItem key={a} value={a}>
                      {a}
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

  if (conditionType === "human_input") {
    const prompt = value?.prompt ?? ""
    const inputType = value?.input_type ?? "text"
    const timeout = value?.timeout_minutes ?? 15
    const timeoutAction = value?.timeout_action ?? "use_default"
    const defaultValue = value?.default_value ?? ""

    return (
      <div className="space-y-3 bg-muted/30 rounded-lg p-3">
        <div className="space-y-1">
          <Label className="text-xs">输入提示</Label>
          <Input
            value={prompt}
            onChange={(e) => onChange({ ...value, prompt: e.target.value })}
            placeholder="请提供所需信息"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label className="text-xs">输入类型</Label>
            <Select
              value={inputType}
              onValueChange={(v) => onChange({ ...value, input_type: v })}
            >
              <SelectTrigger className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {INPUT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">超时时间（分钟）</Label>
            <Input
              type="number"
              value={timeout}
              onChange={(e) =>
                onChange({ ...value, timeout_minutes: parseInt(e.target.value) || 15 })
              }
              className="h-8"
            />
          </div>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">超时动作</Label>
          <Select
            value={timeoutAction}
            onValueChange={(v) => onChange({ ...value, timeout_action: v })}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEOUT_ACTIONS.map((a) => (
                <SelectItem key={a} value={a}>
                  {a}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">默认值</Label>
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

// ==================== Task Editor ====================

function TaskEditor({
  task,
  taskIndex,
  allTaskNames,
  onChange,
  onRemove,
}: {
  task: TaskData
  taskIndex: number
  allTaskNames: string[]
  onChange: (t: TaskData) => void
  onRemove: () => void
}) {
  const toggleDep = (depName: string) => {
    const deps = task.dependencies.includes(depName)
      ? task.dependencies.filter((d) => d !== depName)
      : [...task.dependencies, depName]
    onChange({ ...task, dependencies: deps })
  }

  // HITL config dialog state
  const [hltlDialogOpen, setHITLDialogOpen] = useState(false)

  // Check if executor_type requires HITL config
  const needsHITLConfig = ['ai_approval', 'ai_data', 'ai_confirm'].includes(task.executor_type || 'ai')

  // Parse condition_data from JSON string if it exists
  const condition_data = task.condition_data || {}

  const handleHITLSave = (config: any) => {
    onChange({
      ...task,
      executor_type: task.executor_type,
      condition_data: {
        input_type: config.input_type || (task.executor_type === 'ai_approval' ? 'approval' : task.executor_type === 'ai_data' ? 'data_entry' : 'confirmation'),
        ...config,
      },
    })
  }

  return (
    <div className="border rounded-lg p-3 space-y-3 bg-card">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">
          任务 #{taskIndex + 1}
        </span>
        <div className="flex items-center gap-2">
          {/* HITL Config Button */}
          {needsHITLConfig && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => setHITLDialogOpen(true)}
            >
              <Settings className="w-3 h-3 mr-1" /> HITL配置
            </Button>
          )}
          {/* Delete Button */}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
            onClick={onRemove}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">任务名称 *</Label>
          <Input
            value={task.name}
            onChange={(e) => onChange({ ...task, name: e.target.value })}
            placeholder="任务名称"
            className="h-8"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">执行者类型</Label>
          <Select
            value={task.agent_type}
            onValueChange={(v) => onChange({ ...task, agent_type: v })}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AGENT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">执行模式</Label>
          <Select
            value={task.executor_type || "ai"}
            onValueChange={(v) => onChange({ ...task, executor_type: v })}
          >
            <SelectTrigger className="h-8">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ai">AI</SelectItem>
              <SelectItem value="human">纯人</SelectItem>
              <SelectItem value="ai_approval">审批</SelectItem>
              <SelectItem value="ai_data">数据</SelectItem>
              <SelectItem value="ai_confirm">确认</SelectItem>
              <SelectItem value="auto_eval">自动</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1">
        <Label className="text-xs">任务描述</Label>
        <Textarea
          value={task.description}
          onChange={(e) => onChange({ ...task, description: e.target.value })}
          placeholder="任务详细描述..."
          rows={2}
          className="text-sm"
        />
      </div>

      <div className="space-y-1">
        <Label className="text-xs">所需能力（逗号分隔）</Label>
        <Input
          value={task.required_capabilities}
          onChange={(e) => onChange({ ...task, required_capabilities: e.target.value })}
          placeholder="data_analysis,report_generation"
          className="h-8 text-sm"
        />
      </div>

      <div className="space-y-1">
        <Label className="text-xs">依赖任务</Label>
        {allTaskNames.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">同 step 内暂无其他任务</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {allTaskNames.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => toggleDep(n)}
                className={`px-2 py-0.5 rounded-full text-xs border transition-colors ${
                  task.dependencies.includes(n)
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:border-primary"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        )}
      </div>

      <Separator />

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Label className="text-xs">条件类型</Label>
          <span className="text-[10px] text-muted-foreground">
            — 配置此任务的前置条件
          </span>
        </div>
        <Select
          value={task.condition_type}
          onValueChange={(v) =>
            onChange({
              ...task,
              condition_type: v as ConditionType,
              condition_data: makeDefaultConditionData(v as ConditionType),
            })
          }
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CONDITION_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <ConditionDataEditor
          conditionType={task.condition_type}
          value={task.condition_data}
          onChange={(v) => onChange({ ...task, condition_data: v })}
        />
      </div>

      {/* HITL Config Dialog */}
      {needsHITLConfig && (
        <HITLConfigDialog
          open={hltlDialogOpen}
          onOpenChange={setHITLDialogOpen}
          executorType={task.executor_type || 'ai'}
          initialData={condition_data}
          onSave={handleHITLSave}
        />
      )}
    </div>
  )
}

// ==================== Step Editor ====================

function StepEditor({
  step,
  stepIndex,
  onStepChange,
  onRemove,
}: {
  step: StepData
  stepIndex: number
  onStepChange: (s: StepData) => void
  onRemove: () => void
}) {
  const toggleCollapse = () => {
    onStepChange({ ...step, collapsed: !step.collapsed })
  }

  const addTask = () => {
    const newTask = makeEmptyTask()
    onStepChange({ ...step, tasks: [...step.tasks, newTask] })
  }

  const removeTask = (taskId: string) => {
    const filtered = step.tasks.filter((t) => t.id !== taskId)
    // Also remove references from other tasks' dependencies
    const taskName = step.tasks.find((t) => t.id === taskId)?.name
    const cleaned = filtered.map((t) => ({
      ...t,
      dependencies: taskName ? t.dependencies.filter((d) => d !== taskName) : t.dependencies,
    }))
    onStepChange({ ...step, tasks: cleaned })
  }

  const updateTask = (taskId: string, updated: TaskData) => {
    const newTasks = step.tasks.map((t) => (t.id === taskId ? updated : t))
    onStepChange({ ...step, tasks: newTasks })
  }

  // For dependency selection: show names of other tasks in the same step
  const otherTaskNames = step.tasks
    .map((t) => t.name)
    .filter(Boolean)

  return (
    <div className="border-2 rounded-lg overflow-hidden">
      {/* Step header */}
      <div
        className="flex items-center justify-between p-3 bg-muted/50 cursor-pointer hover:bg-muted/70 transition-colors"
        onClick={toggleCollapse}
      >
        <div className="flex items-center gap-2">
          {step.collapsed ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="font-semibold text-sm">
            步骤 {stepIndex + 1}
            {step.name && `: ${step.name}`}
          </span>
          <span className="text-xs text-muted-foreground">
            ({step.tasks.length} 个任务)
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
          onClick={(e) => {
            e.stopPropagation()
            onRemove()
          }}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Step body */}
      {!step.collapsed && (
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">步骤名称 *</Label>
              <Input
                value={step.name}
                onChange={(e) => onStepChange({ ...step, name: e.target.value })}
                placeholder="步骤名称"
                className="h-8"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">执行者类型</Label>
              <Select
                value={step.agent_type}
                onValueChange={(v) => onStepChange({ ...step, agent_type: v })}
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AGENT_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">所需能力（逗号分隔）</Label>
            <Input
              value={step.required_capabilities}
              onChange={(e) =>
                onStepChange({ ...step, required_capabilities: e.target.value })
              }
              placeholder="data_analysis,coordination"
              className="h-8 text-sm"
            />
          </div>

          <Separator />

          <div className="space-y-2">
            <Label className="text-xs">条件类型</Label>
            <Select
              value={step.condition_type}
              onValueChange={(v) =>
                onStepChange({
                  ...step,
                  condition_type: v as ConditionType,
                  condition_data: makeDefaultConditionData(v as ConditionType),
                })
              }
            >
              <SelectTrigger className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CONDITION_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ConditionDataEditor
              conditionType={step.condition_type}
              value={step.condition_data}
              onChange={(v) => onStepChange({ ...step, condition_data: v })}
            />
          </div>

          <Separator />

          {/* Tasks section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-sm font-medium">任务列表</Label>
              <Button variant="outline" size="sm" onClick={addTask} className="h-7 text-xs">
                <Plus className="h-3 w-3 mr-1" /> 添加任务
              </Button>
            </div>

            {step.tasks.length === 0 ? (
              <div className="text-center py-6 border-2 border-dashed rounded-lg">
                <p className="text-sm text-muted-foreground">
                  暂无任务，点击上方按钮添加
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {step.tasks.map((task, tIdx) => {
                  // For deps: show other task names (excluding current task's own name if set)
                  const depNames = otherTaskNames.filter(
                    (n) => n !== task.name || true // allow self-ref in the list, but toggle logic prevents self-dep
                  )
                  return (
                    <TaskEditor
                      key={task.id}
                      task={task}
                      taskIndex={tIdx}
                      allTaskNames={depNames}
                      onChange={(updated) => updateTask(task.id, updated)}
                      onRemove={() => removeTask(task.id)}
                    />
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== Main Form ====================

export function ScenarioCreate() {
  const navigate = useNavigate()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [createdScenarioId, setCreatedScenarioId] = useState("")

  // Basic info
  const [name, setName] = useState("")
  const [category, setCategory] = useState("general")
  const [description, setDescription] = useState("")
  const [scenarioDesc, setScenarioDesc] = useState("")
  const [triggers, setTriggers] = useState("")
  const [executorType, setExecutorType] = useState<string>("ai")

  // Steps
  const [steps, setSteps] = useState<StepData[]>([])

  const addStep = () => {
    setSteps((prev) => [...prev, makeEmptyStep()])
  }

  const removeStep = (stepId: string) => {
    setSteps((prev) => prev.filter((s) => s.id !== stepId))
  }

  const updateStep = (stepId: string, updated: StepData) => {
    setSteps((prev) => prev.map((s) => (s.id === stepId ? updated : s)))
  }

  // Validation
  const validate = (): string | null => {
    if (!name.trim()) return "请输入场景名称"
    if (!category) return "请选择分类"
    for (let i = 0; i < steps.length; i++) {
      if (!steps[i].name.trim()) return `步骤 ${i + 1} 需要填写名称`
    }
    return null
  }

  // Build payload
  const buildPayload = (): ScenarioCreateRequest => {
    const triggerList = triggers
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)

    const phases = steps.map((step) => ({
      phase_name: step.name.trim(),
      phase_description: "",
      tasks: step.tasks.map((task) => ({
        name: task.name.trim(),
        description: task.description.trim(),
        agent_type: task.agent_type,
        required_capabilities: task.required_capabilities
          ? task.required_capabilities
              .split(",")
              .map((c) => c.trim())
              .filter(Boolean)
          : [],
        dependencies: task.dependencies,
        priority: "medium",
        estimated_hours: 1,
        condition_type: task.condition_type,
        condition_data: task.condition_data,
        executor_type: task.executor_type,
      })),
      depends_on_phases: [],
    }))

    // Collect all task templates (flat list across all steps)
    const taskTemplates = steps.flatMap((step) =>
      step.tasks.map((task) => ({
        name: task.name.trim(),
        description: task.description.trim(),
        agent_type: task.agent_type,
        required_capabilities: task.required_capabilities
          ? task.required_capabilities
              .split(",")
              .map((c) => c.trim())
              .filter(Boolean)
          : [],
        dependencies: task.dependencies,
        condition_type: task.condition_type,
        condition_data: task.condition_data,
        executor_type: task.executor_type,
      }))
    )

    return {
      basic: {
        name: name.trim(),
        category,
        description: description.trim() || undefined,
        scenario_desc: scenarioDesc.trim() || undefined,
        triggers: triggerList,
        executor_type: executorType,
        status: "draft",
        version: "1.0",
        source: "manual",
      },
      project_workflow: {
        workflow_name: name.trim(),
        description: scenarioDesc.trim(),
        phases,
      },
      task_templates: taskTemplates,
    }
  }

  const handleSubmit = async () => {
    const error = validate()
    if (error) {
      alert(error)
      return
    }

    setIsSubmitting(true)
    try {
      const payload = buildPayload()
      const result = await scenariosApi.customCreate(payload)
      setCreatedScenarioId(result.id)
      setShowSuccess(true)
    } catch (err) {
      console.error("Failed to create scenario:", err)
      alert(`创建失败: ${err instanceof Error ? err.message : "未知错误"}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = () => {
    setName("")
    setCategory("general")
    setDescription("")
    setScenarioDesc("")
    setTriggers("")
    setExecutorType("ai")
    setSteps([])
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">创建场景蓝图</h1>
        <p className="text-muted-foreground text-sm mt-1">
          定义场景的步骤和任务模板，作为工作流生成的蓝图
        </p>
      </div>

      {/* Basic Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">基本信息</CardTitle>
          <CardDescription>场景的基本属性</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label htmlFor="name">场景名称 *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：地震应急响应"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="category">分类</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="description">描述</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="场景简要描述..."
              rows={2}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="scenario_desc">适用场景</Label>
            <Textarea
              id="scenario_desc"
              value={scenarioDesc}
              onChange={(e) => setScenarioDesc(e.target.value)}
              placeholder="描述此场景适用于什么情况..."
              rows={2}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="executor_type">执行模式</Label>
            <Select value={executorType} onValueChange={setExecutorType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ai">AI</SelectItem>
                <SelectItem value="human">纯人</SelectItem>
                <SelectItem value="ai_approval">审批</SelectItem>
                <SelectItem value="ai_data">数据</SelectItem>
                <SelectItem value="ai_confirm">确认</SelectItem>
                <SelectItem value="auto_eval">自动</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label htmlFor="triggers">触发条件（逗号分隔）</Label>
            <Input
              id="triggers"
              value={triggers}
              onChange={(e) => setTriggers(e.target.value)}
              placeholder="地震震级 > 6, 人员密集区域"
            />
          </div>
        </CardContent>
      </Card>

      {/* Steps Editor Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">步骤编辑器</CardTitle>
            <CardDescription>
              定义场景的阶段步骤，每个步骤包含若干任务模板
            </CardDescription>
          </div>
          <Button onClick={addStep} size="sm" className="h-8">
            <Plus className="h-4 w-4 mr-1" /> 添加步骤
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {steps.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed rounded-lg">
              <p className="text-muted-foreground mb-2">尚未添加任何步骤</p>
              <p className="text-sm text-muted-foreground mb-4">
                点击「添加步骤」开始构建场景蓝图
              </p>
              <Button onClick={addStep} variant="outline">
                <Plus className="h-4 w-4 mr-1" /> 添加第一个步骤
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {steps.map((step, idx) => (
                <StepEditor
                  key={step.id}
                  step={step}
                  stepIndex={idx}
                  onStepChange={(updated) => updateStep(step.id, updated)}
                  onRemove={() => removeStep(step.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex justify-end gap-3 pb-8">
        <Button variant="outline" onClick={handleReset} disabled={isSubmitting}>
          重置
        </Button>
        <Button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? "创建中..." : "创建场景蓝图"}
        </Button>
      </div>

      {/* Success dialog */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>✅ 场景创建成功</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <p className="text-sm">
              场景 <strong>{name}</strong> 已成功创建。
            </p>
            {createdScenarioId && (
              <p className="text-xs text-muted-foreground font-mono">
                ID: {createdScenarioId}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowSuccess(false)
                navigate("/scenarios")
              }}
            >
              返回列表
            </Button>
            <Button
              onClick={() => {
                setShowSuccess(false)
                handleReset()
              }}
            >
              继续创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ScenarioCreate
