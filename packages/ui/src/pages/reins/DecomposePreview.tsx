import { useState, useEffect } from 'react'
import { GOALS } from '../../shared/api/paths'
import { Link, useParams, useLocation, useNavigate } from 'react-router-dom'
import { projectsApi } from '../../shared/utils/api'
import {
  ArrowLeft,
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle,
  Brain,
  FolderOpen,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Textarea } from '@/shared/components/ui/textarea'

// Priority options
const PRIORITY_OPTIONS = [
  { value: 1, label: 'P0-紧急', variant: 'destructive' as const },
  { value: 2, label: 'P1-高', variant: 'warning' as const },
  { value: 3, label: 'P2-中', variant: 'info' as const },
  { value: 4, label: 'P3-低', variant: 'secondary' as const },
]

function generateTempId() {
  return `temp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

interface DecomposedProject {
  id?: string
  name: string
  description?: string
  priority?: number
  category?: string
}

interface LocationState {
  goalId: string
  goalTitle: string
  projects: DecomposedProject[]
}

export default function DecomposePreview() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  const state = location.state as LocationState | null

  const [projects, setProjects] = useState<DecomposedProject[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (state?.projects && state.projects.length > 0) {
      setProjects(state.projects)
      setLoading(false)
    } else if (id) {
      // Fallback: fetch projects from API
      projectsApi.list({ goal_id: id }).then(apiProjects => {
        if (apiProjects.length > 0) {
          setProjects(apiProjects.map((p: any) => ({
            id: String(p.id),
            name: p.name || p.title || '',
            description: p.description || '',
            priority: { high: 1, medium: 2, low: 3 }[String(p.priority)] || 3,
          })))
        }
        setLoading(false)
      }).catch(() => {
        setLoading(false)
      })
    } else {
      setLoading(false)
    }
  }, [state])

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <Loader2 className="w-10 h-10 text-primary animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">加载中...</p>
      </div>
    )
  }

  if (!state && !id) {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <AlertCircle className="w-10 h-10 text-destructive mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-foreground mb-2">无法访问此页面</h2>
        <p className="text-muted-foreground mb-6">请从「创建目标」流程进入</p>
        <Button asChild>
          <Link to="/coordination/goals/new">
            创建目标
          </Link>
        </Button>
      </div>
    )
  }

  function updateProject(tempId: string, field: keyof DecomposedProject, value: any) {
    setProjects(prev =>
      prev.map(p => (p.id === tempId ? { ...p, [field]: value } : p))
    )
  }

  function addProject() {
    setProjects(prev => [
      ...prev,
      {
        id: generateTempId(),
        name: '',
        description: '',
        priority: 3,
      },
    ])
  }

  function deleteProject(tempId: string) {
    setProjects(prev => prev.filter(p => p.id !== tempId))
  }

  function isValid(): boolean {
    return projects.every(p => p.name && p.name.trim().length > 0)
  }

  async function handleSubmit() {
    if (!isValid()) {
      setError('请填写所有工程的名称')
      return
    }

    try {
      setSubmitting(true)
      setError(null)

      // 调用后端提交端点，创建工程
      const response = await fetch(GOALS.SUBMIT_DECOMPOSE(id!), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projects: projects.map(p => ({
            name: p.name,
            description: p.description || '',
            priority: p.priority ?? 3,
          })),
        }),
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `提交失败 (${response.status})`)
      }

      const result = await response.json()
      setSubmitted(true)

      // 跳转到目标详情页
      setTimeout(() => {
        navigate(`/coordination/goals/${result.goal_id}`)
      }, 1500)
    } catch (err: any) {
      const msg = typeof err === 'string' ? err : err?.detail || err?.message || JSON.stringify(err)
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="max-w-xl mx-auto text-center py-20">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-8 h-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">工程已提交</h2>
        <p className="text-muted-foreground mb-6">工程已创建，正在跳转...</p>
        <div className="flex justify-center">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          to="/coordination/goals"
          className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          返回列表
        </Link>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Brain className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">分析结果预览</h1>
            <p className="text-muted-foreground text-sm">
              目标「{state?.goalTitle || id}」的分析结果，请编辑确认后提交
            </p>
          </div>
        </div>
      </div>

      {/* Project list */}
      <div className="space-y-4 mb-8">
        {projects.length === 0 ? (
          <Card className="text-center py-8">
            <CardContent>
              <FolderOpen className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
              <p className="text-muted-foreground">暂无分解工程</p>
              <Button variant="outline" onClick={addProject} className="mt-3">
                + 添加工程
              </Button>
            </CardContent>
          </Card>
        ) : (
          projects.map((project, index) => (
            <Card key={project.id || index}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-muted rounded-full flex items-center justify-center text-xs font-bold text-muted-foreground">
                      {index + 1}
                    </div>
                    <span className="text-sm font-medium text-muted-foreground">
                      {project.id?.startsWith('temp-') ? '新工程' : '工程'}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteProject(project.id!)}
                    title="删除工程"
                    className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Project name */}
                <div className="space-y-2">
                  <Label htmlFor={`name-${project.id}`}>
                    工程名称 <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id={`name-${project.id}`}
                    type="text"
                    value={project.name}
                    onChange={e => updateProject(project.id!, 'name', e.target.value)}
                    placeholder="请输入工程名称"
                    maxLength={100}
                  />
                </div>

                {/* Project description */}
                <div className="space-y-2">
                  <Label htmlFor={`desc-${project.id}`}>
                    描述
                  </Label>
                  <Textarea
                    id={`desc-${project.id}`}
                    value={project.description || ''}
                    onChange={e => updateProject(project.id!, 'description', e.target.value)}
                    placeholder="请输入工程描述（可选）"
                    maxLength={500}
                    rows={2}
                  />
                </div>

                {/* Priority */}
                <div className="space-y-2">
                  <Label>优先级</Label>
                  <div className="flex gap-2">
                    {PRIORITY_OPTIONS.map(opt => (
                      <Button
                        key={opt.value}
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => updateProject(project.id!, 'priority', opt.value)}
                        className={
                          (project.priority ?? 3) === opt.value
                            ? opt.variant === 'destructive' ? 'border-red-500 text-red-600 bg-red-50' :
                              opt.variant === 'warning' ? 'border-orange-500 text-orange-600 bg-orange-50' :
                              opt.variant === 'info' ? 'border-blue-500 text-blue-600 bg-blue-50' :
                              'border-primary text-primary bg-primary/10'
                            : ''
                        }
                      >
                        {opt.label}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}

        {/* Add project button */}
        <Button
          variant="outline"
          onClick={addProject}
          className="w-full h-12 border-dashed"
        >
          <Plus className="w-4 h-4 mr-2" />
          添加工程
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between items-center">
        <Button variant="outline" asChild>
          <Link to="/coordination/goals">
            取消
          </Link>
        </Button>
        <div className="flex gap-3">
          <Button variant="outline" onClick={addProject}>
            <Plus className="w-4 h-4 mr-1.5" />
            添加工程
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || projects.length === 0 || !isValid()}
          >
            {submitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {submitting ? '提交中...' : '确认提交'}
          </Button>
        </div>
      </div>
    </div>
  )
}
