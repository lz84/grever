import React, { useState, useEffect, useCallback, useRef } from 'react';
import { WORKFLOWS, PROJECTS } from '../../shared/api/paths';
import { useParams, useNavigate } from 'react-router-dom';
import {
  MiniMap, Controls, Background, ReactFlow,
  useNodesState, useEdgesState,
  MarkerType, Connection, Edge, Node, Handle, Position,
  applyNodeChanges, applyEdgeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Textarea } from '@/shared/components/ui/textarea';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from '@/shared/components/ui/alert-dialog';
import {
  Plus, Trash2, Save, RefreshCw, Play, MessageSquare,
  RotateCcw, ArrowLeft,
} from 'lucide-react';

import { workflowsApi, request } from '@/shared/utils/api';

// ============================================================================
// Color palette for visual impact
// ============================================================================
const PHASE_COLORS = [
  { bg: 'bg-red-50', border: 'border-red-400', accent: '#ef4444', icon: '🔴' },
  { bg: 'bg-orange-50', border: 'border-orange-400', accent: '#f97316', icon: '🟠' },
  { bg: 'bg-yellow-50', border: 'border-yellow-400', accent: '#eab308', icon: '🟡' },
  { bg: 'bg-green-50', border: 'border-green-400', accent: '#22c55e', icon: '🟢' },
  { bg: 'bg-blue-50', border: 'border-blue-400', accent: '#3b82f6', icon: '🔵' },
  { bg: 'bg-purple-50', border: 'border-purple-400', accent: '#a855f7', icon: '🟣' },
];

// ============================================================================
// Node Types
// ============================================================================

interface WorkflowNodeData extends Record<string, unknown> {
  id: string;
  title: string;
  description: string;
  type: string;
  status: string;
  assignee?: string;
  phaseIndex?: number;
  onDrillDown?: (projectId: string) => void;
}

const WorkflowNodeComponent = ({ data }: { data: WorkflowNodeData }) => {
  const phaseIdx = (data.phaseIndex ?? 0) as number;
  const color = PHASE_COLORS[phaseIdx] || PHASE_COLORS[0];

  const statusBadgeMap: Record<string, { label: string; variant: string }> = {
    'completed': { label: '已完成', variant: 'success' },
    'done': { label: '已完成', variant: 'success' },
    'running': { label: '进行中', variant: 'info' },
    'in_progress': { label: '进行中', variant: 'info' },
    'active': { label: '进行中', variant: 'info' },
    'verifying': { label: '验证中', variant: 'warning' },
    'reviewing': { label: '验证中', variant: 'warning' },
    'review_needed': { label: '待审核', variant: 'warning' },
    'disputed': { label: '待审核', variant: 'warning' },
    'confirmed': { label: '已确认', variant: 'info' },
    'pending': { label: '待执行', variant: 'secondary' },
    'todo': { label: '待执行', variant: 'secondary' },
    'failed': { label: '失败', variant: 'destructive' },
    'blocked': { label: '阻塞', variant: 'destructive' },
    'draft': { label: '草稿', variant: 'secondary' },
  };
  const statusInfo = statusBadgeMap[data.status] || { label: data.status || '待执行', variant: 'secondary' };

  const nodeIcons: Record<string, string> = {
    execution: '▶', task: '▶', notification: '✉', decision: '◆',
    parallel: '⫕', milestone: '★', start: '🚀', end: '🏁',
  };

  const projectId = data.projectId as string | undefined;
  const onDrillDown = data.onDrillDown as ((projectId: string) => void) | undefined;

  return (
    <div className={`relative rounded-2xl border-2 shadow-xl ${color.border} ${color.bg} overflow-hidden`}
         style={{ minWidth: 280, minHeight: 120 }}>
      <div className="h-1.5 w-full" style={{ backgroundColor: color.accent }} />
      <Handle type="target" position={Position.Left}
              className="w-3 h-3 !bg-gray-400 border-2 border-white" />
      <div className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                style={{ backgroundColor: color.accent }}>
            阶段 {phaseIdx + 1}
          </span>
          <span className="text-sm font-mono text-gray-400">{data.id}</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">{nodeIcons[data.type] || '▶'}</span>
          <span className="text-base font-bold text-gray-900 leading-tight">{data.title}</span>
        </div>
        {data.description && (
          <p className="text-xs text-gray-600 leading-relaxed mb-3"
             style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {data.description}
          </p>
        )}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200/60">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
            <span className="text-xs font-medium text-gray-600">{statusInfo.label}</span>
          </div>
          <span className="text-xs text-gray-400 uppercase tracking-wider">{data.type}</span>
        </div>
        {data.assignee && (
          <div className="text-xs text-gray-500 mt-2 flex items-center gap-1">
            <span>👤</span> {data.assignee}
          </div>
        )}
        
        {projectId && onDrillDown && (
          <div className="mt-3 pt-2 border-t border-gray-200/60">
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.nativeEvent.stopImmediatePropagation();
                onDrillDown(projectId);
              }}
              onMouseDown={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
              className="w-full text-xs bg-blue-500 hover:bg-blue-600 text-white py-1.5 rounded-lg transition-colors flex items-center justify-center gap-1 cursor-pointer"
              style={{ pointerEvents: 'auto' }}
            >
              <span>🔍</span>
              <span>打开工程流程</span>
            </button>
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right}
              className="w-3 h-3 !bg-gray-400 border-2 border-white" />
    </div>
  );
};

const nodeTypes = { workflowNode: WorkflowNodeComponent };

// ============================================================================
// Auto-layout
// ============================================================================

function autoLayout(nodes: any[], edges: any[]) {
  if (nodes.length === 0) return { nodes: [], edges: [] };
  const adj: Record<string, string[]> = {};
  const inDeg: Record<string, number> = {};
  const nodeMap: Record<string, any> = {};
  nodes.forEach((n) => { adj[n.id] = []; inDeg[n.id] = 0; nodeMap[n.id] = n; });
  edges.forEach((e) => { if (adj[e.source]) adj[e.source].push(e.target); if (inDeg[e.target] !== undefined) inDeg[e.target]++; });
  const queue: string[] = [];
  const layer: Record<string, number> = {};
  Object.keys(inDeg).forEach((id) => { if (inDeg[id] === 0) { queue.push(id); layer[id] = 0; } });
  const sorted: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    sorted.push(current);
    for (const neighbor of adj[current]) { inDeg[neighbor]--; if (inDeg[neighbor] === 0) { layer[neighbor] = layer[current] + 1; queue.push(neighbor); } }
  }
  if (sorted.length < nodes.length) nodes.forEach((n, i) => { layer[n.id] = Math.floor(i / 3); });
  const layers: Record<number, string[]> = {};
  sorted.forEach((id) => { const l = layer[id]; if (!layers[l]) layers[l] = []; layers[l].push(id); });
  const NODE_W = 300, NODE_H = 150, GAP_X = 80, GAP_Y = 60;
  const positioned: any[] = [];
  const layerKeys = Object.keys(layers).map(Number).sort((a, b) => a - b);
  layerKeys.forEach((l, li) => {
    const layerNodes = layers[l];
    const maxInLayer = Math.max(1, layerNodes.length);
    const totalH = maxInLayer * (NODE_H + GAP_Y) - GAP_Y;
    const startY = 80 + (Math.max(0, (4 - maxInLayer) * (NODE_H + GAP_Y))) / 2;
    layerNodes.forEach((id, ni) => {
      const orig = nodeMap[id];
      positioned.push({ ...orig, data: { ...orig.data, phaseIndex: li }, position: { x: 80 + li * (NODE_W + GAP_X), y: startY + ni * (NODE_H + GAP_Y) } });
    });
  });
  return { nodes: positioned, edges };
}

// ============================================================================
// Stats panel
// ============================================================================

function StatsPanel({ nodes, edges, workflowName, progressData }: {
  nodes: any[]; edges: any[]; workflowName: string; progressData?: any;
}) {
  const completed = nodes.filter((n) => n.data?.status === 'completed' || n.data?.status === 'done').length;
  const pending = nodes.filter((n) => n.data?.status === 'pending').length;
  const inProgress = nodes.filter((n) => n.data?.status === 'running' || n.data?.status === 'in_progress' || n.data?.status === 'active').length;
  const progress = progressData?.progress_percent ?? (nodes.length > 0 ? Math.round((completed / nodes.length) * 100) : 0);
  return (
    <Card className="absolute top-4 right-4 w-[260px] z-30 shadow-2xl">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <span className="text-lg">📊</span> 流程概览
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1"><span>总进度</span><span className="font-bold text-slate-800">{progress}%</span></div>
          <div className="w-full bg-slate-200 rounded-full h-2.5">
            <div className="h-2.5 rounded-full bg-gradient-to-r from-blue-500 to-green-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-green-50 rounded-xl p-2"><div className="text-lg font-bold text-green-600">{completed}</div><div className="text-[10px] text-green-500">已完成</div></div>
          <div className="bg-blue-50 rounded-xl p-2"><div className="text-lg font-bold text-blue-600">{inProgress}</div><div className="text-[10px] text-blue-500">进行中</div></div>
          <div className="bg-yellow-50 rounded-xl p-2"><div className="text-lg font-bold text-yellow-600">{pending}</div><div className="text-[10px] text-yellow-500">待执行</div></div>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-100">
          <div className="flex justify-between text-xs text-slate-500"><span>节点总数</span><span className="font-semibold text-slate-700">{nodes.length}</span></div>
          <div className="flex justify-between text-xs text-slate-500 mt-1"><span>连接关系</span><span className="font-semibold text-slate-700">{edges.length}</span></div>
        </div>
        {progressData && progressData.steps && (
          <div className="mt-2 pt-2 border-t border-slate-100">
            <div className="text-xs font-semibold text-slate-600 mb-1">步骤状态</div>
            {progressData.steps.slice(0, 5).map((s: any, i: number) => (
              <div key={i} className="flex justify-between text-xs text-slate-500 py-0.5">
                <span className="truncate">{s.name}</span>
                <Badge variant={s.status === 'completed' ? 'success' : s.status === 'running' ? 'info' : 'secondary'} className="text-[10px] px-1.5">{s.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Legend panel
// ============================================================================

function LegendPanel() {
  const items = [
    { color: '#ef4444', label: '应急响应' }, { color: '#f97316', label: '专家研判' },
    { color: '#eab308', label: '综合抢险' }, { color: '#22c55e', label: '物资调度' },
    { color: '#3b82f6', label: '次生防范' }, { color: '#a855f7', label: '灾后重建' },
  ];
  return (
    <Card className="absolute bottom-4 left-4 w-auto z-30 shadow-xl">
      <CardContent className="p-3">
        <div className="text-xs font-bold text-slate-600 mb-2">阶段颜色</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-[10px] text-slate-500">{item.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Add/Edit Node Dialog
// ============================================================================

interface NodeFormData {
  id: string;
  name: string;
  title: string;
  description: string;
  type: string;
  status: string;
  assignee?: string;
}

function NodeDialog({
  open,
  onOpenChange,
  onSubmit,
  initialData,
  existingNodeIds,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSubmit: (data: NodeFormData) => void;
  initialData?: Node;
  existingNodeIds: string[];
}) {
  const isEdit = !!initialData;
  const [form, setForm] = useState<NodeFormData>({
    id: '', name: '', title: '', description: '', type: 'task', status: 'pending', assignee: '',
  });

  useEffect(() => {
    if (initialData) {
      setForm({
        id: initialData.id,
        name: (initialData.data as any)?.name || '',
        title: (initialData.data as any)?.title || '',
        description: (initialData.data as any)?.description || '',
        type: (initialData.data as any)?.type || 'task',
        status: (initialData.data as any)?.status || 'pending',
        assignee: (initialData.data as any)?.assignee || '',
      });
    } else {
      setForm({
        id: `node_${Date.now()}`,
        name: '', title: '', description: '', type: 'task', status: 'pending', assignee: '',
      });
    }
  }, [initialData, open]);

  const handleGenerateId = () => {
    setForm(f => ({ ...f, id: `node_${Date.now()}` }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    onSubmit(form);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEdit ? '编辑节点' : '添加节点'}</DialogTitle>
          <DialogDescription>
            {isEdit ? '修改节点的属性' : '填写新节点的信息'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-[100px_1fr_auto] gap-2 items-center">
            <label className="text-sm font-medium">节点 ID</label>
            <Input
              value={form.id}
              onChange={e => setForm(f => ({ ...f, id: e.target.value }))}
              disabled={isEdit}
              placeholder="node_xxx"
            />
            {!isEdit && (
              <Button type="button" variant="outline" size="sm" onClick={handleGenerateId}>
                <RefreshCw className="w-3 h-3 mr-1" /> 生成
              </Button>
            )}
          </div>
          <div className="grid grid-cols-[100px_1fr] gap-2 items-center">
            <label className="text-sm font-medium">名称</label>
            <Input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="节点名称"
              required
            />
          </div>
          <div className="grid grid-cols-[100px_1fr] gap-2 items-center">
            <label className="text-sm font-medium">标题</label>
            <Input
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="显示标题"
            />
          </div>
          <div className="grid grid-cols-[100px_1fr] gap-2 items-start">
            <label className="text-sm font-medium pt-2">描述</label>
            <Textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="节点描述..."
              rows={2}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid grid-cols-[70px_1fr] gap-2 items-center">
              <label className="text-sm font-medium">类型</label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={form.type}
                onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
              >
                <option value="task">task</option>
                <option value="decision">decision</option>
                <option value="notification">notification</option>
                <option value="parallel">parallel</option>
                <option value="milestone">milestone</option>
                <option value="start">start</option>
                <option value="end">end</option>
              </select>
            </div>
            <div className="grid grid-cols-[70px_1fr] gap-2 items-center">
              <label className="text-sm font-medium">状态</label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={form.status}
                onChange={e => setForm(f => ({ ...f, status: e.target.value }))}
              >
                <option value="pending">pending</option>
                <option value="running">running</option>
                <option value="completed">completed</option>
                <option value="failed">failed</option>
                <option value="draft">draft</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-[100px_1fr] gap-2 items-center">
            <label className="text-sm font-medium">负责人</label>
            <Input
              value={form.assignee}
              onChange={e => setForm(f => ({ ...f, assignee: e.target.value }))}
              placeholder="可选"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button type="submit">{isEdit ? '保存修改' : '添加节点'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Main Component
// ============================================================================

interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  pendingAction?: any;
  confidence?: number;
}

export default function WorkflowDiagram() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [rawNodes, setRawNodes] = useNodesState<any>([]);
  const [rawEdges, setRawEdges] = useEdgesState<any>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [selectedNode, setSelectedNode] = useState<Node<WorkflowNodeData> | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [splitSaving, setSplitSaving] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);

  // DAG edit states
  const [addNodeOpen, setAddNodeOpen] = useState(false);
  const [editNodeOpen, setEditNodeOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'node' | 'edge'; node?: Node; edge?: Edge } | null>(null);
  const [progressData, setProgressData] = useState<any>(null);

  useEffect(() => {
    if (!id) return;

    const fetchProjects = async () => {
      try {
        const workflowData = await workflowsApi.get(id);
        const goalId = (workflowData as any).goal_id;
        if (!goalId) return;
        const projectsData = await request<any[]>(`/projects`, { params: { goal_id: goalId } });
        if (Array.isArray(projectsData)) setProjects(projectsData);
        else if (projectsData && 'projects' in projectsData) setProjects((projectsData as any).projects);
      } catch (err) {
        console.error('Failed to fetch projects for workflow:', err);
      }
    };

    fetchProjects();
  }, [id]);

  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatThinking, setChatThinking] = useState(false);
  const [pendingAction, setPendingAction] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [lastConfidence, setLastConfidence] = useState(0);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const editable = workflowStatus === 'draft' || workflowStatus === 'paused';
  const isDraft = workflowStatus === 'draft';
  const canSplit = editMode && isDraft;

  // Load progress data
  const fetchProgress = useCallback(async () => {
    if (!id) return;
    try {
      const data = await workflowsApi.getProgress(id);
      setProgressData(data);
    } catch {
      // silently ignore
    }
  }, [id]);

  const fetchDiagram = useCallback(async () => {
    if (!id) { setError('Workflow ID is missing'); setLoading(false); return; }
    try {
      setLoading(true);
      const data = await workflowsApi.getDiagram(id);
      setWorkflowName(data.name);
      setWorkflowStatus(data.status);

      const projMap: Record<string, string> = {};
      if (projects && projects.length > 0) {
        projects.forEach((p: any) => { if (p.name) projMap[p.name] = p.id; });
      }

      const flowNodes = data.nodes.map((n: any) => {
        const nodeTitle = n.name || n.title || '';
        let projectId = projMap[nodeTitle];
        if (!projectId) {
          for (const [projName, projId] of Object.entries(projMap)) {
            if (projName.includes(nodeTitle) || nodeTitle.includes(projName)) {
              projectId = projId;
              break;
            }
          }
        }
        return {
          id: n.id, type: 'workflowNode', position: { x: 0, y: 0 },
          data: { ...n, projectId, onDrillDown: (pid: string) => navigate(`/coordination/projects/${pid}?tab=diagram`) }
        };
      });
      const flowEdges = (data.edges || []).map((e: any) => ({
        id: e.id || `${e.source}-${e.target}`, source: e.source, target: e.target,
        label: e.label, animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#94a3b8', strokeWidth: 2 },
        labelStyle: { fill: '#64748b', fontWeight: 500, fontSize: 11 },
        labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.8 },
      }));
      const { nodes: layoutNodes, edges: layoutEdges } = autoLayout(flowNodes, flowEdges);
      setRawNodes(layoutNodes);
      setRawEdges(layoutEdges);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [id, projects, navigate, setRawNodes, setRawEdges]);

  useEffect(() => { fetchDiagram(); }, [fetchDiagram]);

  useEffect(() => {
    if (!projects || projects.length === 0 || rawNodes.length === 0) return;
    const projMap: Record<string, string> = {};
    projects.forEach((p: any) => { if (p.name) projMap[p.name] = p.id; });

    const updated = rawNodes.map(node => {
      const nodeTitle = (node.data as any)?.name || (node.data as any)?.title || '';
      let projectId = projMap[nodeTitle];
      if (!projectId) {
        for (const [projName, projId] of Object.entries(projMap)) {
          if (projName.includes(nodeTitle) || nodeTitle.includes(projName)) {
            projectId = projId;
            break;
          }
        }
      }
      if (projectId && (node.data as any).projectId !== projectId) {
        return { ...node, data: { ...(node.data as object), projectId, onDrillDown: (pid: string) => navigate(`/coordination/projects/${pid}?tab=diagram`) } };
      }
      return node;
    });

    const hasChanges = updated.some((n, i) => n !== rawNodes[i]);
    if (hasChanges) {
      setRawNodes(updated);
    }
  }, [projects, rawNodes, navigate, setRawNodes]);

  // Load progress periodically
  useEffect(() => {
    fetchProgress();
    const interval = setInterval(fetchProgress, 10000);
    return () => clearInterval(interval);
  }, [fetchProgress]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatMessages]);

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  // ========================================================================
  // API: Add Node
  // ========================================================================
  const handleAddNode = async (data: NodeFormData) => {
    if (!id) return;
    try {
      setSaving(true);
      const nodePayload = {
        id: data.id,
        name: data.name,
        title: data.title || data.name,
        description: data.description,
        type: data.type,
        status: data.status,
        assignee: data.assignee || undefined,
      };
      await workflowsApi.addNode(id, nodePayload);
      showToast('✅ 节点已添加');
      setAddNodeOpen(false);
      await fetchDiagram();
    } catch (err: any) {
      showToast(`❌ 添加失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // ========================================================================
  // API: Update Node
  // ========================================================================
  const handleUpdateNode = async (data: NodeFormData) => {
    if (!id || !selectedNode) return;
    try {
      setSaving(true);
      const nodePayload = {
        id: data.id,
        name: data.name,
        title: data.title || data.name,
        description: data.description,
        type: data.type,
        status: data.status,
        assignee: data.assignee || undefined,
      };
      await workflowsApi.updateNode(id, selectedNode.id, nodePayload);
      showToast('✅ 节点已更新');
      setEditNodeOpen(false);
      setSelectedNode(null);
      await fetchDiagram();
    } catch (err: any) {
      showToast(`❌ 更新失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // ========================================================================
  // API: Delete Node
  // ========================================================================
  const handleDeleteNode = async (nodeId: string) => {
    if (!id) return;
    try {
      setSaving(true);
      await workflowsApi.deleteNode(id, nodeId);
      showToast('✅ 节点已删除');
      await fetchDiagram();
    } catch (err: any) {
      showToast(`❌ 删除失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // ========================================================================
  // API: Add Edge (via connect)
  // ========================================================================
  const onConnect = useCallback(async (params: Connection | Edge) => {
    if (!editMode || !editable) return;
    try {
      setSaving(true);
      const data = await workflowsApi.addEdge(id!, params.source, params.target);
      const flowEdges = data.dag.edges.map((e: any) => ({
        id: e.id || `${e.source}-${e.target}`, source: e.source || e.from, target: e.target || e.to,
        label: e.label || '', animated: true, markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#94a3b8', strokeWidth: 2 },
      }));
      setRawEdges(flowEdges);
      showToast('✅ 边已添加');
    } catch (err: any) {
      showToast(`❌ ${err.message}`);
    } finally {
      setSaving(false);
    }
  }, [editMode, editable, id, setRawEdges]);

  // ========================================================================
  // API: Delete Edge (via double-click)
  // ========================================================================
  const handleDeleteEdge = async (source: string, target: string) => {
    if (!id) return;
    try {
      setSaving(true);
      await workflowsApi.deleteEdge(id, source, target);
      showToast('✅ 边已删除');
      await fetchDiagram();
    } catch (err: any) {
      showToast(`❌ 删除边失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const onEdgeDoubleClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    if (!editMode || !editable) return;
    setDeleteTarget({ type: 'edge', edge });
  }, [editMode, editable]);

  // ========================================================================
  // API: Reorder Nodes (save positions after drag)
  // ========================================================================
  const handleSaveLayout = async () => {
    if (!id) return;
    try {
      setSaving(true);
      // Build order from current node positions
      const sorted = [...rawNodes].sort((a, b) => a.position.y - b.position.y || a.position.x - b.position.x);
      const order = sorted.map(n => n.id);
      await workflowsApi.reorderNodes(id, order);
      showToast('✅ 布局已保存');
    } catch (err: any) {
      showToast(`❌ 保存布局失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // ========================================================================
  // API: Activate Workflow
  // ========================================================================
  const handleActivate = async () => {
    if (!id) return;
    try {
      setSaving(true);
      await workflowsApi.activate(id);
      showToast('✅ 工作流已激活');
      await fetchDiagram();
      await fetchProgress();
    } catch (err: any) {
      showToast(`❌ 激活失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // ========================================================================
  // Chat: Load conversation history
  // ========================================================================
  const loadChatHistory = useCallback(async () => {
    if (!id) return;
    try {
      const history = await workflowsApi.getConversationHistory(id);
      if (Array.isArray(history) && history.length > 0) {
        const messages: ChatMessage[] = history.map((h: any) => ({
          role: h.role === 'user' ? 'user' : 'agent',
          content: h.content || h.message || '',
          pendingAction: h.pending_action,
          confidence: h.confidence,
        }));
        setChatMessages(messages);
      }
    } catch {
      // silently ignore
    }
  }, [id]);

  // Open chat panel and load history
  const handleOpenChat = async () => {
    if (!chatOpen) {
      setChatOpen(true);
      await loadChatHistory();
    } else {
      setChatOpen(false);
    }
  };

  // Reset conversation
  const handleResetConversation = async () => {
    if (!id) return;
    try {
      await workflowsApi.resetConversation(id);
      setChatMessages([]);
      setSuggestions([]);
      setPendingAction(null);
      showToast('✅ 对话已重置');
    } catch (err: any) {
      showToast(`❌ 重置失败: ${err.message}`);
    }
  };

  // ========================================================================
  // Chat: Send message
  // ========================================================================
  async function handleAgentSend() {
    if (!chatInput.trim() || chatThinking) return;
    const msg = chatInput.trim();
    setChatInput('');
    setChatThinking(true);

    setChatMessages(prev => [...prev, { role: 'user', content: msg }]);

    try {
      const data = await workflowsApi.converse(id!, msg);

      setChatMessages(prev => [...prev, {
        role: 'agent',
        content: data.content || '',
        pendingAction: data.pending_action || undefined,
        confidence: data.confidence,
      }]);

      setPendingAction(data.pending_action || null);
      setSuggestions(data.suggestions || []);
      setLastConfidence(data.confidence || 0);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { role: 'agent', content: `发送失败：${err?.message || String(err)}` }]);
    } finally {
      setChatThinking(false);
    }
  }

  async function handleConfirmAction() {
    if (!pendingAction) return;
    setChatThinking(true);
    setChatMessages(prev => [...prev, { role: 'user', content: '可以，执行吧' }]);
    try {
      const data = await workflowsApi.converse(id!, '确认执行');
      setChatMessages(prev => [...prev, { role: 'agent', content: data.content || '✅ 已完成修改' }]);
      setPendingAction(null);
      setSuggestions(data.suggestions || []);
      await fetchDiagram();
    } catch (err: any) {
      setChatMessages(prev => [...prev, { role: 'agent', content: `执行失败：${err?.message || String(err)}` }]);
    } finally {
      setChatThinking(false);
    }
  }

  function handleCancelAction() {
    if (!pendingAction) return;
    setChatMessages(prev => [...prev, { role: 'user', content: '算了，取消' }]);
    workflowsApi.converse(id!, '取消').then(data => {
      if (data) setChatMessages(prev => [...prev, { role: 'agent', content: data.content || '已取消' }]);
    }).catch(() => {});
    setPendingAction(null);
  }

  const handleConfirmAndSplit = useCallback(async () => {
    if (!id || !canSplit) return;
    try {
      setSplitSaving(true);
      const data = await workflowsApi.confirmAndSplit(id);
      showToast(`✅ 已拆分为 ${data.projects_created} 个 Project`);
      await fetchDiagram();
    } catch (err: any) {
      showToast(`❌ ${err.message}`);
    } finally {
      setSplitSaving(false);
    }
  }, [id, canSplit, fetchDiagram]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<WorkflowNodeData>) => {
    if (editMode) setSelectedNode(node);
  }, [editMode]);

  // Handle delete key for selected node
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && editMode && selectedNode && !chatOpen) {
        // Don't delete if typing in input
        const tag = (e.target as HTMLElement).tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;
        setDeleteTarget({ type: 'node', node: selectedNode });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [editMode, selectedNode, chatOpen]);

  // Confirm deletion
  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    if (deleteTarget.type === 'node' && deleteTarget.node) {
      await handleDeleteNode(deleteTarget.node.id);
    } else if (deleteTarget.type === 'edge' && deleteTarget.edge) {
      await handleDeleteEdge(deleteTarget.edge.source, deleteTarget.edge.target);
    }
    setDeleteTarget(null);
    if (deleteTarget.type === 'node') setSelectedNode(null);
  };

  const workflowStatusVariant = workflowStatus === 'running' || workflowStatus === 'in_progress' ? 'info' :
    workflowStatus === 'completed' ? 'success' :
    workflowStatus === 'draft' ? 'secondary' : 'warning';

  // ========================================================================
  // Render
  // ========================================================================

  if (loading) {
    return (
      <div className="w-full h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-lg text-gray-700">加载工作流数据...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-screen bg-gray-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-6 text-center">
            <div className="text-2xl mb-2">⚠️</div>
            <h2 className="text-xl font-bold text-slate-800 mb-2">加载工作流图失败</h2>
            <p className="text-slate-600 mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full h-screen flex flex-col bg-gradient-to-br from-slate-50 to-blue-50/30">
      {/* Header */}
      <div className="px-6 py-4 bg-white/80 backdrop-blur border-b border-gray-200/60 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-900">目标流程</h1>
              <span className="text-sm text-slate-500">{workflowName || '未命名'}</span>
              {workflowStatus && (
                <Badge variant={workflowStatusVariant as any}>{workflowStatus}</Badge>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">AI 自动将目标拆分为 {rawNodes.length} 个阶段节点 · {rawEdges.length} 条依赖关系</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={handleOpenChat}
          >
            <MessageSquare className="w-4 h-4 mr-1" />
            {chatOpen ? '关闭对话' : '对话编辑'}
          </Button>
          {editMode && workflowStatus !== 'running' && workflowStatus !== 'completed' && (
            <Button
              variant="secondary"
              size="sm"
              onClick={handleActivate}
              disabled={saving}
            >
              <Play className="w-4 h-4 mr-1" /> 激活
            </Button>
          )}
          {editable && (
            <>
              <Button
                variant={editMode ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setEditMode(!editMode); setSelectedNode(null); }}
              >
                {editMode ? '✏️ 编辑中' : '✏️ 编辑模式'}
              </Button>
              {editMode && (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAddNodeOpen(true)}
                  >
                    <Plus className="w-4 h-4 mr-1" /> 添加节点
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSaveLayout}
                    disabled={saving}
                  >
                    <Save className="w-4 h-4 mr-1" /> 保存布局
                  </Button>
                </>
              )}
              {editMode && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleConfirmAndSplit}
                  disabled={splitSaving || !isDraft}
                >
                  {splitSaving ? '处理中...' : '✅ 确认并拆分'}
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={rawNodes} edges={rawEdges}
          onNodesChange={(changes) => setRawNodes((nds) => applyNodeChanges(changes, nds))}
          onEdgesChange={(changes) => setRawEdges((eds) => applyEdgeChanges(changes, eds))}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeDoubleClick={onEdgeDoubleClick}
          nodeTypes={nodeTypes}
          fitView fitViewOptions={{ padding: 0.15, duration: 300 }}
          minZoom={0.1} maxZoom={2}
          nodesDraggable={editMode && editable}
          nodesConnectable={editMode && editable}
          edgesFocusable={editMode && editable}
          defaultEdgeOptions={{ type: 'smoothstep', animated: true, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#94a3b8', strokeWidth: 2 } }}
        >
          <Background color="#cbd5e1" gap={20} size={1} />
          <Controls className="!bg-white !shadow-xl !rounded-xl !border !border-gray-200" />
          <MiniMap className="!bg-white/90 !backdrop-blur !rounded-xl !shadow-xl !border !border-gray-200"
            nodeColor={(node) => { const d = node.data as Record<string, unknown>; const idx = (d.phaseIndex as number) ?? 0; return PHASE_COLORS[idx]?.accent || '#94a3b8'; }}
            maskColor="rgba(248,250,252,0.6)" />
        </ReactFlow>

        <StatsPanel nodes={rawNodes} edges={rawEdges} workflowName={workflowName} progressData={progressData} />
        <LegendPanel />

        {/* ===== Add Node Dialog ===== */}
        <NodeDialog
          open={addNodeOpen}
          onOpenChange={setAddNodeOpen}
          onSubmit={handleAddNode}
          existingNodeIds={rawNodes.map(n => n.id)}
        />

        {/* ===== Edit Node Dialog ===== */}
        <NodeDialog
          open={editNodeOpen}
          onOpenChange={(v) => { if (!v) { setEditNodeOpen(false); setSelectedNode(null); } }}
          onSubmit={handleUpdateNode}
          initialData={selectedNode ?? undefined}
          existingNodeIds={rawNodes.map(n => n.id)}
        />

        {/* ===== Delete Confirmation ===== */}
        <AlertDialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null); }}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {deleteTarget?.type === 'node' ? '删除节点' : '删除连接'}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {deleteTarget?.type === 'node'
                  ? `确定要删除节点「${(deleteTarget.node?.data as any)?.name || deleteTarget.node?.id}」吗？此操作不可撤销。`
                  : deleteTarget?.edge
                    ? `确定要删除从「${deleteTarget.edge.source}」到「${deleteTarget.edge.target}」的连接吗？`
                    : '确定要删除吗？'}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction onClick={handleConfirmDelete} className="bg-red-500 hover:bg-red-600">
                删除
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* ===== Chat Panel ===== */}
        {chatOpen && (
          <Card className="absolute bottom-4 right-4 w-[420px] z-40 flex flex-col shadow-2xl" style={{ maxHeight: '70vh' }}>
            <CardHeader className="pb-2 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-t-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-purple-600">🧠</span>
                  <CardTitle className="text-sm">AI 对话编辑</CardTitle>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={handleResetConversation} title="重置对话">
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setChatOpen(false)}>×</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto px-4 py-3 space-y-3" style={{ minHeight: 200, maxHeight: '40vh' }}>
              {chatMessages.length === 0 && (
                <div className="text-center text-slate-400 text-sm py-8">
                  <div className="text-2xl mb-2">💡</div>
                  <p>试试说：</p>
                  <p className="text-purple-600 cursor-pointer hover:underline" onClick={() => setChatInput('我觉得应急响应这块少了点什么')}>
                    "我觉得应急响应这块少了点什么"
                  </p>
                  <p className="text-purple-600 cursor-pointer hover:underline mt-1" onClick={() => setChatInput('把阶段3和阶段4合并')}>
                    "把阶段3和阶段4合并"
                  </p>
                  <p className="text-purple-600 cursor-pointer hover:underline mt-1" onClick={() => setChatInput('删除阶段5')}>
                    "删除阶段5"
                  </p>
                </div>
              )}

              {chatMessages.map((msg, i) => (
                <div key={i} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                  <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm ${
                    msg.role === 'user'
                      ? 'bg-purple-500 text-white rounded-tr-none'
                      : 'bg-white border border-slate-200 rounded-tl-none shadow-sm'
                  }`}>
                    {msg.role === 'agent' && (
                      <div className="flex items-center gap-1.5 mb-2">
                        <span className="text-purple-500 text-xs">🧠</span>
                        <span className="text-xs font-medium text-purple-600">刚子</span>
                      </div>
                    )}
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                    {msg.role === 'agent' && msg.pendingAction && (
                      <div className="mt-3 pt-3 border-t border-slate-200">
                        <p className="text-xs text-slate-500 mb-2">
                          置信度 {((msg.confidence || 0) * 100).toFixed(0)}%
                        </p>
                        <div className="p-2 bg-amber-50 rounded-lg border border-amber-200 mb-3">
                          <p className="text-sm text-amber-800 font-medium">
                            {msg.pendingAction.description || msg.pendingAction.action}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={handleConfirmAction}>✓ 确认执行</Button>
                          <Button size="sm" variant="outline" onClick={handleCancelAction}>取消</Button>
                        </div>
                      </div>
                    )}

                    {msg.role === 'agent' && suggestions.length > 0 && !msg.pendingAction && (
                      <div className="mt-3 pt-3 border-t border-slate-200">
                        <p className="text-xs text-slate-500 mb-2">💡 建议：</p>
                        <div className="space-y-1">
                          {suggestions.map((s: any, j: number) => (
                            <button key={j}
                              onClick={() => { setChatInput(s.title || s.description || ''); }}
                              className="w-full text-left p-2 rounded-lg hover:bg-purple-50 border border-purple-100 transition-colors">
                              <p className="text-sm font-medium text-purple-700">{j + 1}. {s.title}</p>
                              {s.reason && <p className="text-xs text-slate-500 mt-0.5">{s.reason}</p>}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {chatThinking && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                      </div>
                      <span className="text-xs text-purple-500">思考中...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </CardContent>

            <div className="px-4 py-3 border-t border-gray-100">
              <div className="flex gap-2">
                <input
                  className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-300"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && chatInput.trim()) { e.preventDefault(); handleAgentSend(); } }}
                  placeholder="说说你想怎么改..."
                  disabled={chatThinking}
                />
                <Button
                  size="sm"
                  onClick={handleAgentSend}
                  disabled={!chatInput.trim() || chatThinking}
                >
                  {chatThinking ? '⏳' : '发送'}
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Selected node quick actions */}
        {selectedNode && editMode && editable && (
          <Card className="absolute top-4 left-4 w-[280px] z-30 shadow-2xl">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <span>📝</span> 节点编辑
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-xs text-slate-500">
                <span className="font-semibold">{(selectedNode.data as any)?.name || selectedNode.id}</span>
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="flex-1" onClick={() => setEditNodeOpen(true)}>
                  编辑
                </Button>
                <Button size="sm" variant="destructive" onClick={() => setDeleteTarget({ type: 'node', node: selectedNode })}>
                  <Trash2 className="w-3 h-3 mr-1" /> 删除
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Toast */}
        {toast && (
          <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-gray-800 text-white px-6 py-3 rounded-xl shadow-2xl z-50 text-sm font-medium">
            {toast}
          </div>
        )}

        {/* Saving overlay */}
        {saving && (
          <div className="absolute inset-0 bg-white/30 backdrop-blur-sm flex items-center justify-center z-50">
            <Card className="p-6 shadow-2xl">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-slate-600 mt-3 font-medium">保存中...</p>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
