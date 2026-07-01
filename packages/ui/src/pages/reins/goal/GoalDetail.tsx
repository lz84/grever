import { useState, useEffect, useRef } from 'react';
import { toast } from "sonner";
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, AlertCircle, Loader2, Save,
  Play, Pause, Zap, X, User, ListTodo, Activity, GitBranch, FileText, Target, Settings,
  Send, MessageSquare, ChevronDown, TrendingUp, Tag, Paperclip, RotateCcw,
} from 'lucide-react';
import { EntityAttachmentPanel } from '@/reins/components/EntityAttachmentPanel'
import { SaveScenarioDialog } from '@/reins/components/SaveScenarioDialog'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/shared/components/ui/card';
import { Input } from '@/shared/components/ui/input';
import { Textarea } from '@/shared/components/ui/textarea';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select';
import { getTaskStatusText, getTaskStatusBadgeClass, getGoalStatusText } from '../../../shared/utils/statusMap';
import { getAgentName } from '../../../shared/utils/agentMap';
import { getModeLabel } from '../../../shared/utils/modeDisplay';
import { tasksApi, goalsApi, projectsApi, agentsApi, disputesApi, workflowsApi, scenariosApi, createScenarioFromGoal } from '../../../shared/utils/api';
import { solutionsApi } from '@/evo/services/solutions';
import type { Solution } from '@/evo/services/solutions';
import type { Task, Goal, Project, Agent, Dispute, Workflow } from '../../../shared/utils/api';
import IterationControlPanel from '@/reins/components/IterationControlPanel';

import GoalIterationPanel from '@/reins/components/GoalIterationPanel';
import GoalVerifier from '@/reins/components/GoalVerifier';
import GoalConstraints from '@/reins/components/GoalConstraints';
import GoalIterationActions from '@/reins/components/GoalIterationActions';
import { Progress } from '@/shared/components/ui/progress';

// ── Helpers ─────────────────────────────────────────────────────────────────

/** 按依赖关系拓扑排序任务，确保执行顺序 */
function sortTasksByExecutionOrder(tasks: Task[]): Task[] {
  const taskMap = new Map<string, Task>();
  const inDegree = new Map<string, number>();
  const dependents = new Map<string, string[]>();

  tasks.forEach(t => {
    taskMap.set(t.id, t);
    inDegree.set(t.id, 0);
    dependents.set(t.id, []);
  });

  // 构建依赖图
  tasks.forEach(t => {
    const deps = (t as any).depends_on || [];
    const depIds = Array.isArray(deps) ? deps : [];
    depIds.forEach(depId => {
      if (taskMap.has(depId)) {
        inDegree.set(t.id, (inDegree.get(t.id) || 0) + 1);
        dependents.get(depId)?.push(t.id);
      }
    });
  });

  // 拓扑排序（Kahn 算法）
  const queue: string[] = [];
  inDegree.forEach((deg, id) => { if (deg === 0) queue.push(id); });
  queue.sort();

  const sorted: Task[] = [];
  while (queue.length > 0) {
    const current = queue.shift()!;
    sorted.push(taskMap.get(current)!);
    dependents.get(current)?.forEach(dep => {
      const newDeg = (inDegree.get(dep) || 0) - 1;
      inDegree.set(dep, newDeg);
      if (newDeg === 0) queue.push(dep);
    });
    queue.sort();
  }

  // 循环依赖兜底：剩余任务追加到末尾
  tasks.forEach(t => { if (!sorted.find(s => s.id === t.id)) sorted.push(t); });
  return sorted;
}

function groupTasksByProject(tasks: Task[], projects: Project[]) {
  const result: { project: Project; tasks: any[] }[] = [];
  for (const proj of projects) {
    const projTasks = tasks.filter(t => t.project_id === proj.id);
    result.push({ project: proj, tasks: projTasks.map(t => ({
      ...t,
      statusText: getTaskStatusText(t.status!),
    })) });
  }
  return result;
}

function mapDisputeToConflict(dispute: Dispute) {
  const typeMap: Record<string, string> = {
    'resource-competition': 'resource-competition',
    'dependency-block': 'dependency-block',
    'dynamic-response': 'dynamic-response',
  };
  const typeLabelMap: Record<string, string> = {
    'resource-competition': '资源竞争',
    'dependency-block': '依赖阻塞',
    'dynamic-response': '动态响应',
  };
  const severityMap: Record<string, string> = {
    'open': '高', 'active': '高', 'resolved': '低', 'closed': '低',
    'under_review': '中', 'appealed': '高',
  };
  const statusMap: Record<string, string> = {
    'open': '未处理', 'active': '处理中', 'resolved': '已解决',
    'closed': '已解决', 'under_review': '审核中', 'appealed': '已上诉',
  };
  return {
    id: dispute.id,
    type: typeMap[dispute.dispute_type || ''] || 'dynamic-response',
    title: typeLabelMap[dispute.dispute_type || ''] || '冲突',
    description: dispute.description,
    severity: severityMap[dispute.status] || '中',
    status: statusMap[dispute.status] || '未处理',
    affectedTasks: dispute.related_task_id ? [dispute.related_task_id] : [],
    affectedAgents: dispute.involved_agents || [],
    resolution: dispute.resolution || null,
    createdAt: dispute.created_at,
    resolvedAt: dispute.resolved_at,
  };
}

// ── Sprint 79: 方案对比(探索模式)────────────────────────────────────────────

interface SolutionComparisonProps {
  goalId: string;
}

const SOL_STATUS_CFG: Record<string, { label: string; variant: string }> = {
  optimal: { label: '最优方案', variant: 'default' },
  compliant: { label: '合规', variant: 'secondary' },
  non_compliant: { label: '不合规', variant: 'destructive' },
  rejected: { label: '已拒绝', variant: 'destructive' },
  pending: { label: '评审中', variant: 'warning' },
};

function getDimLabel(key: string): string {
  const labelMap: Record<string, string> = {
    duration: '工期',
    cost: '成本',
    safety: '安全',
    quality: '质量',
    risk: '风险',
    efficiency: '效率',
    performance: '性能',
    reliability: '可靠性',
    scalability: '可扩展性',
  };
  return labelMap[key] || key;
}

function SolutionComparison({ goalId }: SolutionComparisonProps) {
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSolutions();
  }, [goalId]);

  async function fetchSolutions() {
    setLoading(true);
    try {
      const resp = await solutionsApi.list(goalId);
      setSolutions(resp?.solutions || []);
    } catch {
      setSolutions([]);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mr-2" />
        <span className="text-sm text-muted-foreground">加载方案数据...</span>
      </div>
    );
  }

  if (solutions.length === 0) {
    return (
      <div className="text-center py-10 text-muted-foreground">
        <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">暂无方案数据</p>
        <p className="text-xs mt-1">探索模式启动后将自动生成方案</p>
      </div>
    );
  }

  const bestId = solutions.find(s => s.status === 'optimal')?.id
    || solutions.reduce((best, s) => (s.score > (best?.score ?? 0) ? s : best), solutions[0])?.id;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {solutions.map((sol) => {
        const cfg = SOL_STATUS_CFG[sol.status] || SOL_STATUS_CFG.pending;
        const isBest = sol.id === bestId;
        // Extract dimension scores: look for duration/cost/safety keys in dimensions
        const dims = sol.dimensions || {};
        const dimKeys = Object.keys(dims).filter(k => typeof dims[k] === 'number');

        const badgeVariant = (v: string): any => {
          if (v === 'default') return 'default';
          if (v === 'destructive') return 'destructive';
          if (v === 'warning') return 'default';
          return 'secondary';
        };

        return (
          <Card key={sol.id} className={`overflow-hidden transition-all ${isBest ? 'ring-2 ring-green-500 shadow-md' : 'hover:shadow-sm'}`}>
            {isBest && (
              <div className="bg-green-500 text-white text-center text-xs font-medium py-1">
                ⭐ 最优方案
              </div>
            )}
            <CardContent className="p-4">
              {/* Header: name + score + badge */}
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-sm text-slate-800 truncate flex-1 mr-2" title={sol.name}>
                  {sol.name}
                </h4>
                <Badge variant={badgeVariant(cfg.variant)} className="text-[10px] px-1.5 h-5 shrink-0">
                  {cfg.label}
                </Badge>
              </div>

              {/* Overall score */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs text-slate-500">综合评分</span>
                <span className={`font-bold text-lg ${isBest ? 'text-green-600' : 'text-slate-800'}`}>
                  {typeof sol.score === 'number' ? sol.score.toFixed(1) : sol.score}
                </span>
              </div>

              {/* Dimension scores */}
              {dimKeys.length > 0 ? (
                <div className="space-y-2">
                  {dimKeys.slice(0, 3).map((key) => {
                    const val = dims[key] as number;
                    const pct = val > 1 ? val : val * 100;
                    return (
                      <div key={key}>
                        <div className="flex justify-between text-xs mb-0.5">
                          <span className="text-slate-500">{getDimLabel(key)}</span>
                          <span className="font-medium text-slate-700">{pct.toFixed(0)}%</span>
                        </div>
                        <Progress value={Math.min(100, pct)} className="h-1.5" />
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-xs text-slate-400 text-center py-2">暂无维度评分数据</div>
              )}

              {/* Round info */}
              {sol.round != null && (
                <div className="mt-3 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">第 {sol.round} 轮生成</span>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// ── Sprint 77/80b: 迭代历史 Tab + AI 建议卡片 ────────────────────────────────

interface IterationMessage {
  id: string;
  role: 'ai' | 'human';
  content: string;
  created_at: string;
}

const ITER_STATUS_CFG: Record<string, { label: string; variant: string }> = {
  completed: { label: '已完成', variant: 'success' },
  planned: { label: '计划中', variant: 'secondary' },
  running: { label: '进行中', variant: 'default' },
};

interface IterationHistoryTabProps {
  goalId: string;
  mode: 'research' | 'engineering';
}

interface AISuggestionCardProps {
  iteration: any;
  onConfirm: (response: string) => void;
  onAdjust: (response: string, adjustments: object) => void;
  onSkip: () => void;
  confirming: boolean;
  adjusting: boolean;
}

function AISuggestionCard({ iteration, onConfirm, onAdjust, onSkip, confirming, adjusting }: AISuggestionCardProps) {
  const [showAdjust, setShowAdjust] = useState(false);
  const [adjustText, setAdjustText] = useState('');
  const suggestion = iteration.ai_suggestion;
  const analysisText = suggestion?.analysis || iteration.ai_analysis || '';
  const suggestionText = suggestion?.suggestion || '请查看上方分析详情';

  if (showAdjust) {
    return (
      <div className="space-y-2">
        <h5 className="text-sm font-medium text-amber-700">✏️ 调整建议</h5>
        <Textarea
          value={adjustText}
          onChange={(e) => setAdjustText(e.target.value)}
          placeholder="请输入你的调整意见,例如:增加安全预算、缩短工期..."
          className="text-sm min-h-[80px]"
          rows={3}
        />
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => { onAdjust(adjustText, {}); setShowAdjust(false); setAdjustText(''); }}
            disabled={!adjustText.trim() || adjusting}
          >
            {adjusting ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Save className="w-3 h-3 mr-1" />}
            {adjusting ? '提交中...' : '提交调整'}
          </Button>
          <Button size="sm" variant="outline" onClick={() => { setShowAdjust(false); setAdjustText(''); }}>
            取消
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-lg">🤖</span>
        <h5 className="text-sm font-semibold text-amber-800">AI 建议</h5>
      </div>

      {analysisText && (
        <div>
          <h6 className="text-xs font-medium text-amber-700 mb-1">分析</h6>
          <p className="text-sm text-slate-600 leading-relaxed">{analysisText}</p>
        </div>
      )}

      {suggestionText && (
        <div>
          <h6 className="text-xs font-medium text-amber-700 mb-1">建议</h6>
          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{suggestionText}</p>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <Button
          size="sm"
          variant="default"
          onClick={() => onConfirm('同意执行')}
          disabled={confirming || adjusting}
          className="bg-green-600 hover:bg-green-700"
        >
          {confirming ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <span className="mr-1">✓</span>}
          {confirming ? '确认中...' : '同意'}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setShowAdjust(true)}
          disabled={confirming || adjusting}
        >
          调整
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={onSkip}
          disabled={confirming || adjusting}
        >
          跳过本轮
        </Button>
      </div>
    </div>
  );
}

function IterationHistoryTab({ goalId, mode }: IterationHistoryTabProps) {
  const [iterations, setIterations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Record<string, IterationMessage[]>>({});
  const [chatInput, setChatInput] = useState('');
  const [sending, setSending] = useState(false);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [adjustingId, setAdjustingId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchIterations(); }, [goalId]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, expandedId]);

  async function fetchIterations() {
    setLoading(true);
    try {
      const data = await goalsApi.getIterations(goalId);
      setIterations(Array.isArray(data) ? data : data.iterations || []);
    } catch { setIterations([]); }
    finally { setLoading(false); }
  }

  async function fetchMessages(iterId: string) {
    try {
      const data: any = await goalsApi.iterationDiscuss(goalId, iterId);
      setMessages(prev => ({ ...prev, [iterId]: Array.isArray(data) ? data : data.messages || [] }));
    } catch { /* silent */ }
  }

  async function handleSend(iterId: string) {
    if (!chatInput.trim() || sending) return;
    setSending(true);
    try {
      const resp = await fetch(`/api/v1/goals/${goalId}/iterations/${iterId}/discuss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'human', content: chatInput.trim() }),
      });
      if (resp.ok) { setChatInput(''); await fetchMessages(iterId); }
    } catch { toast.error('发送消息失败'); }
    finally { setSending(false); }
  }

  async function handleExpand(iterId: string) {
    if (expandedId === iterId) { setExpandedId(null); }
    else { setExpandedId(iterId); if (!messages[iterId]) await fetchMessages(iterId); }
  }

  // Sprint 80b: AI 建议操作
  async function handleConfirm(iterId: string, response: string) {
    setConfirmingId(iterId);
    try {
      await goalsApi.iterationConsensus(goalId, iterId, { human_response: response });
      await fetchIterations(); toast.success('已确认');
    } catch { toast.error('确认失败'); }
    finally { setConfirmingId(null); }
  }

  async function handleAdjust(iterId: string, response: string, adjustments: object) {
    setAdjustingId(iterId);
    try {
      await goalsApi.iterationAnalysis(goalId, iterId, { human_response: response, adjustments });
      await fetchIterations(); toast.success('已调整,已创建下一轮');
    } catch { toast.error('调整失败'); }
    finally { setAdjustingId(null); }
  }

  async function handleSkip(iterId: string) {
    setConfirmingId(iterId);
    try {
      await goalsApi.iterationConsensus(goalId, iterId, { human_response: '跳过本轮' });
      await fetchIterations(); toast.success('已跳过');
    } catch { toast.error('跳过失败'); }
    finally { setConfirmingId(null); }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground mr-2" />
        <span className="text-sm text-muted-foreground">加载迭代历史...</span>
      </div>
    );
  }

  if (iterations.length === 0) {
    return (
      <div className="text-center py-10 text-muted-foreground">
        <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">暂无迭代记录</p>
        <p className="text-xs mt-1">启动迭代后将显示迭代历史和讨论</p>
      </div>
    );
  }

  const badgeVariant = (v: string): any => {
    if (v === 'success') return 'default';
    if (v === 'destructive') return 'destructive';
    return 'secondary';
  };

  return (
    <div className="space-y-3">
      {iterations.map((iter) => {
        const cfg = ITER_STATUS_CFG[iter.status || 'planned'] || ITER_STATUS_CFG.planned;
        const analysis = iter.ai_analysis || iter.analysis || iter.summary || '';
        const summary = analysis.slice(0, 80);
        const isExpanded = expandedId === iter.id;
        const iterMessages = messages[iter.id] || [];
        const iterNum = iter.round ?? iter.iteration_number ?? iter.id?.slice(0, 4) ?? '?';
        const isConfirming = confirmingId === iter.id;
        const isAdjusting = adjustingId === iter.id;

        return (
          <Card key={iter.id} className="overflow-hidden">
            {/* 迭代卡片头部 */}
            <div className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-50/50 transition-colors" onClick={() => handleExpand(iter.id)}>
              <span className="font-mono font-bold text-sm text-slate-800">#{iterNum}</span>
              <Badge variant={badgeVariant(cfg.variant)} className="text-[10px] px-1.5 h-5">
                {cfg.label}
              </Badge>
              {iter.score != null && (
                <span className="flex items-center gap-1 text-xs text-green-700">
                  <TrendingUp className="w-3 h-3" />{typeof iter.score === 'number' ? iter.score.toFixed(2) : iter.score}
                </span>
              )}

              {/* 模式特定信息 */}
              {mode === 'research' && iter.solution_name && (
                <span className="text-xs text-blue-600 font-medium">方案: {iter.solution_name}</span>
              )}
              {mode === 'research' && analysis && (
                <span className="text-xs text-muted-foreground truncate flex-1">
                  {summary}{analysis.length > 80 ? '...' : ''}
                </span>
              )}

              <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform shrink-0 ${isExpanded ? 'rotate-180' : ''}`} />
            </div>

            {/* 展开内容 */}
            {isExpanded && (
              <div className="border-t border-slate-100">
                {/* AI 分析详情 */}
                {analysis && (
                  <div className="p-3 bg-slate-50">
                    <h5 className="text-sm font-medium mb-1">分析</h5>
                    <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">{analysis}</p>
                  </div>
                )}

                {/* Sprint 80b: AI 建议卡片(如果有,且状态为 completed 且未回复) */}
                {iter.ai_suggestion && iter.status === 'completed' && !iter.human_response && (
                  <div className="p-3">
                    <AISuggestionCard
                      iteration={iter}
                      onConfirm={(response) => handleConfirm(iter.id, response)}
                      onAdjust={(response, adjustments) => handleAdjust(iter.id, response, adjustments)}
                      onSkip={() => handleSkip(iter.id)}
                      confirming={isConfirming}
                      adjusting={isAdjusting}
                    />
                  </div>
                )}

                {/* 人的回复(已有) */}
                {iter.human_response && (
                  <div className="p-3 bg-blue-50">
                    <h5 className="text-sm font-medium mb-1">你的回复</h5>
                    <p className="text-sm text-blue-700 leading-relaxed">{iter.human_response}</p>
                  </div>
                )}

                {/* 对话历史(已有讨论功能,保留并增强) */}
                {iterMessages.length > 0 && (
                  <div className="p-3 space-y-2.5 bg-slate-50/30 border-t border-slate-100">
                    <h5 className="text-sm font-medium text-slate-700">讨论</h5>
                    <div className="max-h-[300px] overflow-y-auto space-y-2">
                      {iterMessages.map((msg) => (
                        <div key={msg.id} className={`flex ${msg.role === 'human' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm leading-relaxed ${
                            msg.role === 'ai'
                              ? 'bg-blue-100 text-blue-900 rounded-bl-sm'
                              : 'bg-gray-200 text-gray-800 rounded-br-sm'
                          }`}>
                            {msg.content}
                          </div>
                        </div>
                      ))}
                      <div ref={chatEndRef} />
                    </div>
                  </div>
                )}

                {/* Sprint 81: 迭代操作面板(分析、共识、讨论) */}
                <div className="p-3 border-t border-slate-100">
                  <GoalIterationActions
                    goalId={goalId}
                    iterationId={iter.id}
                    iterationNumber={iterNum}
                  />
                </div>

                {/* 输入框 */}
                <div className="flex gap-2 p-2.5 border-t border-slate-100 bg-white">
                  <Textarea
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="输入讨论内容..."
                    className="flex-1 min-h-[36px] max-h-[80px] text-sm resize-none py-1.5"
                    rows={1}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(iter.id); } }}
                  />
                  <Button size="sm" onClick={() => handleSend(iter.id)} disabled={!chatInput.trim() || sending} className="shrink-0 h-[36px] w-[36px] p-0">
                    {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function GoalDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // When entering edit mode, sync draft with current value
  // Goal mode edit
  const [goalModeEditing, setGoalModeEditing] = useState(false);
  const [goalModeDraft, setGoalModeDraft] = useState<'engineering' | 'research'>('engineering');
  const [diversityDraft, setDiversityDraft] = useState<string | undefined>(undefined);
  const [portfolioSizeDraft, setPortfolioSizeDraft] = useState<string>('5');
  const [savingMode, setSavingMode] = useState(false);

  // Workflow generation
  // Save as scenario
  const [savingAsScenario, setSavingAsScenario] = useState(false);
  const [showSaveScenarioDialog, setShowSaveScenarioDialog] = useState(false);
  const [scenarioPreview, setScenarioPreview] = useState<any>(null);

  async function fetchData() {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [goalData, allProjects, allDisputes, allWorkflows] = await Promise.all([
        goalsApi.get(id),
        projectsApi.list(),
        disputesApi.list(undefined, id),
        workflowsApi.list(),
      ]);
      setGoal(goalData);
      const goalProjects = allProjects.filter((p: Project) => p.goal_id === id);
      setProjects(goalProjects);

      // 修复：只用 goal_id 过滤，123 条在 limit=100 以内
      const goalTasks = await tasksApi.list({ goal_id: id });
      setTasks(goalTasks);

      setDisputes(allDisputes);
      const goalWorkflows = allWorkflows.filter((w: any) => w.goal_id === id);
      if (goalWorkflows.length > 0) setWorkflow(goalWorkflows[0]);
    } catch (e: any) {
      setError(e.message || '目标详情加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchData(); }, [id]);

  async function handleSaveAsScenario() {
    if (!id) return;
    setSavingAsScenario(true);
    try {
      const preview = await createScenarioFromGoal(id);
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

  async function openModeEditor() {
    const gm = (goal as any)?.mode;
    setGoalModeDraft((gm as 'engineering' | 'research') || 'engineering');
    setDiversityDraft((goal as any)?.diversity || undefined);
    setPortfolioSizeDraft(String((goal as any)?.portfolio_size ?? 5));
    setGoalModeEditing(true);
  }

  async function handleSaveMode() {
    if (!id) return;
    setSavingMode(true);
    try {
      const modeData: {
        mode: 'engineering' | 'research';
        diversity?: string;
        portfolio_size?: number;
      } = {
        mode: goalModeDraft,
      };
      if (goalModeDraft === 'research') {
        modeData.diversity = diversityDraft || undefined;
        const ps = parseInt(portfolioSizeDraft);
        if (!isNaN(ps)) modeData.portfolio_size = ps;
      }
      await solutionsApi.setGoalMode(id, modeData);
      setGoalModeEditing(false);
      toast.success('模式已更新');
      await fetchData();
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message || '未知错误'));
    } finally {
      setSavingMode(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error || !goal) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-900">{error || '目标不存在'}</h2>
        <Link to="/coordination/goals" className="text-blue-600 hover:underline mt-4 inline-block">返回首页</Link>
      </div>
    );
  }

  const mode = (goal as any)?.mode || 'engineering';
  const completedProjects = projects.filter(p => p.status === 'completed' || p.status === 'done');
  const hasCompletedProjects = completedProjects.length > 0;
  const goalIsDraft = goal.status === 'draft';
  const statusInconsistent = goalIsDraft && hasCompletedProjects;

  const conflicts = disputes.map(mapDisputeToConflict);
  const groupedProjects = groupTasksByProject(tasks, projects);
  const taskCount = tasks.length;
  const projectCount = projects.length;

  const goalStatusVariant = (status: string | null | undefined): any => {
    if (status === 'active' || status === 'in_progress') return 'info';
    if (status === 'completed' || status === 'done') return 'success';
    return 'secondary';
  };

  const projectStatusVariant = (status: string): any => {
    if (status === 'active' || status === 'in_progress') return 'info';
    if (status === 'completed' || status === 'done') return 'success';
    return 'secondary';
  };


  const goalProgress = tasks.length > 0
    ? Math.min(100, Math.round((tasks.filter(t => t.status === 'done' || t.status === 'completed').length / tasks.length) * 100))
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" asChild>
            <Link to="/coordination/goals"><ArrowLeft className="w-4 h-4" /></Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <span className="mono text-sm font-bold text-slate-900">#{String(goal.id || '').slice(0, 8)}</span>
              <Badge variant={goalStatusVariant(goal.status)}>{getGoalStatusText(goal.status!)}</Badge>
            </div>
            <h2 className="text-xl font-bold text-slate-900 mt-1">{goal.title || '未命名目标'}</h2>
            {goal.description && <p className="text-sm text-slate-500 mt-1">{goal.description}</p>}
            {/* 主智能体 */}
            {(goal as any).main_agent_id && (
              <div className="flex items-center gap-1.5 mt-1.5">
                <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200 text-xs">
                  <Zap className="w-3 h-3 mr-0.5" />主智能体: {getAgentName((goal as any).main_agent_id)}
                </Badge>
              </div>
            )}
            {/* Goal Capability Tags */}
            {goal.capability_tags && Object.values(goal.capability_tags).flat().length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {([
                  { key: 'business', label: '业务', color: 'bg-blue-100 text-blue-700' },
                  { key: 'professional', label: '专业', color: 'bg-purple-100 text-purple-700' },
                  { key: 'technical', label: '技术', color: 'bg-green-100 text-green-700' },
                  { key: 'management', label: '管理', color: 'bg-amber-100 text-amber-700' },
                ] as const).map(dim => {
                  const items = goal.capability_tags?.[dim.key] || []
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
        </div>
        <div className="flex gap-2">

          {/* 一键分配 */}
          <Button variant="outline" size="sm" onClick={async () => {
            try {
              const r = await goalsApi.autoAssign(id!);
              toast.success(`已分配 ${r.assigned}/${r.total} 个任务`);
              fetchData();
            } catch (e) {
              toast.error('分配失败');
              console.error(e);
            }
          }}>
            <User className="w-4 h-4 text-blue-600" />一键分配
          </Button>
          {workflow && (
            <Button variant="outline" size="sm" onClick={() => navigate(`/workflows/${workflow.id}/diagram`)}>
              <GitBranch className="w-4 h-4 text-purple-600" />目标流程
            </Button>
          )}
          {/* 执行/暂停/恢复 - 纯图标无文字 */}
          {(() => {
            const gs = goal?.status;
            const isRunning = gs === 'in_progress' || gs === 'active';
            const isPaused = gs === 'paused';
            const isCompleted = gs === 'completed' || gs === 'done';
            if (isRunning) {
              return (
                <Button size="sm" className="bg-amber-500 hover:bg-amber-600" onClick={async () => {
                  try {
                    await goalsApi.pause(goal.id);
                    setGoal({ ...goal!, status: 'paused' });
                  } catch (e) { console.error('Pause failed:', e); }
                }}>
                  <Zap className="w-4 h-4" />
                </Button>
              );
            } else if (isPaused || isCompleted) {
              return (
                <Button size="sm" onClick={async () => {
                  try {
                    await goalsApi.resume(goal.id);
                    setGoal({ ...goal!, status: 'in_progress' });
                  } catch (e) { console.error('Resume failed:', e); }
                }}>
                  <RefreshCw className="w-4 h-4" />
                </Button>
              );
            } else {
              const needsIteration = mode === 'research';
              return (
                <Button size="sm" onClick={async () => {
                  try {
                    await goalsApi.activate(goal.id);
                    setGoal({ ...goal!, status: 'in_progress' });
                    if (needsIteration) {
                      try {
                        await solutionsApi.startIteration(goal.id);
                        toast.success('目标已激活,迭代已启动');
                      } catch {
                        toast.success('目标已激活');
                      }
                    } else {
                      toast.success('目标已激活');
                    }
                  } catch (e) { console.error('Activate failed:', e); }
                }}>
                  <Play className="w-4 h-4" />
                </Button>
              );
            }
          })()}
          {/* 刷新 - 纯图标 */}
          <Button variant="outline" size="sm" onClick={fetchData} title="刷新">
            <RefreshCw className="w-4 h-4" />
          </Button>
          {/* 保存为场景 - ghost样式不显眼 */}
          <Button variant="outline" size="sm" onClick={handleSaveAsScenario} disabled={savingAsScenario} title="保存为场景">
            {savingAsScenario ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Status inconsistency warning */}
      {statusInconsistent && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="font-semibold text-amber-800 text-sm">状态不一致</h4>
              <p className="text-sm text-amber-700 mt-1">
                当前目标状态为<strong>草稿</strong>,但已有 <strong>{completedProjects.length}</strong> 个关联工程标记为<strong>已完成</strong>。
              </p>
              <Button size="sm" variant="outline" className="mt-2 border-amber-300 text-amber-700 hover:bg-amber-100" onClick={async () => {
                try {
                  await goalsApi.resume(goal.id);
                  setGoal({ ...goal, status: 'in_progress' });
                } catch (e) { console.error('Failed to update goal status:', e); }
              }}>
                重新激活目标
              </Button>
            </div>
          </CardContent>
        </Card>
      )}


      {/* ── Mode Display/Edit Card ───────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-500" />
              <CardTitle className="text-sm">运行模式</CardTitle>
              {(() => {
                return <Badge variant={mode === 'research' ? 'warning' : 'default'}>{getModeLabel(mode)}</Badge>;
              })()}
            </div>
            <Button variant="ghost" size="sm" onClick={openModeEditor}>
              {goalModeEditing ? '取消' : '修改'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {goalModeEditing ? (
            <div className="space-y-4">
              {/* Mode selection */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">选择模式</label>
                <div className="flex gap-2">
                  {[
                    { value: 'engineering' as const, label: '工程模式', desc: '标准执行流程' },
                    { value: 'research' as const, label: '研究模式', desc: '多方案探索，找到最优解' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setGoalModeDraft(opt.value)}
                      className={`flex-1 p-3 rounded-lg border-2 text-left transition-all ${
                        goalModeDraft === opt.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="text-sm font-medium text-slate-800">{opt.label}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Research mode fields */}
              {goalModeDraft === 'research' && (
                <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-4">
                  <div className="flex items-center gap-1.5 text-amber-800 text-sm font-medium">
                    <Settings className="w-4 h-4" />
                    研究模式参数
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">多样性策略</label>
                    <Select value={diversityDraft} onValueChange={setDiversityDraft}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择多样性策略" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="best">🏆 最优策略</SelectItem>
                        <SelectItem value="portfolio">📊 组合策略</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {diversityDraft === 'portfolio' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">组合数量</label>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        max="50"
                        value={portfolioSizeDraft}
                        onChange={(e) => setPortfolioSizeDraft(e.target.value)}
                        placeholder="5"
                      />
                      <p className="text-xs text-slate-400 mt-1">组合中包含的方案数量，默认 5</p>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <Button variant="outline" size="sm" onClick={() => setGoalModeEditing(false)} disabled={savingMode}>
                  取消
                </Button>
                <Button size="sm" onClick={handleSaveMode} disabled={savingMode}>
                  {savingMode ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Save className="w-3 h-3 mr-1" />}
                  {savingMode ? '保存中...' : '保存'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Display current mode info */}
              {(() => {
                if (mode === 'research') {
                  return (
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-500">多样性策略:</span>
                        <span className="ml-2 font-medium text-slate-800">
                          {(({ best: '最优', portfolio: '组合' } as Record<string, string>)[(goal as any)?.diversity as string] || '未设置')}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">组合数量:</span>
                        <span className="ml-2 font-medium text-slate-800">
                          {(goal as any)?.portfolio_size ?? 5}
                        </span>
                      </div>
                    </div>
                  );
                }
                return <p className="text-sm text-slate-500">当前使用工程模式,按标准流程执行</p>;
              })()}
            </div>
          )}
        </CardContent>
      </Card>


      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 执行状态(自适应模式) */}
        <Card>
          <CardContent className="p-4 space-y-3">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-500">
                {mode === 'engineering' ? '执行进度' : '研究进度'}
              </span>
              <span className="mono font-bold text-slate-900">
                {mode === 'engineering' ? `${goalProgress}%` : '-'}
              </span>
            </div>
            {mode === 'engineering' ? (
              <>
                <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 transition-all" style={{ width: `${goalProgress}%` }} />
                </div>
                <div className="text-xs text-slate-400">
                  {tasks.filter(t => t.status === 'done' || t.status === 'completed').length} / {tasks.length} 任务已完成
                </div>
              </>
            ) : (
              <div className="text-xs text-slate-500 mt-1">
                {`多样性: ${(({ best: '最优', portfolio: '组合' } as Record<string, string>)[(goal as any)?.diversity as string] || '-')} · 查看下方研究面板`}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Workspace */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-500" />
              <CardTitle className="text-sm">工作目录</CardTitle>
              {goal.workspace_type && (
                <Badge variant={goal.workspace_type === 'local' ? 'info' : 'secondary'}>
                  {goal.workspace_type === 'local' ? '本地' : 'Git'}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {goal.workspace_path ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500 shrink-0">路径:</span>
                  <span className="font-mono text-slate-800 truncate">{goal.workspace_path}</span>
                </div>
                {goal.workspace_status && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-500">状态:</span>
                    <Badge variant={
                      goal.workspace_status === 'cloned' || goal.workspace_status === 'synced' ? 'success' :
                      goal.workspace_status?.includes('failed') || goal.workspace_status === 'error' ? 'destructive' :
                      goal.workspace_status === 'pending' ? 'secondary' : 'warning'
                    }>
                      {goal.workspace_status === 'pending' ? '未初始化' :
                       goal.workspace_status === 'cloned' ? '已克隆' :
                       goal.workspace_status === 'pulling_failed' ? '拉取失败' :
                       goal.workspace_status || '未知'}
                    </Badge>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-400 text-center py-2">暂无工作目录</p>
            )}
          </CardContent>
        </Card>

        {/* Verifier */}
        <GoalVerifier
          goalId={id!}
          currentVerifierId={(goal as any)?.verifier_agent_id}
          onVerifierChanged={fetchData}
        />
      </div>


      {/* Decompose Preview */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-purple-500" />
            <CardTitle className="text-sm">分解图</CardTitle>
          </div>
          <CardDescription>查看或生成目标的任务分解结构</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild className="w-full">
            <Link to={`/goals/${id}/diagram`}>
              <GitBranch className="w-4 h-4 mr-2" />
              查看分解图
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Constraints — 仅研究模式显示 */}
      {id && mode === 'research' && (
        <GoalConstraints goalId={id!} />
      )}




      {/* Sprint 68-73 / Sprint 80: 迭代控制面板(研究模式) */}
      {mode === 'research' && id && (
        <IterationControlPanel goalId={id} goalStatus={goal.status ?? undefined} onSolutionUpdate={fetchData} />
      )}


      {/* Sprint 79/80: 方案对比(研究模式) */}
      {mode === 'research' && id && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-blue-500" />
              <CardTitle className="text-sm">方案对比</CardTitle>
              <Badge variant="warning" className="text-[10px] px-1.5 h-5">研究模式</Badge>
            </div>
            <CardDescription>比较不同方案的优劣,选择最优执行路径</CardDescription>
          </CardHeader>
          <CardContent>
            <SolutionComparison goalId={id!} />
          </CardContent>
        </Card>
      )}


      {/* 附件 — 置顶显示 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Paperclip className="w-4 h-4 text-slate-500" />
            <CardTitle>附件</CardTitle>
          </div>
          <CardDescription>管理目标相关的文档、设计文件等</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <EntityAttachmentPanel entityType="goal" entityId={id!} />
        </CardContent>
      </Card>

      {/* Projects and Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Projects list */}
        <Card>
          <CardHeader>
            <CardTitle>关联工程</CardTitle>
            <p className="text-xs text-slate-500">{projectCount} 个工程</p>
          </CardHeader>
          <CardContent>
            {projects.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">暂无关联工程</p>
            ) : (
              <div className="space-y-3">
                {projects.map(proj => (
                  <Link key={proj.id} to={`/coordination/projects/${proj.id}`} className="block p-3 bg-slate-50 rounded-sm border border-slate-200 hover:bg-slate-100 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-slate-700">{proj.name}</span>
                      <Badge variant={projectStatusVariant(proj.status)}>
                        {proj.status === 'active' || proj.status === 'in_progress' ? '进行中' :
                         proj.status === 'completed' || proj.status === 'done' ? '已完成' : proj.status}
                      </Badge>
                    </div>
                    {proj.description && <p className="text-xs text-slate-500 line-clamp-2">{proj.description}</p>}
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tasks list */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>任务列表</CardTitle>
            <p className="text-xs text-slate-500">{taskCount} 个任务</p>
          </CardHeader>
          <CardContent>
            {tasks.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">暂无任务</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>执行顺序</TableHead>
                    <TableHead>任务</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>分配给</TableHead>
                    <TableHead className="w-[140px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortTasksByExecutionOrder(tasks).map((task, index) => {
                    const status = getTaskStatusText(task.status!);
                    // 关键修复：传入原始状态值（如 'in_progress'），不是人类可读文本（如 '进行中'）
                    const badgeClass = getTaskStatusBadgeClass(task.status);
                    const isDone = task.status === 'done' || task.status === 'completed';
                    const isFailed = task.status === 'failed';
                    const isRunning = task.status === 'in_progress';
                    const isPaused = task.status === 'paused';

                    async function handleTaskAction(id: string, action: string) {
                      try {
                        if (action === 'start') {
                          await tasksApi.assign(id, task.assigned_agent || '');
                          toast.success('任务已开始');
                          // 本地更新状态，避免整页刷新
                          setTasks(prev => prev.map(t => t.id === id ? { ...t, status: 'todo' } : t));
                        } else if (action === 'pause') {
                          await tasksApi.pauseTask(id);
                          toast.success('任务已暂停');
                          setTasks(prev => prev.map(t => t.id === id ? { ...t, status: 'paused' } : t));
                        } else if (action === 'resume') {
                          await tasksApi.resumeTask(id);
                          toast.success('任务已恢复');
                          setTasks(prev => prev.map(t => t.id === id ? { ...t, status: 'todo' } : t));
                        } else if (action === 'retry') {
                          await tasksApi.retryTask(id);
                          toast.success('任务已重试');
                          setTasks(prev => prev.map(t => t.id === id ? { ...t, status: 'todo' } : t));
                        }
                      } catch (e: any) {
                        toast.error(`操作失败: ${e.message || '未知错误'}`);
                      }
                    }

                    return (
                      <TableRow key={task.id} className={isDone ? 'opacity-75' : ''}>
                        <TableCell>
                          <span className="text-xs font-mono text-slate-400">{index + 1}</span>
                        </TableCell>
                        <TableCell>
                          <Link to={`/coordination/tasks/${task.id}`} className={`text-sm font-medium hover:text-blue-600 ${
                            isDone ? 'text-slate-400 line-through' : 'text-slate-700'
                          }`}>
                            {task.title || '未命名任务'}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Badge className={badgeClass}>{status}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-slate-500">{task.assigned_agent ? getAgentName(task.assigned_agent) : '待分配'}</span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            {(!isDone && !isFailed && !isRunning && !isPaused) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-green-600 hover:text-green-700 hover:bg-green-50"
                                title="开始执行"
                                onClick={() => handleTaskAction(task.id, 'start')}
                                disabled={!task.assigned_agent}
                              >
                                <Play className="w-3 h-3" />
                              </Button>
                            )}
                            {isRunning && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                title="暂停"
                                onClick={() => handleTaskAction(task.id, 'pause')}
                              >
                                <Pause className="w-3 h-3" />
                              </Button>
                            )}
                            {isFailed && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                                title="重试"
                                onClick={() => handleTaskAction(task.id, 'retry')}
                              >
                                <RotateCcw className="w-3 h-3" />
                              </Button>
                            )}
                            {isPaused && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 text-green-600 hover:text-green-700 hover:bg-green-50"
                                title="恢复"
                                onClick={() => handleTaskAction(task.id, 'resume')}
                              >
                                <Play className="w-3 h-3" />
                              </Button>
                            )}
                            {isDone && (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>


      {/* Sprint 80b: 迭代历史(研究模式,传入 mode 区分视角) */}
      {mode === 'research' && id && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-blue-500" />
              <CardTitle className="text-sm">
                {'方案历史'}
              </CardTitle>
            </div>
            <CardDescription>
              {'查看方案生成历史,AI 分析与建议'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <IterationHistoryTab goalId={id!} mode={mode} />
          </CardContent>
        </Card>
      )}


      {/* Conflicts */}
      {conflicts.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-amber-500" />
              <CardTitle>冲突列表</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {conflicts.map(conflict => (
                <Card key={conflict.id} className="border-amber-200 bg-amber-50">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-amber-800">{conflict.title}</h4>
                      <Badge variant="warning">{conflict.status}</Badge>
                    </div>
                    <p className="text-sm text-amber-700 mb-2">{conflict.description}</p>
                    <div className="text-xs text-amber-600">
                      {conflict.affectedTasks.length > 0 && <p>影响任务: {conflict.affectedTasks.join(', ')}</p>}
                      {conflict.affectedAgents.length > 0 && <p>影响智能体: {conflict.affectedAgents.length} 个</p>}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Save-as-scenario dialog */}
      <SaveScenarioDialog
        preview={showSaveScenarioDialog ? scenarioPreview : null}
        onClose={() => { setShowSaveScenarioDialog(false); setScenarioPreview(null); }}
        onConfirm={confirmSaveScenario}
        loading={savingAsScenario}
        variant="goal"
      />
    </div>
  );
}
