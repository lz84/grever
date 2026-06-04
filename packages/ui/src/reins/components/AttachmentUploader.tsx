/**
 * AttachmentUploader - 通用附件上传组件
 * Sprint 84: 统一附件体系
 *
 * 支持:
 * - 拖拽上传 + 点击选择
 * - 上传进度显示
 * - 已上传附件列表
 * - 删除附件
 * - sha256 去重（后端）
 */

import { useState, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { Upload, Trash2, Download, FileText, Image, File, X, Loader2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Progress } from '@/shared/components/ui/progress'
import { attachmentsApi } from '@/shared/utils/api'

// 类型定义
export interface Attachment {
  id: string
  filename: string
  file_size: number
  mime_type: string
  sha256_hash: string
  created_at: string
  created_by: string | null
  reused?: boolean
}

interface AttachmentUploaderProps {
  entityType: 'goal' | 'project' | 'task' | 'scenario' | 'step' | 'agent'
  entityId: string
  maxSize?: number // bytes, default 50MB
  onUploadComplete?: (attachment: Attachment) => void
  onDelete?: (attachmentId: string) => void
}

const DEFAULT_MAX_SIZE = 50 * 1024 * 1024 // 50MB

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

export function AttachmentUploader({
  entityType,
  entityId,
  maxSize = DEFAULT_MAX_SIZE,
  onUploadComplete,
  onDelete,
}: AttachmentUploaderProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 加载现有附件
  useEffect(() => {
    loadAttachments()
  }, [entityType, entityId])

  async function loadAttachments() {
    setLoading(true)
    try {
      const data = await attachmentsApi.list(entityType, entityId)
      setAttachments(Array.isArray(data) ? data : (data.attachments || []))
    } catch (e) {
      console.error('Failed to load attachments', e)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return
    
    const validFiles = Array.from(files).filter(file => {
      if (file.size > maxSize) {
        toast.error(`${file.name}: 文件过大（最大 ${formatSize(maxSize)}）`)
        return false
      }
      return true
    })

    if (validFiles.length === 0) return

    setUploading(true)
    let uploaded = 0
    let failed = 0

    for (const file of validFiles) {
      try {
        // 设置进度
        setUploadProgress(0)
        
        // 上传附件
        const result = await attachmentsApi.upload(file, entityType, entityId)
        
        if (result.attachment_id) {
          const attachment: Attachment = {
            id: result.attachment_id,
            filename: result.filename,
            file_size: result.file_size,
            mime_type: result.mime_type || '',
            sha256_hash: '',
            created_at: new Date().toISOString(),
            created_by: null,
            reused: result.reused || false,
          }
          setAttachments(prev => [attachment, ...prev])
          uploaded++
          
          if (onUploadComplete) {
            onUploadComplete(attachment)
          }
          
          if (result.reused) {
            toast.info(`${file.name}: 文件已存在，复用附件`)
          } else {
            toast.success(`${file.name}: 上传成功`)
          }
        } else {
          failed++
          toast.error(`${file.name}: 上传失败`)
        }
        setUploadProgress(100)
      } catch (e: any) {
        failed++
        console.error('Upload error:', e)
        toast.error(`${file.name}: ${e.message || '上传失败'}`)
      }
    }

    setUploading(false)
    setUploadProgress(0)
    
    if (uploaded > 0) {
      loadAttachments()
    }
  }

  async function handleDelete(attachmentId: string, entityT: string, entityI: string) {
    try {
      await attachmentsApi.unlink(attachmentId, entityT, entityI)
      toast.success('附件已取消关联')
      setAttachments(prev => prev.filter(a => a.id !== attachmentId))
      
      if (onDelete) {
        onDelete(attachmentId)
      }
    } catch (e) {
      toast.error('删除失败')
    }
  }

  async function handleDownload(attachment: Attachment) {
    try {
      const resp = await attachmentsApi.download(attachment.id, true)
      if (!resp.ok) throw new Error('下载失败')
      
      const blob = await resp.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = attachment.filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      toast.error('下载失败')
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  return (
    <div className="space-y-4">
      {/* 上传区域 */}
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragOver ? 'border-primary bg-primary/5' : 'border-slate-300 dark:border-slate-600'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          onChange={(e) => handleUpload(e.target.files)}
        />
        
        <div className="space-y-2">
          <Upload className="w-10 h-10 mx-auto text-slate-400" />
          <p className="text-sm text-slate-600 dark:text-slate-400">
            拖拽文件到此处，或点击选择
          </p>
          <p className="text-xs text-slate-500">
            最大 {formatSize(maxSize)}，不允许多执行文件
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                上传中...
              </>
            ) : (
              '选择文件'
            )}
          </Button>
        </div>
        
        {/* 进度条 */}
        {uploading && (
          <div className="mt-4">
            <Progress value={uploadProgress} className="w-full max-w-xs mx-auto" />
          </div>
        )}
      </div>

      {/* 已上传附件列表 */}
      {attachments.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
            已上传附件 ({attachments.length})
          </h3>
          
          <div className="space-y-2">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="flex items-center justify-between p-3 border border-slate-200 dark:border-slate-700 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {getFileIcon(attachment.filename)}
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                      {attachment.filename}
                    </span>
                    <span className="text-xs text-slate-500">
                      {formatSize(attachment.file_size)}
                      {attachment.reused && ' (复用)'}
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-slate-500"
                    onClick={() => handleDownload(attachment)}
                    title="下载"
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                    onClick={() => handleDelete(attachment.id, entityType, entityId)}
                    title="取消关联"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AttachmentUploader
