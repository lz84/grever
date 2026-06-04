import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from "sonner"
import { tasksApi, projectsApi, goalsApi } from '../../../shared/utils/api'
import type { Project, Goal } from '../../../shared/utils/api'
import { ArrowLeft, Save, X, Upload, FileText, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Separator } from '@/shared/components/ui/separator'

export default function CreateTask() {
  const navigate = useNavigate()

  const [goals, setGoals] = useState<Goal[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)

  // Form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedGoalId, setSelectedGoalId] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [priority, setPriority] = useState('medium')
  const [category, setCategory] = useState('')
  const [agentId, setAgentId] = useState('')
  const [estimatedHours, setEstimatedHours] = useState('')
  const [docRefs, setDocRefs] = useState<string[]>([''])
  const [workspacePath, setWorkspacePath] = useState('')
  const [attachments, setAttachments] = useState<File[]>([])

  // Load goals on mount
  useEffect(() => {
    loadGoals()
  }, [])

  // Load projects when goal changes
  useEffect(() => {
    if (selectedGoalId) {
      loadProjects(selectedGoalId)
    } else {
      setProjects([])
    }
  }, [selectedGoalId])

  async function loadGoals() {
    try {
      const items = await goalsApi.list()
      setGoals(items || [])
    } catch (e) {
      console.error('Failed to load goals', e)
    }
  }

  async function loadProjects(goalId: string) {
    try {
      const items = await projectsApi.list({ goal_id: goalId })
      setProjects(items || [])
    } catch (e) {
      console.error('Failed to load projects', e)
    }
  }

  function addDocRef() {
    setDocRefs([...docRefs, ''])
  }

  function removeDocRef(idx: number) {
    setDocRefs(docRefs.filter((_, i) => i !== idx))
  }

  function updateDocRef(idx: number, val: string) {
    const updated = [...docRefs]
    updated[idx] = val
    setDocRefs(updated)
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      setAttachments([...attachments, ...Array.from(e.target.files)])
    }
  }

  function removeAttachment(idx: number) {
    setAttachments(attachments.filter((_, i) => i !== idx))
  }

  async function handleSubmit() {
    if (!title.trim()) {
      toast.error('任务标题不能为空')
      return
    }

    setLoading(true)
    try {
      // Create task
      const task = await tasksApi.create({
        title: title.trim(),
        description: description.trim(),
        priority,
        project_id: selectedProjectId || undefined,
        goal_id: selectedGoalId || undefined,
        category: category || undefined,
        assigned_agent: agentId || undefined,
        estimated_hours: estimatedHours ? Number(estimatedHours) : undefined,
        workspace_path: workspacePath || undefined,
        doc_refs: docRefs.filter(d => d.trim()),
      })
      toast.success(`任务 "${task.title}" 创建成功`)

      // Upload attachments if any
      if (attachments.length > 0 && task.id) {
        for (const file of attachments) {
          await tasksApi.uploadAttachment(task.id, file)
        }
        toast.success(`已上传 ${attachments.length} 个附件`)
      }

      navigate(`/coordination/tasks/${task.id}`)
    } catch (e: any) {
      toast.error(e.message || '创建任务失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center gap-3 max-w-5xl mx-auto">
          <Button variant="outline" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900">创建任务</h1>
            <p className="text-sm text-slate-500">填写任务信息并创建到系统中</p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
            <CardDescription>任务的标题、描述和优先级</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="title">任务标题 <span className="text-red-500">*</span></Label>
              <Input
                id="title"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="输入任务标题..."
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="详细描述任务内容、要求和预期结果..."
                rows={4}
                className="mt-1"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>优先级</Label>
                <Select value={priority} onValueChange={setPriority}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="critical">紧急</SelectItem>
                    <SelectItem value="high">高</SelectItem>
                    <SelectItem value="medium">普通</SelectItem>
                    <SelectItem value="low">低</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>类别</Label>
                <Input
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  placeholder="如：开发、测试、文档..."
                  className="mt-1"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Association */}
        <Card>
          <CardHeader>
            <CardTitle>关联信息</CardTitle>
            <CardDescription>将任务关联到目标和工程</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>目标 (Goal)</Label>
                <Select value={selectedGoalId} onValueChange={setSelectedGoalId}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="选择目标..." />
                  </SelectTrigger>
                  <SelectContent>
                    {goals.map(g => (
                      <SelectItem key={g.id} value={String(g.id)}>
                        {g.title || g.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>工程 (Project)</Label>
                <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder={selectedGoalId ? "选择工程..." : "先选择目标"} />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map(p => (
                      <SelectItem key={p.id} value={String(p.id)}>
                        {p.name || p.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label>分配 Agent</Label>
              <Input
                value={agentId}
                onChange={e => setAgentId(e.target.value)}
                placeholder="Agent ID（可选）"
                className="mt-1"
              />
            </div>

            <div>
              <Label>预估工时（小时）</Label>
              <Input
                type="number"
                value={estimatedHours}
                onChange={e => setEstimatedHours(e.target.value)}
                placeholder="如：8"
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* References */}
        <Card>
          <CardHeader>
            <CardTitle>文档引用</CardTitle>
            <CardDescription>关联的文档路径或 URL</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {docRefs.map((ref, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    value={ref}
                    onChange={e => updateDocRef(idx, e.target.value)}
                    placeholder="/path/to/doc or https://..."
                  />
                  {docRefs.length > 1 && (
                    <Button variant="ghost" size="icon" onClick={() => removeDocRef(idx)}>
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
              <Button variant="outline" size="sm" onClick={addDocRef}>
                <Plus className="w-3 h-3 mr-1" /> 添加引用
              </Button>
            </div>

            <Separator className="my-4" />

            <div>
              <Label>工作区路径</Label>
              <Input
                value={workspacePath}
                onChange={e => setWorkspacePath(e.target.value)}
                placeholder="/path/to/workspace"
                className="mt-1"
              />
            </div>
          </CardContent>
        </Card>

        {/* Attachments */}
        <Card>
          <CardHeader>
            <CardTitle>附件</CardTitle>
            <CardDescription>上传相关文件（创建任务后上传）</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="attachment-input"
              />
              <label htmlFor="attachment-input" className="cursor-pointer">
                <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                <p className="text-sm text-slate-600">点击或拖拽文件上传</p>
                <p className="text-xs text-slate-400 mt-1">支持任意文件类型</p>
              </label>
            </div>

            {attachments.length > 0 && (
              <div className="mt-4 space-y-2">
                {attachments.map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between bg-slate-50 rounded px-3 py-2">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-500" />
                      <span className="text-sm">{file.name}</span>
                      <Badge variant="secondary" className="text-xs">
                        {(file.size / 1024).toFixed(0)} KB
                      </Badge>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => removeAttachment(idx)}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={() => navigate(-1)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !title.trim()}>
            {loading ? '创建中...' : (
              <>
                <Save className="w-4 h-4 mr-1" /> 创建任务
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
