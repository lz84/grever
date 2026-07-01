/**
 * GoalVerificationReports - 验证报告展示组件
 * Sprint 6 task-s6-2
 */

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Shield, AlertTriangle, Lightbulb, Wrench, Plus,
  Loader2, ChevronDown, CheckCircle, XCircle, AlertCircle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/shared/components/ui/accordion'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { goalsApi } from '@/shared/utils/api'
import type { VerificationReport } from '@/shared/utils/api'

// ── 常量映射 ─────────────────────────────────────────────────────────────────

const VERDICT_CFG: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  passed: { label: '通过', icon: <CheckCircle className="w-4 h-4 text-green-500" />, color: 'text-green-700', bg: 'bg-green-50 border-green-200' },
  failed: { label: '未通过', icon: <XCircle className="w-4 h-4 text-red-500" />, color: 'text-red-700', bg: 'bg-red-50 border-red-200' },
  partial: { label: '部分通过', icon: <AlertCircle className="w-4 h-4 text-amber-500" />, color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
}

const SEVERITY_CFG: Record<string, { label: string; color: string }> = {
  high: { label: '高', color: 'bg-red-100 text-red-700' },
  medium: { label: '中', color: 'bg-amber-100 text-amber-700' },
  low: { label: '低', color: 'bg-blue-100 text-blue-700' },
}

// ── 补救任务创建对话框 ────────────────────────────────────────────────────────

interface CreateRemedialTaskDialogProps {
  open: boolean
  onClose: () => void
  goalId: string
  report: VerificationReport | null
  onCreated: () => void
}

function CreateRemedialTaskDialog({ open, onClose, goalId, report, onCreated }: CreateRemedialTaskDialogProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('medium')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open && report) {
      const first = report.remedial_tasks?.[0]
      if (first) {
        setTitle(first.title)
        setDescription(first.description || '')
        setPriority(first.priority || 'medium')
      } else {
        setTitle(''); setDescription(''); setPriority('medium')
      }
    }
  }, [open, report])

  async function handleCreate() {
    if (!title.trim()) { toast.error('请输入补救任务标题'); return }
    setSaving(true)
    try {
      await goalsApi.createRemedialTask(goalId, { title: title.trim(), description: description.trim() || undefined, priority })
      toast.success('补救任务已创建')
      onCreated()
      onClose()
    } catch (e: any) { toast.error('创建失败: ' + (e.message || '未知错误')) }
    finally { setSaving(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>创建补救任务</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">任务标题</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：新增用户认证 API 单元测试" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">描述（可选）</label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="描述补救任务的具体内容..." rows={3} />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">优先级</label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="high">🔴 高</SelectItem>
                <SelectItem value="medium">🟡 中</SelectItem>
                <SelectItem value="low">🔵 低</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>取消</Button>
          <Button onClick={handleCreate} disabled={saving || !title.trim()}>
            {saving ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Plus className="w-3 h-3 mr-1" />}
            {saving ? '创建中...' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── 主组件 ───────────────────────────────────────────────────────────────────

interface GoalVerificationReportsProps { goalId: string }

export default function GoalVerificationReports({ goalId }: GoalVerificationReportsProps) {
  const [reports, setReports] = useState<VerificationReport[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedReport, setSelectedReport] = useState<VerificationReport | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => { fetchReports() }, [goalId])

  async function fetchReports() {
    setLoading(true)
    try {
      const data = await goalsApi.getVerificationReports(goalId)
      setReports(Array.isArray(data) ? data : [])
    } catch { setReports([]) }
    finally { setLoading(false) }
  }

  if (loading) return (
    <Card>
      <CardHeader className="pb-3"><div className="flex items-center gap-2"><Shield className="w-4 h-4 text-slate-500" /><CardTitle className="text-sm">验证报告</CardTitle></div><CardDescription>统筹验证结果</CardDescription></CardHeader>
      <CardContent className="flex items-center justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></CardContent>
    </Card>
  )

  if (reports.length === 0) return (
    <Card>
      <CardHeader className="pb-3"><div className="flex items-center gap-2"><Shield className="w-4 h-4 text-slate-500" /><CardTitle className="text-sm">验证报告</CardTitle></div><CardDescription>统筹验证结果</CardDescription></CardHeader>
      <CardContent><div className="text-center py-8 text-muted-foreground"><Shield className="w-10 h-10 mx-auto mb-3 opacity-40" /><p className="text-sm">暂无验证报告</p><p className="text-xs mt-1">运行目标后将自动生成统筹验证报告</p></div></CardContent>
    </Card>
  )

  const sorted = [...reports].sort((a, b) => (b.round ?? 0) - (a.round ?? 0))

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2"><Shield className="w-4 h-4 text-slate-500" /><CardTitle className="text-sm">验证报告</CardTitle><Badge variant="secondary" className="text-xs">{reports.length} 轮</Badge></div>
          <CardDescription>统筹验证结果与补救建议</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Accordion type="multiple" className="w-full">
            {sorted.map((report) => {
              const vc = VERDICT_CFG[report.verdict ?? 'partial'] || VERDICT_CFG.partial
              return (
                <AccordionItem key={report.id} value={report.id} className="border rounded-lg px-3 mb-2">
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-3 flex-1 text-left">
                      <span className="font-mono font-bold text-sm text-slate-800 shrink-0">第 {report.round ?? '?'} 轮</span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${vc.bg} ${vc.color}`}>{vc.icon}{vc.label}</span>
                      <span className="text-sm text-slate-600 truncate flex-1">{report.summary || '—'}</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-4 pt-2 pb-3">
                      {report.summary && <div className="text-sm text-slate-600 bg-slate-50 rounded p-2">{report.summary}</div>}

                      {report.gaps?.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2"><AlertTriangle className="w-3.5 h-3.5 text-red-500" /><h4 className="text-sm font-medium text-slate-700">发现的空白</h4></div>
                          <div className="space-y-1.5 pl-5">
                            {report.gaps.map((gap: any, i: number) => {
                              const sev = SEVERITY_CFG[gap.severity] || SEVERITY_CFG.medium
                              return (
                                <div key={i} className="flex items-center gap-2">
                                  <span className="text-sm text-slate-600">• {gap.gap}</span>
                                  <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${sev.color}`}>{sev.label}</span>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      {report.recommendations?.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2"><Lightbulb className="w-3.5 h-3.5 text-amber-500" /><h4 className="text-sm font-medium text-slate-700">建议</h4></div>
                          <div className="space-y-1.5 pl-5">
                            {report.recommendations.map((rec: any, i: number) => (
                              <div key={i} className="flex items-start gap-2"><span className="text-sm text-slate-600">• {rec.recommendation}</span></div>
                            ))}
                          </div>
                        </div>
                      )}

                      {report.remedial_tasks?.length > 0 ? (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2"><Wrench className="w-3.5 h-3.5 text-blue-500" /><h4 className="text-sm font-medium text-slate-700">补救任务</h4></div>
                          <div className="space-y-2 pl-5">
                            {report.remedial_tasks.map((task: any, i: number) => (
                              <div key={i} className="flex items-center justify-between gap-3 bg-blue-50 rounded p-2">
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium text-blue-800">{task.title}</p>
                                  {task.description && <p className="text-xs text-blue-600 mt-0.5 truncate">{task.description}</p>}
                                </div>
                                <Button size="sm" variant="outline" className="h-6 text-xs shrink-0 border-blue-300 text-blue-700 hover:bg-blue-100" onClick={() => { setSelectedReport(report); setDialogOpen(true) }}>
                                  <Plus className="w-3 h-3 mr-0.5" />创建
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="flex justify-center pt-1">
                          <Button size="sm" variant="outline" className="text-blue-700 border-blue-300 hover:bg-blue-50" onClick={() => { setSelectedReport(report); setDialogOpen(true) }}>
                            <Plus className="w-3 h-3 mr-1" />创建补救任务
                          </Button>
                        </div>
                      )}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )
            })}
          </Accordion>
        </CardContent>
      </Card>
      <CreateRemedialTaskDialog open={dialogOpen} onClose={() => setDialogOpen(false)} goalId={goalId} report={selectedReport} onCreated={fetchReports} />
    </>
  )
}
