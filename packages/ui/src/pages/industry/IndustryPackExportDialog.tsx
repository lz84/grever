/**
 * Industry Pack Export Dialog
 * Sprint 114 F114-1: 导出对话框
 * - 格式选择（.nexus-pack / .json）
 * - 附加资源开关
 * - 文件大小预估
 * - 下载触发（调用 POST /export，触发浏览器下载）
 */
import { useState } from 'react'
import { Loader2, Download, FileJson, Package, HardDrive } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/components/ui/dialog'
import { Button } from '@/shared/components/ui/button'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { Card, CardContent } from '@/shared/components/ui/card'
import { IndustryPack } from '@/shared/utils/industryTagsApi'

type ExportFormat = 'nexus-pack' | 'json'

interface IndustryPackExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  pack: IndustryPack
}

export default function IndustryPackExportDialog({
  open,
  onOpenChange,
  pack,
}: IndustryPackExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>('nexus-pack')
  const [includeResources, setIncludeResources] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Estimate file size based on pack content counts
  const estimatedSize = (() => {
    let base = 5 // KB for manifest
    base += (pack.tags_count || 0) * 2
    base += (pack.scenarios_count || 0) * 8
    base += (pack.skills_count || 0) * 4
    if (includeResources) base += 20 // additional resources buffer
    return base
  })()

  const formatSize = (kb: number): string => {
    if (kb < 1024) return `${kb} KB`
    return `${(kb / 1024).toFixed(1)} MB`
  }

  const handleExport = async () => {
    setExporting(true)
    setError(null)
    try {
      const apiUrl = `/api/v1/industry-packs/${pack.id}/export`
      const resp = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          include_resources: includeResources,
        }),
      })

      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({ detail: resp.statusText }))
        throw new Error(errBody.detail || `导出失败: ${resp.status}`)
      }

      // Trigger browser download
      const blob = await resp.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const ext = format === 'nexus-pack' ? '.nexus-pack' : '.json'
      a.download = `${pack.id || pack.name}${ext}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      onOpenChange(false)
    } catch (err: any) {
      setError(err.message || '导出失败，请重试')
    } finally {
      setExporting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="w-4 h-4" />
            导出行业包
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Pack info */}
          <Card>
            <CardContent className="pt-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{pack.name}</span>
                <span className="text-gray-400 text-xs font-mono">{pack.id}</span>
              </div>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span>v{pack.version}</span>
                <span>{pack.tags_count ?? 0} 标签</span>
                <span>{pack.scenarios_count ?? 0} 场景</span>
                <span>{pack.skills_count ?? 0} 技能</span>
              </div>
            </CardContent>
          </Card>

          {/* Format selection */}
          <div className="space-y-3">
            <Label>导出格式</Label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                className={`flex items-center gap-2 p-3 rounded-lg border-2 transition-colors text-sm ${
                  format === 'nexus-pack'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setFormat('nexus-pack')}
              >
                <Package className="w-4 h-4" />
                <div className="text-left">
                  <div className="font-medium">.nexus-pack</div>
                  <div className="text-xs text-gray-500">完整行业包格式</div>
                </div>
              </button>
              <button
                type="button"
                className={`flex items-center gap-2 p-3 rounded-lg border-2 transition-colors text-sm ${
                  format === 'json'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setFormat('json')}
              >
                <FileJson className="w-4 h-4" />
                <div className="text-left">
                  <div className="font-medium">.json</div>
                  <div className="text-xs text-gray-500">纯 JSON 数据</div>
                </div>
              </button>
            </div>
          </div>

          {/* Include resources */}
          <div className="flex items-center justify-between py-2">
            <div>
              <Label className="text-sm">包含附加资源</Label>
              <p className="text-xs text-gray-400 mt-0.5">
                包含技能文件、参考数据等附件
              </p>
            </div>
            <Switch
              checked={includeResources}
              onCheckedChange={setIncludeResources}
            />
          </div>

          {/* Size estimate */}
          <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg text-sm">
            <HardDrive className="w-4 h-4 text-gray-400" />
            <span className="text-gray-500">预估文件大小:</span>
            <span className="font-medium text-gray-700">{formatSize(estimatedSize)}</span>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={exporting}>
            取消
          </Button>
          <Button onClick={handleExport} disabled={exporting}>
            {exporting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
                导出中...
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-1" />
                导出下载
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
