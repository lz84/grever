import React, { useState, useEffect } from 'react';
import { disputesApi, Dispute } from '@/shared/utils/api';
import { Button } from '@/shared/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Input } from '@/shared/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select';
import { Checkbox } from '@/shared/components/ui/checkbox';
import { Search, RefreshCw, BarChart3, AlertTriangle, Clock, CheckCircle, Gavel, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { DisputeDetailSheet } from './DisputeDetailSheet';

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

// ==================== Stats Card ====================

interface DisputeStats {
  total: number;
  open: number;
  active: number;
  arbitrating: number;
  resolved: number;
  dismissed: number;
  escalated: number;
  byType: Record<string, number>;
  recentResolved: Dispute[];
}

function DisputeStatsCards({ stats }: { stats: DisputeStats | null }) {
  if (!stats) return null;

  const statItems = [
    { label: '总计', value: stats.total, icon: BarChart3, color: 'text-slate-600' },
    { label: '待处理', value: stats.open, icon: AlertTriangle, color: 'text-amber-600' },
    { label: '处理中', value: stats.active, icon: Clock, color: 'text-blue-600' },
    { label: '仲裁中', value: stats.arbitrating, icon: Gavel, color: 'text-purple-600' },
    { label: '已解决', value: stats.resolved, icon: CheckCircle, color: 'text-green-600' },
  ];

  return (
    <div className="grid grid-cols-5 gap-3 mb-4">
      {statItems.map(({ label, value, icon: Icon, color }) => (
        <Card key={label} className="border-slate-200">
          <CardContent className="p-3 flex items-center gap-3">
            <Icon className={`w-5 h-5 ${color}`} />
            <div>
              <div className="text-xl font-bold">{value}</div>
              <div className="text-xs text-muted-foreground">{label}</div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ==================== Disputes Tab ====================

export function DisputesTab() {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [stats, setStats] = useState<DisputeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDisputes, setSelectedDisputes] = useState<Set<string>>(new Set());
  const [detailDispute, setDetailDispute] = useState<Dispute | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [sortField, setSortField] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [disputeList, statsData] = await Promise.all([
        disputesApi.list(filterStatus !== 'all' ? filterStatus : undefined),
        disputesApi.getStats(),
      ]);
      setDisputes(disputeList || []);
      setStats(statsData || null);
    } catch (error) {
      console.error('获取争议数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterStatus]);

  // Filter + sort locally
  let filtered = disputes;
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (d) =>
        d.description?.toLowerCase().includes(q) ||
        d.dispute_type?.toLowerCase().includes(q) ||
        d.status?.toLowerCase().includes(q) ||
        d.id?.toLowerCase().includes(q)
    );
  }
  filtered = [...filtered].sort((a, b) => {
    const aVal = (a as any)[sortField] || '';
    const bVal = (b as any)[sortField] || '';
    const cmp = String(aVal).localeCompare(String(bVal));
    return sortOrder === 'desc' ? -cmp : cmp;
  });

  const handleSelect = (id: string) => {
    const next = new Set(selectedDisputes);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedDisputes(next);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) setSelectedDisputes(new Set(filtered.map((d) => d.id)));
    else setSelectedDisputes(new Set());
  };

  const handleRowClick = (dispute: Dispute) => {
    setDetailDispute(dispute);
    setDetailOpen(true);
  };

  return (
    <div className="space-y-4">
      <DisputeStatsCards stats={stats} />

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-64 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索争议描述、类型、ID..."
            className="pl-10"
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="open">待处理</SelectItem>
            <SelectItem value="active">处理中</SelectItem>
            <SelectItem value="arbitrating">仲裁中</SelectItem>
            <SelectItem value="resolved">已解决</SelectItem>
            <SelectItem value="dismissed">已驳回</SelectItem>
            <SelectItem value="escalated">已升级</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sortField} onValueChange={setSortField}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="created_at">创建时间</SelectItem>
            <SelectItem value="updated_at">更新时间</SelectItem>
            <SelectItem value="status">状态</SelectItem>
            <SelectItem value="dispute_type">类型</SelectItem>
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
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="w-4 h-4" />
          刷新
        </Button>
      </div>

      {/* Selected actions */}
      {selectedDisputes.size > 0 && (
        <div className="p-3 bg-blue-50 border rounded flex justify-between items-center">
          <span className="text-sm text-blue-700">已选择 {selectedDisputes.size} 项</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setDetailOpen(true)}>
              批量查看
            </Button>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12">
          <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">暂无争议</p>
          <p className="text-sm text-slate-400 mt-1">切换筛选条件或刷新试试</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border">
          {/* Header */}
          <div className="grid grid-cols-12 gap-2 p-3 border-b text-sm font-medium text-muted-foreground bg-slate-50">
            <div className="col-span-1 flex items-center">
              <Checkbox
                checked={selectedDisputes.size === filtered.length && filtered.length > 0}
                onCheckedChange={handleSelectAll}
              />
            </div>
            <div className="col-span-1">ID</div>
            <div className="col-span-4">描述</div>
            <div className="col-span-2">类型</div>
            <div className="col-span-1">状态</div>
            <div className="col-span-2">关联任务</div>
            <div className="col-span-1">时间</div>
          </div>

          {/* Rows */}
          <div className="divide-y">
            {filtered.map((d) => (
              <div
                key={d.id}
                className="grid grid-cols-12 gap-2 p-3 hover:bg-slate-50 cursor-pointer items-center"
                onClick={() => handleRowClick(d)}
              >
                <div className="col-span-1" onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selectedDisputes.has(d.id)}
                    onCheckedChange={() => handleSelect(d.id)}
                  />
                </div>
                <div className="col-span-1">
                  <span className="font-mono text-xs text-slate-500">{d.id.substring(0, 8)}</span>
                </div>
                <div className="col-span-4">
                  <p className="text-sm font-medium truncate">{d.description}</p>
                </div>
                <div className="col-span-2">
                  {d.dispute_type ? getTypeBadge(d.dispute_type) : '-'}
                </div>
                <div className="col-span-1">
                  {getStatusBadge(d.status || '')}
                </div>
                <div className="col-span-2">
                  {d.related_task_id ? (
                    <Link
                      to={`/coordination/tasks/${d.related_task_id}`}
                      className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {d.related_task_id.substring(0, 12)}...
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  ) : (
                    <span className="text-xs text-slate-400">-</span>
                  )}
                </div>
                <div className="col-span-1">
                  <span className="text-xs text-slate-400">
                    {new Date(d.created_at).toLocaleDateString('zh-CN')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detail Sheet */}
      <DisputeDetailSheet
        dispute={detailDispute}
        isOpen={detailOpen}
        onClose={() => { setDetailOpen(false); setDetailDispute(null); }}
        onRefresh={fetchData}
      />
    </div>
  );
}
