import React, { useState, useEffect } from 'react';
import { toast } from "sonner";
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, AlertCircle, CheckCircle, XCircle, Loader2,
  PlayCircle, Clock, User, FileText, MessageSquare, Zap, Brain,
  Paperclip, Tag, ChevronDown, ChevronUp, Terminal, Settings, Shield, UserX,
} from 'lucide-react';
import { getTaskStatusText, getTaskStatusBadgeClass } from '../../../shared/utils/statusMap';
import { getAgentName } from '../../../shared/utils/agentMap';
import { tasksApi, agentsApi, goalsApi, projectsApi, disputesApi } from '../../../shared/utils/api';
import type { Task, Agent, Goal, Project, Dispute } from '../../../shared/utils/api';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/shared/components/ui/card';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/shared/components/ui/tabs';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/shared/components/ui/dialog';
import HITLConfigDialog from '@/shared/components/HITLConfigDialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/shared/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select';
import { Separator } from '@/shared/components/ui/separator';
import { EntityAttachmentPanel } from '@/reins/components/EntityAttachmentPanel';
import { TaskComments } from '@/reins/components/TaskComments';
import { TaskLabels } from '@/reins/components/TaskLabels';
import { TaskSubIssues } from '@/reins/components/TaskSubIssues';
import { TaskContext } from '@/reins/components/TaskContext';
import { TaskFailureLog } from '@/reins/components/TaskFailureLog';
import { TaskVerifications } from '@/reins/components/TaskVerifications';
import { TaskReview } from '@/reins/components/TaskReview';
import { TaskRuling } from '@/reins/components/TaskRuling';
import { TaskProgress } from '@/reins/components/TaskProgress';
import CriteriaRenderer from '@/shared/components/CriteriaRenderer';
import ReactMarkdown from 'react-markdown';

// ── Helpers ────────────────────────────────────────────────────────────────────

/**
 * 从任务描述中提取结构化区块（Done/Acceptance Criteria、依赖关系等）
 * 这些区块有独立的 DB 列或前端组件渲染，不应在 description 中重复显示
 */
function parseDescriptionBlocks(desc: string): {
  descriptionWithoutBlocks: string;
  doneCriteria: string;
  acceptanceCriteria: string;
} {
  if (!desc) return { descriptionWithoutBlocks: '', doneCriteria: '', acceptanceCriteria: '' };

  let descriptionWithoutBlocks = desc;
  let doneCriteria = '';
  let acceptanceCriteria = '';

  // 提取 Done Criteria 区块
  const doneMatch = desc.match(/##\s*Done\s*Criteria\s*\n([\s\S]*?)(?=##\s*[A-Z]|$)/i);
  if (doneMatch) {
    doneCriteria = doneMatch[1].trim();
    descriptionWithoutBlocks = descriptionWithoutBlocks.replace(doneMatch[0], '');
  }

  // 提取 Acceptance Criteria 区块
  const acceptMatch = desc.match(/##\s*Acceptance\s*Criteria\s*\n([\s\S]*?)(?=##\s*[A-Z]|$)/i);
  if (acceptMatch) {
    acceptanceCriteria = acceptMatch[1].trim();
    descriptionWithoutBlocks = descriptionWithoutBlocks.replace(acceptMatch[0], '');
  }

  // 移除 description 中的依赖关系区块（有 DB depends_on 列 + 前端渲染）
  // 匹配 "## 依赖关系" 或 "## Dependencies" 及其内容，到下一个 ## 或结尾
  descriptionWithoutBlocks = descriptionWithoutBlocks.replace(/##\s*依赖关系\s*\n([\s\S]*?)(?=##\s*[A-Z]|##\s*[\u4e00-\u9fa5]|$)/gi, '');

  // 清理多余的 `depends_on=[]` 或 `depends_on=["..."]` 行（子代理可能写在 description 里）
  descriptionWithoutBlocks = descriptionWithoutBlocks.replace(/^depends_on\s*=\s*\[.*\]\s*$/gm, '');

  // 清理多余空行
  descriptionWithoutBlocks = descriptionWithoutBlocks.replace(/\n{3,}/g, '\n\n').trim();

  return { descriptionWithoutBlocks, doneCriteria, acceptanceCriteria };
}

// ── Markdown 渲染组件 ────────────────────────────────────────────────────────

function MarkdownContent({ content, className }: { content: string; className?: string }) {
  return (
    <div className={className || 'prose prose-sm max-w-none'}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
          h4: ({ children }) => <h4 className="text-sm font-medium mt-2 mb-1">{children}</h4>,
          ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>,
          li: ({ children }) => <li className="text-slate-700">{children}</li>,
          code: ({ children }) => <code className="bg-slate-100 text-red-600 px-1 py-0.5 rounded text-xs font-mono">{children}</code>,
          pre: ({ children }) => <pre className="bg-slate-900 text-slate-100 p-3 rounded-sm overflow-x-auto my-2"><code>{children}</code></pre>,
          a: ({ href, children }) => <a href={href} className="text-blue-600 underline">{children}</a>,
          p: ({ children }) => <p className="text-slate-700 my-1.5">{children}</p>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-slate-300 pl-4 text-slate-500 italic my-2">{children}</blockquote>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function mapPriority(priority: number | string | null) {
  if (priority === null || priority === undefined) return '普通';
  const strMap: Record<string, string> = {
    'critical': '紧急', 'high': '高', 'medium': '普通', 'low': '低', 'lowest': '最低',
    '0': '紧急', '1': '高', '2': '普通', '3': '低', '4': '最低',
  };
  const key = typeof priority === 'number' ? String(priority) : String(priority).toLowerCase();
  return strMap[key] || '普通';
}

function priorityColor(priority: number | string | null) {
  const p = typeof priority === 'number' ? String(priority) : String(priority || '').toLowerCase();
  if (p === 'critical' || p === '0') return 'text-red-500';
  if (p === 'high' || p === '1') return 'text-amber-500';
  if (p === 'medium' || p === '2') return 'text-blue-500';
  return 'text-slate-400';
}

// ── Status Update Dialog ───────────────────────────────────────────────────────

interface StatusItem {
  value: string;
  label: string;
  category: 'db' | 'workflow';
  color: string;
}

function StatusUpdateDialog({ task, onClose, onSave }: { task: Task | null; onClose: () => void; onSave: (taskId: string, status: string) => Promise<void> }) {
  const [status, setStatus] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<StatusItem[]>([]);

  useEffect(() => {
    if (task) {
      setStatus(task.status || '');
      tasksApi.getStatuses()
        .then(data => { if (Array.isArray(data)) setStatuses(data); })
        .catch(() => {
          setStatuses([
            { value: 'todo', label: '待处理', category: 'db', color: 'blue' },
            { value: 'in_progress', label: '进行中', category: 'db', color: 'yellow' },
            { value: 'done', label: '已完成', category: 'db', color: 'green' },
            { value: 'failed', label: '失败', category: 'db', color: 'red' },
            { value: 'timeout', label: '已超时', category: 'db', color: 'gray' },
            { value: 'paused', label: '已暂停', category: 'db', color: 'orange' },
            { value: 'review_needed', label: '待审核', category: 'workflow', color: 'purple' },
            { value: 'verifying', label: '验证中', category: 'workflow', color: 'purple' },
            { value: 'waiting_human', label: '等待人工', category: 'workflow', color: 'purple' },
            { value: 'disputed', label: '争议中', category: 'workflow', color: 'red' },
            { value: 'blocked', label: '阻塞中', category: 'workflow', color: 'gray' },
          ]);
        });
    }
  }, [task]);

  async function handleSave() {
    if (!task) return;
    try {
      setSaving(true); setError(null);
      await onSave(task.id, status);
      onClose();
    } catch (e: any) { setError(e.message || '保存失败'); }
    finally { setSaving(false); }
  }

  if (!task) return null;

  return (
    <Dialog open={!!task} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent>
        <DialogHeader><DialogTitle>更新任务状态</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-700 mb-1">任务</p>
            <p className="text-slate-900 bg-slate-50 rounded-sm px-3 py-2 text-sm">{task.title || '未命名任务'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">新状态</label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {statuses.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label} {s.category === 'db' ? '' : '(工作流)'}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-sm px-4 py-3 text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />{error}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Assign Agent Dialog ────────────────────────────────────────────────────────

function AssignAgentDialog({ task, agents, onClose, onSave }: { task: Task | null; agents: Agent[]; onClose: () => void; onSave: (taskId: string, agent: string) => Promise<void> }) {
  const [agent, setAgent] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (task) setAgent(task.assigned_agent || ''); }, [task]);

  async function handleSave() {
    if (!task) return;
    try {
      setSaving(true); setError(null);
      await onSave(task.id, agent);
      onClose();
    } catch (e: any) { setError(e.message || '保存失败'); }
    finally { setSaving(false); }
  }

  if (!task) return null;

  return (
    <Dialog open={!!task} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent>
        <DialogHeader><DialogTitle>分配智能体</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-700 mb-1">任务</p>
            <p className="text-slate-900 bg-slate-50 rounded-sm px-3 py-2 text-sm">{task.title || '未命名任务'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">智能体</label>
            <Select value={agent} onValueChange={setAgent}>
              <SelectTrigger><SelectValue placeholder="待分配" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">待分配</SelectItem>
                {agents.map((a) => (<SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-sm px-4 py-3 text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />{error}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [executionLogs, setExecutionLogs] = useState<any[]>([]);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [activityLog, setActivityLog] = useState<any[]>([]);
  const [effectiveVerifier, setEffectiveVerifier] = useState<any>(null);
  const [verifierEditing, setVerifierEditing] = useState(false);
  const [verifierDraft, setVerifierDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'traces' | 'verifications' | 'advanced' | 'attachments' | 'events'>('details');

  // Dialog states
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  // Sprint 92: HITL dialog
  const [hitlDialogOpen, setHitlDialogOpen] = useState(false);

  function toggleLogExpand(logId: string) {
    setExpandedLogs(prev => {
      const next = new Set(prev);
      if (next.has(logId)) next.delete(logId); else next.add(logId);
      return next;
    });
  }

  // 解析日志输入/输出内容，提取可读摘要
  function getLogInputSummary(log: any): string {
    const input = log.input || {};
    if (input.task_title) return `任务: ${input.task_title}`;
    if (input.description) return input.description.slice(0, 200);
    if (Object.keys(input).length > 0) return JSON.stringify(input).slice(0, 200);
    return '—';
  }

  function getLogOutputSummary(log: any): string {
    const output = log.output || {};
    if (output.result_summary) return output.result_summary.slice(0, 300);
    if (output.message) return String(output.message).slice(0, 200);
    if (output.error) return String(output.error).slice(0, 200);
    if (Object.keys(output).length > 0) return JSON.stringify(output).slice(0, 200);
    return '—';
  }

  // 提取失败原因
  function getFailureReason(log: any): string {
    const output = log.output || {};
    const errMsg = log.error_message || '';
    const exitCode = output.exit_code ?? log.exit_code;
    if (errMsg) return `[exit=${exitCode}] ${errMsg}`;
    if (exitCode !== undefined) return `exit code: ${exitCode}`;
    return '未知原因';
  }

  async function fetchData() {
    if (!id) return;
    try {
      setLoading(true); setError(null);
      const [taskData, allAgents, allDisputes] = await Promise.all([
        tasksApi.get(id),
        agentsApi.list().catch(() => [] as Agent[]),
        disputesApi.list().catch(() => [] as Dispute[]),
      ]);
      setTask(taskData);
      setAgents(allAgents);
      setDisputes(allDisputes.filter((d: Dispute) => d.related_task_id === id));

      if (taskData.goal_id) { try { setGoal(await goalsApi.get(taskData.goal_id)); } catch { /* */ } }
      if (taskData.project_id) { try { setProject(await projectsApi.get(taskData.project_id)); } catch { /* */ } }

      // Fetch execution logs
      try {
        const execData = await tasksApi.getExecutionLogs(id, 50);
        setExecutionLogs(Array.isArray(execData) ? execData : (execData.logs || []));
      } catch { /* */ }

      // Fetch activity log
      try {
        const activityData = await tasksApi.getActivity(id);
        setActivityLog(Array.isArray(activityData) ? activityData : []);
      } catch { /* */ }

      // Fetch effective verifier
      try {
        const v = await tasksApi.getVerifier(id);
        setEffectiveVerifier(v); setVerifierDraft(v.effective_verifier || '');
      } catch { /* */ }
    } catch (e: any) { setError(e.message || '任务详情加载失败'); }
    finally { setLoading(false); }
  }

  useEffect(() => { fetchData(); }, [id]);

  async function handleUpdateStatus(taskId: string, status: string) {
    await tasksApi.updateStatus(taskId, status);
    await fetchData();
  }

  async function handleAssignAgent(taskId: string, agent: string) {
    await tasksApi.assign(taskId, agent);
    await fetchData();
  }

  async function handleCompleteTask() {
    if (!task) return;
    try {
      await tasksApi.completeTask(task.id, { status: 'done' });
      await fetchData();
    } catch (e: any) { toast.error('完成任务失败: ' + (e.message || '未知错误')); }
  }

  async function handleFailTask() {
    if (!task) return;
    try {
      await tasksApi.failTask(task.id, { error_type: 'user_cancelled', error_message: '用户手动标记为失败', retry_count: 0, max_retries: 3 });
      await fetchData();
    } catch (e: any) { toast.error('标记失败: ' + (e.message || '未知错误')); }
  }

  async function handleRetryTask() {
    if (!task) return;
    try { await tasksApi.retryTask(task.id); await fetchData(); }
    catch (e: any) { toast.error('重试失败: ' + (e.message || '未知错误')); }
  }

  async function handlePauseTask() {
    if (!task) return;
    try { await tasksApi.pauseTask(task.id); toast.success('已暂停'); await fetchData(); }
    catch { toast.error('暂停失败'); }
  }

  async function handleResumeTask() {
    if (!task) return;
    try { await tasksApi.resumeTask(task.id); toast.success('已恢复'); await fetchData(); }
    catch { toast.error('恢复失败'); }
  }

  // Sprint 92: 终止任务
  async function handleTerminateTask() {
    if (!task) return;
    if (!confirm(`确定要终止任务 ${task.id.slice(0, 8)} 吗？此操作不可恢复。`)) return;
    try {
      const r = await fetch(`/api/v1/tasks/${task.id}/terminate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: '人工终止' }),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.message || e.detail || '终止失败'); }
      toast.success('已终止');
      await fetchData();
    } catch (e: any) { toast.error(e.message); }
  }

  // Sprint 92: 人工接管
  async function handleTakeoverTask() {
    if (!task) return;
    if (!confirm(`确定要接管任务 ${task.id.slice(0, 8)} 吗？任务将被暂停。`)) return;
    try {
      const r = await fetch(`/api/v1/tasks/${task.id}/takeover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: '人工接管' }),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.message || e.detail || '接管失败'); }
      toast.success('已接管（任务已暂停）');
      await fetchData();
    } catch (e: any) { toast.error(e.message); }
  }

  // Sprint 92: 添加 HITL 审批
  async function handleHitlSave(config: any) {
    if (!task) return;
    try {
      const r = await fetch(`/api/v1/tasks/${task.id}/add-hitl`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: config.title || `人工审批: ${task.title}`,
          description: config.description,
          input_type: 'approval',
          assigned_to: config.approvers?.join(', ') || undefined,
          timeout_minutes: config.timeout_minutes || 30,
        }),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.message || e.detail || '添加 HITL 失败'); }
      toast.success('已添加 HITL 审批');
      await fetchData();
    } catch (e: any) { toast.error(e.message); }
  }

  async function handleSaveVerifier() {
    if (!task) return;
    try {
      await tasksApi.update(task.id, { verifier_agent_id: verifierDraft || null });
      setVerifierEditing(false);
      await fetchData();
    } catch (e: any) { toast.error('保存失败: ' + e.message); }
  }

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>;

  if (error || !task) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-900">{error || '任务不存在'}</h2>
        <Link to="/coordination/tasks" className="text-blue-600 hover:underline mt-4 inline-block">返回任务列表</Link>
      </div>
    );
  }

  const statusText = getTaskStatusText(task.status);
  const isActionable = ['pending', 'todo', 'in_progress', 'running', 'active'].includes(task.status || '');
  const isFailed = task.status === 'failed';
  const isPaused = task.status === 'paused';
  const taskDisputes = disputes.filter((d: Dispute) => d.related_task_id === id);

  const formatDate = (dateStr: string | number | null) => {
    if (!dateStr) return '—';
    // Handle Unix timestamp (seconds) — detect by checking if it's a small number (< year 3000 in ms)
    const ts = typeof dateStr === 'number'
      ? (dateStr < 1e12 ? dateStr * 1000 : dateStr) // seconds → ms
      : typeof dateStr === 'string' && /^\d+$/.test(dateStr)
      ? (parseInt(dateStr, 10) < 1e12 ? parseInt(dateStr, 10) * 1000 : parseInt(dateStr, 10))
      : dateStr;
    return new Date(ts).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" asChild><Link to="/coordination/tasks"><ArrowLeft className="w-4 h-4" /></Link></Button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="mono text-sm font-bold text-slate-500">#{String(task.id).slice(0, 8)}</span>
            <Badge className={getTaskStatusBadgeClass(task.status)}>{statusText}</Badge>
            <Badge variant="secondary">{mapPriority(task.priority)}</Badge>
            {/* Sprint 92 F92-1: HITL审批按钮 */}
            {['todo', 'in_progress', 'paused'].includes(task.status || '') && (
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-xs text-blue-600 border-blue-300 hover:bg-blue-50"
                onClick={() => setHitlDialogOpen(true)}
              >
                <Shield className="w-3 h-3 mr-1" />加审批
              </Button>
            )}
            {(task.status === 'done' || task.status === 'failed') && (
              <Badge variant="outline" className="text-xs text-slate-400">已结束</Badge>
            )}
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">{task.title || '未命名任务'}</h2>
          {task.assigned_agent && (
            <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
              <User className="w-3 h-3" />{getAgentName(task.assigned_agent)}
            </p>
          )}
          {/* 验证智能体 */}
          {effectiveVerifier && (
            <div className="mt-1.5 flex items-center gap-2">
              <span className="text-xs text-slate-400">验证智能体：</span>
              {verifierEditing ? (
                <div className="flex items-center gap-1">
                  <Select value={verifierDraft || '__none__'} onValueChange={(v) => setVerifierDraft(v === '__none__' ? '' : v)}>
                    <SelectTrigger className="h-6 w-28 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3745f1f0-b67d-4287-a10b-e71b3ff17e97">扣子 (默认)</SelectItem>
                      <SelectItem value="876b9322-0fbe-4cd0-97c2-9244a4e3b905">谷子</SelectItem>
                      <SelectItem value="9d899c03-4ada-45a7-805a-b2f0fb4ebb24">麻子</SelectItem>
                      <SelectItem value="8817e140-2c46-40d8-9444-a6bca8a8e8fb">蚊子</SelectItem>
                      <SelectItem value="__none__">不使用</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={handleSaveVerifier}>保存</Button>
                  <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={() => setVerifierEditing(false)}>取消</Button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <Badge variant={effectiveVerifier.effective_verifier ? 'secondary' : 'outline'} className="text-xs">
                    {effectiveVerifier.effective_verifier ? getAgentName(effectiveVerifier.effective_verifier) : '未设置'}
                  </Badge>
                  {effectiveVerifier.inheritance_chain && (
                    <span className="text-xs text-slate-400">
                      {effectiveVerifier.inheritance_chain.task_verifier ? '(任务级)' :
                       effectiveVerifier.inheritance_chain.project_verifier ? '(工程级)' :
                       effectiveVerifier.inheritance_chain.goal_verifier ? `(目标级继承: ${getAgentName(effectiveVerifier.inheritance_chain.goal_verifier) || effectiveVerifier.inheritance_chain.goal_verifier})` :
                       '(默认)'}
                    </span>
                  )}
                  <Button size="sm" variant="ghost" className="h-5 text-xs px-1" onClick={() => setVerifierEditing(true)}>修改</Button>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          {isActionable && <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={handleCompleteTask}><CheckCircle className="w-4 h-4" />完成</Button>}
          {isActionable && <Button size="sm" variant="destructive" onClick={handleFailTask}><XCircle className="w-4 h-4" />标记失败</Button>}
          {isFailed && <Button size="sm" onClick={handleRetryTask}><RefreshCw className="w-4 h-4" />重试</Button>}
          {/* Sprint 92 F92-2: Runtime control buttons */}
          {task.status === 'in_progress' && <Button size="sm" variant="outline" onClick={handlePauseTask}><Zap className="w-4 h-4" />暂停</Button>}
          {task.status === 'in_progress' && <Button size="sm" variant="outline" className="text-orange-600 border-orange-300 hover:bg-orange-50" onClick={handleTerminateTask}><XCircle className="w-4 h-4" />终止</Button>}
          {task.status === 'in_progress' && <Button size="sm" variant="outline" className="text-purple-600 border-purple-300 hover:bg-purple-50" onClick={handleTakeoverTask}><UserX className="w-4 h-4" />接管</Button>}
          {isPaused && <Button size="sm" variant="outline" onClick={handleResumeTask}><PlayCircle className="w-4 h-4" />恢复</Button>}
          {/* Sprint 92 F92-1: Add HITL button */}
          {['todo', 'in_progress', 'paused'].includes(task.status || '') && (
            <Button size="sm" variant="outline" className="text-blue-600 border-blue-300 hover:bg-blue-50" onClick={() => setHitlDialogOpen(true)}>
              <Shield className="w-4 h-4" />加审批
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setStatusDialogOpen(true)}>更新状态</Button>
          <Button variant="outline" size="sm" onClick={() => setAssignDialogOpen(true)}>分配</Button>
          <Button variant="outline" size="sm" onClick={fetchData}><RefreshCw className="w-4 h-4" /></Button>
        </div>
      </div>

      {/* Task Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <div className="flex gap-2 border-b border-slate-200 pb-0">
          <TabsList className="bg-transparent p-0 h-auto rounded-none">
            <TabsTrigger value="details" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700"><FileText className="w-4 h-4" />详情</TabsTrigger>
            <TabsTrigger value="traces" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700"><Zap className="w-4 h-4" />执行记录</TabsTrigger>
            <TabsTrigger value="verifications" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700"><MessageSquare className="w-4 h-4" />任务讨论</TabsTrigger>
            <TabsTrigger value="attachments" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700"><Paperclip className="w-4 h-4" />附件</TabsTrigger>
            <TabsTrigger value="advanced" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700"><Brain className="w-4 h-4" />高级</TabsTrigger>
            <TabsTrigger value="events" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700"><Clock className="w-4 h-4" />事件</TabsTrigger>
          </TabsList>
        </div>

        {/* Attachments tab */}
        <TabsContent value="attachments"><EntityAttachmentPanel entityType="task" entityId={task.id} /></TabsContent>

        {/* Details tab */}
        <TabsContent value="details">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main info */}
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>基本信息</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {task.description && (
                  (() => {
                    const parsed = parseDescriptionBlocks(task.description);
                    return (
                      <>
                        {parsed.descriptionWithoutBlocks && (
                          <div>
                            <h4 className="text-sm font-medium text-slate-500 mb-1">描述</h4>
                            <MarkdownContent content={parsed.descriptionWithoutBlocks} />
                          </div>
                        )}
                      </>
                    );
                  })()
                )}
                {/* 依赖关系（DB depends_on 列，不从 description 提取） */}
                <div>
                  <h4 className="text-sm font-medium text-slate-500 mb-2">🔗 依赖关系</h4>
                  {task.depends_on && task.depends_on.length > 0 ? (
                    <div className="space-y-1">
                      {(task.depends_on as string[]).map((depId: string) => (
                        <div key={depId} className="flex items-center gap-2 text-sm">
                          <span className="text-xs text-slate-400">前置任务:</span>
                          <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">{depId.slice(0, 12)}</code>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400">独立任务，无前置依赖</p>
                  )}
                </div>
                {/* Acceptance Criteria → 验收标准（DB 列） */}
                {task.acceptance_criteria && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-2">🎯 验收标准</h4>
                    <div className="p-3 bg-blue-50 rounded-sm border border-blue-200">
                      <CriteriaRenderer value={task.acceptance_criteria} badgeClass="bg-blue-100 text-blue-700" defaultLabel="验收" />
                    </div>
                  </div>
                )}
                {/* Delivery Criteria → 交付标准（DB 列） */}
                <div>
                  <h4 className="text-sm font-medium text-slate-500 mb-2">📦 交付标准</h4>
                  {task.delivery_criteria ? (
                    <div className="p-3 bg-orange-50 rounded-sm border border-orange-200">
                      <CriteriaRenderer value={task.delivery_criteria} badgeClass="bg-orange-100 text-orange-700" defaultLabel="交付" />
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400">未设置</p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: '状态', value: statusText },
                    { label: '优先级', value: mapPriority(task.priority) },
                    { label: '分配给', value: getAgentName(task.assigned_agent) || '—' },
                    { label: '验证者', value: effectiveVerifier?.effective_verifier ? getAgentName(effectiveVerifier.effective_verifier) : '—' },
                    { label: '截止日期', value: task.due_date || '—' },
                    { label: '创建时间', value: formatDate(task.created_at) },
                    { label: '更新时间', value: formatDate(task.updated_at) },
                    { label: '重试次数', value: String(task.retry_count ?? 0) },
                  ].map(row => (
                    <div key={row.label}>
                      <p className="text-xs font-medium text-slate-500">{row.label}</p>
                      <p className={`text-sm text-slate-800 ${priorityColor(task.priority)}`}>{row.value}</p>
                    </div>
                  ))}
                </div>
                {(() => {
                  const rawTags = (task.capability_tags || {}) as Record<string, any>
                  const hasTags = Object.values(rawTags).some((v: any) => Array.isArray(v) ? v.length > 0 : typeof v === 'string' && v.length > 0)
                  if (!hasTags) return null
                  return (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-2 flex items-center gap-1">
                      <Tag className="w-3 h-3" />能力标签
                    </h4>
                    <div className="space-y-1.5">
                      {([
                        { key: 'business', label: '业务', color: 'bg-blue-100 text-blue-700' },
                        { key: 'professional', label: '专业', color: 'bg-purple-100 text-purple-700' },
                        { key: 'technical', label: '技术', color: 'bg-green-100 text-green-700' },
                        { key: 'management', label: '管理', color: 'bg-amber-100 text-amber-700' },
                      ] as const).map(dim => {
                        const raw = task.capability_tags?.[dim.key]
                        const items = Array.isArray(raw) ? raw : (typeof raw === 'string' ? [raw] : [])
                        if (items.length === 0) return null
                        return (
                          <div key={dim.key} className="flex items-center gap-2">
                            <span className="text-xs font-medium text-slate-400 min-w-[32px]">{dim.label}</span>
                            <div className="flex flex-wrap gap-1">
                              {items.map((cap, i) => (
                                <Badge key={`${cap}-${i}`} variant="secondary" className={`text-xs ${dim.color}`}>{cap}</Badge>
                              ))}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                  )
                })()}
                {(() => {
                  const rawRefs = task.doc_refs as string | string[] | undefined
                  const refs: string[] = Array.isArray(rawRefs) ? rawRefs as string[] : (typeof rawRefs === 'string' ? (rawRefs as string).split(',').map((s: string) => s.trim()).filter(Boolean) : [])
                  if (refs.length === 0) return null
                  return (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-2">文档引用</h4>
                    <div className="space-y-1">
                      {refs.map((ref, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          <FileText className="w-3 h-3 mt-1 text-slate-400" />
                          <span className="text-blue-600 font-mono">{ref}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  )
                })()}
                {task.workspace_path && (
                  <div>
                    <h4 className="text-sm font-medium text-slate-500 mb-1">工作目录</h4>
                    <p className="text-sm text-slate-700 font-mono bg-slate-50 px-3 py-2 rounded-sm">{task.workspace_path}</p>
                  </div>
                )}
                {task.error_message && (
                  <div className="bg-red-50 border border-red-200 rounded-sm p-3">
                    <h4 className="text-sm font-medium text-red-600 mb-1">错误信息</h4>
                    <p className="text-sm text-red-700 whitespace-pre-wrap">{task.error_message}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Sidebar */}
            <div className="space-y-6">
              {goal && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">关联目标</CardTitle></CardHeader>
                  <CardContent>
                    <Link to={`/coordination/goals/${goal.id}`} className="text-sm text-blue-600 hover:underline flex items-center gap-1"><Brain className="w-3 h-3" />{goal.title || '未命名目标'}</Link>
                  </CardContent>
                </Card>
              )}
              {project && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm">关联工程</CardTitle></CardHeader>
                  <CardContent>
                    <Link to={`/coordination/projects/${project.id}`} className="text-sm text-blue-600 hover:underline">{project.name}</Link>
                  </CardContent>
                </Card>
              )}
              {taskDisputes.length > 0 && (
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm text-amber-600">争议告警</CardTitle></CardHeader>
                  <CardContent className="space-y-3">
                    {taskDisputes.map((d) => (
                      <div key={d.id} className="p-3 bg-amber-50 rounded-sm border border-amber-200">
                        <p className="text-sm font-medium text-amber-800">{d.description || '任务存在争议'}</p>
                        <p className="text-xs text-amber-600 mt-1">{d.status}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm">快捷操作</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setStatusDialogOpen(true)}>更新状态</Button>
                  <Button variant="outline" size="sm" className="w-full justify-start" onClick={() => setAssignDialogOpen(true)}>分配智能体</Button>
                  <TaskReview taskId={task.id} onRefresh={fetchData} />
                  <TaskRuling taskId={task.id} onRefresh={fetchData} />
                  <TaskProgress taskId={task.id} onRefresh={fetchData} />
                  <Button variant="outline" size="sm" className="w-full justify-start" asChild><Link to="/coordination/tasks">返回列表</Link></Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Traces tab */}
        <TabsContent value="traces">
          <Card>
            <CardHeader>
              <CardTitle>执行记录</CardTitle>
              <p className="text-xs text-muted-foreground font-normal mt-1">任务执行过程中的操作日志，点击展开可查看系统消息和 Agent 返回的完整内容</p>
            </CardHeader>
            <CardContent>
              {executionLogs.length === 0 ? (
                <div className="text-center py-12 text-slate-400"><Zap className="w-12 h-12 mx-auto mb-3 opacity-50" /><p className="text-lg mb-2">暂无执行记录</p></div>
              ) : (
                <div className="space-y-2">
                  {executionLogs.map((log) => {
                    const actionLabels: Record<string, string> = {
                      heartbeat: '💓 心跳', task_assign: '📋 任务分配', task_execute: '⚡ 任务执行',
                      task_progress: '📊 进度更新', task_start: '🚀 任务开始',
                      task_complete: '✅ 任务完成', task_fail: '❌ 任务失败',
                    };
                    const isFailed = log.status === 'error' || log.status === 'failed';
                    const isExpanded = expandedLogs.has(log.id);
                    const inputSummary = getLogInputSummary(log);
                    const outputSummary = getLogOutputSummary(log);
                    const failureReason = isFailed ? getFailureReason(log) : '';

                    return (
                      <div key={log.id} className={`border rounded-lg overflow-hidden ${isFailed ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white'}`}>
                        {/* Summary row — always visible */}
                        <div
                          className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 ${isFailed ? 'bg-red-50' : ''}`}
                          onClick={() => toggleLogExpand(log.id)}
                        >
                          <Button variant="ghost" size="sm" className="p-0 h-5 w-5" onClick={(e) => { e.stopPropagation(); toggleLogExpand(log.id); }}>
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </Button>
                          <span className="text-xs text-slate-500 w-36 shrink-0">{formatDate(log.created_at)}</span>
                          <Badge variant={isFailed ? 'destructive' : 'secondary'} className="text-xs shrink-0">
                            {actionLabels[log.action] || log.action}
                          </Badge>
                          <span className="text-xs text-slate-600 w-20 shrink-0">{getAgentName(log.agent_id) || '—'}</span>
                          <Badge variant={log.status === 'success' ? 'success' : isFailed ? 'destructive' : 'info'} className="text-xs shrink-0">
                            {log.status === 'success' ? '成功' : isFailed ? '失败' : log.status}
                          </Badge>
                          <span className="text-xs text-slate-500 w-20 shrink-0">{log.duration_ms ? `${log.duration_ms}ms` : '—'}</span>
                          {isFailed && failureReason ? (
                            <span className="text-xs text-red-600 font-medium truncate flex-1">{failureReason}</span>
                          ) : (
                            <span className="text-xs text-slate-500 truncate flex-1">{inputSummary}</span>
                          )}
                        </div>

                        {/* Expanded detail view */}
                        {isExpanded && (
                          <div className={`px-4 pb-4 pt-2 border-t ${isFailed ? 'border-red-200' : 'border-slate-200'}`}>
                            {/* 发送的消息 */}
                            {log.input && Object.keys(log.input).length > 0 && (
                              <div className="mb-3">
                                <div className="flex items-center gap-1.5 mb-1">
                                  <Terminal className="w-3.5 h-3.5 text-blue-500" />
                                  <span className="text-xs font-medium text-blue-600">📤 系统 → Agent</span>
                                </div>
                                <div className="bg-blue-50 border border-blue-200 rounded p-3">
                                  {log.input.task_title && (
                                    <p className="text-xs font-medium text-blue-800 mb-1">【任务】{log.input.task_title}</p>
                                  )}
                                  {log.input.task_description && (
                                    <p className="text-xs text-blue-700 whitespace-pre-wrap">{log.input.task_description}</p>
                                  )}
                                  {log.input.description && !log.input.task_title && (
                                    <p className="text-xs text-blue-700 whitespace-pre-wrap">{log.input.description}</p>
                                  )}
                                  {log.input.goal_title && (
                                    <p className="text-xs text-blue-600 mt-1">目标: {log.input.goal_title}</p>
                                  )}
                                  {log.input.project_name && (
                                    <p className="text-xs text-blue-600">项目: {log.input.project_name}</p>
                                  )}
                                  {Object.keys(log.input).filter(k => !['task_title','task_description','description','goal_title','project_name'].includes(k)).length > 0 && (
                                    <details className="mt-2">
                                      <summary className="text-xs text-blue-500 cursor-pointer">其他字段</summary>
                                      <pre className="text-xs text-slate-600 mt-1 whitespace-pre-wrap">{JSON.stringify(log.input, null, 2)}</pre>
                                    </details>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Agent 的返回 */}
                            {log.output && Object.keys(log.output).length > 0 && (
                              <div className="mb-3">
                                <div className="flex items-center gap-1.5 mb-1">
                                  <Terminal className="w-3.5 h-3.5 text-green-500" />
                                  <span className="text-xs font-medium text-green-600">📥 Agent 返回</span>
                                </div>
                                <div className={`border rounded p-3 ${isFailed ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                                  {log.output.result_summary && (
                                    <pre className={`text-xs whitespace-pre-wrap ${isFailed ? 'text-red-700' : 'text-green-700'}`}>{log.output.result_summary}</pre>
                                  )}
                                  {log.output.message && !log.output.result_summary && (
                                    <p className={`text-xs ${isFailed ? 'text-red-700' : 'text-green-700'}`}>{log.output.message}</p>
                                  )}
                                  {log.output.exit_code !== undefined && (
                                    <p className={`text-xs font-medium mt-1 ${isFailed ? 'text-red-700' : 'text-green-700'}`}>exit code: {log.output.exit_code}</p>
                                  )}
                                  {Object.keys(log.output).filter(k => !['result_summary','message','exit_code'].includes(k)).length > 0 && (
                                    <details className="mt-2">
                                      <summary className="text-xs text-slate-500 cursor-pointer">完整输出</summary>
                                      <pre className="text-xs text-slate-600 mt-1 whitespace-pre-wrap">{JSON.stringify(log.output, null, 2)}</pre>
                                    </details>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* 失败原因高亮 */}
                            {isFailed && failureReason && (
                              <div className="bg-red-100 border border-red-300 rounded p-3">
                                <p className="text-xs font-medium text-red-700 mb-1">❌ 失败原因</p>
                                <p className="text-xs text-red-600 whitespace-pre-wrap">{failureReason}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Verifications/Discussion tab */}
        <TabsContent value="verifications">
          <Card>
            <CardHeader>
              <CardTitle>任务讨论</CardTitle>
              <p className="text-xs text-muted-foreground font-normal mt-1">验证结果、人类评论、执行者响应。人类评论会触发执行者重新派发任务。</p>
            </CardHeader>
            <CardContent>
              <TaskComments taskId={task.id} onRefresh={fetchData} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Advanced tab */}
        <TabsContent value="advanced">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              <TaskLabels taskId={task.id} />
              <TaskSubIssues taskId={task.id} />
              <TaskContext taskId={task.id} />
            </div>
            <div className="space-y-6">
              <TaskFailureLog taskId={task.id} />
              <TaskVerifications taskId={task.id} />
            </div>
          </div>
        </TabsContent>

        {/* Events tab */}
        <TabsContent value="events">
          <Card>
            <CardHeader>
              <CardTitle>事件日志</CardTitle>
              <p className="text-xs text-muted-foreground font-normal mt-1">任务状态变更历史（由 scheduler 写入）</p>
            </CardHeader>
            <CardContent>
              {activityLog.length === 0 ? (
                <div className="text-center py-12 text-slate-400"><Clock className="w-12 h-12 mx-auto mb-3 opacity-50" /><p className="text-lg mb-2">暂无事件记录</p></div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead><TableHead>操作人</TableHead><TableHead>旧状态</TableHead><TableHead>新状态</TableHead><TableHead>原因</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {activityLog.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="text-xs text-slate-500">{formatDate(log.timestamp)}</TableCell>
                        <TableCell className="text-xs">{log.actor ? getAgentName(log.actor) : '-'}</TableCell>
                        <TableCell><Badge variant="outline" className="text-xs">{getTaskStatusText(log.old_status)}</Badge></TableCell>
                        <TableCell><Badge variant="info" className="text-xs">{getTaskStatusText(log.new_status)}</Badge></TableCell>
                        <TableCell className="text-xs text-slate-600 max-w-[200px] truncate">{log.reason || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <StatusUpdateDialog task={statusDialogOpen ? task : null} onClose={() => setStatusDialogOpen(false)} onSave={handleUpdateStatus} />
      <AssignAgentDialog task={assignDialogOpen ? task : null} agents={agents} onClose={() => setAssignDialogOpen(false)} onSave={handleAssignAgent} />
      {/* Sprint 92 F92-1: HITL Config Dialog */}
      <HITLConfigDialog
        open={hitlDialogOpen}
        taskTitle={task?.title || ''}
        onClose={() => setHitlDialogOpen(false)}
        onSave={handleHitlSave}
      />
    </div>
  );
}

export { TaskDetail as TaskDetailPage };
