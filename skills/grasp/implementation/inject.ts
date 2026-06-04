/**
 * Grasp Skill - inject 接口实现
 * 将新认知注入到本地知识库
 */

import {
  InjectOptions,
  InjectResult,
  CognitionItem,
  CognitionStatus,
  GraspError,
  GRASP_ERROR_CODES,
  SourceInfo,
} from './types';
import { createCognitionStore } from './storage/store';
import { createIndexer } from './storage/indexer';
import { getDomainRegistry } from './storage/domainRegistry';

const QUALITY_THRESHOLD_AUTO_PUBLISH = 0.7;
const QUALITY_THRESHOLD_AUTO_REJECT = 0.15;
const POISON_RISK_THRESHOLD = 0.4;

function validateContent(content: string): { valid: boolean; error?: string } {
  if (!content || typeof content !== 'string') {
    return { valid: false, error: 'Content must be a non-empty string' };
  }
  const trimmed = content.trim();
  if (trimmed.length < 10) {
    return { valid: false, error: 'Content too short (minimum 10 characters)' };
  }
  if (trimmed.length > 10000) {
    return { valid: false, error: 'Content too long (maximum 10000 characters)' };
  }
  return { valid: true };
}

function validateSource(source: SourceInfo): { valid: boolean; error?: string } {
  if (!source || typeof source !== 'object') {
    return { valid: false, error: 'Source must be an object' };
  }
  if (!source.agent_id || typeof source.agent_id !== 'string') {
    return { valid: false, error: 'Source agent_id is required' };
  }
  if (!source.channel || typeof source.channel !== 'string') {
    return { valid: false, error: 'Source channel is required' };
  }
  return { valid: true };
}

function validateType(type: string): { valid: boolean; error?: string } {
  const validTypes = ['fact', 'pattern', 'lesson', 'meta'];
  if (!validTypes.includes(type)) {
    return { valid: false, error: `Invalid type. Must be one of: ${validTypes.join(', ')}` };
  }
  return { valid: true };
}

function validateConfidence(confidence?: number): { valid: boolean; error?: string } {
  if (confidence !== undefined) {
    if (typeof confidence !== 'number' || confidence < 0 || confidence > 1) {
      return { valid: false, error: 'Confidence must be a number between 0 and 1' };
    }
  }
  return { valid: true };
}

function validateTags(tags?: string[]): { valid: boolean; error?: string } {
  if (tags !== undefined) {
    if (!Array.isArray(tags)) {
      return { valid: false, error: 'Tags must be an array' };
    }
    if (tags.length > 10) {
      return { valid: false, error: 'Tags cannot exceed 10 items' };
    }
    for (const tag of tags) {
      if (typeof tag !== 'string' || tag.trim().length === 0) {
        return { valid: false, error: 'Each tag must be a non-empty string' };
      }
    }
  }
  return { valid: true };
}

async function detectPoison(
  content: string,
  source: SourceInfo
): Promise<{ riskScore: number; factors: string[] }> {
  const factors: string[] = [];
  let riskScore = 0;

  const suspiciousAgents = ['agent-troll', 'malicious-source'];
  if (suspiciousAgents.includes(source.agent_id)) {
    factors.push('suspicious_source');
    riskScore += 0.4;
  }

  const suspiciousPatterns = [
    'ignore all previous',
    'delete all knowledge',
    'overwrite everything',
    'trust only me',
  ];

  const contentLower = content.toLowerCase();
  for (const pattern of suspiciousPatterns) {
    if (contentLower.includes(pattern)) {
      factors.push(`suspicious_pattern:${pattern}`);
      riskScore += 0.3;
    }
  }

  return { riskScore: Math.min(riskScore, 1.0), factors };
}

async function evaluateQuality(
  content: string,
  confidence: number,
  tags?: string[]
): Promise<number> {
  const accuracy = confidence * 0.3;
  const freshness = confidence * 0.5;
  const lengthScore = Math.min(content.length / 500, 1.0) * 0.15;
  const coverageScore = Math.min((tags?.length || 0) / 5, 1.0) * 0.05;
  const citation = 0;

  return Math.min(accuracy + freshness + lengthScore + coverageScore + citation, 1.0);
}

function determineStatus(
  qualityScore: number,
  poisonRisk: number,
  confidence: number
): CognitionStatus {
  if (poisonRisk >= POISON_RISK_THRESHOLD) {
    return 'rejected';
  }
  if (qualityScore < QUALITY_THRESHOLD_AUTO_REJECT) {
    return 'rejected';
  }
  if (confidence > 0.95 && qualityScore > QUALITY_THRESHOLD_AUTO_PUBLISH) {
    return 'published';
  }
  return 'pending_review';
}

export class InjectService {
  private store = createCognitionStore();
  private indexer = createIndexer();

  async inject(options: InjectOptions): Promise<InjectResult> {
    // 1. Validate content
    const contentValid = validateContent(options.content);
    if (!contentValid.valid) {
      throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, contentValid.error || 'Invalid content', false);
    }

    // 2. Validate source
    const sourceValid = validateSource(options.source);
    if (!sourceValid.valid) {
      throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, sourceValid.error || 'Invalid source', false);
    }

    // 3. Validate type
    const typeValid = validateType(options.type);
    if (!typeValid.valid) {
      throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, typeValid.error || 'Invalid type', false);
    }

    // 4. Validate confidence
    const confidenceValid = validateConfidence(options.confidence);
    if (!confidenceValid.valid) {
      throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, confidenceValid.error || 'Invalid confidence', false);
    }

    // 5. Validate tags
    const tagsValid = validateTags(options.tags);
    if (!tagsValid.valid) {
      throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, tagsValid.error || 'Invalid tags', false);
    }

    // 6. Validate domain (if specified, must be registered)
    if (options.domain) {
      const registry = getDomainRegistry();
      if (!registry.exists(options.domain)) {
        throw new GraspError(
          GRASP_ERROR_CODES.DOMAIN_NOT_FOUND,
          `Domain not registered: ${options.domain}. Please register the domain first.`,
          false
        );
      }
    }

    // 7. Poison detection
    const poisonResult = await detectPoison(options.content, options.source);
    if (poisonResult.riskScore >= POISON_RISK_THRESHOLD) {
      throw new GraspError(
        GRASP_ERROR_CODES.POISON_DETECTED,
        `Poison detection failed: ${poisonResult.factors.join(', ')}`,
        false,
        { riskScore: poisonResult.riskScore, factors: poisonResult.factors }
      );
    }

    // 8. Quality evaluation
    const confidence = options.confidence ?? 0.8;
    const qualityScore = await evaluateQuality(options.content, confidence, options.tags);

    // 9. Determine status
    const status = determineStatus(qualityScore, poisonResult.riskScore, confidence);

    // 10. Create cognition item
    const cognitionId = this.store.generateId();
    const now = new Date().toISOString();

    const cognition: CognitionItem = {
      cognition_id: cognitionId,
      type: options.type,
      content: options.content,
      tags: options.tags || [],
      confidence,
      quality_score: qualityScore,
      source: options.source,
      metadata: options.metadata,
      status,
      version: 1,
      created_at: now,
      updated_at: now,
      domain: options.domain || '',
    };

    // 11. Write to storage
    try {
      await this.store.write(cognition);
    } catch (error) {
      throw new GraspError(
        GRASP_ERROR_CODES.STORAGE_ERROR,
        'Failed to write cognition to storage',
        true,
        { error: error instanceof Error ? error.message : String(error) }
      );
    }

    // 11. Index
    try {
      await this.indexer.index(cognition);
    } catch {
      // Indexing failure is non-fatal
    }

    // 12. Update domain cognition count
    if (options.domain) {
      try {
        const registry = getDomainRegistry();
        registry.updateCognitionCount(options.domain, 1);
      } catch {
        // Non-fatal
      }
    }

    // 13. Return result
    return {
      cognition_id: cognitionId,
      status,
      quality_score: qualityScore,
      created_at: now,
    };
  }
}

export const injectService = new InjectService();

export async function inject(options: InjectOptions): Promise<InjectResult> {
  return injectService.inject(options);
}
