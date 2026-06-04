import { useState, useEffect } from 'react';
import { SCENARIOS, WORKFLOWS } from '../../../shared/api/paths';
import { toast } from "sonner";
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, AlertCircle, Loader2, CheckCircle, ExternalLink,
  Star, GitBranch, Activity, Clock, FileText, PlayCircle,
  BarChart3, Settings, Trash2, Plus, Code, Edit3, Tag, Save, X,
  ChevronDown, ChevronRight, User, Zap, Layers, Copy, XCircle,
} from 'lucide-react';
import { scenariosApi, request } from '../../../shared/utils/api';
import type { Scenario, ScenarioStep, ScenarioTask, ConditionType, ScenarioProject, ScenarioProjectTask } from '../../../shared/utils/scenariosApi';
import ScenarioProjectDialog from '@/reach/components/ScenarioProjectDialog';
import ScenarioTaskDialog from '@/reach/components/ScenarioTaskDialog';
import HITLConfigDialog from '../../../shared/components/HITLConfigDialog';
import type { ScenarioProjectFormData } from '@/reach/components/ScenarioProjectDialog';
import type { ScenarioTaskFormData } from '@/reach/components/ScenarioTaskDialog';

// ─ Safe parse helpers (API returns JSON strings, not arrays) ─────────────────

function safeParseList(val: unknown): string[] {
  if (Array.isArray(val)) return val;
  if (typeof val === 'string') {
    try { return JSON.parse(val); } catch { return []; }
  }
  return [];
}

// Extended scenario type with optional fields used in UI
interface ScenarioExtended extends Scenario {
  source?: string;
  trust_level?: string;
}
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { executorTypeLabel } from '@/shared/utils/scenariosApi';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription,
} from '@/shared/components/ui/dialog';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/shared/components/ui/table';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/shared/components/ui/tabs';
import { Input } from '@/shared/components/ui/input';
import { Separator } from '@/shared/components/ui/separator';
import { Progress } from '@/shared/components/ui/progress';
import { Textarea } from '@/shared/components/ui/textarea';
import { Label } from '@/shared/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select';

// ── Condition Type Helpers ──────────────────────────────────────────────────────

const CONDITION_CONFIG: Record<ConditionType, { label: string; icon: string; variant: string; bgClass: string; textClass: string; badgeClass: string }> = {
  none:           { label: '无条件',   icon: '✅', variant: 'secondary', bgClass: 'bg-slate-100', textClass: 'text-slate-600', badgeClass: 'bg-slate-100 text-slate-600 border-slate-200' },
  auto_eval:     { label: '自动评估', icon: '🔵', variant: 'default',   bgClass: 'bg-blue-50',   textClass: 'text-blue-700',   badgeClass: 'bg-blue-100 text-blue-700 border-blue-200' },
  human_decision:{ label: '人工决策', icon: '🟠', variant: 'warning',   bgClass: 'bg-orange-50', textClass: 'text-orange-700', badgeClass: 'bg-orange-100 text-orange-700 border-orange-200' },
  human_input:   { label: '人工输入', icon: '🟢', variant: 'secondary', bgClass: 'bg-green-50',  textClass: 'text-green-700',  badgeClass: 'bg-green-100 text-green-700 border-green-200' },
};

function ConditionBadge({ type }: { type: ConditionType | string }) {
  const cfg = CONDITION_CONFIG[type as ConditionType] || CONDITION_CONFIG.none;
  return (
    <Badge variant="outline" className={`text-xs font-medium ${cfg.badgeClass}`}>
      {cfg.icon} {cfg.label}
    </Badge>
  );
}

function ConditionDataViewer({ data, label = '条件数据' }: { data: Record<string, any> | null | undefined; label?: string }) {
  const [expanded, setExpanded] = useState(false);
  if (!data) return null;
  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors"
      >
        {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        {label}
      </button>
      {expanded && (
        <pre className="mt-1 bg-slate-900 text-slate-100 rounded-lg p-3 text-xs overflow-x-auto max-h-48 overflow-y-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ── Badges ──────────────────────────────────────────────────────────────────────

function getBadgeVariant(status: string | undefined): any {
  const map: Record<string, string> = {
    active: 'success', archived: 'secondary', draft: 'warning', deprecated: 'destructive',
  };
  return (map[status || ''] || 'secondary') as any;
}

function getCategoryVariant(category: string | undefined): any {
  const map: Record<string, string> = {
    earthquake: 'destructive', fire: 'warning', chemical: 'secondary',
    flood: 'info', general: 'secondary',
  };
  return (map[category || ''] || 'secondary') as any;
}

const CATEGORY_LABELS: Record<string, string> = {
  earthquake: '地震', fire: '火灾', chemical: '化学品',
  flood: '防汛', general: '通用',
};

const SOURCE_LABELS: Record<string, string> = {
  manual: '手动创建', ai_generated: 'AI生成', execution_flowback: '执行回流',
  cognitive_derived: '认知推导', execution_derived: '执行推导',
  template: '模板创建', evolved: '自动演化',
};

const CONDITION_OPTIONS: ConditionType[] = ['none', 'auto_eval', 'human_decision', 'human_input'];

// ── Task Card ───────────────────────────────────────────────────────────────────

function TaskCard({ task, index, total }: { task: ScenarioTask; index: number; total: number }) {
  const deps = safeParseList(task.dependencies);
  const caps = safeParseList(task.required_capabilities);
  return (
    <div className={`ml-6 pl-4 border-l-2 border-slate-200 ${index < total - 1 ? 'pb-3' : ''}`}>
      <div className="flex items-start gap-2">
        <div className="mt-1.5 w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold shrink-0">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800">{task.name}</span>
            <ConditionBadge type={task.condition_type} />
          </div>
          {task.description && (
            <p className="text-xs text-slate-500 mt-0.5">{task.description}</p>
          )}
          <div className="flex items-center gap-3 mt-1.5 flex-wrap text-xs text-slate-400">
            {task.agent_type && (
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" /> {task.agent_type}
              </span>
            )}
            {deps.length > 0 && (
              <span className="flex items-center gap-1">
                <Layers className="w-3 h-3" /> 依赖: {deps.join(', ')}
              </span>
            )}
            {caps.length > 0 && (
              <span className="flex items-center gap-1">
                <Zap className="w-3 h-3" /> {caps.join(', ')}
              </span>
            )}
          </div>
          <ConditionDataViewer data={task.condition_data} label="任务条件数据" />
        </div>
      </div>
    </div>
  );
}

// ── Project (Step) Tab Content ─────────────────────────────────────────────────

function ProjectTabContent({ step, tasks, onUpdateStep, onDeleteStep, onAddTask, onUpdateTask, onDeleteTask }: {
  step: ScenarioStep;
  tasks: ScenarioTask[];
  onUpdateStep: (data: Partial<ScenarioStep>) => void;
  onDeleteStep: () => void;
  onAddTask: () => void;
  onUpdateTask: (taskId: string, data: Partial<ScenarioTask>) => void;
  onDeleteTask: (taskId: string) => void;
}) {
  const stepTasks = tasks
    .filter(t => t.phase_name === step.name)
    .sort((a, b) => (a.order_in_phase ?? 0) - (b.order_in_phase ?? 0));

  const stepCaps = safeParseList(step.required_capabilities);

  return (
    <div className="space-y-4">
      {/* Step header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-bold">
            {step.name}
          </span>
          <ConditionBadge type={step.condition_type} />
          <span className="text-xs text-slate-400">
            {stepTasks.length} 个任务
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-slate-500">
          {step.agent_type && (
            <span className="flex items-center gap-1">
              <User className="w-3.5 h-3.5" /> {step.agent_type}
            </span>
          )}
          {stepCaps.length > 0 && (
            <span className="flex items-center gap-1">
              <Zap className="w-3.5 h-3.5" /> {stepCaps.join(', ')}
            </span>
          )}
        </div>
      </div>
      <ConditionDataViewer data={step.condition_data} label="步骤条件数据" />

      {/* Step inline editor */}
      <div className="flex gap-2">
        <StepEditor
          step={step}
          tasks={stepTasks}
          onUpdate={onUpdateStep}
          onDelete={onDeleteStep}
          onAddTask={onAddTask}
        />
      </div>

      {/* Tasks table */}
      {stepTasks.length > 0 ? (
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>任务名称</TableHead>
                <TableHead>描述</TableHead>
                <TableHead>执行者</TableHead>
                <TableHead>执行模式</TableHead>
                <TableHead>条件类型</TableHead>
                <TableHead>依赖</TableHead>
                <TableHead className="w-20">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stepTasks.map((task, i) => {
                const caps = safeParseList(task.required_capabilities);
                const deps = safeParseList(task.dependencies);
                return (
                  <TableRow key={task.id}>
                    <TableCell className="text-xs text-slate-400">{i + 1}</TableCell>
                    <TableCell>
                      <span className="text-sm font-medium text-slate-800">{task.name}</span>
                      {caps.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {caps.map((cap, ci) => (
                            <Badge key={ci} variant="outline" className="text-[10px]">{cap}</Badge>
                          ))}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 max-w-[200px] truncate">
                      {task.description || '—'}
                    </TableCell>
                    <TableCell className="text-xs">{task.agent_type || '—'}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px]">
                        {executorTypeLabel(task.executor_type)}
                      </Badge>
                    </TableCell>
                    <TableCell><ConditionBadge type={task.condition_type} /></TableCell>
                    <TableCell className="text-xs text-slate-400">
                      {deps.length > 0 ? deps.join(', ') : '—'}
                    </TableCell>
                    <TableCell>
                      <TaskEditorInline
                        task={task}
                        onUpdate={(data) => onUpdateTask(task.id, data)}
                        onDelete={() => onDeleteTask(task.id)}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="text-center py-8 border border-dashed border-slate-300 rounded-lg">
          <Copy className="w-8 h-8 mx-auto text-slate-300 mb-2" />
          <p className="text-sm text-slate-400">该步骤暂无关联任务</p>
          <Button size="sm" variant="outline" className="mt-3" onClick={onAddTask}>
            <Plus className="w-3 h-3 mr-1" />添加任务
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Scenario Timeline ─────────────────────────────────────────────────────────

function ScenarioTimeline({ scenario }: { scenario: ScenarioExtended }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Clock className="w-4 h-4" />版本历史
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-3 h-3 rounded-full mt-1 bg-blue-500" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Badge variant={getBadgeVariant(scenario?.status)}>{scenario?.status || 'unknown'}</Badge>
              <span className="text-xs text-slate-400">{scenario?.updated_at ? new Date(scenario.updated_at).toLocaleDateString('zh-CN') : '—'}</span>
            </div>
            <p className="text-sm text-slate-700 mt-1">
              v{scenario?.version || '1.0'} · {SOURCE_LABELS[scenario?.source || ''] || scenario?.source || 'unknown'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Scenario Metrics ──────────────────────────────────────────────────────────

function ScenarioMetrics({ scenario }: { scenario: Scenario }) {
  const metrics = [
    { label: '使用次数', value: scenario?.usage_count ?? 0, icon: PlayCircle },
    { label: '成功率', value: scenario?.success_rate ? `${scenario.success_rate.toFixed(1)}%` : '—', icon: CheckCircle },
    { label: '平均耗时', value: scenario?.avg_duration_ms ? `${Math.round(scenario.avg_duration_ms / 60000)} 分钟` : '—', icon: Clock },
    { label: '版本', value: scenario?.version || '—', icon: FileText },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <BarChart3 className="w-4 h-4" />场景指标
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {metrics.map(m => (
            <div key={m.label} className="bg-slate-50 rounded-sm p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <m.icon className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-xs text-slate-500">{m.label}</span>
              </div>
              <p className="text-lg font-bold text-slate-800">{m.value}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Basic Info Edit Form ───────────────────────────────────────────────────────

function BasicInfoEditor({ scenario, onSave, onCancel }: { scenario: Scenario; onSave: (data: Partial<Scenario>) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState({
    name: scenario.name || '',
    category: scenario.category || '',
    description: scenario.description || '',
    scenario_desc: scenario.scenario_desc || '',
    triggers: Array.isArray(scenario.triggers) ? scenario.triggers.join(', ') : '',
    status: scenario.status || 'draft',
  });
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      const triggers = draft.triggers.split(',').map(s => s.trim()).filter(Boolean);
      onSave({
        name: draft.name,
        category: draft.category,
        description: draft.description,
        scenario_desc: draft.scenario_desc,
        triggers,
        status: draft.status as Scenario['status'],
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <Label>场景名称</Label>
        <Input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} className="mt-1" />
      </div>
      <div>
        <Label>分类</Label>
        <Select value={draft.category} onValueChange={v => setDraft({ ...draft, category: v })}>
          <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="general">通用</SelectItem>
            <SelectItem value="earthquake">地震</SelectItem>
            <SelectItem value="fire">火灾</SelectItem>
            <SelectItem value="chemical">化学品</SelectItem>
            <SelectItem value="flood">防汛</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label>简要描述</Label>
        <Input value={draft.description} onChange={e => setDraft({ ...draft, description: e.target.value })} className="mt-1" />
      </div>
      <div>
        <Label>场景详细描述</Label>
        <Textarea value={draft.scenario_desc} onChange={e => setDraft({ ...draft, scenario_desc: e.target.value })} className="mt-1" rows={4} />
      </div>
      <div>
        <Label>触发条件（逗号分隔）</Label>
        <Input value={draft.triggers} onChange={e => setDraft({ ...draft, triggers: e.target.value })} className="mt-1" placeholder="例如: 地震, 火灾" />
      </div>
      <div>
        <Label>状态</Label>
        <Select value={draft.status} onValueChange={v => setDraft({ ...draft, status: v as Scenario['status'] })}>
          <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="draft">草稿</SelectItem>
            <SelectItem value="active">活跃</SelectItem>
            <SelectItem value="deprecated">已废弃</SelectItem>
            <SelectItem value="archived">已归档</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-2 justify-end">
        <Button variant="outline" onClick={onCancel} disabled={saving}>取消</Button>
        <Button onClick={handleSave} disabled={saving || !draft.name.trim()}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Save className="w-4 h-4 mr-1" />} 保存
        </Button>
      </div>
    </div>
  );
}

// ── Step Editor ────────────────────────────────────────────────────────────────

function StepEditor({ step, tasks, onUpdate, onDelete, onAddTask }: {
  step: ScenarioStep;
  tasks: ScenarioTask[];
  onUpdate: (data: Partial<ScenarioStep>) => void;
  onDelete: () => void;
  onAddTask: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    name: step.name || '',
    agent_type: step.agent_type || '',
    required_capabilities: Array.isArray(step.required_capabilities) ? step.required_capabilities.join(', ') : '',
    condition_type: step.condition_type || 'none',
    condition_data_json: JSON.stringify(step.condition_data || {}, null, 2),
  });
  const [jsonError, setJsonError] = useState<string | null>(null);

  function handleConditionDataChange(value: string) {
    setDraft({ ...draft, condition_data_json: value });
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch {
      setJsonError('JSON 格式无效');
    }
  }

  async function handleSave() {
    if (jsonError) return;
    let conditionData: Record<string, any> | null = null;
    try {
      conditionData = JSON.parse(draft.condition_data_json);
    } catch { /* keep null */ }
    onUpdate({
      name: draft.name,
      agent_type: draft.agent_type || null,
      required_capabilities: draft.required_capabilities.split(',').map(s => s.trim()).filter(Boolean),
      condition_type: draft.condition_type as ConditionType,
      condition_data: conditionData,
    });
    setEditing(false);
  }

  if (!editing) {
    return (
      <div className="flex items-center gap-2 mb-2">
        <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={() => setEditing(true)}>
          <Edit3 className="w-3 h-3 mr-1" />编辑步骤
        </Button>
        <Button size="sm" variant="ghost" className="h-6 text-xs text-red-500" onClick={onDelete}>
          <Trash2 className="w-3 h-3 mr-1" />删除
        </Button>
        <Button size="sm" variant="outline" className="h-6 text-xs" onClick={onAddTask}>
          <Plus className="w-3 h-3 mr-1" />添加任务
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3 mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">编辑步骤</span>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => setEditing(false)}>取消</Button>
          <Button size="sm" className="h-6 text-xs" onClick={handleSave} disabled={!!jsonError || !draft.name.trim()}>
            <Save className="w-3 h-3 mr-1" />保存
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs">步骤名称</Label>
          <Input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} className="mt-1 h-8 text-sm" />
        </div>
        <div>
          <Label className="text-xs">执行者</Label>
          <Input value={draft.agent_type} onChange={e => setDraft({ ...draft, agent_type: e.target.value })} className="mt-1 h-8 text-sm" placeholder="例如: command" />
        </div>
      </div>
      <div>
        <Label className="text-xs">所需能力（逗号分隔）</Label>
        <Input value={draft.required_capabilities} onChange={e => setDraft({ ...draft, required_capabilities: e.target.value })} className="mt-1 h-8 text-sm" />
      </div>
      <div>
        <Label className="text-xs">条件类型</Label>
        <Select value={draft.condition_type} onValueChange={v => setDraft({ ...draft, condition_type: v as ConditionType })}>
          <SelectTrigger className="mt-1 h-8 text-sm"><SelectValue /></SelectTrigger>
          <SelectContent>
            {CONDITION_OPTIONS.map(opt => (
              <SelectItem key={opt} value={opt}>{CONDITION_CONFIG[opt].label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-xs">条件数据 (JSON)</Label>
        <Textarea
          value={draft.condition_data_json}
          onChange={e => handleConditionDataChange(e.target.value)}
          className="mt-1 font-mono text-xs min-h-[80px]"
          rows={3}
        />
        {jsonError && <p className="text-xs text-red-500 mt-1">{jsonError}</p>}
      </div>
    </div>
  );
}

// ── Task Editor (inline) ───────────────────────────────────────────────────────

function TaskEditorInline({ task, onUpdate, onDelete }: {
  task: ScenarioTask;
  onUpdate: (data: Partial<ScenarioTask>) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [hltlDialogOpen, setHITLDialogOpen] = useState(false);

  const [draft, setDraft] = useState({
    name: task.name || '',
    description: task.description || '',
    agent_type: task.agent_type || '',
    required_capabilities: Array.isArray(task.required_capabilities) ? task.required_capabilities.join(', ') : '',
    dependencies: Array.isArray(task.dependencies) ? task.dependencies.join(', ') : '',
    condition_type: task.condition_type || 'none',
    condition_data_json: JSON.stringify(task.condition_data || {}, null, 2),
    executor_type: task.executor_type || 'ai',
  });
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Parse condition_data from task
  const condition_data = task.condition_data || {};

  // Parse condition_data from draft JSON
  const draft_condition_data = draft.condition_data_json ? JSON.parse(draft.condition_data_json) : {};

  function handleConditionDataChange(value: string) {
    setDraft({ ...draft, condition_data_json: value });
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch {
      setJsonError('JSON 格式无效');
    }
  }

  function handleHITLSave(config: any) {
    setDraft({
      ...draft,
      condition_data_json: JSON.stringify({
        input_type: config.input_type || (draft.executor_type === 'ai_approval' ? 'approval' : draft.executor_type === 'ai_data' ? 'data_entry' : 'confirmation'),
        ...draft_condition_data,
        ...config,
      }, null, 2),
    });
    setHITLDialogOpen(false);
  }

  function handleSave() {
    if (jsonError) return;
    let conditionData: Record<string, any> | null = null;
    try {
      conditionData = JSON.parse(draft.condition_data_json);
    } catch { /* keep null */ }
    onUpdate({
      name: draft.name,
      description: draft.description || null,
      agent_type: draft.agent_type || null,
      required_capabilities: draft.required_capabilities.split(',').map(s => s.trim()).filter(Boolean),
      dependencies: draft.dependencies.split(',').map(s => s.trim()).filter(Boolean),
      condition_type: draft.condition_type as ConditionType,
      condition_data: conditionData,
      executor_type: draft.executor_type,
    });
    setEditing(false);
  }

  if (!editing) {
    return (
      <div className="flex items-center gap-2 mt-1">
        <Button size="sm" variant="ghost" className="h-5 text-xs px-1" onClick={() => setEditing(true)}>
          <Edit3 className="w-3 h-3" />
        </Button>
        <Button size="sm" variant="ghost" className="h-5 text-xs px-1 text-red-500" onClick={onDelete}>
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2 mt-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">编辑任务</span>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => setEditing(false)}>取消</Button>
          <Button size="sm" className="h-6 text-xs" onClick={handleSave} disabled={!!jsonError || !draft.name.trim()}>
            <Save className="w-3 h-3 mr-1" />保存
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs">任务名称</Label>
          <Input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} className="mt-1 h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">执行者</Label>
          <Input value={draft.agent_type} onChange={e => setDraft({ ...draft, agent_type: e.target.value })} className="mt-1 h-7 text-xs" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs">执行模式</Label>
          <Select value={draft.executor_type} onValueChange={v => setDraft({ ...draft, executor_type: v })}>
            <SelectTrigger className="mt-1 h-7 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ai">AI</SelectItem>
              <SelectItem value="human">纯人</SelectItem>
              <SelectItem value="ai_approval">审批</SelectItem>
              <SelectItem value="ai_data">数据</SelectItem>
              <SelectItem value="ai_confirm">确认</SelectItem>
              <SelectItem value="auto_eval">自动</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          {['ai_approval', 'ai_data', 'ai_confirm'].includes(draft.executor_type) && (
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-xs"
              onClick={() => setHITLDialogOpen(true)}
            >
              <Settings className="w-3 h-3 mr-1" /> HITL配置
            </Button>
          )}
        </div>
      </div>
      <div>
        <Label className="text-xs">描述</Label>
        <Input value={draft.description} onChange={e => setDraft({ ...draft, description: e.target.value })} className="mt-1 h-7 text-xs" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs">所需能力</Label>
          <Input value={draft.required_capabilities} onChange={e => setDraft({ ...draft, required_capabilities: e.target.value })} className="mt-1 h-7 text-xs" />
        </div>
        <div>
          <Label className="text-xs">依赖（逗号分隔）</Label>
          <Input value={draft.dependencies} onChange={e => setDraft({ ...draft, dependencies: e.target.value })} className="mt-1 h-7 text-xs" />
        </div>
      </div>
      <div>
        <Label className="text-xs">条件类型</Label>
        <Select value={draft.condition_type} onValueChange={v => setDraft({ ...draft, condition_type: v as ConditionType })}>
          <SelectTrigger className="mt-1 h-7 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            {CONDITION_OPTIONS.map(opt => (
              <SelectItem key={opt} value={opt}>{CONDITION_CONFIG[opt].label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-xs">条件数据 (JSON)</Label>
        <Textarea
          value={draft.condition_data_json}
          onChange={e => handleConditionDataChange(e.target.value)}
          className="mt-1 font-mono text-xs min-h-[60px]"
          rows={2}
        />
        {jsonError && <p className="text-xs text-red-500 mt-1">{jsonError}</p>}
      </div>

      {/* HITL Config Dialog */}
      {['ai_approval', 'ai_data', 'ai_confirm'].includes(draft.executor_type) && (
        <HITLConfigDialog
          open={hltlDialogOpen}
          onOpenChange={setHITLDialogOpen}
          executorType={draft.executor_type}
          initialData={condition_data}
          onSave={handleHITLSave}
        />
      )}
    </div>
  );
}

// ── Step Detail Tab Content ────────────────────────────────────────────────────

function StepsDetailTab({ scenario, onRefresh }: { scenario: Scenario; onRefresh: () => void }) {
  const [saving, setSaving] = useState(false);
  const [newStepDialog, setNewStepDialog] = useState(false);
  const [newTaskForStep, setNewTaskForStep] = useState<string | null>(null);
  const [activeStepTab, setActiveStepTab] = useState<string>('');

  const steps: ScenarioStep[] = scenario.steps || [];
  const tasks: ScenarioTask[] = scenario.task_templates || [];

  // Initialize active tab to first step
  useEffect(() => {
    if (steps.length > 0 && !activeStepTab) {
      setActiveStepTab(steps[0].id);
    }
  }, [steps, activeStepTab]);

  async function updateScenario(data: Partial<Scenario>) {
    setSaving(true);
    try {
      await scenariosApi.update(scenario.id, data);
      toast.success('已更新');
      onRefresh();
    } catch (e: any) {
      toast.error('更新失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  async function updateStep(stepId: string, data: Partial<ScenarioStep>) {
    setSaving(true);
    try {
      const updatedSteps = steps.map(s => s.id === stepId ? { ...s, ...data } : s);
      await scenariosApi.update(scenario.id, { steps: updatedSteps });
      toast.success('步骤已更新');
      onRefresh();
    } catch (e: any) {
      toast.error('更新失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  async function deleteStep(stepId: string) {
    if (!confirm('确定要删除此步骤吗？')) return;
    setSaving(true);
    try {
      const updatedSteps = steps.filter(s => s.id !== stepId);
      await scenariosApi.update(scenario.id, { steps: updatedSteps });
      toast.success('步骤已删除');
      onRefresh();
    } catch (e: any) {
      toast.error('删除失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  async function updateTask(taskId: string, data: Partial<ScenarioTask>) {
    setSaving(true);
    try {
      const updatedTasks = tasks.map(t => t.id === taskId ? { ...t, ...data } : t);
      await scenariosApi.update(scenario.id, { task_templates: updatedTasks });
      toast.success('任务已更新');
      onRefresh();
    } catch (e: any) {
      toast.error('更新失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  async function deleteTask(taskId: string) {
    if (!confirm('确定要删除此任务吗？')) return;
    setSaving(true);
    try {
      const updatedTasks = tasks.filter(t => t.id !== taskId);
      await scenariosApi.update(scenario.id, { task_templates: updatedTasks });
      toast.success('任务已删除');
      onRefresh();
    } catch (e: any) {
      toast.error('删除失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  if (saving) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        <span className="ml-2 text-sm text-slate-500">保存中...</span>
      </div>
    );
  }

  if (steps.length === 0 && tasks.length === 0) {
    return (
      <div className="text-center py-12">
        <Layers className="w-12 h-12 mx-auto text-slate-300 mb-3" />
        <p className="text-sm text-slate-400 mb-4">此场景暂无步骤和任务定义</p>
        <Button size="sm" onClick={() => setNewStepDialog(true)}>
          <Plus className="w-4 h-4 mr-1" />添加步骤
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          共 <span className="font-bold text-slate-700">{steps.length}</span> 个步骤，
          <span className="font-bold text-slate-700"> {tasks.length}</span> 个任务
        </p>
        <Button size="sm" onClick={() => setNewStepDialog(true)}>
          <Plus className="w-4 h-4 mr-1" />添加步骤
        </Button>
      </div>

      {/* Nested Tabs: each Project/Step is a tab */}
      <Tabs value={activeStepTab} onValueChange={setActiveStepTab}>
        <TabsList className="w-full justify-start overflow-x-auto">
          {steps.map((step, i) => {
            const stepTaskCount = tasks.filter(t => t.phase_name === step.name).length;
            return (
              <TabsTrigger key={step.id} value={step.id} className="flex items-center gap-1.5">
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-[10px] font-bold">
                  {i + 1}
                </span>
                <span className="truncate max-w-[120px]">{step.name}</span>
                <Badge variant="secondary" className="text-[10px] ml-1">{stepTaskCount}</Badge>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {steps.map((step) => (
          <TabsContent key={step.id} value={step.id} className="mt-4">
            <ProjectTabContent
              step={step}
              tasks={tasks}
              onUpdateStep={(data) => updateStep(step.id, data)}
              onDeleteStep={() => deleteStep(step.id)}
              onAddTask={() => setNewTaskForStep(step.name)}
              onUpdateTask={(taskId, data) => updateTask(taskId, data)}
              onDeleteTask={(taskId) => deleteTask(taskId)}
            />
          </TabsContent>
        ))}
      </Tabs>

      {/* New task inline form */}
      {newTaskForStep && (
        <NewTaskForm
          phaseName={newTaskForStep}
          scenarioId={scenario.id}
          existingTasks={tasks}
          onCancel={() => setNewTaskForStep(null)}
          onSuccess={() => { setNewTaskForStep(null); onRefresh(); }}
        />
      )}
      {/* New step dialog */}
      <NewStepDialog
        open={newStepDialog}
        onClose={() => setNewStepDialog(false)}
        scenarioId={scenario.id}
        onSuccess={onRefresh}
      />
    </div>
  );
}

// ── New Step Dialog ────────────────────────────────────────────────────────────

function NewStepDialog({ open, onClose, scenarioId, onSuccess }: {
  open: boolean;
  onClose: () => void;
  scenarioId: string;
  onSuccess: () => void;
}) {
  const [name, setName] = useState('');
  const [agentType, setAgentType] = useState('');
  const [conditionType, setConditionType] = useState<ConditionType>('none');
  const [saving, setSaving] = useState(false);

  async function handleCreate() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      // We need to fetch current scenario, append step, and save
      const current = await scenariosApi.get(scenarioId);
      const newStep: ScenarioStep = {
        id: `step-${Date.now()}`,
        name: name.trim(),
        agent_type: agentType || null,
        required_capabilities: [],
        condition_type: conditionType,
        condition_data: null,
      };
      const updatedSteps = [...(current.steps || []), newStep];
      await scenariosApi.update(scenarioId, { steps: updatedSteps });
      toast.success('步骤已创建');
      onSuccess();
      onClose();
    } catch (e: any) {
      toast.error('创建失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={o => { if (!o) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>添加新步骤</DialogTitle>
          <DialogDescription>为该场景蓝图添加一个新步骤。</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>步骤名称</Label>
            <Input value={name} onChange={e => setName(e.target.value)} className="mt-1" placeholder="例如: 应急响应" />
          </div>
          <div>
            <Label>执行者（可选）</Label>
            <Input value={agentType} onChange={e => setAgentType(e.target.value)} className="mt-1" placeholder="例如: command" />
          </div>
          <div>
            <Label>条件类型</Label>
            <Select value={conditionType} onValueChange={v => setConditionType(v as ConditionType)}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                {CONDITION_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt}>{CONDITION_CONFIG[opt].label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={handleCreate} disabled={saving || !name.trim()}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Plus className="w-4 h-4 mr-1" />} 创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── New Task Form ──────────────────────────────────────────────────────────────

function NewTaskForm({ phaseName, scenarioId, existingTasks, onCancel, onSuccess }: {
  phaseName: string;
  scenarioId: string;
  existingTasks: ScenarioTask[];
  onCancel: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [agentType, setAgentType] = useState('');
  const [executorType, setExecutorType] = useState('ai');
  const [conditionType, setConditionType] = useState<ConditionType>('none');
  const [saving, setSaving] = useState(false);

  async function handleCreate() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const current = await scenariosApi.get(scenarioId);
      const phaseTasks = (current.task_templates || []).filter(t => t.phase_name === phaseName);
      const newTask: ScenarioTask = {
        id: `task-${Date.now()}`,
        name: name.trim(),
        description: description || null,
        agent_type: agentType || null,
        required_capabilities: [],
        dependencies: [],
        condition_type: conditionType,
        condition_data: null,
        phase_name: phaseName,
        order_in_phase: phaseTasks.length,
        executor_type: executorType,
      };
      const updatedTasks = [...(current.task_templates || []), newTask];
      await scenariosApi.update(scenarioId, { task_templates: updatedTasks });
      toast.success('任务已创建');
      onSuccess();
    } catch (e: any) {
      toast.error('创建失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="border-dashed border-slate-300 bg-slate-50/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">添加任务到 "{phaseName}"</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">任务名称</Label>
              <Input value={name} onChange={e => setName(e.target.value)} className="mt-1 h-8 text-sm" placeholder="任务名称" />
            </div>
            <div>
              <Label className="text-xs">执行者</Label>
              <Input value={agentType} onChange={e => setAgentType(e.target.value)} className="mt-1 h-8 text-sm" placeholder="例如: rescue" />
            </div>
          </div>
          <div>
            <Label className="text-xs">描述</Label>
            <Input value={description} onChange={e => setDescription(e.target.value)} className="mt-1 h-8 text-sm" />
          </div>
          <div>
            <Label className="text-xs">执行模式</Label>
            <Select value={executorType} onValueChange={v => setExecutorType(v)}>
              <SelectTrigger className="mt-1 h-8 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ai">AI</SelectItem>
                <SelectItem value="human">纯人</SelectItem>
                <SelectItem value="ai_approval">审批</SelectItem>
                <SelectItem value="ai_data">数据</SelectItem>
                <SelectItem value="ai_confirm">确认</SelectItem>
                <SelectItem value="auto_eval">自动</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">条件类型</Label>
            <Select value={conditionType} onValueChange={v => setConditionType(v as ConditionType)}>
              <SelectTrigger className="mt-1 h-8 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                {CONDITION_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt}>{CONDITION_CONFIG[opt].label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="outline" onClick={onCancel} disabled={saving}>取消</Button>
            <Button size="sm" onClick={handleCreate} disabled={saving || !name.trim()}>
              {saving ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Plus className="w-3 h-3 mr-1" />} 创建
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Create Goal Dialog ──────────────────────────────────────────────────────────

function CreateGoalDialog({ scenario, open, onClose, onSuccess }: {
  scenario: ScenarioExtended;
  open: boolean;
  onClose: () => void;
  onSuccess: (goalId: string) => void;
}) {
  const [title, setTitle] = useState(scenario?.name ? `${scenario.name} - 执行目标` : '');
  const [description, setDescription] = useState(scenario?.description || '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setTitle(scenario?.name ? `${scenario.name} - 执行目标` : '');
      setDescription(scenario?.description || '');
    }
  }, [open, scenario]);

  async function handleCreate() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const result = await scenariosApi.instantiate(scenario.id, {
        goal_title: title.trim(),
        goal_description: description.trim() || undefined,
        goal_priority: 'medium',
        goal_status: 'draft',
      });
      toast.success('目标已创建', { description: `Goal ID: ${result.goal_id}` });
      onSuccess(result.goal_id);
      onClose();
    } catch (e: any) {
      toast.error('创建目标失败: ' + (e.message || '未知错误'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>从场景创建Goal</DialogTitle>
          <DialogDescription>
            将场景「{scenario?.name}」实例化为执行目标，将自动创建关联的 Projects 和 Tasks。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>目标标题 <span className="text-red-500">*</span></Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1"
              placeholder="输入目标标题"
              disabled={saving}
            />
          </div>
          <div>
            <Label>目标描述</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1"
              placeholder="输入目标描述（可选）"
              rows={3}
              disabled={saving}
            />
          </div>
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
            <p className="text-xs text-blue-700">
              此操作将从场景蓝图中自动创建 Goal → Projects → Tasks 的完整执行链路。
              {scenario.projects && scenario.projects.length > 0 && (
                <> 将创建 <strong>{scenario.projects.length}</strong> 个 Project 和 <strong>{scenario.projects.reduce((sum, p) => sum + (p.tasks?.length || 0), 0)}</strong> 个 Task。</>
              )}
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={handleCreate} disabled={saving || !title.trim()}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <PlayCircle className="w-4 h-4 mr-1" />}
            创建目标
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Projects Tab (Sprint 85c + 87c: CRUD integration) ──────────────────────

function ProjectsTab({ scenario, onRefresh }: { scenario: Scenario; onRefresh: () => void }) {
  const [projectDialog, setProjectDialog] = useState<{ open: boolean; edit?: { id: string } & ScenarioProjectFormData }>({ open: false });
  const [taskDialog, setTaskDialog] = useState<{ open: boolean; edit?: { id: string } & ScenarioTaskFormData; projectId?: string }>({ open: false });
  const [deleting, setDeleting] = useState<string | null>(null); // 'project-xxx' or 'task-xxx'

  const projects = scenario.projects || [];
  const goalTags = scenario.goal_capability_tags as Record<string, string[]> | null;

  // Collect all unique tags across projects
  const allTags = new Set<string>();
  projects.forEach((p: ScenarioProject) => {
    const tags = p.capability_tags || [];
    if (Array.isArray(tags)) tags.forEach((t: string) => allTags.add(t));
    else if (typeof tags === 'object') Object.values(tags).forEach((v: any) => { if (v) allTags.add(String(v)); });
  });

  // ── Project CRUD handlers ──

  async function handleProjectSubmit(isEdit: boolean, data: ScenarioProjectFormData) {
    if (isEdit && projectDialog.edit) {
      await request(
        `/scenarios/${scenario.id}/projects/${projectDialog.edit.id}`,
        { method: 'PUT', body: JSON.stringify(data) },
      );
      toast.success('项目已更新');
    } else {
      await request(
        `/scenarios/${scenario.id}/projects`,
        { method: 'POST', body: JSON.stringify(data) },
      );
      toast.success('项目已创建');
    }
    setProjectDialog({ open: false });
    onRefresh();
  }

  async function handleDeleteProject(projectId: string, projectName: string) {
    if (!confirm(`确定要删除项目「${projectName}」吗？此操作不可撤销。`)) return;
    setDeleting(projectId);
    try {
      await request(`/scenarios/${scenario.id}/projects/${projectId}`, { method: 'DELETE' });
      toast.success('项目已删除');
      onRefresh();
    } catch (e: any) {
      toast.error('删除失败: ' + (e.message || '未知错误'));
    } finally {
      setDeleting(null);
    }
  }

  // ── Task CRUD handlers ──

  async function handleTaskSubmit(isEdit: boolean, data: ScenarioTaskFormData) {
    if (isEdit && taskDialog.edit) {
      await request(
        `/scenarios/${scenario.id}/tasks/${taskDialog.edit.id}`,
        { method: 'PUT', body: JSON.stringify(data) },
      );
      toast.success('任务已更新');
    } else {
      await request(
        `/scenarios/${scenario.id}/tasks`,
        { method: 'POST', body: JSON.stringify(data) },
      );
      toast.success('任务已创建');
    }
    setTaskDialog({ open: false });
    onRefresh();
  }

  async function handleDeleteTask(projectId: string, taskId: string, taskName: string) {
    if (!confirm(`确定要删除任务「${taskName}」吗？此操作不可撤销。`)) return;
    setDeleting(taskId);
    try {
      await request(`/scenarios/${scenario.id}/tasks/${taskId}`, { method: 'DELETE' });
      toast.success('任务已删除');
      onRefresh();
    } catch (e: any) {
      toast.error('删除失败: ' + (e.message || '未知错误'));
    } finally {
      setDeleting(null);
    }
  }

  // ── Helpers for Dialog refs ──

  const projectRefs = projects.map((p: ScenarioProject) => ({ id: p.id, name: p.name }));
  const allTaskRefs: { id: string; name: string; project_id: string }[] = [];
  projects.forEach((p: ScenarioProject) => {
    (p.tasks || []).forEach((t: ScenarioProjectTask) => {
      allTaskRefs.push({ id: t.id, name: t.name, project_id: p.id });
    });
  });

  return (
    <div className="space-y-6">
      {/* Project summary */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="w-4 h-4" />项目列表
            </CardTitle>
            <CardDescription>共 {projects.length} 个项目</CardDescription>
          </div>
          <Button size="sm" onClick={() => setProjectDialog({ open: true })}>
            <Plus className="w-4 h-4 mr-1" />新建项目
          </Button>
        </CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <div className="text-center py-8 text-sm text-slate-400">
              暂无项目数据
              <div className="mt-3">
                <Button size="sm" onClick={() => setProjectDialog({ open: true })}>
                  <Plus className="w-4 h-4 mr-1" />新建第一个项目
                </Button>
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>项目名称</TableHead>
                  <TableHead>阶段</TableHead>
                  <TableHead className="w-24">任务数</TableHead>
                  <TableHead>能力标签</TableHead>
                  <TableHead className="w-24">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.map((project: ScenarioProject, i: number) => {
                  const projTasks = project.tasks || [];
                  return (
                    <TableRow key={project.id}>
                      <TableCell className="text-xs text-slate-400">{i + 1}</TableCell>
                      <TableCell className="font-medium text-sm">{project.name}</TableCell>
                      <TableCell className="text-xs text-slate-500">
                        <Badge variant="secondary" className="text-xs">
                          Phase {project.order || (i + 1)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs font-medium">
                        {projTasks.length}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {(() => {
                            const tags = project.capability_tags || [];
                            if (Array.isArray(tags)) {
                              return tags.map((tag: string, ti: number) => (
                                <Badge key={ti} variant="outline" className="text-[10px]">{tag}</Badge>
                              ));
                            }
                            if (typeof tags === 'object') {
                              return Object.entries(tags).map(([dim, val]: [string, any]) => (
                                <Badge key={dim} variant="outline" className="text-[10px]">{String(val)}</Badge>
                              ));
                            }
                            return <span className="text-xs text-slate-400">—</span>;
                          })()}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm" variant="ghost" className="h-7 w-7 p-0"
                            onClick={() => setProjectDialog({
                              open: true,
                              edit: {
                                id: project.id,
                                name: project.name,
                                description: project.description || '',
                                project_type: (project.project_type as any) || 'mandatory',
                                condition_type: (project.condition_type as any) || 'none',
                                order_index: project.order || 0,
                                capability_tags: Array.isArray(project.capability_tags) ? project.capability_tags : [],
                              },
                            })}
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-700"
                            onClick={() => handleDeleteProject(project.id, project.name)}
                            disabled={deleting === project.id}
                          >
                            {deleting === project.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                          </Button>
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

      {/* Task lists per project */}
      {projects.map((project: ScenarioProject) => {
        const projTasks = project.tasks || [];
        return (
          <Card key={`tasks-${project.id}`}>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  项目「{project.name}」的任务
                </CardTitle>
                <CardDescription>{projTasks.length} 个任务</CardDescription>
              </div>
              <Button size="sm" variant="outline" onClick={() => setTaskDialog({ open: true, projectId: project.id })}>
                <Plus className="w-4 h-4 mr-1" />新建任务
              </Button>
            </CardHeader>
            <CardContent>
              {projTasks.length === 0 ? (
                <div className="text-center py-6 text-sm text-slate-400">
                  暂无任务
                  <div className="mt-2">
                    <Button size="sm" variant="outline" onClick={() => setTaskDialog({ open: true, projectId: project.id })}>
                      <Plus className="w-3 h-3 mr-1" />添加任务
                    </Button>
                  </div>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10">#</TableHead>
                      <TableHead>任务名称</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead className="w-24">优先级</TableHead>
                      <TableHead className="w-24">预估工时</TableHead>
                      <TableHead>依赖</TableHead>
                      <TableHead className="w-24">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {projTasks.map((task: ScenarioProjectTask, ti: number) => {
                      const deps = safeParseList(task.dependencies);
                      const priorityLabel: Record<string, string> = { low: '低', medium: '中', high: '高', critical: '紧急' };
                      return (
                        <TableRow key={task.id}>
                          <TableCell className="text-xs text-slate-400">{ti + 1}</TableCell>
                          <TableCell className="font-medium text-sm">{task.name}</TableCell>
                          <TableCell className="text-xs text-slate-500 max-w-[200px] truncate">
                            {task.description || '—'}
                          </TableCell>
                          <TableCell>
                            <Badge variant={task.priority === 'critical' ? 'destructive' : task.priority === 'high' ? 'default' : 'secondary'} className="text-xs">
                              {priorityLabel[task.priority] || task.priority || '—'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs">
                            {task.estimated_hours != null ? `${task.estimated_hours}h` : '—'}
                          </TableCell>
                          <TableCell className="text-xs text-slate-400">
                            {deps.length > 0 ? deps.join(', ') : '—'}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm" variant="ghost" className="h-7 w-7 p-0"
                                onClick={() => setTaskDialog({
                                  open: true,
                                  edit: {
                                    id: task.id,
                                    name: task.name,
                                    description: task.description || '',
                                    project_id: project.id,
                                    phase_name: project.name,
                                    agent_type: task.agent_type || '',
                                    priority: (task.priority as any) || 'medium',
                                    estimated_hours: task.estimated_hours || 0,
                                    dependencies: Array.isArray(deps) ? deps : [],
                                  },
                                })}
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                              </Button>
                              <Button
                                size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-700"
                                onClick={() => handleDeleteTask(project.id, task.id, task.name)}
                                disabled={deleting === task.id}
                              >
                                {deleting === task.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                              </Button>
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
        );
      })}

      {/* Goal-level capability tags by dimension */}
      {goalTags && Object.keys(goalTags).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Tag className="w-4 h-4" />能力标签（按维度）
            </CardTitle>
            <CardDescription>Goal 级别能力标签分类</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(goalTags).map(([dimension, tags]: [string, string[]]) => (
                <div key={dimension} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                    {dimension}
                  </span>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {(tags || []).map((tag: string, ti: number) => (
                      <Badge key={ti} variant="default" className="text-xs">{tag}</Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Project Dialog */}
      <ScenarioProjectDialog
        open={projectDialog.open}
        onOpenChange={(v) => setProjectDialog({ open: v, edit: v ? projectDialog.edit : undefined })}
        scenarioId={scenario.id}
        initialData={projectDialog.edit}
        onSubmit={handleProjectSubmit}
      />

      {/* Task Dialog */}
      <ScenarioTaskDialog
        open={taskDialog.open}
        onOpenChange={(v) => setTaskDialog({ open: v, edit: v ? taskDialog.edit : undefined })}
        scenarioId={scenario.id}
        initialData={taskDialog.edit}
        onSubmit={handleTaskSubmit}
        projects={projectRefs}
        tasks={allTaskRefs}
      />
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function ScenarioDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [scenario, setScenario] = useState<ScenarioExtended | null>(null);
  const [relatedScenarios, setRelatedScenarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [editingBasic, setEditingBasic] = useState(false);
  const [showCreateGoalDialog, setShowCreateGoalDialog] = useState(false);

  // Star state
  const [starredIds, setStarredIds] = useState(new Set<string>());
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}');
      setStarredIds(new Set(Object.keys(stored)));
    } catch {}

    const handler = () => {
      try {
        const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}');
        setStarredIds(new Set(Object.keys(stored)));
      } catch {}
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  // HITL state (Sprint 91)
  const [hitlRequests, setHitlRequests] = useState<any[]>([]);
  const [hitlLoading, setHitlLoading] = useState(false);

  async function fetchHitlRequests() {
    if (!id) return;
    try {
      setHitlLoading(true);
      const r = await fetch(`/api/v1/human-input/pending?scenario_ref=${encodeURIComponent(id)}`);
      if (r.ok) {
        const data = await r.json();
        setHitlRequests(data.requests || []);
      }
    } catch (e) {
      console.error('Failed to fetch HITL requests:', e);
    } finally {
      setHitlLoading(false);
    }
  }

  const hitlPendingCount = hitlRequests.length;

  async function handleHitlApprove(inputId: string) {
    try {
      const r = await fetch(`/api/v1/human-input/${inputId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_data: {}, submitted_by: 'web-user' }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || '审批失败');
      }
      toast.success('✅ 审批通过');
      fetchHitlRequests();
      fetchScenario();
    } catch (e: any) {
      toast.error(`❌ ${e.message}`);
    }
  }

  async function handleHitlReject(inputId: string) {
    if (!confirm('确定要拒绝此审批请求吗？关联任务将被标记为 failed。')) return;
    try {
      const r = await fetch(`/api/v1/human-input/${inputId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || '拒绝失败');
      }
      toast.success('✅ 已拒绝');
      fetchHitlRequests();
      fetchScenario();
    } catch (e: any) {
      toast.error(`❌ ${e.message}`);
    }
  }

  useEffect(() => { fetchScenario(); fetchHitlRequests(); }, [id]);

  async function fetchScenario() {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await scenariosApi.get(id);
      setScenario(data);
      try {
        const listData = await scenariosApi.list({ category: data.category });
        setRelatedScenarios((listData.items || []).filter((s: any) => s.id !== id).slice(0, 5));
      } catch {}
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchScenario(); }, [id]);

  function toggleStar() {
    if (!scenario) return;
    try {
      const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}');
      if (stored[scenario.id]) {
        delete stored[scenario.id];
      } else {
        stored[scenario.id] = {
          name: scenario.name, category: scenario.category,
          status: scenario.status, version: scenario.version,
          description: scenario.scenario_desc,
          starredAt: new Date().toISOString(),
        };
      }
      localStorage.setItem('nexus_starred_scenarios', JSON.stringify(stored));
      setStarredIds(new Set(Object.keys(stored)));
    } catch {}
  }

  async function handleDelete() {
    if (!scenario) return;
    setDeleting(true);
    try {
      await scenariosApi.delete(scenario.id);
      toast.success('场景已删除');
      navigate('/scenarios');
    } catch (e: any) {
      toast.error('删除失败: ' + (e.message || '未知错误'));
    } finally {
      setDeleting(false);
      setShowDeleteDialog(false);
    }
  }

  async function handleBasicInfoSave(data: Partial<Scenario>) {
    try {
      await scenariosApi.update(scenario!.id, data);
      toast.success('基本信息已更新');
      setEditingBasic(false);
      fetchScenario();
    } catch (e: any) {
      toast.error('更新失败: ' + (e.message || '未知错误'));
    }
  }

  function handleCreateGoalSuccess(goalId: string) {
    navigate(`/coordination/goals/${goalId}`);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error || !scenario) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-900">{error || '场景不存在'}</h2>
        <Link to="/scenarios" className="text-blue-600 hover:underline mt-4 inline-block">返回场景库</Link>
      </div>
    );
  }

  const isStarred = starredIds.has(scenario.id);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" asChild>
          <Link to="/scenarios"><ArrowLeft className="w-4 h-4" /></Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-slate-900">{scenario.name}</h2>
            <Badge variant={getBadgeVariant(scenario.status)}>{scenario.status}</Badge>
            <Badge variant={getCategoryVariant(scenario.category)}>
              {CATEGORY_LABELS[scenario.category || ''] || scenario.category}
            </Badge>
            {scenario.executor_type && (
              <Badge variant="outline" className="text-xs">
                {executorTypeLabel(scenario.executor_type)}
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            v{scenario.version} · {SOURCE_LABELS[scenario.source || ''] || scenario.source}
            {scenario.trust_level && ` · 可信度: ${scenario.trust_level}`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={toggleStar} title={isStarred ? '取消收藏' : '收藏'}>
            <Star className={`w-4 h-4 ${isStarred ? 'fill-yellow-400 text-yellow-400' : 'text-slate-400'}`} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowDeleteDialog(true)} className="text-red-500">
            <Trash2 className="w-4 h-4" />删除
          </Button>
          <Button variant="default" size="sm" onClick={() => setShowCreateGoalDialog(true)} className="bg-blue-600 hover:bg-blue-700">
            <PlayCircle className="w-4 h-4 mr-1" />从场景创建Goal
          </Button>
          <Button variant="outline" size="sm" onClick={fetchScenario}><RefreshCw className="w-4 h-4" />刷新</Button>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue="basic">
        <TabsList>
          <TabsTrigger value="basic">基本信息</TabsTrigger>
          <TabsTrigger value="steps">
            步骤详情
            {(scenario.projects?.length || 0) > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">{scenario.projects?.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="projects">
            项目
            {(scenario.projects?.length || 0) > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">{scenario.projects?.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="stats">统计</TabsTrigger>
          <TabsTrigger value="hitl">
            HITL 审批
            {hitlPendingCount > 0 && (
              <Badge variant="destructive" className="ml-1.5 text-xs">{hitlPendingCount}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* ── Basic Info Tab ── */}
        <TabsContent value="basic">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>基本信息</CardTitle>
                <CardDescription>场景蓝图的基本属性和描述</CardDescription>
              </div>
              {!editingBasic && (
                <Button size="sm" variant="outline" onClick={() => setEditingBasic(true)}>
                  <Edit3 className="w-4 h-4 mr-1" />编辑
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {editingBasic ? (
                <BasicInfoEditor
                  scenario={scenario}
                  onSave={handleBasicInfoSave}
                  onCancel={() => setEditingBasic(false)}
                />
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <InfoField label="场景名称" value={scenario.name} />
                    <InfoField label="分类" value={CATEGORY_LABELS[scenario.category] || scenario.category} />
                    <InfoField label="状态" value={<Badge variant={getBadgeVariant(scenario.status)}>{scenario.status}</Badge>} />
                    <InfoField label="版本" value={`v${scenario.version}`} />
                    <InfoField label="来源" value={SOURCE_LABELS[scenario.source || ''] || scenario.source || '—'} />
                    <InfoField label="可信度" value={scenario.trust_level || '—'} />
                  </div>
                  <Separator />
                  <div>
                    <h4 className="text-sm font-medium text-slate-700 mb-1">简要描述</h4>
                    <p className="text-sm text-slate-600">{scenario.description || '暂无'}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-slate-700 mb-1">场景详细描述</h4>
                    <p className="text-sm text-slate-600 whitespace-pre-wrap">{scenario.scenario_desc || '暂无'}</p>
                  </div>
                  {scenario.triggers && scenario.triggers.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-slate-700 mb-1">触发条件</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {scenario.triggers.map((t, i) => (
                          <Badge key={i} variant="outline" className="text-xs">{t}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Scenario Timeline */}
          <div className="mt-4">
            <ScenarioTimeline scenario={scenario} />
          </div>
        </TabsContent>

        {/* ── Steps Detail Tab ── */}
        <TabsContent value="steps">
          <StepsDetailTab scenario={scenario} onRefresh={fetchScenario} />
        </TabsContent>

        {/* ── Projects Tab (Sprint 85c + 87c) ── */}
        <TabsContent value="projects">
          <ProjectsTab scenario={scenario} onRefresh={fetchScenario} />
        </TabsContent>

        {/* ── Stats Tab ── */}
        <TabsContent value="stats">
          <div className="space-y-6">
            <ScenarioMetrics scenario={scenario} />

            {/* Detailed stats table */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />详细统计
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>指标</TableHead>
                      <TableHead>数值</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="text-muted-foreground">总使用次数</TableCell>
                      <TableCell className="font-medium">{scenario.usage_count || 0} 次</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">成功率</TableCell>
                      <TableCell className="font-medium">{scenario.success_rate ? `${scenario.success_rate.toFixed(1)}%` : '—'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">平均耗时</TableCell>
                      <TableCell className="font-medium">{scenario.avg_duration_ms ? `${Math.round(scenario.avg_duration_ms / 60000)} 分钟` : '—'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">项目数</TableCell>
                      <TableCell className="font-medium">{scenario.projects?.length || 0}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">任务数</TableCell>
                      <TableCell className="font-medium">
                        {scenario.projects?.reduce((sum, p) => sum + (p.tasks?.length || 0), 0) || 0}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">版本</TableCell>
                      <TableCell className="font-medium">v{scenario.version || '1.0'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">来源</TableCell>
                      <TableCell className="font-medium">{SOURCE_LABELS[scenario.source || ''] || scenario.source || '—'}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="text-muted-foreground">可信度</TableCell>
                      <TableCell className="font-medium">{scenario.trust_level || '—'}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>

                {/* Success rate visual */}
                {scenario.success_rate != null && (
                  <div className="mt-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">成功率</span>
                      <span className="font-bold">{scenario.success_rate.toFixed(1)}%</span>
                    </div>
                    <Progress value={scenario.success_rate} className="h-2" />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ── HITL 审批 Tab (Sprint 91) ── */}
        <TabsContent value="hitl">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-4 h-4" />HITL 审批
                </CardTitle>
                <CardDescription>当前场景下需要人工审批的任务</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={fetchHitlRequests}>
                <RefreshCw className="w-3 h-3 mr-1" />刷新
              </Button>
            </CardHeader>
            <CardContent>
              {hitlLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                </div>
              ) : hitlRequests.length === 0 ? (
                <div className="text-center py-8 text-sm text-slate-400">
                  <CheckCircle className="w-10 h-10 mx-auto mb-3 text-green-400" />
                  <p>暂无待审批的 HITL 请求</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {hitlRequests.map((req: any) => (
                    <Card key={req.id} className="border-l-4 border-l-blue-500">
                      <CardContent className="pt-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-sm">{req.title}</span>
                              <Badge variant="outline" className="text-xs">
                                {executorTypeLabel(req.executor_type)}
                              </Badge>
                              <Badge variant="secondary" className="text-xs">
                                {req.input_type}
                              </Badge>
                            </div>
                            {req.description && (
                              <p className="text-xs text-slate-500 mb-2">{req.description}</p>
                            )}
                            <div className="flex gap-4 text-xs text-slate-400">
                              <span>任务: {req.task_id?.slice(0, 16)}...</span>
                              <span>创建: {new Date(req.created_at).toLocaleString('zh-CN')}</span>
                              {req.required_role && <span>角色要求: {req.required_role}</span>}
                              {req.assigned_to && <span>指定人员: {req.assigned_to}</span>}
                            </div>
                          </div>
                          <div className="flex gap-2 shrink-0">
                            <Button
                              size="sm"
                              className="bg-green-600 hover:bg-green-700"
                              onClick={() => handleHitlApprove(req.id)}
                            >
                              <CheckCircle className="w-3 h-3 mr-1" />通过
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleHitlReject(req.id)}
                            >
                              <XCircle className="w-3 h-3 mr-1" />拒绝
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Right sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left main content is now in tabs above, this is extra sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Blueprint summary */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <GitBranch className="w-4 h-4" />蓝图概览
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">项目数</span>
                <span className="font-bold text-slate-800">{scenario.projects?.length || 0}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">任务数</span>
                <span className="font-bold text-slate-800">
                  {scenario.projects?.reduce((sum, p) => sum + (p.tasks?.length || 0), 0) || 0}
                </span>
              </div>
              <Separator />
              {/* Condition type summary */}
              {scenario.projects && scenario.projects.length > 0 && (
                <div>
                  <span className="text-xs text-slate-500">项目条件分布</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(
                      scenario.projects.reduce((acc, p) => {
                        acc[p.condition_type || 'none'] = (acc[p.condition_type || 'none'] || 0) + 1;
                        return acc;
                      }, {} as Record<string, number>)
                    ).map(([type, count]) => (
                      <ConditionBadge key={type} type={type} />
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Related scenarios */}
          {relatedScenarios.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">同类场景</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {relatedScenarios.map((related: any) => (
                  <Link key={related.id} to={`/scenarios/${related.id}`} className="block p-3 bg-slate-50 rounded-sm border border-slate-200 hover:bg-slate-100 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-slate-800 truncate">{related.name}</p>
                      <Badge variant={getBadgeVariant(related.status)} className="shrink-0">{related.status}</Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      v{related.version} · {related.usage_count || 0} 次使用
                    </p>
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Create Goal Dialog */}
      <CreateGoalDialog
        scenario={scenario as ScenarioExtended}
        open={showCreateGoalDialog}
        onClose={() => setShowCreateGoalDialog(false)}
        onSuccess={handleCreateGoalSuccess}
      />

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={(open) => { if (!open) setShowDeleteDialog(false); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">
            确定要删除场景 <strong>{scenario.name}</strong> 吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={deleting}>取消</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <span className="text-xs text-slate-500">{label}</span>
      <p className="text-sm font-medium text-slate-800 mt-0.5">{value}</p>
    </div>
  );
}
