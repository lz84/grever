import React, { useState, useEffect, useCallback } from 'react';
import { humanInputApi } from '../../../shared/utils/api';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, Loader2, CheckCircle, XCircle, Clock,
  GitBranch, Zap, ArrowRight, AlertCircle,
} from 'lucide-react';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { Progress } from '@/shared/components/ui/progress';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/shared/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/components/ui/select';
import { Textarea } from '@/shared/components/ui/textarea';
import { Separator } from '@/shared/components/ui/separator';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from '@/shared/components/ui/sheet';

// ============================================================================
// Types
// ============================================================================

interface HumanInputRequest {
  id: string;
  input_type: string;
  description: string;
  schema?: any;
  task_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  expired_at?: string;
  submitted_value?: any;
  history?: HistoryEntry[];
  context?: Record<string, any>;
  title?: string;
}

interface HistoryEntry {
  timestamp: string;
  status: string;
  message?: string;
  submitted_value?: any;
}

interface HumanInputStats {
  total: number;
  pending: number;
  submitted: number;
  rejected: number;
  expired: number;
  by_type: Record<string, number>;
}

// ============================================================================
// Status Badge (shadcn)
// ============================================================================

function StatusBadge({ status }: { status: string }) {
  const variant = status === 'pending' ? 'outline' : status === 'submitted' ? 'default' : status === 'rejected' ? 'destructive' : 'secondary';
  const labels: Record<string, string> = {
    pending: '待处理',
    submitted: '已提交',
    rejected: '已拒绝',
    expired: '已过期',
  };
  return <Badge variant={variant as any}>{labels[status] || status}</Badge>;
}

function TypeBadge({ type }: { type: string }) {
  const labels: Record<string, string> = {
    approval: '审批',
    confirmation: '确认',
    input: '协助',
    choice: '选择',
  };
  return <Badge variant="secondary">{labels[type] || type}</Badge>;
}

// ============================================================================
// Stats Cards (shadcn Card)
// ============================================================================

function StatsCards({ stats }: { stats: HumanInputStats }) {
  const cards = [
    { label: '总计', value: stats.total, variant: 'default' as const },
    { label: '待处理', value: stats.pending, variant: 'outline' as const },
    { label: '已提交', value: stats.submitted, variant: 'default' as const },
    { label: '已拒绝', value: stats.rejected, variant: 'destructive' as const },
    { label: '已过期', value: stats.expired, variant: 'secondary' as const },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
      {cards.map(c => (
        <Card key={c.label} className="text-center py-3">
          <CardContent className="p-0">
            <div className="text-2xl font-bold">{c.value}</div>
            <div className="text-xs text-muted-foreground">{c.label}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ============================================================================
// Human Input Detail Sheet (shadcn Sheet)
// ============================================================================

interface DetailSheetProps {
  inputRequest: HumanInputRequest | null;
  onClose: () => void;
  onSubmit: (inputId: string, value: any) => void;
  onReject: (inputId: string, reason?: string) => void;
}

function getContextExplanation(req: HumanInputRequest): { reason: string; action: string; consequence: string } {
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

function HumanInputDetailSheet({ inputRequest, onClose, onSubmit, onReject }: DetailSheetProps) {
  const [textInput, setTextInput] = useState('');
  const [choiceValue, setChoiceValue] = useState('');
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  // Sprint 91: approval_reason state
  const [approvalReason, setApprovalReason] = useState('');

  useEffect(() => {
    if (inputRequest) {
      setTextInput('');
      setShowReject(false);
      setRejectReason('');
      setApprovalReason('');
      if (inputRequest.schema?.choices && Array.isArray(inputRequest.schema.choices)) {
        // 只接受字符串类型的初始值
        const sv = inputRequest.submitted_value;
        const initial = typeof sv === 'string' ? sv : (inputRequest.schema.choices[0] || '');
        setChoiceValue(initial);
      }
    }
  }, [inputRequest]);

  if (!inputRequest) return null;

  // Sprint 91: build input_data with approval_reason
  const handleSubmit = () => {
    let value: any;
    switch (inputRequest.input_type) {
      case 'approval':
        // F91-3: approval_reason required
        if (!approvalReason.trim()) {
          alert('请填写审批理由');
          return;
        }
        value = { approved: true, approval_reason: approvalReason.trim() };
        break;
      case 'confirmation':
        value = { confirmed: true };
        break;
      case 'input': value = textInput.trim(); break;
      case 'choice': value = choiceValue; break;
      default: value = textInput.trim();
    }
    if (value !== undefined) onSubmit(inputRequest.id, value);
  };

  const handleReject = () => {
    onReject(inputRequest.id, rejectReason || undefined);
    setShowReject(false);
  };

  const explanation = getContextExplanation(inputRequest);

  const typeLabels: Record<string, { confirm: string; reject: string }> = {
    approval: { confirm: '批准', reject: '拒绝' },
    confirmation: { confirm: '确认', reject: '否决' },
    input: { confirm: '提交', reject: '拒绝' },
    choice: { confirm: '提交', reject: '拒绝' },
  };
  const labels = typeLabels[inputRequest.input_type] || typeLabels.confirmation;

  return (
    <Sheet open={!!inputRequest} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent className="w-[520px] sm:max-w-[520px] flex flex-col overflow-y-auto">
        <SheetHeader className="pb-4 border-b">
          <div className="flex items-center justify-between pr-6">
            <div>
              <SheetTitle>人工协助请求</SheetTitle>
              <div className="flex gap-2 mt-2">
                <StatusBadge status={inputRequest.status} />
                <TypeBadge type={inputRequest.input_type} />
              </div>
            </div>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {/* What is this? */}
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-4">
              <h4 className="text-sm font-semibold text-blue-800 mb-2">📋 这是什么请求？</h4>
              <p className="text-sm text-blue-900 leading-relaxed">
                {inputRequest.description || 'Agent 需要你提供人工协助。'}
              </p>
              {inputRequest.task_id && (
                <div className="mt-2 text-xs text-blue-700 bg-blue-100 rounded px-2 py-1 inline-block font-mono">
                  关联任务: {inputRequest.task_id}
                </div>
              )}
            </CardContent>
          </Card>

          {/* F91-2: Permission info */}
          {(inputRequest as any).required_role || (inputRequest as any).assigned_to ? (
            <Card className="bg-amber-50 border-amber-200">
              <CardContent className="pt-4">
                <h4 className="text-sm font-semibold text-amber-800 mb-2">🔐 权限要求</h4>
                {(inputRequest as any).required_role && (
                  <p className="text-xs text-amber-900 mb-1">要求角色: <strong>{(inputRequest as any).required_role}</strong></p>
                )}
                {(inputRequest as any).assigned_to && (
                  <p className="text-xs text-amber-900">指定人员: <strong>{(inputRequest as any).assigned_to}</strong></p>
                )}
              </CardContent>
            </Card>
          ) : null}

          {/* Why do you need me? */}
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="pt-4">
              <h4 className="text-sm font-semibold text-amber-800 mb-2">❓ 为什么需要你？</h4>
              <p className="text-sm text-amber-900 leading-relaxed">{explanation.reason}</p>
            </CardContent>
          </Card>

          {/* What should you do? */}
          <Card className="bg-green-50 border-green-200">
            <CardContent className="pt-4">
              <h4 className="text-sm font-semibold text-green-800 mb-2">✅ 你需要做什么？</h4>
              <p className="text-sm text-green-900 leading-relaxed">{explanation.action}</p>
              <p className="text-xs text-green-700 mt-2">💡 {explanation.consequence}</p>
            </CardContent>
          </Card>

          {/* Action area */}
          {inputRequest.status === 'pending' && (
            <div className="space-y-4">
              <Separator />

              {/* Approval / Confirmation */}
              {(inputRequest.input_type === 'approval' || inputRequest.input_type === 'confirmation') && (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    {inputRequest.input_type === 'approval' ? 'Agent 正在等待你的审批决定：' : '请确认以下操作是否正确：'}
                  </p>
                  {/* F91-3: before_snapshot display */}
                  {inputRequest.context?.before_snapshot && (
                    <Card className="bg-slate-50 border-slate-200">
                      <CardContent className="pt-4">
                        <h4 className="text-xs font-semibold text-slate-700 mb-2">📸 审批前状态</h4>
                        <pre className="text-xs text-slate-600 whitespace-pre-wrap max-h-32 overflow-auto">
                          {typeof inputRequest.context.before_snapshot === 'string'
                            ? inputRequest.context.before_snapshot
                            : JSON.stringify(inputRequest.context.before_snapshot, null, 2)}
                        </pre>
                      </CardContent>
                    </Card>
                  )}
                  {/* F91-3: approval_reason input (required for approval) */}
                  {inputRequest.input_type === 'approval' && (
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-red-700">
                        审批理由 <span className="text-red-500">*必填</span>
                      </label>
                      <Textarea
                        value={approvalReason}
                        onChange={e => setApprovalReason(e.target.value)}
                        placeholder="请输入审批理由，说明通过或驳回的原因..."
                        rows={3}
                        className="border-red-200 focus:border-red-400"
                      />
                    </div>
                  )}
                  <div className="flex gap-2">
                    <Button className="flex-1" onClick={handleSubmit}>
                      <CheckCircle className="w-4 h-4 mr-1" />{labels.confirm}
                    </Button>
                    <Button variant="destructive" className="flex-1" onClick={() => setShowReject(true)}>
                      <XCircle className="w-4 h-4 mr-1" />{labels.reject}
                    </Button>
                  </div>
                </div>
              )}

              {/* Input type */}
              {inputRequest.input_type === 'input' && (
                <div className="space-y-3">
                  <label className="text-sm font-medium">请输入你希望 Agent 知道的信息：</label>
                  <Textarea
                    value={textInput}
                    onChange={e => setTextInput(e.target.value)}
                    placeholder="输入你的指令、补充信息或决策依据..."
                    rows={4}
                  />
                  <div className="flex gap-2">
                    <Button className="flex-1" disabled={!textInput.trim()} onClick={handleSubmit}>
                      提交
                    </Button>
                    <Button variant="destructive" className="flex-1" onClick={() => setShowReject(true)}>
                      <XCircle className="w-4 h-4 mr-1" />{labels.reject}
                    </Button>
                  </div>
                </div>
              )}

              {/* Choice type */}
              {inputRequest.input_type === 'choice' && inputRequest.schema?.choices && Array.isArray(inputRequest.schema.choices) && (
                <div className="space-y-3">
                  <label className="text-sm font-medium">请选择一个方案：</label>
                  <Select value={choiceValue} onValueChange={setChoiceValue}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {inputRequest.schema.choices.map((choice: string, idx: number) => (
                        <SelectItem key={idx} value={choice}>{choice}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="flex gap-2">
                    <Button className="flex-1" onClick={handleSubmit}>提交</Button>
                    <Button variant="destructive" className="flex-1" onClick={() => setShowReject(true)}>
                      <XCircle className="w-4 h-4 mr-1" />{labels.reject}
                    </Button>
                  </div>
                </div>
              )}

              {/* Unknown type */}
              {!(['approval', 'confirmation', 'input'].includes(inputRequest.input_type) ||
                 (inputRequest.input_type === 'choice' && inputRequest.schema?.choices)) && (
                <p className="text-sm text-muted-foreground text-center py-4">未知的输入类型</p>
              )}

              {/* Reject reason */}
              {showReject && (
                <Card className="bg-red-50 border-red-200">
                  <CardContent className="pt-4 space-y-3">
                    <label className="text-sm font-medium text-red-800">
                      📝 请说明拒绝原因（可选）：
                    </label>
                    <Textarea
                      value={rejectReason}
                      onChange={e => setRejectReason(e.target.value)}
                      placeholder="例如：这个决策不符合我们的安全标准..."
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <Button variant="destructive" className="flex-1" onClick={handleReject}>确认拒绝</Button>
                      <Button variant="outline" className="flex-1" onClick={() => { setShowReject(false); setRejectReason(''); }}>取消</Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Resolved state */}
          {inputRequest.status !== 'pending' && (
            <div className="space-y-3">
              <Separator />
              <h4 className="text-sm font-semibold">
                {inputRequest.status === 'submitted' ? '✅ 已批准/确认' : '❌ 已拒绝'}
              </h4>
              {inputRequest.submitted_value !== undefined && (
                <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-32">
                  {typeof inputRequest.submitted_value === 'object'
                    ? JSON.stringify(inputRequest.submitted_value, null, 2)
                    : String(inputRequest.submitted_value)}
                </pre>
              )}
            </div>
          )}

          {/* Timeline */}
          {inputRequest.history && inputRequest.history.length > 0 && (
            <div className="space-y-3">
              <Separator />
              <h4 className="text-sm font-semibold">时间线</h4>
              {inputRequest.history.map((entry, i) => (
                <Card key={i} className={
                  entry.status === 'pending' ? 'bg-yellow-50 border-yellow-200' :
                  entry.status === 'submitted' ? 'bg-blue-50 border-blue-200' :
                  entry.status === 'rejected' ? 'bg-red-50 border-red-200' :
                  'bg-muted'
                }>
                  <CardContent className="pt-4">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium">
                        {entry.status === 'pending' && '⏳ 待处理'}
                        {entry.status === 'submitted' && '✅ 已提交'}
                        {entry.status === 'rejected' && '❌ 已拒绝'}
                        {entry.status === 'expired' && '⏰ 已过期'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(entry.timestamp).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    {entry.message && <p className="text-xs text-muted-foreground mb-1">{entry.message}</p>}
                    {entry.submitted_value !== undefined && (
                      <p className="text-xs font-mono">
                        提交值: {typeof entry.submitted_value === 'object'
                          ? JSON.stringify(entry.submitted_value)
                          : String(entry.submitted_value)}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function HumanInputPage() {
  const [inputs, setInputs] = useState<HumanInputRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<HumanInputStats | null>(null);
  const [selectedInput, setSelectedInput] = useState<HumanInputRequest | null>(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  // Sprint 92 fix: 提取 loadData 到组件级别，避免循环依赖
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await humanInputApi.listPending();
      const list = Array.isArray(data) ? data : (data.requests || data.items || []);
      setInputs(list);

      const s: HumanInputStats = {
        total: list.length,
        pending: list.filter((item: HumanInputRequest) => item.status === 'pending').length,
        submitted: list.filter((item: HumanInputRequest) => item.status === 'submitted').length,
        rejected: list.filter((item: HumanInputRequest) => item.status === 'rejected').length,
        expired: list.filter((item: HumanInputRequest) => item.status === 'expired').length,
        by_type: list.reduce((acc: Record<string, number>, item: HumanInputRequest) => {
          acc[item.input_type] = (acc[item.input_type] || 0) + 1;
          return acc;
        }, {}),
      };
      setStats(s);
    } catch (err: any) {
      console.error(err);
      setInputs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSubmit = async (inputId: string, value: any) => {
    try {
      const r = await fetch(`/api/v1/human-input/${inputId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_data: value, submitted_by: 'web-user' }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || '提交失败');
      }
      showToast('✅ 输入已提交');
      loadData();
      if (selectedInput?.id === inputId) {
        const r2 = await fetch(`/api/v1/human-input/${inputId}`);
        if (r2.ok) setSelectedInput(await r2.json());
      }
    } catch (err: any) {
      showToast(`❌ ${err.message}`);
    }
  };

  const handleReject = async (inputId: string, reason?: string) => {
    try {
      const r = await fetch(`/api/v1/human-input/${inputId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason || 'Rejected by human operator' }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || '拒绝失败');
      }
      showToast('✅ 请求已拒绝');
      loadData();
      setSelectedInput(null);
    } catch (err: any) {
      showToast(`❌ ${err.message}`);
    }
  };

  const handleSelect = async (item: HumanInputRequest) => {
    try {
      const r = await fetch(`/api/v1/human-input/${item.id}`);
      if (r.ok) {
        const detail = await r.json();
        setSelectedInput(detail);
      } else {
        setSelectedInput(item);
      }
    } catch {
      setSelectedInput(item);
    }
  };

  const filtered = filterStatus === 'all' ? inputs : inputs.filter(d => d.status === filterStatus);

  return (
    <div className="w-full h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="p-4 bg-white border-b flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-900">人工协助</h1>
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="w-4 h-4 mr-1" />刷新
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Stats */}
        {stats && <StatsCards stats={stats} />}

        {/* Filter */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {[
            { key: 'all', label: '全部' },
            { key: 'pending', label: '待处理' },
            { key: 'submitted', label: '已提交' },
            { key: 'rejected', label: '已拒绝' },
            { key: 'expired', label: '已过期' },
          ].map(f => (
            <Button
              key={f.key}
              variant={filterStatus === f.key ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus(f.key)}
            >
              {f.label}
            </Button>
          ))}
        </div>

        {/* List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <p className="text-muted-foreground">暂无人工协助请求</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filtered.map(d => (
              <Card
                key={d.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => handleSelect(d)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <StatusBadge status={d.status} />
                      <TypeBadge type={d.input_type} />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {new Date(d.created_at).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-foreground mb-2 line-clamp-2">
                    {d.description}
                  </p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="font-mono">ID: {d.id.slice(0, 8)}...</span>
                    {d.task_id && <span>任务: {d.task_id}</span>}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Detail Sheet (shadcn Sheet replaces fixed div) */}
      <HumanInputDetailSheet
        inputRequest={selectedInput}
        onClose={() => setSelectedInput(null)}
        onSubmit={handleSubmit}
        onReject={handleReject}
      />

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white px-6 py-3 rounded-lg shadow-lg z-50 text-sm">
          {toast}
        </div>
      )}
    </div>
  );
}
