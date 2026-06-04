import { useState, useEffect } from "react"
import { GRASP } from "../../shared/api/paths"
import { BookOpen, Search, Plus, Edit, Trash2, CheckCircle, XCircle, Loader2, ExternalLink } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/components/ui/card"
import { Badge } from "@/shared/components/ui/badge"
import { Button } from "@/shared/components/ui/button"
import { Input } from "@/shared/components/ui/input"
import { Label } from "@/shared/components/ui/label"
import { Textarea } from "@/shared/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/components/ui/dialog"

interface KnowledgeItem {
  id: string
  title: string
  content: string
  category: string
  tags: string[]
  source_url?: string
  verified: boolean
  created_at: string
  updated_at: string
}

const CATEGORIES = [
  { value: "architecture", label: "架构" },
  { value: "api", label: "API" },
  { value: "deployment", label: "部署" },
  { value: "troubleshooting", label: "故障排查" },
  { value: "best-practices", label: "最佳实践" },
]

export function CognitiveKnowledge() {
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const [filterCategory, setFilterCategory] = useState("all")
  const [showCreate, setShowCreate] = useState(false)
  const [editItem, setEditItem] = useState<KnowledgeItem | null>(null)
  const [form, setForm] = useState({
    title: "",
    content: "",
    category: "architecture",
    tags: "",
    source_url: "",
  })

  useEffect(() => {
    loadItems()
  }, [filterCategory])

  const loadItems = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: "100" })
      if (filterCategory !== "all") params.append("category", filterCategory)
      const res = await fetch(GRASP.KNOWLEDGE_LIST + `?${params}`)
      if (res.ok) {
        const data = await res.json()
        setItems(data.items || [])
      } else {
        setItems([])
      }
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  const filteredItems = items.filter((item) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      item.title.toLowerCase().includes(q) ||
      item.content.toLowerCase().includes(q) ||
      item.tags.some((t) => t.toLowerCase().includes(q))
    )
  })

  const handleCreate = async () => {
    if (!form.title.trim() || !form.content.trim()) return
    try {
      const res = await fetch(GRASP.KNOWLEDGE_LIST, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
        }),
      })
      if (res.ok) {
        setForm({ title: "", content: "", category: "architecture", tags: "", source_url: "" })
        setShowCreate(false)
        loadItems()
      }
    } catch (err) {
      console.error("Failed to create:", err)
    }
  }

  const handleUpdate = async () => {
    if (!editItem || !form.title.trim()) return
    try {
      const res = await fetch(GRASP.COGNITION_GET(editItem.id), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
        }),
      })
      if (res.ok) {
        setEditItem(null)
        loadItems()
      }
    } catch (err) {
      console.error("Failed to update:", err)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(GRASP.COGNITION_GET(id), { method: "DELETE" })
      loadItems()
    } catch (err) {
      console.error("Failed to delete:", err)
    }
  }

  const openEdit = (item: KnowledgeItem) => {
    setEditItem(item)
    setForm({
      title: item.title,
      content: item.content,
      category: item.category,
      tags: item.tags.join(", "),
      source_url: item.source_url || "",
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <BookOpen className="h-8 w-8" />
            认知知识库
          </h1>
          <p className="text-muted-foreground mt-1">
            管理知识库条目，支持分类、标签和来源追踪
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          添加知识
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索标题、内容、标签..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={filterCategory} onValueChange={setFilterCategory}>
          <SelectTrigger className="w-[180px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部分类</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Items */}
      {loading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            暂无知识条目
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredItems.map((item) => (
            <Card key={item.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="space-y-1 flex-1">
                    <CardTitle className="text-base">{item.title}</CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">
                        {CATEGORIES.find((c) => c.value === item.category)?.label || item.category}
                      </Badge>
                      {item.verified ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(item)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-3">{item.content}</p>
                {item.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {item.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                    ))}
                  </div>
                )}
                {item.source_url && (
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 flex items-center gap-1 text-xs text-blue-500 hover:underline"
                  >
                    <ExternalLink className="h-3 w-3" />
                    {item.source_url}
                  </a>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>添加知识条目</DialogTitle>
            <DialogDescription>向知识库添加新的条目</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="create-title">标题 *</Label>
              <Input
                id="create-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="知识标题"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-content">内容 *</Label>
              <Textarea
                id="create-content"
                rows={4}
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                placeholder="详细知识内容..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-category">分类</Label>
                <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="create-tags">标签 (逗号分隔)</Label>
                <Input
                  id="create-tags"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  placeholder="tag1, tag2"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-url">来源URL</Label>
              <Input
                id="create-url"
                value={form.source_url}
                onChange={(e) => setForm({ ...form, source_url: e.target.value })}
                placeholder="https://..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>取消</Button>
            <Button onClick={handleCreate}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editItem} onOpenChange={(o) => !o && setEditItem(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>编辑知识条目</DialogTitle>
            <DialogDescription>修改知识库条目</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-title">标题 *</Label>
              <Input
                id="edit-title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-content">内容 *</Label>
              <Textarea
                id="edit-content"
                rows={4}
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-category">分类</Label>
                <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-tags">标签 (逗号分隔)</Label>
                <Input
                  id="edit-tags"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-url">来源URL</Label>
              <Input
                id="edit-url"
                value={form.source_url}
                onChange={(e) => setForm({ ...form, source_url: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditItem(null)}>取消</Button>
            <Button onClick={handleUpdate}>保存修改</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default CognitiveKnowledge;
