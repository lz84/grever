-- Sprint 98 P2-6: 新增 pack_type 变更时的校验 TRIGGER
-- 现有 validate_custom_pack_update 只监控 base_pack_id 列的 UPDATE
-- 新增 TRIGGER 监控 pack_type 列的 UPDATE（防止 standard->custom 时绕过校验）

CREATE TRIGGER validate_custom_pack_type_change
BEFORE UPDATE OF pack_type ON industry_packs
WHEN NEW.pack_type = 'custom' AND NEW.base_pack_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'custom_pack_requires_base: pack_type 改为 custom 时必须指定 base_pack_id');
END;
