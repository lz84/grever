#!/usr/bin/env python3
"""
029_migrate_data.py - 迁移旧的 task_attachments 数据到新的统一附件体系

旧表: task_attachments
新表: attachments + attachment_links

流程：
1. 创建新表（SQL）
2. 遍历旧记录，计算 sha256
3. 如果 hash 已存在 → 复用 attachment，只建 link
4. 如果文件不存在 → 跳过，记录日志
5. 迁移完成后将旧表重命名为 task_attachments_backup
"""

import os
import hashlib
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_db_path() -> str:
    """获取数据库路径"""
    # 优先使用环境变量
    env_path = os.environ.get("SQLITE_PATH")
    if env_path:
        return env_path
    
    # 默认路径
    default_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "reins.db"
    return str(default_path)


def sha256_file(filepath: str) -> Optional[str]:
    """计算文件 sha256"""
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def get_existing_attachment_by_hash(db: sqlite3.Connection, sha256: str) -> Optional[dict]:
    """检查是否已有相同 hash 的 attachment"""
    cursor = db.execute(
        "SELECT id, filename, file_path, mime_type, file_size, created_by, created_at FROM attachments WHERE sha256_hash = ?",
        (sha256,)
    )
    row = cursor.fetchone()
    if row:
        return {
            "id": row[0],
            "filename": row[1],
            "file_path": row[2],
            "mime_type": row[3],
            "file_size": row[4],
            "created_by": row[5],
            "created_at": row[6],
        }
    return None


def create_new_attachment(db: sqlite3.Connection, att_data: dict) -> str:
    """创建新的 attachments 记录，返回 attachment_id"""
    import uuid
    att_id = f"att-{uuid.uuid4().hex[:8]}"
    
    db.execute(
        """INSERT INTO attachments 
           (id, filename, file_path, mime_type, sha256_hash, file_size, created_by, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            att_id,
            att_data["filename"],
            att_data["file_path"],
            att_data["mime_type"],
            att_data["sha256_hash"],
            att_data["file_size"],
            att_data["created_by"],
            att_data["created_at"],
        )
    )
    db.commit()
    return att_id


def create_new_link(db: sqlite3.Connection, attachment_id: str, entity_type: str, entity_id: str, created_by: Optional[str] = None) -> str:
    """创建新的 attachment_links 记录，返回 link_id"""
    import uuid
    link_id = f"link-{uuid.uuid4().hex[:8]}"
    
    db.execute(
        """INSERT INTO attachment_links 
           (id, attachment_id, entity_type, entity_id, created_by, created_at) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            link_id,
            attachment_id,
            entity_type,
            entity_id,
            created_by,
            datetime.now().isoformat(),
        )
    )
    db.commit()
    return link_id


def main():
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"数据库不存在: {db_path}")
        return
    
    print(f"连接数据库: {db_path}")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    
    # 检查旧表是否存在
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='task_attachments'"
    )
    if not cursor.fetchone():
        print("旧表 task_attachments 不存在，跳过迁移")
        db.close()
        return
    
    print("检测到旧表 task_attachments，开始迁移...")
    
    # 获取所有旧记录
    cursor = db.execute("SELECT * FROM task_attachments ORDER BY created_at")
    old_records = cursor.fetchall()
    
    print(f"共 {len(old_records)} 条旧记录")
    
    migrated_count = 0
    skipped_count = 0
    reused_count = 0
    
    for record in old_records:
        task_id = record["task_id"]
        filename = record["filename"]
        file_path = record["file_path"]
        mime_type = record["mime_type"]
        file_size = record["file_size"]
        uploaded_by = record["uploaded_by"]
        created_at = record["created_at"]
        
        print(f"\n处理: task_id={task_id}, filename={filename}")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"  ⚠️  文件不存在，跳过: {file_path}")
            skipped_count += 1
            continue
        
        # 计算 sha256
        sha256 = sha256_file(file_path)
        if sha256 is None:
            print(f"  ⚠️  计算 sha256 失败，跳过: {file_path}")
            skipped_count += 1
            continue
        
        print(f"  sha256={sha256[:16]}...")
        
        # 检查是否已存在相同 hash
        existing = get_existing_attachment_by_hash(db, sha256)
        if existing:
            # 复用
            print(f"  ✓ 复用已存在的 attachment: {existing['id']}")
            create_new_link(db, existing["id"], "task", task_id, uploaded_by)
            reused_count += 1
        else:
            # 创建新 attachment + link
            att_data = {
                "filename": filename,
                "file_path": file_path,
                "mime_type": mime_type,
                "sha256_hash": sha256,
                "file_size": file_size,
                "created_by": uploaded_by,
                "created_at": created_at,
            }
            att_id = create_new_attachment(db, att_data)
            create_new_link(db, att_id, "task", task_id, uploaded_by)
            migrated_count += 1
            print(f"  ✓ 创建新 attachment: {att_id}")
    
    # 重命名旧表
    print("\n重命名旧表 task_attachments → task_attachments_backup")
    db.execute("ALTER TABLE task_attachments RENAME TO task_attachments_backup")
    db.commit()
    
    print("\n✅ 迁移完成!")
    print(f"  - 成功迁移: {migrated_count}")
    print(f"  - 复用已存在: {reused_count}")
    print(f"  - 跳过（文件不存在）: {skipped_count}")
    
    db.close()


if __name__ == "__main__":
    main()
