#!/usr/bin/env python3
"""
清理空projects的脚本

根据审计发现，82个项目中有25个没有关联任务。
原因是workflow_split.py只为type="execution"或type="step"的DAG节点创建task。
如果DAG节点类型是其他值（如decision, milestone），project就为空。
"""

import sqlite3
import json
from typing import List, Dict, Tuple
import argparse


def get_empty_projects(db_path: str) -> List[Dict]:
    """查询没有tasks的projects"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询没有关联任务的projects
    cursor.execute('''
        SELECT p.id, p.name, p.description, p.workflow_id, w.dag
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        LEFT JOIN workflows w ON p.workflow_id = w.id
        WHERE t.project_id IS NULL
    ''')
    
    empty_projects = []
    for row in cursor.fetchall():
        project = {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'workflow_id': row[3],
            'dag': row[4]
        }
        empty_projects.append(project)
    
    conn.close()
    return empty_projects


def analyze_dag_node_types(empty_projects: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """分析空projects的DAG节点类型，区分是否需要创建placeholder task"""
    needs_placeholder = []
    can_delete = []
    
    for project in empty_projects:
        dag_str = project.get('dag')
        if not dag_str:
            can_delete.append(project)
            continue
            
        try:
            dag = json.loads(dag_str) if isinstance(dag_str, str) else dag_str
            nodes = dag.get('nodes', [])
            
            # 找到与当前project同名或相似的节点
            project_node = None
            for node in nodes:
                if node.get('title') == project['name'] or node.get('name') == project['name']:
                    project_node = node
                    break
            
            if project_node:
                node_type = project_node.get('type', 'execution')
                # 如果节点类型不是execution或step，则需要创建placeholder task
                if node_type not in ['execution', 'step']:
                    needs_placeholder.append({
                        'project': project,
                        'node': project_node,
                        'node_type': node_type
                    })
                else:
                    # 如果是execution或step类型但没有task，可能是其他问题
                    can_delete.append(project)
            else:
                # 没有找到对应的DAG节点，可能可以删除
                can_delete.append(project)
                
        except json.JSONDecodeError:
            # DAG格式错误，考虑删除
            can_delete.append(project)
    
    return needs_placeholder, can_delete


def create_placeholder_tasks(db_path: str, placeholder_projects: List[Dict]):
    """为需要的projects创建placeholder task"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    created_tasks = 0
    
    for item in placeholder_projects:
        project = item['project']
        node = item['node']
        
        # 生成task ID
        import uuid
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        
        # 创建placeholder task
        cursor.execute('''
            INSERT INTO tasks 
            (id, title, description, project_id, goal_id, assigned_agent, status, priority, dependencies, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (
            task_id,
            f"Placeholder for {project['name']}",
            f"Placeholder task for {node.get('type', 'unknown')} node type",
            project['id'],
            project.get('goal_id', ''),
            '',
            'todo',
            'medium',
            '[]'
        ))
        
        created_tasks += 1
        print(f"Created placeholder task {task_id} for project {project['id']} (node type: {item['node_type']})")
    
    conn.commit()
    conn.close()
    
    print(f"Created {created_tasks} placeholder tasks")


def delete_empty_projects(db_path: str, projects_to_delete: List[Dict]):
    """删除确实不需要的空projects"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    deleted_count = 0
    
    for project in projects_to_delete:
        # 删除project
        cursor.execute('DELETE FROM projects WHERE id = ?', (project['id'],))
        deleted_count += 1
        print(f"Deleted empty project {project['id']}: {project['name']}")
    
    conn.commit()
    conn.close()
    
    print(f"Deleted {deleted_count} empty projects")


def main():
    parser = argparse.ArgumentParser(description='清理空projects')
    parser.add_argument('--db-path', default='D:/work/research/agents-nexus/data/reins.db', 
                       help='数据库路径')
    parser.add_argument('--dry-run', action='store_true', 
                       help='只显示将要执行的操作，不实际修改数据')
    args = parser.parse_args()
    
    print("开始分析空projects...")
    
    # 获取空projects
    empty_projects = get_empty_projects(args.db_path)
    print(f"发现 {len(empty_projects)} 个空projects")
    
    if len(empty_projects) == 0:
        print("没有发现空projects，任务完成")
        return
    
    # 分析DAG节点类型
    needs_placeholder, can_delete = analyze_dag_node_types(empty_projects)
    
    print(f"\n需要创建placeholder task的projects: {len(needs_placeholder)}")
    for item in needs_placeholder:
        project = item['project']
        print(f"  - {project['id']}: {project['name']} (type: {item['node_type']})")
    
    print(f"\n可以直接删除的projects: {len(can_delete)}")
    for project in can_delete:
        print(f"  - {project['id']}: {project['name']}")
    
    if args.dry_run:
        print("\n这是dry-run模式，不会修改任何数据")
        return
    
    # 执行操作
    if needs_placeholder:
        print(f"\n正在创建placeholder tasks...")
        create_placeholder_tasks(args.db_path, needs_placeholder)
    
    if can_delete:
        print(f"\n正在删除空projects...")
        delete_empty_projects(args.db_path, can_delete)
    
    # 最终统计
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) 
        FROM projects 
        WHERE id NOT IN (SELECT DISTINCT project_id FROM tasks WHERE project_id IS NOT NULL)
    ''')
    remaining_empty = cursor.fetchone()[0]
    conn.close()
    
    print(f"\n清理完成！剩余空projects数量: {remaining_empty}")


if __name__ == "__main__":
    main()