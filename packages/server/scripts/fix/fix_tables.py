import sqlite3

conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
c = conn.cursor()

# 创建 task_dependencies 表
c.execute('''CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id VARCHAR(32) NOT NULL,
    dependency_id VARCHAR(32) NOT NULL,
    PRIMARY KEY (task_id, dependency_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (dependency_id) REFERENCES tasks(id)
)''')
print('task_dependencies table created')

# 列出所有表
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for r in c.fetchall():
    print(r[0])

conn.commit()
conn.close()
