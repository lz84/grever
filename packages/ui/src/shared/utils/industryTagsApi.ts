/**
 * Industry Capability Tags API
 * Sprint 93: 能力标签库
 * 
 * ⚠️ 所有路径从 api/paths.ts 导入
 */
import { request } from './api'
import { INDUSTRY_TAGS, INDUSTRY_PACKS } from '../api/paths'

// ==================== Types ====================

export type TagDimension = 'business' | 'professional' | 'technical' | 'management'
export type TagLevel = 'basic' | 'intermediate' | 'advanced'
export type TagStatus = 'active' | 'deprecated' | 'replaced_by'
export type PackStatus = 'draft' | 'published' | 'deprecated'
export type PackType = 'standard' | 'custom'

export interface IndustryTag {
  id: string
  industry: string
  tag_name: string
  tag_name_en?: string
  description: string
  dimension: TagDimension
  level: TagLevel
  prerequisites: string[]
  tools: string[]
  examples: string[]
  status: TagStatus
  replaced_by?: string
  version_major: number
  version_minor: number
  version_patch: number
  created_at: number
  updated_at?: number
}

export interface IndustryPack {
  id: string
  name: string
  industry: string
  version: string
  description?: string
  tags_count: number
  scenarios_count: number
  skills_count: number
  knowledge_count: number
  agent_schemes_count: number
  versions_count: number
  status: PackStatus
  pack_type?: PackType
  base_pack_id?: string
  created_at: number
  updated_at?: number
}

export interface IndustryPackDetail extends IndustryPack {
  contents: IndustryPackContentItem[]
}

export interface IndustryPackContentItem {
  pack_id: string
  content_type: string
  content_id: string
}

// ==================== Tags API ====================

export const industryTagsApi = {
  list: (params?: { industry?: string; dimension?: TagDimension; level?: TagLevel; status?: TagStatus; search?: string; page?: number; page_size?: number }) =>
    request<{ items: IndustryTag[]; total: number; page: number; page_size: number }>(INDUSTRY_TAGS.LIST, { params }),
  get: (tagId: string) => request<IndustryTag>(INDUSTRY_TAGS.GET(tagId)),
  create: (data: Partial<IndustryTag>) =>
    request<{ success: boolean; id: string }>(INDUSTRY_TAGS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (tagId: string, data: Partial<IndustryTag>) =>
    request<{ success: boolean; id: string }>(INDUSTRY_TAGS.UPDATE(tagId), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (tagId: string) =>
    request<{ success: boolean; id: string }>(INDUSTRY_TAGS.REMOVE(tagId), { method: 'DELETE' }),
  listIndustries: () => request<string[]>(INDUSTRY_TAGS.GET_INDUSTRIES),
  listByIndustry: (industry: string) =>
    request<{ items: IndustryTag[]; total: number; industry: string }>(INDUSTRY_TAGS.GET_BY_INDUSTRY(industry)),
  getTagStats: (tagId: string) =>
    request<{ tasks_using: { id: string; title: string }[]; agents_using: { id: string; name: string }[]; usage_count: number }>(`${INDUSTRY_TAGS.GET_STATS}?tag_id=${encodeURIComponent(tagId)}`),
  getReferences: (tagId: string) =>
    request<{ tag_id: string; task_count: number; scenario_count: number; agent_count: number; total_count: number }>(INDUSTRY_TAGS.GET_REFERENCES(tagId)),
  getAgentIndustryTags: (agentId: string) =>
    request<{ agent_id: string; manual_tags: any[]; inferred_tags: any[] }>(`${INDUSTRY_TAGS.AGENT_TAGS}?agent_id=${encodeURIComponent(agentId)}`),
}

// ==================== Packs API ====================

export const industryPacksApi = {
  list: (params?: { industry?: string; status?: PackStatus; page?: number; page_size?: number }) =>
    request<{ items: IndustryPack[]; total: number; page: number; page_size: number }>(INDUSTRY_PACKS.LIST, { params }),
  get: (packId: string) => request<IndustryPackDetail>(INDUSTRY_PACKS.GET(packId)),
  create: (data: Partial<IndustryPack>) =>
    request<{ success: boolean; id: string }>(INDUSTRY_PACKS.CREATE, { method: 'POST', body: JSON.stringify(data) }),
  update: (packId: string, data: Partial<IndustryPack>) =>
    request<{ success: boolean; id: string }>(INDUSTRY_PACKS.UPDATE(packId), { method: 'PUT', body: JSON.stringify(data) }),
  remove: (packId: string) =>
    request<{ success: boolean; id: string }>(INDUSTRY_PACKS.REMOVE(packId), { method: 'DELETE' }),
}
