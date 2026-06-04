/**
 * Grasp Skill - Type Definitions
 * Nexus 认知系统的所有数据结构、接口和错误码
 */

// ============ 基础类型 ============

export type CognitionType = 'fact' | 'pattern' | 'lesson' | 'meta';
export type CognitionStatus = 'published' | 'pending_review' | 'rejected';

/** 来源信息 */
export interface SourceInfo {
  agent_id: string;
  task_id?: string;
  channel: string;
}

/** 认知条目（存储格式） */
export interface CognitionItem {
  cognition_id: string;
  type: CognitionType;
  content: string;
  tags: string[];
  confidence: number;
  quality_score: number;
  source: SourceInfo;
  metadata?: Record<string, unknown>;
  status: CognitionStatus;
  version: number;
  created_at: string;
  updated_at: string;
  domain?: string;  // 领域标签，如 "金融"、"项目管理"
}

// ============ Inject 接口 ============

export interface InjectOptions {
  type: CognitionType;
  content: string;
  source: SourceInfo;
  tags?: string[];
  confidence?: number;
  metadata?: Record<string, unknown>;
  domain?: string;  // 领域标签，如 "金融"、"项目管理"
}

export interface InjectResult {
  cognition_id: string;
  status: CognitionStatus;
  quality_score: number;
  created_at: string;
}

// ============ Retrieve 接口 ============

export interface RetrieveQuery {
  query: string;
  type?: CognitionType[];
  tags?: string[];
  status?: CognitionStatus[];
  min_confidence?: number;
  min_quality?: number;
  source_agent?: string;
  domain?: string;  // 领域过滤
  limit?: number;
  offset?: number;
}

export interface RetrieveResult {
  items: CognitionItem[];
  total: number;
  has_more: boolean;
  query_time_ms: number;
}

// ============ Update 接口 ============

export interface CognitionUpdate {
  content?: string;
  tags?: string[];
  confidence?: number;
  metadata?: Record<string, unknown>;
}

export interface UpdateResult {
  cognition_id: string;
  status: CognitionStatus;
  quality_score: number;
  updated_at: string;
  version: number;
}

// ============ Register 接口 ============

export interface CognitionTypeDefinition {
  id: string;
  name: string;
  description: string;
  schema: Record<string, unknown>;
}

export interface TagRule {
  parent: string;
  children: string[];
  allowed: boolean;
}

export interface TagSystem {
  rootTags: string[];
  tagRules: TagRule[];
}

export interface ReviewRule {
  id: string;
  condition: string;
  action: 'auto_approve' | 'auto_reject' | 'manual_review';
  confidenceThreshold?: number;
}

export interface QualityRule {
  id: string;
  dimension: string;
  weight: number;
  calculation: string;
}

export interface RegisterOptions {
  cognitionTypes?: CognitionTypeDefinition[];
  tagSystem?: TagSystem;
  reviewRules?: ReviewRule[];
  qualityRules?: QualityRule[];
}

export interface RegisterResult {
  status: 'success' | 'partial' | 'failed';
  registered: number;
  errors: ErrorInfo[];
}

export interface ErrorInfo {
  code: string;
  message: string;
  field?: string;
}

// ============ 错误处理 ============

export const GRASP_ERROR_CODES = {
  INVALID_CONTENT: 'INVALID_CONTENT',
  POISON_DETECTED: 'POISON_DETECTED',
  LOW_QUALITY: 'LOW_QUALITY',
  STORAGE_ERROR: 'STORAGE_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  FORBIDDEN: 'FORBIDDEN',
  INVALID_UPDATE: 'INVALID_UPDATE',
  INVALID_REGISTRATION: 'INVALID_REGISTRATION',
  DOMAIN_NOT_FOUND: 'DOMAIN_NOT_FOUND',
  DOMAIN_EXISTS: 'DOMAIN_EXISTS',
} as const;

export type GraspErrorCode = typeof GRASP_ERROR_CODES[keyof typeof GRASP_ERROR_CODES];

export class GraspError extends Error {
  constructor(
    public code: GraspErrorCode,
    message: string,
    public retryable: boolean = false,
    public details?: Record<string, unknown>
  ) {
    super(`[${code}] ${message}`);
    this.name = 'GraspError';
  }
}

// ============ 领域接口 ============

export interface Domain {
  name: string;           // 领域名称，如 "Nexus项目"、"软件项目管理"
  description?: string;    // 领域描述
  created_at: string;     // 创建时间
  cognition_count: number; // 该领域下的认知数量
}

export interface RegisterDomainOptions {
  name: string;           // 领域名称
  description?: string;   // 领域描述
}

export interface DomainStats {
  domains: Domain[];
  total_cognitions: number;
}

// ============ 存储接口 ============

export interface QueryFilters {
  type?: CognitionType[];
  tags?: string[];
  status?: CognitionStatus[];
  min_confidence?: number;
  min_quality?: number;
  source_agent?: string;
  created_after?: string;
  created_before?: string;
}

export interface Pagination {
  limit: number;
  offset: number;
}

export interface CognitionStore {
  write(cognition: CognitionItem): Promise<void>;
  read(cognition_id: string): Promise<CognitionItem | null>;
  update(cognition: CognitionItem): Promise<void>;
  delete(cognition_id: string): Promise<void>;
  query(filters: QueryFilters, pagination?: Pagination): Promise<{ items: CognitionItem[]; total: number }>;
  generateId(): string;
}

export interface Indexer {
  index(cognition: CognitionItem): Promise<void>;
  unindex(cognition_id: string): Promise<void>;
  vectorSearch(query: string, options?: { topK?: number; minScore?: number }): Promise<string[]>;
  keywordSearch(query: string, options?: { topK?: number; fields?: string[] }): Promise<string[]>;
  refresh(): Promise<void>;
}
