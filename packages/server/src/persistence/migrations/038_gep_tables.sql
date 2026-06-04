-- Migration 038: GEP Protocol Tables
-- 创建 Gene/Capsule/EvolutionEvent 存储表
-- Date: 2026-06-01

-- genes 表
CREATE TABLE IF NOT EXISTS genes (
    id TEXT PRIMARY KEY,
    schema_version TEXT DEFAULT '1.0',
    category TEXT,
    signals_match TEXT,
    preconditions TEXT,
    strategy TEXT,
    constraints TEXT,
    validation TEXT,
    epigenetic_marks TEXT,
    asset_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- capsules 表
CREATE TABLE IF NOT EXISTS capsules (
    id TEXT PRIMARY KEY,
    schema_version TEXT DEFAULT '1.0',
    trigger TEXT,
    gene_id TEXT REFERENCES genes(id),
    summary TEXT,
    confidence REAL,
    blast_radius TEXT,
    outcome TEXT,
    success_streak INT DEFAULT 0,
    content TEXT,
    diff TEXT,
    strategy TEXT,
    a2a TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- evolution_events 表
CREATE TABLE IF NOT EXISTS evolution_events (
    id TEXT PRIMARY KEY,
    schema_version TEXT DEFAULT '1.0',
    parent_id TEXT REFERENCES evolution_events(id),
    intent TEXT,
    signals TEXT,
    genes_used TEXT,
    mutation_id TEXT,
    blast_radius TEXT,
    outcome TEXT,
    capsule_id TEXT REFERENCES capsules(id),
    env_fingerprint TEXT,
    meta TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
