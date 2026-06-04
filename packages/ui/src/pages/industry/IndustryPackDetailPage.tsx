/**
 * Industry Pack Detail Page
 * Sprint 115 F115-1: 行业包详情页
 * 8 个 Tab：概览/能力标签/场景模板/提示词模板/SOP/检查清单/参考数据/版本历史
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft, Loader2, Package, Tag, Layout, FileText,
  ClipboardCheck, ListChecks, Database, History, RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/ui/tabs'
import { industryPacksApi, IndustryPack, PackStatus, IndustryTag, industryTagsApi } from '@/shared/utils/industryTagsApi'
import {
  promptTemplatesApi, PromptTemplate,
  sopsApi, SOP,
  checklistsApi, Checklist,
  referenceDataApi, ReferenceData,
} from '@/shared/utils/api'
import IndustryPackVersionsTab from './IndustryPackVersionsTab'

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  published: { label: '已发布', color: 'bg-green-100 text-green-700' },
  deprecated: { label: '已废弃', color: 'bg-red-100 text-red-700' },
}

interface PackDetailData {
  pack: IndustryPack | null
  tags: IndustryTag[]
  promptTemplates: PromptTemplate[]
  sops: SOP[]
  checklists: Checklist[]
  referenceData: ReferenceData[]
  loading: boolean
}

export default function IndustryPackDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<PackDetailData>({
    pack: null,
    tags: [],
    promptTemplates: [],
    sops: [],
    checklists: [],
    referenceData: [],
    loading: true,
  })
  const [activeTab, setActiveTab] = useState('overview')
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async () => {
    if (!id) return
    setData((d) => ({ ...d, loading: true }))
    try {
      const [pack, tags, prompts, sops, checklists, refData] = await Promise.allSettled([
        industryPacksApi.get(id),
        industryTagsApi.list({ industry: id, page_size: 100 }),
        promptTemplatesApi.list({ pack_id: id }),
        sopsApi.list({ pack_id: id }),
        checklistsApi.list({ pack_id: id }),
        referenceDataApi.list({ pack_id: id }),
      ])

      setData({
        pack: pack.status === 'fulfilled' ? pack.value : null,
        tags: tags.status === 'fulfilled' ? tags.value.items || tags.value : [],
        promptTemplates:
          prompts.status === 'fulfilled' ? prompts.value.items || prompts.value : [],
        sops: sops.status === 'fulfilled' ? sops.value.items || sops.value : [],
        checklists:
          checklists.status === 'fulfilled' ? checklists.value.items || checklists.value : [],
        referenceData:
          refData.status === 'fulfilled' ? refData.value.items || refData.value : [],
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
          <TabsTrigger value="tags">
            <Tag className="w-3.5 h-3.5 mr-1" /> 能力标签
          </TabsTrigger>
          <TabsTrigger value="scenarios">
            <Layout className="w-3.5 h-3.5 mr-1" /> 场景模板
          </TabsTrigger>
          <TabsTrigger value="prompts">
            <FileText className="w-3.5 h-3.5 mr-1" /> 提示词模板
          </TabsTrigger>
          <TabsTrigger value="sops">
            <ClipboardCheck className="w-3.5 h-3.5 mr-1" /> SOP
          </TabsTrigger>
          <TabsTrigger value="checklists">
            <ListChecks className="w-3.5 h-3.5 mr-1" /> 检查清单
          </TabsTrigger>
          <TabsTrigger value="reference">
            <Database className="w-3.5 h-3.5 mr-1" /> 参考数据
          </TabsTrigger>
          <TabsTrigger value="versions">
            <History className="w-3.5 h-3.5 mr-1" /> 版本历史
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <Database className="w-4 h-4" /> 技能数
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{pack.skills_count ?? 0}</p>
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
                  <span>{pack.created_at ? new Date(pack.created_at).toLocaleString('zh-CN') : '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">更新时间</span>
                  <span>{pack.updated_at ? new Date(pack.updated_at).toLocaleString('zh-CN') : '-'}</span>
                </div>
              </CardContent>
            </Card>
          </div>
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

        {/* Prompts Tab */}
        <TabsContent value="prompts">
          <PromptsTab templates={data.promptTemplates} />
        </TabsContent>

        {/* SOPs Tab */}
        <TabsContent value="sops">
          <SOPsTab sops={data.sops} />
        </TabsContent>

        {/* Checklists Tab */}
        <TabsContent value="checklists">
          <ChecklistsTab checklists={data.checklists} />
        </TabsContent>

        {/* Reference Data Tab */}
        <TabsContent value="reference">
          <ReferenceTab data={data.referenceData} />
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

function PromptsTab({ templates }: { templates: PromptTemplate[] }) {
  if (templates.length === 0) {
    return (
      <Card>
        <CardContent className="pt-4">
          <p className="text-center text-gray-400 py-8 text-sm">暂无提示词模板</p>
        </CardContent>
      </Card>
    )
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {templates.length} 个模板</div>
        <div className="space-y-3">
          {templates.map((t) => (
            <div key={t.id} className="p-3 border rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{t.name}</span>
                <span className="text-xs text-gray-400 font-mono">{t.id}</span>
              </div>
              {t.description && (
                <p className="text-xs text-gray-500 mb-2">{t.description}</p>
              )}
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto max-h-24 text-gray-600">
                {t.content}
              </pre>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function SOPsTab({ sops }: { sops: SOP[] }) {
  if (sops.length === 0) {
    return (
      <Card>
        <CardContent className="pt-4">
          <p className="text-center text-gray-400 py-8 text-sm">暂无 SOP</p>
        </CardContent>
      </Card>
    )
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {sops.length} 个 SOP</div>
        <div className="space-y-3">
          {sops.map((sop) => (
            <div key={sop.id} className="p-3 border rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{sop.name}</span>
                <span className="text-xs text-gray-400 font-mono">{sop.id}</span>
              </div>
              {sop.description && (
                <p className="text-xs text-gray-500 mb-2">{sop.description}</p>
              )}
              <div className="text-xs text-gray-500">
                {sop.steps?.length || 0} 个步骤
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ChecklistsTab({ checklists }: { checklists: Checklist[] }) {
  if (checklists.length === 0) {
    return (
      <Card>
        <CardContent className="pt-4">
          <p className="text-center text-gray-400 py-8 text-sm">暂无检查清单</p>
        </CardContent>
      </Card>
    )
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {checklists.length} 个检查清单</div>
        <div className="space-y-3">
          {checklists.map((cl) => (
            <div key={cl.id} className="p-3 border rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{cl.name}</span>
                <span className="text-xs text-gray-400 font-mono">{cl.id}</span>
              </div>
              {cl.description && (
                <p className="text-xs text-gray-500 mb-2">{cl.description}</p>
              )}
              <div className="text-xs text-gray-500">
                {cl.items?.length || 0} 个检查项
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ReferenceTab({ data }: { data: ReferenceData[] }) {
  if (data.length === 0) {
    return (
      <Card>
        <CardContent className="pt-4">
          <p className="text-center text-gray-400 py-8 text-sm">暂无参考数据</p>
        </CardContent>
      </Card>
    )
  }
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs text-gray-400 mb-3">共 {data.length} 条参考数据</div>
        <div className="space-y-3">
          {data.map((rd) => (
            <div key={rd.id} className="p-3 border rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{rd.name}</span>
                <Badge variant="outline" className="text-xs">
                  {rd.data_type}
                </Badge>
              </div>
              {rd.description && (
                <p className="text-xs text-gray-500 mb-2">{rd.description}</p>
              )}
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto max-h-24 text-gray-600">
                {typeof rd.content === 'string'
                  ? rd.content
                  : JSON.stringify(rd.content, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
