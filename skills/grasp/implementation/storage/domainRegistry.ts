/**
 * Grasp Skill - Domain Registry
 * 领域注册与管理
 */

import * as fs from 'fs';
import * as path from 'path';
import { Domain, DomainStats, RegisterDomainOptions } from '../types';

const DEFAULT_STORAGE_PATH = path.join(process.cwd(), 'memory', 'grasp');
const DOMAINS_FILE = 'domains.jsonl';

export class DomainRegistry {
  private storagePath: string;
  private filePath: string;
  private domains: Map<string, Domain>;

  constructor(storagePath: string = DEFAULT_STORAGE_PATH) {
    this.storagePath = storagePath;
    this.filePath = path.join(storagePath, DOMAINS_FILE);
    this.domains = new Map();
    this.ensureDirectory();
    this.load();
  }

  private ensureDirectory(): void {
    if (!fs.existsSync(this.storagePath)) {
      fs.mkdirSync(this.storagePath, { recursive: true });
    }
  }

  private load(): void {
    if (!fs.existsSync(this.filePath)) {
      return;
    }

    const content = fs.readFileSync(this.filePath, 'utf-8');
    const lines = content.trim().split('\n').filter(line => line.trim());

    for (const line of lines) {
      try {
        const domain = JSON.parse(line) as Domain;
        this.domains.set(domain.name, domain);
      } catch {
        // Skip invalid lines
      }
    }
  }

  private save(): void {
    const lines = Array.from(this.domains.values())
      .map(d => JSON.stringify(d))
      .join('\n') + '\n';
    fs.writeFileSync(this.filePath, lines, 'utf-8');
  }

  /**
   * 注册新领域
   */
  register(options: RegisterDomainOptions): Domain {
    if (this.domains.has(options.name)) {
      throw new Error(`Domain already exists: ${options.name}`);
    }

    const domain: Domain = {
      name: options.name,
      description: options.description,
      created_at: new Date().toISOString(),
      cognition_count: 0,
    };

    this.domains.set(domain.name, domain);
    this.save();
    return domain;
  }

  /**
   * 获取领域信息
   */
  get(name: string): Domain | undefined {
    return this.domains.get(name);
  }

  /**
   * 获取所有领域
   */
  list(): Domain[] {
    return Array.from(this.domains.values());
  }

  /**
   * 检查领域是否存在
   */
  exists(name: string): boolean {
    return this.domains.has(name);
  }

  /**
   * 删除领域
   */
  delete(name: string): boolean {
    const deleted = this.domains.delete(name);
    if (deleted) {
      this.save();
    }
    return deleted;
  }

  /**
   * 更新认知计数
   */
  updateCognitionCount(name: string, delta: number): void {
    const domain = this.domains.get(name);
    if (domain) {
      domain.cognition_count += delta;
      if (domain.cognition_count < 0) {
        domain.cognition_count = 0;
      }
      this.save();
    }
  }

  /**
   * 获取领域统计
   */
  getStats(): DomainStats {
    return {
      domains: this.list(),
      total_cognitions: Array.from(this.domains.values()).reduce(
        (sum, d) => sum + d.cognition_count, 
        0
      ),
    };
  }
}

let registryInstance: DomainRegistry | null = null;

export function getDomainRegistry(): DomainRegistry {
  if (!registryInstance) {
    registryInstance = new DomainRegistry();
  }
  return registryInstance;
}
