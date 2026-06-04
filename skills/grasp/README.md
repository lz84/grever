# Grasp Skill Implementation

## 项目结构

```
skills/grasp/
├── Skill.md                          # 技能规范文档（已创建）
├── implementation/
│   ├── index.ts                      # 入口文件
│   ├── types.ts                      # TypeScript 类型定义
│   ├── register.ts                   # register 实现
│   ├── inject.ts                     # inject 实现
│   ├── retrieve.ts                   # retrieve 实现
│   ├── update.ts                     # update 实现
│   └── storage/
│       ├── indexer.ts                # 索引器
│       ├── store.ts                  # 存储层
│       └── migration.ts              # 迁移脚本
├── tests/
│   ├── register.test.ts
│   ├── inject.test.ts
│   ├── retrieve.test.ts
│   └── update.test.ts
└── seed/
    ├── schema.yaml                   # 初始 schema
    ├── seed_cognitions.jsonl         # 种子认知数据
    └── tag_system.yaml               # 初始标签体系
```

## 类型定义 (types.ts)

```typescript
// Grasp Skill 类型定义

export type CognitionType = 'fact' | 'pattern' | 'lesson' | 'meta';

export type CognitionStatus = 'published' | 'pending_review' | 'rejected';

export interface SourceInfo {
  agent_id: string;
  task_id?: string;
  channel: string;
}

export interface CognitionInput {
  type: CognitionType;
  content: string;
  source: SourceInfo;
  tags?: string[];
  confidence?: number;
  metadata?: object;
}

export interface CognitionItem {
  cognition_id: string;
  type: CognitionType;
  content: string;
  tags: string[];
  confidence: number;
  quality_score: number;
  source: SourceInfo;
  status: CognitionStatus;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface InjectOptions extends CognitionInput {
  // 复用了 CognitionInput 结构
}

export interface InjectResult {
  cognition_id: string;
  status: CognitionStatus;
  quality_score: number;
  created_at: string;
}

export interface RetrieveQuery {
  query: string;
  type?: CognitionType[];
  tags?: string[];
  min_confidence?: number;
  min_quality?: number;
  source_agent?: string;
  limit?: number;
  offset?: number;
}

export interface RetrieveResult {
  items: CognitionItem[];
  total: number;
  has_more: boolean;
  query_time_ms: number;
}

export interface CognitionUpdate {
  content?: string;
  tags?: string[];
  confidence?: number;
  metadata?: object;
}

export interface UpdateResult {
  cognition_id: string;
  status: CognitionStatus;
  quality_score: number;
  updated_at: string;
  version: number;
}

// 注册相关类型
export interface CognitionTypeDefinition {
  id: string;
  name: string;
  description: string;
  schema: object;
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

// 错误码
export const GRASP_ERROR_CODES = {
  INVALID_CONTENT: 'INVALID_CONTENT',
  POISON_DETECTED: 'POISON_DETECTED',
  LOW_QUALITY: 'LOW_QUALITY',
  STORAGE_ERROR: 'STORAGE_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  FORBIDDEN: 'FORBIDDEN',
  INVALID_UPDATE: 'INVALID_UPDATE',
  INVALID_REGISTRATION: 'INVALID_REGISTRATION',
} as const;

export class GraspError extends Error {
  constructor(
    public code: typeof GRASP_ERROR_CODES[keyof typeof GRASP_ERROR_CODES],
    message: string,
    public retryable: boolean = false,
    public details?: object
  ) {
    super(message);
    this.name = 'GraspError';
  }
}

// 接口定义
export interface GraspInterface {
  register(options: RegisterOptions): Promise<RegisterResult>;
  inject(options: InjectOptions): Promise<InjectResult>;
  retrieve(query: RetrieveQuery): Promise<RetrieveResult>;
  update(cognition_id: string, update: CognitionUpdate): Promise<UpdateResult>;
}
```

## 实现步骤

### 1. 创建基础存储层 (storage/store.ts)

```typescript
// 待实现：JSONL 存储和索引管理
```

### 2. 实现 inject (inject.ts)

```typescript
// 待实现：认知注入逻辑（含安全检测、质量评分）
```

### 3. 实现 retrieve (retrieve.ts)

```typescript
// 待实现：认知检索逻辑（向量检索 + 关键词检索）
```

### 4. 实现 update (update.ts)

```typescript
// 待实现：认知更新逻辑（含权限检查、版本控制）
```

### 5. 实现 register (register.ts)

```typescript
// 待实现：认知注册逻辑（schema、标签体系、规则配置）
```

### 6. 创建入口文件 (index.ts)

```typescript
// 待实现：GraspSkill 类入口，导出所有接口
```

## 种子数据

### seed/schema.yaml

```yaml
# 初始认知 schema 定义
cognitionTypes:
  - id: task_decomposition
    name: 任务分解
    description: 任务分解相关的认知类型
    
  - id: tool_usage
    name: 工具使用
    description: 工具和 API 使用相关的认知
    
  - id: best_practice
    name: 最佳实践
    description: 最佳实践相关的认知
```

### seed/tag_system.yaml

```yaml
# 初始标签体系
rootTags:
  - 任务分解
  - 最佳实践
  - 错误模式
  - 工具使用
  
tagRules:
  - parent: 任务分解
    children:
      - 依赖分析
      - 并行调度
      - 任务拆解
    allowed: true
    
  - parent: 工具使用
    children:
      - Docker
      - API
      - Python
    allowed: true
```

### seed/seed_cognitions.jsonl

```jsonl
{"cognition_id":"cog-seed-001","type":"lesson","content":"任务分解时，应先识别依赖关系再安排并行","tags":["任务分解","最佳实践"],"confidence":0.95,"quality_score":0.9,"source":{"agent_id":"system","task_id":"","channel":"seed"},"status":"published","version":1,"created_at":"2026-04-03T00:00:00Z","updated_at":"2026-04-03T00:00:00Z"}
{"cognition_id":"cog-seed-002","type":"fact","content":"Docker 镜像拉取命令是 docker pull","tags":["工具使用","Docker"],"confidence":1.0,"quality_score":0.95,"source":{"agent_id":"system","task_id":"","channel":"seed"},"status":"published","version":1,"created_at":"2026-04-03T00:00:00Z","updated_at":"2026-04-03T00:00:00Z"}
{"cognition_id":"cog-seed-003","type":"pattern","content":"任务分解应遵循 MECE 原则（相互独立，完全穷尽）","tags":["任务分解","最佳实践","方法论"],"confidence":0.9,"quality_score":0.85,"source":{"agent_id":"system","task_id":"","channel":"seed"},"status":"published","version":1,"created_at":"2026-04-03T00:00:00Z","updated_at":"2026-04-03T00:00:00Z"}
```

## 开发计划

### Phase 1: 基础框架 (1 天)
- [x] 创建 Skill.md 规范文档
- [ ] 实现 types.ts 类型定义
- [ ] 实现 storage/store.ts 基础存储层
- [ ] 实现 storage/indexer.ts 索引器

### Phase 2: 核心接口实现 (2 天)
- [ ] 实现 inject.ts（含安全检测）
- [ ] 实现 retrieve.ts（向量检索）
- [ ] 实现 update.ts（版本控制）
- [ ] 实现 register.ts（配置管理）

### Phase 3: 测试与验证 (1 天)
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] MCP 协议集成验证

### Phase 4: 种子数据与文档 (0.5 天)
- [ ] 准备种子认知数据
- [ ] 编写 README 使用指南
- [ ] 性能测试与优化

## 依赖项

```json
{
  "dependencies": {
    "uuid": ">=9.0.0",
    "jsonlines": ">=0.3.0",
    "ai-vector-store": ">=0.0.1"
  },
  "devDependencies": {
    "@types/node": ">=18.0.0",
    "typescript": ">=5.0.0",
    "jest": ">=29.0.0",
    "@types/jest": ">=29.0.0"
  }
}
```

## 下一步

1. 开始实现 types.ts 类型定义
2. 实现基础存储层
3. 逐个实现四个核心接口
4. 编写测试用例
5. 集成验证
