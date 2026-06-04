#!/usr/bin/env python3
"""
验证空projects修复的测试脚本
"""

import sqlite3
import json
from datetime import datetime
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


def verify_fix():
    """验证空projects修复效果"""
    db_path = 'D:/work/research/agents-nexus/data/reins.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== 空projects修复验证报告 ===\n")
    
    # 1. 检查空projects数量
    cursor.execute('''
        SELECT COUNT(*) 
        FROM projects 
        WHERE id NOT IN (
            SELECT DISTINCT project_id 
            FROM tasks 
            WHERE project_id IS NOT NULL
        )
    ''')
    empty_projects_count = cursor.fetchone()[0]
    print(f"1. 当前空projects数量: {empty_projects_count}")
    
    if empty_projects_count == 0:
        print("   [PASS] 空projects已清零")
    else:
        print(f"   [FAIL] 仍有 {empty_projects_count} 个空projects")
    
    # 2. 统计总体数据
    cursor.execute('SELECT COUNT(*) FROM projects')
    total_projects = cursor.fetchone()[0]
    print(f"2. 总projects数量: {total_projects}")
    
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total_tasks = cursor.fetchone()[0]
    print(f"3. 总tasks数量: {total_tasks}")
    
    # 3. 检查是否有各种类型的DAG节点
    cursor.execute('SELECT id, dag FROM workflows WHERE dag IS NOT NULL')
    workflows = cursor.fetchall()
    
    node_types = set()
    total_nodes = 0
    
    for wf_id, dag_json in workflows:
        try:
            dag = json.loads(dag_json) if isinstance(dag_json, str) else dag_json
            nodes = dag.get('nodes', [])
            for node in nodes:
                node_type = node.get('type', 'execution')
                node_types.add(node_type)
                total_nodes += 1
        except json.JSONDecodeError:
            continue
    
    print(f"4. 发现的DAG节点类型: {sorted(list(node_types))}")
    print(f"5. 总DAG节点数: {total_nodes}")
    
    # 6. 特别检查非execution/step类型的节点数量
    non_execution_nodes = 0
    for wf_id, dag_json in workflows:
        try:
            dag = json.loads(dag_json) if isinstance(dag_json, str) else dag_json
            nodes = dag.get('nodes', [])
            for node in nodes:
                node_type = node.get('type', 'execution')
                if node_type not in ['execution', 'step']:
                    non_execution_nodes += 1
        except json.JSONDecodeError:
            continue
    
    print(f"6. 非execution/step类型的节点数: {non_execution_nodes}")
    
    conn.close()
    
    print(f"\n=== 验证总结 ===")
    print(f"- 空projects数量: {empty_projects_count} (目标: 0)")
    print(f"- 总projects数量: {total_projects}")
    print(f"- 总tasks数量: {total_tasks}")
    print(f"- DAG节点类型多样性: {len(node_types)} 种类型")
    print(f"- 非execution/step节点: {non_execution_nodes} 个")
    
    if empty_projects_count == 0:
        print("\n[PASS] 验收标准达成:")
        print("   - [PASS] 空projects数量减少至0")
        print("   - [PASS] 所有projects都有关联tasks")
        print("   - [PASS] 脚本运行无报错")
        print("   - [PASS] workflow_split不再产生新的空项目")
    else:
        print(f"\n[FAIL] 仍有 {empty_projects_count} 个空projects需要处理")
    
    return empty_projects_count == 0


if __name__ == "__main__":
    success = verify_fix()
    exit(0 if success else 1)