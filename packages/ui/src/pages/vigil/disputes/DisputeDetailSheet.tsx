import React, { useState, useEffect } from 'react';
import { disputesApi, Dispute } from '@/shared/utils/api';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/shared/components/ui/sheet';
import { Button } from '@/shared/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/ui/tabs';
import { Textarea } from '@/shared/components/ui/textarea';
import { Input } from '@/shared/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';
import { ExternalLink, Clock, MessageSquare, Gavel, RefreshCw, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

// ==================== Badge helpers ====================

function getStatusBadge(status: string) {
  const config: Record<string, { variant: string; label: string }> = {
    open: { variant: 'warning', label: '待处理' },
    active: { variant: 'warning', label: '处理中' },
    arbitrating: { variant: 'info', label: '仲裁中' },
    resolved: { variant: 'success', label: '已解决' },
    dismissed: { variant: 'secondary', label: '已驳回' },
    escalated: { variant: 'destructive', label: '已升级' },
  };
  const c = config[status] || { variant: 'secondary', label: status };
  return <Badge variant={c.variant as any}>{c.label}</Badge>;
}

function getTypeBadge(type: string) {
  const config: Record<string, { variant: string; label: string }> = {
    conflicting_results: { variant: 'warning', label: '结果冲突' },
    timeout: { variant: 'destructive', label: '超时争议' },
    quality_dispute: { variant: 'info', label: '质量争议' },
    resource_conflict: { variant: 'secondary', label: '资源冲突' },
    priority_conflict: { variant: 'warning', label: '优先级冲突' },
    rule_violation: { variant: 'destructive', label: '规则违反' },
  };
  const c = config[type] || { variant: 'secondary', label: type };
  return <Badge variant={c.variant as any}>{c.label}</Badge>;
}

// ==================== Arbitrate Dialog ====================

interface ArbitrateDialogProps {
  dispute: Dispute | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

function ArbitrateDialog({ dispute, isOpen, onClose, onSuccess }: ArbitrateDialogProps) {
  const [decision, setDecision] = useState('');
  const [reason, setReason] = useState('');
  const [arbitrator, setArbitrator] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setDecision('');
      setReason('');
      setArbitrator('');
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!dispute || !decision) return;
    setLoading(true);
    try {
      await disputesApi.arbitrate(dispute.id, {
        decision,
        reason: reason || undefined,
        arbitrator: arbitrator || undefined,
      });
      onSuccess();
      onClose();
    } catch (error) {
      console.error('仲裁失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Gavel className="w-5 h-5" />
            仲裁争议
          </DialogTitle>
          <DialogDescription>
            {dispute?.description}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">仲裁决定 *</label>
            <Textarea
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              rows={3}
              placeholder="请输入仲裁决定..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">仲裁理由</label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="请输入仲裁理由..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">仲裁人</label>
            <Input
              value={arbitrator}
              onChange={(e) => setArbitrator(e.target.value)}
              placeholder="仲裁人名称..."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>取消</Button>
          <Button onClick={handleSubmit} disabled={loading || !decision}>
            {loading ? '提交中...' : '提交仲裁'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Discuss Dialog ====================

interface DiscussDialogProps {
  dispute: Dispute | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

function DiscussDialog({ dispute, isOpen, onClose, onSuccess }: DiscussDialogProps) {
  const [message, setMessage] = useState('');
  const [author, setAuthor] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setMessage('');
      setAuthor('');
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispute || !message) return;
    setLoading(true);
    try {
      await disputesApi.discuss(dispute.id, {
        message,
        author: author || undefined,
      });
      setMessage('');
      onSuccess();
    } catch (error) {
      console.error('讨论提交失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            参与讨论
          </DialogTitle>
          <DialogDescription>
            {dispute?.description}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">讨论内容 *</label>
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              placeholder="请输入你的观点..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">署名</label>
            <Input
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="你的名字..."
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={onClose} disabled={loading}>取消</Button>
            <Button type="submit" disabled={loading || !message}>
              <Send className="w-4 h-4 mr-1" />
              {loading ? '提交中...' : '提交'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Status Update Dialog ====================

interface StatusUpdateDialogProps {
  dispute: Dispute | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

function StatusUpdateDialog({ dispute, isOpen, onClose, onSuccess }: StatusUpdateDialogProps) {
  const [newStatus, setNewStatus] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) setNewStatus('');
  }, [isOpen]);

  const handleSubmit = async () => {
    if (!dispute || !newStatus) return;
    setLoading(true);
    try {
      await disputesApi.updateStatus(dispute.id, newStatus);
      onSuccess();
      onClose();
    } catch (error) {
      console.error('状态更新失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>更新状态</DialogTitle>
          <DialogDescription>
            当前状态: {dispute?.status}
          </DialogDescription>
        </DialogHeader>
        <Select value={newStatus} onValueChange={setNewStatus}>
          <SelectTrigger>
            <SelectValue placeholder="选择新状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="open">待处理</SelectItem>
            <SelectItem value="active">处理中</SelectItem>
            <SelectItem value="arbitrating">仲裁中</SelectItem>
            <SelectItem value="resolved">已解决</SelectItem>
            <SelectItem value="dismissed">已驳回</SelectItem>
            <SelectItem value="escalated">已升级</SelectItem>
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>取消</Button>
          <Button onClick={handleSubmit} disabled={loading || !newStatus}>
            {loading ? '更新中...' : '确认更新'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Timeline Component ====================

interface TimelineProps {
  disputeId: string;
  loading: boolean;
}

function Timeline({ disputeId, loading }: TimelineProps) {
  const [timeline, setTimeline] = useState<any[]>([]);
  const [fetching, setFetching] = useState(false);

  const fetchTimeline = async () => {
    setFetching(true);
    try {
      const data = await disputesApi.getTimeline(disputeId);
      setTimeline(data || []);
    } catch (error) {
      console.error('获取时间线失败:', error);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (disputeId) fetchTimeline();
  }, [disputeId]);

  if (fetching || loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (timeline.length === 0) {
    return (
      <div className="text-center py-6 text-muted-foreground text-sm">
        <Clock className="w-8 h-8 mx-auto mb-2 text-slate-300" />
        <p>暂无时间线记录</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-h-96 overflow-y-auto">
      {timeline.map((event: any, idx: number) => (
        <div key={idx} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-2.5 h-2.5 rounded-full bg-blue-500 mt-1.5" />
            {idx < timeline.length - 1 && (
              <div className="w-0.5 flex-1 bg-slate-200 mt-1" />
            )}
          </div>
          <div className="pb-4 flex-1">
            <div className="flex justify-between items-start">
              <p className="text-sm font-medium">{event.event || event.type || event.action || '事件'}</p>
              <span className="text-xs text-muted-foreground">
                {event.timestamp || event.created_at ? new Date(event.timestamp || event.created_at).toLocaleString('zh-CN') : ''}
              </span>
            </div>
            {event.description || event.message || event.details ? (
              <p className="text-sm text-muted-foreground mt-0.5">
                {event.description || event.message || event.details}
              </p>
            ) : null}
            {event.actor || event.author || event.by ? (
              <p className="text-xs text-slate-400 mt-1">
                操作者: {event.actor || event.author || event.by}
              </p>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

// ==================== Discussion Messages Component ====================

interface DiscussionMessagesProps {
  disputeId: string;
  loading: boolean;
}

function DiscussionMessages({ disputeId, loading }: DiscussionMessagesProps) {
  const [messages, setMessages] = useState<any[]>([]);
  const [fetching, setFetching] = useState(false);

  const fetchMessages = async () => {
    setFetching(true);
    try {
      const data = await disputesApi.getDetail(disputeId);
      setMessages(data?.messages || data?.discussions || data?.comments || []);
    } catch (error) {
      console.error('获取讨论失败:', error);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (disputeId) fetchMessages();
  }, [disputeId]);

  if (fetching || loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="text-center py-6 text-muted-foreground text-sm">
        <MessageSquare className="w-8 h-8 mx-auto mb-2 text-slate-300" />
        <p>暂无讨论</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {messages.map((msg: any, idx: number) => (
        <Card key={idx} className="border-slate-200">
          <CardContent className="p-3">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium">{msg.author || msg.user || '匿名'}</span>
              <span className="text-xs text-muted-foreground">
                {msg.created_at ? new Date(msg.created_at).toLocaleString('zh-CN') : ''}
              </span>
            </div>
            <p className="text-sm text-slate-700 mt-1">{msg.message || msg.content || msg.text}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ==================== Main Detail Sheet ====================

interface DisputeDetailSheetProps {
  dispute: Dispute | null;
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

export function DisputeDetailSheet({ dispute, isOpen, onClose, onRefresh }: DisputeDetailSheetProps) {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Sub-dialogs
  const [arbitrateOpen, setArbitrateOpen] = useState(false);
  const [discussOpen, setDiscussOpen] = useState(false);
  const [statusUpdateOpen, setStatusUpdateOpen] = useState(false);
  const [actionDispute, setActionDispute] = useState<Dispute | null>(null);

  const fetchDetail = async () => {
    if (!dispute?.id) return;
    setLoading(true);
    try {
      const data = await disputesApi.getDetail(dispute.id);
      setDetail(data);
    } catch (error) {
      console.error('获取争议详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && dispute?.id) {
      fetchDetail();
      setActiveTab('overview');
    }
  }, [isOpen, dispute?.id]);

  const handleActionSuccess = () => {
    fetchDetail();
    onRefresh();
  };

  if (!dispute) return null;

  const d = detail || dispute;

  return (
    <>
      <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
        <SheetContent className="w-[500px] sm:max-w-[500px] overflow-y-auto">
          <SheetHeader className="mb-2">
            <SheetTitle className="text-base">{dispute.description?.substring(0, 50)}{dispute.description?.length > 50 ? '...' : ''}</SheetTitle>
            <SheetDescription>
              <div className="flex gap-2 mt-1">
                {getTypeBadge(dispute.dispute_type || '')}
                {getStatusBadge(dispute.status || '')}
              </div>
            </SheetDescription>
          </SheetHeader>

          <div className="flex gap-2 mb-4">
            <Button size="sm" className="flex-1" variant="outline" onClick={() => { setActionDispute(dispute); setArbitrateOpen(true); }}>
              <Gavel className="w-4 h-4 mr-1" /> 仲裁
            </Button>
            <Button size="sm" className="flex-1" variant="outline" onClick={() => { setActionDispute(dispute); setDiscussOpen(true); }}>
              <MessageSquare className="w-4 h-4 mr-1" /> 讨论
            </Button>
            <Button size="sm" className="flex-1" variant="outline" onClick={() => { setActionDispute(dispute); setStatusUpdateOpen(true); }}>
              更新状态
            </Button>
            <Button size="sm" variant="ghost" onClick={fetchDetail}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full">
              <TabsTrigger value="overview" className="flex-1">概览</TabsTrigger>
              <TabsTrigger value="timeline" className="flex-1">时间线</TabsTrigger>
              <TabsTrigger value="discussion" className="flex-1">讨论</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4 mt-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">基本信息</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">ID</span>
                    <span className="font-mono text-slate-900">{dispute.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">类型</span>
                    {getTypeBadge(dispute.dispute_type || '')}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">状态</span>
                    {getStatusBadge(dispute.status || '')}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">创建时间</span>
                    <span>{new Date(dispute.created_at).toLocaleString('zh-CN')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">更新时间</span>
                    <span>{dispute.updated_at ? new Date(dispute.updated_at).toLocaleString('zh-CN') : '-'}</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">描述</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{dispute.description}</p>
                </CardContent>
              </Card>

              {d.resolution && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">解决方案</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-700">{d.resolution}</p>
                  </CardContent>
                </Card>
              )}

              {d.involved_agents && d.involved_agents.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">涉及 Agent</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {d.involved_agents.map((agent: string, i: number) => (
                        <Badge key={i} variant="outline">{agent}</Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {dispute.related_task_id && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">关联任务</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Link
                      to={`/coordination/tasks/${dispute.related_task_id}`}
                      className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                    >
                      {dispute.related_task_id}
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </CardContent>
                </Card>
              )}

              {d.resolution_details && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">解决详情</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-700">{d.resolution_details}</p>
                  </CardContent>
                </Card>
              )}

              {/* Fallback: show raw detail data if available */}
              {detail && Object.keys(detail).length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">完整详情</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-slate-100 p-3 rounded overflow-x-auto whitespace-pre-wrap break-all">
                      {JSON.stringify(detail, null, 2)}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="timeline" className="mt-4">
              <Timeline disputeId={dispute.id} loading={loading} />
            </TabsContent>

            <TabsContent value="discussion" className="mt-4">
              <DiscussionMessages disputeId={dispute.id} loading={loading} />
            </TabsContent>
          </Tabs>
        </SheetContent>
      </Sheet>

      <ArbitrateDialog
        dispute={actionDispute}
        isOpen={arbitrateOpen}
        onClose={() => setArbitrateOpen(false)}
        onSuccess={handleActionSuccess}
      />
      <DiscussDialog
        dispute={actionDispute}
        isOpen={discussOpen}
        onClose={() => setDiscussOpen(false)}
        onSuccess={handleActionSuccess}
      />
      <StatusUpdateDialog
        dispute={actionDispute}
        isOpen={statusUpdateOpen}
        onClose={() => setStatusUpdateOpen(false)}
        onSuccess={handleActionSuccess}
      />
    </>
  );
}

export { ArbitrateDialog, DiscussDialog, StatusUpdateDialog };
