import React, { useState, useEffect } from 'react';
import { toast } from "sonner";
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, AlertCircle, Loader2, GitBranch, Save, Pause, Play, RotateCcw, CheckCircle, User,
  Tag,
} from 'lucide-react';
import { projectsApi, tasksApi, agentsApi, goalsApi, scenariosApi } from '../../../shared/utils/api'
import { getAgentName } from '../../../shared/utils/agentMap';
import { solutionsApi } from '@/evo/services/solutions';
import type { Project, Task, Agent, Goal } from '../../../shared/utils/api';
import { getTaskStatusText, getTaskStatusBadgeClass } from '../../../shared/utils/statusMap';
import { SaveScenarioDialog } from '@/reins/components/SaveScenarioDialog'
import { TaskEditModal, TaskRestartDialog } from '@/reins/components/TaskEditModal'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/shared/components/ui/card';
import { Input } from '@/shared/components/ui/input';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { Progress } from '@/shared/components/ui/progress';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table';
import {
  Search, FileText, Brain, MessageSquare, Paperclip
} from 'lucide-react';
import { EntityAttachmentPanel } from '@/reins/components/EntityAttachmentPanel'

// ── Task Tree Visualization ──────────────────────────────────────────────────

interface TaskTreeVisualizationProps {
  projectId: string;
}

function TaskTreeVisualization({ projectId }: TaskTreeVisualizationProps) {
  const [treeData, setTreeData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchTaskTree = async () => {
      try {
        setLoading(true);
        const data = await projectsApi.getTaskTree(projectId);
        setTreeData(data);
        // Expand all nodes by default
        const allIds = new Set<string>();
        const collectIds = (node: any) => {
          if (!node) return;
          allIds.add(node.id || node.task_id);
          if (node.children) node.children.forEach(collectIds);
        };
        if (data?.tasks) data.tasks.forEach(collectIds);
        if (data?.nodes) data.nodes.forEach(collectIds);
        setExpandedNodes(allIds);
        setError(null);
      } catch (err: any) {
        setError(err.message || '获取任务树失败');
      } finally {
        setLoading(false);
      }
    };
    fetchTaskTree();
  }, [projectId]);

  function toggleNode(id: string) {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function renderNode(node: any, depth: number = 0): React.ReactNode {
    const nodeId = node.id || node.task_id || '';
    const children = node.children || node.subtasks || [];
    const isExpanded = expandedNodes.has(nodeId);
    const status = node.status || 'todo';
    const statusBadge = getTaskStatusBadgeClass(status);
    const statusText = getTaskStatusText(status);
    const assignee = node.assigned_agent ? getAgentName(node.assigned_agent) : null;

    return (
      <div key={nodeId} style={{ marginLeft: depth > 0 ? 24 : 0 }}>
        <div
          className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-slate-50 cursor-pointer group"
          onClick={() => children.length > 0 && toggleNode(nodeId)}
        >
          {children.length > 0 ? (
            <span className="w-4 h-4 flex items-center justify-center text-xs text-muted-foreground">
              {isExpanded ? '▼' : '▶'}
            </span>
          ) : (
            <span className="w-4 h-4" />
          )}
          <Badge className={statusBadge}>{statusText}</Badge>
          <span className="text-sm font-medium text-slate-800">{node.title || node.name || '未命名任务'}</span>
          {assignee && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <User className="w-3 h-3" />{assignee}
            </span>
          )}
          {node.priority && (
            <Badge variant="outline" className="text-xs">P{node.priority}</Badge>
          )}
        </div>
        {isExpanded && children.length > 0 && (
          <div className="border-l-2 border-slate-200 ml-2">
            {children.map((child: any) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">加载任务树...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="text-center text-red-500">
            <AlertCircle className="w-5 h-5 mx-auto mb-1" />
            <p className="text-sm">加载任务树失败</p>
            <p className="text-xs text-red-400 mt-1">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Handle different response formats
  const nodes = treeData?.tasks || treeData?.nodes || treeData?.items || [];

  if (!nodes || nodes.length === 0) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-sm text-muted-foreground text-center">暂无任务树数据</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <GitBranch className="w-4 h-4" />任务树
        </CardTitle>
        <CardDescription>点击节点展开/折叠子任务</CardDescription>
      </CardHeader>
      <CardContent className="max-h-96 overflow-y-auto">
        <div className="space-y-1">
          {nodes.map((node: any) => renderNode(node))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Project DAG Visualization ──────────────────────────────────────────────────

interface ProjectDagVisualizationProps {
  projectId: string;
}

interface Step {
  id: string;
  title: string;
  desc: string;
  status: 'done' | 'current' | 'pending' | 'verifying' | 'blocked' | 'review_needed' | 'failed';
  originalStatus: string;
  assignee: string;
}

const STATUS_TEXT: Record<string, string> = {
  todo: '待执行', in_progress: '进行中', active: '进行中', running: '进行中',
  done: '已完成', completed: '已完成', blocked: '阻塞', verifying: '验证中',
  review_needed: '待审核', reviewing: '审核中', failed: '失败',
};

const STATUS_COLOR: Record<string, string> = {
  todo: 'bg-slate-500 text-white', in_progress: 'bg-blue-600 text-white',
  active: 'bg-blue-600 text-white', running: 'bg-blue-600 text-white',
  verifying: 'bg-amber-500 text-white', done: 'bg-green-600 text-white',
  completed: 'bg-green-600 text-white', blocked: 'bg-red-600 text-white',
  review_needed: 'bg-orange-500 text-white', reviewing: 'bg-purple-600 text-white',
  failed: 'bg-red-700 text-white',
};

const STEP_STATUS_COLOR: Record<string, string> = {
  done: 'bg-green-50 border-green-200',
  current: 'bg-blue-50 border-blue-300',
  pending: 'bg-slate-50 border-slate-200',
  verifying: 'bg-amber-50 border-amber-300',
  blocked: 'bg-red-50 border-red-300',
  review_needed: 'bg-orange-50 border-orange-300',
  failed: 'bg-red-100 border-red-400',
};

function ProjectDagVisualization({ projectId }: ProjectDagVisualizationProps) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const icons = [Search, FileText, Brain, MessageSquare];

  useEffect(() => {
    const fetchDiagramData = async () => {
      try {
        setLoading(true);
        const data = await projectsApi.getDiagram(projectId);
        const diagramSteps: Step[] = data.nodes?.map((node: any) => {
          const original = node.status || 'todo';
          const mapped = original === 'completed' || original === 'done' ? 'done' :
            original === 'in_progress' || original === 'active' || original === 'running' ? 'current' :
            original === 'verifying' || original === 'reviewing' ? 'verifying' :
            original === 'blocked' ? 'blocked' :
            original === 'review_needed' || original === 'disputed' ? 'review_needed' :
            original === 'failed' ? 'failed' : 'pending';
          return { id: node.id, title: node.title || '未命名任务', desc: node.description || '',
            status: mapped, originalStatus: original, assignee: node.assignee || '' };
        }) || [];
        setSteps(diagramSteps);
        setError(null);
      } catch (err: any) {
        setError(err.message || '获取工程流程图数据失败');
      } finally {
        setLoading(false);
      }
    };
    fetchDiagramData();
  }, [projectId]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">加载流程图数据...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-4">
          <div className="text-center text-red-500">
            <AlertCircle className="w-5 h-5 mx-auto mb-1" />
            <p className="text-sm">加载流程图失败</p>
            <p className="text-xs text-red-400 mt-1">{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {steps.length > 0 ? (
        <div className="flex items-center justify-center gap-0 overflow-x-auto pb-2">
          {steps.map((step, i) => {
            const Icon = icons[i % icons.length];
            const isLast = i === steps.length - 1;
            return (
              <div key={step.id} className="flex items-center">
                <div className={`flex flex-col items-center p-3 rounded-lg border-2 transition-all w-48 ${STEP_STATUS_COLOR[step.status] || 'bg-slate-50 border-slate-200'}`}>
                  <div className={`px-2 py-0.5 rounded text-xs font-medium mb-2 ${STATUS_COLOR[step.originalStatus] || 'bg-slate-100 text-slate-600'}`}>
                    {STATUS_TEXT[step.originalStatus] || step.originalStatus}
                  </div>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 border-2 ${
                    step.status === 'done' ? 'bg-green-500 border-green-500 text-white' :
                    step.status === 'current' ? 'bg-white border-blue-400 text-blue-600 animate-pulse' :
                    step.status === 'pending' ? 'bg-white border-slate-300 text-slate-400' :
                    step.status === 'verifying' ? 'bg-amber-500 border-amber-500 text-white' :
                    step.status === 'blocked' ? 'bg-red-600 border-red-600 text-white' :
                    step.status === 'review_needed' ? 'bg-orange-500 border-orange-500 text-white' :
                    'bg-red-700 border-red-700 text-white'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <h4 className="font-bold text-xs text-center leading-tight">{step.title}</h4>
                  {step.assignee && <p className="text-xs text-slate-400 mt-1">@{step.assignee}</p>}
                </div>
                {!isLast && (
                  <div className={`w-12 h-0.5 mx-2 ${
                    step.status === 'done' ? 'bg-green-500' :
                    step.status === 'current' ? 'bg-blue-500' : 'bg-slate-300'
                  }`} />
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground text-center py-4">暂无流程数据</p>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [restartingTask, setRestartingTask] = useState<Task | null>(null);
  const [savingAsScenario, setSavingAsScenario] = useState(false);
  const [showSaveScenarioDialog, setShowSaveScenarioDialog] = useState(false);
  const [scenarioPreview, setScenarioPreview] = useState<any>(null);
  const [projectVerifierEditing, setProjectVerifierEditing] = useState(false);
  const [projectVerifierDraft, setProjectVerifierDraft] = useState('');
  const [projectNameEditing, setProjectNameEditing] = useState(false);
  const [projectNameDraft, setProjectNameDraft] = useState('');
  const [goalEditing, setGoalEditing] = useState(false);
  const [goalDraft, setGoalDraft] = useState('');
  // 旧状态编辑已移除，请使用暂停/恢复按钮

  // Project mode edit
  const [projectModeEditing, setProjectModeEditing] = useState(false);
  const [projectModeDraft, setProjectModeDraft] = useState<'inherit' | 'normal' | 'exploration'>('inherit');
  const [projectOptTargetDraft, setProjectOptTargetDraft] = useState<string>('');
  const [projectConvergeThresholdDraft, setProjectConvergeThresholdDraft] = useState<string>('0.05');
  const [projectMaxRoundsDraft, setProjectMaxRoundsDraft] = useState<string>('10');
  const [savingProjectMode, setSavingProjectMode] = useState(false);

  const effectiveVerifier = (project as any)?.verifier_agent_id || goal?.verifier_agent_id || null;
  const verifierSource = (project as any)?.verifier_agent_id ? 'project' : goal?.verifier_agent_id ? 'goal' : null;

  useEffect(() => {
    if (projectVerifierEditing && !projectVerifierDraft) {
      setProjectVerifierDraft(effectiveVerifier);
    }
  }, [projectVerifierEditing, effectiveVerifier]);

  async function fetchData() {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const proj = await projectsApi.get(id);
      setProject(proj);
      const [allTasks, allAgents, allGoals] = await Promise.all([
        tasksApi.list(),
        agentsApi.list().catch(() => [] as Agent[]),
        goalsApi.list().catch(() => [] as Goal[]),
      ]);
      const projTasks = allTasks.filter((t: Task) => t.project_id === id);
      setTasks(projTasks);
      setAgents(allAgents);
      setGoals(allGoals);
      if (proj.goal_id) {
        try {
          const g = await goalsApi.get(proj.goal_id);
          setGoal(g);
        } catch { /* goal not critical */ }
      }
    } catch (e: any) {
      setError(e.message || '工程详情加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchData(); }, [id]);

  async function handleSaveTask(taskId: string, status: string, agent: string) {
    await tasksApi.updateStatus(taskId, status);
    const task = tasks.find(t => t.id === taskId);
    if (agent && (!task || task.assigned_agent !== agent)) {
      await tasksApi.assign(taskId, agent);
    }
    const updated = await tasksApi.list({ project_id: id });
    setTasks(updated);
  }

  async function handleRestartTask(taskId: string, agent: string) {
    // Step 1: Assign agent if different
    const task = tasks.find(t => t.id === taskId);
    if (agent && (!task || task.assigned_agent !== agent)) {
      await tasksApi.assign(taskId, agent);
    }
    // Step 2: Restart
    await tasksApi.restartTask(taskId);
    // Step 3: Refresh tasks
    const updated = await tasksApi.list({ project_id: id });
    setTasks(updated);
  }

  async function handleSaveGoal() {
    if (!project) return;
    try {
      const newGoalId = goalDraft === '__none__' ? null : goalDraft;
      await projectsApi.update(project.id, { goal_id: newGoalId });
      setGoalEditing(false);
      // Refresh goal display
      if (newGoalId) {
        try {
          const g = await goalsApi.get(newGoalId);
          setGoal(g);
        } catch { setGoal(null); }
      } else {
        setGoal(null);
      }
      await fetchData();
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message || '未知错误'));
    }
  }

  async function handleProjectPause() {
    if (!id) return;
    try {
      await projectsApi.pause(id);
      toast.success('工程已暂停');
      await fetchData();
    } catch (e: any) {
      toast.error('暂停失败: ' + (e.message || '未知错误'));
    }
  }

  async function handleProjectResume() {
    if (!id) return;
    try {
      await projectsApi.resume(id);
      toast.success('工程已恢复');
      await fetchData();
    } catch (e: any) {
      toast.error('恢复失败: ' + (e.message || '未知错误'));
    }
  }

  async function handleSaveProjectName() {
    if (!id || !project) return;
    try {
      await projectsApi.update(id, { name: projectNameDraft });
      await fetchData();
      setProjectNameEditing(false);
    } catch (e: any) {
      setError(e.message || '更新工程名称失败');
    }
  }

  async function handleSaveAsScenario() {
    if (!id) return;
    setSavingAsScenario(true);
    try {
      const preview = await scenariosApi.fromProject(id);
      setScenarioPreview(preview);
      setShowSaveScenarioDialog(true);
    } catch (e: any) {
      toast.error('生成场景预览失败: ' + (e.message || '未知错误'));
    } finally {
      setSavingAsScenario(false);
    }
  }

  async function confirmSaveScenario() {
    if (!id || !scenarioPreview) return;
    try {
      await scenariosApi.customCreate(scenarioPreview);
      setShowSaveScenarioDialog(false);
      setScenarioPreview(null);
      toast.success('场景已保存');
    } catch (e: any) {
      toast.error('保存场景失败: ' + (e.message || '未知错误'));
    }
  }

  function openProjectModeEditor() {
    const pm = (project as any)?.mode;
    setProjectModeDraft(pm || 'inherit');
    setProjectOptTargetDraft((project as any)?.optimization_target || '');
    setProjectConvergeThresholdDraft(String((project as any)?.convergence_threshold ?? 0.05));
    setProjectMaxRoundsDraft(String((project as any)?.max_rounds ?? 10));
    setProjectModeEditing(true);
  }

  async function handleSaveProjectMode() {
    if (!id) return;
    setSavingProjectMode(true);
    try {
      // If inherit, set to null (use goal's mode)
      if (projectModeDraft === 'inherit') {
        await projectsApi.update(id, {
          mode: null,
          optimization_target: null,
          convergence_threshold: null,
          max_rounds: null,
        } as any);
      } else {
        // Try setting via projects API with mode field
        const modeData: any = {
          mode: projectModeDraft,
        };
        if (projectModeDraft === 'exploration') {
          modeData.optimization_target = projectOptTargetDraft || undefined;
          const ct = parseFloat(projectConvergeThresholdDraft);
          if (!isNaN(ct)) modeData.convergence_threshold = ct;
          const mr = parseInt(projectMaxRoundsDraft);
          if (!isNaN(mr)) modeData.max_rounds = mr;
        }
        await projectsApi.update(id, modeData);
      }
      setProjectModeEditing(false);
      toast.success('工程模式已更新');
      await fetchData();
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message || '未知错误'));
    } finally {
      setSavingProjectMode(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-900">{error || '工程不存在'}</h2>
        <Link to="/coordination/projects" className="text-blue-600 hover:underline mt-4 inline-block">返回工程列表</Link>
      </div>
    );
  }

  const completedCount = tasks.filter(t => t.status === 'done' || t.status === 'completed').length;
  const progress = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0;

  const projectStatusText: Record<string, string> = {
    active: '进行中', in_progress: '进行中', completed: '已完成', done: '已完成',
    on_hold: '已暂停', paused: '已暂停', cancelled: '已取消',
    draft: '草稿', archived: '已归档',
  };

  const statusBadgeVariant = (status: string): any => {
    if (status === 'active' || status === 'in_progress') return 'info';
    if (status === 'completed' || status === 'done') return 'success';
    if (status === 'on_hold' || status === 'paused') return 'warning';
    return 'secondary';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <Button variant="outline" size="icon" asChild>
          <Link to="/coordination/projects"><ArrowLeft className="w-4 h-4" /></Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="mono text-sm font-bold text-muted-foreground">#{String(project.id).slice(0, 8)}</span>
            <Badge variant={statusBadgeVariant(project.status)}>{projectStatusText[project.status] || project.status}</Badge>
            {goalEditing ? (
              <div className="inline-flex items-center gap-2">
                <Select value={goalDraft || '__none__'} onValueChange={setGoalDraft}>
                  <SelectTrigger className="h-7 w-48 text-xs">
                    <SelectValue placeholder="选择目标" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">不关联</SelectItem>
                    {goals.map(g => (
                      <SelectItem key={g.id} value={g.id}>{g.title || g.id}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button size="sm" onClick={handleSaveGoal}>保存</Button>
                <Button size="sm" variant="outline" onClick={() => { setGoalEditing(false); setGoalDraft(project.goal_id || '__none__'); }}>取消</Button>
              </div>
            ) : (
              <div className="inline-flex items-center gap-1.5">
                {goal ? (
                  <Link to={`/coordination/goals/${goal.id}`} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                    → {goal.title || '目标'}
                  </Link>
                ) : (
                  <span className="text-xs text-muted-foreground">→ 未关联目标</span>
                )}
                <Button variant="ghost" size="sm" className="h-5 text-xs px-1 text-slate-400 hover:text-slate-600" onClick={() => { setGoalEditing(true); setGoalDraft(project.goal_id || '__none__'); }} title="修改所属目标">✏️</Button>
              </div>
            )}
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            {projectNameEditing ? (
              <div className="inline-flex items-center gap-2">
                <input
                  className="border border-slate-300 rounded px-2 py-0.5 text-lg font-bold w-80"
                  value={projectNameDraft}
                  onChange={(e) => setProjectNameDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSaveProjectName(); if (e.key === 'Escape') setProjectNameEditing(false); }}
                  autoFocus
                />
                <Button size="sm" onClick={handleSaveProjectName}>保存</Button>
                <Button size="sm" variant="outline" onClick={() => setProjectNameEditing(false)}>取消</Button>
              </div>
            ) : (
              <div className="inline-flex items-center gap-2">
                <span>{project.name}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs px-1 text-slate-400 hover:text-slate-600"
                  onClick={() => { setProjectNameDraft(project.name || ''); setProjectNameEditing(true); }}
                  title="修改工程名称"
                >
                  ✏️
                </Button>
              </div>
            )}
          </h2>
          {project.description && <p className="text-sm text-muted-foreground mt-1">{project.description}</p>}
          {/* Project Capability Tags */}
          {project.capability_tags && Object.values(project.capability_tags).flat().length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {([
                { key: 'business', label: '业务', color: 'bg-blue-100 text-blue-700' },
                { key: 'professional', label: '专业', color: 'bg-purple-100 text-purple-700' },
                { key: 'technical', label: '技术', color: 'bg-green-100 text-green-700' },
                { key: 'management', label: '管理', color: 'bg-amber-100 text-amber-700' },
              ] as const).map(dim => {
                const items = project.capability_tags?.[dim.key] || []
                if (items.length === 0) return null
                return (
                  <div key={dim.key} className="flex items-center gap-1.5">
                    <span className="text-[10px] font-medium text-slate-400">{dim.label}</span>
                    <div className="flex flex-wrap gap-1">
                      {items.map((cap, i) => (
                        <Badge key={`${cap}-${i}`} variant="secondary" className={`text-xs ${dim.color}`}>{cap}</Badge>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleSaveAsScenario} disabled={savingAsScenario}>
            {savingAsScenario ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 text-green-600" />}
            保存为场景
          </Button>
          {/* 一键分配 */}
          <Button variant="outline" size="sm" onClick={async () => {
            try {
              const r = await projectsApi.autoAssign(id!);
              toast.success(`已分配 ${r.assigned}/${r.total} 个任务`);
              fetchData();
            } catch (e) {
              toast.error('分配失败');
              console.error(e);
            }
          }}>
            <User className="w-4 h-4 text-blue-600" />一键分配
          </Button>
          {project.status === 'completed' ? (
            <Button variant="secondary" size="sm" disabled><Pause className="w-4 h-4" />已完成</Button>
          ) : project.status === 'paused' ? (
            <Button variant="outline" size="sm" onClick={handleProjectResume}><Play className="w-4 h-4" />恢复</Button>
          ) : project.status === 'active' || project.status === 'in_progress' ? (
            <Button variant="outline" size="sm" onClick={handleProjectPause}><Pause className="w-4 h-4" />暂停</Button>
          ) : (
            <Button variant="outline" size="sm" disabled><Pause className="w-4 h-4" />{projectStatusText[project.status] || project.status}</Button>
          )}
          <Button variant="outline" size="sm" onClick={fetchData}><RotateCcw className="w-4 h-4" />刷新</Button>
          <Button variant="outline" size="sm" asChild><Link to={`/coordination/projects/${id}/diagram`}><GitBranch className="w-4 h-4 text-blue-600" />流程图</Link></Button>
          <Button variant="outline" size="sm" asChild><Link to={`/coordination/projects/${id}/tree`}><GitBranch className="w-4 h-4 text-green-600" />任务分解</Link></Button>
        </div>
      </div>

      {/* Tabs: 概览 | 任务 | 任务树 | 流程图 */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="tasks">任务 ({tasks.length})</TabsTrigger>
          <TabsTrigger value="tree">任务树</TabsTrigger>
          <TabsTrigger value="diagram">流程图</TabsTrigger>
          <TabsTrigger value="attachments"><Paperclip className="w-3 h-3 mr-1" />附件</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* 工程信息（合并执行进度 + 验证智能体） */}
          <Card>
            <CardHeader>
              <CardTitle>工程信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 进度条（最上方） */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-muted-foreground">进度</span>
                  <span className="text-sm font-bold">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">{completedCount} 已完成 / {tasks.length} 总任务</p>
              </div>

              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                {/* ID + 所属目标 同行 */}
                <div>
                  <span className="text-muted-foreground">ID:</span>
                  <span className="ml-2 font-mono">{String(project.id).slice(0, 8)}...</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">所属目标:</span>
                  {goalEditing ? (
                    <div className="inline-flex items-center gap-1">
                      <Select value={goalDraft || '__none__'} onValueChange={setGoalDraft}>
                        <SelectTrigger className="h-7 w-36 text-xs">
                          <SelectValue placeholder="选择目标" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">不关联</SelectItem>
                          {goals.map(g => (
                            <SelectItem key={g.id} value={g.id}>{g.title || g.id}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button size="sm" className="h-7 text-xs" onClick={handleSaveGoal}>保存</Button>
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => { setGoalEditing(false); setGoalDraft(project.goal_id || ''); }}>取消</Button>
                    </div>
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      {goal ? (
                        <Link to={`/coordination/goals/${goal.id}`} className="text-xs text-blue-600 hover:underline">
                          {goal.title || goal.id}
                        </Link>
                      ) : (
                        <span className="text-xs text-muted-foreground">未关联</span>
                      )}
                      <Button variant="ghost" size="sm" className="h-5 text-xs px-1" title="修改所属目标" onClick={() => { setGoalEditing(true); setGoalDraft(project.goal_id || '__none__'); }}>✏️</Button>
                    </span>
                  )}
                </div>

                {/* 状态 单独占一行 */}
                <div className="col-span-2 flex items-center gap-2">
                  <span className="text-muted-foreground">状态:</span>
                  <span className="inline-flex items-center gap-1.5">
                    <Badge variant={statusBadgeVariant(project.status)}>{projectStatusText[project.status] || project.status}</Badge>
                    {project.status === 'active' && (
                      <Button variant="ghost" size="sm" className="h-5 text-xs px-1 text-amber-600" onClick={handleProjectPause}>暂停</Button>
                    )}
                    {project.status === 'paused' && (
                      <Button variant="ghost" size="sm" className="h-5 text-xs px-1 text-green-600" onClick={handleProjectResume}>恢复</Button>
                    )}
                  </span>
                </div>

                {/* 验证智能体 单独占一行 */}
                <div className="col-span-2 flex items-center gap-4">
                  <span className="text-muted-foreground">验证智能体:</span>
                  {projectVerifierEditing ? (
                    <div className="inline-flex items-center gap-2">
                      <Select value={projectVerifierDraft} onValueChange={setProjectVerifierDraft}>
                        <SelectTrigger className="h-7 w-36 text-xs">
                          <SelectValue placeholder="选择智能体" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">继承自目标</SelectItem>
                          {['3745f1f0-b67d-4287-a10b-e71b3ff17e97', '9d899c03-4ada-45a7-805a-b2f0fb4ebb24', '876b9322-0fbe-4cd0-97c2-9244a4e3b905', '8817e140-2c46-40d8-9444-a6bca8a8e8fb', 'fefd19b0-7c1a-4927-b294-c795c76afb9f'].map(a => (
                            <SelectItem key={a} value={a}>{getAgentName(a)}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button size="sm" className="h-7 text-xs" onClick={async () => {
                        try {
                          if (projectVerifierDraft === 'all') {
                            // Inherit from goal: clear verifier
                            await projectsApi.update((project as any).id, { verifier_agent_id: null });
                          } else {
                            // Use dedicated setVerifier API
                            await projectsApi.setVerifier((project as any).id, projectVerifierDraft);
                          }
                          toast.success('验证智能体已更新');
                          await fetchData();
                          setProjectVerifierEditing(false);
                        } catch (e: any) {
                          toast.error('保存失败: ' + (e.message || '未知错误'));
                        }
                      }}>保存</Button>
                      <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setProjectVerifierEditing(false)}>取消</Button>
                    </div>
                  ) : (
                    <span className="inline-flex items-center gap-1.5">
                      {effectiveVerifier ? (
                        <>
                          <span className="text-slate-800 font-medium">{getAgentName(effectiveVerifier)}</span>
                          {verifierSource === 'project' && (
                            <Badge variant="secondary" className="text-[10px] px-1">工程独立</Badge>
                          )}
                          {verifierSource === 'goal' && (
                            <span className="text-xs text-muted-foreground">（继承自目标）</span>
                          )}
                        </>
                      ) : (
                        <span className="text-xs text-red-500 font-medium">⚠️ 未设置验证智能体</span>
                      )}
                      <Button variant="ghost" size="sm" className="h-5 text-xs px-1" title="修改验证智能体" onClick={() => { setProjectVerifierEditing(true); setProjectVerifierDraft(effectiveVerifier || ''); }}>✏️</Button>
                    </span>
                  )}
                </div>

                {/* 运行模式 单独占一行 */}
                <div className="col-span-2 flex flex-col gap-3">
                  <div className="flex items-center gap-4">
                    <span className="text-muted-foreground">运行模式:</span>
                    {projectModeEditing ? (
                      <div className="inline-flex items-center gap-2">
                        <Select value={projectModeDraft} onValueChange={(v) => setProjectModeDraft(v as any)}>
                          <SelectTrigger className="h-7 w-36 text-xs">
                            <SelectValue placeholder="选择模式" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="inherit">继承目标</SelectItem>
                            <SelectItem value="normal">常规模式</SelectItem>
                            <SelectItem value="exploration">探索模式</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button size="sm" className="h-7 text-xs" onClick={handleSaveProjectMode} disabled={savingProjectMode}>
                          {savingProjectMode ? <Loader2 className="w-3 h-3 animate-spin" /> : '保存'}
                        </Button>
                        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setProjectModeEditing(false)}>取消</Button>
                      </div>
                    ) : (
                      <span className="inline-flex items-center gap-1.5">
                        {(() => {
                          const pm = (project as any)?.mode;
                          if (pm === 'exploration') {
                            return (
                              <span className="inline-flex items-center gap-1.5">
                                <Badge variant="warning">探索模式</Badge>
                                {(() => { const ot = (project as any)?.optimization_target; const label = ({ duration: '最短工期', cost: '最低成本', overall: '综合最优' } as Record<string, string>)[ot]; return ot ? <span className="text-xs text-muted-foreground">({label || ''})</span> : null; })()}
                              </span>
                            );
                          }
                          if (pm === 'normal') {
                            return <Badge variant="secondary">常规模式</Badge>;
                          }
                          return (
                            <span className="text-xs text-muted-foreground">继承自目标</span>
                          );
                        })()}
                        <Button variant="ghost" size="sm" className="h-5 text-xs px-1" title="修改运行模式" onClick={openProjectModeEditor}>✏️</Button>
                      </span>
                    )}
                  </div>

                  {/* Exploration mode params (inline edit) */}
                  {projectModeEditing && projectModeDraft === 'exploration' && (
                    <div className="ml-0 rounded-lg border border-amber-200 bg-amber-50/50 p-3 space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">优化目标</label>
                        <Select value={projectOptTargetDraft} onValueChange={setProjectOptTargetDraft}>
                          <SelectTrigger className="h-7 text-xs">
                            <SelectValue placeholder="选择优化目标" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="duration">最短工期</SelectItem>
                            <SelectItem value="cost">最低成本</SelectItem>
                            <SelectItem value="overall">综合最优</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-slate-700 mb-1">收敛阈值</label>
                          <Input
                            type="number"
                            step="0.01"
                            min="0.01"
                            max="1"
                            className="h-7 text-xs"
                            value={projectConvergeThresholdDraft}
                            onChange={(e) => setProjectConvergeThresholdDraft(e.target.value)}
                            placeholder="0.05"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-700 mb-1">最大轮次</label>
                          <Input
                            type="number"
                            step="1"
                            min="1"
                            max="100"
                            className="h-7 text-xs"
                            value={projectMaxRoundsDraft}
                            onChange={(e) => setProjectMaxRoundsDraft(e.target.value)}
                            placeholder="10"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tasks">
          <Card>
            <CardContent className="pt-6">
              {tasks.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">暂无任务</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>任务</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>分配给</TableHead>
                      <TableHead>截止日期</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tasks.map(task => {
                      const statusText = getTaskStatusText(task.status);
                      const isReviewNeeded = task.status === 'review_needed';
                      return (
                        <TableRow key={task.id} className={isReviewNeeded ? 'bg-orange-50' : ''}>
                          <TableCell>
                            <button onClick={() => navigate(`/coordination/tasks/${task.id}`)} className="text-left">
                              <p className={`text-sm font-medium ${statusText === '已完成' ? 'text-muted-foreground line-through' : 'text-slate-800 hover:text-blue-600'}`}>
                                {task.title || '未命名任务'}
                              </p>
                            </button>
                          </TableCell>
                          <TableCell>
                            <Badge className={getTaskStatusBadgeClass(task.status)}>{statusText}</Badge>
                          </TableCell>
                          <TableCell>
                            {task.assigned_agent ? (
                              <span className="text-sm text-slate-600 flex items-center gap-1">
                                <User className="w-3 h-3" />{getAgentName(task.assigned_agent)}
                              </span>
                            ) : <span className="text-muted-foreground text-sm">未分配</span>}
                          </TableCell>
                          <TableCell>
                            <span className="text-sm text-muted-foreground">{task.due_date || '—'}</span>
                          </TableCell>
                          <TableCell>
                            {isReviewNeeded ? (
                              <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => navigate(`/coordination/tasks/${task.id}`)}>
                                <AlertCircle className="w-3 h-3" />审核
                              </Button>
                            ) : task.status === 'done' || task.status === 'failed' || task.status === 'timeout' || task.status === 'blocked' || task.status === 'review_needed' || task.status === 'verifying' ? (
                              <div className="flex items-center gap-1">
                                <Button variant="outline" size="sm" onClick={() => setEditingTask(task)}>编辑</Button>
                                <Button variant="outline" size="sm" className="text-amber-600 border-amber-300 hover:bg-amber-50" onClick={() => {
                                  if (task.assigned_agent) {
                                    handleRestartTask(task.id, task.assigned_agent);
                                  } else {
                                    setRestartingTask(task);
                                  }
                                }}><RotateCcw className="w-3 h-3" />重启</Button>
                              </div>
                            ) : (
                              <Button variant="outline" size="sm" onClick={() => setEditingTask(task)}>编辑</Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tree">
          <TaskTreeVisualization projectId={id!} />
        </TabsContent>

        <TabsContent value="diagram">
          <ProjectDagVisualization projectId={id!} />
          <div className="flex gap-2 mt-4">
            <Button variant="outline" size="sm" asChild><Link to={`/coordination/projects/${id}/diagram`}><GitBranch className="w-4 h-4 text-blue-600" />完整流程图</Link></Button>
            <Button variant="outline" size="sm" asChild><Link to={`/coordination/projects/${id}/tree`}><GitBranch className="w-4 h-4 text-green-600" />任务分解</Link></Button>
          </div>
        </TabsContent>

        {/* Attachments tab */}
        <TabsContent value="attachments">
          <Card>
            <CardHeader>
              <CardTitle>附件</CardTitle>
              <CardDescription>管理工程相关的文档、设计文件等</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <EntityAttachmentPanel entityType="project" entityId={id!} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Modals */}
      <TaskEditModal task={editingTask} agents={agents} onClose={() => setEditingTask(null)} onSave={handleSaveTask} />
      <TaskRestartDialog task={restartingTask} agents={agents} onClose={() => setRestartingTask(null)} onRestart={handleRestartTask} />
      <SaveScenarioDialog preview={showSaveScenarioDialog ? scenarioPreview : null} onClose={() => { setShowSaveScenarioDialog(false); setScenarioPreview(null); }} onConfirm={confirmSaveScenario} loading={savingAsScenario} variant="project" />
    </div>
  );
}
