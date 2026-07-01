import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card';
import { Badge } from '@/shared/components/ui/badge';
import { Separator } from '@/shared/components/ui/separator';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/shared/components/ui/accordion';
import { CheckCircle, AlertCircle, XCircle, Wrench } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface TaskSelfReviewNode {
  name: string;
  status: 'passed' | 'passed_after_retry' | 'failed';
  standards_checked: string[];
  corrections_made: string[];
  retry_count?: number;
  known_issues?: string[];
}

export interface TaskSelfReviewReport {
  self_review_count: number;
  nodes: TaskSelfReviewNode[];
}

// ── Helper Functions ───────────────────────────────────────────────────────────

function getStatusIcon(status: TaskSelfReviewNode['status']) {
  switch (status) {
    case 'passed':
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'passed_after_retry':
      return <AlertCircle className="w-4 h-4 text-amber-500" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />;
    default:
      return null;
  }
}

function getStatusText(status: TaskSelfReviewNode['status']) {
  switch (status) {
    case 'passed':
      return '通过 ✅';
    case 'passed_after_retry':
      return '重试后通过 ⚠️';
    case 'failed':
      return '失败 ❌';
    default:
      return status;
  }
}

// ── Sub Components ─────────────────────────────────────────────────────────────

function NodeDetails({ node }: { node: TaskSelfReviewNode }) {
  return (
    <div className="space-y-3">
      {/* Standards Checked */}
      {node.standards_checked.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-500 mb-1">检查标准：</p>
          <div className="flex flex-wrap gap-1">
            {node.standards_checked.map((std, i) => (
              <Badge key={i} variant="secondary" className="text-xs">
                {std}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Corrections Made */}
      {node.corrections_made.length > 0 && (
        <div className="flex items-start gap-2">
          <Wrench className="w-4 h-4 text-blue-500 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs font-medium text-slate-500 mb-1">修复内容：</p>
            <ul className="space-y-1">
              {node.corrections_made.map((corr, i) => (
                <li key={i} className="text-xs text-slate-700">
                  • {corr}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Retry info */}
      {node.retry_count !== undefined && node.retry_count > 1 && (
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs font-medium text-slate-500">重试信息：</p>
            <p className="text-xs text-slate-700">
              第 1 次失败 → 修正 → 第 {node.retry_count} 次通过
            </p>
          </div>
        </div>
      )}

      {/* Known Issues */}
      {node.known_issues && node.known_issues.length > 0 && (
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs font-medium text-slate-500 mb-1">已知问题：</p>
            <ul className="space-y-1">
              {node.known_issues.map((issue, i) => (
                <li key={i} className="text-xs text-amber-700">
                  • {issue}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function TaskSelfReview({ task }: { task: { self_review_count?: number; self_review_report?: string | TaskSelfReviewReport } }) {
  const report = React.useMemo<TaskSelfReviewReport | null>(() => {
    if (!task.self_review_report) return null;

    // 如果是字符串，尝试解析
    if (typeof task.self_review_report === 'string') {
      try {
        return JSON.parse(task.self_review_report);
      } catch {
        return null;
      }
    }

    return task.self_review_report;
  }, [task.self_review_report]);

  if (!report || report.nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">自检报告</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-400 text-center py-4">暂无自检报告</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">自检报告</CardTitle>
        <p className="text-xs text-slate-500 mt-1">自检次数：{report.self_review_count}</p>
      </CardHeader>
      <CardContent>
        <Accordion type="multiple" className="space-y-3">
          {report.nodes.map((node, idx) => (
            <AccordionItem key={idx} value={`node-${idx}`} className="border-l-2 border-l-slate-200">
              <AccordionTrigger className="no-underline hover:no-underline px-3 py-2 hover:bg-slate-50 rounded-lg">
                <div className="flex items-center gap-2">
                  {getStatusIcon(node.status)}
                  <span className="text-sm font-medium">{node.name}</span>
                  <Badge variant="secondary" className="text-xs ml-auto">
                    {getStatusText(node.status)}
                  </Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="px-3 pb-3 pt-1">
                  <NodeDetails node={node} />
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </CardContent>
    </Card>
  );
}
