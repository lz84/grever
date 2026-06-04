/**
 * 目标分解预览组件
 * 调用 goalsApi.decomposePreview / autoDecomposePreview
 */

import { useState } from 'react'
import { toast } from 'sonner'
import { Loader2, Eye, GitBranch, CheckCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { goalsApi } from '@/shared/utils/api'
import type { Task, DecomposedProject } from '@/shared/utils/api'

interface GoalDecomposePreviewProps {
  goalId: string
  onDecompose?: () => void
}

export default function GoalDecomposePreview({ goalId, onDecompose }: GoalDecomposePreviewProps) {
  const [mode, setMode] = useState<'manual' | 'auto'>('manual')
  const [selectedAgent, setSelectedAgent] = useState<string>('__none__')
  const [loading, setLoading] = useState(false)
  const [previewTasks, setPreviewTasks] = useState<Task[]>([])
  const [previewProjects, setPreviewProjects] = useState<DecomposedProject[]>([])
  const [showPreview, setShowPreview] = useState(false)

  async function handlePreview() {
    setLoading(true)
    setShowPreview(false)
    try {
      if (mode === 'auto') {
        const resp = await goalsApi.autoDecomposePreview(goalId)
        setPreviewProjects(resp.projects || [])
        setPreviewTasks([])
      } else {
        const resp = await goalsApi.decomposePreview(goalId, selectedAgent === '__none__' ? undefined : selectedAgent)
        setPreviewTasks(resp.tasks || [])
        setPreviewProjects([])
      }
      setShowPreview(true)
      toast.success('分解预览已生成')
    } catch (e: any) {
      toast.error('分解预览失败: ' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirmDecompose() {
    setLoading(true)
    try {
      if (mode === 'auto') {
        await goalsApi.autoDecompose(goalId)
        toast.success('自动分解成功')
      } else {
        await goalsApi.decompose(goalId, selectedAgent === '__none__' ? undefined : selectedAgent)
        toast.success('分解成功')
      }
      onDecompose?.()
      setShowPreview(false)
    } catch (e: any) {
      toast.error('分解失败: ' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const taskStatusBadge = (status: string | null) => {
    const cls = status === 'done' ? 'bg-green-100 text-green-800' :
                status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                status === 'todo' ? 'bg-gray-100 text-gray-800' :
                'bg-yellow-100 text-yellow-800'
    return <span className={`text-xs px-1.5 py-0.5 rounded ${cls}`}>{status || 'pending'}</span>
  }

  const priorityBadge = (priority: number | string | null) => {
    if (priority === null || priority === undefined) return <span className="text-xs text-muted-foreground">-</span>
    const p = typeof priority === 'number' ? priority : parseInt(priority)
    const cls = p <= 1 ? 'text-red-600' : p <= 2 ? 'text-orange-600' : p <= 3 ? 'text-blue-600' : 'text-gray-600'
    return <span className={`text-xs font-medium ${cls}`}>P{p}</span>
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-purple-500" />
          <CardTitle className="text-sm">目标分解</CardTitle>
        </div>
        <CardDescription>预览分解结果并确认创建任务和工程</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Mode Selection */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setMode('manual')}
            className={`flex-1 p-3 rounded-lg border-2 text-left transition-all ${
              mode === 'manual' ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="text-sm font-medium">手动分解</div>
            <div className="text-xs text-muted-foreground">选择智能体进行分解</div>
          </button>
          <button
            type="button"
            onClick={() => setMode('auto')}
            className={`flex-1 p-3 rounded-lg border-2 text-left transition-all ${
              mode === 'auto' ? 'border-purple-500 bg-purple-50' : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="text-sm font-medium">自动分解</div>
            <div className="text-xs text-muted-foreground">LLM 自动生成工程列表</div>
          </button>
        </div>

        {/* Agent Selection for Manual Mode */}
        {mode === 'manual' && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">选择分解智能体</label>
            <Select value={selectedAgent} onValueChange={setSelectedAgent}>
              <SelectTrigger>
                <SelectValue placeholder="选择智能体" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">系统默认</SelectItem>
                <SelectItem value="kouzi">kouzi（开发专员）</SelectItem>
                <SelectItem value="mazi">mazi（技术专家）</SelectItem>
                <SelectItem value="guzi">guzi（业务专家）</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Preview Button */}
        <Button onClick={handlePreview} disabled={loading} className="w-full">
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin mr-1" />
          ) : (
            <Eye className="w-4 h-4 mr-1" />
          )}
          {loading ? '生成预览中...' : '预览分解'}
        </Button>

        {/* Preview Results */}
        {showPreview && (
          <div className="space-y-3">
            {previewTasks.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                    预览任务 ({previewTasks.length})
                  </h4>
                  <Button size="sm" onClick={handleConfirmDecompose} disabled={loading}>
                    {loading ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
                    确认分解
                  </Button>
                </div>
                <div className="border rounded-md max-h-[300px] overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[40%]">任务名称</TableHead>
                        <TableHead>优先级</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>分类</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewTasks.map((task, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-medium text-sm">{task.title || '未命名'}</TableCell>
                          <TableCell>{priorityBadge(task.priority)}</TableCell>
                          <TableCell>{taskStatusBadge(task.status)}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{task.capability_tags ? Object.keys(task.capability_tags).join(', ') : '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            {previewProjects.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                    预览工程 ({previewProjects.length})
                  </h4>
                  <Button size="sm" onClick={handleConfirmDecompose} disabled={loading}>
                    {loading ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
                    确认分解
                  </Button>
                </div>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {previewProjects.map((proj, i) => (
                    <div key={i} className="p-3 border rounded-lg bg-slate-50">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{proj.name}</span>
                        {proj.priority && (
                          <Badge variant={proj.priority <= 1 ? 'destructive' : proj.priority <= 2 ? 'default' : 'secondary'}>
                            P{proj.priority}
                          </Badge>
                        )}
                      </div>
                      {proj.description && (
                        <p className="text-xs text-muted-foreground mt-1">{proj.description}</p>
                      )}
                      {proj.dependencies && proj.dependencies.length > 0 && (
                        <div className="flex items-center gap-1 mt-1.5">
                          <AlertCircle className="w-3 h-3 text-amber-500" />
                          <span className="text-xs text-amber-700">
                            依赖: {proj.dependencies.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {previewTasks.length === 0 && previewProjects.length === 0 && (
              <div className="text-center py-4 text-muted-foreground">
                <AlertCircle className="w-6 h-6 mx-auto mb-2 text-amber-500" />
                <p className="text-sm">暂无分解结果</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
