/**
 * Industry Packs Page
 * Sprint 93: 能力标签库
 * Sprint 98 F98-2: 标准/定制包区分
 * Sprint 114 F114-3: 列表页增强（导入/导出按钮、版本标签、来源标识、内容统计）
 * Sprint 115 F115-2: 路由跳转（点击包名跳转详情页）
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, Search, RefreshCw, Loader2,
  Plus, Package, BookOpen, Wrench, Bot,
  Download, Upload, ExternalLink, Tag,
  FileText, ListChecks, Database, Layers,
  FileUp,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { industryPacksApi, IndustryPack, PackStatus, PackType } from '@/shared/utils/industryTagsApi'
import IndustryPackExportDialog from '@/pages/industry/IndustryPackExportDialog'
import IndustryPackImportDialog from '@/pages/industry/IndustryPackImportDialog'

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'bg-gray-100 text-gray-700' },
  published: { label: '已发布', color: 'bg-green-100 text-green-700' },
  deprecated: { label: '已废弃', color: 'bg-red-100 text-red-700' },
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  standard: { label: '标准包', color: 'bg-blue-100 text-blue-800' },
  custom: { label: '定制包', color: 'bg-purple-100 text-purple-800' },
}

interface CreatePackForm {
  name: string
  industry: string
  version: string
  description: string
  pack_type: PackType
  base_pack_id: string
}

const DEFAULT_FORM: CreatePackForm = {
  name: '',
  industry: '',
  version: '1.0.0',
  description: '',
  pack_type: 'standard',
  base_pack_id: '',
}

export default function IndustryPacksPage() {
  const [packs, setPacks] = useState<IndustryPack[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  const [industryFilter, setIndustryFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  // Create dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [form, setForm] = useState<CreatePackForm>(DEFAULT_FORM)

  // Import dialog state
  const [importDialogOpen, setImportDialogOpen] = useState(false)

  // Export dialog state
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [exportPack, setExportPack] = useState<IndustryPack | null>(null)

  // Standard packs for custom pack's base selection
  const standardPacks = packs.filter(p => p.pack_type === 'standard' || !p.pack_type)

  const loadPacks = async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: pageSize }
      if (industryFilter && industryFilter !== 'all') params.industry = industryFilter
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter

      const res = await industryPacksApi.list(params as any)
      // Client-side search filter
      let items = res.items
      if (search) {
        const q = search.toLowerCase()
        items = items.filter(p =>
          p.name.toLowerCase().includes(q) ||
          p.industry.toLowerCase().includes(q) ||
          (p.description || '').toLowerCase().includes(q)
        )
      }
      setPacks(items)
      setTotal(res.total)
    } catch (e) {
      console.error('Failed to load packs', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPacks()
  }, [industryFilter, statusFilter, page])

  const handleCreatePack = async () => {
    if (!form.name || !form.industry) return
    setCreateLoading(true)
    try {
      const payload: any = {
        name: form.name,
        industry: form.industry,
        version: form.version,
        description: form.description,
        pack_type: form.pack_type,
      }
      if (form.pack_type === 'custom' && form.base_pack_id) {
        payload.base_pack_id = form.base_pack_id
      }
      await industryPacksApi.create(payload)
      setCreateDialogOpen(false)
      setForm(DEFAULT_FORM)
      loadPacks()
    } catch (e) {
      console.error('Failed to create pack', e)
    } finally {
      setCreateLoading(false)
    }
  }

  const getBasePackName = (basePackId: string) => {
    const base = packs.find(p => p.id === basePackId)
    return base ? base.name : basePackId
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Link to="/scenarios/center" className="text-gray-400 hover:text-gray-600">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <h1 className="text-2xl font-semibold">行业包管理</h1>
            <Badge variant="outline">{total} 个包</Badge>
          </div>
          <p className="text-gray-500 text-sm ml-7">
            能力标签库 + 场景 + 技能 + 知识 的完整解决方案包
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadPacks}>
            <RefreshCw className="w-4 h-4 mr-1" /> 刷新
          </Button>
          <Button variant="outline" size="sm" onClick={() => setImportDialogOpen(true)}>
            <Upload className="w-4 h-4 mr-1" /> 导入
          </Button>
          <Button variant="default" size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-1" /> 新建行业包
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
                  <SelectItem value="chemical-emergency">化工应急</SelectItem>
                  <SelectItem value="software-development">软件开发</SelectItem>
                  <SelectItem value="healthcare">医疗健康</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">状态:</span>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="全部状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="draft">草稿</SelectItem>
                  <SelectItem value="published">已发布</SelectItem>
                  <SelectItem value="deprecated">已废弃</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="搜索行业包..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
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

      {/* Pack list */}
      {!loading && (
        <>
          {packs.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-gray-400">
                暂无行业包
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {packs.map(pack => (
                <PackCard
                  key={pack.id}
                  pack={pack}
                  onViewBasePack={(id) => {
                    const baseIdx = packs.findIndex(p => p.id === id)
                    if (baseIdx !== -1) {
                      setPage(Math.ceil((baseIdx + 1) / pageSize))
                    }
                  }}
                  onExport={(p) => {
                    setExportPack(p)
                    setExportDialogOpen(true)
                  }}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex justify-center gap-2 mt-6">
              <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                上一页
              </Button>
              <span className="text-sm text-gray-500 py-2 px-3">{page} / {Math.ceil(total / pageSize)}</span>
              <Button variant="outline" size="sm" disabled={page >= Math.ceil(total / pageSize)} onClick={() => setPage(p => p + 1)}>
                下一页
              </Button>
            </div>
          )}
        </>
      )}

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建行业包</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="pack-type">类型</Label>
              <Select
                value={form.pack_type}
                onValueChange={(v) => setForm(f => ({ ...f, pack_type: v as PackType, base_pack_id: '' }))}
              >
                <SelectTrigger id="pack-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">标准包</SelectItem>
                  <SelectItem value="custom">定制包</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {form.pack_type === 'custom' && (
              <div className="space-y-2">
                <Label htmlFor="base-pack">基于哪个标准包</Label>
                <Select
                  value={form.base_pack_id}
                  onValueChange={(v) => setForm(f => ({ ...f, base_pack_id: v }))}
                >
                  <SelectTrigger id="base-pack">
                    <SelectValue placeholder="请选择标准包" />
                  </SelectTrigger>
                  <SelectContent>
                    {standardPacks.map(sp => (
                      <SelectItem key={sp.id} value={sp.id}>{sp.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="pack-name">名称</Label>
              <Input
                id="pack-name"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="例如：化工应急行业标准包"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="pack-industry">行业</Label>
              <Select
                value={form.industry}
                onValueChange={(v) => setForm(f => ({ ...f, industry: v }))}
              >
                <SelectTrigger id="pack-industry">
                  <SelectValue placeholder="请选择行业" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="chemical-emergency">化工应急</SelectItem>
                  <SelectItem value="software-development">软件开发</SelectItem>
                  <SelectItem value="healthcare">医疗健康</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pack-version">版本</Label>
              <Input
                id="pack-version"
                value={form.version}
                onChange={e => setForm(f => ({ ...f, version: e.target.value }))}
                placeholder="1.0.0"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="pack-desc">描述</Label>
              <Input
                id="pack-desc"
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="简要描述此行业包的内容..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={createLoading}>
              取消
            </Button>
            <Button onClick={handleCreatePack} disabled={createLoading || !form.name || !form.industry}>
              {createLoading ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Export Dialog */}
      {exportPack && (
        <IndustryPackExportDialog
          open={exportDialogOpen}
          onOpenChange={setExportDialogOpen}
          pack={exportPack}
        />
      )}

      {/* Import Dialog */}
      <IndustryPackImportDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onImported={loadPacks}
      />
    </div>
  )
}

interface PackCardProps {
  pack: IndustryPack
  onViewBasePack: (basePackId: string) => void
  onExport: (pack: IndustryPack) => void
}

function PackCard({ pack, onViewBasePack, onExport }: PackCardProps) {
  const status = STATUS_LABELS[pack.status] || STATUS_LABELS.draft
  const packType = pack.pack_type || 'standard'
  const typeInfo = TYPE_LABELS[packType] || TYPE_LABELS.standard

  return (
    <Card className="hover:border-blue-300 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <Link
              to={`/industry-packs/${pack.id}`}
              className="text-base font-semibold hover:text-blue-600 transition-colors flex items-center gap-1"
            >
              {pack.name}
              <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100" />
            </Link>
            <code className="text-xs text-gray-400 font-mono">{pack.id}</code>
          </div>
          <div className="flex flex-col items-end gap-1">
            <Badge className={status.color} variant="secondary">
              {status.label}
            </Badge>
            <Badge className={typeInfo.color} variant="secondary">
              {typeInfo.label}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-500 mb-4 line-clamp-2">
          {pack.description || '暂无描述'}
        </p>

        {/* Custom pack base info */}
        {packType === 'custom' && pack.base_pack_id && (
          <div className="mb-3 px-2 py-1.5 bg-purple-50 border border-purple-100 rounded text-xs text-purple-700 flex items-center justify-between gap-1">
            <span>基于：{pack.base_pack_id}</span>
            <button
              type="button"
              className="underline hover:text-purple-900"
              onClick={() => onViewBasePack(pack.base_pack_id!)}
            >
              查看标准包
            </button>
          </div>
        )}

        {/* Content stats (F114-3: 内容统计) */}
        <div className="flex items-center gap-4 text-xs text-gray-400 mb-3">
          <div className="flex items-center gap-1">
            <Tag className="w-3.5 h-3.5" />
            <span>{pack.tags_count ?? 0} 标签</span>
          </div>
          <div className="flex items-center gap-1">
            <Bot className="w-3.5 h-3.5" />
            <span>{pack.scenarios_count ?? 0} 场景</span>
          </div>
          <div className="flex items-center gap-1">
            <Wrench className="w-3.5 h-3.5" />
            <span>{pack.skills_count ?? 0} 技能</span>
          </div>
        </div>

        {/* Version tag + source indicator (F114-3) */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs font-mono">
              v{pack.version}
            </Badge>
            <span className="text-xs text-gray-400">
              {pack.pack_type === 'custom' ? '📥 导入' : '🏠 创建'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t">
          <Link
            to={`/industry-packs/${pack.id}`}
            className="text-xs text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1"
          >
            查看详情 →
          </Link>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7 px-2"
              onClick={() => onExport(pack)}
            >
              <Download className="w-3.5 h-3.5 mr-1" />
              导出
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
