import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Clock, AlertTriangle, Loader2, FileText } from 'lucide-react';
import { tracesApi } from '../../../shared/utils/api';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog';

interface ExecutionReportModalProps {
  isOpen: boolean
  onClose: () => void
  traceId: string | null
}

interface TraceStep {
  type?: string;
  success?: boolean;
  duration_ms?: number;
  name?: string;
  error?: string;
}

interface TraceData {
  id?: string;
  success?: boolean;
  duration_ms?: number;
  steps?: TraceStep[];
  goal_id?: string;
  project_id?: string;
  task_id?: string;
  agent_id?: string;
}

export default function ExecutionReportModal({ isOpen, onClose, traceId }: ExecutionReportModalProps) {
  const [trace, setTrace] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && traceId) {
      fetchTraceDetail();
    }
  }, [isOpen, traceId]);

  async function fetchTraceDetail() {
    if (!traceId) return;
    
    try {
      setLoading(true);
      setError(null);
      const result = await tracesApi.get(traceId);
      setTrace(result as TraceData);
    } catch (err: any) {
      setError(err.message || '加载执行报告失败');
    } finally {
      setLoading(false);
    }
  }

  function formatDuration(ms?: number): string {
    if (!ms) return '--';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}min`;
  }

  const getStatusIcon = (success?: boolean) => {
    if (success === true) return <CheckCircle className="w-5 h-5 text-green-500" />;
    if (success === false) return <XCircle className="w-5 h-5 text-red-500" />;
    return <Clock className="w-5 h-5 text-muted-foreground" />;
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-500" />
            执行报告
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg px-4 py-3 text-sm text-destructive">
            <AlertTriangle className="w-5 h-5 inline mr-2" />
            {error}
          </div>
        ) : trace ? (
          <div className="space-y-6 py-4">
            {/* 执行摘要 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="w-4 h-4 text-muted-foreground" />
                  执行摘要
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(trace.success)}
                    <div>
                      <div className="text-sm font-medium">
                        {trace.success === true ? '执行成功' : trace.success === false ? '执行失败' : '执行中'}
                      </div>
                      <div className="text-xs text-muted-foreground">执行状态</div>
                    </div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">{formatDuration(trace.duration_ms)}</div>
                    <div className="text-xs text-muted-foreground">执行时长</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 执行详情 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">执行详情</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {trace.steps && trace.steps.length > 0 ? (
                  <div className="space-y-2">
                    {trace.steps.map((step, index) => (
                      <div key={index} className="flex items-start gap-3 p-2 rounded-lg bg-muted/50">
                        {getStatusIcon(step.success)}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">
                            {step.name || step.type || `步骤 ${index + 1}`}
                          </div>
                          {step.error && (
                            <div className="text-xs text-destructive mt-1">{step.error}</div>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDuration(step.duration_ms)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">暂无执行详情</div>
                )}
              </CardContent>
            </Card>

            {/* 元数据 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">元数据</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {trace.id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Trace ID</span>
                      <span className="font-mono text-xs">{trace.id}</span>
                    </div>
                  )}
                  {trace.goal_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">目标 ID</span>
                      <span className="font-mono text-xs">{trace.goal_id}</span>
                    </div>
                  )}
                  {trace.project_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">工程 ID</span>
                      <span className="font-mono text-xs">{trace.project_id}</span>
                    </div>
                  )}
                  {trace.task_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">任务 ID</span>
                      <span className="font-mono text-xs">{trace.task_id}</span>
                    </div>
                  )}
                  {trace.agent_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Agent ID</span>
                      <span className="font-mono text-xs">{trace.agent_id}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">暂无数据</div>
        )}

        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>关闭</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
