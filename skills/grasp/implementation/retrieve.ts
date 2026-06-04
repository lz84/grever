/**
 * Grasp Skill - retrieve 接口实现
 * 从知识库检索匹配的认知条目
 */

import {
  RetrieveQuery,
  RetrieveResult,
  CognitionItem,
  CognitionStatus,
  GraspError,
  GRASP_ERROR_CODES,
} from './types';
import { createCognitionStore } from './storage/store';
import { createIndexer } from './storage/indexer';

function validateQuery(query: RetrieveQuery): void {
  if (!query || typeof query !== 'object') {
    throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, 'Query must be an object', false);
  }

  if (!query.query || typeof query.query !== 'string') {
    throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, 'Query text is required', false);
  }

  if (query.query.trim().length === 0) {
    throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, 'Query text cannot be empty', false);
  }

  if (query.limit !== undefined && (query.limit < 1 || query.limit > 100)) {
    throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, 'Limit must be between 1 and 100', false);
  }

  if (query.offset !== undefined && query.offset < 0) {
    throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, 'Offset must be non-negative', false);
  }

  if (query.type) {
    const validTypes = ['fact', 'pattern', 'lesson', 'meta'];
    for (const type of query.type) {
      if (!validTypes.includes(type)) {
        throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, `Invalid type: ${type}`, false);
      }
    }
  }

  if (query.status) {
    const validStatuses: CognitionStatus[] = ['published', 'pending_review', 'rejected'];
    for (const status of query.status) {
      if (!validStatuses.includes(status)) {
        throw new GraspError(GRASP_ERROR_CODES.INVALID_CONTENT, `Invalid status: ${status}`, false);
      }
    }
  }
}

function mergeResults(vectorIds: string[], keywordIds: string[]): string[] {
  const scored = new Map<string, number>();

  vectorIds.forEach((id, index) => {
    const score = 1.0 - (index / vectorIds.length) * 0.5;
    scored.set(id, (scored.get(id) || 0) + score);
  });

  keywordIds.forEach((id, index) => {
    const score = 0.8 - (index / keywordIds.length) * 0.3;
    scored.set(id, (scored.get(id) || 0) + score);
  });

  return Array.from(scored.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);
}

function applyFilters(items: CognitionItem[], query: RetrieveQuery): CognitionItem[] {
  return items.filter(item => {
    // Default: only published cognitions
    if (!query.status || query.status.length === 0) {
      if (item.status !== 'published') {
        return false;
      }
    } else {
      if (!query.status.includes(item.status)) {
        return false;
      }
    }

    if (query.type && query.type.length > 0) {
      if (!query.type.includes(item.type)) {
        return false;
      }
    }

    if (query.tags && query.tags.length > 0) {
      if (!query.tags.every(tag => item.tags.includes(tag))) {
        return false;
      }
    }

    if (query.min_confidence !== undefined && item.confidence < query.min_confidence) {
      return false;
    }

    if (query.min_quality !== undefined && item.quality_score < query.min_quality) {
      return false;
    }

    if (query.source_agent && item.source.agent_id !== query.source_agent) {
      return false;
    }

    // Domain filter
    if (query.domain && item.domain !== query.domain) {
      return false;
    }

    return true;
  });
}

function sortResults(items: CognitionItem[], rankedIds: string[]): CognitionItem[] {
  const rankMap = new Map<string, number>();
  rankedIds.forEach((id, index) => {
    rankMap.set(id, rankedIds.length - index);
  });

  return items.sort((a, b) => {
    const rankA = rankMap.get(a.cognition_id) || 0;
    const rankB = rankMap.get(b.cognition_id) || 0;

    if (rankA !== rankB) {
      return rankB - rankA;
    }

    if (a.quality_score !== b.quality_score) {
      return b.quality_score - a.quality_score;
    }

    return b.confidence - a.confidence;
  });
}

export class RetrieveService {
  private store = createCognitionStore();
  private indexer = createIndexer();

  async retrieve(query: RetrieveQuery): Promise<RetrieveResult> {
    const startTime = Date.now();

    try {
      // 1. Validate query
      validateQuery(query);

      // 2. Vector search
      const vectorIds = await this.indexer.vectorSearch(query.query, {
        topK: 20,
        minScore: 0.1,
      });

      // 3. Keyword search
      const keywordIds = await this.indexer.keywordSearch(query.query, {
        topK: 20,
      });

      // 4. Merge results
      const mergedIds = mergeResults(vectorIds, keywordIds);

      // 5. Fetch cognitions
      const cognitions: CognitionItem[] = [];
      for (const id of mergedIds) {
        const item = await this.store.read(id);
        if (item) {
          cognitions.push(item);
        }
      }

      // 6. Apply filters
      const filtered = applyFilters(cognitions, query);

      // 7. Sort
      const sorted = sortResults(filtered, mergedIds);

      // 8. Paginate
      const limit = query.limit ?? 10;
      const offset = query.offset ?? 0;
      const paginated = sorted.slice(offset, offset + limit);
      const total = filtered.length;

      return {
        items: paginated,
        total,
        has_more: total > offset + limit,
        query_time_ms: Date.now() - startTime,
      };
    } catch (error) {
      if (error instanceof GraspError) {
        throw error;
      }
      throw new GraspError(
        GRASP_ERROR_CODES.STORAGE_ERROR,
        'Failed to retrieve cognitions',
        true,
        { error: error instanceof Error ? error.message : String(error) }
      );
    }
  }
}

export const retrieveService = new RetrieveService();

export async function retrieve(query: RetrieveQuery): Promise<RetrieveResult> {
  return retrieveService.retrieve(query);
}

export async function batchRetrieve(queries: RetrieveQuery[]): Promise<RetrieveResult[]> {
  return Promise.all(queries.map(q => retrieveService.retrieve(q)));
}

export async function getById(cognitionId: string): Promise<CognitionItem | null> {
  const store = createCognitionStore();
  return store.read(cognitionId);
}

export async function getByType(type: CognitionItem['type']): Promise<CognitionItem[]> {
  const store = createCognitionStore();
  const result = await store.query({ type: [type] }, { limit: 1000, offset: 0 });
  return result.items;
}

export async function getByTags(tags: string[]): Promise<CognitionItem[]> {
  const store = createCognitionStore();
  const result = await store.query({ tags }, { limit: 1000, offset: 0 });
  return result.items;
}
