#!/usr/bin/env python3
"""检查 DB 表结构 vs Model 定义的不一致"""
import sqlite3

DB_PATH = '/home/user/tianshu/data/reins.db'
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

tables_to_check = [
    'human_input_requests',
    'execution_logs',
    'task_comments',
    'task_relations',
    'scheduler_logs',
    'trace_events',
    'tasks',
    'agents',
]

for table in tables_to_check:
    cur.execute(f"PRAGMA table_info({table})")
    cols = cur.fetchall()
    if cols:
        print(f"\n{table} ({len(cols)} cols):")
        for c in cols:
            print(f"  {c[1]:25s} {c[2]:15s} {'NOT NULL' if c[3] else 'NULL'}  DEFAULT={c[4]}")
    else:
        print(f"\n{table}: TABLE MISSING")

conn.close()