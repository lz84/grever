import { useState, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"
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
  DialogDescription,
} from "@/shared/components/ui/dialog"
import { Plus, Loader2, CheckCircle2, GitBranch, Layers } from "lucide-react"
import DecompositionView, { type DecompTreeItem } from '@/shared/components/DecompositionView'
import ScenarioProjectDialog from '@/reach/components/ScenarioProjectDialog'
import ScenarioTaskDialog from '@/reach/components/ScenarioTaskDialog'
import type { ScenarioProjectFormData, ProjectType } from '@/reach/components/ScenarioProjectDialog'
import type { ScenarioTaskFormData, TaskPriority } from '@/reach/components/ScenarioTaskDialog'
import { request as apiRequest } from "@/shared/utils/api"

// ==================== Constants ====================

const CATEGORIES = ["earthquake", "fire", "chemical", "flood", "software", "general"]
const CATEGORY_LABELS: Record<string, string> = {
  earthquake: '地震', fire: '火灾', chemical: '化学品',
  flood: '防汛', software: '软件开发', general: '通用',
}

// ==================== Local Types ====================

interface LocalProject {
  id: string
  name: string
  description: string
  project_type: ProjectType
  condition_type: string
  condition_data: Record<string, any> | null
  order_index: number
  next_step: string[] | null
  tasks: LocalTask[]
}

interface LocalTask {
  id: string
  name: string
  title: string
  description: string
  priority: TaskPriority
  required_capabilities: string[]
  dependencies: string[]
  condition_type: string
  condition_data: Record<string, any> | null
  executor_type: string
  order_in_phase: number
}

let _localCounter = 0
function genId() {
  _localCounter++
  return `local-${_localCounter}-${Date.now().toString(36).slice(-4)}`
}

// ==================== Safe parse ====================
function safeParseList(val: unknown): string[] {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') { try { return JSON.parse(val) } catch { return [] } }
  return []
}

// ==================== Main Component ====================

export function ScenarioCreate() {
  const navigate = useNavigate()

  // Basic info
  const [name, setName] = useState("")
  const [category, setCategory] = useState("general")
  const [description, setDescription] = useState("")
  const [scenarioDesc, setScenarioDesc] = useState("")
  const [triggers, setTriggers] = useState("")

  // Local tree state (projects + tasks)
  const [projects, setProjects] = useState<LocalProject[]>([])

  // Dialog state
  const [projectDialogOpen, setProjectDialogOpen] = useState(false)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [editProjectData, setEditProjectData] = useState<LocalProject | null>(null)
  const [editTaskData, setEditTaskData] = useState<{ task: LocalTask; projectId: string } | null>(null)
  const [taskParentProject, setTaskParentProject] = useState<string>("")

  // Submit state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitProgress, setSubmitProgress] = useState("")
  const [showSuccess, setShowSuccess] = useState(false)
  const [createdScenarioId, setCreatedScenarioId] = useState("")

  // ── Tree construction for DecompositionView ──

  const tree: DecompTreeItem[] = useMemo(() => {
    if (projects.length === 0) return []
    return [{
      id: "root-goal",
      type: "goal" as const,
      name: name || "未命名场景",
      description: scenarioDesc || description || "",
      status: "draft",
      children: projects.map(p => ({
        id: p.id,
        type: "project" as const,
        name: p.name,
        description: p.description,
        status: "planned",
        _data: { ...p },
        children: p.tasks.map(t => ({
          id: t.id,
          type: "task" as const,
          name: t.name,
          title: t.title || t.name,
          description: t.description,
          status: "pending",
          priority: t.priority,
          _data: { ...t, depends_on: t.dependencies },
        })),
      })),
    }]
  }, [projects, name, scenarioDesc, description])

  const dagProjects = useMemo(() => {
    return projects.map(p => ({
      id: p.id,
      name: p.name,
      status: "planned",
      next_step: p.next_step || [],
    }))
  }, [projects])

  const dagTasks = useMemo(() => {
    return projects.flatMap(p =>
      p.tasks.map(t => ({
        id: t.id,
        title: t.title || t.name,
        status: "pending",
        project_id: p.id,
      }))
    )
  }, [projects])

  // All tasks across all projects (for dependency selection in task dialog)
  const allTasksFlat = useMemo(() => projects.flatMap(p => p.tasks.map(t => ({
    id: t.id,
    name: t.title || t.name,
    project_id: p.id,
  }))), [projects])

  const projectRefs = useMemo(() => projects.map(p => ({ id: p.id, name: p.name })), [projects])

  // ── Callbacks ──

  const handleCreateProject = useCallback((data: ScenarioProjectFormData) => {
    const newProject: LocalProject = {
      id: genId(),
      name: data.name,
      description: data.description,
      project_type: data.project_type,
      condition_type: data.condition_type,
      condition_data: null,
      order_index: data.order_index,
      next_step: [],
      tasks: [],
    }
    setProjects(prev => {
      const updated = [...prev, newProject]
      // Auto-link DAG chain
      if (prev.length > 0) {
        const lastId = prev[prev.length - 1].id
        return updated.map((p, i) => {
          if (p.id === lastId) return { ...p, next_step: [newProject.id] }
          return p
        })
      }
      return updated
    })
    setProjectDialogOpen(false)
  }, [])

  const handleEditProject = useCallback((data: ScenarioProjectFormData) => {
    if (!editProjectData) return
    setProjects(prev => prev.map(p => {
      if (p.id !== editProjectData.id) return p
      return {
        ...p,
        name: data.name,
        description: data.description,
        project_type: data.project_type,
        condition_type: data.condition_type,
        order_index: data.order_index,
      }
    }))
    setProjectDialogOpen(false)
    setEditProjectData(null)
  }, [editProjectData])

  const handleDeleteProject = useCallback((projectId: string) => {
    setProjects(prev => prev.filter(p => p.id !== projectId))
  }, [])

  const handleCreateTask = useCallback((data: ScenarioTaskFormData) => {
    const newTask: LocalTask = {
      id: genId(),
      name: data.title,
      title: data.title,
      description: data.description,
      priority: data.priority,
      required_capabilities: data.capability_tags || [],
      dependencies: data.depends_on || [],
      condition_type: 'none',
      condition_data: null,
      executor_type: 'ai',
      order_in_phase: 0,
    }
    setProjects(prev => prev.map(p => {
      if (p.id !== data.project_id) return p
      return { ...p, tasks: [...p.tasks, newTask] }
    }))
    setTaskDialogOpen(false)
    setTaskParentProject("")
  }, [])

  const handleEditTask = useCallback((data: ScenarioTaskFormData) => {
    if (!editTaskData) return
    const { task, projectId } = editTaskData
    setProjects(prev => prev.map(p => {
      if (p.id !== projectId) return p
      return {
        ...p,
        tasks: p.tasks.map(t => {
          if (t.id !== task.id) return t
          return {
            ...t,
            name: data.title,
            title: data.title,
            description: data.description,
            priority: data.priority,
            required_capabilities: data.capability_tags || [],
            dependencies: data.depends_on || [],
          }
        }),
      }
    }))
    setTaskDialogOpen(false)
    setEditTaskData(null)
  }, [editTaskData])

  const handleDeleteTask = useCallback((taskId: string, projectId: string) => {
    setProjects(prev => prev.map(p => {
      if (p.id !== projectId) return p
      return { ...p, tasks: p.tasks.filter(t => t.id !== taskId) }
    }))
  }, [])

  const callbacks = useMemo(() => ({
    onCreateProject: () => { setEditProjectData(null); setProjectDialogOpen(true) },
    onCreateTask: (projectId: string) => {
      setTaskParentProject(projectId)
      setEditTaskData(null)
      setTaskDialogOpen(true)
    },
    onEdit: (item: DecompTreeItem) => {
      if (item.type === "project") {
        const proj = projects.find(p => p.id === item.id)
        if (proj) {
          setEditProjectData(proj)
          setProjectDialogOpen(true)
        }
      } else if (item.type === "task") {
        for (const p of projects) {
          const task = p.tasks.find(t => t.id === item.id)
          if (task) {
            setEditTaskData({ task, projectId: p.id })
            setTaskDialogOpen(true)
            return
          }
        }
      }
    },
    onDelete: (itemId: string, type: "project" | "task") => {
      if (type === "project") {
        handleDeleteProject(itemId)
      } else {
        for (const p of projects) {
          if (p.tasks.some(t => t.id === itemId)) {
            handleDeleteTask(itemId, p.id)
            return
          }
        }
      }
    },
    onEditDependsOn: (item: DecompTreeItem) => {
      if (item.type === "task") {
        for (const p of projects) {
          const task = p.tasks.find(t => t.id === item.id)
          if (task) {
            setEditTaskData({ task, projectId: p.id })
            setTaskDialogOpen(true)
            return
          }
        }
      }
    },
  }), [projects, handleDeleteProject, handleDeleteTask])

  // ── Validation ──

  const validate = (): string | null => {
    if (!name.trim()) return "请输入场景名称"
    if (projects.length === 0) return "请至少添加一个工程"
    for (const p of projects) {
      if (!p.name.trim()) return "工程名称不能为空"
    }
    return null
  }

  // ── Submit ──

  const handleSubmit = async () => {
    const error = validate()
    if (error) { alert(error); return }

    setIsSubmitting(true)
    setSubmitProgress("正在创建场景...")
    try {
      const triggerList = triggers.split(",").map(t => t.trim()).filter(Boolean)

      // Step 1: Create scenario with basic info
      const scenarioResult = await apiRequest("/scenarios", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          category,
          description: description.trim() || undefined,
          scenario_desc: scenarioDesc.trim() || undefined,
          triggers: triggerList,
          status: "draft",
          version: "1.0",
        }),
      }) as { id: string }
      const scenarioId = scenarioResult.id
      setCreatedScenarioId(scenarioId)

      // Step 2: Create projects (phases)
      setSubmitProgress("正在创建工程结构...")
      const projectIds: string[] = []
      for (let i = 0; i < projects.length; i++) {
        const p = projects[i]
        const projResult = await apiRequest(`/scenarios/${scenarioId}/projects`, {
          method: "POST",
          body: JSON.stringify({
            name: p.name.trim(),
            description: p.description,
            project_type: p.project_type,
            condition_type: p.condition_type,
            condition_data: p.condition_data,
            order_index: i,
            capability_tags: {},
            next_step: [],
          }),
        }) as { id: string }
        projectIds.push(projResult.id)
      }

      // Step 3: Link DAG chain (Phase 1 → Phase 2 → ...)
      setSubmitProgress("正在链接 DAG...")
      for (let i = 0; i < projectIds.length - 1; i++) {
        await apiRequest(`/scenarios/${scenarioId}/projects/${projectIds[i]}`, {
          method: "PUT",
          body: JSON.stringify({ next_step: [projectIds[i + 1]] }),
        })
      }

      // Step 4: Create tasks under each project
      setSubmitProgress("正在创建任务...")
      for (let i = 0; i < projects.length; i++) {
        const p = projects[i]
        for (let j = 0; j < p.tasks.length; j++) {
          const t = p.tasks[j]
          await apiRequest(`/scenarios/${scenarioId}/tasks`, {
            method: "POST",
            body: JSON.stringify({
              project_id: projectIds[i],
              phase_name: p.name.trim(),
              name: t.name.trim(),
              description: t.description.trim(),
              required_capabilities: t.required_capabilities,
              dependencies: t.dependencies,
              order_in_phase: j,
              priority: t.priority,
              condition_type: t.condition_type,
              condition_data: t.condition_data,
              executor_type: t.executor_type,
            }),
          })
        }
      }

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
    setProjects([])
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">创建场景蓝图</h1>
        <p className="text-muted-foreground text-sm mt-1">
          定义场景的结构，使用树 + DAG 视图构建工程与任务
        </p>
      </div>

      {/* Basic Info */}
      <div>
        <div className="px-4 py-2 bg-gray-100 border border-gray-200 rounded-t-lg">
          <span className="text-sm font-medium text-gray-700">基本信息</span>
        </div>
        <Card className="rounded-t-none border-t-0">
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>场景名称 *</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：罐体泄漏应急处置" />
              </div>
              <div className="space-y-1">
                <Label>分类</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(c => (<SelectItem key={c} value={c}>{CATEGORY_LABELS[c] || c}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <Label>描述</Label>
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="场景简要描述..." rows={2} />
            </div>
            <div className="space-y-1">
              <Label>适用场景</Label>
              <Textarea value={scenarioDesc} onChange={(e) => setScenarioDesc(e.target.value)} placeholder="描述此场景适用于什么情况..." rows={2} />
            </div>
            <div className="space-y-1">
              <Label>触发条件（逗号分隔）</Label>
              <Input value={triggers} onChange={(e) => setTriggers(e.target.value)} placeholder="地震震级 > 6, 人员密集区域" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tree + DAG Editor */}
      <div>
        <div className="px-4 py-2 bg-gray-100 border border-gray-200 rounded-t-lg">
          <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
            <GitBranch className="w-4 h-4" />场景结构
          </span>
        </div>
        <Card className="rounded-t-none border-t-0">
          <CardContent>
            <DecompositionView
              root={{ id: "root-goal", name: name || "未命名场景", status: "draft", description: scenarioDesc || description || undefined }}
              tree={tree}
              projects={dagProjects}
              tasks={dagTasks}
              stats={{ projectCount: projects.length, taskCount: allTasksFlat.length }}
              rootTypeLabel="场景"
              showExecutor={false}
              callbacks={callbacks}
            />
        </CardContent>
        </Card>
      </div>

      {/* Action buttons */}
      <div className="flex justify-end gap-3 pb-8">
        <Button variant="outline" onClick={handleReset} disabled={isSubmitting}>重置</Button>
        <Button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              {submitProgress || "创建中..."}
            </>
          ) : (
            "创建场景蓝图"
          )}
        </Button>
      </div>

      {/* Project Dialog */}
      <ScenarioProjectDialog
        open={projectDialogOpen}
        onOpenChange={(v) => {
          if (!v) {
            setProjectDialogOpen(false)
            setEditProjectData(null)
          }
        }}
        scenarioId={createdScenarioId || "temp"}
        onSubmit={async (isEdit, data) => {
          if (isEdit) {
            handleEditProject(data)
          } else {
            handleCreateProject(data)
          }
        }}
        initialData={editProjectData ? {
          id: editProjectData.id,
          name: editProjectData.name,
          description: editProjectData.description,
          project_type: editProjectData.project_type,
          condition_type: 'none',
          condition_data: null,
          order_index: editProjectData.order_index,
          capability_tags: [],
        } : undefined}
      />

      {/* Task Dialog */}
      <ScenarioTaskDialog
        open={taskDialogOpen}
        onOpenChange={(v) => {
          if (!v) {
            setTaskDialogOpen(false)
            setEditTaskData(null)
            setTaskParentProject("")
          }
        }}
        scenarioId={createdScenarioId || "temp"}
        projects={projectRefs}
        tasks={allTasksFlat}
        onSubmit={async (isEdit, data) => {
          if (isEdit) {
            handleEditTask(data)
          } else {
            handleCreateTask(data)
          }
        }}
        initialData={editTaskData ? {
          id: editTaskData.task.id,
          title: editTaskData.task.title || editTaskData.task.name || '',
          description: editTaskData.task.description || '',
          project_id: editTaskData.projectId,
          priority: editTaskData.task.priority,
          capability_tags: editTaskData.task.required_capabilities || [],
          depends_on: editTaskData.task.dependencies || [],
          condition_type: 'none' as const,
          condition_data: null,
        } : (taskParentProject ? {
          id: '',
          title: '',
          description: '',
          project_id: taskParentProject,
          priority: 'medium' as TaskPriority,
          capability_tags: [],
          depends_on: [],
          condition_type: 'none' as const,
          condition_data: null,
        } : undefined)}
      />

      {/* Success dialog */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
              场景创建成功
            </DialogTitle>
            <DialogDescription>场景蓝图 + 工程结构已完整创建</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm">场景 <strong>{name}</strong> 已成功创建。</p>
            {createdScenarioId && <p className="text-xs text-muted-foreground font-mono">ID: {createdScenarioId}</p>}
            <div className="space-y-2 bg-muted/50 rounded-lg p-3">
              <div className="flex items-center gap-2 text-sm">
                <GitBranch className="w-4 h-4 text-blue-500" />
                <span><strong>{projects.length}</strong> 个工程（Phases）</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Layers className="w-4 h-4 text-purple-500" />
                <span><strong>{allTasksFlat.length}</strong> 个任务</span>
              </div>
              {projects.length > 0 && (
                <div className="text-xs text-muted-foreground space-y-0.5 mt-1">
                  {projects.map((p, i) => (
                    <div key={p.id}>Phase {i + 1}: {p.name}（{p.tasks.length} 个任务）{i < projects.length - 1 ? " →" : " ✓"}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowSuccess(false); navigate("/scenarios") }}>返回列表</Button>
            <Button onClick={() => { setShowSuccess(false); navigate(`/scenarios/${createdScenarioId}`) }}>查看详情</Button>
            <Button variant="secondary" onClick={() => { setShowSuccess(false); handleReset() }}>继续创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ScenarioCreate

