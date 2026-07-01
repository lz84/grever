import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  MiniMap, Controls, Background, ReactFlow,
  ReactFlowProvider,
  useNodesState, useEdgesState,
  MarkerType, Position, Handle,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/shared/components/ui/toggle-group'
import {
  ChevronDown, ChevronRight, Target, FolderKanban, ListTodo,
  Plus, Layers, Loader2, RefreshCw, Trash2, Pencil, GitBranch, User, Network,
} from 'lucide-react'
import { getAgentName } from '@/shared/utils/agentMap'

// ============================================================================
// Types
// ============================================================================

/** Generic tree item used by DecompositionView */
export interface DecompTreeItem {
  id: string
  type: 'goal' | 'project' | 'task'
  name: string
  description?: string
  status: string
  priority?: string
  assigned_agent?: string
  children?: DecompTreeItem[]
  _data?: Record<string, any>
}

/** Callbacks for CRUD operations (optional → read-only mode) */
export interface DecompCallbacks {
  onCreateProject?: () => void
  onCreateTask?: (projectId: string) => void
  onEdit?: (item: DecompTreeItem) => void
  onDelete?: (id: string, type: 'project' | 'task') => void
  onRefresh?: () => void
  onEditDependsOn?: (item: DecompTreeItem) => void
}

// ============================================================================
// Status helpers (shared with GoalDecomposePage)
// ============================================================================

export function getStatusBadge(status: string): { variant: 'info' | 'success' | 'secondary' | 'destructive' | 'default' | 'warning' | 'outline'; label: string } {
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

export function getPriorityBadge(priority?: string): { label: string; color: string } {
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
// Tree Node Component
// ============================================================================

function DecompTreeNode({
  node, depth, collapsed, onToggle, callbacks, showExecutor = true,
}: {
  node: DecompTreeItem; depth: number;
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  callbacks: DecompCallbacks;
  showExecutor?: boolean;
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
        {showExecutor && node.type === 'task' && node.assigned_agent !== undefined && (
          node.assigned_agent ? (
            <span className="flex items-center gap-1 text-[10px] text-slate-500 shrink-0">
              <User className="w-3 h-3" /> {getAgentName(node.assigned_agent)}
            </span>
          ) : (
            <span className="text-[10px] text-amber-600 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded shrink-0">
              待分配
            </span>
          )
        )}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          {node.type === 'goal' && callbacks.onCreateProject && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); callbacks.onCreateProject!(); }}>
              <Plus className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'project' && callbacks.onCreateTask && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); callbacks.onCreateTask!(node.id); }}>
              <Plus className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'project' && callbacks.onEdit && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); callbacks.onEdit!(node); }} title="编辑工程">
              <Pencil className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'project' && callbacks.onDelete && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={e => { e.stopPropagation(); callbacks.onDelete!(node.id, 'project'); }} title="删除工程">
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'task' && callbacks.onEdit && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); callbacks.onEdit!(node); }} title="编辑任务">
              <Pencil className="w-3 h-3" />
            </Button>
          )}
          {node.type === 'task' && callbacks.onDelete && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={e => { e.stopPropagation(); callbacks.onDelete!(node.id, 'task'); }} title="删除任务">
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
          {node.type !== 'goal' && callbacks.onEditDependsOn && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={e => { e.stopPropagation(); callbacks.onEditDependsOn!(node); }} title="编辑依赖">
              <Layers className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>
      {hasChildren && !isCollapsed && node.children!.map(child => (
        <DecompTreeNode key={child.id} node={child} depth={depth + 1}
          collapsed={collapsed} onToggle={onToggle} callbacks={callbacks} />
      ))}
    </div>
  )
}

// ============================================================================
// DAG Node Component (ReactFlow)
// ============================================================================

function DecompDagNode({ data, showExecutor = true }: { data: any; showExecutor?: boolean }) {
  const nodeType = data.type
  const statusInfo = getStatusBadge(data.status)
  const assignedName = data.assigned_agent ? getAgentName(data.assigned_agent) : null

  const iconConfig: Record<string, { icon: React.ReactNode; color: string; bg: string; border: string; badgeBg: string }> = {
    goal: {
      icon: <Target className="w-3.5 h-3.5" />,
      color: 'text-purple-700', bg: '#f5f3ff', border: '2px solid #a78bfa', badgeBg: 'bg-purple-100 text-purple-700',
    },
    project: {
      icon: <FolderKanban className="w-3.5 h-3.5" />,
      color: 'text-emerald-700', bg: data.status === 'completed' || data.status === 'done' ? '#dcfce7' : data.status === 'active' || data.status === 'in_progress' ? '#dbeafe' : '#f3f4f6',
      border: `2px solid ${data.status === 'completed' ? '#22c55e' : data.status === 'active' ? '#3b82f6' : '#d1d5db'}`,
      badgeBg: data.status === 'completed' || data.status === 'done' ? 'bg-green-100 text-green-700' : data.status === 'active' || data.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600',
    },
    task: {
      icon: <ListTodo className="w-3.5 h-3.5" />,
      color: 'text-blue-700', bg: data.status === 'done' || data.status === 'completed' ? '#f0fdf4' : data.status === 'in_progress' ? '#eff6ff' : '#fafafa',
      border: `1px solid ${data.status === 'done' ? '#86efac' : data.status === 'in_progress' ? '#93c5fd' : '#e5e7eb'}`,
      badgeBg: data.status === 'done' || data.status === 'completed' ? 'bg-green-100 text-green-700' : data.status === 'in_progress' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600',
    },
  }

  const cfg = iconConfig[nodeType] || iconConfig.task

  return (
    <div
      style={{
        background: cfg.bg,
        border: cfg.border,
        borderRadius: nodeType === 'goal' ? '10px' : nodeType === 'project' ? '8px' : '6px',
        padding: nodeType === 'goal' ? '10px 14px' : '7px 10px',
        minWidth: nodeType === 'goal' ? '180px' : nodeType === 'project' ? '160px' : '130px',
        maxWidth: '240px',
        fontSize: nodeType === 'goal' ? '13px' : '11px',
        fontWeight: nodeType === 'goal' ? '700' : nodeType === 'project' ? '600' : '500',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        position: 'relative',
      }}
    >
      <Handle type="source" position={Position.Right} style={{ background: '#94a3b8', width: 8, height: 8 }} />
      <Handle type="target" position={Position.Left} style={{ background: '#94a3b8', width: 8, height: 8 }} />
      <div className="flex items-center gap-1.5 mb-1">
        <span className={cfg.color}>{cfg.icon}</span>
        <span className={`text-[9px] font-medium px-1 py-0 rounded ${cfg.badgeBg}`}>
          {nodeType === 'goal' ? '目标' : nodeType === 'project' ? '工程' : '任务'}
        </span>
        <span className="text-[9px] text-slate-500 ml-auto">{statusInfo.label}</span>
      </div>
      <div className={`font-medium truncate ${cfg.color}`} style={{ fontSize: nodeType === 'goal' ? '13px' : '11px' }}>
        {data.label}
      </div>
      {showExecutor && nodeType === 'task' && (
        assignedName ? (
          <div className="flex items-center gap-1 mt-1 text-[10px] text-slate-500">
            <User className="w-2.5 h-2.5" />
            <span>{assignedName}</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 mt-1 text-[10px] text-amber-600">
            <User className="w-2.5 h-2.5" />
            <span>待分配</span>
          </div>
        )
      )}
    </div>
  )
}

const dagNodeTypes = (showExecutor: boolean) => ({ dagNode: (props: any) => <DecompDagNode {...props} showExecutor={showExecutor} /> })

// ============================================================================
// DAG View Component
// ============================================================================

interface DagNodeData {
  id: string
  type: 'dagNode'
  position: { x: number; y: number }
  sourcePosition: typeof Position.Right
  targetPosition: typeof Position.Left
  data: { label: string; type: string; status: string; assigned_agent?: string }
}

interface DagEdgeData {
  id: string
  source: string
  target: string
  sourcePosition: typeof Position.Right
  targetPosition: typeof Position.Left
  animated: boolean
  markerEnd: { type: typeof MarkerType.ArrowClosed }
  style: { stroke: string; strokeWidth: number; strokeDasharray?: string }
}

function DecompDagView({
  rootName,
  rootStatus,
  rootId,
  projects,
  tasks,
  dagLayoutKey,
  showExecutor = true,
}: {
  rootName: string
  rootStatus: string
  rootId: string
  projects: Array<{ id: string; name: string; status: string; next_step?: string[] }>
  tasks: Array<{ id: string; title: string; status: string; project_id: string; assigned_agent?: string; next_step?: string[] }>
  dagLayoutKey: number
  showExecutor?: boolean
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([])

  const dagData = useMemo(() => {
    const allNodes: DagNodeData[] = []
    const allEdges: DagEdgeData[] = []

    // Root node
    allNodes.push({
      id: rootId,
      type: 'dagNode',
      position: { x: 0, y: 0 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: { label: rootName, type: 'goal', status: rootStatus },
    })

    // Project nodes
    projects.forEach(p => {
      allNodes.push({
        id: p.id,
        type: 'dagNode',
        position: { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: p.name, type: 'project', status: p.status },
      })
    })

    // Project dependency edges
    projects.forEach(p => {
      const nextSteps = p.next_step || []
      nextSteps.forEach((nextId: string) => {
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

    // Root → root projects
    if (projects.length > 0) {
      const targetedProjects = new Set<string>()
      projects.forEach(p => {
        (p.next_step || []).forEach((nid: string) => targetedProjects.add(nid))
      })
      projects.forEach(p => {
        if (!targetedProjects.has(p.id)) {
          allEdges.push({
            id: `edge-root-${p.id}`,
            source: rootId,
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
        type: 'dagNode',
        position: { x: 0, y: 0 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: t.title, type: 'task', status: t.status, assigned_agent: t.assigned_agent || undefined },
      })
    })

    // Task dependency edges
    tasks.forEach(t => {
      const nextSteps = t.next_step || []
      nextSteps.forEach((nextId: string) => {
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

    // Project → root tasks
    projects.forEach(p => {
      const projTasks = tasks.filter(t => t.project_id === p.id)
      const targetedTasks = new Set<string>()
      projTasks.forEach(t => {
        (t.next_step || []).forEach((nid: string) => targetedTasks.add(nid))
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

    return { nodes: allNodes, edges: allEdges }
  }, [projects, tasks, dagLayoutKey, rootId, rootName, rootStatus])

  // Auto-layout
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
        layer[neighbor] = Math.max(layer[neighbor] || 0, layer[current] + 1)
        if (inDeg[neighbor] === 0) {
          queue.push(neighbor)
        }
      }
    }

    dagData.nodes.forEach(n => {
      if (layer[n.id] === undefined) layer[n.id] = 0
    })

    const layers: Record<number, string[]> = {}
    dagData.nodes.forEach(n => {
      const l = layer[n.id]
      if (!layers[l]) layers[l] = []
      layers[l].push(n.id)
    })

    const priorityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }
    Object.keys(layers).forEach(lKey => {
      const l = parseInt(lKey)
      layers[l].sort((a, b) => {
        const na = nodeMap[a]?.data?.label || ''
        const nb = nodeMap[b]?.data?.label || ''
        const pa = priorityOrder[nodeMap[a]?.data?.priority || ''] ?? 99
        const pb = priorityOrder[nodeMap[b]?.data?.priority || ''] ?? 99
        if (pa !== pb) return pa - pb
        return na.localeCompare(nb)
      })
    })

    const NODE_W = 200, NODE_H = 80, GAP_X = 80, GAP_Y = 20
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

  const reactFlowInstanceRef = useRef<any>(null)
  useEffect(() => {
    if (nodes.length > 0 && reactFlowInstanceRef.current) {
      const timer = setTimeout(() => {
        reactFlowInstanceRef.current.fitView({ padding: 0.2, duration: 200 })
      }, 150)
      return () => clearTimeout(timer)
    }
  }, [nodes.length])

  // Always render ReactFlow - root node is always present in DAG

  return (
    <ReactFlowProvider>
      <ReactFlow
        nodes={nodes} edges={edges}
        nodeTypes={dagNodeTypes(showExecutor)}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onInit={(instance) => { reactFlowInstanceRef.current = instance }}
        minZoom={0.1} maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        elementsSelectable={false}
        defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed } }}
      >
        <Background color="#e2e8f0" gap={16} size={1} />
        <Controls className="!bg-white !shadow-md !rounded-lg" />
        <MiniMap className="!bg-white/90 !rounded-lg !shadow-md" maskColor="rgba(248,250,252,0.5)" />
      </ReactFlow>
    </ReactFlowProvider>
  )
}

// ============================================================================
// Main DecompositionView Component
// ============================================================================

export interface DecompositionViewProps {
  /** Root node info */
  root: { id: string; name: string; status: string; description?: string }
  /** Tree data */
  tree: DecompTreeItem[]
  /** Flattened projects for DAG */
  projects: Array<{ id: string; name: string; status: string; next_step?: string[] }>
  /** Flattened tasks for DAG */
  tasks: Array<{ id: string; title: string; status: string; project_id: string; assigned_agent?: string; next_step?: string[] }>
  /** Stats */
  stats?: { projectCount: number; taskCount: number }
  /** Legend label for root type */
  rootTypeLabel?: string
  /** Callbacks (omit for read-only mode) */
  callbacks?: DecompCallbacks
  /** Whether to show executor info (default: true for goals, false for scenarios) */
  showExecutor?: boolean
  // HMR trigger
  /** Loading state */
  loading?: boolean
  /** Error state */
  error?: string | null
  /** Retry handler */
  onRetry?: () => void
}

export default function DecompositionView({
  root, tree, projects, tasks, stats,
  rootTypeLabel = '目标',
  callbacks, showExecutor = true, loading, error, onRetry,
}: DecompositionViewProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [dagLayoutKey, setDagLayoutKey] = useState(0)
  const [panelLayout, setPanelLayout] = useState<'tree' | 'split' | 'dag'>('split')

  useEffect(() => {
    if (tree.length > 0) setCollapsed(new Set())
  }, [tree])

  function toggleCollapse(id: string) {
    setCollapsed(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

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
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          {onRetry && <Button onClick={onRetry}>重试</Button>}
        </div>
      </div>
    )
  }

  const projectCount = stats?.projectCount ?? projects.length
  const taskCount = stats?.taskCount ?? tasks.length

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span>{projectCount} 个项目</span>
        <span>·</span>
        <span>{taskCount} 个任务</span>
      </div>

      {/* Legend + Toggle */}
      <div className="flex items-center justify-between bg-white rounded-lg border border-slate-200 px-4 py-2">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="font-medium text-slate-700">图例:</span>
          <span className="flex items-center gap-1">
            <Target className="w-3.5 h-3.5 text-purple-500" /> {rootTypeLabel}
          </span>
          <span className="flex items-center gap-1">
            <FolderKanban className="w-3.5 h-3.5 text-emerald-500" /> 工程
          </span>
          <span className="flex items-center gap-1">
            <ListTodo className="w-3.5 h-3.5 text-blue-500" /> 任务
          </span>
          <span className="border-l border-slate-200 h-4" />
          {showExecutor && (
            <>
              <span className="flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-slate-500" /> 执行者
              </span>
              <span className="flex items-center gap-1 text-amber-600">
                <User className="w-3.5 h-3.5" /> 待分配
              </span>
            </>
          )}
        </div>
        <ToggleGroup value={panelLayout} onValueChange={(v) => setPanelLayout(v as 'tree' | 'split' | 'dag')} className="shrink-0">
          <ToggleGroupItem value="split" className="h-7 px-2.5 text-xs gap-1">
            <Layers className="w-3.5 h-3.5" />
            <span>全部</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="tree" className="h-7 px-2.5 text-xs gap-1">
            <GitBranch className="w-3.5 h-3.5" />
            <span>树</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="dag" className="h-7 px-2.5 text-xs gap-1">
            <Network className="w-3.5 h-3.5" />
            <span>图</span>
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Main Layout */}
      <div className="flex gap-2" style={{ minHeight: '70vh' }}>
        {/* Tree */}
        {(panelLayout === 'tree' || panelLayout === 'split') && (
          <Card className="overflow-hidden flex flex-col" style={{ width: panelLayout === 'split' ? '45%' : '100%' }}>
            <CardHeader className="pb-2 shrink-0">
              <CardTitle className="text-sm flex items-center gap-2">
                <ListTodo className="w-4 h-4" />
                分解树
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex-1 overflow-hidden">
              <div className="px-2 py-2 h-full overflow-y-auto">
                {tree.length === 0 ? (
                  <div>
                    <DecompTreeNode
                      key={root.id}
                      node={root as DecompTreeItem}
                      depth={0}
                      collapsed={collapsed}
                      onToggle={toggleCollapse}
                      callbacks={callbacks || {}}
                      showExecutor={showExecutor}
                    />
                    <div className="ml-10 pl-4 border-l-2 border-dashed border-muted-foreground/20 my-2">
                      <p className="text-muted-foreground text-xs py-1">暂无分解数据</p>
                      {callbacks?.onCreateProject && (
                        <Button variant="outline" size="sm" className="h-7 text-xs mb-2" onClick={callbacks.onCreateProject}>
                          <Plus className="w-3 h-3 mr-1" /> 创建第一个工程
                        </Button>
                      )}
                    </div>
                  </div>
                ) : (
                  tree.map(node => (
                    <DecompTreeNode key={node.id} node={node} depth={0}
                      collapsed={collapsed} onToggle={toggleCollapse}
                      callbacks={callbacks || {}} showExecutor={showExecutor} />
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* DAG */}
        {(panelLayout === 'dag' || panelLayout === 'split') && (
          <Card className="overflow-hidden flex flex-col" style={{ width: panelLayout === 'split' ? '55%' : '100%' }}>
            <CardHeader className="pb-2 shrink-0 flex-row items-center justify-between space-y-0">
              <CardTitle className="text-sm flex items-center gap-2">
                <Layers className="w-4 h-4" />
                依赖关系图 (DAG)
              </CardTitle>
              <Button variant="outline" size="sm" onClick={() => setDagLayoutKey(k => k + 1)} title="重新布局 DAG">
                <GitBranch className="w-3.5 h-3.5 mr-1" /> 重新排列
              </Button>
            </CardHeader>
            <CardContent className="p-0 flex-1 overflow-hidden" style={{ minHeight: '60vh' }}>
              <DecompDagView
                rootName={root.name}
                rootStatus={root.status}
                rootId={root.id}
                projects={projects}
                tasks={tasks}
                dagLayoutKey={dagLayoutKey}
                showExecutor={showExecutor}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
