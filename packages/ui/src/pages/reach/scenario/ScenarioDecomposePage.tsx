import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { scenariosApi, request } from '../../../shared/utils/api'
import type { Scenario, ScenarioProject, ScenarioProjectTask } from '../../../shared/utils/scenariosApi'

import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog'
import { ArrowLeft, RefreshCw, Layers } from 'lucide-react'
import DecompositionView, { type DecompTreeItem } from '@/shared/components/DecompositionView'

// Safe parse helper — API returns some fields as JSON strings
function safeParseList(val: unknown): string[] {
  if (Array.isArray(val)) return val
  if (typeof val === 'string') {
    try { return JSON.parse(val) } catch { return [] }
  }
  return []
}

// ── Project Dialog ────────────────────────────────────────────────────────────

function ScenarioProjectDialog({
  open, onOpenChange, onSubmit, initialData, isEdit,
}: {
  open: boolean; onOpenChange: (v: boolean) => void;
  onSubmit: (data: { name: string; description: string; project_type: string; order: number }) => void;
  initialData?: { name: string; description: string; project_type: string; order: number };
  isEdit?: boolean;
}) {
  const [name, setName] = useState(initialData?.name || '')
  const [description, setDescription] = useState(initialData?.description || '')
  const [projectType, setProjectType] = useState(initialData?.project_type || 'mandatory')
  const [order, setOrder] = useState(initialData?.order ?? 0)

  useEffect(() => {
    if (open) {
      setName(initialData?.name || '')
      setDescription(initialData?.description || '')
      setProjectType(initialData?.project_type || 'mandatory')
      setOrder(initialData?.order ?? 0)
    }
  }, [open, initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSubmit({ name: name.trim(), description: description.trim(), project_type: projectType, order })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑 Project' : '新建 Project'}</DialogTitle>
          <DialogDescription>{isEdit ? '修改项目信息' : '填写项目基本信息'}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium">名称 *</label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="项目名称" required />
          </div>
          <div>
            <label className="text-sm font-medium">描述</label>
            <Textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="项目描述..." rows={3} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">类型</label>
              <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                value={projectType} onChange={e => setProjectType(e.target.value)}>
                <option value="mandatory">必选</option>
                <option value="optional">可选</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">顺序</label>
              <Input type="number" value={order} onChange={e => setOrder(parseInt(e.target.value) || 0)} />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button type="submit">{isEdit ? '保存' : '创建'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Task Dialog ───────────────────────────────────────────────────────────────

function ScenarioTaskDialog({
  open, onOpenChange, onSubmit, projects, tasks, initialData, isEdit,
}: {
  open: boolean; onOpenChange: (v: boolean) => void;
  onSubmit: (data: {
    title: string; description: string; project_id: string; priority: string;
    depends_on: string[];
  }) => void;
  projects: Array<{ id: string; name: string }>;
  tasks: Array<{ id: string; name: string; project_id: string }>;
  initialData?: {
    title: string; description: string; project_id: string; priority: string;
    depends_on: string[];
  };
  isEdit?: boolean;
}) {
  const [title, setTitle] = useState(initialData?.title || '')
  const [description, setDescription] = useState(initialData?.description || '')
  const [projectId, setProjectId] = useState(initialData?.project_id || '')
  const [priority, setPriority] = useState(initialData?.priority || 'medium')
  const [dependsOn, setDependsOn] = useState<string[]>(initialData?.depends_on || [])

  useEffect(() => {
    if (open) {
      setTitle(initialData?.title || '')
      setDescription(initialData?.description || '')
      setProjectId(initialData?.project_id || '')
      setPriority(initialData?.priority || 'medium')
      setDependsOn(initialData?.depends_on || [])
    }
  }, [open, initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    onSubmit({ title: title.trim(), description: description.trim(), project_id: projectId, priority, depends_on: dependsOn })
  }

  const toggleDependsOn = (taskId: string) => {
    setDependsOn(prev => prev.includes(taskId) ? prev.filter(id => id !== taskId) : [...prev, taskId])
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑 Task' : '新建 Task'}</DialogTitle>
          <DialogDescription>{isEdit ? '修改任务信息' : '填写任务信息'}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium">标题 *</label>
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="任务标题" required />
          </div>
          <div>
            <label className="text-sm font-medium">描述</label>
            <Textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="任务描述..." rows={2} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">所属 Project</label>
              <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                value={projectId} onChange={e => setProjectId(e.target.value)}>
                <option value="">-- 选择项目 --</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">优先级</label>
              <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                value={priority} onChange={e => setPriority(e.target.value)}>
                <option value="critical">紧急</option>
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">依赖任务 (同工程下)</label>
            <div className="border rounded-md p-2 max-h-40 overflow-y-auto space-y-1">
              {tasks.filter(t => !projectId || t.project_id === projectId).length === 0 && (
                <p className="text-xs text-muted-foreground p-1">
                  {projectId ? '该工程下暂无其他任务' : '请先选择所属工程'}
                </p>
              )}
              {tasks.filter(t => !projectId || t.project_id === projectId).map(t => (
                <label key={t.id} className="flex items-center gap-2 text-sm p-1 hover:bg-muted/50 rounded cursor-pointer">
                  <input type="checkbox" checked={dependsOn.includes(t.id)} onChange={() => toggleDependsOn(t.id)}
                    className="rounded border-gray-300" />
                  <span className="truncate text-xs">{t.name}</span>
                </label>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button type="submit">{isEdit ? '保存' : '创建'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ScenarioDecomposePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dialogs
  const [projectDialogOpen, setProjectDialogOpen] = useState(false)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [editProjectOpen, setEditProjectOpen] = useState(false)
  const [editTaskOpen, setEditTaskOpen] = useState(false)
  const [editDependsOnOpen, setEditDependsOnOpen] = useState(false)
  const [editProjectData, setEditProjectData] = useState<ScenarioProject | null>(null)
  const [editTaskData, setEditTaskData] = useState<{ task: ScenarioProjectTask; projectId: string } | null>(null)
  const [editDependsOnItem, setEditDependsOnItem] = useState<DecompTreeItem | null>(null)
  const [taskParentProject, setTaskParentProject] = useState<string | undefined>()

  const fetchData = useCallback(async () => {
    if (!id) return
    try {
      setLoading(true)
      setError(null)
      const data = await scenariosApi.get(id)
      setScenario(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { fetchData() }, [fetchData])

  // Build tree from scenario data
  const tree: DecompTreeItem[] = useMemo(() => {
    if (!scenario) return []
    const projects: ScenarioProject[] = scenario.projects || []

    return [{
      id: scenario.id,
      type: 'goal' as const,
      name: scenario.name || '未命名场景',
      description: scenario.scenario_desc || scenario.description || '',
      status: scenario.status || 'draft',
      children: projects.map(p => ({
        id: p.id,
        type: 'project' as const,
        name: p.name || '未命名项目',
        description: p.description || '',
        status: 'planned',
        priority: undefined,
        _data: p,
        children: (p.tasks || []).map(t => ({
          id: t.id,
          type: 'task' as const,
          name: t.title || t.name || '未命名任务',
          description: t.description || '',
          status: 'pending',
          priority: t.priority,
          _data: t,
        })),
      })),
    }]
  }, [scenario])

  // Flatten projects for DAG
  const dagProjects = useMemo(() => {
    if (!scenario) return []
    return (scenario.projects || []).map(p => ({
      id: p.id,
      name: p.name,
      status: 'planned',
      next_step: safeParseList(p.next_step),
    }))
  }, [scenario])

  // Flatten tasks for DAG
  const dagTasks = useMemo(() => {
    if (!scenario) return []
    const all: Array<{ id: string; title: string; status: string; project_id: string; depends_on?: string[] }> = []
    scenario.projects?.forEach(p => {
      (p.tasks || []).forEach(t => {
        all.push({
          id: t.id,
          title: (t.title as string) || (t.name as string) || '未命名任务',
          status: 'pending',
          project_id: p.id,
          depends_on: safeParseList(t.depends_on || t.dependencies || []),
        })
      })
    })
    return all
  }, [scenario])

  const projectCount = scenario?.projects?.length || 0
  const taskCount = dagTasks.length

  // ── Edit Depends On Handler ─────────────────────────────────────────────────

  async function handleEditDependsOn(dependsOn: string[]) {
    if (!editDependsOnItem) return
    try {
      if (editDependsOnItem.type === 'project') {
        // Project depends on next_step
        const project = editDependsOnItem._data as ScenarioProject
        await request(`/scenarios/${id}/projects/${project.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            next_step: dependsOn,
          }),
        })
      } else if (editDependsOnItem.type === 'task') {
        // Task depends on depends_on
        const task = editDependsOnItem._data as ScenarioProjectTask
        await request(`/scenarios/${id}/tasks/${task.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            depends_on: dependsOn,
          }),
        })
      }
      setEditDependsOnOpen(false)
      setEditDependsOnItem(null)
      await fetchData()
    } catch (e: any) {
      alert('保存依赖失败: ' + e.message)
    }
  }

  // ── CRUD Handlers ───────────────────────────────────────────────────────

  async function handleCreateProject(data: { name: string; description: string; project_type: string; order: number }) {
    try {
      await request(`/scenarios/${id}/projects`, {
        method: 'POST',
        body: JSON.stringify({
          name: data.name,
          description: data.description,
          project_type: data.project_type,
          order: data.order,
          capability_tags: [],
          condition_type: 'none',
          condition_data: null,
        }),
      })
      setProjectDialogOpen(false)
      await fetchData()
    } catch (e: any) {
      alert('创建失败: ' + e.message)
    }
  }

  async function handleEditProject(data: { name: string; description: string; project_type: string; order: number }) {
    if (!editProjectData) return
    try {
      await request(`/scenarios/${id}/projects/${editProjectData.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: data.name,
          description: data.description,
          project_type: data.project_type,
          order: data.order,
        }),
      })
      setEditProjectOpen(false)
      setEditProjectData(null)
      await fetchData()
    } catch (e: any) {
      alert('更新失败: ' + e.message)
    }
  }

  async function handleDeleteProject(projectId: string) {
    if (!confirm('确定删除这个项目吗？')) return
    try {
      await request(`/scenarios/${id}/projects/${projectId}`, { method: 'DELETE' })
      await fetchData()
    } catch (e: any) {
      alert('删除失败: ' + e.message)
    }
  }

  async function handleCreateTask(data: { title: string; description: string; project_id: string; priority: string; depends_on: string[] }) {
    try {
      // Backend accepts name and dependencies, convert for compatibility
      await request(`/scenarios/${id}/tasks`, {
        method: 'POST',
        body: JSON.stringify({
          name: data.title,
          description: data.description,
          project_id: data.project_id,
          priority: data.priority,
          dependencies: data.depends_on || [],
          condition_type: 'none',
          condition_data: null,
        }),
      })
      setTaskDialogOpen(false)
      setTaskParentProject(undefined)
      await fetchData()
    } catch (e: any) {
      alert('创建失败: ' + e.message)
    }
  }

  async function handleEditTask(data: { title: string; description: string; project_id: string; priority: string; depends_on: string[] }) {
    if (!editTaskData) return
    try {
      // Backend accepts name and dependencies, convert for compatibility
      await request(`/scenarios/${id}/tasks/${editTaskData.task.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: data.title,
          description: data.description,
          project_id: data.project_id,
          priority: data.priority,
          dependencies: data.depends_on || [],
        }),
      })
      setEditTaskOpen(false)
      setEditTaskData(null)
      await fetchData()
    } catch (e: any) {
      alert('更新失败: ' + e.message)
    }
  }

  async function handleDeleteTask(taskId: string) {
    if (!confirm('确定删除这个任务吗？')) return
    try {
      await request(`/scenarios/${id}/tasks/${taskId}`, { method: 'DELETE' })
      await fetchData()
    } catch (e: any) {
      alert('删除失败: ' + e.message)
    }
  }

  // Callbacks for DecompositionView
  const callbacks = useMemo(() => ({
    onCreateProject: () => setProjectDialogOpen(true),
    onCreateTask: (projectId: string) => { setTaskParentProject(projectId); setTaskDialogOpen(true) },
    onEdit: (item: DecompTreeItem) => {
      if (item.type === 'project') {
        setEditProjectData(item._data as ScenarioProject)
        setEditProjectOpen(true)
      } else if (item.type === 'task') {
        // Find parent project ID
        const parentProject = scenario?.projects?.find(p => p.tasks?.some(t => t.id === item.id))
        setEditTaskData({ task: item._data as ScenarioProjectTask, projectId: parentProject?.id || '' })
        setEditTaskOpen(true)
      }
    },
    onDelete: (itemId: string, type: 'project' | 'task') => {
      if (type === 'project') handleDeleteProject(itemId)
      else handleDeleteTask(itemId)
    },
    onRefresh: fetchData,
    onEditDependsOn: (item: DecompTreeItem) => {
      setEditDependsOnItem(item)
      setEditDependsOnOpen(true)
    },
  }), [scenario, id, fetchData])

  // Project refs for task dialog
  const projectRefs = useMemo(() => {
    return (scenario?.projects || []).map(p => ({ id: p.id, name: p.name }))
  }, [scenario])

  // All task refs for dependency selection
  const allTaskRefs = useMemo(() => {
    const all: Array<{ id: string; name: string; project_id: string }> = []
    scenario?.projects?.forEach(p => {
      (p.tasks || []).forEach(t => {
        all.push({ id: t.id, name: (t.title as string) || (t.name as string) || '', project_id: p.id })
      })
    })
    return all
  }, [scenario])

  // ── Edit Depends On Dialog ──────────────────────────────────────────────────

  function EditDependsOnDialog({
    open, onOpenChange, onSubmit, currentDependsOn, allItems, itemType, parentId, parentType,
  }: {
    open: boolean; onOpenChange: (v: boolean) => void;
    onSubmit: (dependsOn: string[]) => void;
    currentDependsOn: string[];
    allItems: { id: string; name: string; type: string; parent_id?: string; parent_type?: string }[];
    itemType: 'project' | 'task';
    parentId?: string;
    parentType?: string;
  }) {
    const [selected, setSelected] = useState<string[]>(currentDependsOn)

    useEffect(() => {
      if (open) setSelected(currentDependsOn)
    }, [open, currentDependsOn])

    const filteredItems = allItems.filter(item => {
      if (itemType === 'project') return item.type === 'project'
      if (item.type !== 'task') return false
      // For tasks, only show siblings: same parent_id + same parent_type
      if (parentId && parentType) {
        return item.parent_id === parentId && item.parent_type === parentType
      }
      // Fallback: same project_id
      if (parentId) return item.parent_id === parentId
      return true
    })

    const toggle = (id: string) => {
      setSelected(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])
    }

    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>编辑依赖关系</DialogTitle>
            <DialogDescription>
              {itemType === 'project' ? '选择依赖的其他 Project' : '选择依赖的其他 Task'}
            </DialogDescription>
          </DialogHeader>
          <div className="border rounded-md p-2 max-h-60 overflow-y-auto space-y-1">
            {filteredItems.length === 0 && <p className="text-xs text-muted-foreground p-1">暂无可选项目</p>}
            {filteredItems.map(item => (
              <label key={item.id} className="flex items-center gap-2 text-sm p-1 hover:bg-muted/50 rounded cursor-pointer">
                <input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)}
                  className="rounded border-gray-300" />
                <span className="truncate text-xs">{item.name || item.id}</span>
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button onClick={() => { onSubmit(selected); onOpenChange(false); }}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(`/scenarios/${id}`)}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              {scenario?.name || '场景分解'}
            </h1>
            {scenario?.description && (
              <p className="text-sm text-muted-foreground mt-1">{scenario.description}</p>
            )}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Decomposition View */}
      <DecompositionView
        root={{
          id: scenario?.id || '',
          name: scenario?.name || '未命名场景',
          status: scenario?.status || 'draft',
          description: scenario?.scenario_desc || scenario?.description || undefined,
        }}
        tree={tree}
        projects={dagProjects}
        tasks={dagTasks}
        stats={{ projectCount, taskCount }}
        rootTypeLabel="场景"
        loading={loading}
        error={error}
        onRetry={fetchData}
        callbacks={callbacks}
        showExecutor={false}
      />

      {/* Project Dialogs */}
      <ScenarioProjectDialog
        open={projectDialogOpen}
        onOpenChange={setProjectDialogOpen}
        onSubmit={handleCreateProject}
      />
      {editProjectData && (
        <ScenarioProjectDialog
          open={editProjectOpen}
          onOpenChange={(v) => { if (!v) { setEditProjectOpen(false); setEditProjectData(null); } }}
          onSubmit={handleEditProject}
          initialData={{
            name: editProjectData.name,
            description: editProjectData.description || '',
            project_type: editProjectData.project_type || 'mandatory',
            order: editProjectData.order || 0,
          }}
          isEdit
        />
      )}

      {/* Task Dialogs */}
      <ScenarioTaskDialog
        open={taskDialogOpen}
        onOpenChange={(v) => { if (!v) { setTaskDialogOpen(false); setTaskParentProject(undefined); } }}
        onSubmit={handleCreateTask}
        projects={projectRefs}
        tasks={allTaskRefs}
        initialData={taskParentProject ? {
          title: '', description: '', project_id: taskParentProject, priority: 'medium',
          depends_on: [],
        } : undefined}
      />
      {editTaskData && (
        <ScenarioTaskDialog
          open={editTaskOpen}
          onOpenChange={(v) => { if (!v) { setEditTaskOpen(false); setEditTaskData(null); } }}
          onSubmit={handleEditTask}
          projects={projectRefs}
          tasks={allTaskRefs}
          initialData={{
            title: (editTaskData.task.title as string) || (editTaskData.task.name as string) || '',
            description: editTaskData.task.description || '',
            project_id: editTaskData.projectId,
            priority: editTaskData.task.priority || 'medium',
            depends_on: safeParseList(editTaskData.task.depends_on || editTaskData.task.dependencies || []),
          }}
          isEdit
        />
      )}

      {/* Edit Depends On Dialog */}
      {editDependsOnItem && (
        <EditDependsOnDialog
          open={editDependsOnOpen}
          onOpenChange={(v) => { if (!v) { setEditDependsOnOpen(false); setEditDependsOnItem(null); } }}
          onSubmit={handleEditDependsOn}
          currentDependsOn={(editDependsOnItem._data as any)?.depends_on || []}
          allItems={allTaskRefs.map(t => ({ id: t.id, name: t.name, type: 'task', parent_id: t.project_id, parent_type: 'project' }))}
          itemType={editDependsOnItem.type === 'project' ? 'project' : 'task'}
          parentId={(editDependsOnItem._data as any)?.id}
          parentType={editDependsOnItem.type === 'project' ? undefined : 'project'}
        />
      )}
    </div>
  )
}
