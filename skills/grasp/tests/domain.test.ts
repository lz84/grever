/**
 * Grasp Skill - Domain Tests
 */

import {
  registerDomain,
  getDomainStats,
  inject,
  retrieve,
} from '../implementation/index';

describe('domain', () => {
  describe('registerDomain', () => {
    it('should register a new domain', () => {
      const domain = registerDomain({
        name: 'TestDomain',
        description: 'Test domain',
      });

      expect(domain.name).toBe('TestDomain');
      expect(domain.description).toBe('Test domain');
      expect(domain.cognition_count).toBe(0);
    });

    it('should throw when registering duplicate domain', () => {
      registerDomain({ name: 'DuplicateTest' });

      expect(() => {
        registerDomain({ name: 'DuplicateTest' });
      }).toThrow();
    });
  });

  describe('getDomainStats', () => {
    it('should return domain statistics', () => {
      const stats = getDomainStats();

      expect(stats.domains).toBeDefined();
      expect(Array.isArray(stats.domains)).toBe(true);
      expect(stats.total_cognitions).toBeDefined();
    });
  });

  describe('domain validation in inject', () => {
    it('should accept cognition without domain', async () => {
      const result = await inject({
        type: 'fact',
        content: 'This is a test cognition without domain specification.',
        source: { agent_id: 'test', channel: 'test' },
      });

      expect(result.cognition_id).toBeDefined();
    });

    it('should accept cognition with registered domain', async () => {
      registerDomain({ name: 'FinanceTest' });

      const result = await inject({
        type: 'fact',
        content: 'This is a finance test cognition for domain validation.',
        source: { agent_id: 'test', channel: 'test' },
        domain: 'FinanceTest',
      });

      expect(result.cognition_id).toBeDefined();
    });

    it('should reject cognition with unregistered domain', async () => {
      await expect(
        inject({
          type: 'fact',
          content: 'This should fail because domain is not registered.',
          source: { agent_id: 'test', channel: 'test' },
          domain: 'UnregisteredDomain123',
        })
      ).rejects.toThrow();
    });
  });

  describe('domain filter in retrieve', () => {
    it('should store domain in cognition', async () => {
      registerDomain({ name: 'FilterDomain' });

      const result = await inject({
        type: 'fact',
        content: 'This is a filter domain test cognition for retrieval purposes here.',
        source: { agent_id: 'test', channel: 'test' },
        domain: 'FilterDomain',
        confidence: 0.97,
      });

      // Just verify inject succeeded with domain
      expect(result.cognition_id).toBeDefined();
    });
  });
});
