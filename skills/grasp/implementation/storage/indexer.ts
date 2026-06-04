/**
 * Grasp Skill - Indexer
 * 简单的文本向量化和检索实现
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  CognitionItem,
  Indexer,
} from '../types';

const DEFAULT_INDEX_PATH = path.join(process.cwd(), 'memory', 'grasp', 'index');
const VECTOR_FILE = 'vector.index.jsonl';
const KEYWORD_FILE = 'keyword.index.jsonl';

interface VectorEntry {
  cognition_id: string;
  vector: number[];
  content: string;
}

interface KeywordEntry {
  cognition_id: string;
  keywords: string[];
}

export class GraspIndexer implements Indexer {
  private indexPath: string;
  private vectorPath: string;
  private keywordPath: string;
  private vectors: Map<string, VectorEntry> = new Map();
  private keywords: Map<string, KeywordEntry> = new Map();

  constructor(indexPath: string = DEFAULT_INDEX_PATH) {
    this.indexPath = indexPath;
    this.vectorPath = path.join(indexPath, VECTOR_FILE);
    this.keywordPath = path.join(indexPath, KEYWORD_FILE);
    this.ensureDirectory();
    this.loadIndexes();
  }

  private ensureDirectory(): void {
    if (!fs.existsSync(this.indexPath)) {
      fs.mkdirSync(this.indexPath, { recursive: true });
    }
  }

  private loadIndexes(): void {
    // Load vector index
    if (fs.existsSync(this.vectorPath)) {
      const content = fs.readFileSync(this.vectorPath, 'utf-8');
      const lines = content.trim().split('\n').filter(line => line.trim());
      for (const line of lines) {
        try {
          const entry: VectorEntry = JSON.parse(line);
          this.vectors.set(entry.cognition_id, entry);
        } catch {
          // Skip invalid entries
        }
      }
    }

    // Load keyword index
    if (fs.existsSync(this.keywordPath)) {
      const content = fs.readFileSync(this.keywordPath, 'utf-8');
      const lines = content.trim().split('\n').filter(line => line.trim());
      for (const line of lines) {
        try {
          const entry: KeywordEntry = JSON.parse(line);
          this.keywords.set(entry.cognition_id, entry);
        } catch {
          // Skip invalid entries
        }
      }
    }
  }

  private saveVectors(): void {
    const content = Array.from(this.vectors.values())
      .map(v => JSON.stringify(v))
      .join('\n') + '\n';
    fs.writeFileSync(this.vectorPath, content, 'utf-8');
  }

  private saveKeywords(): void {
    const content = Array.from(this.keywords.values())
      .map(k => JSON.stringify(k))
      .join('\n') + '\n';
    fs.writeFileSync(this.keywordPath, content, 'utf-8');
  }

  private simpleVectorize(text: string): number[] {
    // Simple TF-based vectorization
    const words = text.toLowerCase().split(/\s+/);
    const wordCount: Map<string, number> = new Map();

    for (const word of words) {
      if (word.length > 2) {
        wordCount.set(word, (wordCount.get(word) || 0) + 1);
      }
    }

    // Create a simple hash-based vector (for demo purposes)
    const dimension = 128;
    const vector = new Array(dimension).fill(0);

    for (const [word, count] of wordCount) {
      const hash = this.hashString(word);
      for (let i = 0; i < dimension; i++) {
        vector[i] += count * Math.sin(hash + i);
      }
    }

    // Normalize
    const magnitude = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
    if (magnitude > 0) {
      for (let i = 0; i < dimension; i++) {
        vector[i] /= magnitude;
      }
    }

    return vector;
  }

  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    }
    return hash;
  }

  private extractKeywords(text: string): string[] {
    const stopWords = new Set([
      '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也',
      '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那',
      'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
      'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
    ]);

    const words = text.toLowerCase().split(/\s+/);
    return words.filter(w => w.length > 2 && !stopWords.has(w));
  }

  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) return 0;

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    if (normA === 0 || normB === 0) return 0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  async index(cognition: CognitionItem): Promise<void> {
    const vector = this.simpleVectorize(cognition.content);
    this.vectors.set(cognition.cognition_id, {
      cognition_id: cognition.cognition_id,
      vector,
      content: cognition.content,
    });

    const kw = this.extractKeywords(cognition.content);
    this.keywords.set(cognition.cognition_id, {
      cognition_id: cognition.cognition_id,
      keywords: kw,
    });

    this.saveVectors();
    this.saveKeywords();
  }

  async unindex(cognition_id: string): Promise<void> {
    this.vectors.delete(cognition_id);
    this.keywords.delete(cognition_id);
    this.saveVectors();
    this.saveKeywords();
  }

  async vectorSearch(
    query: string,
    options?: { topK?: number; minScore?: number }
  ): Promise<string[]> {
    const topK = options?.topK ?? 10;
    const minScore = options?.minScore ?? 0.1;

    const queryVector = this.simpleVectorize(query);
    const scores: Array<{ id: string; score: number }> = [];

    for (const [id, entry] of this.vectors) {
      const score = this.cosineSimilarity(queryVector, entry.vector);
      if (score >= minScore) {
        scores.push({ id, score });
      }
    }

    scores.sort((a, b) => b.score - a.score);
    return scores.slice(0, topK).map(s => s.id);
  }

  async keywordSearch(
    query: string,
    options?: { topK?: number; fields?: string[] }
  ): Promise<string[]> {
    const topK = options?.topK ?? 10;
    const queryKeywords = this.extractKeywords(query);

    if (queryKeywords.length === 0) {
      return [];
    }

    const scores: Array<{ id: string; score: number }> = [];

    for (const [id, entry] of this.keywords) {
      let matchCount = 0;
      for (const qk of queryKeywords) {
        if (entry.keywords.some(k => k.includes(qk) || qk.includes(k))) {
          matchCount++;
        }
      }

      if (matchCount > 0) {
        const score = matchCount / queryKeywords.length;
        scores.push({ id, score });
      }
    }

    scores.sort((a, b) => b.score - a.score);
    return scores.slice(0, topK).map(s => s.id);
  }

  async refresh(): Promise<void> {
    this.vectors.clear();
    this.keywords.clear();
    this.loadIndexes();
  }
}

export function createIndexer(indexPath?: string): Indexer {
  return new GraspIndexer(indexPath);
}
