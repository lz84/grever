import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { PROJECTS } from '../api/paths';
import { useNavigate } from 'react-router-dom';
import { getAgentName } from '../utils/agentMap';
import {
  MiniMap, Controls, Background, ReactFlow, ReactFlowProvider,
  useNodesState, useEdgesState,
  MarkerType, Node, Edge, Handle, Position,
  applyNodeChanges, applyEdgeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// ============================================================================
// Color scheme per tree level
// ============================================================================
const LEVEL_COLORS: Record<string, { bg: string; border: string; accent: string; icon: string; label: string }> = {
  project: { bg: 'bg-emerald-50',   border: 'border-emerald-400',   accent: '#10b981', icon: '📦', label: '工程' },
  task:    { bg: 'bg-amber-50',     border: 'border-amber-400',     accent: '#f59e0b', icon: '⚡', label: '任务' },
};

// ============================================================================
// Node component — large beautiful cards
// ============================================================================

interface TreeNode {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string | number;
  type: 'project' | 'task';
  children?: TreeNode[];
  assigned_agent?: string;
  phase_order?: number;
}

const TreeNodeComponent = ({ data }: { data: { node: TreeNode; level: number } }) => {
  const { node, level } = data;
  const color = LEVEL_COLORS[node.type] || LEVEL_COLORS.task;

  // Status badge
  const statusMap: Record<string, { label: string; color: string }> = {
    completed: { label: '已完成', color: 'bg-green-100 text-green-700' },
    done:      { label: '已完成', color: 'bg-green-100 text-green-700' },
    confirmed: { label: '已确认', color: 'bg-indigo-100 text-indigo-700' },
    in_progress: { label: '进行中', color: 'bg-blue-100 text-blue-700' },
    active:    { label: '进行中', color: 'bg-blue-100 text-blue-700' },
    running:   { label: '运行中', color: 'bg-blue-100 text-blue-700' },
    pending:   { label: '待执行', color: 'bg-gray-100 text-gray-600' },
    todo:      { label: '待执行', color: 'bg-gray-100 text-gray-600' },
    failed:    { label: '失败', color: 'bg-red-100 text-red-700' },
    draft:     { label: '草稿', color: 'bg-gray-100 text-gray-600' },
  };
  const statusInfo = statusMap[node.status] || statusMap.pending;

  // Normalize priority to string for mapping
  const priorityStr = typeof node.priority === 'number' ? String(node.priority) : String(node.priority || '');
  const priorityMap: Record<string, { label: string; color: string }> = {
    critical: { label: '紧急', color: 'bg-red-100 text-red-700' },
    high:     { label: '高', color: 'bg-orange-100 text-orange-700' },
    medium:   { label: '中', color: 'bg-yellow-100 text-yellow-700' },
    low:      { label: '低', color: 'bg-green-100 text-green-700' },
    p0:       { label: 'P0', color: 'bg-red-100 text-red-700' },
    p1:       { label: 'P1', color: 'bg-orange-100 text-orange-700' },
    p2:       { label: 'P2', color: 'bg-yellow-100 text-yellow-700' },
    p3:       { label: 'P3', color: 'bg-green-100 text-green-700' },
    '0':      { label: '紧急', color: 'bg-red-100 text-red-700' },
    '1':      { label: '高', color: 'bg-orange-100 text-orange-700' },
    '2':      { label: '中', color: 'bg-yellow-100 text-yellow-700' },
    '3':      { label: '低', color: 'bg-green-100 text-green-700' },
  };
  const priorityInfo = priorityMap[priorityStr] || { label: priorityStr, color: 'bg-gray-100 text-gray-600' };

  // Fixed dimensions per level — prevents long titles from breaking layout
  const DIMS: Record<string, { w: number; h: number }> = {
    project: { w: 240, h: 180 },
    task:    { w: 220, h: 160 },
  };
  const dim = DIMS[node.type] || DIMS.task;

  return (
    <div className={`relative rounded-2xl border-2 shadow-xl overflow-hidden ${color.border} ${color.bg}`}
         style={{ width: dim.w, height: dim.h }}>
      {/* Top accent bar */}
      <div className="h-1.5 w-full" style={{ backgroundColor: color.accent }} />

      {/* Target handle (except root) */}
      {level > 0 && (
        <Handle type="target" position={Position.Left}
                className="w-3 h-3 bg-gray-400! border-2 border-white" />
      )}

      <div className="p-3">
        {/* Level label + type icon */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white truncate"
                style={{ backgroundColor: color.accent }}>
            {color.icon} {color.label}
          </span>
          {node.phase_order !== undefined && node.phase_order >= 0 && (
            <span className="text-[10px] text-gray-400 font-mono">阶段{node.phase_order + 1}</span>
          )}
        </div>

        {/* Title — max 2 lines, truncated */}
        <h3 className="text-sm font-bold text-gray-900 leading-snug mb-1"
            style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
            title={node.title}>
          {node.title}
        </h3>

        {/* Description — max 1 line */}
        {node.description && (
          <p className="text-[10px] text-gray-500 leading-relaxed mb-2"
             style={{ display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
             title={node.description}>
            {node.description}
          </p>
        )}

        {/* Status + Priority bar */}
        <div className="flex items-center justify-between mt-1 pt-1.5 border-t border-gray-200/60">
          <div className="flex items-center gap-1.5">
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
          </div>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${priorityInfo.color}`}>
            {priorityInfo.label}
          </span>
        </div>

        {/* Assigned agent */}
        {node.assigned_agent && (
          <div className="text-[10px] text-gray-400 mt-1 truncate" title={getAgentName(node.assigned_agent)}>
            👤 {getAgentName(node.assigned_agent)}
          </div>
        )}

        {/* Children count */}
        {node.children && node.children.length > 0 && (
          <div className="text-[10px] text-gray-400 mt-0.5">
            {node.children.length} 个子{node.type === 'project' ? '任务' : '任务'}
          </div>
        )}
      </div>

      {/* Source handle (if has children) */}
      {node.children && node.children.length > 0 && (
        <Handle type="source" position={Position.Right}
                className="w-3 h-3 bg-gray-400! border-2 border-white" />
      )}
    </div>
  );
};

const nodeTypes = { treeNode: TreeNodeComponent };

// ============================================================================
// Auto-layout: horizontal tree layout
// ============================================================================

function layoutTree(root: TreeNode): { nodes: any[]; edges: any[] } {
  const nodes: any[] = [];
  const edges: any[] = [];

  // Card dimensions — MUST match TreeNodeComponent DIMS
  const CARD_W: Record<string, number> = { project: 240, task: 220 };
  const CARD_H: Record<string, number> = { project: 180, task: 160 };
  const COL_GAP = 80;
  const SIBLING_GAP = 30;

  // Compute the vertical span a subtree needs
  function subtreeSpan(node: TreeNode): number {
    if (!node.children || node.children.length === 0) {
      return CARD_H[node.type] || 160;
    }
    let span = 0;
    node.children.forEach((c, i) => {
      span += subtreeSpan(c);
      if (i < node.children!.length - 1) span += SIBLING_GAP;
    });
    return Math.max(CARD_H[node.type] || 160, span);
  }

  // Position nodes: y = center of card
  function assignPositions(node: TreeNode, col: number, topY: number) {
    const nodeId = `${node.type}-${node.id}`;
    const cardH = CARD_H[node.type] || 160;
    const centerY = topY + cardH / 2;

    nodes.push({
      id: nodeId,
      type: 'treeNode',
      position: { x: 80 + col * 320, y: centerY },
      data: { node, level: col },
    });

    if (node.children && node.children.length > 0) {
      const childSpans = node.children.map(c => subtreeSpan(c));
      const totalSpan = childSpans.reduce((s, h) => s + h, 0) + (node.children.length - 1) * SIBLING_GAP;

      // Center children block vertically around parent's center
      let childTop = centerY - totalSpan / 2;

      node.children.forEach((child, i) => {
        const childNodeId = `${child.type}-${child.id}`;

        edges.push({
          id: `edge-${nodeId}-${childNodeId}`,
          source: nodeId,
          target: childNodeId,
          type: 'smoothstep',
          animated: true,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#94a3b8', strokeWidth: 2 },
        });

        assignPositions(child, col + 1, childTop);
        childTop += childSpans[i] + SIBLING_GAP;
      });
    }
  }

  const rootSpan = subtreeSpan(root);
  assignPositions(root, 0, 60);

  return { nodes, edges };
}

// ============================================================================
// Stats panel (top-right)
// ============================================================================

function TreeStatsPanel({ nodes }: { nodes: any[] }) {
  const projects = nodes.filter(n => n.data?.node?.type === 'project').length;
  const tasks = nodes.filter(n => n.data?.node?.type === 'task').length;
  const completed = nodes.filter(n => ['completed', 'done'].includes(n.data?.node?.status)).length;
  const total = nodes.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl border border-gray-200 p-5 z-30 min-w-[240px]">
      <h3 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
        <span className="text-lg">📊</span> 分解概览
      </h3>

      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>总进度</span>
          <span className="font-bold text-gray-800">{progress}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div className="h-2.5 rounded-full bg-linear-to-r from-emerald-500 to-amber-500 transition-all"
               style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-center">
        <div className="bg-emerald-50 rounded-xl p-2">
          <div className="text-lg font-bold text-emerald-600">{projects}</div>
          <div className="text-[10px] text-emerald-500">工程</div>
        </div>
        <div className="bg-amber-50 rounded-xl p-2">
          <div className="text-lg font-bold text-amber-600">{tasks}</div>
          <div className="text-[10px] text-amber-500">任务</div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Legend panel (bottom-left)
// ============================================================================

function TreeLegendPanel() {
  const items = [
    { color: '#10b981', icon: '📦', label: '工程 (Project)' },
    { color: '#f59e0b', icon: '⚡', label: '任务 (Task)' },
  ];

  return (
    <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-sm rounded-xl shadow-xl border border-gray-200 p-3 z-30">
      <div className="text-xs font-bold text-gray-600 mb-2">层级图例</div>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-[11px] text-gray-500">{item.icon} {item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface TaskNode {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: number | string;
  assignee?: string;
  dueDate?: string;
  createdAt?: string;
  parent_id?: string | null;
  children: TaskNode[];
}

export default function ProjectTaskTree({ projectId }: { projectId: string }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Fetch project task tree data from API
  useEffect(() => {
    if (!projectId) return;
    
    setLoading(true);
    setError(null);
    
    fetch(PROJECTS.GET_TASK_TREE(projectId))
      .then(r => { 
        if (!r.ok) throw new Error(`HTTP ${r.status}`); 
        return r.json(); 
      })
      .then(data => {
        const allTasks: TaskNode[] = data.root_tasks || [];
        const taskMap: Record<string, TaskNode> = {};
        allTasks.forEach(t => { 
          taskMap[t.id] = { ...t, children: [] }; 
        });
        
        // Build the tree structure
        const roots: TaskNode[] = [];
        allTasks.forEach(t => {
          const node = taskMap[t.id];
          if (t.parent_id && taskMap[t.parent_id]) {
            taskMap[t.parent_id].children.push(node);
          } else {
            roots.push(node);
          }
        });

        // Create a virtual root node representing the project itself
        const projectRoot: TreeNode = {
          id: projectId,
          title: '工程根节点',
          description: '工程任务分解',
          status: 'active',
          priority: 'medium',
          type: 'project',
          children: []
        };

        // Fetch project details to get the actual project name
        fetch(PROJECTS.GET(projectId))
          .then(r => r.json())
          .then(proj => {
            projectRoot.title = proj.name || '工程';
            projectRoot.description = proj.description || '';
            
            // Transform the tree structure to TreeNode format
            const transformTaskToTreeNode = (task: TaskNode): TreeNode => ({
              id: task.id,
              title: task.title || '未命名任务',
              description: task.description,
              status: task.status,
              priority: task.priority,
              type: 'task',
              assigned_agent: task.assignee,
              children: task.children.map(transformTaskToTreeNode)
            });

            // Add transformed tasks as children of the project root
            projectRoot.children = roots.map(transformTaskToTreeNode);

            // Generate nodes and edges with proper layout
            const { nodes: layoutNodes, edges: layoutEdges } = layoutTree(projectRoot);

            setNodes(layoutNodes);
            setEdges(layoutEdges);
          })
          .catch(e => {
            console.error('Error fetching project details:', e);
            
            // If project details fail, still create the tree with the basic root
            const transformTaskToTreeNode = (task: TaskNode): TreeNode => ({
              id: task.id,
              title: task.title || '未命名任务',
              description: task.description,
              status: task.status,
              priority: task.priority,
              type: 'task',
              assigned_agent: task.assignee,
              children: task.children.map(transformTaskToTreeNode)
            });

            // Add transformed tasks as children of the project root
            projectRoot.children = roots.map(transformTaskToTreeNode);

            // Generate nodes and edges with proper layout
            const { nodes: layoutNodes, edges: layoutEdges } = layoutTree(projectRoot);

            setNodes(layoutNodes);
            setEdges(layoutEdges);
          })
          .finally(() => setLoading(false));
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, [projectId]);

  if (loading) {
    return (
      <div className="h-[500px] flex items-center justify-center bg-slate-50 rounded-b-lg">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          <p className="mt-4 text-lg text-gray-700">加载任务树...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-[500px] flex items-center justify-center bg-red-50 border-t border-red-200">
        <div className="text-center p-6 bg-white rounded-lg shadow-md max-w-md">
          <div className="text-red-500 text-2xl mb-2">⚠️</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">加载任务树失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-blue-500 text-white rounded-sm hover:bg-blue-600">重试</button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[500px] relative">
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={(changes) => setNodes((nds) => applyNodeChanges(changes, nds))}
          onEdgesChange={(changes) => setEdges((eds) => applyEdgeChanges(changes, eds))}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1, duration: 300 }}
          minZoom={0.1}
          maxZoom={2}
          defaultEdgeOptions={{
            type: 'smoothstep',
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#94a3b8', strokeWidth: 2 },
          }}
        >
          <Background color="#cbd5e1" gap={20} size={1} />
          <Controls className="bg-white! shadow-xl! rounded-xl! border! border-gray-200!" />
          <MiniMap
            className="bg-white/90! backdrop-blur-sm! rounded-xl! shadow-xl! border! border-gray-200!"
            nodeColor={(node) => {
              const d = node.data as { node?: TreeNode };
              const type = d.node?.type || 'task';
              return LEVEL_COLORS[type]?.accent || '#94a3b8';
            }}
            maskColor="rgba(248,250,252,0.6)"
          />
        </ReactFlow>

        {/* Floating panels */}
        <TreeStatsPanel nodes={nodes} />
        <TreeLegendPanel />
      </ReactFlowProvider>
    </div>
  );
}
