import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  MiniMap, Controls, Background, ReactFlow,
  useNodesState, useEdgesState,
  MarkerType, Node, Edge, Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { goalsApi, projectsApi, tasksApi, request } from '../../../shared/utils/api'
import type { Goal, Project, Task } from '../../../shared/utils/api'

import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog'
import {
  ChevronDown, ChevronRight, Target, FolderKanban, ListTodo,
  Plus, Layers, ArrowLeft, Loader2, AlertCircle, RefreshCw, Trash2, Pencil, GitBranch,
} from 'lucide-react'

// ============================================================================
// Types
// ============================================================================

interface TreeItem {
  id: string
  type: 'goal' | 'project' | 'task'
  name: string
  description?: string
  status: string
  priority?: string
  goal_id?: string
  project_id?: string
  children?: TreeItem[]
  _data?: Project | Task
}

// ============================================================================
// Status helpers
// ============================================================================

function getStatusBadge(status: string): { variant: 'info' | 'success' | 'secondary' | 'destructive' | 'default' | 'warning' | 'outline'; label: string } {
  const s = status?.toLowerCase() || ''
  const map: Record<string, { variant: any; label: string }> = {
    'active': { variant: 'info', label: '进行中' },
    'in_progress': { variant: 'info', label: '进行中' },
    'completed': { variant: 'success', label: '已完成' },
    'done': { variant: 'success', label: '已完成' },
    'planned': { variant: 'secondary', label: '计划中' },
    'todo': { variant: 'secondary', label: '待办' },
    'pending': { variant: 'secondary', label: '待办' },
    'failed': { variant: 'destructive', label: '失败' },
    'cancelled': { variant: 'secondary', label: '已取消' },
    'on_hold': { variant: 'warning', label: '暂停' },
    'archived': { variant: 'outline', label: '已归档' },
  }
  return map[s] || { variant: 'secondary', label: status || '未知' }
}

function getPriorityBadge(priority?: string): { label: string; color: string } {
  const p = priority?.toLowerCase() || ''
  const map: Record<string, { label: string; color: string }> = {
    'high': { label: '高', color: 'text-red-500' },
    'medium': { label: '中', color: 'text-yellow-500' },
    'low': { label: '低', color: 'text-green-500' },
    'critical': { label: '紧急', color: 'text-red-700' },
  }
  return map[p] || { label: p || '-', color: 'text-gray-400' }
}

// ============================================================================
// Dialog components
// ============================================================================

function ProjectDialog({
  open, onOpenChange, onSubmit, initialData, isEdit,
}: {
  open: boolean; onOpenChange: (v: boolean) => void;
  onSubmit: (data: { name: string; description: string; priority: string }) => void;
  initialData?: { name: string; description: string; priority: string };
  isEdit?: boolean;
}) {
  const [name, setName] = useState(initialData?.name || '')
  const [description, setDescription] = useState(initialData?.description || '')
  const [priority, setPriority] = useState(initialData?.priority || 'medium')

  useEffect(() => {
    if (open) {
      setName(initialData?.name || '')
      setDescription(initialData?.description || '')
      setPriority(initialData?.priority || 'medium')
    }
  }, [open, initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSubmit({ name: name.trim(), description: description.trim(), priority })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑 Project' : '新建 Project'}</DialogTitle>
          <DialogDescription>{isEdit ? '修改项目基本信息' : '填写项目基本信息'}</DialogDescription>
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
          <div>
            <label className="text-sm font-medium">优先级</label>
            <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={priority} onChange={e => setPriority(e.target.value)}>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button type="submit">创建</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function TaskDialog({
  open, onOpenChange, onSubmit, projects, tasks, initialData, isEdit,
}: {
  open: boolean; onOpenChange: (v: boolean) => void;
  onSubmit: (data: {
    title: string; description: string; priority: string;
    project_id: string; depends_on: string[];
  }) => void;
  projects: Project[];
  tasks: Task[];
  initialData?: { title: string; description: string; priority: string; project_id: string; depends_on: string[] };
  isEdit?: boolean;
}) {
  const [title, setTitle] = useState(initialData?.title || '')
  const [description, setDescription] = useState(initialData?.description || '')
  const [priority, setPriority] = useState(initialData?.priority || 'medium')
  const [projectId, setProjectId] = useState(initialData?.project_id || '')
  const [dependsOn, setDependsOn] = useState<string[]>(initialData?.depends_on || [])

  useEffect(() => {
    if (open) {
      setTitle(initialData?.title || '')
      setDescription(initialData?.description || '')
      setPriority(initialData?.priority || 'medium')
      setProjectId(initialData?.project_id || '')
      setDependsOn(initialData?.depends_on || [])
    }
  }, [open, initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    onSubmit({ title: title.trim(), description: description.trim(), priority, project_id: projectId, depends_on: dependsOn })
  }

  const toggleDependency = (taskId: string) => {
    setDependsOn(prev => prev.includes(taskId) ? prev.filter(id => id !== taskId) : [...prev, taskId])
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑 Task' : '新建 Task'}</DialogTitle>
          <DialogDescription>{isEdit ? '修改任务信息' : '填写任务信息，可设置依赖关系'}</DialogDescription>
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
              <label className="text-sm font-medium">优先级</label>
              <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                value={priority} onChange={e => setPriority(e.target.value)}>
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">所属 Project</label>
              <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                value={projectId} onChange={e => {
                const newProj = e.target.value
                setProjectId(newProj)
                if (newProj) {
                  const projTasks = tasks.filter(t => t.project_id === newProj)
                  const projTaskIds = new Set(projTasks.map(t => t.id))
                  setDependsOn(prev => prev.filter(id => projTaskIds.has(id)))
                } else {
                  setDependsOn([])
                }
              }}>
                <option value="">-- 选择项目 --</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>
                      <div>
            <label className="text-sm font-medium mb-1 block">依赖任务 (同工程下任务)</label>
            <div className="border rounded-md p-2 max-h-40 overflow-y-auto space-y-1">
              {tasks.filter(t => !projectId || t.project_id === projectId).length === 0 && (
                <p className="text-xs text-muted-foreground p-1">
                  {projectId ? '该工程下暂无其他任务' : '请先选择所属工程'}
                </p>
              )}
              {tasks.filter(t => !projectId || t.project_id === projectId).map(t => (
                <label key={t.id} className="flex items-center gap-2 text-sm p-1 hover:bg-muted/50 rounded cursor-pointer">
                  <input type="checkbox" checked={dependsOn.includes(t.id)} onChange={() => toggleDependency(t.id)}
                    className="rounded border-gray-300" />
                  <span className="truncate text-xs">{t.title || t.id}</span>
                </label>
              ))}
            </div>
            {dependsOn.length > 0 && (
              <p className="text-xs text-muted-foreground mt-1">已选择 {dependsOn.length} 个依赖</p>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button type="submit">创建</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function EditDependsOnDialog({
  open, onOpenChange, onSubmit, currentDependsOn, allItems, itemType, parentId, parentType,
}: {
  open: boolean; onOpenChange: (v: boolean) => void;
  onSubmit: (dependsOn: string[]) => void;
  currentDependsOn: string[];
  allItems: { id: string; name: string; type: string; parent_id?: string; parent_type?: string }[];
  itemType: 'project' | 'task';
  /** The parent ID of the item being edited */
  parentId?: string;
  /** The type of parent: 'project' or 'task' */
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

// ============================================================================
// Tree Node Component
// ============================================================================

function TreeNode({
  node, depth, collapsed, onToggle, onCreateTask, onCreateProject, onEditDependsOn, onDelete, onEdit,
}: {
  node: TreeItem; depth: number;
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  onCreateTask?: (parentId?: string) => void;
  onCreateProject?: () => void;
  onEditDependsOn?: (item: TreeItem) => void;
  onDelete?: (id: string, type: 'project' | 'task') => void;
  onEdit?: (item: TreeItem) => void;
}) {
  const isCollapsed = collapsed.has(node.id)
  const hasChildren = node.children && node.children.length > 0
  const statusInfo = getStatusBadge(node.status)
  const indent = depth * 20

  const icons: Record<string, React.ReactNode> = {
    goal: <Target className="w-4 h-4 text-purple-500" />,
    project: <FolderKanban className="w-4 h-4 text-emerald-500" />,
    task: <ListTodo className="w-4 h-4 text-blue-500" />,
  }

  const depCount = (node._data as any)?.depends_on?.length || 0

  return (
    <div key={node.id}>
      <div
        className="flex items-center gap-1.5 py-1.5 px-2 hover:bg-muted/50 rounded-md transition-colors cursor-pointer group"
        style={{ paddingLeft: `${8 + indent}px` }}
        onClick={() => hasChildren && onToggle(node.id)}
      >
        <div className="w-4 h-4 flex items-center justify-center shrink-0">
          {hasChildren ? (
            isCollapsed ? <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
          ) : <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />}
        </div>
        {icons[node.type]}
        <span className="flex-1 text-sm font-medium truncate">{node.name}</span>
        <Badge variant={statusInfo.variant} className="text-[10px] h-5 shrink-0">{statusInfo.label}</Badge>
        {node.priority && node.type !== 'goal' && (
          <span className={`text-[10px] ${getPriorityBadge(node.priority).color} shrink-0`}>
            {getPriorityBadge(node.priority).label}
          </span>
        )}
        {depCount > 0 && (
          <span className="text-[10px] text-amber-600 shrink-0" title={`依赖 ${depCount} 个`}>
            🔗{depCount}
          </span>
        )}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          {node.type === 'goal' && onCreateProject && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); onCreateProject(); }}>
              <Plus className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'project' && onCreateTask && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); onCreateTask(node.id); }}>
              <Plus className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'project' && onEdit && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); onEdit(node); }} title="编辑工程">
              <Pencil className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'project' && onDelete && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={e => { e.stopPropagation(); onDelete(node.id, 'project'); }} title="删除工程">
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'task' && onEdit && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); onEdit(node); }} title="编辑任务">
              <Pencil className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'task' && onDelete && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={e => { e.stopPropagation(); onDelete(node.id, 'task'); }} title="删除任务">
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
          {node.type !== 'goal' && onEditDependsOn && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); onEditDependsOn(node); }} title="编辑依赖">
              <Layers className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>
      {hasChildren && !isCollapsed && node.children!.map(child => (
        <TreeNode key={child.id} node={child} depth={depth + 1}
          collapsed={collapsed} onToggle={onToggle}
          onCreateTask={onCreateTask} onCreateProject={onCreateProject}
          onEditDependsOn={onEditDependsOn} onDelete={onDelete} onEdit={onEdit} />
      ))}
    </div>
  )
}

// ============================================================================
// DAG Component
// ============================================================================

function DagView({ goal, projects, tasks, dagLayoutKey }: { goal?: Goal | null; projects: Project[]; tasks: Task[]; dagLayoutKey: number }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([])

  const dagData = useMemo(() => {
    const allNodes: any[] = []
    const allEdges: any[] = []

    // ── DAG = 流程图，箭头表示执行顺序（上游 → 下游）──

    // Goal node
    if (goal) {
      allNodes.push({
        id: goal.id,
        type: 'default',
        position: { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: goal.title || '未命名目标', type: 'goal', status: goal.status },
        style: {
          background: '#f5f3ff',
          border: '2px solid #a78bfa',
          borderRadius: '10px',
          padding: '10px 16px',
          minWidth: '180px',
          fontSize: '14px',
          fontWeight: '700',
        },
      })
    }

    // Project nodes
    projects.forEach(p => {
      allNodes.push({
        id: p.id,
        type: 'default',
        position: { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: p.name, type: 'project', status: p.status },
        style: {
          background: p.status === 'completed' || p.status === 'done' ? '#dcfce7' :
                      p.status === 'active' || p.status === 'in_progress' ? '#dbeafe' : '#f3f4f6',
          border: `2px solid ${p.status === 'completed' ? '#22c55e' : p.status === 'active' ? '#3b82f6' : '#d1d5db'}`,
          borderRadius: '8px',
          padding: '8px 12px',
          minWidth: '160px',
          fontSize: '12px',
          fontWeight: '600',
        },
      })
    })

    // Project dependency edges: use next_step (forward links, upstream → downstream)
    projects.forEach(p => {
      const nextSteps = (p as any).next_step || []
      nextSteps.forEach((nextId: string) => {
        // Only draw edge if target project exists in current list
        if (projects.some(pp => pp.id === nextId)) {
          allEdges.push({
            id: `edge-dep-${p.id}-${nextId}`,
            source: p.id,
            target: nextId,
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#f59e0b', strokeWidth: 2 },
          })
        }
      })
    })

    // Goal → root projects (not referenced by any project's next_step)
    if (goal && projects.length > 0) {
      const targetedProjects = new Set<string>()
      projects.forEach(p => {
        ((p as any).next_step || []).forEach((nid: string) => targetedProjects.add(nid))
      })
      projects.forEach(p => {
        if (!targetedProjects.has(p.id)) {
          allEdges.push({
            id: `edge-goal-${p.id}`,
            source: goal.id,
            target: p.id,
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            animated: false,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#a78bfa', strokeWidth: 2, strokeDasharray: '4 4' },
          })
        }
      })
    }

    // Task nodes
    tasks.forEach(t => {
      allNodes.push({
        id: t.id,
        type: 'default',
        position: { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: t.title || t.id, type: 'task', status: t.status },
        style: {
          background: t.status === 'done' || t.status === 'completed' ? '#f0fdf4' :
                      t.status === 'in_progress' ? '#eff6ff' : '#fafafa',
          border: `1px solid ${t.status === 'done' ? '#86efac' : t.status === 'in_progress' ? '#93c5fd' : '#e5e7eb'}`,
          borderRadius: '6px',
          padding: '6px 10px',
          minWidth: '120px',
          fontSize: '11px',
        },
      })
    })

    // Task dependency edges: use next_step (forward links, upstream → downstream)
    tasks.forEach(t => {
      const nextSteps = (t as any).next_step || []
      nextSteps.forEach((nextId: string) => {
        // Only draw edge if target task exists
        if (tasks.some(tt => tt.id === nextId)) {
          allEdges.push({
            id: `edge-task-${t.id}-${nextId}`,
            source: t.id,
            target: nextId,
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#a78bfa', strokeWidth: 1.5 },
          })
        }
      })
    })

    // Project → Task: only for root tasks (not referenced by any sibling task's next_step)
    projects.forEach(p => {
      const projTasks = tasks.filter(t => t.project_id === p.id)
      const targetedTasks = new Set<string>()
      projTasks.forEach(t => {
        ((t as any).next_step || []).forEach((nid: string) => targetedTasks.add(nid))
      })
      projTasks.forEach(t => {
        if (!targetedTasks.has(t.id)) {
          allEdges.push({
            id: `edge-proj-${p.id}-${t.id}`,
            source: p.id,
            target: t.id,
            sourcePosition: Position.Right,
            targetPosition: Position.Left,
            animated: false,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#34d399', strokeWidth: 1.5, strokeDasharray: '4 4' },
          })
        }
      })
    })

    return { nodes: allNodes as any[], edges: allEdges as any[] }
  }, [projects, tasks, dagLayoutKey])

  // Auto-layout: topological layers (execution order → horizontal, same order → vertical)
  useEffect(() => {
    if (dagData.nodes.length === 0) {
      setNodes([])
      setEdges(dagData.edges as any[])
      return
    }

    const adj: Record<string, string[]> = {}
    const preds: Record<string, string[]> = {}
    const inDeg: Record<string, number> = {}
    const nodeMap: Record<string, any> = {}

    dagData.nodes.forEach(n => {
      adj[n.id] = []
      preds[n.id] = []
      inDeg[n.id] = 0
      nodeMap[n.id] = n
    })

    dagData.edges.forEach(e => {
      if (adj[e.source] !== undefined) {
        adj[e.source].push(e.target)
        preds[e.target].push(e.source)
        if (inDeg[e.target] !== undefined) inDeg[e.target]++
      }
    })

    // Longest-path topological layering: layer[v] = max(layer[p] for p in preds[v]) + 1
    const queue: string[] = []
    const layer: Record<string, number> = {}
    Object.keys(inDeg).forEach(id => {
      if (inDeg[id] === 0) {
        queue.push(id)
        layer[id] = 0
      }
    })

    while (queue.length > 0) {
      const current = queue.shift()!
      for (const neighbor of adj[current]) {
        inDeg[neighbor]--
        // Always take the max layer from all predecessors
        layer[neighbor] = Math.max(layer[neighbor] || 0, layer[current] + 1)
        if (inDeg[neighbor] === 0) {
          queue.push(neighbor)
        }
      }
    }

    // Handle cycles / unreachable: assign to layer 0
    dagData.nodes.forEach(n => {
      if (layer[n.id] === undefined) layer[n.id] = 0
    })

    // Group by layer
    const layers: Record<number, string[]> = {}
    dagData.nodes.forEach(n => {
      const l = layer[n.id]
      if (!layers[l]) layers[l] = []
      layers[l].push(n.id)
    })

    // Sort within each layer by priority, then by creation order (stable)
    const priorityOrder: Record<string, number> = {
      'critical': 0, 'high': 1, 'medium': 2, 'low': 3
    }
    Object.keys(layers).forEach(lKey => {
      const l = parseInt(lKey)
      layers[l].sort((a, b) => {
        const na = nodeMap[a]?.data?.label || ''
        const nb = nodeMap[b]?.data?.label || ''
        const pa = priorityOrder[nodeMap[a]?.data?.priority || ''] ?? 99
        const pb = priorityOrder[nodeMap[b]?.data?.priority || ''] ?? 99
        if (pa !== pb) return pa - pb
        // Stable sort: maintain original order for same priority
        return na.localeCompare(nb)
      })
    })

    // Position nodes: layer → x (horizontal), index in layer → y (vertical)
    const NODE_W = 200, NODE_H = 55, GAP_X = 80, GAP_Y = 16
    const positioned = dagData.nodes.map(n => {
      const l = layer[n.id]
      const layerNodes = layers[l]
      const ni = layerNodes.indexOf(n.id)
      return {
        ...n,
        position: {
          x: 40 + l * (NODE_W + GAP_X),
          y: ni * (NODE_H + GAP_Y),
        },
      }
    })

    setNodes(positioned as any)
    setEdges(dagData.edges as any)
  }, [dagData])

  if (dagData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        暂无数据。先在左侧创建 Project 和 Task。
      </div>
    )
  }

  return (
    <ReactFlow
      key={dagLayoutKey}
      nodes={nodes} edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1} maxZoom={2}
      nodesDraggable={false}
      nodesConnectable={false}
      edgesFocusable={false}
      elementsSelectable={false}
      defaultEdgeOptions={{
        markerEnd: { type: MarkerType.ArrowClosed },
      }}
    >
      <Background color="#e2e8f0" gap={16} size={1} />
      <Controls className="!bg-white !shadow-md !rounded-lg" />
      <MiniMap className="!bg-white/90 !rounded-lg !shadow-md" maskColor="rgba(248,250,252,0.5)" />
    </ReactFlow>
  )
}

// ============================================================================
// Main Page
// ============================================================================

export default function GoalDecomposePage() {
  const { id: goalId } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [goal, setGoal] = useState<Goal | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  // Dialogs
  const [projectDialogOpen, setProjectDialogOpen] = useState(false)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [editDependsOnOpen, setEditDependsOnOpen] = useState(false)
  const [taskParentProject, setTaskParentProject] = useState<string | undefined>()
  const [editDependsOnItem, setEditDependsOnItem] = useState<TreeItem | null>(null)

  // Edit dialogs
  const [editProjectOpen, setEditProjectOpen] = useState(false)
  const [editTaskOpen, setEditTaskOpen] = useState(false)
  const [editProjectItem, setEditProjectItem] = useState<TreeItem | null>(null)
  const [editTaskItem, setEditTaskItem] = useState<TreeItem | null>(null)
  const [dagLayoutKey, setDagLayoutKey] = useState(0)

  const fetchData = useCallback(async () => {
    if (!goalId) return
    try {
      setLoading(true)
      setError(null)
      const [goalsList, projectsList, tasksList] = await Promise.all([
        goalsApi.list(),
        projectsApi.list({ goal_id: goalId }),
        tasksApi.list({ goal_id: goalId }),
      ])
      const currentGoal = goalsList.find((g: Goal) => g.id === goalId) || null
      setGoal(currentGoal)
      setProjects(projectsList)
      setTasks(tasksList)
      // Auto-expand goal node
      if (currentGoal) setCollapsed(new Set())
    } catch (e: any) {
      setError(e.message || '加载失败，请检查服务器是否启动')
    } finally {
      setLoading(false)
    }
  }, [goalId])

  useEffect(() => { fetchData() }, [fetchData])

  function toggleCollapse(id: string) {
    setCollapsed(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Build tree
  const tree: TreeItem[] = useMemo(() => {
    if (!goal) return []
    return [{
      id: goal.id,
      type: 'goal',
      name: goal.title || '未命名目标',
      status: goal.status || 'draft',
      children: projects.map(p => ({
        id: p.id,
        type: 'project' as const,
        name: p.name || '未命名项目',
        description: p.description || '',
        status: p.status || 'planned',
        priority: p.priority,
        goal_id: p.goal_id || undefined,
        _data: p,
        children: tasks
          .filter(t => t.project_id === p.id)
          .map(t => ({
            id: t.id,
            type: 'task' as const,
            name: t.title || '未命名任务',
            description: t.description || '',
            status: t.status || 'pending',
            priority: String(t.priority || ''),
            project_id: t.project_id || undefined,
            _data: t,
          })),
      })),
    }]
  }, [goal, projects, tasks])

  // All items for dependency selection (with parent scope info)
  const allSelectableItems = useMemo(() => {
    const items: { id: string; name: string; type: string; parent_id?: string; parent_type?: string }[] = []
    projects.forEach(p => items.push({ id: p.id, name: `📁 ${p.name}`, type: 'project' }))
    tasks.forEach(t => items.push({
      id: t.id,
      name: `✅ ${t.title || t.id}`,
      type: 'task',
      parent_id: (t as any).parent_id || t.project_id || undefined,
      parent_type: (t as any).parent_id ? 'task' : 'project',
    }))
    return items
  }, [projects, tasks])

  // ---- Handlers ----

  const handleCreateProject = async (data: { name: string; description: string; priority: string }) => {
    try {
      await projectsApi.create({
        name: data.name,
        description: data.description,
        goal_id: goalId,
        depends_on: [],
      })
      setProjectDialogOpen(false)
      await fetchData()
    } catch (e: any) {
      alert('创建失败: ' + e.message)
    }
  }

  const handleCreateTask = async (data: { title: string; description: string; priority: string; project_id: string; depends_on: string[] }) => {
    try {
      const newTask = await tasksApi.create({
        title: data.title,
        description: data.description,
        project_id: data.project_id,
        priority: data.priority,
        acceptance_criteria: `[{"type": "subjective", "name": "完成标准", "desc": "任务已完成"}]`,
      })
      // Update depends_on via PATCH if any
      if (data.depends_on && data.depends_on.length > 0) {
        await tasksApi.update(newTask.id, { depends_on: data.depends_on })
      }
      setTaskDialogOpen(false)
      setTaskParentProject(undefined)
      await fetchData()
    } catch (e: any) {
      alert('创建失败: ' + e.message)
    }
  }

  const handleEditDependsOn = async (dependsOn: string[]) => {
    if (!editDependsOnItem) return
    try {
      if (editDependsOnItem.type === 'project') {
        await projectsApi.updateDependsOn(editDependsOnItem.id, dependsOn)
      } else if (editDependsOnItem.type === 'task') {
        await tasksApi.update(editDependsOnItem.id, { depends_on: dependsOn })
      }
      setEditDependsOnOpen(false)
      setEditDependsOnItem(null)
      await fetchData()
    } catch (e: any) {
      alert('保存失败: ' + e.message)
    }
  }

  const handleDelete = async (id: string, type: 'project' | 'task') => {
    const label = type === 'project' ? '工程' : '任务'
    if (!confirm(`确定删除这个${label}吗？`)) return
    try {
      if (type === 'project') {
        await projectsApi.remove(id)
      } else {
        await tasksApi.remove(id)
      }
      await fetchData()
    } catch (e: any) {
      alert(`删除失败: ${e.message}`)
    }
  }

  // ---- Edit handlers ----

  const handleEditProject = async (data: { name: string; description: string; priority: string }) => {
    if (!editProjectItem) return
    try {
      // PUT /projects/ only accepts name, verifier_agent_id, goal_id
      await projectsApi.update(editProjectItem.id, {
        name: data.name,
      })
      setEditProjectOpen(false)
      setEditProjectItem(null)
      await fetchData()
    } catch (e: any) {
      alert('更新失败: ' + e.message)
    }
  }

  const handleEditTask = async (data: { title: string; description: string; priority: string; project_id: string; depends_on: string[] }) => {
    if (!editTaskItem) return
    try {
      // PUT /tasks/ doesn't accept project_id, only title/desc/priority/depends_on
      await tasksApi.update(editTaskItem.id, {
        title: data.title,
        description: data.description,
        priority: data.priority,
        depends_on: data.depends_on,
      })
      setEditTaskOpen(false)
      setEditTaskItem(null)
      await fetchData()
    } catch (e: any) {
      alert('更新失败: ' + e.message)
    }
  }

  const handleEditItem = (item: TreeItem) => {
    if (item.type === 'project') {
      setEditProjectItem(item)
      setEditProjectOpen(true)
    } else if (item.type === 'task') {
      setEditTaskItem(item)
      setEditTaskOpen(true)
    }
  }

  // ---- Render ----

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground ml-3">加载分解数据...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-4" />
        <p className="text-destructive mb-4">{error}</p>
        <Button onClick={fetchData}>重试</Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(`/coordination/goals/${goalId}`)}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-500" />
              {goal?.title || '目标分解'}
            </h1>
            {goal?.description && (
              <p className="text-sm text-muted-foreground mt-1">{goal.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setDagLayoutKey(k => k + 1)} title="重新布局 DAG">
            <GitBranch className="w-4 h-4" /> 一键重排
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span>{projects.length} 个项目</span>
        <span>·</span>
        <span>{tasks.length} 个任务</span>
      </div>

      {/* Main Layout: Left Tree + Right DAG */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ minHeight: '70vh' }}>
        {/* Left: Tree */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ListTodo className="w-4 h-4" />
              分解树
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="px-2 pb-2 max-h-[65vh] overflow-y-auto">
              {tree.length === 0 ? (
                <div className="text-center py-12">
                  <Target className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
                  <p className="text-muted-foreground text-sm">暂无分解数据</p>
                  <Button variant="outline" size="sm" className="mt-3" onClick={() => setProjectDialogOpen(true)}>
                    <Plus className="w-3 h-3 mr-1" /> 创建第一个 Project
                  </Button>
                </div>
              ) : (
                tree.map(node => (
                  <TreeNode key={node.id} node={node} depth={0}
                    collapsed={collapsed} onToggle={toggleCollapse}
                    onCreateTask={(projectId) => { setTaskParentProject(projectId); setTaskDialogOpen(true); }}
                    onCreateProject={() => setProjectDialogOpen(true)}
                    onEditDependsOn={(item) => {
                      setEditDependsOnItem(item)
                      setEditDependsOnOpen(true)
                    }}
                    onDelete={handleDelete}
                    onEdit={handleEditItem} />
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right: DAG */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="w-4 h-4" />
              依赖关系图 (DAG)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0" style={{ height: '65vh' }}>
            <DagView goal={goal} projects={projects} tasks={tasks} dagLayoutKey={dagLayoutKey} />
          </CardContent>
        </Card>
      </div>

      {/* Dialogs */}
      <ProjectDialog
        open={projectDialogOpen}
        onOpenChange={setProjectDialogOpen}
        onSubmit={handleCreateProject}
      />
      <TaskDialog
        open={taskDialogOpen}
        onOpenChange={(v) => { if (!v) { setTaskDialogOpen(false); setTaskParentProject(undefined); } }}
        onSubmit={handleCreateTask}
        projects={projects}
        tasks={tasks}
        initialData={taskParentProject ? { title: '', description: '', priority: 'medium', project_id: taskParentProject, depends_on: [] } : undefined}
      />
      {editDependsOnItem && (
        <EditDependsOnDialog
          open={editDependsOnOpen}
          onOpenChange={(v) => { if (!v) { setEditDependsOnOpen(false); setEditDependsOnItem(null); } }}
          onSubmit={handleEditDependsOn}
          currentDependsOn={(editDependsOnItem._data as any)?.depends_on || []}
          allItems={allSelectableItems}
          itemType={editDependsOnItem.type === 'project' ? 'project' : 'task'}
          parentId={(editDependsOnItem._data as any)?.parent_id || (editDependsOnItem._data as any)?.project_id}
          parentType={(editDependsOnItem._data as any)?.parent_id ? 'task' : 'project'}
        />
      )}

      {/* Edit Project Dialog */}
      <ProjectDialog
        open={editProjectOpen}
        onOpenChange={(v) => { if (!v) { setEditProjectOpen(false); setEditProjectItem(null); } }}
        onSubmit={handleEditProject}
        initialData={editProjectItem ? {
          name: editProjectItem.name,
          description: editProjectItem.description || '',
          priority: editProjectItem.priority || 'medium',
        } : undefined}
        isEdit
      />

      {/* Edit Task Dialog */}
      <TaskDialog
        open={editTaskOpen}
        onOpenChange={(v) => { if (!v) { setEditTaskOpen(false); setEditTaskItem(null); } }}
        onSubmit={handleEditTask}
        projects={projects}
        tasks={tasks}
        initialData={editTaskItem ? {
          title: editTaskItem.name,
          description: editTaskItem.description || '',
          priority: editTaskItem.priority || 'medium',
          project_id: (editTaskItem._data as any)?.project_id || '',
          depends_on: (editTaskItem._data as any)?.depends_on || [],
        } : undefined}
        isEdit
      />
    </div>
  )
}
