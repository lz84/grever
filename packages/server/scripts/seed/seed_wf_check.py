"""
Sprint 35-c: 为每个目标创建 Workflow（让流程图有内容）
"""
import sqlite3, json, uuid

DB = r'D:\work\research\agents-nexus\data\reins.db'
uid = lambda p='': f"{p}{uuid.uuid4().hex[:8]}"
conn = sqlite3.connect(DB)
c = conn.cursor()
now = '2026-04-22 16:30:00'

# 查看现有工作流表结构
c.execute("PRAGMA table_info(workflows)")
cols = [r[1] for r in c.fetchall()]
print('workflows cols:', cols)

c.execute("PRAGMA table_info(workflow_steps)")
cols = [r[1] for r in c.fetchall()]
print('workflow_steps cols:', cols)

# 查看现有目标
c.execute('SELECT id, title, matched_scenario_id FROM goals')
goals = c.fetchall()
print('\nGoals:', goals)

conn.close()
