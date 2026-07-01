/**
 * Industry Pack Detail Page
 * Sprint 115 F115-1: 行业包详情页
 * 7 个 Tab：概览/知识库/能力标签/场景模板/智能体方案/技能/版本历史
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Loader2, Package, Tag, Layout, Database, History, RefreshCw, BookOpen,
  Plus, Pencil, Trash2, Cpu, Wrench,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import { Label } from '@/shared/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/ui/tabs'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/shared/components/ui/dialog'
import { industryPacksApi, IndustryPack, PackStatus, IndustryTag, industryTagsApi } from '@/shared/utils/industryTagsApi'
import { knowledgeApi, KnowledgeEntry, KnowledgeCreate, KnowledgeUpdate } from '@/shared/utils/api'
import { agentSchemesApi, AgentScheme, AgentSchemeCreate, AgentSchemeUpdate, packSkillsApi, PackSkill } from '@/shared/utils/api'
import IndustryPackVersionsTab from './IndustryPackVersionsTab'

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  active: { label: '活跃', color: 'bg-green-100 text-green-700' },
  published: { label: '已发布', color: 'bg-green-100 text-green-700' },
  deprecated: { label: '已废弃', color: 'bg-red-100 text-red-700' },
}

interface PackDetailData {
  pack: IndustryPack | null
  tags: IndustryTag[]
  loading: boolean
}

export default function IndustryPackDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<PackDetailData>({
    pack: null,
    tags: [],
    loading: true,
  })
  const [activeTab, setActiveTab] = useState('overview')
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async () => {
    if (!id) return
    setData((d) => ({ ...d, loading: true }))
    try {
      const [pack, tags] = await Promise.allSettled([
        industryPacksApi.get(id),
        industryTagsApi.list({ industry: id, page_size: 100 }),
      ])

      setData({
        pack: pack.status === 'fulfilled' ? pack.value : null,
        tags: tags.status === 'fulfilled' ? tags.value.items || tags.value : [],
        loading: false,
      })
    } catch {
      setData((d) => ({ ...d, loading: false }))
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadData()
    setRefreshing(false)
  }

  useEffect(() => {
    loadData()
  }, [id])

  const { pack, loading } = data

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!pack) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center">
            <Package className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 text-lg">找不到行业包</p>
            <Button variant="link" onClick={() => navigate('/industry/packs')}>
              返回列表
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const statusInfo = STATUS_LABELS[pack.status] || STATUS_LABELS.draft

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <button
              onClick={() => navigate('/industry/packs')}
              className="text-gray-400 hover:text-gray-600"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <h1 className="text-2xl font-semibold">{pack.name}</h1>
            <Badge className={statusInfo.color} variant="secondary">
              {statusInfo.label}
            </Badge>
          </div>
          <p className="text-gray-500 text-sm ml-7 font-mono">
            {pack.id} · v{pack.version} · {pack.industry}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      {/* Description */}
      {pack.description && (
        <Card className="mb-6">
          <CardContent className="pt-4">
            <p className="text-sm text-gray-600">{pack.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="overview">
            <Package className="w-3.5 h-3.5 mr-1" /> 概览
          </TabsTrigger>
          <TabsTrigger value="knowledge">
            <BookOpen className="w-3.5 h-3.5 mr-1" /> 知识库
          </TabsTrigger>
          <TabsTrigger value="tags">
            <Tag className="w-3.5 h-3.5 mr-1" /> 能力标签
          </TabsTrigger>
          <TabsTrigger value="scenarios">
            <Layout className="w-3.5 h-3.5 mr-1" /> 场景模板
          </TabsTrigger>
          <TabsTrigger value="agent-schemes">
            <BookOpen className="w-3.5 h-3.5 mr-1" /> 智能体方案
          </TabsTrigger>
          <TabsTrigger value="skills">
            <Wrench className="w-3.5 h-3.5 mr-1" /> 技能
          </TabsTrigger>
          <TabsTrigger value="versions">
            <History className="w-3.5 h-3.5 mr-1" /> 版本历史
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                  <BookOpen className="w-4 h-4" /> 知识库
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.knowledge_count ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                  <Tag className="w-4 h-4" /> 能力标签
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.tags_count ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                  <Layout className="w-4 h-4" /> 场景模板
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.scenarios_count ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                  <BookOpen className="w-4 h-4" /> 智能体方案
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.agent_schemes_count ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                  <Database className="w-4 h-4" /> 技能
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.skills_count ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500 flex items-center gap-2">
                  <History className="w-4 h-4" /> 版本历史
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.versions_count ?? 0}</p>
              </CardContent>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500">包信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">ID</span>
                  <span className="font-mono text-xs">{pack.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">版本</span>
                  <span>v{pack.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">行业</span>
                  <span>{pack.industry}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">状态</span>
                  <Badge className={statusInfo.color} variant="secondary">
                    {statusInfo.label}
                  </Badge>
                </div>
                {pack.pack_type && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">类型</span>
                    <span>{pack.pack_type === 'standard' ? '标准包' : '定制包'}</span>
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-gray-500">时间</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">创建时间</span>
                  <span>{pack.created_at ? new Date(pack.created_at * 1000).toLocaleString('zh-CN') : '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">更新时间</span>
                  <span>{pack.updated_at ? new Date(pack.updated_at * 1000).toLocaleString('zh-CN') : '-'}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Knowledge Tab */}
        <TabsContent value="knowledge">
          {id && <KnowledgeTab packId={id} packName={pack.name} />}
        </TabsContent>

        {/* Tags Tab */}
        <TabsContent value="tags">
          <TagsTab tags={data.tags} />
        </TabsContent>

        {/* Scenarios Tab */}
        <TabsContent value="scenarios">
          <Card>
            <CardContent className="pt-4">
              {pack.scenarios_count === 0 ? (
                <p className="text-center text-gray-400 py-8 text-sm">暂无场景模板</p>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-gray-500">
                    共 {pack.scenarios_count} 个场景模板（详情场景列表页查看）
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Agent Schemes Tab */}
        <TabsContent value="agent-schemes">
          {id && <AgentSchemesTab packId={id} packName={pack.name} />}
        </TabsContent>

        {/* Skills Tab (Sprint 116) */}
        <TabsContent value="skills">
          {id && <SkillsTab packId={id} />}
        </TabsContent>

        {/* Versions Tab */}
        <TabsContent value="versions">
          {id && <IndustryPackVersionsTab packId={id} />}
        </TabsContent>
      </Tabs>
    </div>
  )
}

/* ==================== Sub-Tab Components ==================== */

function TagsTab({ tags }: { tags: IndustryTag[] }) {
  if (tags.length === 0) {
    return (
      <Card>
        <CardContent className="pt-4">
          <p className="text-center text-gray-400 py-8 text-sm">暂无能力标签</p>
        </CardContent>
      </Card>
    )
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {tags.length} 个标签</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {tags.map((tag) => (
            <div key={tag.id} className="p-3 border rounded-lg hover:bg-gray-50">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{tag.tag_name}</span>
                <Badge variant="outline" className="text-xs">
                  {tag.dimension}
                </Badge>
              </div>
              <p className="text-xs text-gray-500 line-clamp-2">
                {tag.description}
              </p>
              <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                <span>{tag.level}</span>
                {tag.status === 'deprecated' && (
                  <Badge variant="destructive" className="text-xs px-1">
                    已废弃
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// Removed: PromptsTab, SOPsTab, ChecklistsTab, ReferenceTab (orphaned content types)

/* ==================== Knowledge Tab (Sprint 75 Phase 2) ==================== */

function KnowledgeTab({ packId, packName }: { packId: string; packName: string }) {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingEntry, setEditingEntry] = useState<KnowledgeEntry | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  // Form state
  const [formName, setFormName] = useState('')
  const [formCategory, setFormCategory] = useState('general')
  const [formContent, setFormContent] = useState('')
  const [formVersion, setFormVersion] = useState('1.0.0')
  const [formTags, setFormTags] = useState('')

  const loadEntries = () => {
    if (!packId) return
    setLoading(true)
    knowledgeApi.list({ pack_id: packId, page_size: 100 })
      .then((res) => {
        setEntries(res.items || [])
        setTotal(res.total || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadEntries() }, [packId])

  const openCreate = () => {
    setEditingEntry(null)
    setFormName('')
    setFormCategory('general')
    setFormContent('')
    setFormVersion('1.0.0')
    setFormTags('')
    setDialogOpen(true)
  }

  const openEdit = (entry: KnowledgeEntry) => {
    setEditingEntry(entry)
    setFormName(entry.name)
    setFormCategory(entry.category || 'general')
    setFormContent(entry.content || '')
    setFormVersion(entry.version || '1.0.0')
    setFormTags((entry.tags || []).join(', '))
    setDialogOpen(true)
  }

  const handleSave = async () => {
    if (!formName.trim()) return
    setSaving(true)
    try {
      const tags = formTags.split(',').map(t => t.trim()).filter(Boolean)
      if (editingEntry) {
        const data: KnowledgeUpdate = {
          name: formName.trim(),
          category: formCategory,
          content: formContent.trim() || undefined,
          version: formVersion.trim() || undefined,
          tags,
        }
        await knowledgeApi.update(editingEntry.id, data)
      } else {
        const data: KnowledgeCreate = {
          pack_id: packId,
          name: formName.trim(),
          category: formCategory,
          content: formContent.trim() || undefined,
          version: formVersion.trim() || undefined,
          tags,
        }
        await knowledgeApi.create(data)
      }
      setDialogOpen(false)
      loadEntries()
    } catch (e) {
      console.error('保存知识条目失败', e)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    setSaving(true)
    try {
      await knowledgeApi.remove(deleteId)
      setDeleteId(null)
      loadEntries()
    } catch (e) {
      console.error('删除知识条目失败', e)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <>
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs text-gray-400">共 {total} 个知识条目</span>
            <Button size="sm" variant="outline" onClick={openCreate}>
              <Plus className="w-3 h-3 mr-1" />新建知识
            </Button>
          </div>
          {entries.length === 0 ? (
            <p className="text-center text-gray-400 py-8 text-sm">暂无知识库条目</p>
          ) : (
            <div className="space-y-3">
              {entries.map((entry) => (
                <div key={entry.id} className="p-3 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{entry.name}</span>
                    <div className="flex items-center gap-1">
                      <Badge variant="outline" className="text-xs">{entry.category}</Badge>
                      <button
                        onClick={() => openEdit(entry)}
                        className="p-1 text-gray-400 hover:text-gray-600 rounded"
                        title="编辑"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => setDeleteId(entry.id)}
                        className="p-1 text-gray-400 hover:text-red-500 rounded"
                        title="删除"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  {entry.content && (
                    <p className="text-xs text-gray-500 line-clamp-2 mb-1">{entry.content}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-400">
                    <span>v{entry.version}</span>
                    {entry.tags && entry.tags.length > 0 && (
                      <span>标签: {entry.tags.join(', ')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingEntry ? '编辑知识条目' : '新建知识条目'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <Label className="text-xs">名称 *</Label>
              <Input
                value={formName}
                onChange={e => setFormName(e.target.value)}
                placeholder="知识条目名称"
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">分类</Label>
                <Input
                  value={formCategory}
                  onChange={e => setFormCategory(e.target.value)}
                  placeholder="general"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">版本</Label>
                <Input
                  value={formVersion}
                  onChange={e => setFormVersion(e.target.value)}
                  placeholder="1.0.0"
                  className="mt-1"
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">内容</Label>
              <Textarea
                value={formContent}
                onChange={e => setFormContent(e.target.value)}
                placeholder="知识内容..."
                rows={4}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs">标签（逗号分隔）</Label>
              <Input
                value={formTags}
                onChange={e => setFormTags(e.target.value)}
                placeholder="标签1, 标签2"
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSave} disabled={saving || !formName.trim()}>
              {saving ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteId} onOpenChange={v => !v && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600 py-2">确定要删除这个知识条目吗？此操作不可撤销。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={saving}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

/* ==================== Agent Schemes Tab ==================== */

function AgentSchemesTab({ packId, packName }: { packId: string; packName: string }) {
  const [entries, setEntries] = useState<AgentScheme[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  const loadEntries = () => {
    if (!packId) return
    setLoading(true)
    agentSchemesApi.list({ pack_id: packId, page_size: 100 })
      .then((res) => {
        setEntries(res.items || [])
        setTotal(res.total || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadEntries() }, [packId])

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {total} 个智能体方案</div>
        {entries.length === 0 ? (
          <p className="text-center text-gray-400 py-8 text-sm">暂无智能体方案</p>
        ) : (
          <div className="space-y-3">
            {entries.map((entry) => (
              <div key={entry.id} className="p-3 border rounded-lg hover:bg-gray-50">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{entry.name}</span>
                </div>
                {entry.description && (
                  <p className="text-xs text-gray-500 line-clamp-2 mb-1">{entry.description}</p>
                )}
                {entry.roles && entry.roles.length > 0 && (
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                    <span>{entry.roles.length} 个角色</span>
                  </div>
                )}
                <div className="mt-2 text-xs text-gray-500">
                  <span className="font-mono">ID: {entry.id}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/* ==================== Skills Tab (Sprint 116) ==================== */

function SkillsTab({ packId }: { packId: string }) {
  const [skills, setSkills] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  const loadSkills = () => {
    if (!packId) return
    setLoading(true)
    packSkillsApi.byPack(packId)
      .then((res) => {
        setSkills(res.skills || [])
        setTotal(res.total || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadSkills() }, [packId])

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {total} 个技能</div>
        {skills.length === 0 ? (
          <p className="text-center text-gray-400 py-8 text-sm">暂无技能</p>
        ) : (
          <div className="space-y-3">
            {skills.map((skill) => (
              <div key={skill.id} className="p-3 border rounded-lg hover:bg-gray-50">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{skill.name}</span>
                  {skill.tool_dependency && (
                    <Badge variant="outline" className="text-xs">
                      {skill.tool_dependency}
                    </Badge>
                  )}
                </div>
                {skill.description && (
                  <p className="text-xs text-gray-500 line-clamp-2 mb-2">{skill.description}</p>
                )}
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  {skill.required_tags && skill.required_tags.length > 0 && (
                    <span>{skill.required_tags.length} 个所需标签</span>
                  )}
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  <span className="font-mono">ID: {skill.id}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
