/**
 * Grasp Skill - update 接口测试
 * @ts-nocheck
 */

import { inject } from '../implementation/inject';
import { update, revert, softDelete } from '../implementation/update';
import { getById } from '../implementation/retrieve';

describe('update', () => {
  let testCognitionId;

  beforeEach(async () => {
    // Inject a test cognition before each test
    const result = await inject({
      type: 'fact',
      content: 'This is the original content for update testing.',
      source: {
        agent_id: 'test-agent',
        channel: 'test',
      },
      tags: ['test', 'original'],
      confidence: 0.8,
    });
    testCognitionId = result.cognition_id;
  });

  describe('validation', () => {
    it('should accept empty update (no-op)', async () => {
      // Empty update {} is valid - it just returns existing data without changes
      const result = await update(testCognitionId, {});
      expect(result.cognition_id).toBe(testCognitionId);
    });

    it('should reject invalid confidence', async () => {
      await expect(
        update(testCognitionId, { confidence: 1.5 })
      ).rejects.toThrow();

      await expect(
        update(testCognitionId, { confidence: -0.1 })
      ).rejects.toThrow();
    });

    it('should reject too many tags', async () => {
      await expect(
        update(testCognitionId, {
          tags: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'],
        })
      ).rejects.toThrow();
    });

    it('should reject empty string tag', async () => {
      await expect(
        update(testCognitionId, {
          tags: ['valid', ''],
        })
      ).rejects.toThrow();
    });

    it('should reject short content', async () => {
      await expect(
        update(testCognitionId, {
          content: 'short',
        })
      ).rejects.toThrow();
    });
  });

  describe('not found', () => {
    it('should throw NOT_FOUND for non-existent cognition', async () => {
      await expect(
        update('non-existent-id-12345', { content: 'New content here.' })
      ).rejects.toThrow('NOT_FOUND');
    });
  });

  describe('content update', () => {
    it('should update content', async () => {
      const newContent = 'This is the updated content for testing purposes.';

      const result = await update(testCognitionId, { content: newContent });

      expect(result.cognition_id).toBe(testCognitionId);
      expect(result.updated_at).toBeDefined();
      expect(result.version).toBeGreaterThan(1);

      const updated = await getById(testCognitionId);
      expect(updated.content).toBe(newContent);
    });
  });

  describe('tags update', () => {
    it('should update tags', async () => {
      const result = await update(testCognitionId, {
        tags: ['updated', 'tags'],
      });

      expect(result.cognition_id).toBe(testCognitionId);

      const updated = await getById(testCognitionId);
      expect(updated.tags).toEqual(['updated', 'tags']);
    });
  });

  describe('confidence update', () => {
    it('should update confidence', async () => {
      const result = await update(testCognitionId, { confidence: 0.95 });

      expect(result.cognition_id).toBe(testCognitionId);

      const updated = await getById(testCognitionId);
      expect(updated.confidence).toBe(0.95);
    });
  });

  describe('metadata update', () => {
    it('should update metadata', async () => {
      const result = await update(testCognitionId, {
        metadata: { key: 'value', number: 42 },
      });

      expect(result.cognition_id).toBe(testCognitionId);

      const updated = await getById(testCognitionId);
      expect(updated.metadata).toEqual({ key: 'value', number: 42 });
    });
  });

  describe('version increment', () => {
    it('should increment version on update', async () => {
      const before = await getById(testCognitionId);
      const originalVersion = before.version;

      await update(testCognitionId, { content: 'Updated content for version test.' });

      const after = await getById(testCognitionId);
      expect(after.version).toBe(originalVersion + 1);
    });
  });

  describe('quality re-evaluation', () => {
    it('should re-evaluate quality when content changes', async () => {
      const before = await getById(testCognitionId);
      const originalQuality = before.quality_score;

      // Update with longer content
      await update(testCognitionId, {
        content: 'This is a much longer updated content that should have a different quality score because it contains more text and information.',
      });

      const after = await getById(testCognitionId);
      expect(after.quality_score).not.toBe(originalQuality);
    });
  });

  describe('no changes', () => {
    it('should return existing data when no changes made', async () => {
      const before = await getById(testCognitionId);

      await update(testCognitionId, {});

      // No version increment when no changes
      const after = await getById(testCognitionId);
      expect(after.version).toBe(before.version);
    });
  });
});

describe('revert', () => {
  let testCognitionId;

  beforeEach(async () => {
    const result = await inject({
      type: 'fact',
      content: 'Content for revert testing.',
      source: {
        agent_id: 'test-agent',
        channel: 'test',
      },
      tags: ['test'],
      confidence: 0.8,
    });
    testCognitionId = result.cognition_id;
  });

  it('should revert cognition to pending_review', async () => {
    const result = await revert(testCognitionId);

    expect(result.cognition_id).toBe(testCognitionId);
    expect(result.status).toBe('pending_review');
    expect(result.version).toBeGreaterThan(1);
  });

  it('should throw NOT_FOUND for non-existent cognition', async () => {
    await expect(revert('non-existent-id')).rejects.toThrow('NOT_FOUND');
  });
});

describe('softDelete', () => {
  let testCognitionId;

  beforeEach(async () => {
    const result = await inject({
      type: 'fact',
      content: 'Content for soft delete testing.',
      source: {
        agent_id: 'test-agent',
        channel: 'test',
      },
      tags: ['test'],
      confidence: 0.8,
    });
    testCognitionId = result.cognition_id;
  });

  it('should soft delete cognition (mark as rejected)', async () => {
    await softDelete(testCognitionId);

    const deleted = await getById(testCognitionId);
    expect(deleted.status).toBe('rejected');
  });

  it('should throw NOT_FOUND for non-existent cognition', async () => {
    await expect(softDelete('non-existent-id')).rejects.toThrow('NOT_FOUND');
  });
});
