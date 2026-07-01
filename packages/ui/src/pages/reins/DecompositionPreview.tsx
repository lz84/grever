/**
 * DecompositionPreview.tsx - Sprint 2 s2-6
 * Decomposition Preview Page with Projects, Tasks, Assumptions, and Pending Confirmations
 */

import React, { useState, useEffect } from 'react'
import { Link, useParams, useNavigate, useLocation } from 'react-router-dom'
import {
  ArrowLeft, Plus, Trash2, Loader2, AlertCircle,
  Brain, FolderOpen, GitBranch, FileText, CheckCircle,
  ChevronDown, ChevronRight, ShieldAlert,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Textarea } from '@/shared/components/ui/textarea'
import { decompositionApi } from '@/shared/utils/api'
import { toast } from 'sonner'

// Types
interface Task {
  id?: string
  title: string
  type: string
  description?: string
}

interface Project {
  id?: string
  index: number
  name: string
  description: string
  priority: string
  category: string
  depends_on: number[]
  deliverables: string[]
  estimated_effort: string
  tasks: Task[]
}

interface Assumption {
  id: number
  text: string
  category: string
  risk_level: string
}

interface PendingConfirmation {
  id: string
  text: string
  category: string
  resolved: boolean
}

interface LocationState {
  goalId: string
  goalTitle: string
  projects: Project[]
  assumptions: Assumption[]
  pendingConfirmations: PendingConfirmation[]
}

// Category labels
const CATEGORY_LABELS: Record<string, string> = {
  research: '调研',
  design: '设计',
  implementation: '实施',
  testing: '测试',
  review: '评审',
  other: '其他',
}

const ASSUMPTION_CATEGORY_LABELS: Record<string, string> = {
  resource: '资源',
  technical: '技术',
  business: '业务',
  timeline: '时间',
}

const EFFORT_LABELS: Record<string, string> = {
  S: '<1周',
  M: '1-2周',
  L: '2-4周',
  XL: '>4周',
}

export default function DecompositionPreview() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const location = useLocation()

  const [projects, setProjects] = useState<Project[]>([])
  const [assumptions, setAssumptions] = useState<Assumption[]>([])
  const [pendingConfirmations, setPendingConfirmations] = useState<PendingConfirmation[]>([])
  const [goalTitle, setGoalTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const [goalId, setGoalId] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPreviewData = async () => {
      if (!id) {
        setError('缺少目标ID')
        setLoading(false)
        return
      }

      try {
        // Use state from navigation if available
        const state = location.state as LocationState | null
        if (state?.projects && state.projects.length > 0) {
          setProjects(state.projects.map((p, i) => ({ ...p, index: i })))
          setAssumptions(state.assumptions || [])
          setPendingConfirmations(state.pendingConfirmations || [])
          setGoalTitle(state.goalTitle)
          setGoalId(state.goalId)
          setExpandedProjects(new Set(state.projects.map((_, i) => String(i))))
          setError(null)
        } else {
          // Use real API to load decomposition preview
          const previewData = await decompositionApi.getPreview(id)
          setProjects(previewData.projects.map((p: any, i: number) => ({
            ...p,
            id: p.id || `proj-${i}`,
            index: i,
            name: p.name || '未命名工程',
            description: p.description || '',
            priority: typeof p.priority === 'string' ? p.priority : 'medium',
            category: p.category || 'other',
            depends_on: p.dependencies?.map((d: string) => projects.findIndex(p => p.id === d)) || [],
            deliverables: [],
            estimated_effort: 'M',
            tasks: [],
          })))
          setAssumptions(previewData.assumptions || [])
          setPendingConfirmations(previewData.pending_confirmations || [])
          setGoalTitle('')
          setGoalId(id)
          setExpandedProjects(new Set(previewData.projects.map((_: any, i: number) => String(i))))
          setError(null)
        }
      } catch (e: any) {
        setError(e.message || '加载分解预览失败')
        setLoading(false)
      }
    }
    loadPreviewData()
  }, [id, location.state])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto text-center py-20">
        <Loader2 className="w-10 h-10 text-primary animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">加载分解结果...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <AlertCircle className="w-10 h-10 text-destructive mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-foreground mb-2">加载失败</h2>
        <p className="text-muted-foreground mb-6">{error}</p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4 mr-1" /> 返回
        </Button>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="max-w-2xl mx-auto text-center py-20">
        <AlertCircle className="w-10 h-10 text-destructive mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-foreground mb-2">无法访问此页面</h2>
        <p className="text-muted-foreground mb-6">请从「创建目标」流程进入</p>
        <Button asChild>
          <Link to="/coordination/goals/new">创建目标</Link>
        </Button>
      </div>
    )
  }

  function toggleProjectExpand(index: string) {
    setExpandedProjects(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  function updateProject(index: number, field: keyof Project, value: any) {
    setProjects(prev => prev.map((p, i) => (i === index ? { ...p, [field]: value } : p)))
  }

  function deleteProject(index: number) {
    const newProjects = projects.filter((_, i) => i !== index)
    setProjects(
      newProjects.map((p, i) => ({
        ...p,
        index: i,
        depends_on: p.depends_on
          .map(d => (d > index ? d - 1 : d))
          .filter(d => d !== index && d >= 0 && d < newProjects.length),
      }))
    )
  }

  function isValid(): boolean {
    return projects.every(p => p.name && p.name.trim().length > 0)
  }

  async function handleConfirm() {
    if (!goalId) {
      alert('缺少目标ID')
      return
    }

    // In real flow, this would call POST /api/v1/goals/{id}/confirm-decomposition
    try {
      console.log('Confirming decomposition for goal:', goalId)
      alert('分解已确认，正在触发分配...')

      // Simulate navigation to goal detail
      setTimeout(() => {
        navigate(`/coordination/goals/${goalId}`)
      }, 1000)
    } catch (err: any) {
      alert(err.message || '确认失败')
    }
  }

  function handleModify() {
    // In real flow, this would navigate back to edit page
    navigate(-1)
  }

  // Build dependency map for display
  const depMap: Record<number, string[]> = {}
  projects.forEach((p, i) => {
    depMap[i] = p.depends_on.filter(d => d < i).map(d => projects[d]?.name || `项目 ${d + 1}`)
  })

  return (
    <div className="max-w-4xl mx-auto">
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
            <h1 className="text-2xl font-bold text-foreground">分解预览</h1>
            <p className="text-muted-foreground text-sm">
              {goalTitle} - 请确认以下分解方案
            </p>
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="text-2xl font-bold text-primary">{projects.length}</div>
            <div className="text-xs text-muted-foreground">子项目</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="text-2xl font-bold text-amber-600">{assumptions.length}</div>
            <div className="text-xs text-muted-foreground">假设</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <div className="text-2xl font-bold text-emerald-600">
              {projects.filter(p => p.depends_on.length === 0).length}
            </div>
            <div className="text-xs text-muted-foreground">根节点</div>
          </CardContent>
        </Card>
      </div>

      {/* Assumptions list */}
      {assumptions.length > 0 && (
        <Card className="mb-6 border-amber-200 bg-amber-50/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-amber-800">
              <ShieldAlert className="w-4 h-4" />
              假设清单
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {assumptions.map((a, i) => {
                const riskColor =
                  a.risk_level === 'high'
                    ? 'bg-red-100 text-red-700'
                    : a.risk_level === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-green-100 text-green-700'
                return (
                  <div key={a.id ?? i} className="flex items-start gap-2 text-sm">
                    <span className="text-muted-foreground shrink-0">{i + 1}.</span>
                    <span className="flex-1">{a.text}</span>
                    <Badge variant="outline" className={`shrink-0 ${riskColor} border-0`}>
                      {a.risk_level === 'high' ? '高风险' : a.risk_level === 'medium' ? '中风险' : '低风险'}
                    </Badge>
                    <Badge variant="outline" className="shrink-0">
                      {ASSUMPTION_CATEGORY_LABELS[a.category] || a.category}
                    </Badge>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pending Confirmations */}
      {pendingConfirmations.length > 0 && (
        <Card className="mb-6 border-amber-400 bg-amber-50/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-amber-700">
              <AlertCircle className="w-4 h-4" />
              待确认事项
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pendingConfirmations.map((pc, i) => (
                <div key={pc.id} className="flex items-center gap-2 text-sm">
                  <div className={`w-3 h-3 rounded-full ${pc.resolved ? 'bg-green-500' : 'bg-amber-500 animate-pulse'}`} />
                  <span className={`flex-1 ${pc.resolved ? 'text-muted-foreground line-through' : 'text-amber-800'}`}>
                    {i + 1}. {pc.text}
                  </span>
                  <Badge variant="outline" className="shrink-0">
                    {pc.category}
                  </Badge>
                  <Badge variant={pc.resolved ? 'default' : 'secondary'}>
                    {pc.resolved ? '已确认' : '待确认'}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Project tree */}
      <div className="space-y-3 mb-8">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-purple-600" />
          分解产物树
        </h2>

        {projects.map((project, index) => {
          const isExpanded = expandedProjects.has(String(index))
          const deps = depMap[index] || []

          return (
            <Card key={project.id || index} className={deps.length > 0 ? 'border-l-4 border-l-purple-400' : ''}>
              {/* Header row — click to expand */}
              <CardHeader className="pb-2 cursor-pointer" onClick={() => toggleProjectExpand(String(index))}>
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 flex items-center justify-center shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                  </div>
                  <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-xs font-bold text-purple-600">
                    {index + 1}
                  </div>
                  <span className="flex-1 font-medium truncate">{project.name || '未命名工程'}</span>
                  <Badge variant="outline" className="shrink-0">
                    {CATEGORY_LABELS[project.category] || project.category}
                  </Badge>
                  <Badge variant="outline" className="shrink-0">
                    {EFFORT_LABELS[project.estimated_effort] || project.estimated_effort}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={e => {
                      e.stopPropagation()
                      deleteProject(index)
                    }}
                    title="删除工程"
                    className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                {/* Dependencies bar */}
                {deps.length > 0 && (
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 ml-7">
                    <span>
                      ← 依赖: {deps.join(', ')}
                    </span>
                  </div>
                )}
              </CardHeader>

              {/* Expandable content */}
              {isExpanded && (
                <CardContent className="space-y-4 pt-0">
                  {/* Project description */}
                  <div className="space-y-2">
                    <Label htmlFor={`desc-${index}`}>描述</Label>
                    <Textarea
                      id={`desc-${index}`}
                      value={project.description || ''}
                      onChange={e => updateProject(index, 'description', e.target.value)}
                      placeholder="请输入工程描述（可选）"
                      maxLength={500}
                      rows={2}
                    />
                  </div>

                  {/* Tasks */}
                  {project.tasks && project.tasks.length > 0 && (
                    <div className="space-y-2">
                      <Label>任务列表</Label>
                      <div className="space-y-2 pl-4">
                        {project.tasks.map((task, ti) => (
                          <div key={ti} className="flex items-start gap-2 text-sm">
                            <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                            <div className="flex-1">
                              <div className="font-medium">{task.title}</div>
                              {task.description && <div className="text-xs text-muted-foreground">{task.description}</div>}
                              <Badge variant="outline" className="text-[10px] h-4 mt-1">{task.type}</Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Deliverables */}
                  {project.deliverables && project.deliverables.length > 0 && (
                    <div className="space-y-2">
                      <Label>交付物</Label>
                      <div className="space-y-2">
                        {project.deliverables.map((d: string, di: number) => (
                          <div key={di} className="flex items-center gap-2">
                            <FileText className="w-3 h-3 text-muted-foreground shrink-0" />
                            <Input
                              value={d}
                              onChange={e => {
                                const newDels = [...(project.deliverables || [])]
                                newDels[di] = e.target.value
                                updateProject(index, 'deliverables', newDels)
                              }}
                              placeholder="交付物描述"
                              className="text-sm"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          )
        })}
      </div>

      {/* Actions */}
      <div className="flex justify-between items-center pb-8">
        <Button variant="outline" onClick={handleModify}>
          <Plus className="w-4 h-4 mr-1.5" />
          修改分解
        </Button>
        <div className="flex gap-3">
          <Button onClick={handleModify}>
            <Plus className="w-4 h-4 mr-1.5" />
            返回编辑
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={projects.length === 0 || !isValid()}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <CheckCircle className="w-4 h-4 mr-1.5" />
            确认并开始执行
          </Button>
        </div>
      </div>
    </div>
  )
}
