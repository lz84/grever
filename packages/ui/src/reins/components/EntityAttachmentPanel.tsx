import { useState, useEffect } from 'react'
import { toast } from "sonner"
import { Upload, Download, Trash2, Loader2, File, Image, FileText } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { attachmentsApi } from '@/shared/utils/api'

interface Attachment {
  id: string
  filename: string
  mime_type: string | null
  file_size: number
  created_at: string | null
  created_by: string | null
}

interface EntityAttachmentPanelProps {
  entityType: string
  entityId: string
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp']
  const docExts = ['doc', 'docx', 'pdf', 'txt', 'md', 'rtf']
  if (imageExts.includes(ext)) return <Image className="w-4 h-4 text-purple-500" />
  if (docExts.includes(ext)) return <FileText className="w-4 h-4 text-blue-500" />
  return <File className="w-4 h-4 text-slate-400" />
}

export function EntityAttachmentPanel({ entityType, entityId }: EntityAttachmentPanelProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [showUpload, setShowUpload] = useState(false)

  useEffect(() => { loadAttachments() }, [entityType, entityId])

  async function loadAttachments() {
    setLoading(true)
    try {
      const data = await attachmentsApi.list(entityType, entityId)
      setAttachments(Array.isArray(data) ? data : (data.attachments || []))
    } catch { /* */ }
    finally { setLoading(false) }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return
    setUploading(true)
    let uploaded = 0, failed = 0
    for (const file of Array.from(files)) {
      try {
        await attachmentsApi.upload(file, entityType, entityId)
        uploaded++
      } catch { failed++ }
    }
    if (uploaded > 0) toast.success(`上传成功 ${uploaded} 个文件`)
    if (failed > 0) toast.error(`上传失败 ${failed} 个文件`)
    setUploading(false)
    setShowUpload(false)
    await loadAttachments()
  }

  async function handleDelete(att: Attachment) {
    if (!confirm(`确定删除 "${att.filename}"？`)) return
    try {
      await attachmentsApi.delete(att.id, true)
      toast.success('删除成功')
      await loadAttachments()
    } catch { toast.error('删除失败') }
  }

  async function handleDownload(att: Attachment) {
    try {
      const resp = await attachmentsApi.download(att.id, true)
      if (resp.ok) {
        const blob = await resp.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url; a.download = att.filename; a.click()
        URL.revokeObjectURL(url)
      }
    } catch { toast.error('下载失败') }
  }

  return (
    <div className="p-4 space-y-4">
      {/* File List — 放上面 */}
      {loading ? (
        <div className="text-center py-8 text-slate-400">
          <Loader2 className="w-6 h-6 mx-auto animate-spin" />
          <p className="mt-2 text-sm">加载中...</p>
        </div>
      ) : attachments.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <File className="w-8 h-8 mx-auto mb-2" />
          <p className="text-sm">暂无附件</p>
        </div>
      ) : (
        <div className="space-y-2">
          {attachments.map(att => (
            <div key={att.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-4 py-3 hover:bg-slate-100 transition-colors">
              <div className="flex items-center gap-3 min-w-0">
                {getFileIcon(att.filename)}
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate max-w-xs">{att.filename}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-slate-400">{formatSize(att.file_size)}</span>
                    {att.created_at && <span className="text-xs text-slate-400">{new Date(att.created_at).toLocaleDateString('zh-CN')}</span>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1 ml-3">
                <Button variant="ghost" size="icon" onClick={() => handleDownload(att)} title="下载"><Download className="w-4 h-4 text-slate-500" /></Button>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(att)} title="删除"><Trash2 className="w-4 h-4 text-red-400" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Area — 放下面 */}
      {showUpload ? (
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300 hover:border-blue-400'}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files) }}
          onClick={() => document.getElementById(`att-upload-${entityId}`)?.click()}
        >
          <input id={`att-upload-${entityId}`} type="file" multiple className="hidden" onChange={e => { handleUpload(e.target.files); if (!uploading) setShowUpload(false) }} />
          {uploading ? (
            <Loader2 className="w-8 h-8 mx-auto mb-2 text-blue-500 animate-spin" />
          ) : (
            <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
          )}
          <p className="text-sm text-slate-600">{uploading ? '上传中...' : '点击或拖拽文件到此处上传'}</p>
          <p className="text-xs text-slate-400 mt-1">支持任意文件类型</p>
          {!uploading && (
            <Button variant="ghost" size="sm" className="mt-2" onClick={e => { e.stopPropagation(); setShowUpload(false) }}>收起</Button>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center">
          <Button variant="outline" size="sm" onClick={() => setShowUpload(true)}>
            <Upload className="w-3 h-3 mr-1" />上传附件
          </Button>
        </div>
      )}
    </div>
  )
}
