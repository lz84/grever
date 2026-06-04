#!/usr/bin/env python3
"""
Sprint 46 Task 46-1: 修复任务依赖引用

功能:
- 遍历所有 tasks，解析 `dependencies` JSON 字段
- 对每个 task，通过 `project_id → goal_id → workflow_id` 找到对应 DAG
- 从 workflow 获取 DAG 数据，建立 `node_id → task_id` 映射
- 替换 dependencies 中的 DAG 节点 ID 为实际 task ID
- 写入 `task_dependencies` 表（规范化存储）
- 无法映射的引用标记为 orphan 并清理
"""

import json
import sqlite3
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime


def get_database_connection():
    """获取数据库连接"""
    from pathlib import Path
    
    # 使用 SQLAlchemy 连接数据库
    db_path = r"D:\work\research\agents-nexus\data\reins.db"
    engine = create_engine(f"sqlite:///{db_path}")
    return engine


def get_node_to_task_mapping_for_workflow(db, workflow_id: str) -> Dict[str, str]:
    """
    为指定 workflow 建立 node_id → task_id 映射
    该函数模拟 workflow_split.py 中的逻辑来构建映射
    """
    # 获取 workflow 的 DAG 数据
    wf_result = db.execute(text(
        "SELECT dag, goal_id FROM workflows WHERE id = :workflow_id"
    ), {"workflow_id": workflow_id}).fetchone()
    
    if not wf_result:
        print(f"Warning: Workflow {workflow_id} not found")
        return {}
    
    dag_data = json.loads(wf_result.dag) if isinstance(wf_result.dag, str) else wf_result.dag
    if not dag_data:
        dag_data = {"nodes": [], "edges": []}
    
    # 获取该 workflow 下的所有 tasks，按 project_id 分组
    tasks_result = db.execute(text(
        "SELECT id, project_id FROM tasks WHERE goal_id = :goal_id"
    ), {"goal_id": wf_result.goal_id}).fetchall()
    
    # 获取所有相关的 projects
    project_task_map = {}  # project_id -> task_id
    for task_row in tasks_result:
        project_task_map[task_row.project_id] = task_row.id
    
    # 获取 projects 信息以关联到 DAG 节点
    projects_result = db.execute(text(
        "SELECT id, workflow_id FROM projects WHERE goal_id = :goal_id AND workflow_id = :workflow_id"
    ), {"goal_id": wf_result.goal_id, "workflow_id": workflow_id}).fetchall()
    
    # 建立 project_id -> node_id 的映射
    project_to_node = {}
    for proj_row in projects_result:
        project_to_node[proj_row.id] = proj_row.id  # 实际上我们需要的是 project 与 DAG 节点的关联
    
    # 重新实现映射逻辑：基于 workflow DAG 节点和实际创建的 tasks
    nodes = dag_data.get("nodes", [])
    node_to_task = {}
    
    # 遍历 DAG 节点，尝试找到对应的 task
    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("type", "execution")
        
        # 根据 workflow_split.py 的逻辑，只有特定类型的节点会创建任务
        if node_type in ("execution", "step"):
            # 寻找与该节点相关的 project 和 task
            # 由于 project 名称可能与 node 标题匹配，我们尝试这种方式
            node_title = node.get("title", node.get("name", ""))
            
            # 查找该项目下的 task
            project_result = db.execute(text(
                "SELECT id FROM projects WHERE workflow_id = :workflow_id AND name = :node_title LIMIT 1"
            ), {"workflow_id": workflow_id, "node_title": node_title}).fetchone()
            
            if project_result:
                # 在这个 project 下查找 task
                task_result = db.execute(text(
                    "SELECT id FROM tasks WHERE project_id = :project_id LIMIT 1"
                ), {"project_id": project_result.id}).fetchone()
                
                if task_result:
                    node_to_task[node_id] = task_result.id
            else:
                # 如果找不到精确匹配的 project，尝试按顺序或其他方式匹配
                # 这里使用一种启发式方法：根据 phase_order 匹配
                project_result = db.execute(text(
                    "SELECT id FROM projects WHERE workflow_id = :workflow_id AND phase_order = :node_order LIMIT 1"
                ), {
                    "workflow_id": workflow_id, 
                    "node_order": node.get("order", 0)
                }).fetchone()
                
                if project_result:
                    task_result = db.execute(text(
                        "SELECT id FROM tasks WHERE project_id = :project_id LIMIT 1"
                    ), {"project_id": project_result.id}).fetchone()
                    
                    if task_result:
                        node_to_task[node_id] = task_result.id

    # 如果上面的方法没找到足够的映射，尝试另一种方法
    # 直接查询当前 project_id 和 goal_id 的任务
    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("type", "execution")
        
        if node_type in ("execution", "step"):
            # 查找同一 goal_id 和 workflow_id 下的 task
            # 但需要知道 node 对应哪个 project，这里我们反向工程
            project_result = db.execute(text("""
                SELECT p.id 
                FROM projects p
                JOIN tasks t ON t.project_id = p.id
                WHERE p.workflow_id = :workflow_id
                AND p.goal_id = (
                    SELECT goal_id 
                    FROM tasks 
                    WHERE project_id = p.id 
                    LIMIT 1
                )
                LIMIT 1
            """), {"workflow_id": workflow_id}).fetchone()
            
            if project_result:
                # 查找属于这个 project 的 task
                task_results = db.execute(text(
                    "SELECT id FROM tasks WHERE project_id = :project_id"
                ), {"project_id": project_result.id}).fetchall()
                
                # 尝试将 node_id 映射到 task_id
                for task_row in task_results:
                    # 这里我们尝试通过一些属性匹配 node 和 task
                    task_details = db.execute(text(
                        "SELECT title, description FROM tasks WHERE id = :task_id"
                    ), {"task_id": task_row.id}).fetchone()
                    
                    if task_details:
                        # 如果 task 的标题与 node 的标题相似，建立映射
                        node_title = node.get("title", node.get("name", "")).lower()
                        task_title = task_details.title.lower()
                        
                        if node_title == task_title or node_title.replace(" ", "_") == task_title.replace(" ", "_"):
                            node_to_task[node_id] = task_row.id
                            break
    
    return node_to_task


def fix_task_dependencies():
    """执行修复任务依赖的主函数"""
    print("开始修复任务依赖引用...")
    
    engine = get_database_connection()
    
    with engine.connect() as conn:
        # 开始事务
        trans = conn.begin()
        
        try:
            # 1. 获取所有有 dependencies 的 tasks
            tasks_result = conn.execute(text(
                "SELECT id, project_id, goal_id, dependencies FROM tasks WHERE dependencies IS NOT NULL AND dependencies != '[]'"
            )).fetchall()
            
            print(f"找到 {len(tasks_result)} 个有依赖的任务")
            
            orphan_count = 0
            fixed_count = 0
            
            # 清空现有的 task_dependencies 表，准备重新填充
            conn.execute(text("DELETE FROM task_dependencies"))
            
            for task_row in tasks_result:
                task_id = task_row.id
                project_id = task_row.project_id
                dependencies_str = task_row.dependencies
                
                if not dependencies_str or dependencies_str == '[]':
                    continue
                
                try:
                    dependencies = json.loads(dependencies_str)
                except json.JSONDecodeError:
                    print(f"任务 {task_id} 的依赖字段格式错误: {dependencies_str}")
                    continue
                
                # 检查是否包含非 UUID 格式的依赖（即可能是 DAG 节点 ID）
                has_dag_refs = any(not is_valid_uuid(dep) for dep in dependencies)
                
                if not has_dag_refs:
                    # 如果已经是有效 UUID，跳过
                    continue
                
                # 获取 project 的 workflow_id
                project_result = conn.execute(text(
                    "SELECT workflow_id FROM projects WHERE id = :project_id"
                ), {"project_id": project_id}).fetchone()
                
                if not project_result or not project_result.workflow_id:
                    print(f"任务 {task_id} 对应的项目 {project_id} 没有关联的 workflow")
                    orphan_count += len([dep for dep in dependencies if not is_valid_uuid(dep)])
                    # 清理无效依赖
                    valid_deps = [dep for dep in dependencies if is_valid_uuid(dep)]
                    if valid_deps != dependencies:
                        new_deps_str = json.dumps(valid_deps, ensure_ascii=False)
                        conn.execute(text(
                            "UPDATE tasks SET dependencies = :deps WHERE id = :task_id"
                        ), {"deps": new_deps_str, "task_id": task_id})
                    continue
                
                workflow_id = project_result.workflow_id
                
                # 获取该 workflow 的 node_id → task_id 映射
                node_to_task = get_node_to_task_mapping_for_workflow(conn, workflow_id)
                
                # 转换依赖
                new_dependencies = []
                for dep in dependencies:
                    if is_valid_uuid(dep):
                        # 已经是有效的 task ID，直接保留
                        new_dependencies.append(dep)
                    elif dep in node_to_task:
                        # 是 DAG 节点 ID，转换为 task ID
                        mapped_task_id = node_to_task[dep]
                        new_dependencies.append(mapped_task_id)
                        print(f"映射: {dep} -> {mapped_task_id} (任务 {task_id})")
                    else:
                        # 无法映射，标记为 orphan
                        print(f"无法映射依赖: {dep} (任务 {task_id})")
                        orphan_count += 1
                        # 不添加到新的依赖列表中（清理 orphan 引用）
                
                # 更新任务的依赖
                new_deps_str = json.dumps(new_dependencies, ensure_ascii=False)
                conn.execute(text(
                    "UPDATE tasks SET dependencies = :deps WHERE id = :task_id"
                ), {"deps": new_deps_str, "task_id": task_id})
                
                if new_dependencies != dependencies:
                    fixed_count += 1
                    print(f"修复任务 {task_id} 的依赖: {dependencies} -> {new_dependencies}")
                
                # 将依赖关系写入 task_dependencies 表
                for dep_task_id in new_dependencies:
                    # 检查是否已经存在此依赖关系
                    existing_dep = conn.execute(text(
                        "SELECT 1 FROM task_dependencies WHERE task_id = :task_id AND dependency_id = :dep_id"
                    ), {"task_id": task_id, "dep_id": dep_task_id}).fetchone()
                    
                    if not existing_dep:
                        # 插入新的依赖关系
                        conn.execute(text("""
                            INSERT INTO task_dependencies (task_id, dependency_id)
                            VALUES (:task_id, :dep_id)
                        """), {
                            "task_id": task_id,
                            "dep_id": dep_task_id
                        })
            
            trans.commit()
            print(f"修复完成! 修复了 {fixed_count} 个任务的依赖，发现 {orphan_count} 个孤儿依赖")
            
            # 统计 task_dependencies 表中的记录数量
            dep_count = conn.execute(text("SELECT COUNT(*) FROM task_dependencies")).fetchone()[0]
            print(f"task_dependencies 表现在有 {dep_count} 条记录")
            
        except Exception as e:
            trans.rollback()
            print(f"修复过程中出错，已回滚: {str(e)}")
            raise e


def is_valid_uuid(uuid_str: str) -> bool:
    """检查字符串是否为有效的 UUID"""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def validate_fix():
    """验证修复结果"""
    print("\n开始验证修复结果...")
    
    engine = get_database_connection()
    
    with engine.connect() as conn:
        # 检查 task_dependencies 表是否有数据
        dep_count = conn.execute(text("SELECT COUNT(*) FROM task_dependencies")).fetchone()[0]
        print(f"OK task_dependencies 表有 {dep_count} 条记录")
        
        # 检查 tasks 表中的依赖是否都是有效的 task ID
        tasks_result = conn.execute(text(
            "SELECT id, dependencies FROM tasks WHERE dependencies IS NOT NULL AND dependencies != '[]'"
        )).fetchall()
        
        invalid_deps = 0
        total_deps = 0
        
        for task_row in tasks_result:
            try:
                deps = json.loads(task_row.dependencies)
                for dep in deps:
                    total_deps += 1
                    # 检查依赖是否是有效的 task ID
                    task_exists = conn.execute(text(
                        "SELECT 1 FROM tasks WHERE id = :task_id"
                    ), {"task_id": dep}).fetchone()
                    
                    if not task_exists:
                        print(f"ERROR 任务 {task_row.id} 的依赖 {dep} 不存在")
                        invalid_deps += 1
            except json.JSONDecodeError:
                print(f"ERROR 任务 {task_row.id} 的依赖字段格式错误: {task_row.dependencies}")
                invalid_deps += 1
        
        if invalid_deps == 0:
            print(f"OK 所有 {total_deps} 个依赖都指向有效的任务 ID")
        else:
            print(f"ERROR 发现 {invalid_deps}/{total_deps} 个无效依赖")
        
        # 检查 task_dependencies 表中外键约束的有效性
        invalid_fk_count = conn.execute(text("""
            SELECT COUNT(*) 
            FROM task_dependencies td
            LEFT JOIN tasks t1 ON td.task_id = t1.id
            LEFT JOIN tasks t2 ON td.dependency_id = t2.id
            WHERE t1.id IS NULL OR t2.id IS NULL
        """)).fetchone()[0]
        
        if invalid_fk_count == 0:
            print("OK task_dependencies 表中外键引用都有效")
        else:
            print(f"ERROR task_dependencies 表中有 {invalid_fk_count} 个无效外键引用")
    
    print("验证完成!")


if __name__ == "__main__":
    print("开始执行任务依赖修复脚本...")
    
    # 先备份数据库（简单复制）
    import shutil
    from datetime import datetime
    backup_name = f"D:/work/research/agents-nexus/data/reins-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    try:
        shutil.copy(r"D:\work\research\agents-nexus\data\reins.db", backup_name)
        print(f"数据库已备份至: {backup_name}")
    except Exception as e:
        print(f"备份失败: {str(e)}")
        response = input("是否继续？(y/N): ")
        if response.lower() != 'y':
            exit(1)
    
    # 执行修复
    fix_task_dependencies()
    
    # 验证修复结果
    validate_fix()
    
    print("\n任务依赖修复脚本执行完毕!")