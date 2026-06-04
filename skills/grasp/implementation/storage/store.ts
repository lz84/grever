/**
 * Grasp Skill - Storage Layer
 * 基于 JSONL 的轻量级存储实现
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import {
  CognitionItem,
  CognitionStore,
  QueryFilters,
  Pagination,
} from '../types';

const DEFAULT_STORAGE_PATH = path.join(process.cwd(), 'memory', 'grasp');
const COGNITIONS_FILE = 'cognitions.jsonl';

export class JsonlCognitionStore implements CognitionStore {
  private storagePath: string;
  private filePath: string;

  constructor(storagePath: string = DEFAULT_STORAGE_PATH) {
    this.storagePath = storagePath;
    this.filePath = path.join(storagePath, COGNITIONS_FILE);
    this.ensureDirectory();
  }

  private ensureDirectory(): void {
    if (!fs.existsSync(this.storagePath)) {
      fs.mkdirSync(this.storagePath, { recursive: true });
    }
  }

  private readAll(): CognitionItem[] {
    if (!fs.existsSync(this.filePath)) {
      return [];
    }

    const content = fs.readFileSync(this.filePath, 'utf-8');
    const lines = content.trim().split('\n').filter(line => line.trim());

    return lines
      .map((line: string) => {
        try {
          return JSON.parse(line) as CognitionItem;
        } catch {
          return null;
        }
      })
      .filter((item): item is CognitionItem => item !== null);
  }

  private writeAll(items: CognitionItem[]): void {
    const content = items.map(item => JSON.stringify(item)).join('\n') + '\n';
    fs.writeFileSync(this.filePath, content, 'utf-8');
  }

  async write(cognition: CognitionItem): Promise<void> {
    const line = JSON.stringify(cognition) + '\n';
    fs.appendFileSync(this.filePath, line, 'utf-8');
  }

  async read(cognition_id: string): Promise<CognitionItem | null> {
    const items = this.readAll();
    return items.find(item => item.cognition_id === cognition_id) || null;
  }

  async update(cognition: CognitionItem): Promise<void> {
    const items = this.readAll();
    const index = items.findIndex(item => item.cognition_id === cognition.cognition_id);

    if (index === -1) {
      throw new Error(`Cognition not found: ${cognition.cognition_id}`);
    }

    items[index] = cognition;
    this.writeAll(items);
  }

  async delete(cognition_id: string): Promise<void> {
    const items = this.readAll();
    const filtered = items.filter(item => item.cognition_id !== cognition_id);
    this.writeAll(filtered);
  }

  async query(
    filters: QueryFilters = {},
    pagination: Pagination = { limit: 10, offset: 0 }
  ): Promise<{ items: CognitionItem[]; total: number }> {
    let filtered = this.readAll();

    if (filters.type && filters.type.length > 0) {
      filtered = filtered.filter(item => filters.type!.includes(item.type));
    }

    if (filters.tags && filters.tags.length > 0) {
      filtered = filtered.filter(item => filters.tags!.every(tag => item.tags.includes(tag)));
    }

    if (filters.status && filters.status.length > 0) {
      filtered = filtered.filter(item => filters.status!.includes(item.status));
    }

    if (filters.min_confidence !== undefined) {
      filtered = filtered.filter(item => item.confidence >= filters.min_confidence!);
    }

    if (filters.min_quality !== undefined) {
      filtered = filtered.filter(item => item.quality_score >= filters.min_quality!);
    }

    if (filters.source_agent) {
      filtered = filtered.filter(item => item.source.agent_id === filters.source_agent);
    }

    if (filters.created_after) {
      filtered = filtered.filter(item => new Date(item.created_at) >= new Date(filters.created_after!));
    }

    if (filters.created_before) {
      filtered = filtered.filter(item => new Date(item.created_at) <= new Date(filters.created_before!));
    }

    const total = filtered.length;
    const paginated = filtered.slice(pagination.offset, pagination.offset + pagination.limit);

    return { items: paginated, total };
  }

  generateId(): string {
    return `cog-${Date.now()}-${crypto.randomUUID().substring(0, 8)}`;
  }
}

export function createCognitionStore(storagePath?: string): CognitionStore {
  return new JsonlCognitionStore(storagePath);
}
