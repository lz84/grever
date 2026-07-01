import { useState, useEffect, useCallback, useMemo } from 'react';
import { SCENARIOS, WORKFLOWS } from '../../../shared/api/paths';
import { toast } from "sonner";
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, AlertCircle, Loader2, CheckCircle, ExternalLink,
  Star, GitBranch, Activity, Clock, FileText, PlayCircle,
  BarChart3, Settings, Trash2, Plus, Code, Edit3, Tag, Save, X,
  ChevronDown, ChevronRight, Zap, Layers, Copy,
} from 'lucide-react';
import { scenariosApi, request } from '../../../shared/utils/api';
import type { Scenario, ScenarioStep, ScenarioTask, ConditionType, ScenarioProject, ScenarioProjectTask } from '../../../shared/utils/scenariosApi';
import DecompositionView, { type DecompTreeItem } from '@/shared/components/DecompositionView';
import ScenarioProjectDialog from '@/reach/components/ScenarioProjectDialog';
import ScenarioTaskDialog from '@/reach/components/ScenarioTaskDialog';
import type { ScenarioProjectFormData } from '@/reach/components/ScenarioProjectDialog';
import type { ProjectType } from '@/reach/components/ScenarioProjectDialog';
import type { ScenarioTaskFormData } from '@/reach/components/ScenarioTaskDialog';
import type { TaskPriority } from '@/reach/components/ScenarioTaskDialog';

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
                <> 将创建 <strong>{scenario.projects.length}</strong> 个工程和 <strong>{scenario.projects.reduce((sum, p) => sum + (p.tasks?.length || 0), 0)}</strong> 个任务。</>
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

// ── Edit Depends On Dialog ──────────────────────────────────────────────────────
function EditDependsOnDialog({
  open, onOpenChange, onSubmit, currentDependsOn, allItems, itemType, parentId, parentType,
}: {
  open: boolean; onOpenChange: (v: boolean) => void;
  onSubmit: (dependsOn: string[]) => void;
  currentDependsOn: string[];
  allItems: Array<{ id: string; name: string; type: string; parent_id?: string; parent_type?: string }>;
  itemType: 'project' | 'task';
  parentId?: string;
  parentType?: string;
}) {
  const [selected, setSelected] = useState<string[]>(currentDependsOn)

  useEffect(() => {
    if (open) setSelected(currentDependsOn)
  }, [open, currentDependsOn])

  const filteredItems = allItems.filter(item => {
    if (item.type !== itemType) return false
    if (item.id === parentId) return false
    if (itemType === 'task' && parentId && parentType) {
      return item.parent_id === parentId && item.parent_type === parentType
    }
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
        {selected.length > 0 && (
          <p className="text-xs text-muted-foreground mt-1">已选择 {selected.length} 个依赖</p>
        )}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={() => { onSubmit(selected); onOpenChange(false); }}>保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Diagram Tab (Sprint 85c + 87c: CRUD integration) ──────────────────────
function DiagramTab({ scenario, onRefresh }: { scenario: Scenario; onRefresh: () => void }) {
  const [projectDialogOpen, setProjectDialogOpen] = useState(false)
  const [taskDialogOpen, setTaskDialogOpen] = useState(false)
  const [editProjectOpen, setEditProjectOpen] = useState(false)
  const [editTaskOpen, setEditTaskOpen] = useState(false)
  const [editProjectData, setEditProjectData] = useState<ScenarioProject | null>(null)
  const [editTaskData, setEditTaskData] = useState<{ task: ScenarioProjectTask; projectId: string } | null>(null)
  const [taskParentProject, setTaskParentProject] = useState<string | undefined>()
  const [editDependsOnItem, setEditDependsOnItem] = useState<DecompTreeItem | null>(null)
  const [editDependsOnOpen, setEditDependsOnOpen] = useState(false)

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
        name: p.name || '未命名工程',
        description: p.description || '',
        status: 'planned',
        _data: { ...p },
        children: (p.tasks || []).map(t => ({
          id: t.id,
          type: 'task' as const,
          name: t.name || '未命名任务',
          description: t.description || '',
          status: 'pending',
          priority: t.priority,
          _data: { ...t, depends_on: safeParseList(t.dependencies) },
        })),
      })),
    }]
  }, [scenario])

  const dagProjects = useMemo(() => {
    if (!scenario) return []
    return (scenario.projects || []).map(p => ({
      id: p.id,
      name: p.name,
      status: 'planned',
      next_step: safeParseList(p.next_step),
    }))
  }, [scenario])

  const dagTasks = useMemo(() => {
    if (!scenario) return []
    const all: Array<{ id: string; title: string; status: string; project_id: string }> = []
    scenario.projects?.forEach(p => {
      (p.tasks || []).forEach(t => {
        all.push({ id: t.id, title: t.title || t.name || '未命名任务', status: 'pending', project_id: p.id })
      })
    })
    return all
  }, [scenario])

  const projectCount = scenario?.projects?.length || 0
  const taskCount = dagTasks.length

  // ── CRUD Handlers ──

  async function handleCreateProject(data: { name: string; description: string; project_type: string; order: number }) {
    try {
      await request(`/scenarios/${scenario.id}/projects`, {
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
      onRefresh()
    } catch (e: any) {
      alert('创建失败: ' + e.message)
    }
  }

  async function handleEditProject(data: { name: string; description: string; project_type: string; order: number }) {
    if (!editProjectData) return
    try {
      await request(`/scenarios/${scenario.id}/projects/${editProjectData.id}`, {
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
      onRefresh()
    } catch (e: any) {
      alert('更新失败: ' + e.message)
    }
  }

  async function handleDeleteProject(projectId: string) {
    if (!confirm('确定删除这个项目吗？')) return
    try {
      await request(`/scenarios/${scenario.id}/projects/${projectId}`, { method: 'DELETE' })
      onRefresh()
    } catch (e: any) {
      alert('删除失败: ' + e.message)
    }
  }

  async function handleDeleteTask(taskId: string) {
    if (!confirm('确定删除这个任务吗？')) return
    try {
      await request(`/scenarios/${scenario.id}/tasks/${taskId}`, { method: 'DELETE' })
      onRefresh()
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
        setProjectDialogOpen(true)
      } else if (item.type === 'task') {
        const parentProject = scenario?.projects?.find(p => p.tasks?.some(t => t.id === item.id))
        setEditTaskData({ task: item._data as ScenarioProjectTask, projectId: parentProject?.id || '' })
        setTaskDialogOpen(true)
      }
    },
    onDelete: (itemId: string, type: 'project' | 'task') => {
      if (type === 'project') handleDeleteProject(itemId)
      else handleDeleteTask(itemId)
    },
    onRefresh,
    onEditDependsOn: (item: DecompTreeItem) => {
      setEditDependsOnItem(item)
      setEditDependsOnOpen(true)
    },
  }), [scenario, onRefresh])

  // Project refs for task dialog
  const projectRefs = useMemo(() => {
    return (scenario?.projects || []).map(p => ({ id: p.id, name: p.name }))
  }, [scenario])

  // All task refs for dependency selection
  const allTaskRefs = useMemo(() => {
    const all: Array<{ id: string; name: string; project_id: string }> = []
    scenario?.projects?.forEach(p => {
      (p.tasks || []).forEach(t => {
        all.push({ id: t.id, name: t.title || t.name || '未命名任务', project_id: p.id })
      })
    })
    return all
  }, [scenario])

  // All items for dependency selection
  const allSelectableItems = useMemo(() => {
    const items: Array<{ id: string; name: string; type: string; parent_id?: string; parent_type?: string }> = []
    scenario?.projects?.forEach(p => items.push({ id: p.id, name: `📁 ${p.name}`, type: 'project' }))
    scenario?.projects?.forEach(p => {
      (p.tasks || []).forEach(t => items.push({
        id: t.id,
        name: `✅ ${t.title || t.name || t.id}`,
        type: 'task',
        parent_id: p.id,
        parent_type: 'project',
      }))
    })
    return items
  }, [scenario])

  // Edit depends on handler
  async function handleEditDependsOn(dependsOn: string[]) {
    if (!editDependsOnItem) return
    try {
      if (editDependsOnItem.type === 'project') {
        await request(`/scenarios/${scenario.id}/projects/${editDependsOnItem.id}`, {
          method: 'PUT',
          body: JSON.stringify({ next_step: dependsOn }),
        })
      } else {
        await request(`/scenarios/${scenario.id}/tasks/${editDependsOnItem.id}`, {
          method: 'PUT',
          body: JSON.stringify({ dependencies: dependsOn }),
        })
      }
      setEditDependsOnOpen(false)
      setEditDependsOnItem(null)
      onRefresh()
    } catch (e: any) {
      alert('保存失败: ' + e.message)
    }
  }

  return (
    <>
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
        showExecutor={false}
        callbacks={callbacks}
      />

      {/* Project Dialogs */}
      <ScenarioProjectDialog
        open={projectDialogOpen}
        onOpenChange={(v) => {
          if (!v) {
            setProjectDialogOpen(false)
            setEditProjectOpen(false)
            setEditProjectData(null)
          }
        }}
        scenarioId={scenario.id}
        onSubmit={async (isEdit, data) => {
          try {
            if (isEdit && editProjectData) {
              await request(`/scenarios/${scenario.id}/projects/${editProjectData.id}`, {
                method: 'PUT',
                body: JSON.stringify({
                  name: data.name,
                  description: data.description,
                  project_type: data.project_type,
                  condition_type: data.condition_type,
                  order_index: data.order_index,
                  capability_tags: data.capability_tags,
                }),
              })
            } else {
              await request(`/scenarios/${scenario.id}/projects`, {
                method: 'POST',
                body: JSON.stringify({
                  name: data.name,
                  description: data.description,
                  project_type: data.project_type,
                  condition_type: data.condition_type,
                  order_index: data.order_index,
                  capability_tags: data.capability_tags,
                }),
              })
            }
            onRefresh()
            setProjectDialogOpen(false)
            setEditProjectOpen(false)
            setEditProjectData(null)
          } catch (e: any) {
            alert((isEdit ? '更新失败: ' : '创建失败: ') + e.message)
          }
        }}
        initialData={editProjectData ? {
          id: editProjectData.id,
          name: editProjectData.name,
          description: editProjectData.description || '',
          project_type: (editProjectData.project_type || 'mandatory') as ProjectType,
          condition_type: 'none',
          condition_data: null,
          order_index: editProjectData.order || 0,
          capability_tags: [],
        } : undefined}
      />

      {/* Task Dialogs */}
      <ScenarioTaskDialog
        open={taskDialogOpen}
        onOpenChange={(v) => {
          if (!v) {
            setTaskDialogOpen(false)
            setEditTaskOpen(false)
            setEditTaskData(null)
            setTaskParentProject(undefined)
          }
        }}
        scenarioId={scenario.id}
        onSubmit={async (isEdit, data) => {
          try {
            if (isEdit && editTaskData) {
              await request(`/scenarios/${scenario.id}/tasks/${editTaskData.task.id}`, {
                method: 'PUT',
                body: JSON.stringify({
                  name: data.title,
                  description: data.description,
                  project_id: data.project_id,
                  priority: data.priority,
                  required_capabilities: data.capability_tags,
                  dependencies: data.depends_on || [],
                }),
              })
            } else {
              await request(`/scenarios/${scenario.id}/tasks`, {
                method: 'POST',
                body: JSON.stringify({
                  name: data.title,
                  description: data.description,
                  project_id: data.project_id,
                  priority: data.priority,
                  required_capabilities: data.capability_tags,
                  dependencies: data.depends_on || [],
                  condition_type: 'none',
                  condition_data: null,
                }),
              })
            }
            onRefresh()
            setTaskDialogOpen(false)
            setTaskParentProject(undefined)
            setEditTaskOpen(false)
            setEditTaskData(null)
          } catch (e: any) {
            alert((isEdit ? '更新失败: ' : '创建失败: ') + e.message)
          }
        }}
        projects={projectRefs}
        tasks={allTaskRefs}
        initialData={editTaskData ? {
          id: editTaskData.task.id,
          title: editTaskData.task.title || editTaskData.task.name || '',
          description: editTaskData.task.description || '',
          project_id: editTaskData.projectId,
          priority: (editTaskData.task.priority || 'medium') as TaskPriority,
          capability_tags: safeParseList(editTaskData.task.required_capabilities),
          depends_on: safeParseList(editTaskData.task.dependencies),
          condition_type: 'none' as const,
          condition_data: null,
        } : (taskParentProject ? {
          id: '',
          title: '', description: '', project_id: taskParentProject,
          priority: 'medium' as TaskPriority, capability_tags: [], depends_on: [],
          condition_type: 'none' as const, condition_data: null,
        } : undefined)}
      />

      {/* Edit Depends On Dialog */}
      {editDependsOnItem && (
        <EditDependsOnDialog
          open={editDependsOnOpen}
          onOpenChange={(v) => { if (!v) { setEditDependsOnOpen(false); setEditDependsOnItem(null); } }}
          onSubmit={handleEditDependsOn}
          currentDependsOn={
            editDependsOnItem.type === 'project'
              ? safeParseList((editDependsOnItem._data as ScenarioProject)?.next_step)
              : safeParseList((editDependsOnItem._data as ScenarioProjectTask)?.dependencies)
          }
          allItems={allSelectableItems}
          itemType={editDependsOnItem.type === 'project' ? 'project' : 'task'}
          parentId={editDependsOnItem.type === 'task' ? (editDependsOnItem._data as ScenarioProjectTask)?.id : undefined}
          parentType={editDependsOnItem.type}
        />
      )}
    </>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────────

// ── InfoField helper ───────────────────────────────────────────────────────────
function InfoField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-900">{value || '—'}</span>
    </div>
  );
}

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
  const [projectDialog, setProjectDialog] = useState<{ open: boolean; edit?: { id: string } & ScenarioProjectFormData }>({ open: false });
  const [taskDialog, setTaskDialog] = useState<{ open: boolean; edit?: { id: string } & ScenarioTaskFormData; projectId?: string }>({ open: false });

  // Star state
  const [starredIds, setStarredIds] = useState(new Set<string>());
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('grever_starred_scenarios') || '{}');
      setStarredIds(new Set(Object.keys(stored)));
    } catch {}

    const handler = () => {
      try {
        const stored = JSON.parse(localStorage.getItem('grever_starred_scenarios') || '{}');
        setStarredIds(new Set(Object.keys(stored)));
      } catch {}
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  useEffect(() => { fetchScenario(); }, [id]);

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

  function toggleStar() {
    if (!scenario) return;
    try {
      const stored = JSON.parse(localStorage.getItem('grever_starred_scenarios') || '{}');
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
      localStorage.setItem('grever_starred_scenarios', JSON.stringify(stored));
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
      const updateData: { name?: string; description?: string; status?: 'draft' | 'active' | 'deprecated' | 'archived' } = {}
      if (data.name !== undefined) updateData.name = data.name
      if (data.description !== undefined && data.description !== null) updateData.description = data.description
      if (data.status !== undefined) updateData.status = data.status as 'draft' | 'active' | 'deprecated' | 'archived'
      await scenariosApi.update(scenario!.id, updateData);
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
          <TabsTrigger value="diagram">
            <GitBranch className="w-3.5 h-3.5 mr-1" />场景详细
          </TabsTrigger>
          <TabsTrigger value="stats">统计</TabsTrigger>
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
                    <InfoField label="工程数" value={String(scenario.projects?.length || 0)} />
                    <InfoField label="任务数" value={String(scenario.projects?.reduce((sum: number, p: any) => sum + (p.tasks?.length || 0), 0) || 0)} />
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

        {/* ── Projects Tab (Sprint 85c + 87c) ── */}

        {/* ── Diagram Tab ── */}
        <TabsContent value="diagram">
          <DiagramTab scenario={scenario} onRefresh={fetchScenario} />
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
                      <TableCell className="text-muted-foreground">工程数</TableCell>
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

      </Tabs>

      </div>
  );
}