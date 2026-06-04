/**
 * CriteriaRenderer — 统一验收标准渲染组件
 * 解析 JSON 格式 {"criteria": [{"type": "compile|api|page|integration|custom", "name": "检查名", "desc": "描述"}]}
 * 支持 done_criteria / delivery_criteria / acceptance_criteria 三种区域
 */
import React from 'react'
import { Badge } from '@/shared/components/ui/badge'

const TYPE_BADGE: Record<string, string> = {
  compile: 'bg-slate-100 text-slate-700',
  api: 'bg-blue-100 text-blue-700',
  page: 'bg-green-100 text-green-700',
  custom: 'bg-purple-100 text-purple-700',
  subjective: 'bg-amber-100 text-amber-700',
  integration: 'bg-indigo-100 text-indigo-700',
}

const TYPE_LABEL: Record<string, string> = {
  compile: '编译', api: 'API', page: '页面',
  custom: '自定义', subjective: '主观', integration: '集成',
}

export interface CriteriaItem {
  type?: string
  name?: string
  desc?: string
  description?: string
  endpoint?: string
  url?: string
}

export interface CriteriaRendererProps {
  /** Raw JSON string or parsed object */
  value: string | object | null | undefined
  /** Badge label color override */
  badgeClass?: string
  /** Default label if type missing */
  defaultLabel?: string
  /** Section title */
  title?: string
}

function parseCriteria(value: string | object | null | undefined): CriteriaItem[] | null {
  if (!value) return null
  let raw: any = value
  if (typeof value === 'string') {
    try { raw = JSON.parse(value) } catch { return null }
  }
  const criteria = raw.criteria || raw
  if (!Array.isArray(criteria)) return null
  return criteria
}

export default function CriteriaRenderer({ value, badgeClass, defaultLabel, title }: CriteriaRendererProps) {
  const items = parseCriteria(value)
  if (!items || items.length === 0) return null

  return (
    <div>
      {title && <h4 className="text-sm font-medium text-slate-500 mb-2">{title}</h4>}
      <div className="space-y-2">
        {items.map((c, i) => (
          <div key={i} className="flex items-start gap-2 p-2 bg-slate-50 rounded-sm">
            <span className="text-xs font-medium text-slate-400 min-w-[20px]">{i + 1}.</span>
            <Badge variant="secondary" className={`text-xs mt-0.5 ${badgeClass || TYPE_BADGE[c.type || ''] || 'bg-slate-100 text-slate-600'}`}>
              {TYPE_LABEL[c.type || ''] || defaultLabel || c.type || '检查'}
            </Badge>
            <span className="text-sm text-slate-700">
              {c.name && <span className="font-medium">{c.name}</span>}
              {(c.name && c.desc) && <span className="text-slate-500">: </span>}
              {c.desc && <span className="text-slate-500">{c.desc}</span>}
              {!c.desc && !c.name && <span className="text-slate-500">{c.description || ''}</span>}
            </span>
            {c.endpoint && <span className="text-xs text-blue-500 font-mono ml-1">{c.endpoint}</span>}
            {c.url && <span className="text-xs text-green-500 font-mono ml-1">{c.url}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
