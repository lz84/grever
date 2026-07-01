import React, { useState, useEffect } from 'react';
import { humanInputApi } from '../../../shared/utils/api';
import { Link } from 'react-router-dom';
import { User, Clock, CheckCircle, XCircle, Loader2, RefreshCw, BookOpen, ArrowRight, AlertTriangle } from 'lucide-react';
import { Button } from "@/shared/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card";
import { Badge } from "@/shared/components/ui/badge";
import { Input } from "@/shared/components/ui/input";

// Types
interface HumanInputRequest {
  id: string;
  task_id: string;
  title: string;
  description: string;
  input_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  submitted_by?: string;
  submitted_at?: string;
  context?: any;
  timeout_minutes?: number;  // Sprint 92 F92-4
}

interface Stats {
  total: number;
  pending: number;
  submitted: number;
  rejected: number;
  expired: number;
}

// Stats cards component
function StatsCards({ stats }: { stats: Stats }) {
  const cards = [
    { label: '总计', value: stats.total, icon: User, color: 'text-gray-600' },
    { label: '待处理', value: stats.pending, icon: Clock, color: 'text-yellow-600' },
    { label: '已提交', value: stats.submitted, icon: CheckCircle, color: 'text-blue-600' },
    { label: '已拒绝', value: stats.rejected, icon: XCircle, color: 'text-red-600' },
    { label: '已过期', value: stats.expired, icon: Clock, color: 'text-gray-500' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {cards.map((card, index) => (
        <Card key={index}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.label}</CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Recent requests component
function RecentRequests({ requests, loading }: { requests: HumanInputRequest[]; loading: boolean }) {
  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: string; label: string }> = {
      pending: { variant: "secondary", label: '待处理' },
      submitted: { variant: "default", label: '已提交' },
      rejected: { variant: "destructive", label: '已拒绝' },
      expired: { variant: "outline", label: '已过期' },
    };
    const c = config[status] || { variant: "outline", label: status };
    return <Badge variant={c.variant as any}>{c.label}</Badge>;
  };

  // Sprint 92 F92-4: 超时检测
  function isTimedOut(req: HumanInputRequest): boolean {
    if (req.status !== 'pending' || !req.timeout_minutes) return false;
    const created = new Date(req.created_at).getTime();
    const deadline = created + req.timeout_minutes * 60 * 1000;
    return Date.now() > deadline;
  }

  const getTypeBadge = (type: string) => {
    const typeConfig: Record<string, string> = {
      approval: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
      confirmation: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
      input: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
      choice: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
    };
    const colors = typeConfig[type] || 'bg-gray-100 text-gray-700';
    const labels: Record<string, string> = {
      approval: '审批',
      confirmation: '确认',
      input: '输入',
      choice: '选择',
    };
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${colors}`}>
        {labels[type] || type}
      </span>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>近期请求</CardTitle>
        <CardDescription>最新的人工输入请求</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {requests.slice(0, 5).map(request => (
          <div key={request.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                {getStatusBadge(request.status)}
                {getTypeBadge(request.input_type)}
                {isTimedOut(request) && (
                  <Badge variant="destructive" className="text-xs gap-1">
                    <AlertTriangle className="w-3 h-3" />超时
                  </Badge>
                )}
              </div>
              <p className="text-sm font-medium truncate">{request.title}</p>
              <p className="text-xs text-muted-foreground truncate">{request.description}</p>
            </div>
            <div className="text-right text-xs text-muted-foreground ml-4">
              <div>{new Date(request.created_at).toLocaleDateString('zh-CN')}</div>
              <div className="font-mono">{request.id.substring(0, 8)}...</div>
            </div>
          </div>
        ))}
        {requests.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">暂无请求</div>
        )}
      </CardContent>
    </Card>
  );
}

// Main dashboard component
export default function HumanInputDashboard() {
  const [requests, setRequests] = useState<HumanInputRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Stats>({
    total: 0,
    pending: 0,
    submitted: 0,
    rejected: 0,
    expired: 0
  });

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const data = await humanInputApi.listPending();
      const requestsList = Array.isArray(data) ? data : data.requests || [];
      
      setRequests(requestsList);
      
      // Calculate stats
      const calculatedStats = requestsList.reduce(
        (acc: { total: number; pending: number; submitted: number; rejected: number; expired: number }, req: { status: string }) => {
          acc.total++;
          if (req.status === 'pending') acc.pending++;
          else if (req.status === 'submitted') acc.submitted++;
          else if (req.status === 'rejected') acc.rejected++;
          else if (req.status === 'expired') acc.expired++;
          return acc;
        },
        { total: 0, pending: 0, submitted: 0, rejected: 0, expired: 0 }
      );
      
      setStats(calculatedStats);
    } catch (error) {
      console.error('Error fetching human input requests:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <User className="h-8 w-8" />
            人类输入管理
          </h1>
          <p className="text-muted-foreground mt-1">
            管理和处理需要人类干预的任务请求
          </p>
        </div>
        <Button variant="outline" onClick={fetchRequests} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          刷新数据
        </Button>
      </div>

      {/* Stats */}
      <StatsCards stats={stats} />

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent requests */}
        <div className="lg:col-span-2">
          <RecentRequests requests={requests} loading={loading} />
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Info panel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                关于人类输入
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                人类输入功能允许系统在需要人类决策、确认或输入时暂停执行流程。
              </p>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">审批</Badge>
                  <span className="text-muted-foreground">需要人工批准的请求</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">确认</Badge>
                  <span className="text-muted-foreground">需要人工确认的操作</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">输入</Badge>
                  <span className="text-muted-foreground">需要用户提供信息的请求</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">选择</Badge>
                  <span className="text-muted-foreground">需要人工做出选择的请求</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick actions */}
          <Card>
            <CardHeader>
              <CardTitle>快速操作</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/human-input">
                  <ArrowRight className="mr-2 h-4 w-4" />
                  处理待办事项
                </Link>
              </Button>
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/coordination/tasks">
                  <ArrowRight className="mr-2 h-4 w-4" />
                  查看任务
                </Link>
              </Button>
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/coordination/goals">
                  <ArrowRight className="mr-2 h-4 w-4" />
                  查看目标
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
