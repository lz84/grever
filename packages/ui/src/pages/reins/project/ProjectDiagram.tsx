import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  MiniMap, Controls, Background, ReactFlow,
  useNodesState, useEdgesState,
  MarkerType, Edge, Node, Handle, Position,
  applyNodeChanges, applyEdgeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Card, CardContent } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';

// Node types for project diagram
interface ProjectDiagramNodeData {
  id: string;
  title: string;
  status: string;
  assignee: string;
  type: string;
  priority: number | string;
}

const ProjectDiagramNode = ({ data }: { data: ProjectDiagramNodeData }) => {
  const statusBadgeMap: Record<string, { label: string; variant: string }> = {
    'completed': { label: '已完成', variant: 'success' },
    'done': { label: '已完成', variant: 'success' },
    'in_progress': { label: '进行中', variant: 'info' },
    'active': { label: '进行中', variant: 'info' },
    'running': { label: '进行中', variant: 'info' },
    'todo': { label: '待开始', variant: 'secondary' },
    'pending': { label: '待开始', variant: 'secondary' },
    'blocked': { label: '阻塞', variant: 'destructive' },
    'verifying': { label: '验证中', variant: 'warning' },
    'reviewing': { label: '验证中', variant: 'warning' },
    'review_needed': { label: '待审核', variant: 'warning' },
    'disputed': { label: '待审核', variant: 'warning' },
    'on_hold': { label: '暂停', variant: 'warning' },
    'failed': { label: '失败', variant: 'destructive' },
  };
  const statusInfo = statusBadgeMap[data.status] || { label: data.status, variant: 'secondary' };

  const priorityLabels: Record<number, string> = {
    0: '紧急', 1: '高', 2: '中', 3: '低',
  };
  const priorityLabel = priorityLabels[Number(data.priority)] || '中';

  return (
    <div className="relative rounded-lg border shadow-md bg-white w-52 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">任务</span>
        <div className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${
            statusInfo.variant === 'success' ? 'bg-green-500' :
            statusInfo.variant === 'info' ? 'bg-blue-500' :
            statusInfo.variant === 'destructive' ? 'bg-red-500' :
            statusInfo.variant === 'warning' ? 'bg-amber-500' :
            'bg-gray-400'
          }`} />
          <span className="text-xs text-gray-500">{priorityLabel}</span>
        </div>
      </div>
      <div className="font-medium text-sm text-gray-800 truncate">{data.title}</div>
      {data.assignee && (
        <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
          <span>👤</span> {data.assignee}
        </div>
      )}
      <div className="text-xs text-gray-400 mt-1">
        <Badge variant={statusInfo.variant as any}>{statusInfo.label}</Badge>
      </div>
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-gray-400" />
      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-gray-400" />
    </div>
  );
};

const nodeTypes = { projectDiagramNode: ProjectDiagramNode };

// Auto-layout function
function autoLayout(nodes: any[], edges: any[]) {
  if (nodes.length === 0) return { nodes: [], edges: [] };
  
  const adj: Record<string, string[]> = {};
  const inDeg: Record<string, number> = {};
  const nodeMap: Record<string, any> = {};
  
  nodes.forEach((n) => { 
    adj[n.id] = []; 
    inDeg[n.id] = 0; 
    nodeMap[n.id] = n; 
  });
  
  edges.forEach((e) => { 
    if (adj[e.source]) adj[e.source].push(e.target); 
    if (inDeg[e.target] !== undefined) inDeg[e.target]++;
  });
  
  const queue: string[] = [];
  const layer: Record<string, number> = {};
  
  Object.keys(inDeg).forEach((id) => { 
    if (inDeg[id] === 0) { 
      queue.push(id); 
      layer[id] = 0; 
    } 
  });
  
  const sorted: string[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    sorted.push(current);
    for (const neighbor of adj[current]) { 
      inDeg[neighbor]--;
      if (inDeg[neighbor] === 0) { 
        layer[neighbor] = layer[current] + 1; 
        queue.push(neighbor); 
      } 
    }
  }
  
  if (sorted.length < nodes.length) {
    nodes.forEach((n, i) => { 
      layer[n.id] = Math.floor(i / 3); 
    });
  }
  
  const layers: Record<number, string[]> = {};
  sorted.forEach((id) => { 
    const l = layer[id]; 
    if (!layers[l]) layers[l] = []; 
    layers[l].push(id); 
  });
  
  const NODE_W = 320, NODE_H = 140, GAP_X = 100, GAP_Y = 80;
  const positioned: any[] = [];
  const layerKeys = Object.keys(layers).map(Number).sort((a, b) => a - b);
  
  layerKeys.forEach((l, li) => {
    const layerNodes = layers[l];
    const maxInLayer = Math.max(1, layerNodes.length);
    const totalH = maxInLayer * (NODE_H + GAP_Y) - GAP_Y;
    const startY = 80 + (Math.max(0, (4 - maxInLayer) * (NODE_H + GAP_Y))) / 2;
    
    layerNodes.forEach((id, ni) => {
      const orig = nodeMap[id];
      positioned.push({ 
        ...orig, 
        position: { x: 80 + li * (NODE_W + GAP_X), y: startY + ni * (NODE_H + GAP_Y) } 
      });
    });
  });
  
  return { nodes: positioned, edges };
}

export default function ProjectDiagram() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projectName, setProjectName] = useState('');
  const [projectStatus, setProjectStatus] = useState('');

  const fetchProjectDiagram = useCallback(async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/v1/projects/${id}/diagram`);
      
      if (!response.ok) {
        throw new Error(`获取工程流程图失败: ${response.status}`);
      }
      
      const data = await response.json();
      
      setProjectName(data.name || '未知工程');
      setProjectStatus(data.status || 'active');
      
      const diagramNodes = data.nodes?.map((node: any) => ({
        id: node.id,
        type: 'projectDiagramNode',
        position: { x: 0, y: 0 },
        data: {
          id: node.id,
          title: node.title || '未命名任务',
          status: node.status || 'todo',
          assignee: node.assignee || '',
          type: node.type || 'task',
          priority: node.priority || 2
        }
      })) || [];

      const diagramEdges = data.edges?.map((edge: any) => ({
        id: edge.source + '-' + edge.target,
        source: edge.source,
        target: edge.target,
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#94a3b8', strokeWidth: 2 },
        label: edge.label || '依赖',
        labelStyle: { fill: '#64748b', fontWeight: 500, fontSize: 11 },
        labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.8 },
      })) || [];

      const { nodes: layoutedNodes, edges: layoutedEdges } = autoLayout(diagramNodes, diagramEdges);

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    } catch (err: any) {
      setError(err.message || '获取工程流程图数据失败');
    } finally {
      setLoading(false);
    }
  }, [id, setNodes, setEdges]);

  useEffect(() => {
    fetchProjectDiagram();
  }, [fetchProjectDiagram]);

  const statusVariant = projectStatus === 'active' || projectStatus === 'in_progress' ? 'info' :
    projectStatus === 'completed' || projectStatus === 'done' ? 'success' :
    projectStatus === 'on_hold' ? 'warning' : 'secondary';

  if (loading) {
    return (
      <div className="w-full h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="mt-4 text-lg text-gray-700">加载工程流程图...</p>
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
            <h2 className="text-xl font-bold text-slate-800 mb-2">加载工程流程图失败</h2>
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
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>←</Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-900">工程流程图</h1>
              <span className="text-sm text-slate-500">{projectName || '未命名工程'}</span>
              {projectStatus && (
                <Badge variant={statusVariant as any}>{projectStatus}</Badge>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              工程内 {nodes.length} 个任务节点 · {edges.length} 条依赖关系
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to={`/coordination/projects/${id}`}>
              返回工程详情
            </Link>
          </Button>
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes} 
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView 
          fitViewOptions={{ padding: 0.15, duration: 300 }}
          minZoom={0.1} 
          maxZoom={2}
          defaultEdgeOptions={{
            type: 'smoothstep', 
            animated: true, 
            markerEnd: { type: MarkerType.ArrowClosed }, 
            style: { stroke: '#94a3b8', strokeWidth: 2 },
            labelStyle: { fill: '#64748b', fontWeight: 500, fontSize: 11 },
            labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.8 },
          }}
        >
          <Background color="#cbd5e1" gap={20} size={1} />
          <Controls className="!bg-white !shadow-xl !rounded-xl !border !border-gray-200" />
          <MiniMap 
            className="!bg-white/90 !backdrop-blur !rounded-xl !shadow-xl !border !border-gray-200"
            nodeColor={(node) => {
              const nodeData = node.data as unknown as ProjectDiagramNodeData;
              switch (nodeData.status) {
                case 'completed': case 'done': return '#22c55e';
                case 'in_progress': case 'active': return '#3b82f6';
                case 'todo': case 'pending': return '#9ca3af';
                case 'blocked': return '#ef4444';
                case 'on_hold': return '#f59e0b';
                case 'failed': return '#ef4444';
                default: return '#9ca3af';
              }
            }}
            maskColor="rgba(248,250,252,0.6)" 
          />
        </ReactFlow>
      </div>
    </div>
  );
}
