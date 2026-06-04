import React, { useState, useEffect } from 'react';
import { HUMAN_REVIEW } from '../../shared/api/paths';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Search,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  BarChart3,
  ExternalLink
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import { Checkbox } from '@/shared/components/ui/checkbox'
import { Separator } from '@/shared/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { DisputesTab } from './disputes/DisputesTab'

// Define interfaces
interface RulingItem {
  id: string;
  type: 'disputed' | 'waiting_human' | 'pending_assist';
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  status: string;
  created_at: string;
  updated_at: string;
  task_id: string;
  error_message?: string;
  goal_id?: string;
  project_id?: string;
  verification_cycle?: number;
  input_type?: string;
  submitted_by?: string;
  submitted_at?: string;
  metadata?: Record<string, any>;
}

// Extended interface for human input request details
interface HumanInputDetail {
  id: string;
  input_type: string;
  description: string;
  schema?: { choices?: string[] };
  task_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  submitted_value?: any;
  context?: Record<string, any>;
  title?: string;
  required_role?: string;
  assigned_to?: string;
}

interface RulingsStats {
  total: number;
  pending: number;
  submitted: number;
  rejected: number;
  disputed: number;
  waiting_human: number;
  byType: Record<string, number>;
  byPriority: Record<string, number>;
  recent: RulingItem[];
}

// ==================== Status/Type/Priority badges ====================

function getStatusBadge(status: string) {
  const config: Record<string, { variant: string; label: string }> = {
    pending: { variant: 'outline', label: '待处理' },
    submitted: { variant: 'default', label: '已提交' },
    rejected: { variant: 'destructive', label: '已拒绝' },
    disputed: { variant: 'warning', label: '争议中' },
    waiting_human: { variant: 'warning', label: '等待人工' },
    done: { variant: 'default', label: '已完成' },
    in_progress: { variant: 'default', label: '进行中' },
    review_needed: { variant: 'secondary', label: '待审核' },
    timeout: { variant: 'secondary', label: '已超时' }
  };
  const c = config[status] || { variant: 'secondary', label: status };
  return <Badge variant={c.variant as any}>{c.label}</Badge>;
}

function getTypeBadge(type: string) {
  const config: Record<string, { variant: string; label: string }> = {
    disputed: { variant: 'warning', label: '争议' },
    waiting_human: { variant: 'warning', label: '待审批' },
    pending_assist: { variant: 'secondary', label: '待输入' },
  };
  const c = config[type] || { variant: 'secondary', label: type };
  return <Badge variant={c.variant as any}>{c.label}</Badge>;
}

function getPriorityBadge(priority: string) {
  const config: Record<string, { variant: string; label: string }> = {
    low: { variant: 'default', label: '低' },
    medium: { variant: 'warning', label: '中' },
    high: { variant: 'destructive', label: '高' },
  };
  const c = config[priority] || { variant: 'secondary', label: priority };
  return <Badge variant={c.variant as any}>{c.label}</Badge>;
}

// ==================== Type-specific badges ====================

function InputTypeBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    approval: '审批',
    confirmation: '确认',
    input: '协助',
    choice: '选择',
  };
  return <Badge variant="secondary">{labels[type] || type}</Badge>;
}

// ==================== Context explanation helper ====================

function getContextExplanation(req: HumanInputDetail): { reason: string; action: string; consequence: string } {
  const typeDefaults: Record<string, { reason: string; action: string; consequence: string }> = {
    approval: {
      reason: 'Agent 需要你的批准才能继续。',
      action: '判断这个决策是否合理，选择"批准"或"拒绝"。',
      consequence: '批准后 Agent 继续执行；拒绝后停止或采用替代方案。',
    },
    confirmation: {
      reason: 'Agent 需要你确认这个操作是正确的。',
      action: '确认无误后点击"确认"；有问题点击"否决"并说明原因。',
      consequence: '确认后 Agent 执行操作；否决后操作取消。',
    },
    input: {
      reason: 'Agent 需要你提供额外信息或指导。',
      action: '在输入框中填写你希望 Agent 知道的内容。',
      consequence: '提交后 Agent 根据输入继续执行。',
    },
    choice: {
      reason: 'Agent 需要你从多个方案中选择一个。',
      action: '选择最合适的方案，然后点击"提交"。',
      consequence: '提交后 Agent 按你选择的方案执行。',
    },
  };
  const base = typeDefaults[req.input_type] || typeDefaults.confirmation;
  const reason = req.description ? `${req.description} — ${base.reason}` : base.reason;
  return { reason, action: base.action, consequence: base.consequence };
}

// ==================== Quick ruling modal ====================

interface QuickRulingModalProps {
  item: RulingItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (action: string, ruling: string, inputData?: any) => void;
}

function QuickRulingModal({ item, isOpen, onClose, onSubmit }: QuickRulingModalProps) {
  // Ruling (disputed) state
  const [rulingAction, setRulingAction] = useState('approve');
  const [ruling, setRuling] = useState('');
  const [verifComments, setVerifComments] = useState<Array<{content: string; created_at: string}>>([]);
  const [acceptanceCriteria, setAcceptanceCriteria] = useState<any[]>([]);

  // Assist/Approval state
  const [assistDetail, setAssistDetail] = useState<HumanInputDetail | null>(null);
  const [assistLoading, setAssistLoading] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [choiceValue, setChoiceValue] = useState('');
  const [approvalReason, setApprovalReason] = useState('');

  useEffect(() => {
    if (isOpen && item) {
      setRulingAction('approve');
      setRuling('');
      setVerifComments([]);
      setAcceptanceCriteria([]);
      setAssistDetail(null);
      setAssistLoading(false);
      setTextInput('');
      setChoiceValue('');
      setApprovalReason('');

      // For pending_assist type, fetch full human input details by ID
      if (item.type === 'pending_assist' && item.id) {
        setAssistLoading(true);
        fetch(`/api/v1/human-input/${item.id}`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data) {
              setAssistDetail(data);
              if (data.schema?.choices && Array.isArray(data.schema.choices)) {
                setChoiceValue(data.schema.choices[0] || '');
              }
            }
            setAssistLoading(false);
          })
          .catch(() => { setAssistLoading(false); });
      }

      // For waiting_human type, try to find associated human_input_request by task_id
      if (item.type === 'waiting_human' && item.task_id) {
        setAssistLoading(true);
        fetch(`/api/v1/human-input/task/${item.task_id}`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data && data.length > 0) {
              const pending = data.find((d: any) => d.status === 'pending') || data[0];
              setAssistDetail(pending);
              if (pending.schema?.choices && Array.isArray(pending.schema.choices)) {
                setChoiceValue(pending.schema.choices[0] || '');
              }
            }
            setAssistLoading(false);
          })
          .catch(() => { setAssistLoading(false); });
      }

      // For disputed type, load verification comments
      if (item.type === 'disputed') {
        fetch(`/api/v1/tasks/${item.task_id}/comments`)
          .then(r => r.ok ? r.json() : [])
          .then((data: any[]) => {
            if (Array.isArray(data)) {
              setVerifComments(data.filter((c: any) => c.type === 'verification_result').slice(-5));
            }
          })
          .catch(() => {});
        fetch(`/api/v1/tasks/${item.task_id}`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data && data.acceptance_criteria) {
              try {
                const ac = typeof data.acceptance_criteria === 'string'
                  ? JSON.parse(data.acceptance_criteria) : data.acceptance_criteria;
                setAcceptanceCriteria(ac.criteria || ac || []);
              } catch { /* */ }
            }
          })
          .catch(() => {});
      }
    }
  }, [isOpen, item?.id]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (item?.type === 'pending_assist' || (item?.type === 'waiting_human' && assistDetail)) {
      handleAssistSubmit();
    } else if (item?.type === 'waiting_human' && !assistDetail) {
      handleApprovalSubmit();
    } else {
      onSubmit(rulingAction, ruling);
    }
  };

  // 待输入/审批: 通过 human-input API 提交
  const handleAssistSubmit = () => {
    if (!assistDetail) return;
    let inputData: any;
    switch (assistDetail.input_type) {
      case 'approval':
        if (!approvalReason.trim()) { alert('请填写审批理由'); return; }
        inputData = { approved: true, approval_reason: approvalReason.trim() };
        break;
      case 'confirmation':
        inputData = { confirmed: true };
        break;
      case 'input':
        inputData = textInput.trim();
        if (!inputData) { alert('请输入内容'); return; }
        break;
      case 'choice':
        inputData = choiceValue;
        if (!inputData) { alert('请选择一个方案'); return; }
        break;
      default:
        inputData = textInput.trim();
    }
    onSubmit('approve', ruling, inputData);
  };

  // 待审批(无关联 HITL): 通过 batch-ruling API 提交
  const handleApprovalSubmit = () => {
    onSubmit(rulingAction, ruling);
  };

  if (!item) return null;

  const typeLabels: Record<string, string> = {
    disputed: '争议', waiting_human: '待审批', pending_assist: '待输入',
  };

  // ==================== 待审批 (without assistDetail) ====================
  const renderApprovalContent = () => (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 这是什么 */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-4">
          <h4 className="text-sm font-semibold text-blue-800 mb-2">📋 这是什么请求？</h4>
          <p className="text-sm text-blue-900 leading-relaxed">{item.description || 'Agent 请求你的审批。'}</p>
          {item.task_id && (
            <div className="mt-2 text-xs text-blue-700 bg-blue-100 rounded px-2 py-1 inline-block font-mono">
              关联任务: {item.task_id}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 为什么需要你 */}
      <Card className="bg-amber-50 border-amber-200">
        <CardContent className="pt-4">
          <h4 className="text-sm font-semibold text-amber-800 mb-2">❓ 为什么需要你？</h4>
          <p className="text-sm text-amber-900 leading-relaxed">Agent 执行到决策点，暂停等待你的批准。请判断这个操作是否合理。</p>
        </CardContent>
      </Card>

      {/* 你需要做什么 */}
      <Card className="bg-green-50 border-green-200">
        <CardContent className="pt-4">
          <h4 className="text-sm font-semibold text-green-800 mb-2">✅ 你需要做什么？</h4>
          <p className="text-sm text-green-900 leading-relaxed">选择"批准"让 Agent 继续，或"拒绝"终止这个操作。</p>
          <p className="text-xs text-green-700 mt-2">💡 批准 → Agent 继续执行；拒绝 → 操作终止，任务标记失败。</p>
        </CardContent>
      </Card>

      <Separator />

      {/* 审批操作：只有批准/拒绝 */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">审批操作</label>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'approve', label: '批准', desc: '放行，继续执行' },
            { value: 'reject', label: '拒绝', desc: '终止操作' },
          ].map(opt => (
            <Button
              key={opt.value}
              type="button"
              variant={rulingAction === opt.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setRulingAction(opt.value)}
              className="flex flex-col items-center h-auto py-2"
            >
              <span>{opt.label}</span>
              <span className="text-xs opacity-60">{opt.desc}</span>
            </Button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">审批说明（可选）</label>
        <Textarea
          value={ruling}
          onChange={(e) => setRuling(e.target.value)}
          rows={3}
          placeholder="请输入审批说明..."
        />
      </div>
    </form>
  );

  // ==================== 待输入/审批(有关联 HITL) ====================
  const renderAssistContent = () => {
    if (assistLoading) {
      return <div className="flex justify-center py-8"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div></div>;
    }
    if (!assistDetail) {
      return <p className="text-sm text-muted-foreground text-center py-8">无法加载请求详情</p>;
    }

    const explanation = getContextExplanation(assistDetail);
    const btnMap: Record<string, { confirm: string; reject: string }> = {
      approval: { confirm: '批准', reject: '拒绝' },
      confirmation: { confirm: '确认', reject: '否决' },
      input: { confirm: '提交', reject: '拒绝' },
      choice: { confirm: '提交', reject: '拒绝' },
    };
    const btnLabels = btnMap[assistDetail.input_type] || btnMap.confirmation;

    return (
      <div className="space-y-4">
        {/* 这是什么 */}
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-4">
            <h4 className="text-sm font-semibold text-blue-800 mb-2">📋 这是什么请求？</h4>
            <p className="text-sm text-blue-900 leading-relaxed">{assistDetail.description || 'Agent 需要你提供人工协助。'}</p>
            {assistDetail.task_id && (
              <div className="mt-2 text-xs text-blue-700 bg-blue-100 rounded px-2 py-1 inline-block font-mono">
                关联任务: {assistDetail.task_id}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 权限要求 */}
        {(assistDetail as any).required_role || (assistDetail as any).assigned_to ? (
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="pt-4">
              <h4 className="text-sm font-semibold text-amber-800 mb-2">🔐 权限要求</h4>
              {(assistDetail as any).required_role && <p className="text-xs text-amber-900 mb-1">要求角色: <strong>{(assistDetail as any).required_role}</strong></p>}
              {(assistDetail as any).assigned_to && <p className="text-xs text-amber-900">指定人员: <strong>{(assistDetail as any).assigned_to}</strong></p>}
            </CardContent>
          </Card>
        ) : null}

        {/* 为什么需要你 */}
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="pt-4">
            <h4 className="text-sm font-semibold text-amber-800 mb-2">❓ 为什么需要你？</h4>
            <p className="text-sm text-amber-900 leading-relaxed">{explanation.reason}</p>
          </CardContent>
        </Card>

        {/* 你需要做什么 */}
        <Card className="bg-green-50 border-green-200">
          <CardContent className="pt-4">
            <h4 className="text-sm font-semibold text-green-800 mb-2">✅ 你需要做什么？</h4>
            <p className="text-sm text-green-900 leading-relaxed">{explanation.action}</p>
            <p className="text-xs text-green-700 mt-2">💡 {explanation.consequence}</p>
          </CardContent>
        </Card>

        <Separator />

        {/* 审批 */}
        {assistDetail.input_type === 'approval' && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Agent 正在等待你的审批决定：</p>
            {assistDetail.context?.before_snapshot && (
              <Card className="bg-slate-50 border-slate-200">
                <CardContent className="pt-4">
                  <h4 className="text-xs font-semibold text-slate-700 mb-2">📸 审批前状态</h4>
                  <pre className="text-xs text-slate-600 whitespace-pre-wrap max-h-32 overflow-auto">
                    {typeof assistDetail.context.before_snapshot === 'string'
                      ? assistDetail.context.before_snapshot
                      : JSON.stringify(assistDetail.context.before_snapshot, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium text-red-700">审批理由 <span className="text-red-500">*必填</span></label>
              <Textarea
                value={approvalReason}
                onChange={e => setApprovalReason(e.target.value)}
                placeholder="请输入审批理由，说明通过或驳回的原因..."
                rows={3}
                className="border-red-200 focus:border-red-400"
              />
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={handleAssistSubmit}>
                <CheckCircle className="w-4 h-4 mr-1" />{btnLabels.confirm}
              </Button>
              <Button variant="destructive" className="flex-1" onClick={() => onSubmit('reject', ruling)}>
                <XCircle className="w-4 h-4 mr-1" />{btnLabels.reject}
              </Button>
            </div>
          </div>
        )}

        {/* 确认 */}
        {assistDetail.input_type === 'confirmation' && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">请确认以下操作是否正确：</p>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={handleAssistSubmit}>
                <CheckCircle className="w-4 h-4 mr-1" />{btnLabels.confirm}
              </Button>
              <Button variant="destructive" className="flex-1" onClick={() => onSubmit('reject', ruling)}>
                <XCircle className="w-4 h-4 mr-1" />{btnLabels.reject}
              </Button>
            </div>
          </div>
        )}

        {/* 协助(文本输入) */}
        {assistDetail.input_type === 'input' && (
          <div className="space-y-3">
            <label className="text-sm font-medium">请输入你希望 Agent 知道的信息：</label>
            <Textarea
              value={textInput}
              onChange={e => setTextInput(e.target.value)}
              placeholder="输入你的指令、补充信息或决策依据..."
              rows={4}
            />
            <div className="flex gap-2">
              <Button className="flex-1" disabled={!textInput.trim()} onClick={handleAssistSubmit}>{btnLabels.confirm}</Button>
              <Button variant="destructive" className="flex-1" onClick={() => onSubmit('reject', ruling)}>
                <XCircle className="w-4 h-4 mr-1" />{btnLabels.reject}
              </Button>
            </div>
          </div>
        )}

        {/* 选择 */}
        {assistDetail.input_type === 'choice' && assistDetail.schema?.choices && Array.isArray(assistDetail.schema.choices) && (
          <div className="space-y-3">
            <label className="text-sm font-medium">请选择一个方案：</label>
            <Select value={choiceValue} onValueChange={setChoiceValue}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {assistDetail.schema.choices.map((choice: string, idx: number) => (
                  <SelectItem key={idx} value={choice}>{choice}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={handleAssistSubmit}>{btnLabels.confirm}</Button>
              <Button variant="destructive" className="flex-1" onClick={() => onSubmit('reject', ruling)}>
                <XCircle className="w-4 h-4 mr-1" />{btnLabels.reject}
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // ==================== 待裁决 (disputed) ====================
  const renderRulingContent = () => (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 争议点 */}
      <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
        <h4 className="text-sm font-medium text-red-700 mb-1">⚠️ 争议点</h4>
        <p className="text-sm text-red-800 whitespace-pre-wrap">{item.error_message || '验证连续失败，升级至人工裁决'}</p>
        {item.verification_cycle && (
          <span className={`text-xs mt-1 inline-block ${item.verification_cycle >= 3 ? 'text-red-600 font-bold' : 'text-red-500'}`}>
            验证周期 {item.verification_cycle}/3
          </span>
        )}
      </div>

      {/* 验收标准 */}
      {acceptanceCriteria.length > 0 && (
        <div className="p-3 bg-slate-50 border rounded-lg">
          <h4 className="text-sm font-medium text-slate-700 mb-2">验收标准</h4>
          <div className="space-y-1">
            {acceptanceCriteria.map((c: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <Badge variant="secondary" className="text-xs shrink-0">{c.type || '?'}</Badge>
                <span className="text-slate-700">{c.desc || c.description || c.name || ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 验证历史 */}
      {verifComments.length > 0 && (
        <div className="p-3 bg-slate-50 border rounded-lg">
          <h4 className="text-sm font-medium text-slate-700 mb-2">验证历史</h4>
          <div className="space-y-1.5 max-h-40 overflow-y-auto">
            {verifComments.map((c, i) => {
              const isDisputed = c.content.startsWith('DISPUTED');
              const isFail = c.content.startsWith('FAIL');
              const color = isDisputed ? 'text-red-700 bg-red-50 border-red-200'
                : isFail ? 'text-orange-700 bg-orange-50 border-orange-200'
                : 'text-green-700 bg-green-50 border-green-200';
              return (
                <div key={i} className={`p-2 rounded border text-xs ${color}`}>
                  <div className="font-medium">{c.content.split('\n')[0]}</div>
                  {c.content.split('\n').slice(1).join('\n') && (
                    <div className="mt-0.5 whitespace-pre-wrap opacity-80">{c.content.split('\n').slice(1).join('\n')}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 裁决操作：通过/拒绝/要求修改 */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">裁决操作</label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: 'approve', label: '通过', desc: '结果接受，标记完成' },
            { value: 'reject', label: '拒绝', desc: '结果不可接受，标记失败' },
            { value: 'request_changes', label: '要求修改', desc: '方向对但有问题，退回重做' },
          ].map(opt => (
            <Button
              key={opt.value}
              type="button"
              variant={rulingAction === opt.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setRulingAction(opt.value)}
              className="flex flex-col items-center h-auto py-2"
            >
              <span>{opt.label}</span>
              <span className="text-xs opacity-60">{opt.desc}</span>
            </Button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">裁决说明</label>
        <Textarea
          value={ruling}
          onChange={(e) => setRuling(e.target.value)}
          rows={3}
          placeholder="请输入裁决说明..."
        />
      </div>
    </form>
  );

  // ==================== Footer ====================
  const renderFooter = () => {
    if (item.type === 'pending_assist') return null; // assist has inline buttons
    if (item.type === 'waiting_human' && assistDetail) return null; // assist has inline buttons

    return (
      <DialogFooter className="gap-2">
        <Button asChild variant="outline" size="sm">
          <Link to={`/coordination/tasks/${item.task_id}`}>查看任务</Link>
        </Button>
        <Button type="button" variant="outline" onClick={onClose}>取消</Button>
        <Button type="submit" onClick={handleSubmit}>
          {item.type === 'waiting_human' ? '提交审批' : '提交裁决'}
        </Button>
      </DialogFooter>
    );
  };

  // ==================== Main render ====================
  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{item.title}</DialogTitle>
          <DialogDescription className="flex items-center gap-2 flex-wrap">
            <Badge variant="secondary">{typeLabels[item.type] || item.type}</Badge>
            {(item.type === 'pending_assist' || item.type === 'waiting_human') && assistDetail && <InputTypeBadge type={assistDetail.input_type} />}
            {getStatusBadge(item.status)}
            {getPriorityBadge(item.priority)}
            <span className="text-xs text-slate-400 ml-auto">
              {new Date(item.created_at).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })}
            </span>
          </DialogDescription>
        </DialogHeader>

        {/* Three-way routing */}
        {item.type === 'disputed' ? renderRulingContent() :
         item.type === 'pending_assist' || (item.type === 'waiting_human' && assistDetail) ? renderAssistContent() :
         item.type === 'waiting_human' ? renderApprovalContent() :
         renderRulingContent()}

        {renderFooter()}
      </DialogContent>
    </Dialog>
  );
}

// ==================== Main component ====================

const RulingsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as 'all' | 'disputed' | 'approval' | 'assist' | 'disputes') || 'all';
  const [activeTab, setActiveTab] = useState<'all' | 'disputed' | 'approval' | 'assist' | 'disputes'>(initialTab);
  const [items, setItems] = useState<RulingItem[]>([]);
  const [stats, setStats] = useState<RulingsStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [quickRulingModalOpen, setQuickRulingModalOpen] = useState(false);
  const [quickRulingItem, setQuickRulingItem] = useState<RulingItem | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // Batch ruling state
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [batchProgress, setBatchProgress] = useState(0);
  const [batchResult, setBatchResult] = useState<{
    show: boolean;
    successCount: number;
    failedCount: number;
    failedItems: Array<{id: string; type: string; error: string}>;
  } | null>(null);
  const [showFailedDetails, setShowFailedDetails] = useState(false);

  useEffect(() => {
    fetchRulings();
  }, [activeTab, filterPriority, searchQuery, currentPage, pageSize, sortField, sortOrder]);

  const fetchRulings = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      const typeMap: Record<string, string> = {
        all: 'all', disputed: 'disputed',
        approval: 'waiting', assist: 'assist',
      };
      
      params.append('type', typeMap[activeTab] || 'all');
      if (filterPriority !== 'all') params.append('priority', filterPriority);
      if (searchQuery) params.append('search', searchQuery);
      params.append('limit', pageSize.toString());
      params.append('offset', ((currentPage - 1) * pageSize).toString());
      params.append('sort_by', sortField);
      params.append('sort_order', sortOrder);

      const response = await fetch(`/api/v1/human-review/pending?${params}`);
      if (response.ok) {
        const data = await response.json();
        setItems(data.items || []);
      }

      const statsResponse = await fetch(HUMAN_REVIEW.GET_STATS);
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats({
          total: statsData.total || 0,
          pending: statsData.pending_count || 0,
          submitted: statsData.submitted_count || 0,
          rejected: statsData.rejected_count || 0,
          disputed: statsData.disputed_count || 0,
          waiting_human: statsData.waiting_human_count || 0,
          byType: statsData.by_type || {},
          byPriority: statsData.by_priority || {},
          recent: statsData.recent_pending || [],
        });
      }
    } catch (error) {
      console.error('Error fetching rulings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectItem = (id: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(id)) newSelected.delete(id);
    else newSelected.add(id);
    setSelectedItems(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) setSelectedItems(new Set(items.map(item => item.id)));
    else setSelectedItems(new Set());
  };

  const handleQuickRuling = async (action: string, ruling: string, inputData?: any) => {
    if (!quickRulingItem) return;
    try {
      // 待输入/待审批(有关联 HITL)：走 human-input API
      if (quickRulingItem.type === 'pending_assist') {
        const submitData = {
          input_data: inputData || {},
          submitted_by: 'web-user',
        };
        const response = await fetch(`/api/v1/human-input/${quickRulingItem.id}/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(submitData),
        });
        if (response.ok) {
          fetchRulings();
          setQuickRulingModalOpen(false);
        } else {
          const err = await response.json();
          alert(err.detail || '提交失败');
        }
      } else if (quickRulingItem.type === 'waiting_human') {
        const hirResp = await fetch(`/api/v1/human-input/task/${quickRulingItem.task_id}`);
        if (hirResp.ok) {
          const hirData = await hirResp.json();
          const pendingHir = Array.isArray(hirData) ? hirData.find((d: any) => d.status === 'pending') : null;
          if (pendingHir) {
            // 有关联 HITL → 走 human-input API
            const submitData = {
              input_data: inputData || {},
              submitted_by: 'web-user',
            };
            const response = await fetch(`/api/v1/human-input/${pendingHir.id}/submit`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(submitData),
            });
            if (response.ok) {
              fetchRulings();
              setQuickRulingModalOpen(false);
            } else {
              const err = await response.json();
              alert(err.detail || '提交失败');
            }
          } else {
            // 无关联 HITL → 走 batch-ruling API (approve/reject 对应 done/failed)
            const rulingAction = action === 'approve' ? 'done' : action === 'reject' ? 'failed' : action;
            const rulingData = {
              items: [{ id: quickRulingItem.id, type: quickRulingItem.type, ruling, action: rulingAction }],
              global_ruling: ruling
            };
            const response = await fetch(HUMAN_REVIEW.BATCH_RULING, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(rulingData)
            });
            if (response.ok) {
              fetchRulings();
              setQuickRulingModalOpen(false);
            }
          }
        } else {
          // API 不可达 → 走 batch-ruling
          const rulingAction = action === 'approve' ? 'done' : action === 'reject' ? 'failed' : action;
          const rulingData = {
            items: [{ id: quickRulingItem.id, type: quickRulingItem.type, ruling, action: rulingAction }],
            global_ruling: ruling
          };
          const response = await fetch(HUMAN_REVIEW.BATCH_RULING, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rulingData)
          });
          if (response.ok) {
            fetchRulings();
            setQuickRulingModalOpen(false);
          }
        }
      } else {
        // 待裁决：走 batch-ruling API
        const rulingData = {
          items: [{ id: quickRulingItem.id, type: quickRulingItem.type, ruling, action }],
          global_ruling: ruling
        };
        const response = await fetch(HUMAN_REVIEW.BATCH_RULING, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(rulingData)
        });
        if (response.ok) {
          fetchRulings();
          setQuickRulingModalOpen(false);
        }
      }
    } catch (error) {
      console.error('Error submitting ruling:', error);
    }
  };

  const handleBatchRuling = async (action: string) => {
    if (selectedItems.size === 0) return;
    setIsBatchProcessing(true);
    setBatchProgress(0);
    setBatchResult(null);

    const selectedArray = Array.from(selectedItems);
    const totalItems = selectedArray.length;
    let processedCount = 0;
    let successCount = 0;
    let failedCount = 0;
    const failedItems: Array<{id: string; type: string; error: string}> = [];

    for (const id of selectedArray) {
      const item = items.find(i => i.id === id);
      const rulingData = {
        items: [{ id, type: item?.type || 'disputed', ruling: `Batch: ${action}`, action }],
        global_ruling: `Batch action: ${action}`
      };

      try {
        const response = await fetch(HUMAN_REVIEW.BATCH_RULING, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(rulingData)
        });
        if (response.ok) {
          const result = await response.json();
          const itemResult = result.results?.[0];
          if (itemResult?.success) successCount++;
          else { failedCount++; failedItems.push({ id, type: item?.type || 'unknown', error: itemResult?.error || '裁决失败' }); }
        } else {
          failedCount++;
          failedItems.push({ id, type: item?.type || 'unknown', error: 'Request failed' });
        }
      } catch (err: any) {
        failedCount++;
        failedItems.push({ id, type: item?.type || 'unknown', error: err.message || 'Network error' });
      }

      processedCount++;
      setBatchProgress(Math.round((processedCount / totalItems) * 100));
    }

    setBatchResult({ show: true, successCount, failedCount, failedItems });
    setSelectedItems(new Set());
    setIsBatchProcessing(false);
    fetchRulings();
  };

  const refreshData = () => { fetchRulings(); };

  if (loading && !items.length) {
    return (
      <div className="w-full h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const tabList = [
    { key: 'all', label: '全部', count: stats?.total || 0 },
    { key: 'disputed', label: '待裁决', count: stats?.disputed || 0 },
    { key: 'approval', label: '待审批', count: stats?.waiting_human || 0 },
    { key: 'assist', label: '待输入', count: stats?.pending || 0 },
    { key: 'disputes', label: '争议管理', count: 0 },
  ] as const;

  return (
    <div className="w-full h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <div className="p-4 bg-white border-b">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">裁决中心</h1>
            <p className="text-sm text-slate-500">Human Ruling Dashboard</p>
          </div>
          <Button variant="outline" size="sm" onClick={refreshData}>
            <RefreshCw className="w-4 h-4" />
            刷新
          </Button>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v as any); setCurrentPage(1); }}>
          <TabsList>
            {tabList.map(tab => (
              <TabsTrigger key={tab.key} value={tab.key} className="gap-1.5">
                {tab.label}
                <span className="ml-1 px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-600">
                  {tab.count}
                </span>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Filters (hidden for disputes tab) */}
      {activeTab !== 'disputes' && (
      <div className="p-4 bg-white border-b flex flex-wrap gap-3">
        <div className="flex-1 min-w-64 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索标题、描述..."
            className="pl-10"
          />
        </div>
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="全部优先级" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部优先级</SelectItem>
            <SelectItem value="low">低优先级</SelectItem>
            <SelectItem value="medium">中优先级</SelectItem>
            <SelectItem value="high">高优先级</SelectItem>
          </SelectContent>
        </Select>
        <Select value={pageSize.toString()} onValueChange={(v) => { setPageSize(Number(v)); setCurrentPage(1); }}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="10">10/页</SelectItem>
            <SelectItem value="20">20/页</SelectItem>
            <SelectItem value="50">50/页</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortField} onValueChange={setSortField}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="created_at">创建时间</SelectItem>
            <SelectItem value="updated_at">更新时间</SelectItem>
            <SelectItem value="priority">优先级</SelectItem>
            <SelectItem value="status">状态</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortOrder} onValueChange={(v) => setSortOrder(v as 'asc' | 'desc')}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="desc">降序</SelectItem>
            <SelectItem value="asc">升序</SelectItem>
          </SelectContent>
        </Select>
      </div>
      )}

      {/* Batch Operations (hidden for disputes tab) */}
      {activeTab !== 'disputes' && selectedItems.size > 0 && (
        <div className="p-4 bg-blue-50 border-b space-y-3">
          <div className="flex justify-between items-center">
            <div className="text-sm text-blue-700">已选择 {selectedItems.size} 项</div>
            <div className="flex gap-2">
              <Button size="sm" className="bg-amber-500 hover:bg-amber-600" onClick={() => handleBatchRuling('approve')} disabled={isBatchProcessing}>
                批量通过
              </Button>
              <Button size="sm" variant="destructive" onClick={() => handleBatchRuling('reject')} disabled={isBatchProcessing}>
                批量拒绝
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleBatchRuling('request_changes')} disabled={isBatchProcessing}>
                批量要求修改
              </Button>
            </div>
          </div>
          
          {isBatchProcessing && (
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-blue-600">正在处理... {batchProgress}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2.5">
                <div 
                  className={`h-2.5 rounded-full transition-all duration-300 ${batchProgress === 100 ? 'bg-green-500' : 'bg-blue-500'}`}
                  style={{ width: `${batchProgress}%` }}
                />
              </div>
            </div>
          )}
          
          {batchResult && batchResult.show && (
            <Card className="border-slate-200">
              <CardContent className="p-3">
                <div className="flex justify-between items-start mb-2">
                  <div className="text-sm">
                    <span className="text-green-600 font-medium">成功: {batchResult.successCount}</span>
                    {batchResult.failedCount > 0 && (
                      <span className="text-red-600 font-medium ml-3">失败: {batchResult.failedCount}</span>
                    )}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => { setBatchResult(null); setShowFailedDetails(false); }}>×</Button>
                </div>
                
                {batchResult.failedCount > 0 && batchResult.failedItems.length > 0 && (
                  <div className="mt-2">
                    <button
                      onClick={() => setShowFailedDetails(!showFailedDetails)}
                      className="flex items-center gap-1 text-xs text-red-600 font-medium"
                    >
                      {showFailedDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      失败详情 ({batchResult.failedCount} 项)
                    </button>
                    
                    {showFailedDetails && (
                      <div className="mt-2 max-h-64 overflow-y-auto space-y-1">
                        {batchResult.failedItems.map((item, idx) => (
                          <div key={idx} className="flex justify-between items-start p-1.5 bg-red-50 rounded border border-red-100 text-xs">
                            <div className="flex-1 min-w-0">
                              <span className="text-red-600">{item.type}</span>
                              <span className="text-slate-500 ml-1 font-mono text-[10px]">{item.id}</span>
                              <div className="text-red-500 text-[11px] break-all mt-0.5">{item.error}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Content */}
      {activeTab === 'disputes' ? (
        <div className="flex-1 overflow-y-auto p-4">
          <DisputesTab />
        </div>
      ) : (
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12">
            <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">暂无待处理项</p>
            <p className="text-sm text-slate-400 mt-1">切换筛选条件或刷新试试</p>
          </div>
        ) : (
          <div className="bg-white">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={selectedItems.size === items.length && items.length > 0}
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead className="w-28">类型</TableHead>
                  <TableHead className="w-20">优先级</TableHead>
                  <TableHead className="w-28">状态</TableHead>
                  <TableHead className="w-36">创建时间</TableHead>
                  <TableHead className="w-36">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id} className="cursor-pointer hover:bg-slate-50" onClick={() => { setQuickRulingItem(item); setQuickRulingModalOpen(true); }}>
                    <TableCell>
                      <Checkbox
                        checked={selectedItems.has(item.id)}
                        onCheckedChange={(checked) => { if (checked) handleSelectItem(item.id); else { const s = new Set(selectedItems); s.delete(item.id); setSelectedItems(s); } }}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-foreground truncate max-w-md">{item.title}</div>
                      {item.description && (
                        <p className="text-sm text-muted-foreground mt-0.5 line-clamp-1 truncate max-w-lg">{item.description}</p>
                      )}
                    </TableCell>
                    <TableCell>{getTypeBadge(item.type)}</TableCell>
                    <TableCell>{getPriorityBadge(item.priority)}</TableCell>
                    <TableCell>{getStatusBadge(item.status)}</TableCell>
                    <TableCell>
                      <span className="text-sm text-foreground">{new Date(item.created_at).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="sm" onClick={() => { setQuickRulingItem(item); setQuickRulingModalOpen(true); }}>
                          {item.type === 'disputed' ? '裁决' : item.type === 'waiting_human' ? '审批' : '处理'}
                        </Button>
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/coordination/tasks/${item.task_id}`}><ExternalLink className="w-3 h-3" /></Link>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
      )}

      {/* Pagination (hidden for disputes tab) */}
      {activeTab !== 'disputes' && (
      <div className="p-4 bg-white border-t flex justify-between items-center">
        <p className="text-sm text-slate-600">
          显示 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, stats?.total || 0)} 条，共 {stats?.total || 0} 条
        </p>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            上一页
          </Button>
          <span className="px-3 py-2 text-sm">
            {currentPage} / {Math.ceil((stats?.total || 1) / pageSize)}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCurrentPage(p => Math.min(Math.ceil((stats?.total || 1) / pageSize), p + 1))}
            disabled={currentPage === Math.ceil((stats?.total || 1) / pageSize)}
          >
            下一页
          </Button>
        </div>
      </div>
      )}

      {/* Quick Ruling Modal */}
      <QuickRulingModal
        item={quickRulingItem}
        isOpen={quickRulingModalOpen}
        onClose={() => setQuickRulingModalOpen(false)}
        onSubmit={handleQuickRuling}
      />
    </div>
  );
};

export default RulingsPage;
