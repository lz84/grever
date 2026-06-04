import { useState, useEffect } from 'react'
import { toast } from "sonner"
import { Upload, Trash2, Download, FileText, Image, File, X, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Badge } from '@/shared/components/ui/badge'
import { Card, CardContent } from '@/shared/components/ui/card'
import { tasksApi } from '@/shared/utils/api'

interface Attachment {
  id: string
  task_id: string
  filename: string
  file_type: string
  file_size: number
  uploaded_at: string
  uploader: string | null
}

interface AttachmentPanelProps {
  taskId: string
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
  const codeExts = ['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'c', 'cpp', 'go', 'rs', 'sh', 'bash']
  const dataExts = ['csv', 'json', 'xml', 'yaml', 'yml', 'sql']

  if (imageExts.includes(ext)) return <Image className="w-5 h-5 text-purple-500" />
  if (docExts.includes(ext)) return <FileText className="w-5 h-5 text-blue-500" />
  if (codeExts.includes(ext)) return <FileText className="w-5 h-5 text-green-500" />
  if (dataExts.includes(ext)) return <File className="w-5 h-5 text-orange-500" />
  return <File className="w-5 h-5 text-slate-400" />
}

export function AttachmentPanel({ taskId }: AttachmentPanelProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    loadAttachments()
  }, [taskId])

  async function loadAttachments() {
    setLoading(true)
    try {
      const data = await tasksApi.getAttachments(taskId)
      setAttachments(Array.isArray(data) ? data : (data.attachments || []))
    } catch (e) {
      console.error('Failed to load attachments', e)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return
    setUploading(true)
    let uploaded = 0
    let failed = 0
    for (const file of Array.from(files)) {
      try {
        const resp = await tasksApi.uploadAttachment(taskId, file)
        if (resp.ok) {
          uploaded++
        } else {
          failed++
        }
      } catch (e) {
        failed++
      }
    }
    if (uploaded > 0) toast.success(`上传成功 ${uploaded} 个文件`)
    if (failed > 0) toast.error(`${failed} 个文件上传失败`)
    setUploading(false)
    loadAttachments()
  }

  async function handleDelete(attachmentId: string) {
    try {
      await tasksApi.deleteAttachment(taskId, attachmentId)
      toast.success('附件已删除')
      loadAttachments()
    } catch (e) {
      toast.error('删除失败')
    }
  }

  async function handleDownload(attachment: Attachment) {
    try {
      const resp = await tasksApi.downloadAttachment(taskId, attachment.id)
      if (resp && resp.ok) {
        const blob = await resp.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = attachment.filename
        a.click()
        URL.revokeObjectURL(url)
      } else {
        toast.error('下载失败')
      }
    } catch (e) {
      toast.error('下载失败')
    }
  }

  return (
    <div className="p-4 space-y-4">
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300 hover:border-blue-400'}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => {
          e.preventDefault()
          setDragOver(false)
          handleUpload(e.dataTransfer.files)
        }}
        onClick={() => document.getElementById('attachment-upload')?.click()}
      >
        <input
          id="attachment-upload"
          type="file"
          multiple
          className="hidden"
          onChange={e => handleUpload(e.target.files)}
        />
        {uploading ? (
          <Loader2 className="w-8 h-8 mx-auto mb-2 text-blue-500 animate-spin" />
        ) : (
          <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
        )}
        <p className="text-sm text-slate-600">
          {uploading ? '上传中...' : '点击或拖拽文件到此处上传'}
        </p>
        <p className="text-xs text-slate-400 mt-1">支持任意文件类型</p>
      </div>

      {/* File List */}
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
                    {att.uploaded_at && (
                      <span className="text-xs text-slate-400">
                        {new Date(att.uploaded_at).toLocaleDateString('zh-CN')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1 ml-3">
                <Button variant="ghost" size="icon" onClick={() => handleDownload(att)} title="下载">
                  <Download className="w-4 h-4 text-slate-500" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(att.id)} title="删除">
                  <Trash2 className="w-4 h-4 text-red-400" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AttachmentPanel
