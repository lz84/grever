/**
 * Industry Pack Import Dialog
 * Sprint 114 F114-2: 导入对话框
 * - 拖拽上传 .grever-pack 文件
 * - manifest 预览内容
 * - 策略选择（create/upsert/force）
 * - 自动安装依赖
 * - 进度/结果展示
 */
import { useState, useRef, useCallback } from 'react'
import { Loader2, Upload, FileUp, FileText, CheckCircle, XCircle, AlertCircle, Package } from 'lucide-react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select'
import { Card, CardContent } from '@/shared/components/ui/card'
import { Badge } from '@/shared/components/ui/badge'

type ImportStrategy = 'create' | 'upsert' | 'force'
type ImportPhase = 'upload' | 'preview' | 'importing' | 'result'

interface PackManifest {
  name?: string
  id?: string
  version?: string
  industry?: string
  description?: string
  pack_type?: string
  tags_count?: number
  scenarios_count?: number
  skills_count?: number
  [key: string]: any
}

interface IndustryPackImportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported?: () => void
}

const STRATEGY_LABELS: Record<ImportStrategy, string> = {
  create: '创建新包（同名冲突时拒绝）',
  upsert: '更新已有包（保留缺失字段）',
  force: '强制覆盖（删除已有内容后重建）',
}

export default function IndustryPackImportDialog({
  open,
  onOpenChange,
  onImported,
}: IndustryPackImportDialogProps) {
  const [phase, setPhase] = useState<ImportPhase>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [manifest, setManifest] = useState<PackManifest | null>(null)
  const [strategy, setStrategy] = useState<ImportStrategy>('upsert')
  const [autoInstallDeps, setAutoInstallDeps] = useState(true)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{
    success: boolean
    pack_id?: string
    message?: string
  } | null>(null)

  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reset = useCallback(() => {
    setPhase('upload')
    setFile(null)
    setManifest(null)
    setStrategy('upsert')
    setAutoInstallDeps(true)
    setImporting(false)
    setError(null)
    setResult(null)
  }, [])

  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (!open) reset()
      onOpenChange(open)
    },
    [onOpenChange, reset]
  )

  const readFileManifest = async (f: File) => {
    try {
      const text = await f.text()
      let parsed: any
      try {
        parsed = JSON.parse(text)
      } catch {
        // Try to extract manifest from zip-like or raw format
        setError('文件格式无效，请上传 .grever-pack 或 .json 文件')
        return
      }

      const m: PackManifest = {
        name: parsed.name || parsed.manifest?.name,
        id: parsed.id || parsed.manifest?.id,
        version: parsed.version || parsed.manifest?.version || 'unknown',
        industry: parsed.industry || parsed.manifest?.industry,
        description: parsed.description || parsed.manifest?.description,
        pack_type: parsed.pack_type || parsed.manifest?.pack_type,
        tags_count: parsed.tags_count || parsed.tags?.length || 0,
        scenarios_count: parsed.scenarios_count || parsed.scenarios?.length || 0,
        skills_count: parsed.skills_count || parsed.skills?.length || 0,
      }
      setFile(f)
      setManifest(m)
      setPhase('preview')
      setError(null)
    } catch (err: any) {
      setError(`读取文件失败: ${err.message}`)
    }
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile) {
        readFileManifest(droppedFile)
      }
    },
    [readFileManifest]
  )

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0]
      if (selectedFile) {
        readFileManifest(selectedFile)
      }
    },
    [readFileManifest]
  )

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    setPhase('importing')
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('strategy', strategy)
      if (autoInstallDeps) formData.append('auto_install_deps', 'true')

      const resp = await fetch('/api/v1/industry-packs/import', {
        method: 'POST',
        body: formData,
      })

      const data = await resp.json()

      if (!resp.ok) {
        throw new Error(data.detail || data.message || `导入失败: ${resp.status}`)
      }

      setResult({
        success: data.success !== false,
        pack_id: data.pack_id,
        message: data.message,
      })
      setPhase('result')
      if (data.success !== false && onImported) {
        onImported()
      }
    } catch (err: any) {
      setError(err.message || '导入失败')
      setPhase('preview')
    } finally {
      setImporting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            导入行业包
          </DialogTitle>
        </DialogHeader>

        {/* Phase: Upload */}
        {phase === 'upload' && (
          <div className="space-y-4 py-2">
            <div
              className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
                isDragging
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <FileUp className="w-10 h-10 mx-auto mb-3 text-gray-300" />
              <p className="text-sm font-medium text-gray-600">
                拖拽 .grever-pack 文件到这里，或点击选择
              </p>
              <p className="text-xs text-gray-400 mt-1">
                支持 .grever-pack 和 .json 格式
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".grever-pack,.json"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                <XCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}
          </div>
        )}

        {/* Phase: Preview */}
        {phase === 'preview' && (
          <div className="space-y-4 py-2">
            {/* Manifest preview */}
            {manifest && (
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-600">
                      Manifest 预览
                    </span>
                    <Badge variant="outline" className="ml-auto text-xs">
                      {(file ? file.size / 1024 : 0).toFixed(1)} KB
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-400 text-xs">名称</span>
                      <p className="font-medium">{manifest.name || '-'}</p>
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">ID</span>
                      <p className="font-mono text-xs">{manifest.id || '-'}</p>
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">版本</span>
                      <p className="font-mono text-xs">{manifest.version}</p>
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">行业</span>
                      <p>{manifest.industry || '-'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Package className="w-3 h-3" />
                      {manifest.tags_count || 0} 标签
                    </span>
                    <span>{manifest.scenarios_count || 0} 场景</span>
                    <span>{manifest.skills_count || 0} 技能</span>
                  </div>
                  {manifest.description && (
                    <p className="text-xs text-gray-400 mt-2 line-clamp-2">
                      {manifest.description}
                    </p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Strategy */}
            <div className="space-y-2">
              <Label>导入策略</Label>
              <Select
                value={strategy}
                onValueChange={(v) => setStrategy(v as ImportStrategy)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(STRATEGY_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Auto install deps */}
            <div className="flex items-center justify-between py-2">
              <div>
                <Label className="text-sm">自动安装依赖</Label>
                <p className="text-xs text-gray-400 mt-0.5">
                  自动安装此行业包所依赖的其他包
                </p>
              </div>
              <Switch
                checked={autoInstallDeps}
                onCheckedChange={setAutoInstallDeps}
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}
          </div>
        )}

        {/* Phase: Importing */}
        {phase === 'importing' && (
          <div className="flex flex-col items-center justify-center py-10">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-3" />
            <p className="text-sm text-gray-600">正在导入行业包...</p>
            <p className="text-xs text-gray-400 mt-1">这可能需要几秒钟</p>
          </div>
        )}

        {/* Phase: Result */}
        {phase === 'result' && result && (
          <div className="space-y-4 py-2">
            <div
              className={`flex items-start gap-3 p-4 rounded-lg ${
                result.success
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
              }`}
            >
              {result.success ? (
                <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
              )}
              <div>
                <p
                  className={`font-medium text-sm ${
                    result.success ? 'text-green-700' : 'text-red-700'
                  }`}
                >
                  {result.success ? '导入成功' : '导入失败'}
                </p>
                {result.message && (
                  <p className="text-xs text-gray-500 mt-1">{result.message}</p>
                )}
                {result.pack_id && (
                  <p className="text-xs font-mono text-gray-400 mt-1">
                    Pack ID: {result.pack_id}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          {phase === 'upload' && (
            <Button variant="outline" onClick={() => handleOpenChange(false)}>
              取消
            </Button>
          )}
          {phase === 'preview' && (
            <>
              <Button variant="outline" onClick={() => setPhase('upload')}>
                重新选择
              </Button>
              <Button onClick={handleImport} disabled={importing}>
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-1" />
                    导入中...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-1" />
                    确认导入
                  </>
                )}
              </Button>
            </>
          )}
          {phase === 'result' && (
            <Button onClick={() => handleOpenChange(false)}>完成</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
