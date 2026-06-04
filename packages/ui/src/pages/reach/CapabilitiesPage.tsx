import { useState, useEffect } from 'react'
import { MCP_SERVERS, SKILLS } from '../../shared/api/paths'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, Plus, Search, ExternalLink, CheckCircle,
  X, Server, Wrench, Package, RefreshCw
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Label } from '@/shared/components/ui/label'
import { Textarea } from '@/shared/components/ui/textarea'
import {
  Dialog,
  DialogContent,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/components/ui/tabs'

interface McpServer {
  id: string
  name: string
  description: string
  transport: string
  url: string
  icon: string | null
  category: string
  status: string
  created_at: string
  auth_type?: string
  rate_limit?: number
  ssl_verify?: boolean
}

interface McpTool {
  id: string
  server_id: string
  name: string
  description: string
  parameters: string
  return_type: string
}

interface Skill {
  id: string
  name: string
  description: string
  category: string
  installed: boolean
  path: string
}

export default function CapabilitiesPage() {
  // MCP state
  const [servers, setServers] = useState<McpServer[]>([])
  const [selectedServer, setSelectedServer] = useState<McpServer | null>(null)
  const [tools, setTools] = useState<McpTool[]>([])

  // Skills state
  const [skills, setSkills] = useState<Skill[]>([])
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)

  // Common state
  const [activeTab, setActiveTab] = useState<'mcp' | 'skills'>('mcp')
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  // New MCP form
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newTransport, setNewTransport] = useState('http')
  const [newUrl, setNewUrl] = useState('')
  const [newCategory, setNewCategory] = useState('数据')
  const [creating, setCreating] = useState(false)

  const mcpCategories = ['数据', '工具', '知识库', '自动化', '资讯']
  const skillCategories = ['任务', '认知', '调度', 'Nexus', '验证']

  const currentCategories = activeTab === 'mcp' ? mcpCategories : skillCategories

  // Fetch MCP servers
  async function fetchServers() {
    try {
      const res = await fetch(MCP_SERVERS.LIST)
      const data = await res.json()
      setServers(data.servers || [])
    } catch {
      // ignore
    }
  }

  // Fetch skills
  async function fetchSkills() {
    try {
      const res = await fetch(SKILLS.LIST)
      const data = await res.json()
      setSkills(data.skills || [])
    } catch {
      // ignore
    }
  }

  // Fetch tools for a server
  async function fetchTools(serverId: string) {
    try {
      const res = await fetch(MCP_SERVERS.GET_TOOLS(serverId))
      const data = await res.json()
      setTools(data.tools || [])
    } catch {
      setTools([])
    }
  }

  // Initial load
  useEffect(() => {
    setLoading(true)
    Promise.all([fetchServers(), fetchSkills()]).finally(() => setLoading(false))
  }, [])

  // Create MCP server
  async function handleCreate() {
    if (!newName || !newUrl) return
    setCreating(true)
    try {
      const body: any = {
        name: newName,
        description: newDesc,
        transport: newTransport,
        url: newUrl,
        category: newCategory,
        tools: []
      }
      await fetch(MCP_SERVERS.CREATE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      setShowCreateModal(false)
      setNewName('')
      setNewDesc('')
      setNewTransport('http')
      setNewUrl('')
      setNewCategory('数据')
      await fetchServers()
    } finally {
      setCreating(false)
    }
  }

  // Filter items based on search and category
  const filteredMcp = servers.filter(s => {
    const matchSearch = !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchCat = categoryFilter === 'all' || s.category === categoryFilter
    return matchSearch && matchCat
  })

  const filteredSkills = skills.filter(s => {
    const matchSearch = !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchCat = categoryFilter === 'all' || s.category === categoryFilter
    return matchSearch && matchCat
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">加载能力库...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" asChild>
            <Link to="/system/agents">
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div>
            <h2 className="text-xl font-bold">能力库</h2>
            <p className="text-sm text-muted-foreground">智能体能力 · 技能市场，智能体一键安装</p>
          </div>
        </div>
        {activeTab === 'mcp' && (
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4" />
            新增能力
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v as 'mcp' | 'skills'); setSearchQuery(''); setCategoryFilter('all') }}>
        <TabsList>
          <TabsTrigger value="mcp" className="flex items-center gap-1.5">
            <Server className="w-4 h-4" />
            MCP库 ({servers.length})
          </TabsTrigger>
          <TabsTrigger value="skills" className="flex items-center gap-1.5">
            <Package className="w-4 h-4" />
            技能库 ({skills.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="mcp" className="space-y-4">
          {/* Search & Filter */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="搜索智能体能力..."
                className="pl-10"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="全部分类" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分类</SelectItem>
                {currentCategories.map(c => (
                  <SelectItem key={c} value={c}>{c}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* MCP Cards */}
          {filteredMcp.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <Server className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                <p className="text-muted-foreground">暂无智能体能力</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredMcp.map(server => (
                <Card
                  key={server.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => {
                    setSelectedServer(server)
                    fetchTools(server.id)
                  }}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Server className="w-5 h-5 text-blue-500" />
                        <CardTitle className="text-base">{server.name}</CardTitle>
                      </div>
                      <Badge variant={server.status === 'active' ? 'success' : 'secondary'}>
                        {server.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{server.description}</p>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <Badge variant="secondary">{server.category}</Badge>
                      <span className="font-mono">{server.transport}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="skills" className="space-y-4">
          {/* Search & Filter */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="搜索技能..."
                className="pl-10"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="全部分类" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分类</SelectItem>

                {currentCategories.map(c => (
                  <SelectItem key={c} value={c}>{c}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Skills Grid */}
          {filteredSkills.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <Package className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                <p className="text-muted-foreground">暂无技能</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSkills.map(skill => (
                <Card key={skill.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Package className="w-5 h-5 text-indigo-500" />
                        <CardTitle className="text-base">{skill.name}</CardTitle>
                      </div>
                      <Badge variant="success">已安装</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{skill.description}</p>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">{skill.category}</Badge>
                      <Button variant="link" size="sm" className="text-xs p-0 h-auto" onClick={() => setSelectedSkill(skill)}>
                        <ExternalLink className="w-3 h-3 mr-1" />
                        详情
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* MCP Server Detail Modal */}
      <Dialog open={!!selectedServer} onOpenChange={(open) => !open && setSelectedServer(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="flex items-center gap-2">
                <Server className="w-5 h-5 text-blue-500" />
                {selectedServer?.name}
              </DialogTitle>
            </div>
          </DialogHeader>
          {selectedServer && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{selectedServer.description}</p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">传输方式:</span> <span className="font-mono ml-2">{selectedServer.transport}</span></div>
                <div><span className="text-muted-foreground">分类:</span> <span className="ml-2">{selectedServer.category}</span></div>
                <div><span className="text-muted-foreground">认证方式:</span> <span className="ml-2">{selectedServer.auth_type || '无'}</span></div>
                <div><span className="text-muted-foreground">速率限制:</span> <span className="ml-2">{selectedServer.rate_limit || '无'}</span></div>
              </div>
              <div>
                <span className="text-muted-foreground text-sm">URL:</span>
                <span className="font-mono text-sm ml-2 text-blue-600">{selectedServer.url}</span>
              </div>

              <div className="border-t pt-4">
                <div className="flex items-center gap-2 mb-3">
                  <Wrench className="w-4 h-4 text-indigo-500" />
                  <h4 className="font-bold">工具列表 ({tools.length})</h4>
                </div>
                {tools.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无工具</p>
                ) : (
                  <div className="space-y-2">
                    {tools.map(tool => (
                      <div key={tool.id} className="p-3 bg-muted rounded-md">
                        <div className="flex items-center gap-2 mb-1">
                          <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                          <span className="font-medium text-sm">{tool.name}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{tool.description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Skill Detail Modal */}
      <Dialog open={!!selectedSkill} onOpenChange={(open) => !open && setSelectedSkill(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-indigo-500" />
              {selectedSkill?.name}
            </DialogTitle>
          </DialogHeader>
          {selectedSkill && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant="success">已安装</Badge>
                <Badge variant="secondary">{selectedSkill.category}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{selectedSkill.description}</p>
              <div className="text-xs text-muted-foreground font-mono break-all">路径: {selectedSkill.path}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create MCP Modal */}
      <Dialog open={showCreateModal} onOpenChange={(open) => !open && setShowCreateModal(false)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>新增 智能体能力</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="mcp-name">名称</Label>
              <Input
                id="mcp-name"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="如: 天气查询"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mcp-desc">描述</Label>
              <Textarea
                id="mcp-desc"
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                rows={2}
                placeholder="如: 获取实时天气和预报"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="mcp-transport">传输方式</Label>
                <Select value={newTransport} onValueChange={setNewTransport}>
                  <SelectTrigger id="mcp-transport">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="http">HTTP</SelectItem>
                    <SelectItem value="sse">SSE</SelectItem>
                    <SelectItem value="stdio">stdio</SelectItem>
                    <SelectItem value="streamable">Streamable</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="mcp-category">分类</Label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger id="mcp-category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {mcpCategories.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="mcp-url">URL</Label>
              <Input
                id="mcp-url"
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
                className="font-mono"
                placeholder="http://..."
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setShowCreateModal(false)} disabled={creating}>
                取消
              </Button>
              <Button onClick={handleCreate} disabled={creating || !newName || !newUrl}>
                {creating ? '创建中...' : '创建'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
