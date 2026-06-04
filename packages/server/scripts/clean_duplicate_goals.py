import sqlite3

DB_PATH = r'D:\work\research\agents-nexus\data\reins.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find duplicate goals by title
cur.execute('SELECT title, COUNT(*) as cnt FROM goals GROUP BY title HAVING cnt > 1')
dups = cur.fetchall()

to_delete = []
for d in dups:
    title = d['title']
    print(f'Duplicate: {title} (count: {d["cnt"]})')
    cur.execute('SELECT id, status, priority, created_at FROM goals WHERE title = ? ORDER BY created_at DESC', (title,))
    rows = cur.fetchall()
    for i, r in enumerate(rows):
        print(f'  [{i}] id={r["id"]}, status={r["status"]}, priority={r["priority"]}, created={r["created_at"]}')
        if i > 0:
            to_delete.append(r['id'])

if to_delete:
    print(f'\nDeleting {len(to_delete)} duplicate goals (keeping newest)...')
    for gid in to_delete:
        # Delete related projects
        cur.execute('DELETE FROM projects WHERE goal_id = ?', (gid,))
        # Delete related tasks
        cur.execute('DELETE FROM tasks WHERE goal_id = ?', (gid,))
        # Delete the goal
        cur.execute('DELETE FROM goals WHERE id = ?', (gid,))
        print(f'  Deleted goal {gid}')
    conn.commit()
    print('Done!')
else:
    print('No duplicates to delete.')

conn.close()
