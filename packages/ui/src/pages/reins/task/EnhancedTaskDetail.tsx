import React, { useState, useEffect } from 'react';
import { WORKFLOWS } from '../../../shared/api/paths';
import { tasksApi, workflowsApi } from '../../../shared/utils/api';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, RefreshCw, AlertCircle, Loader2, CheckCircle, XCircle, Clock, User,
  Activity, FileText, AlertTriangle, PlayCircle, ChevronDown, ChevronUp,
  GitBranch, Zap, ArrowRight,
} from 'lucide-react';
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/shared/components/ui/card';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/shared/components/ui/tabs';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import { getAgentName } from '../../../shared/utils/agentMap';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/shared/components/ui/table';
import { Separator } from '@/shared/components/ui/separator';
import HumanInputTaskWidget from '../../../shared/components/HumanInputTaskWidget';

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  goal_id?: string;
  project_id?: string;
  assigned_agent?: string;
  result_summary?: string;
  error_type?: string;
  error_message?: string;
  blocked_reason?: string;
  retry_count?: number;
  max_retries?: number;
  dependency_ids: string[];
  verifier_agent_id?: string;
}

interface TaskActivity {
  id: string;
  task_id: string;
  old_status: string;
  new_status: string;
  reason: string;
  timestamp: string;
}

interface WorkflowStep {
  id: string;
  name: string;
  description: string;
  status: string;
  order: number;
  agent_id?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  dependencies: string[];
}

interface Workflow {
  id: string;
  name: string;
  status: string;
  steps: WorkflowStep[];
  started_at?: string;
  completed_at?: string;
}

function getTaskStatusText(status: string | undefined): string {
  if (!status) return '未知';
  const map: Record<string, string> = {
    'todo': '待办', 'pending': '待办', 'in_progress': '进行中',
    'active': '进行中', 'running': '进行中', 'completed': '已完成',
    'done': '已完成', 'failed': '失败', 'blocked': '阻塞',
    'review_needed': '待审核', 'verifying': '验证中', 'waiting_human': '等待人工',
    'disputed': '争议中',
  };
  return map[status] || status;
}

function getTaskStatusBadgeClass(status: string | undefined): string {
  if (!status) return 'bg-slate-100 text-slate-600';
  const map: Record<string, string> = {
    'todo': 'bg-slate-100 text-slate-600', 'pending': 'bg-slate-100 text-slate-600',
    'in_progress': 'bg-blue-100 text-blue-700', 'active': 'bg-blue-100 text-blue-700',
    'running': 'bg-blue-100 text-blue-700', 'completed': 'bg-green-100 text-green-700',
    'done': 'bg-green-100 text-green-700', 'failed': 'bg-red-100 text-red-700',
    'blocked': 'bg-red-100 text-red-700', 'review_needed': 'bg-orange-100 text-orange-700',
    'verifying': 'bg-amber-100 text-amber-700', 'waiting_human': 'bg-purple-100 text-purple-700',
    'disputed': 'bg-orange-100 text-orange-700',
  };
  return map[status] || 'bg-slate-100 text-slate-600';
}

const TaskDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<Task | null>(null);
  const [activities, setActivities] = useState<TaskActivity[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'activities' | 'trace' | 'human'>('details');
  const [showActivityDetail, setShowActivityDetail] = useState(false);

  async function fetchTaskDetails() {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const [taskResp, activitiesResp, workflowsResp] = await Promise.all([
        tasksApi.get(id),
        tasksApi.getActivity(id).catch(() => []),
        workflowsApi.list({ task_id: id, page_size: 10 }).catch(() => []),
      ]);
      setTask(taskResp as any as Task);
      setActivities(Array.isArray(activitiesResp) ? activitiesResp : []);
      const wfData = Array.isArray(workflowsResp) ? workflowsResp : (workflowsResp.items || []);
      setWorkflows(wfData);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) fetchTaskDetails();
  }, [id]);

  async function handleRetryTask() {
    if (!id) return;
    try {
      await tasksApi.retryTask(id);
      fetchTaskDetails();
    } catch (e) {
      console.error('重试失败', e);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="flex items-center justify-center py-20">
        <Card className="max-w-md">
          <CardContent className="p-6 text-center">
            <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-slate-800 mb-2">{error || '任务不存在'}</h2>
            <Button variant="outline" asChild><Link to="/coordination/tasks">返回列表</Link></Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isFailed = task.status === 'failed';
  const isCompleted = task.status === 'completed' || task.status === 'done';
  const isReviewNeeded = task.status === 'review_needed';
  const isWaitingHuman = task.status === 'waiting_human';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" asChild>
          <Link to="/coordination/tasks"><ArrowLeft className="w-4 h-4" /></Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="mono text-sm font-bold text-slate-500">#{String(task.id || '').slice(0, 8)}</span>
            <Badge className={getTaskStatusBadgeClass(task.status)}>{getTaskStatusText(task.status)}</Badge>
            <Badge variant="secondary">{task.priority || '普通'}</Badge>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">{task.title || '未命名任务'}</h2>
        </div>
        <div className="flex gap-2">
          {isFailed && (
            <Button size="sm" onClick={handleRetryTask}>
              <RefreshCw className="w-4 h-4" />重试
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={fetchTaskDetails}>
            <RefreshCw className="w-4 h-4" />刷新
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
        <div className="flex gap-2 border-b border-slate-200 pb-0">
          <TabsList className="bg-transparent p-0 h-auto rounded-none">
            <TabsTrigger value="details" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700">
              <FileText className="w-4 h-4" />详情
            </TabsTrigger>
            <TabsTrigger value="activities" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700">
              <Activity className="w-4 h-4" />活动历史
            </TabsTrigger>
            <TabsTrigger value="human" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700">
              <User className="w-4 h-4" />人工输入
            </TabsTrigger>
            <TabsTrigger value="trace" className="px-4 py-2 text-sm font-medium transition-colors flex items-center gap-1.5 border-b-2 -mb-px rounded-none data-[state=active]:border-blue-500 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent text-slate-500 hover:text-slate-700">
              <GitBranch className="w-4 h-4" />全链路 Trace
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="details">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>任务详情</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {task.description && (
                <div>
                  <h4 className="text-sm font-medium text-slate-500 mb-1">描述</h4>
                  <p className="text-slate-800 whitespace-pre-wrap">{task.description}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: '状态', value: getTaskStatusText(task.status) },
                  { label: '优先级', value: task.priority || '—' },
                  { label: '分配给', value: task.assigned_agent || '—' },
                  { label: '创建时间', value: new Date(task.created_at).toLocaleString('zh-CN') },
                  { label: '开始时间', value: task.started_at ? new Date(task.started_at).toLocaleString('zh-CN') : '—' },
                  { label: '完成时间', value: task.completed_at ? new Date(task.completed_at).toLocaleString('zh-CN') : '—' },
                  { label: '重试次数', value: `${task.retry_count ?? 0} / ${task.max_retries ?? 0}` },
                  { label: '类别', value: task.category || '—' },
                ].map(row => (
                  <div key={row.label}>
                    <p className="text-xs font-medium text-slate-500">{row.label}</p>
                    <p className="text-sm text-slate-800">{row.value}</p>
                  </div>
                ))}
              </div>
              {task.result_summary && (
                <div>
                  <h4 className="text-sm font-medium text-slate-500 mb-1">执行结果摘要</h4>
                  <p className="text-sm text-slate-800 bg-slate-50 rounded-sm px-3 py-2">{task.result_summary}</p>
                </div>
              )}
              {task.error_message && (
                <div className="bg-red-50 border border-red-200 rounded-sm p-3">
                  <h4 className="text-sm font-medium text-red-600 mb-1">错误信息</h4>
                  <p className="text-sm text-red-700">{task.error_message}</p>
                </div>
              )}
              {task.blocked_reason && (
                <div className="bg-amber-50 border border-amber-200 rounded-sm p-3">
                  <h4 className="text-sm font-medium text-amber-600 mb-1">阻塞原因</h4>
                  <p className="text-sm text-amber-700">{task.blocked_reason}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-6">
            {/* Quick actions */}
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">快捷操作</CardTitle></CardHeader>
              <CardContent className="space-y-2">
                {isFailed && (
                  <Button size="sm" variant="outline" className="w-full justify-start" onClick={handleRetryTask}>
                    <RefreshCw className="w-4 h-4" />重试任务
                  </Button>
                )}
                {isReviewNeeded && (
                  <Button size="sm" className="w-full justify-start bg-orange-600 hover:bg-orange-700">
                    <CheckCircle className="w-4 h-4" />审核通过
                  </Button>
                )}
                {isWaitingHuman && (
                  <Button size="sm" className="w-full justify-start bg-purple-600 hover:bg-purple-700">
                    <User className="w-4 h-4" />提供人工输入
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
        </TabsContent>

        <TabsContent value="activities">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>活动历史</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setShowActivityDetail(!showActivityDetail)}>
                {showActivityDetail ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                {showActivityDetail ? '收起详情' : '展开详情'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-lg mb-2">暂无活动记录</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>变更类型</TableHead>
                    <TableHead>状态变更</TableHead>
                    {showActivityDetail && <TableHead>原因</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activities.map((activity) => (
                    <TableRow key={activity.id}>
                      <TableCell>
                        <span className="text-sm text-slate-500">
                          {new Date(activity.timestamp).toLocaleString('zh-CN')}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{activity.reason || '状态更新'}</Badge>
                      </TableCell>
                      <TableCell>
                        {activity.old_status && activity.new_status ? (
                          <div className="flex items-center gap-2 text-sm">
                            <Badge className={getTaskStatusBadgeClass(activity.old_status)}>{getTaskStatusText(activity.old_status)}</Badge>
                            <span className="text-slate-400">→</span>
                            <Badge className={getTaskStatusBadgeClass(activity.new_status)}>{getTaskStatusText(activity.new_status)}</Badge>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </TableCell>
                      {showActivityDetail && (
                        <TableCell>
                          <span className="text-sm text-slate-600">{activity.reason || '—'}</span>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
        </TabsContent>

        <TabsContent value="human">
        <HumanInputTaskWidget taskId={task.id} />
        </TabsContent>

        <TabsContent value="trace">
        <div className="space-y-6">
          {workflows.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <GitBranch className="w-12 h-12 text-muted-foreground mb-3" />
                <p className="text-lg text-muted-foreground mb-1">暂无关联工作流</p>
                <p className="text-sm text-muted-foreground">此任务未关联到任何工作流</p>
              </CardContent>
            </Card>
          ) : (
            workflows.map((wf) => (
              <Card key={wf.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-blue-500" />
                      <CardTitle className="text-base">{wf.name || '未命名工作流'}</CardTitle>
                      <Badge variant="secondary">{wf.status}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {wf.started_at ? new Date(wf.started_at).toLocaleString('zh-CN') : '—'}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {wf.steps && wf.steps.length > 0 ? (
                    <div className="space-y-2">
                      {/* Chain header */}
                      <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                        <span>执行链路</span>
                        <span className="ml-auto">{wf.steps.filter((s) => s.status === 'completed' || s.status === 'done').length} / {wf.steps.length} 步骤完成</span>
                      </div>
                      {/* Step chain */}
                      <div className="flex items-center gap-0 overflow-x-auto pb-2">
                        {wf.steps
                          .slice()
                          .sort((a, b) => (a.order || 0) - (b.order || 0))
                          .map((step, i) => {
                            const isLast = i === wf.steps.length - 1;
                            const stepDone = step.status === 'completed' || step.status === 'done';
                            const stepRunning = step.status === 'in_progress' || step.status === 'running';
                            const stepFailed = step.status === 'failed';
                            return (
                              <div key={step.id} className="flex items-center">
                                <div className={`flex flex-col items-center p-3 rounded-lg border-2 min-w-[160px] ${
                                  stepDone ? 'bg-green-50 border-green-200' :
                                  stepRunning ? 'bg-blue-50 border-blue-300' :
                                  stepFailed ? 'bg-red-50 border-red-300' :
                                  'bg-slate-50 border-slate-200'
                                }`}>
                                  <Badge variant="secondary" className={`text-xs mb-2 ${
                                    stepDone ? 'bg-green-100 text-green-700' :
                                    stepRunning ? 'bg-blue-100 text-blue-700' :
                                    stepFailed ? 'bg-red-100 text-red-700' : ''
                                  }`}>
                                    {step.status}
                                  </Badge>
                                  <p className="text-sm font-medium text-center leading-tight mb-1">{step.name}</p>
                                  {step.agent_id && (
                                    <p className="text-xs text-muted-foreground">@{getAgentName(step.agent_id)}</p>
                                  )}
                                  {step.started_at && (
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {new Date(step.started_at).toLocaleTimeString('zh-CN')}
                                    </p>
                                  )}
                                </div>
                                {!isLast && (
                                  <ArrowRight className={`w-5 h-5 mx-1 flex-shrink-0 ${
                                    stepDone ? 'text-green-400' : 'text-muted-foreground'
                                  }`} />
                                )}
                              </div>
                            );
                          })}
                      </div>
                      {/* Step detail table */}
                      <Separator className="my-4" />
                      <p className="text-xs text-muted-foreground mb-2">步骤详情</p>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>步骤</TableHead>
                            <TableHead>状态</TableHead>
                            <TableHead>Agent</TableHead>
                            <TableHead>开始</TableHead>
                            <TableHead>完成</TableHead>
                            <TableHead>错误</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {wf.steps
                            .slice()
                            .sort((a, b) => (a.order || 0) - (b.order || 0))
                            .map((step) => (
                              <TableRow key={step.id} className={step.status === 'failed' ? 'bg-red-50' : step.status === 'in_progress' ? 'bg-blue-50' : ''}>
                                <TableCell className="text-sm font-medium max-w-[200px] truncate">{step.name}</TableCell>
                                <TableCell><Badge variant="secondary">{step.status}</Badge></TableCell>
                                <TableCell className="text-sm text-muted-foreground">{step.agent_id ? getAgentName(step.agent_id) : '—'}</TableCell>
                                <TableCell className="text-sm text-muted-foreground">{step.started_at ? new Date(step.started_at).toLocaleString('zh-CN') : '—'}</TableCell>
                                <TableCell className="text-sm text-muted-foreground">{step.completed_at ? new Date(step.completed_at).toLocaleString('zh-CN') : '—'}</TableCell>
                                <TableCell className="text-sm text-red-600 max-w-[150px] truncate">{step.error || '—'}</TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-6">此工作流暂无步骤数据</p>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
        </TabsContent>
      </Tabs>

    </div>
  );
};

export default TaskDetailPage;
