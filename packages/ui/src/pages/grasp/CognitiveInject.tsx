import { useState, useEffect } from 'react';
import { GRASP } from '../../shared/api/paths';
import { Zap, ChevronLeft, ChevronRight } from 'lucide-react';
import { Pagination } from '@/shared/components/ui/pagination';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Button } from '@/shared/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table';

interface InjectLog {
  id: string
  source: 'task' | 'workflow' | 'dispute'
  type: string
  cognition_count: number
  status: 'success' | 'failed'
  error_message?: string
  created_at: string
}

interface InjectRule {
  id: string
  name: string
  trigger_condition: string
  target_kb: string
  enabled: boolean
  created_at: string
}

const SOURCE_LABELS: Record<string, string> = {
  task: '任务完成',
  workflow: '工作流完成',
  dispute: '争议解决',
}

const TYPE_LABELS: Record<string, string> = {
  task_result: 'task_result',
  workflow_result: 'workflow_result',
  dispute_result: 'dispute_result',
}

export default function CognitiveInject() {
  const [logs, setLogs] = useState<InjectLog[]>([])
  const [rules, setRules] = useState<InjectRule[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null)
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const ITEMS_PER_PAGE = 10;

  useEffect(() => {
    const loadLogs = async () => {
      setLoading(true);
      try {
        const res = await fetch(GRASP.INJECT_RULES + `/logs?page=${currentPage}&page_size=${ITEMS_PER_PAGE}`);
        if (res.ok) {
          const data = await res.json();
          setLogs(data.logs || []);
          setTotalLogs(data.total || data.logs?.length || 0);
        } else {
          console.error('Failed to load injection logs');
          setLogs([]);
          setTotalLogs(0);
        }
      } catch (err) {
        console.error('Failed to load injection logs:', err);
        setLogs([]);
        setTotalLogs(0);
      } finally {
        setLoading(false);
      }
    };

    const loadRules = async () => {
      try {
        const res = await fetch(GRASP.INJECT_RULES);
        if (res.ok) {
          const data = await res.json();
          setRules(data.rules || []);
        } else {
          console.error('Failed to load injection rules');
          setRules([]);
        }
      } catch (err) {
        console.error('Failed to load injection rules:', err);
        setRules([]);
      }
    };

    loadLogs();
    loadRules();
  }, [currentPage]);

  const toggleRule = (ruleId: string) => {
    setRules(prev => prev.map(r => {
      if (r.id === ruleId) return { ...r, enabled: !r.enabled };
      return r;
    }));
  };

  function formatTime(dateStr: string): string {
    return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Zap className="w-8 h-8 text-primary animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载中...</p>
        </div>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(totalLogs / ITEMS_PER_PAGE));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Zap className="w-5 h-5 text-muted-foreground" />
            数据导入
          </h1>
          <p className="text-sm text-muted-foreground mt-1">将外部数据和知识导入认知系统</p>
          <p className="text-xs text-muted-foreground mt-1">支持任务结果，工作流输出和争议解决方案的自动注入</p>
        </div>
      </div>

      {/* Injection History */}
      <Card>
        <CardHeader>
          <CardTitle>注入历史</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {logs.length === 0 ? (
            <div className="p-8 text-center">
              <Zap className="w-12 h-12 mx-auto text-muted-foreground mb-3 opacity-50" />
              <p className="text-muted-foreground mb-4">暂无注入记录</p>
              <Button>导入数据</Button>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>来源</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>认知数</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map(log => (
                    <>
                      <TableRow
                        key={log.id}
                        className="cursor-pointer"
                        onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                      >
                        <TableCell className="text-muted-foreground">{formatTime(log.created_at)}</TableCell>
                        <TableCell>{SOURCE_LABELS[log.source]}</TableCell>
                        <TableCell className="text-muted-foreground">{TYPE_LABELS[log.type]}</TableCell>
                        <TableCell>{log.cognition_count}</TableCell>
                        <TableCell>
                          <Badge variant={log.status === 'success' ? 'success' : 'destructive'}>
                            {log.status === 'success' ? '✅ 成功' : '❌ 失败'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                      {expandedLogId === log.id && log.error_message && (
                        <TableRow key={`${log.id}-detail`}>
                          <TableCell colSpan={5} className="bg-destructive/10 text-destructive text-xs">
                            错误信息：{log.error_message}
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  ))}
                </TableBody>
              </Table>
              {totalPages > 1 && (
                <div className="border-t p-4">
                  <Pagination 
                    currentPage={currentPage} 
                    totalPages={totalPages} 
                    onPageChange={setCurrentPage} 
                  />
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Injection Rules */}
      <Card>
        <CardHeader>
          <CardTitle>注入规则</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {rules.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>暂无注入规则</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>规则名称</TableHead>
                  <TableHead>触发条件</TableHead>
                  <TableHead>目标知识库</TableHead>
                  <TableHead>开关</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map(rule => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell className="text-muted-foreground">{rule.trigger_condition}</TableCell>
                    <TableCell className="text-muted-foreground">{rule.target_kb}</TableCell>
                    <TableCell>
                      <button
                        onClick={() => toggleRule(rule.id)}
                        className={`w-10 h-5 rounded-full transition-colors relative ${rule.enabled ? 'bg-primary' : 'bg-muted'}`}
                      >
                        <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${rule.enabled ? 'left-5' : 'left-0.5'}`} />
                      </button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
