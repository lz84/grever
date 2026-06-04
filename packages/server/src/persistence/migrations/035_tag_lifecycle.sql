-- 1. industry_packs 新增 pack_type 和 base_pack_id 字段
ALTER TABLE industry_packs ADD COLUMN pack_type TEXT DEFAULT 'standard';
ALTER TABLE industry_packs ADD COLUMN base_pack_id TEXT;

-- 2. TRIGGER 校验：定制包必须有 base_pack_id（INSERT）
CREATE TRIGGER validate_custom_pack_insert
BEFORE INSERT ON industry_packs
WHEN NEW.pack_type = 'custom' AND NEW.base_pack_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'custom_pack_requires_base: 定制包必须指定 base_pack_id');
END;

-- 3. TRIGGER 校验：定制包 UPDATE 时 base_pack_id 不能设为 NULL
CREATE TRIGGER validate_custom_pack_update
BEFORE UPDATE OF base_pack_id ON industry_packs
WHEN OLD.pack_type = 'custom' AND NEW.base_pack_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'custom_pack_requires_base: 定制包的 base_pack_id 不能为 NULL');
END;

-- 4. industry_capability_tags 新增 replaced_by 字段
ALTER TABLE industry_capability_tags ADD COLUMN replaced_by TEXT;

-- 5. 新增版本管理三字段
ALTER TABLE industry_capability_tags ADD COLUMN version_major INTEGER DEFAULT 1;
ALTER TABLE industry_capability_tags ADD COLUMN version_minor INTEGER DEFAULT 0;
ALTER TABLE industry_capability_tags ADD COLUMN version_patch INTEGER DEFAULT 0;

-- 6. 创建索引
CREATE INDEX idx_ict_replaced_by ON industry_capability_tags(replaced_by);
CREATE INDEX idx_ip_pack_type ON industry_packs(pack_type);
CREATE INDEX idx_ip_base_pack ON industry_packs(base_pack_id);

-- 7. 现有数据默认值
UPDATE industry_packs SET pack_type = 'standard' WHERE pack_type IS NULL;
