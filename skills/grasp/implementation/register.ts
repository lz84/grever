/**
 * Grasp Skill - register 接口实现
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import {
  RegisterOptions,
  RegisterResult,
  ErrorInfo,
  CognitionTypeDefinition,
  TagSystem,
  ReviewRule,
  QualityRule,
} from './types';

const MEMORY_PATH = path.join(process.cwd(), 'memory', 'grasp');
const SCHEMA_FILE = 'schema.yaml';
const TAG_SYSTEM_FILE = 'tag_system.yaml';
const REVIEW_RULES_FILE = 'review_rules.yaml';
const QUALITY_RULES_FILE = 'quality_rules.yaml';

interface RegisteredConfig {
  cognitionTypes: CognitionTypeDefinition[];
  tagSystem: TagSystem | null;
  reviewRules: ReviewRule[];
  qualityRules: QualityRule[];
}

/** 内存中的注册配置 */
let registeredConfig: RegisteredConfig = {
  cognitionTypes: [],
  tagSystem: null,
  reviewRules: [],
  qualityRules: [],
};

/** 验证认知类型定义 */
function validateCognitionType(type: CognitionTypeDefinition): ErrorInfo | null {
  if (!type.id || typeof type.id !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'CognitionType id is required', field: 'id' };
  }
  if (!type.name || typeof type.name !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'CognitionType name is required', field: 'name' };
  }
  if (!type.description || typeof type.description !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'CognitionType description is required', field: 'description' };
  }
  if (!type.schema || typeof type.schema !== 'object') {
    return { code: 'INVALID_REGISTRATION', message: 'CognitionType schema must be an object', field: 'schema' };
  }
  return null;
}

/** 验证标签体系 */
function validateTagSystem(tagSystem: TagSystem): ErrorInfo | null {
  if (!tagSystem.rootTags || !Array.isArray(tagSystem.rootTags)) {
    return { code: 'INVALID_REGISTRATION', message: 'TagSystem rootTags must be an array', field: 'rootTags' };
  }
  if (tagSystem.rootTags.length === 0) {
    return { code: 'INVALID_REGISTRATION', message: 'TagSystem rootTags cannot be empty', field: 'rootTags' };
  }
  if (tagSystem.tagRules && !Array.isArray(tagSystem.tagRules)) {
    return { code: 'INVALID_REGISTRATION', message: 'TagSystem tagRules must be an array', field: 'tagRules' };
  }
  return null;
}

/** 验证审核规则 */
function validateReviewRule(rule: ReviewRule): ErrorInfo | null {
  if (!rule.id || typeof rule.id !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'ReviewRule id is required', field: 'id' };
  }
  if (!rule.condition || typeof rule.condition !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'ReviewRule condition is required', field: 'condition' };
  }
  if (!['auto_approve', 'auto_reject', 'manual_review'].includes(rule.action)) {
    return { code: 'INVALID_REGISTRATION', message: 'ReviewRule action must be one of: auto_approve, auto_reject, manual_review', field: 'action' };
  }
  return null;
}

/** 验证质量规则 */
function validateQualityRule(rule: QualityRule): ErrorInfo | null {
  if (!rule.id || typeof rule.id !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'QualityRule id is required', field: 'id' };
  }
  if (!rule.dimension || typeof rule.dimension !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'QualityRule dimension is required', field: 'dimension' };
  }
  if (typeof rule.weight !== 'number' || rule.weight < 0 || rule.weight > 1) {
    return { code: 'INVALID_REGISTRATION', message: 'QualityRule weight must be a number between 0 and 1', field: 'weight' };
  }
  if (!rule.calculation || typeof rule.calculation !== 'string') {
    return { code: 'INVALID_REGISTRATION', message: 'QualityRule calculation is required', field: 'calculation' };
  }
  return null;
}

/** 确保目录存在 */
function ensureDirectory(): void {
  if (!fs.existsSync(MEMORY_PATH)) {
    fs.mkdirSync(MEMORY_PATH, { recursive: true });
  }
}

/** 保存配置到 YAML 文件 */
function saveConfig(): void {
  ensureDirectory();

  if (registeredConfig.cognitionTypes.length > 0) {
    fs.writeFileSync(
      path.join(MEMORY_PATH, SCHEMA_FILE),
      yaml.dump({ cognitionTypes: registeredConfig.cognitionTypes }),
      'utf-8'
    );
  }

  if (registeredConfig.tagSystem) {
    fs.writeFileSync(
      path.join(MEMORY_PATH, TAG_SYSTEM_FILE),
      yaml.dump(registeredConfig.tagSystem),
      'utf-8'
    );
  }

  if (registeredConfig.reviewRules.length > 0) {
    fs.writeFileSync(
      path.join(MEMORY_PATH, REVIEW_RULES_FILE),
      yaml.dump({ reviewRules: registeredConfig.reviewRules }),
      'utf-8'
    );
  }

  if (registeredConfig.qualityRules.length > 0) {
    fs.writeFileSync(
      path.join(MEMORY_PATH, QUALITY_RULES_FILE),
      yaml.dump({ qualityRules: registeredConfig.qualityRules }),
      'utf-8'
    );
  }
}

/** 注册服务类 */
export class RegisterService {
  async register(options: RegisterOptions): Promise<RegisterResult> {
    const errors: ErrorInfo[] = [];
    let registered = 0;

    // 注册认知类型
    if (options.cognitionTypes && options.cognitionTypes.length > 0) {
      for (const type of options.cognitionTypes) {
        const error = validateCognitionType(type);
        if (error) {
          errors.push(error);
          continue;
        }

        // 检查是否已存在
        const existing = registeredConfig.cognitionTypes.find(t => t.id === type.id);
        if (existing) {
          // 更新现有类型
          Object.assign(existing, type);
        } else {
          registeredConfig.cognitionTypes.push(type);
        }
        registered++;
      }
    }

    // 注册标签体系
    if (options.tagSystem) {
      const error = validateTagSystem(options.tagSystem);
      if (error) {
        errors.push(error);
      } else {
        registeredConfig.tagSystem = options.tagSystem;
        registered++;
      }
    }

    // 注册审核规则
    if (options.reviewRules && options.reviewRules.length > 0) {
      for (const rule of options.reviewRules) {
        const error = validateReviewRule(rule);
        if (error) {
          errors.push(error);
          continue;
        }

        const existing = registeredConfig.reviewRules.find(r => r.id === rule.id);
        if (existing) {
          Object.assign(existing, rule);
        } else {
          registeredConfig.reviewRules.push(rule);
        }
        registered++;
      }
    }

    // 注册质量规则
    if (options.qualityRules && options.qualityRules.length > 0) {
      for (const rule of options.qualityRules) {
        const error = validateQualityRule(rule);
        if (error) {
          errors.push(error);
          continue;
        }

        const existing = registeredConfig.qualityRules.find(r => r.id === rule.id);
        if (existing) {
          Object.assign(existing, rule);
        } else {
          registeredConfig.qualityRules.push(rule);
        }
        registered++;
      }
    }

    // 保存配置
    if (registered > 0) {
      saveConfig();
    }

    // 确定状态
    let status: 'success' | 'partial' | 'failed' = 'success';
    if (errors.length > 0 && registered > 0) {
      status = 'partial';
    } else if (errors.length > 0 && registered === 0) {
      status = 'failed';
    }

    return {
      status,
      registered,
      errors,
    };
  }
}

export const registerService = new RegisterService();

export async function register(options: RegisterOptions): Promise<RegisterResult> {
  return registerService.register(options);
}

/** 获取已注册的配置 */
export function getRegisteredConfig(): RegisteredConfig {
  return { ...registeredConfig };
}

/** 加载已保存的配置 */
export function loadConfig(): void {
  try {
    if (fs.existsSync(path.join(MEMORY_PATH, SCHEMA_FILE))) {
      const content = fs.readFileSync(path.join(MEMORY_PATH, SCHEMA_FILE), 'utf-8');
      const data = yaml.load(content) as { cognitionTypes?: CognitionTypeDefinition[] };
      if (data?.cognitionTypes) {
        registeredConfig.cognitionTypes = data.cognitionTypes;
      }
    }

    if (fs.existsSync(path.join(MEMORY_PATH, TAG_SYSTEM_FILE))) {
      const content = fs.readFileSync(path.join(MEMORY_PATH, TAG_SYSTEM_FILE), 'utf-8');
      registeredConfig.tagSystem = yaml.load(content) as TagSystem;
    }

    if (fs.existsSync(path.join(MEMORY_PATH, REVIEW_RULES_FILE))) {
      const content = fs.readFileSync(path.join(MEMORY_PATH, REVIEW_RULES_FILE), 'utf-8');
      const data = yaml.load(content) as { reviewRules?: ReviewRule[] };
      if (data?.reviewRules) {
        registeredConfig.reviewRules = data.reviewRules;
      }
    }

    if (fs.existsSync(path.join(MEMORY_PATH, QUALITY_RULES_FILE))) {
      const content = fs.readFileSync(path.join(MEMORY_PATH, QUALITY_RULES_FILE), 'utf-8');
      const data = yaml.load(content) as { qualityRules?: QualityRule[] };
      if (data?.qualityRules) {
        registeredConfig.qualityRules = data.qualityRules;
      }
    }
  } catch {
    // Ignore load errors
  }
}

// ============ 领域注册 ============

import { getDomainRegistry } from './storage/domainRegistry';
import {
  RegisterDomainOptions,
  Domain,
  DomainStats,
} from './types';

export class DomainRegistrationService {
  /**
   * 注册新领域
   */
  registerDomain(options: RegisterDomainOptions): Domain {
    const registry = getDomainRegistry();
    return registry.register(options);
  }

  /**
   * 获取领域信息
   */
  getDomain(name: string): Domain | undefined {
    const registry = getDomainRegistry();
    return registry.get(name);
  }

  /**
   * 获取所有领域
   */
  listDomains(): Domain[] {
    const registry = getDomainRegistry();
    return registry.list();
  }

  /**
   * 检查领域是否存在
   */
  hasDomain(name: string): boolean {
    const registry = getDomainRegistry();
    return registry.exists(name);
  }

  /**
   * 删除领域
   */
  deleteDomain(name: string): boolean {
    const registry = getDomainRegistry();
    return registry.delete(name);
  }

  /**
   * 获取领域统计
   */
  getDomainStats(): DomainStats {
    const registry = getDomainRegistry();
    return registry.getStats();
  }

  /**
   * 验证领域是否存在（用于 inject 时的验证）
   */
  validateDomain(name: string): boolean {
    const registry = getDomainRegistry();
    return registry.exists(name);
  }
}

export const domainRegistrationService = new DomainRegistrationService();

export function registerDomain(options: RegisterDomainOptions): Domain {
  return domainRegistrationService.registerDomain(options);
}

export function getDomainStats(): DomainStats {
  return domainRegistrationService.getDomainStats();
}
