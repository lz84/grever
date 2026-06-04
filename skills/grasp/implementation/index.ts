/**
 * Grasp Skill - 入口文件
 * Nexus 认知系统的对外接口封装
 */

export * from './types';

export { registerService, register, getRegisteredConfig, loadConfig } from './register';
export { injectService, inject } from './inject';
export { retrieveService, retrieve, batchRetrieve, getById, getByType, getByTags } from './retrieve';
export { updateService, update, revert, softDelete } from './update';
export { domainRegistrationService, registerDomain, getDomainStats } from './register';

export { JsonlCognitionStore, createCognitionStore } from './storage/store';
export { GraspIndexer, createIndexer } from './storage/indexer';

export class GraspSkill {
  async register(options: import('./types').RegisterOptions): Promise<import('./types').RegisterResult> {
    const { register } = await import('./register');
    return register(options);
  }

  async inject(options: import('./types').InjectOptions): Promise<import('./types').InjectResult> {
    const { inject } = await import('./inject');
    return inject(options);
  }

  async retrieve(query: import('./types').RetrieveQuery): Promise<import('./types').RetrieveResult> {
    const { retrieve } = await import('./retrieve');
    return retrieve(query);
  }

  async update(
    cognitionId: string,
    update: import('./types').CognitionUpdate,
    agentId?: string
  ): Promise<import('./types').UpdateResult> {
    const { update: doUpdate } = await import('./update');
    return doUpdate(cognitionId, update, agentId);
  }
}

export function createGraspSkill(): GraspSkill {
  return new GraspSkill();
}

export const GRASP_TOOLS = [
  {
    name: 'grasp_register',
    description: '注册认知模式的定义、标签体系、审核规则',
    inputSchema: {
      type: 'object' as const,
      properties: {
        cognitionTypes: {
          type: 'array' as const,
          items: {
            type: 'object' as const,
            properties: {
              id: { type: 'string' as const },
              name: { type: 'string' as const },
              description: { type: 'string' as const },
              schema: { type: 'object' as const },
            },
            required: ['id', 'name', 'description', 'schema'],
          },
        },
        tagSystem: {
          type: 'object' as const,
          properties: {
            rootTags: { type: 'array' as const, items: { type: 'string' as const } },
            tagRules: {
              type: 'array' as const,
              items: {
                type: 'object' as const,
                properties: {
                  parent: { type: 'string' as const },
                  children: { type: 'array' as const, items: { type: 'string' as const } },
                  allowed: { type: 'boolean' as const },
                },
                required: ['parent', 'children', 'allowed'],
              },
            },
          },
          required: ['rootTags', 'tagRules'],
        },
        reviewRules: {
          type: 'array' as const,
          items: {
            type: 'object' as const,
            properties: {
              id: { type: 'string' as const },
              condition: { type: 'string' as const },
              action: { type: 'string' as const, enum: ['auto_approve', 'auto_reject', 'manual_review'] as const },
              confidenceThreshold: { type: 'number' as const },
            },
            required: ['id', 'condition', 'action'],
          },
        },
      },
    },
  },
  {
    name: 'grasp_inject',
    description: '将新认知注入到知识库',
    inputSchema: {
      type: 'object' as const,
      properties: {
        type: {
          type: 'string' as const,
          enum: ['fact', 'pattern', 'lesson', 'meta'] as const,
        },
        content: { type: 'string' as const },
        source: {
          type: 'object' as const,
          properties: {
            agent_id: { type: 'string' as const },
            task_id: { type: 'string' as const },
            channel: { type: 'string' as const },
          },
          required: ['agent_id', 'channel'],
        },
        tags: { type: 'array' as const, items: { type: 'string' as const } },
        confidence: { type: 'number' as const, minimum: 0, maximum: 1 },
        metadata: { type: 'object' as const },
      },
      required: ['type', 'content', 'source'],
    },
  },
  {
    name: 'grasp_retrieve',
    description: '从知识库检索认知',
    inputSchema: {
      type: 'object' as const,
      properties: {
        query: { type: 'string' as const },
        type: {
          type: 'array' as const,
          items: { type: 'string' as const, enum: ['fact', 'pattern', 'lesson', 'meta'] as const },
        },
        tags: { type: 'array' as const, items: { type: 'string' as const } },
        status: {
          type: 'array' as const,
          items: { type: 'string' as const, enum: ['published', 'pending_review', 'rejected'] as const },
        },
        min_confidence: { type: 'number' as const, minimum: 0, maximum: 1 },
        min_quality: { type: 'number' as const, minimum: 0, maximum: 1 },
        source_agent: { type: 'string' as const },
        limit: { type: 'number' as const, default: 10 },
        offset: { type: 'number' as const, default: 0 },
      },
      required: ['query'],
    },
  },
  {
    name: 'grasp_update',
    description: '更新已有认知',
    inputSchema: {
      type: 'object' as const,
      properties: {
        cognition_id: { type: 'string' as const },
        content: { type: 'string' as const },
        tags: { type: 'array' as const, items: { type: 'string' as const } },
        confidence: { type: 'number' as const, minimum: 0, maximum: 1 },
        metadata: { type: 'object' as const },
      },
      required: ['cognition_id'],
    },
  },
];

export const GRASP_RESOURCES = [
  {
    uri: 'grasp://cognition/{id}',
    name: '认知条目',
    mimeType: 'application/json',
  },
  {
    uri: 'grasp://cognitions',
    name: '认知列表',
    mimeType: 'application/json',
  },
  {
    uri: 'grasp://types',
    name: '认知类型定义',
    mimeType: 'application/json',
  },
  {
    uri: 'grasp://tags',
    name: '标签体系',
    mimeType: 'application/json',
  },
];
