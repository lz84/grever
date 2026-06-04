/**
 * Grasp Skill - register 接口测试
 * @ts-nocheck
 */

import { register, getRegisteredConfig } from '../implementation/register';

describe('register', () => {
  beforeEach(() => {
    // Reset registered config before each test
  });

  describe('register cognition types', () => {
    it('should register a valid cognition type', async () => {
      const result = await register({
        cognitionTypes: [
          {
            id: 'test_type',
            name: 'Test Type',
            description: 'A test cognition type',
            schema: { type: 'object' },
          },
        ],
      });

      expect(result.status).toBe('success');
      expect(result.registered).toBe(1);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject cognition type without id', async () => {
      const result = await register({
        cognitionTypes: [
          {
            id: '',
            name: 'Test Type',
            description: 'A test cognition type',
            schema: { type: 'object' },
          },
        ],
      });

      expect(result.status).toBe('failed');
      expect(result.registered).toBe(0);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should reject cognition type without name', async () => {
      const result = await register({
        cognitionTypes: [
          {
            id: 'test_type',
            name: '',
            description: 'A test cognition type',
            schema: { type: 'object' },
          },
        ],
      });

      expect(result.status).toBe('failed');
    });

    it('should reject cognition type without schema', async () => {
      const result = await register({
        cognitionTypes: [
          {
            id: 'test_type',
            name: 'Test Type',
            description: 'A test cognition type',
          },
        ],
      });

      expect(result.status).toBe('failed');
    });

    it('should update existing cognition type', async () => {
      // Register first
      await register({
        cognitionTypes: [
          {
            id: 'update_test',
            name: 'Original Name',
            description: 'Original description',
            schema: { type: 'object' },
          },
        ],
      });

      // Update
      const result = await register({
        cognitionTypes: [
          {
            id: 'update_test',
            name: 'Updated Name',
            description: 'Updated description',
            schema: { type: 'string' },
          },
        ],
      });

      expect(result.status).toBe('success');
      expect(result.registered).toBe(1);

      const config = getRegisteredConfig();
      const type = config.cognitionTypes.find(t => t.id === 'update_test');
      expect(type.name).toBe('Updated Name');
    });
  });

  describe('register tag system', () => {
    it('should register a valid tag system', async () => {
      const result = await register({
        tagSystem: {
          rootTags: ['tag1', 'tag2'],
          tagRules: [
            { parent: 'tag1', children: ['child1', 'child2'], allowed: true },
          ],
        },
      });

      expect(result.status).toBe('success');
      expect(result.registered).toBe(1);
    });

    it('should reject tag system without rootTags', async () => {
      const result = await register({
        tagSystem: {
          rootTags: [],
          tagRules: [],
        },
      });

      expect(result.status).toBe('failed');
    });
  });

  describe('register review rules', () => {
    it('should register a valid review rule', async () => {
      const result = await register({
        reviewRules: [
          {
            id: 'high_confidence_rule',
            condition: 'confidence > 0.95',
            action: 'auto_approve',
            confidenceThreshold: 0.95,
          },
        ],
      });

      expect(result.status).toBe('success');
      expect(result.registered).toBe(1);
    });

    it('should reject review rule with invalid action', async () => {
      const result = await register({
        reviewRules: [
          {
            id: 'invalid_rule',
            condition: 'confidence > 0.95',
            action: 'invalid_action',
          },
        ],
      });

      expect(result.status).toBe('failed');
    });
  });

  describe('register quality rules', () => {
    it('should register a valid quality rule', async () => {
      const result = await register({
        qualityRules: [
          {
            id: 'accuracy_rule',
            dimension: 'accuracy',
            weight: 0.4,
            calculation: 'confidence * 0.4',
          },
        ],
      });

      expect(result.status).toBe('success');
      expect(result.registered).toBe(1);
    });

    it('should reject quality rule with invalid weight', async () => {
      const result = await register({
        qualityRules: [
          {
            id: 'invalid_weight_rule',
            dimension: 'accuracy',
            weight: 1.5,
            calculation: 'confidence * 0.4',
          },
        ],
      });

      expect(result.status).toBe('failed');
    });
  });

  describe('mixed registration', () => {
    it('should register multiple items with partial failure', async () => {
      const result = await register({
        cognitionTypes: [
          {
            id: 'valid_type',
            name: 'Valid Type',
            description: 'Valid description',
            schema: { type: 'object' },
          },
          {
            id: '',
            name: 'Invalid Type',
            description: 'Missing id',
            schema: { type: 'object' },
          },
        ],
        tagSystem: {
          rootTags: ['tag1'],
          tagRules: [],
        },
      });

      expect(result.status).toBe('partial');
      expect(result.registered).toBeGreaterThan(0);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });
});
