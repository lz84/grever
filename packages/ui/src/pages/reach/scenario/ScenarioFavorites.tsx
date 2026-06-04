import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Star, RefreshCw, Search, Trash2, AlertCircle, FileText, Loader2, Zap } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/shared/components/ui/alert-dialog'

const CATEGORY_LABELS: Record<string, string> = {
  earthquake: '地震', fire: '火灾', chemical: '化学品', flood: '防汛', general: '通用',
}
const CATEGORY_CLASSES: Record<string, string> = {
  earthquake: 'bg-red-100 text-red-700',
  fire: 'bg-orange-100 text-orange-700',
  chemical: 'bg-purple-100 text-purple-700',
  flood: 'bg-blue-100 text-blue-700',
  general: 'bg-slate-100 text-slate-600',
}
const STATUS_LABELS: Record<string, string> = { active: '活跃', archived: '归档', draft: '草稿' }
const STATUS_CLASSES: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  archived: 'bg-slate-100 text-slate-600',
  draft: 'bg-orange-100 text-orange-700',
}

export default function ScenarioFavorites() {
  const navigate = useNavigate()
  const [starred, setStarred] = useState<Record<string, any>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStarred()
  }, [])

  function loadStarred() {
    setLoading(true)
    try {
      const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}')
      setStarred(stored)
    } catch {
      setStarred({})
    }
    setLoading(false)
  }

  const filteredStarred = useMemo(() => {
    const list = Object.entries(starred)
    if (!searchQuery) return list
    const q = searchQuery.toLowerCase()
    return list.filter(([, v]) =>
      v.name.toLowerCase().includes(q) || (v.description || '').toLowerCase().includes(q)
    )
  }, [starred, searchQuery])

  const handleUnstar = (id: string) => {
    const stored = JSON.parse(localStorage.getItem('nexus_starred_scenarios') || '{}')
    delete stored[id]
    localStorage.setItem('nexus_starred_scenarios', JSON.stringify(stored))
    setStarred({ ...stored })
  }

  const handleClearAll = () => {
    localStorage.setItem('nexus_starred_scenarios', '{}')
    setStarred({})
    setShowClearConfirm(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Star className="w-5 h-5 text-yellow-500 fill-yellow-400" />
            收藏场景
          </h1>
          <p className="text-sm text-muted-foreground mt-1">我收藏的场景方案</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadStarred}>
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新
          </Button>
          {Object.keys(starred).length > 0 && (
            <Button variant="destructive" onClick={() => setShowClearConfirm(true)}>
              <Trash2 className="w-4 h-4 mr-2" />
              清空全部
            </Button>
          )}
        </div>
      </div>

      {/* Search */}
      {Object.keys(starred).length > 0 && (
        <Input
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="搜索收藏..."
          className="max-w-md"
        />
      )}

      {/* Clear confirm dialog */}
      <AlertDialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-orange-500" />
              确认清空
            </AlertDialogTitle>
            <AlertDialogDescription>
              确定要清空所有收藏吗？此操作不可恢复。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleClearAll}>确定</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* List */}
      {Object.keys(starred).length === 0 ? (
        <Card>
          <CardContent className="text-center py-16">
            <Star className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-muted-foreground mb-4">暂无收藏</p>
            <Button variant="link" onClick={() => navigate('/scenarios')}>
              去场景库看看
            </Button>
          </CardContent>
        </Card>
      ) : filteredStarred.length === 0 ? (
        <Card>
          <CardContent className="text-center py-16">
            <Search className="w-8 h-8 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-muted-foreground">未找到匹配的收藏</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredStarred.map(([id, data]) => (
            <Card key={id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <CardTitle className="text-base">{data.name}</CardTitle>
                  </div>
                  <div className="flex gap-1 flex-wrap">
                    <Badge className={CATEGORY_CLASSES[data.category] || 'bg-slate-100 text-slate-600'}>
                      {CATEGORY_LABELS[data.category] || data.category}
                    </Badge>
                    <Badge className={STATUS_CLASSES[data.status] || 'bg-slate-100 text-slate-600'}>
                      {STATUS_LABELS[data.status] || data.status}
                    </Badge>
                    <Badge variant="outline">{data.version}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {data.description && (
                  <p className="text-sm text-muted-foreground mb-4">{data.description}</p>
                )}
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => navigate(`/scenarios/${id}`)}>
                    查看详情
                  </Button>
                  <Button size="sm" onClick={() => navigate(`/coordination/goals/new?scenario_id=${id}`)}>
                    <Zap className="w-3 h-3 mr-1" />
                    实例化
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => handleUnstar(id)}>
                    取消收藏
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
