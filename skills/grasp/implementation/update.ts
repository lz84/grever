/**
 * Grasp Skill - update 接口实现
 * 更新已存在的认知条目
 */

import {
  CognitionUpdate,
  UpdateResult,
  CognitionItem,
  GraspError,
  GRASP_ERROR_CODES,
} from './types';
import { createCognitionStore } from './storage/store';
import { createIndexer } from './storage/indexer';
import { getRegisteredConfig } from './register';

function validateUpdate(update: CognitionUpdate): { valid: boolean; error?: string } {
  if (!update || typeof update !== 'object') {
    return { valid: false, error: 'Update must be an object' };
  }

  if (update.content !== undefined) {
    if (typeof update.content !== 'string') {
      return { valid: false, error: 'Content must be a string' };
    }
    const trimmed = update.content.trim();
    if (trimmed.length > 0 && trimmed.length < 10) {
      return { valid: false, error: 'Content too short (minimum 10 characters)' };
    }
    if (trimmed.length > 10000) {
      return { valid: false, error: 'Content too long (maximum 10000 characters)' };
    }
  }

  if (update.tags !== undefined) {
    if (!Array.isArray(update.tags)) {
      return { valid: false, error: 'Tags must be an array' };
    }
    if (update.tags.length > 10) {
      return { valid: false, error: 'Tags cannot exceed 10 items' };
    }
    for (const tag of update.tags) {
      if (typeof tag !== 'string' || tag.trim().length === 0) {
        return { valid: false, error: 'Each tag must be a non-empty string' };
      }
    }
  }

  if (update.confidence !== undefined) {
    if (typeof update.confidence !== 'number' || update.confidence < 0 || update.confidence > 1) {
      return { valid: false, error: 'Confidence must be a number between 0 and 1' };
    }
  }

  return { valid: true };
}

async function reevaluateQuality(
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

function determineNewStatus(
  _oldStatus: string,
  qualityScore: number,
  confidence: number
): string {
  if (qualityScore < 0.3) {
    return 'rejected';
  }
  if (confidence > 0.95 && qualityScore > 0.9) {
    return 'published';
  }
  return 'pending_review';
}

export class UpdateService {
  private store = createCognitionStore();
  private indexer = createIndexer();

  async update(cognitionId: string, update: CognitionUpdate, agentId?: string): Promise<UpdateResult> {
    // 1. Validate update
    const valid = validateUpdate(update);
    if (!valid.valid) {
      throw new GraspError(GRASP_ERROR_CODES.INVALID_UPDATE, valid.error || 'Invalid update', false);
    }

    // 2. Read existing cognition
    const existing = await this.store.read(cognitionId);
    if (!existing) {
      throw new GraspError(GRASP_ERROR_CODES.NOT_FOUND, `Cognition not found: ${cognitionId}`, false);
    }

    // 3. Permission check
    const config = getRegisteredConfig();
    if (config.reviewRules.length === 0) {
      // Default: only source agent can update
      if (agentId && existing.source.agent_id !== agentId) {
        throw new GraspError(GRASP_ERROR_CODES.FORBIDDEN, 'No permission to update this cognition', false);
      }
    }

    // 4. Check if there are actual changes
    const hasContentChange = update.content !== undefined && update.content !== existing.content;
    const hasConfidenceChange = update.confidence !== undefined && update.confidence !== existing.confidence;
    const hasTagsChange = update.tags !== undefined && JSON.stringify(update.tags) !== JSON.stringify(existing.tags);

    if (!hasContentChange && !hasConfidenceChange && !hasTagsChange && !update.metadata) {
      // No actual changes, return existing
      return {
        cognition_id: cognitionId,
        status: existing.status,
        quality_score: existing.quality_score,
        updated_at: existing.updated_at,
        version: existing.version,
      };
    }

    // 5. Re-evaluate quality if content changed
    let qualityScore = existing.quality_score;
    let confidence = update.confidence ?? existing.confidence;
    let newContent = update.content ?? existing.content;
    let newTags = update.tags ?? existing.tags;

    if (hasContentChange || hasConfidenceChange || hasTagsChange) {
      qualityScore = await reevaluateQuality(newContent, confidence, newTags);
    }

    // 6. Determine new status
    let newStatus = existing.status;
    if (existing.status === 'published') {
      // Re-evaluate status for published items
      newStatus = determineNewStatus(existing.status, qualityScore, confidence) as any;
    } else if (existing.status === 'rejected') {
      // Rejected items go to pending_review on update
      newStatus = 'pending_review';
    }

    // 7. Update cognition
    const now = new Date().toISOString();
    const updated: CognitionItem = {
      ...existing,
      content: newContent,
      tags: newTags,
      confidence,
      quality_score: qualityScore,
      metadata: update.metadata ?? existing.metadata,
      status: newStatus as any,
      version: existing.version + 1,
      updated_at: now,
    };

    // 8. Write to storage
    try {
      await this.store.update(updated);
    } catch (error) {
      throw new GraspError(
        GRASP_ERROR_CODES.STORAGE_ERROR,
        'Failed to update cognition',
        true,
        { error: error instanceof Error ? error.message : String(error) }
      );
    }

    // 9. Re-index if content changed
    if (hasContentChange) {
      try {
        await this.indexer.unindex(cognitionId);
        await this.indexer.index(updated);
      } catch {
        // Indexing failure is non-fatal
      }
    }

    // 10. Return result
    return {
      cognition_id: cognitionId,
      status: newStatus as any,
      quality_score: qualityScore,
      updated_at: now,
      version: updated.version,
    };
  }

  async revert(cognitionId: string, _agentId?: string): Promise<UpdateResult> {
    // Simple revert: just mark for review
    const existing = await this.store.read(cognitionId);
    if (!existing) {
      throw new GraspError(GRASP_ERROR_CODES.NOT_FOUND, `Cognition not found: ${cognitionId}`, false);
    }

    const now = new Date().toISOString();
    const reverted: CognitionItem = {
      ...existing,
      status: 'pending_review',
      updated_at: now,
      version: existing.version + 1,
    };

    await this.store.update(reverted);

    return {
      cognition_id: cognitionId,
      status: 'pending_review',
      quality_score: existing.quality_score,
      updated_at: now,
      version: reverted.version,
    };
  }

  async softDelete(cognitionId: string, agentId?: string): Promise<void> {
    const existing = await this.store.read(cognitionId);
    if (!existing) {
      throw new GraspError(GRASP_ERROR_CODES.NOT_FOUND, `Cognition not found: ${cognitionId}`, false);
    }

    // Permission check
    if (agentId && existing.source.agent_id !== agentId) {
      throw new GraspError(GRASP_ERROR_CODES.FORBIDDEN, 'No permission to delete this cognition', false);
    }

    // Soft delete: mark as rejected
    const now = new Date().toISOString();
    const deleted: CognitionItem = {
      ...existing,
      status: 'rejected',
      updated_at: now,
      version: existing.version + 1,
    };

    await this.store.update(deleted);
    await this.indexer.unindex(cognitionId);
  }
}

export const updateService = new UpdateService();

export async function update(
  cognitionId: string,
  update: CognitionUpdate,
  agentId?: string
): Promise<UpdateResult> {
  return updateService.update(cognitionId, update, agentId);
}

export async function revert(cognitionId: string, agentId?: string): Promise<UpdateResult> {
  return updateService.revert(cognitionId, agentId);
}

export async function softDelete(cognitionId: string, agentId?: string): Promise<void> {
  return updateService.softDelete(cognitionId, agentId);
}
