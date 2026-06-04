/**
 * Industry Tags Library Page
 * Sprint 93: 能力标签库
 * Sprint 98 F98-1: 生命周期状态展示（active/deprecated/replaced_by）
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, Search, RefreshCw, Loader2, ChevronDown,
  Plus, ExternalLink, Wrench, BookOpen, X, AlertTriangle
} from 'lucide-react'
import { CreateTagDialog } from './industry/CreateTagDialog'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/ui/tabs'
import {
  industryTagsApi,
  IndustryTag,
  TagDimension,
  TagLevel,
} from '@/shared/utils/industryTagsApi'

const DIMENSION_LABELS: Record<string, string> = {
  business: '业务',
  professional: '专业',
  technical: '技术',
  management: '管理',
}

const DIMENSION_COLORS: Record<string, string> = {
  business: 'bg-blue-100 text-blue-800',
  professional: 'bg-purple-100 text-purple-800',
  technical: 'bg-orange-100 text-orange-800',
  management: 'bg-green-100 text-green-800',
}

const LEVEL_LABELS: Record<string, string> = {
  basic: '基础',
  intermediate: '进阶',
  advanced: '高级',
}

// Status badge styles
const STATUS_STYLES: Record<string, string> = {
  active: 'bg-green-100 text-green-800 border-green-200',
  deprecated: 'bg-gray-100 text-gray-800 border-gray-200',
  replaced_by: 'bg-orange-100 text-orange-800 border-orange-200',
}

const STATUS_LABELS: Record<string, string> = {
  active: '活跃',
  deprecated: '已废弃',
  replaced_by: '已替换',
}

// Card row style for deprecated
const DEPRECATED_ROW_CLASS = 'bg-gray-50 border-gray-200'

// Border style for replaced
const REPLACED_BORDER_CLASS = 'border-orange-300 border-2'

interface TagReferences {
  tag_id: string
  task_count: number
  scenario_count: number
  agent_count: number
  total_count: number
}

export default function IndustryTagsPage() {
  const [tags, setTags] = useState<IndustryTag[]>([])
  const [industries, setIndustries] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // Filters
  const [industryFilter, setIndustryFilter] = useState<string>('all')
  const [dimensionFilter, setDimensionFilter] = useState<string>('all')
  const [levelFilter, setLevelFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  // Detail modal
  const [selectedTag, setSelectedTag] = useState<IndustryTag | null>(null)
  const [tagReferences, setTagReferences] = useState<TagReferences | null>(null)
  const [referencesLoading, setReferencesLoading] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false)

  // Replaced-by tag name cache
  const [tagNameCache, setTagNameCache] = useState<Record<string, string>>({})

  const loadIndustries = async () => {
    try {
      const list = await industryTagsApi.listIndustries()
      setIndustries(list)
    } catch (e) {
      console.error('Failed to load industries', e)
    }
  }

  const loadTags = async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize }
      if (industryFilter && industryFilter !== 'all') params.industry = industryFilter
      if (dimensionFilter && dimensionFilter !== 'all') params.dimension = dimensionFilter
      if (levelFilter && levelFilter !== 'all') params.level = levelFilter
      if (search) params.search = search

      const res = await industryTagsApi.list(params as any)
      setTags(res.items)
      setTotal(res.total)
    } catch (e) {
      console.error('Failed to load tags', e)
    } finally {
      setLoading(false)
    }
  }

  // Load tag name for replaced_by tag IDs
  const loadTagName = useCallback(async (tagId: string) => {
    if (tagNameCache[tagId] || tagId === '__none__') return
    try {
      const tag = await industryTagsApi.get(tagId)
      setTagNameCache(prev => ({ ...prev, [tagId]: tag.tag_name }))
    } catch (e) {
      setTagNameCache(prev => ({ ...prev, [tagId]: tagId }))
    }
  }, [tagNameCache])

  useEffect(() => {
    loadIndustries()
  }, [])

  useEffect(() => {
    loadTags()
  }, [industryFilter, dimensionFilter, levelFilter, search, page])

  // Pre-load names for all replaced_by targets across visible tags
  useEffect(() => {
    tags.forEach(tag => {
      if (tag.status === 'deprecated' && tag.replaced_by) {
        loadTagName(tag.replaced_by)
      }
    })
  }, [tags, loadTagName])

  const openTagDetail = async (tag: IndustryTag) => {
    setSelectedTag(tag)
    setModalLoading(true)
    setTagReferences(null)
    try {
      const refs = await industryTagsApi.getReferences(tag.id)
      setTagReferences(refs)
    } catch (e) {
      console.error('Failed to load references', e)
    } finally {
      setModalLoading(false)
    }
  }

  const closeTagDetail = () => {
    setSelectedTag(null)
    setTagReferences(null)
  }

  const openReplacedTag = async (replacedById: string) => {
    setModalLoading(true)
    setTagReferences(null)
    try {
      const tag = await industryTagsApi.get(replacedById)
      setSelectedTag(tag)
      try {
        const refs = await industryTagsApi.getReferences(replacedById)
        setTagReferences(refs)
      } catch (e) {
        // ignore
      }
    } catch (e) {
      console.error('Failed to open replaced tag', e)
    } finally {
      setModalLoading(false)
    }
  }

  const dimensionGroups = ['business', 'professional', 'technical', 'management']

  const filteredByDimension = (dimension: string) =>
    tags.filter(t => t.dimension === dimension)

  return (
    <>
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link to="/scenarios/center" className="text-gray-400 hover:text-gray-600">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="text-2xl font-semibold">能力标签库</h1>
            <Badge variant="outline">{total} 个标签</Badge>
          </div>
          <p className="text-gray-500 text-sm ml-7">
            智能体协作的能力标准体系
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadTags}>
            <RefreshCw className="w-4 h-4 mr-1" /> 刷新
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="w-4 h-4 mr-1" /> 新建标签
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">行业:</span>
              <Select value={industryFilter} onValueChange={setIndustryFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="全部行业" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部行业</SelectItem>
                  {industries.map(ind => (
                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">维度:</span>
              <Select value={dimensionFilter} onValueChange={setDimensionFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="全部维度" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部维度</SelectItem>
                  <SelectItem value="business">业务</SelectItem>
                  <SelectItem value="professional">专业</SelectItem>
                  <SelectItem value="technical">技术</SelectItem>
                  <SelectItem value="management">管理</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">级别:</span>
              <Select value={levelFilter} onValueChange={setLevelFilter}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="全部级别" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部级别</SelectItem>
                  <SelectItem value="basic">基础</SelectItem>
                  <SelectItem value="intermediate">进阶</SelectItem>
                  <SelectItem value="advanced">高级</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="搜索标签名称或描述..."
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1) }}
                  className="pl-9"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Content */}
      {!loading && (
        <>
          {/* Filtered list view (when filters active) */}
          {(dimensionFilter !== 'all' || industryFilter !== 'all' || levelFilter !== 'all' || search) && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  搜索结果
                  {dimensionFilter !== 'all' && <span className="ml-2 font-normal text-gray-500">维度: {DIMENSION_LABELS[dimensionFilter]}</span>}
                  {industryFilter !== 'all' && <span className="ml-2 font-normal text-gray-500">行业: {industryFilter}</span>}
                  {levelFilter !== 'all' && <span className="ml-2 font-normal text-gray-500">级别: {LEVEL_LABELS[levelFilter]}</span>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {tags.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">未找到匹配的标签</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {tags.map(tag => (
                      <TagCard
                        key={tag.id}
                        tag={tag}
                        tagNameCache={tagNameCache}
                        onTagClick={openTagDetail}
                        onReplacedTagClick={openReplacedTag}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Dimension tabs view (when no filter) */}
          {dimensionFilter === 'all' && industryFilter === 'all' && levelFilter === 'all' && !search && (
            <Tabs defaultValue="professional">
              <TabsList className="mb-4">
                {dimensionGroups.map(dim => (
                  <TabsTrigger key={dim} value={dim}>
                    {DIMENSION_LABELS[dim]}
                    <span className="ml-1.5 text-xs opacity-60">
                      ({tags.filter(t => t.dimension === dim).length})
                    </span>
                  </TabsTrigger>
                ))}
              </TabsList>

              {dimensionGroups.map(dim => (
                <TabsContent key={dim} value={dim}>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {filteredByDimension(dim).map(tag => (
                      <TagCard
                        key={tag.id}
                        tag={tag}
                        tagNameCache={tagNameCache}
                        onTagClick={openTagDetail}
                        onReplacedTagClick={openReplacedTag}
                      />
                    ))}
                    {filteredByDimension(dim).length === 0 && (
                      <div className="col-span-3 text-center py-8 text-gray-400">
                        暂无 {DIMENSION_LABELS[dim]} 维度的标签
                      </div>
                    )}
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          )}

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex justify-center gap-2 mt-6">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
              >
                上一页
              </Button>
              <span className="text-sm text-gray-500 py-2 px-3">
                {page} / {Math.ceil(total / pageSize)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(total / pageSize)}
                onClick={() => setPage(p => p + 1)}
              >
                下一页
              </Button>
            </div>
          )}
        </>
      )}

      {/* Tag Detail Modal */}
      {selectedTag && (
        <TagDetailModal
          tag={selectedTag}
          references={tagReferences}
          loading={referencesLoading || modalLoading}
          onClose={closeTagDetail}
          onNavigateToTag={openReplacedTag}
        />
      )}
    </div>
  <CreateTagDialog
    isOpen={createOpen}
    onClose={() => setCreateOpen(false)}
    onSuccess={(newTag) => {
      setTags((prev) => [newTag, ...prev])
      setTotal((prev) => prev + 1)
    }}
  />
  </>
  )
}

interface TagCardProps {
  tag: IndustryTag
  tagNameCache: Record<string, string>
  onTagClick: (tag: IndustryTag) => void
  onReplacedTagClick: (tagId: string) => void
}

function TagCard({ tag, tagNameCache, onTagClick, onReplacedTagClick }: TagCardProps) {
  const [expanded, setExpanded] = useState(false)

  // Determine card styling based on status
  const isDeprecated = tag.status === 'deprecated'
  const isReplaced = tag.status === 'replaced_by'

  let cardClass = 'border rounded-lg p-3 hover:border-blue-300 transition-colors cursor-pointer'
  if (isDeprecated) cardClass += ' bg-gray-50'
  if (isReplaced) cardClass += ' border-orange-300 border-2'

  return (
    <div
      className={cardClass}
      onClick={() => {
        setExpanded(!expanded)
        if (expanded) onTagClick(tag)
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono truncate">{tag.id}</code>
            <Badge className={DIMENSION_COLORS[tag.dimension]} variant="secondary">
              {DIMENSION_LABELS[tag.dimension]}
            </Badge>
            <Badge variant="outline">{LEVEL_LABELS[tag.level]}</Badge>
            {/* Status badge */}
            <Badge
              className={`border ${STATUS_STYLES[tag.status] || ''}`}
              variant="secondary"
            >
              {STATUS_LABELS[tag.status] || tag.status}
            </Badge>
          </div>
          <h3 className="font-medium text-sm mt-1">{tag.tag_name}</h3>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </div>

      <p className="text-xs text-gray-500 line-clamp-2">{tag.description}</p>

      {/* Deprecated replacement hint */}
      {isDeprecated && tag.replaced_by && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <button
            className="text-xs text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
            onClick={(e) => {
              e.stopPropagation()
              onReplacedTagClick(tag.replaced_by!)
            }}
          >
            <AlertTriangle className="w-3 h-3" />
            建议替换为 {tagNameCache[tag.replaced_by] || tag.replaced_by} →
          </button>
        </div>
      )}

      {/* Replaced-by hint */}
      {isReplaced && tag.replaced_by && (
        <div className="mt-2 pt-2 border-t border-orange-200">
          <button
            className="text-xs text-orange-600 hover:text-orange-800 hover:underline flex items-center gap-1"
            onClick={(e) => {
              e.stopPropagation()
              onReplacedTagClick(tag.replaced_by!)
            }}
          >
            已替换为 {tagNameCache[tag.replaced_by] || tag.replaced_by} →
          </button>
        </div>
      )}

      {expanded && (
        <div className="mt-3 pt-3 border-t space-y-2 text-xs" onClick={e => e.stopPropagation()}>
          {tag.prerequisites.length > 0 && (
            <div>
              <span className="text-gray-500">前置依赖：</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {tag.prerequisites.map(p => (
                  <Badge key={p} variant="outline">{p}</Badge>
                ))}
              </div>
            </div>
          )}
          {tag.tools.length > 0 && (
            <div>
              <span className="text-gray-500">关联工具：</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {tag.tools.map(t => (
                  <Badge key={t} variant="outline" className="bg-orange-50">{t}</Badge>
                ))}
              </div>
            </div>
          )}
          {tag.examples.length > 0 && (
            <div>
              <span className="text-gray-500">使用示例：</span>
              <ul className="mt-1 space-y-0.5 text-gray-600">
                {tag.examples.map((ex, i) => (
                  <li key={i} className="flex items-start gap-1">
                    <span className="text-gray-400">•</span>
                    <span>{ex}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {tag.tag_name_en && (
            <div className="text-gray-400 italic">{tag.tag_name_en}</div>
          )}
          {/* Click for full details */}
          <div className="pt-1">
            <button
              className="text-xs text-blue-500 hover:text-blue-700"
              onClick={(e) => {
                e.stopPropagation()
                onTagClick(tag)
              }}
            >
              查看详情 v{tag.version_major}.{tag.version_minor}.{tag.version_patch}
            </button>
          </div>
        </div>
      )}
      </div>
  )
}

interface TagDetailModalProps {
  tag: IndustryTag
  references: TagReferences | null
  loading: boolean
  onClose: () => void
  onNavigateToTag: (tagId: string) => void
}

function TagDetailModal({ tag, references, loading, onClose, onNavigateToTag }: TagDetailModalProps) {
  // Compute version string
  const versionStr = `v${tag.version_major}.${tag.version_minor}.${tag.version_patch}`

  // Gather scenarios with non-zero counts from references
  const activeScenarios: { label: string; count: number }[] = []
  if (references) {
    if (references.task_count > 0) activeScenarios.push({ label: '任务', count: references.task_count })
    if (references.scenario_count > 0) activeScenarios.push({ label: '场景', count: references.scenario_count })
    if (references.agent_count > 0) activeScenarios.push({ label: 'Agent', count: references.agent_count })
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose} />
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div className="flex-1 min-w-0 pr-4">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono">{tag.id}</code>
              <Badge className={DIMENSION_COLORS[tag.dimension]} variant="secondary">
                {DIMENSION_LABELS[tag.dimension]}
              </Badge>
              <Badge variant="outline">{LEVEL_LABELS[tag.level]}</Badge>
              <Badge className={`border ${STATUS_STYLES[tag.status] || ''}`} variant="secondary">
                {STATUS_LABELS[tag.status] || tag.status}
              </Badge>
            </div>
            <h2 className="text-lg font-semibold">{tag.tag_name}</h2>
            {tag.tag_name_en && (
              <p className="text-sm text-gray-500 italic">{tag.tag_name_en}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 text-sm">
          {/* Version and Status row */}
          <div className="flex items-center gap-3">
            <span className="text-gray-500">版本：</span>
            <span className="font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              {versionStr}
            </span>
            <span className="text-gray-400 text-xs">行业：{tag.industry}</span>
          </div>

          {/* Description */}
          <div>
            <div className="text-gray-500 mb-1">描述</div>
            <p className="text-gray-700">{tag.description}</p>
          </div>

          {/* Replaced By */}
          {tag.replaced_by && (
            <div className="flex items-start gap-2">
              <span className="text-gray-500 shrink-0">已被替换为：</span>
              <button
                className="text-orange-600 hover:text-orange-800 hover:underline text-left"
                onClick={() => onNavigateToTag(tag.replaced_by!)}
              >
                {tag.replaced_by}
              </button>
            </div>
          )}

          {/* Prerequisites */}
          {tag.prerequisites.length > 0 && (
            <div>
              <span className="text-gray-500">前置依赖：</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {tag.prerequisites.map(p => (
                  <Badge key={p} variant="outline">{p}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Tools */}
          {tag.tools.length > 0 && (
            <div>
              <span className="text-gray-500">关联工具：</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {tag.tools.map(t => (
                  <Badge key={t} variant="outline" className="bg-orange-50">{t}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Examples */}
          {tag.examples.length > 0 && (
            <div>
              <span className="text-gray-500">使用示例：</span>
              <ul className="mt-1 space-y-1 text-gray-600">
                {tag.examples.map((ex, i) => (
                  <li key={i} className="flex items-start gap-1">
                    <span className="text-gray-400 mt-0.5">•</span>
                    <span>{ex}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* References */}
          <div className="border-t border-gray-100 pt-4">
            <div className="text-gray-500 mb-2">被引用数</div>
            {loading ? (
              <div className="flex items-center gap-2 text-gray-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">加载中...</span>
              </div>
            ) : references ? (
              <div className="space-y-2">
                {/* Total count */}
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-blue-600">{references.total_count}</span>
                  <span className="text-gray-500 text-sm">次被引用</span>
                </div>
                {/* Breakdown */}
                <div className="flex gap-3 text-xs text-gray-600">
                  {references.task_count > 0 && (
                    <span className="bg-blue-50 px-2 py-1 rounded border border-blue-100">
                      任务: {references.task_count}
                    </span>
                  )}
                  {references.scenario_count > 0 && (
                    <span className="bg-purple-50 px-2 py-1 rounded border border-purple-100">
                      场景: {references.scenario_count}
                    </span>
                  )}
                  {references.agent_count > 0 && (
                    <span className="bg-green-50 px-2 py-1 rounded border border-green-100">
                      Agent: {references.agent_count}
                    </span>
                  )}
                </div>
                {/* Active scenarios */}
                {activeScenarios.length > 0 && (
                  <div className="mt-2">
                    <div className="text-xs text-gray-400 mb-1">使用场景：</div>
                    <div className="flex flex-wrap gap-1">
                      {activeScenarios.map(s => (
                        <Badge key={s.label} variant="outline" className="bg-gray-50">
                          {s.label} ({s.count})
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-gray-400">暂无引用数据</div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-gray-100 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>
      </>
  )
}
