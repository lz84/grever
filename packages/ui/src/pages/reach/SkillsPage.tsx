import { useState, useEffect } from 'react'
import { SKILLS } from '../../shared/api/paths'
import { Download, Search, ExternalLink, BookOpen, Code, Check, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'

interface Skill {
  id: string
  name: string
  description: string
  category: string
  installed: boolean
  path: string
  source: string
  content?: string
}

const CATEGORY_LABELS: Record<string, string> = {
  '认知': '认知',
  '协调': '协调',
  '基础设施': '基础设施',
  '执行': '执行',
  '验证': '验证',
  '通用': '通用',
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [downloading, setDownloading] = useState<string | null>(null)
  const [downloadMsg, setDownloadMsg] = useState('')

  // Fetch skills from Nexus API
  async function fetchSkills() {
    try {
      setLoading(true)
      const res = await fetch(SKILLS.LIST)
      const data = await res.json()
      setSkills(data.skills || [])
    } catch (e) {
      console.error('Failed to fetch skills:', e)
    } finally {
      setLoading(false)
    }
  }

  // Fetch skill detail with content
  async function fetchSkillDetail(id: string) {
    try {
      const res = await fetch(`/api/v1/skills/${id}`)
      const data = await res.json()
      setSelectedSkill(data)
    } catch (e) {
      console.error('Failed to fetch skill detail:', e)
    }
  }

  // Generate install prompt for a skill
  async function fetchInstallPrompt(skill: Skill): Promise<string> {
    const res = await fetch(`/api/v1/skills/${skill.id}/install-prompt`)
    if (!res.ok) throw new Error('获取安装指令失败')
    return await res.text()
  }

  // Install skill: copy install prompt to clipboard
  async function installSkill(skill: Skill) {
    setDownloading(skill.id)
    setDownloadMsg('')
    try {
      const prompt = await fetchInstallPrompt(skill)
      await navigator.clipboard.writeText(prompt)
      setDownloadMsg(`${skill.name} 安装指令已复制，发送给智能体即可安装`)
    } catch (e) {
      setDownloadMsg('获取安装指令失败')
    } finally {
      setDownloading(null)
    }
  }

  useEffect(() => {
    fetchSkills()
  }, [])

  // Filter skills
  const filtered = skills.filter(s => {
    const matchSearch = !searchQuery || 
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchCategory = !categoryFilter || s.category === categoryFilter
    return matchSearch && matchCategory
  })

  const categories = [...new Set(skills.map(s => s.category))]

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Nexus 技能库</h1>
          <p className="text-muted-foreground mt-2">
            {skills.length} 个原生技能 · 4 层架构 · Agent 可随时取用
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="搜索技能..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="所有类别" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">所有类别</SelectItem>
              {categories.map(c => (
                <SelectItem key={c} value={c}>{CATEGORY_LABELS[c] || c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Skills Grid */}
        {loading ? (
          <div className="text-center py-12 text-muted-foreground">加载中...</div>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="text-center py-16">
              <BookOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
              <p className="text-lg text-muted-foreground">没有匹配的技能</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(skill => (
              <Card 
                key={skill.id} 
                className="hover:shadow-lg transition cursor-pointer"
                onClick={() => fetchSkillDetail(skill.id)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-lg truncate">{skill.name}</CardTitle>
                      <Badge variant="secondary" className="mt-1">
                        {CATEGORY_LABELS[skill.category] || skill.category}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">{skill.source}</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                    {skill.description}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="default"
                      size="sm"
                      className="flex-1"
                      onClick={(e) => {
                        e.stopPropagation()
                        installSkill(skill)
                      }}
                      disabled={downloading === skill.id}
                    >
                      {downloading === skill.id ? (
                        <span className="animate-spin mr-1">⏳</span>
                      ) : (
                        <Download className="w-3.5 h-3.5 mr-1" />
                      )}
                      安装
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        fetchSkillDetail(skill.id)
                      }}
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1" />
                      详情
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Download message */}
        {downloadMsg && (
          <div className={`p-3 rounded-lg flex items-center gap-2 ${
            downloadMsg.startsWith('✅') ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {downloadMsg.startsWith('✅') ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
            <span className="flex-1 text-sm">{downloadMsg}</span>
            <Button variant="ghost" size="sm" onClick={() => setDownloadMsg('')} className="text-sm">
              关闭
            </Button>
          </div>
        )}

        {/* Skill Detail Modal */}
        <Dialog open={!!selectedSkill} onOpenChange={(open) => !open && setSelectedSkill(null)}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <DialogTitle className="text-xl">{selectedSkill?.name}</DialogTitle>
                  <DialogDescription className="flex gap-2 mt-2">
                    <Badge variant="secondary">
                      {selectedSkill && (CATEGORY_LABELS[selectedSkill.category] || selectedSkill.category)}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">
                      {selectedSkill?.path}
                    </span>
                  </DialogDescription>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedSkill(null)}
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </DialogHeader>
            
            <div className="flex-1 overflow-y-auto space-y-4">
              <div>
                <p className="text-foreground">{selectedSkill?.description}</p>
              </div>
              {selectedSkill?.content && (
                <div>
                  <Label className="flex items-center gap-2 mb-2">
                    <Code className="w-4 h-4" />
                    SKILL.md 内容
                  </Label>
                  <pre className="bg-muted p-4 rounded-lg text-sm overflow-x-auto whitespace-pre-wrap max-h-96">
                    {selectedSkill.content}
                  </pre>
                </div>
              )}
            </div>
            
            <div className="flex gap-2 pt-4 border-t">
              <Button
                variant="default"
                onClick={() => selectedSkill && installSkill(selectedSkill)}
                disabled={downloading === selectedSkill?.id}
              >
                <Download className="w-4 h-4 mr-2" />
                {downloading === selectedSkill?.id ? '安装中...' : '复制安装指令'}
              </Button>
              <Button variant="outline" onClick={() => setSelectedSkill(null)}>
                关闭
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Usage Guide */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              使用说明
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted/50 p-4 rounded-lg">
              <Label className="font-semibold mb-2 block">智能体如何安装技能？</Label>
              <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
                <li>在技能库页面浏览可用技能</li>
                <li>点击「安装」将安装指令复制到剪贴板</li>
                <li>将指令发送给目标智能体，智能体自动从 Nexus 下载并安装技能</li>
                <li>智能体安装完成后即可使用该技能</li>
              </ol>
            </div>
            <div className="bg-muted/50 p-4 rounded-lg">
              <Label className="font-semibold mb-2 block">API 端点</Label>
              <code className="block bg-black text-green-400 p-3 rounded text-xs overflow-x-auto">
                GET /api/v1/skills — 获取技能列表<br/>
                GET /api/v1/skills/{'{id}'} — 获取技能详情<br/>
                GET /api/v1/skills/{'{id}'}/install-prompt — 获取安装指令<br/>
                GET /api/v1/skills/{'{id}'}/raw/{'{filename}'} — 下载技能文件
              </code>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
