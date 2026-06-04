/**
 * Grasp Skill - retrieve 接口测试
 * @ts-nocheck
 */

import { retrieve, getById, getByType, getByTags } from '../implementation/retrieve';
import { inject } from '../implementation/inject';

describe('retrieve', () => {
  const testContent = 'This is a test cognition content for retrieval testing purposes.';

  beforeAll(async () => {
    // Inject some test cognitions
    await inject({
      type: 'fact',
      content: testContent,
      source: {
        agent_id: 'test-agent',
        channel: 'test',
      },
      tags: ['test', 'fact'],
      confidence: 0.9,
    });

    await inject({
      type: 'pattern',
      content: 'A common pattern for task decomposition involves identifying dependencies first.',
      source: {
        agent_id: 'test-agent',
        channel: 'test',
      },
      tags: ['pattern', 'task-decomposition'],
      confidence: 0.85,
    });

    await inject({
      type: 'lesson',
      content: 'When deploying vLLM, GPU memory may be insufficient if max_model_len is not properly configured.',
      source: {
        agent_id: 'test-agent-2',
        channel: 'test',
      },
      tags: ['lesson', 'deployment', 'vllm'],
      confidence: 0.95,
    });
  });

  describe('query validation', () => {
    it('should reject empty query', async () => {
      await expect(
        retrieve({
          query: '',
        })
      ).rejects.toThrow();
    });

    it('should reject whitespace-only query', async () => {
      await expect(
        retrieve({
          query: '     ',
        })
      ).rejects.toThrow();
    });

    it('should reject missing query', async () => {
      await expect(retrieve({})).rejects.toThrow();
    });

    it('should reject invalid limit', async () => {
      await expect(
        retrieve({
          query: 'test',
          limit: 0,
        })
      ).rejects.toThrow();

      await expect(
        retrieve({
          query: 'test',
          limit: 101,
        })
      ).rejects.toThrow();
    });

    it('should reject negative offset', async () => {
      await expect(
        retrieve({
          query: 'test',
          offset: -1,
        })
      ).rejects.toThrow();
    });

    it('should reject invalid type filter', async () => {
      await expect(
        retrieve({
          query: 'test',
          type: ['invalid'],
        })
      ).rejects.toThrow();
    });

    it('should reject invalid status filter', async () => {
      await expect(
        retrieve({
          query: 'test',
          status: ['invalid'],
        })
      ).rejects.toThrow();
    });
  });

  describe('basic retrieval', () => {
    it('should retrieve cognitions by query', async () => {
      const result = await retrieve({
        query: 'test',
      });

      expect(result.items).toBeDefined();
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.total).toBeGreaterThanOrEqual(0);
      expect(result.has_more).toBeDefined();
      expect(result.query_time_ms).toBeGreaterThanOrEqual(0);
    });

    it('should return empty results for non-matching query', async () => {
      const result = await retrieve({
        query: 'xyznonexistent123',
      });

      expect(result.items).toBeDefined();
      expect(result.items.length).toBe(0);
      expect(result.total).toBe(0);
      expect(result.has_more).toBe(false);
    });
  });

  describe('type filtering', () => {
    it('should filter by single type', async () => {
      const result = await retrieve({
        query: 'test',
        type: ['fact'],
      });

      for (const item of result.items) {
        expect(item.type).toBe('fact');
      }
    });

    it('should filter by multiple types', async () => {
      const result = await retrieve({
        query: 'test',
        type: ['fact', 'pattern'],
      });

      for (const item of result.items) {
        expect(['fact', 'pattern']).toContain(item.type);
      }
    });
  });

  describe('tags filtering', () => {
    it('should filter by single tag', async () => {
      const result = await retrieve({
        query: 'test',
        tags: ['test'],
      });

      for (const item of result.items) {
        expect(item.tags).toContain('test');
      }
    });

    it('should filter by multiple tags (AND)', async () => {
      const result = await retrieve({
        query: 'deployment',
        tags: ['lesson', 'deployment'],
      });

      for (const item of result.items) {
        expect(item.tags).toContain('lesson');
        expect(item.tags).toContain('deployment');
      }
    });
  });

  describe('confidence filtering', () => {
    it('should filter by min_confidence', async () => {
      const result = await retrieve({
        query: 'test',
        min_confidence: 0.9,
      });

      for (const item of result.items) {
        expect(item.confidence).toBeGreaterThanOrEqual(0.9);
      }
    });
  });

  describe('source_agent filtering', () => {
    it('should filter by source_agent', async () => {
      const result = await retrieve({
        query: 'vllm',
        source_agent: 'test-agent-2',
      });

      for (const item of result.items) {
        expect(item.source.agent_id).toBe('test-agent-2');
      }
    });
  });

  describe('pagination', () => {
    it('should respect limit parameter', async () => {
      const result = await retrieve({
        query: 'test',
        limit: 1,
      });

      expect(result.items.length).toBeLessThanOrEqual(1);
    });

    it('should respect offset parameter', async () => {
      const result1 = await retrieve({
        query: 'test',
        limit: 10,
        offset: 0,
      });

      const result2 = await retrieve({
        query: 'test',
        limit: 10,
        offset: 1,
      });

      expect(result2.total).toBe(result1.total);
    });

    it('should set has_more correctly', async () => {
      const result = await retrieve({
        query: 'test',
        limit: 1,
      });

      expect(result.has_more).toBe(result.total > 1);
    });
  });

  describe('getById', () => {
    it('should retrieve by cognition_id', async () => {
      // First inject a cognition
      const injectResult = await inject({
        type: 'fact',
        content: 'This is a specific test content for getById testing.',
        source: {
          agent_id: 'test-agent',
          channel: 'test',
        },
        tags: ['test'],
        confidence: 0.8,
      });

      const item = await getById(injectResult.cognition_id);

      expect(item).not.toBeNull();
      expect(item.cognition_id).toBe(injectResult.cognition_id);
    });

    it('should return null for non-existent id', async () => {
      const item = await getById('non-existent-id-12345');

      expect(item).toBeNull();
    });
  });

  describe('getByType', () => {
    it('should retrieve all cognitions of a type', async () => {
      const items = await getByType('fact');

      expect(Array.isArray(items)).toBe(true);
      for (const item of items) {
        expect(item.type).toBe('fact');
      }
    });
  });

  describe('getByTags', () => {
    it('should retrieve cognitions by tags', async () => {
      const items = await getByTags(['test']);

      expect(Array.isArray(items)).toBe(true);
      for (const item of items) {
        expect(item.tags).toContain('test');
      }
    });
  });

  describe('domain filter', () => {
    it('should filter by domain', async () => {
      // Inject with domain
      const result = await inject({
        type: 'fact',
        content: 'This is a finance domain cognition for testing purposes here.',
        source: { agent_id: 'test-agent', channel: 'test' },
        domain: '金融',
        confidence: 0.97,
      });

      // Get by ID and verify domain is stored
      const cognition = await getById(result.cognition_id);
      expect(cognition).not.toBeNull();
      expect(cognition?.domain).toBe('金融');
    });
  });
});
