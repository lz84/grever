/**
 * CreateTagDialog - 新建能力标签
 * 字段全面、录入方便
 */
import React, { useState, useEffect } from 'react'
import { Loader2, Plus, X, Tag, Info, Wrench, BookOpen } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/shared/components/ui/dialog'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Textarea } from '@/shared/components/ui/textarea'
import { Badge } from '@/shared/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/components/ui/tabs'
import { industryTagsApi, IndustryTag, TagDimension, TagLevel } from '@/shared/utils/industryTagsApi'

interface CreateTagDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (tag: IndustryTag) => void
}

const DIMENSIONS: { value: TagDimension; label: string; desc: string }[] = [
  { value: 'business', label: '业务', desc: '业务流程、运营管理类能力' },
  { value: 'professional', label: '专业', desc: '化工、安全等专业领域知识' },
  { value: 'technical', label: '技术', desc: '工具使用、系统操作技能' },
  { value: 'management', label: '管理', desc: '团队协作、项目管理能力' },
]

const LEVELS: { value: TagLevel; label: string; desc: string }[] = [
  { value: 'basic', label: '基础', desc: '了解概念' },
  { value: 'intermediate', label: '进阶', desc: '能够独立执行' },
  { value: 'advanced', label: '高级', desc: '精通，能解决复杂问题' },
]

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
    .replace(/^-|-$/g, '')
}

export function CreateTagDialog({ isOpen, onClose, onSuccess }: CreateTagDialogProps) {
  // Basic info
  const [industry, setIndustry] = useState('')
  const [tagName, setTagName] = useState('')
  const [tagNameEn, setTagNameEn] = useState('')
  const [description, setDescription] = useState('')

  // Capability definition
  const [dimension, setDimension] = useState<TagDimension>('professional')
  const [level, setLevel] = useState<TagLevel>('basic')

  // Advanced
  const [prerequisites, setPrerequisites] = useState<string[]>([])
  const [prereqSearch, setPrereqSearch] = useState('')
  const [toolInput, setToolInput] = useState('')
  const [examples, setExamples] = useState('')

  // Meta
  const [industries, setIndustries] = useState<string[]>([])
  const [availableTags, setAvailableTags] = useState<IndustryTag[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Load data
  useEffect(() => {
    if (isOpen) {
      industryTagsApi.listIndustries().then(setIndustries).catch(console.error)
      industryTagsApi.list({ page_size: 200 }).then(r => setAvailableTags(r.items)).catch(console.error)
    }
  }, [isOpen])

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setIndustry('')
      setTagName('')
      setTagNameEn('')
      setDescription('')
      setDimension('professional')
      setLevel('basic')
      setPrerequisites([])
      setExamples('')
      setError('')
      setPrereqSearch('')
      setToolInput('')
    }
  }, [isOpen])

  // Auto-generate ID
  const tagId = industry && tagName
    ? `${dimension.slice(0, 4)}:${slugify(tagName)}`
    : ''

  const handleAddPrereq = (id: string) => {
    if (id && !prerequisites.includes(id)) setPrerequisites(prev => [...prev, id])
    setPrereqSearch('')
  }

  const handleSubmit = async () => {
    if (!industry.trim()) { setError('请选择或输入所属行业'); return }
    if (!tagName.trim()) { setError('请输入标签名称'); return }
    if (!description.trim()) { setError('请输入标签描述'); return }

    setSubmitting(true)
    setError('')
    try {
      const parsedTools = toolInput.split('\n').map(t => t.trim()).filter(Boolean)
      const result = await industryTagsApi.create({
        id: tagId,
        industry: industry.trim(),
        tag_name: tagName.trim(),
        tag_name_en: tagNameEn.trim() || undefined,
        description: description.trim(),
        dimension,
        level,
        prerequisites: prerequisites.length > 0 ? prerequisites : undefined,
        tools: parsedTools.length > 0 ? parsedTools : undefined,
        examples: examples.trim() ? [examples.trim()] : undefined,
        status: 'active',
      })
      const newTag = await industryTagsApi.get(result.id)
      onSuccess(newTag)
      onClose()
    } catch (e: any) {
      setError(e?.message || e?.detail || '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  const filteredTags = availableTags.filter(t =>
    t.id !== tagId &&
    (t.tag_name.includes(prereqSearch) || t.id.includes(prereqSearch)) &&
    !prerequisites.includes(t.id)
  ).slice(0, 10)

  return (
    <Dialog open={isOpen} onOpenChange={open => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-blue-600" />
            新建能力标签
          </DialogTitle>
          <DialogDescription>
            填写能力标签信息。标签ID根据「行业+标签名称」自动生成，可自行修改。
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="basic" className="mt-2">
          <TabsList className="grid grid-cols-3 w-full">
            <TabsTrigger value="basic" className="gap-1 text-xs">
              <Info className="w-3 h-3" />基本信息
            </TabsTrigger>
            <TabsTrigger value="capability" className="gap-1 text-xs">
              <Wrench className="w-3 h-3" />能力定义
            </TabsTrigger>
            <TabsTrigger value="advanced" className="gap-1 text-xs">
              <BookOpen className="w-3 h-3" />示例
            </TabsTrigger>
          </TabsList>

          {/* ===== 基本信息 ===== */}
          <TabsContent value="basic" className="space-y-4 mt-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                所属行业 <span className="text-red-500">*</span>
              </label>
              <Select value={industry} onValueChange={setIndustry}>
                <SelectTrigger><SelectValue placeholder="请选择或输入行业..." /></SelectTrigger>
                <SelectContent>
                  {industries.map(ind => (
                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                placeholder="或直接输入新行业名称（英文）"
                value={industry}
                onChange={e => setIndustry(e.target.value)}
                className="mt-1"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                标签名称 <span className="text-red-500">*</span>
              </label>
              <Input
                value={tagName}
                onChange={e => setTagName(e.target.value)}
                placeholder="例如：危化品识别、应急响应分级"
                className="text-base"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">标签ID（自动生成）</label>
              <Input
                value={tagId}
                readOnly
                className="font-mono text-sm bg-slate-50"
                placeholder="dimension:name-slug"
              />
              <p className="text-xs text-slate-400">
                格式：<code className="bg-slate-100 px-1 rounded">维度缩写:标签拼音</code>
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">英文名称（可选）</label>
              <Input
                value={tagNameEn}
                onChange={e => setTagNameEn(e.target.value)}
                placeholder="例如：Hazardous Material Identification"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                标签描述 <span className="text-red-500">*</span>
              </label>
              <Textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="描述这个能力的核心职责、适用场景、能力边界..."
                rows={4}
              />
            </div>
          </TabsContent>

          {/* ===== 能力定义 ===== */}
          <TabsContent value="capability" className="space-y-4 mt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                能力维度 <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {DIMENSIONS.map(dim => (
                  <button
                    key={dim.value}
                    type="button"
                    onClick={() => setDimension(dim.value)}
                    className={`p-3 rounded-lg border-2 text-left transition-all ${
                      dimension === dim.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-2 h-2 rounded-full ${
                        dim.value === 'business' ? 'bg-blue-500' :
                        dim.value === 'professional' ? 'bg-purple-500' :
                        dim.value === 'technical' ? 'bg-orange-500' : 'bg-green-500'
                      }`} />
                      <span className="font-medium text-sm">{dim.label}</span>
                    </div>
                    <p className="text-xs text-slate-500">{dim.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">
                能力级别 <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {LEVELS.map(lvl => (
                  <button
                    key={lvl.value}
                    type="button"
                    onClick={() => setLevel(lvl.value)}
                    className={`p-3 rounded-lg border-2 text-center transition-all ${
                      level === lvl.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="font-medium text-sm mb-0.5">{lvl.label}</div>
                    <div className="text-xs text-slate-500">{lvl.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 前置标签 */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">前置标签（可选）</label>
              <p className="text-xs text-slate-400 -mt-1">掌握此标签前应先具备的能力。可选多个。</p>

              {prerequisites.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {prerequisites.map(pid => {
                    const tag = availableTags.find(t => t.id === pid)
                    return (
                      <Badge key={pid} variant="secondary" className="gap-1 pl-2 pr-1 py-1">
                        <span className="text-xs">{tag?.tag_name || pid}</span>
                        <button type="button" onClick={() => setPrerequisites(prev => prev.filter(p => p !== pid))}
                          className="ml-1 text-slate-400 hover:text-red-500 rounded-full p-0.5">
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    )
                  })}
                </div>
              )}

              <div className="relative">
                <Input
                  value={prereqSearch}
                  onChange={e => setPrereqSearch(e.target.value)}
                  placeholder="搜索已有标签..."
                />
                {prereqSearch && filteredTags.length > 0 && (
                  <div className="absolute z-10 w-full bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto mt-1">
                    {filteredTags.map(t => (
                      <button
                        key={t.id}
                        type="button"
                        className="w-full text-left px-3 py-2 hover:bg-slate-50 text-sm border-b last:border-b-0"
                        onClick={() => handleAddPrereq(t.id)}
                      >
                        <div className="font-medium text-xs text-slate-500">{t.id}</div>
                        <div>{t.tag_name}</div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 关联工具 */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">关联工具（可选）</label>
              <p className="text-xs text-slate-400 -mt-1">执行此能力时需要的工具名称，一行一个。</p>
              <Textarea
                value={toolInput}
                onChange={e => setToolInput(e.target.value)}
                placeholder={"智能体能力: msds-lookup\n知识库: 危化品处置手册\n数据库: chemical_registry"}
                rows={4}
              />
            </div>
          </TabsContent>

          {/* ===== 示例 ===== */}
          <TabsContent value="advanced" className="space-y-4 mt-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">使用示例（可选）</label>
              <Textarea
                value={examples}
                onChange={e => setExamples(e.target.value)}
                placeholder="描述典型使用场景，例如：&#10;- 识别泄漏物质为液碱（NaOH），属于Ⅲ类危化品&#10;- 根据 MSDS 判断处置方案"
                rows={5}
              />
            </div>

            {/* 摘要 */}
            <div className="rounded-lg border bg-slate-50 p-4 space-y-1.5">
              <h4 className="text-sm font-semibold text-slate-700">标签摘要</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <div className="text-slate-500">标签ID</div>
                <div className="font-mono text-slate-700">{tagId || <span className="text-slate-400">—</span>}</div>
                <div className="text-slate-500">标签名称</div>
                <div className="text-slate-700">{tagName || <span className="text-slate-400">—</span>}</div>
                <div className="text-slate-500">维度</div>
                <div className="text-slate-700">{DIMENSIONS.find(d => d.value === dimension)?.label}</div>
                <div className="text-slate-500">级别</div>
                <div className="text-slate-700">{LEVELS.find(l => l.value === level)?.label}</div>
                <div className="text-slate-500">前置标签</div>
                <div className="text-slate-700">{prerequisites.length > 0 ? `${prerequisites.length} 个` : <span className="text-slate-400">无</span>}</div>
                <div className="text-slate-500">关联工具</div>
                <div className="text-slate-700">{toolInput.trim() ? toolInput.split('\n').filter(Boolean).join(', ') : <span className="text-slate-400">无</span>}</div>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {error && (
          <div className="mt-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={submitting}>取消</Button>
          <Button onClick={handleSubmit} disabled={submitting} className="gap-2">
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            <Plus className="w-4 h-4" />
            创建标签
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
