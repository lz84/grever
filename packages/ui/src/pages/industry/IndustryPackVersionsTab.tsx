/**
 * Industry Pack Versions Tab
 * Sprint 112 F112-1: 版本历史前端组件
 * 展示版本历史表格（版本/操作/时间/备注）
 * 调用 GET /api/v1/industry-packs/{id}/versions
 */
import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'
import { industryPacksExtendedApi, PackVersion } from '@/shared/utils/api'

const OPERATION_LABELS: Record<string, { label: string; color: string }> = {
  create: { label: '创建', color: 'bg-blue-100 text-blue-700' },
  created: { label: '创建', color: 'bg-blue-100 text-blue-700' },
  update: { label: '更新', color: 'bg-green-100 text-green-700' },
  updated: { label: '更新', color: 'bg-green-100 text-green-700' },
  publish: { label: '发布', color: 'bg-purple-100 text-purple-700' },
  published: { label: '发布', color: 'bg-purple-100 text-purple-700' },
  rollback: { label: '回滚', color: 'bg-orange-100 text-orange-700' },
  upgrade: { label: '升级', color: 'bg-green-100 text-green-700' },
  deprecate: { label: '废弃', color: 'bg-red-100 text-red-700' },
  import: { label: '导入', color: 'bg-cyan-100 text-cyan-700' },
}

function formatTimestamp(ts: number): string {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface IndustryPackVersionsTabProps {
  packId: string
}

export default function IndustryPackVersionsTab({ packId }: IndustryPackVersionsTabProps) {
  const [versions, setVersions] = useState<PackVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    if (!packId) return
    setLoading(true)
    industryPacksExtendedApi
      .versions(packId)
      .then((res) => {
        setVersions(res.items || [])
        setTotal(res.total || 0)
      })
      .catch((err) => {
        console.error('Failed to load pack versions:', err)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [packId])

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (versions.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-gray-400 text-sm">
          暂无版本记录
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-400 mb-2">共 {total} 条版本记录</div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left py-2.5 px-4 font-medium text-gray-600 w-28">版本</th>
              <th className="text-left py-2.5 px-4 font-medium text-gray-600 w-24">操作</th>
              <th className="text-left py-2.5 px-4 font-medium text-gray-600 w-44">时间</th>
              <th className="text-left py-2.5 px-4 font-medium text-gray-600 w-24">操作人</th>
              <th className="text-left py-2.5 px-4 font-medium text-gray-600">备注</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => {
              const op = v.action || v.operation || ''
              const opInfo = OPERATION_LABELS[op] || {
                label: op || '-',
                color: 'bg-gray-100 text-gray-600',
              }
              return (
                <tr key={v.id} className="border-b last:border-0 hover:bg-gray-50/50">
                  <td className="py-2.5 px-4 font-mono text-xs">{v.version}</td>
                  <td className="py-2.5 px-4">
                    <Badge className={opInfo.color} variant="secondary">
                      {opInfo.label}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-4 text-gray-500 text-xs">
                    {formatTimestamp(v.created_at)}
                  </td>
                  <td className="py-2.5 px-4 text-gray-500 text-xs">
                    {v.created_by || '-'}
                  </td>
                  <td className="py-2.5 px-4 text-gray-500 text-xs">
                    {v.notes || '-'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
