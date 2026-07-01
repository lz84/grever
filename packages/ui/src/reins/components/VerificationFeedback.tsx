/**
 * VerificationFeedback - 验证反馈展示组件
 * 展示四维度验证结果，包含业务结果、跨任务一致性、目标对齐、质量判断
 *
 * 使用方式：
 * <VerificationFeedback feedback={data} taskId="xxx" />
 * 或放在 TaskDetail 页面自动从 task.verification_feedback 读取
 */

import { useState } from 'react'
import { CheckCircle, XCircle, AlertTriangle, RotateCcw, FileText, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Separator } from '@/shared/components/ui/separator'
import { toast } from 'sonner'
import { tasksApi } from '@/shared/utils/api'

// ── Types ──────────────────────────────────────────────────────────────────────

export type Verdict = 'passed' | 'failed' | 'partial'

export interface DimensionStatus {
  status: 'passed' | 'failed'
  details: string
}

export interface VerificationFeedback {
  verdict: Verdict
  verification_round: number
  dimensions: {
    business_result: DimensionStatus
    cross_task_consistency: DimensionStatus
    goal_alignment: DimensionStatus
    quality: DimensionStatus
  }
  feedback: string
  raw_result?: unknown
}

// ── 常量映射 ─────────────────────────────────────────────────────────────────

const DIMENSION_LABELS: Record<keyof VerificationFeedback['dimensions'], string> = {
  business_result: '业务结果',
  cross_task_consistency: '跨任务一致性',
  goal_alignment: '目标对齐',
  quality: '质量判断',
}

// ── 辅助函数 ─────────────────────────────────────────────────────────────────

function getVerdictIcon(verdict: Verdict) {
  switch (verdict) {
    case 'passed':
      return <CheckCircle className="w-5 h-5 text-green-500" />
    case 'failed':
      return <XCircle className="w-5 h-5 text-red-500" />
    case 'partial':
      return <AlertTriangle className="w-5 h-5 text-amber-500" />
  }
}

function getVerdictLabel(verdict: Verdict) {
  switch (verdict) {
    case 'passed': return '✅ 通过'
    case 'failed': return '❌ 未通过'
    case 'partial': return '⚠️ 部分通过'
  }
}

function getStatusIcon(status: 'passed' | 'failed') {
  if (status === 'passed') {
    return <CheckCircle className="w-3.5 h-3.5 text-green-500" />
  }
  return <XCircle className="w-3.5 h-3.5 text-red-500" />
}

function getStatusBadgeVariant(status: 'passed' | 'failed'): 'default' | 'destructive' {
  return status === 'passed' ? 'default' : 'destructive'
}

// ── 维度行组件 ───────────────────────────────────────────────────────────────

interface DimensionRowProps {
  label: string
  status: 'passed' | 'failed'
  details: string
}

function DimensionRow({ label, status, details }: DimensionRowProps) {
  return (
    <div className={`flex items-start gap-2 py-2 px-3 rounded-lg ${status === 'failed' ? 'bg-red-50' : 'bg-green-50'}`}>
      {getStatusIcon(status)}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-800">{label}</span>
          <Badge variant={getStatusBadgeVariant(status)} className="text-xs">
            {status === 'passed' ? '通过' : '未通过'}
          </Badge>
        </div>
        {details && (
          <p className="text-xs text-slate-600 mt-0.5">{details}</p>
        )}
      </div>
    </div>
  )
}

// ── 主组件 ───────────────────────────────────────────────────────────────────

interface VerificationFeedbackProps {
  /** 验证反馈数据，直接传入则不自动拉取 */
  feedback?: VerificationFeedback
  /** 任务 ID，用于自动拉取和重新提交 */
  taskId?: string
  /** 手动触发重新加载 */
  onRefresh?: () => void
}

export default function VerificationFeedback({ feedback: propFeedback, taskId, onRefresh }: VerificationFeedbackProps) {
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // 如果没有传入 feedback，组件将渲染空状态
  // 外部可控制是否显示此组件
  const feedback = propFeedback

  // 重新提交触发新一轮验证
  async function handleResubmit() {
    if (!taskId) {
      toast.error('任务 ID 缺失，无法重新提交')
      return
    }
    setSubmitting(true)
    try {
      await tasksApi.resubmitVerification(taskId)
      toast.success('已重新提交验证')
      onRefresh?.()
    } catch (e: any) {
      toast.error('重新提交失败: ' + (e.message || '未知错误'))
    } finally {
      setSubmitting(false)
    }
  }

  // 无数据时显示空状态
  if (!feedback) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">验证反馈</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-slate-400 text-center py-4">暂无验证反馈</p>
        </CardContent>
      </Card>
    )
  }

  const { verdict, verification_round, dimensions, feedback: feedbackText } = feedback

  // 分类维度
  const passedDimensions = (Object.entries(dimensions) as [keyof typeof dimensions, DimensionStatus][])
    .filter(([, dim]) => dim.status === 'passed')
  const failedDimensions = (Object.entries(dimensions) as [keyof typeof dimensions, DimensionStatus][])
    .filter(([, dim]) => dim.status === 'failed')

  const verdictBgClass = verdict === 'failed'
    ? 'bg-red-50 border-red-200'
    : verdict === 'passed'
      ? 'bg-green-50 border-green-200'
      : 'bg-amber-50 border-amber-200'

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-slate-500" />
            <CardTitle className="text-sm">验证反馈</CardTitle>
          </div>
          <Badge variant="secondary" className="text-xs">
            第 {verification_round} 轮
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* 结论行 */}
        <div className={`flex items-center gap-2 p-3 rounded-lg border ${verdictBgClass}`}>
          {getVerdictIcon(verdict)}
          <span className="text-sm font-medium">
            结论：{getVerdictLabel(verdict)}
          </span>
        </div>

        {/* 未通过维度 */}
        {failedDimensions.length > 0 && (
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">❌ 未通过维度：</p>
            <div className="space-y-2">
              {failedDimensions.map(([key, dim]) => (
                <DimensionRow
                  key={key}
                  label={DIMENSION_LABELS[key]}
                  status={dim.status}
                  details={dim.details}
                />
              ))}
            </div>
          </div>
        )}

        {/* 已通过维度 */}
        {passedDimensions.length > 0 && (
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">
              {failedDimensions.length > 0 ? '✅ 已通过维度：' : '✅ 全部维度通过'}
            </p>
            <div className="space-y-2">
              {passedDimensions.map(([key, dim]) => (
                <DimensionRow
                  key={key}
                  label={DIMENSION_LABELS[key]}
                  status={dim.status}
                  details={dim.details}
                />
              ))}
            </div>
          </div>
        )}

        {/* 全局反馈/修改建议 */}
        {feedbackText && (
          <>
            <Separator />
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-xs font-medium text-blue-600 mb-1">💡 修改建议</p>
              <p className="text-sm text-slate-700">{feedbackText}</p>
            </div>
          </>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-2 pt-1">
          {taskId && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={handleResubmit}
              disabled={submitting || loading}
            >
              {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
              重新提交
            </Button>
          )}
          {taskId && (
            <Button
              variant="ghost"
              size="sm"
              className="flex-1"
              onClick={() => {
                toast.info('自检报告功能开发中')
              }}
            >
              <FileText className="w-3 h-3" />
              查看自检报告
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
