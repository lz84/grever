"""
Sprint 35-b: 补充其余场景对应的目标 + 每个目标的 Workflow
"""
import sqlite3, json, uuid

DB = r'D:\work\research\agents-nexus\data\reins.db'
uid = lambda p='': f"{p}{uuid.uuid4().hex[:8]}"
conn = sqlite3.connect(DB)
c = conn.cursor()
now = '2026-04-22 16:30:00'

# ============================================================
# 补充其他3个场景的目标
# ============================================================
scenarios_data = [
    ('goal-eq-001', 'scenario-eq-001', '某省7.2级地震应急救援',
     '某省发生7.2级地震，震源深度15km，震中烈度Ⅸ度，造成大量房屋倒塌、基础设施损毁和人员伤亡',
     [
         ('proj-eq-001', '灾情评估与态势感知', 'completed', [
             ('卫星遥感影像获取与分析', 'done', 1, 'agent-satellite'),
             ('震区烈度分布图绘制', 'done', 1, 'agent-analytics'),
             ('房屋倒塌率评估', 'done', 2, 'agent-inspector'),
             ('伤亡人数初步统计', 'done', 2, 'agent-medical'),
         ]),
         ('proj-eq-002', '生命搜救与人员转移', 'in_progress', [
             ('搜救队伍编组与部署', 'done', 1, 'agent-rescue'),
             ('重点建筑废墟搜救', 'in_progress', 1, 'agent-search'),
             ('被困人员生命探测', 'in_progress', 1, 'agent-search'),
             ('伤员现场急救', 'in_progress', 2, 'agent-medical'),
             ('重伤员直升机转运', 'todo', 2, 'agent-transport'),
             ('临时避难所安置', 'todo', 3, 'agent-shelter'),
         ]),
         ('proj-eq-003', '基础设施抢修与恢复', 'active', [
             ('道路桥梁应急抢通', 'in_progress', 1, 'agent-engineer'),
             ('通信基站应急恢复', 'todo', 1, 'agent-comms'),
             ('电力线路抢修', 'todo', 2, 'agent-power'),
             ('供水系统排查修复', 'todo', 2, 'agent-water'),
         ]),
         ('proj-eq-004', '物资保障与灾后重建', 'active', [
             ('救灾物资紧急调拨', 'in_progress', 1, 'agent-logistics'),
             ('帐篷搭建与营地规划', 'todo', 2, 'agent-shelter'),
             ('灾后重建规划编制', 'todo', 3, 'agent-planner'),
         ]),
     ]),
    ('goal-flood-001', 'scenario-flood-001', '城市内涝防汛应急响应',
     '连续暴雨导致城市多处内涝，水位超警戒线，需紧急排水和疏散低洼地区居民',
     [
         ('proj-fl-001', '排水系统应急调度', 'in_progress', [
             ('排水泵站全开运行', 'done', 1, 'agent-drainage'),
             ('易涝点巡查监测', 'in_progress', 1, 'agent-inspector'),
             ('管道淤塞紧急疏通', 'todo', 2, 'agent-maintenance'),
             ('河道水位实时监控', 'in_progress', 1, 'agent-monitor'),
         ]),
         ('proj-fl-002', '群众转移安置', 'in_progress', [
             ('危险区域人员排查', 'done', 1, 'agent-community'),
             ('转移路线规划', 'done', 1, 'agent-planner'),
             ('群众分批转移', 'in_progress', 2, 'agent-transport'),
             ('安置点物资保障', 'todo', 2, 'agent-logistics'),
             ('特殊人群优先转移', 'todo', 3, 'agent-medical'),
         ]),
         ('proj-fl-003', '防汛物资调配', 'active', [
             ('沙袋防汛物资调拨', 'done', 1, 'agent-logistics'),
             ('抽水设备部署', 'in_progress', 2, 'agent-drainage'),
             ('应急发电设备部署', 'todo', 2, 'agent-power'),
         ]),
     ]),
    ('goal-fire-001', 'scenario-fire-001', '森林火灾扑救行动',
     '山区发生森林火灾，火势蔓延迅速，威胁周边村庄和重要设施',
     [
         ('proj-fi-001', '火情侦察与态势研判', 'in_progress', [
             ('无人机火场侦察', 'done', 1, 'agent-drone'),
             ('火势蔓延趋势模拟', 'done', 1, 'agent-analytics'),
             ('气象条件分析', 'in_progress', 2, 'agent-weather'),
             ('火线长度与强度测量', 'todo', 2, 'agent-inspector'),
         ]),
         ('proj-fi-002', '地面灭火力量部署', 'active', [
             ('消防队伍集结开赴火场', 'done', 1, 'agent-fire'),
             ('隔离带开辟', 'in_progress', 1, 'agent-engineer'),
             ('高压水枪阵地设置', 'todo', 2, 'agent-fire'),
             ('村庄周边防火隔离带', 'in_progress', 1, 'agent-fire'),
         ]),
         ('proj-fi-003', '空中灭火支援', 'active', [
             ('灭火直升机调配', 'done', 1, 'agent-aviation'),
             ('空中洒水作业', 'in_progress', 1, 'agent-aviation'),
             ('红外火场监测', 'todo', 2, 'agent-drone'),
         ]),
         ('proj-fi-004', '群众疏散与安置', 'active', [
             ('火场周边村庄疏散', 'done', 1, 'agent-community'),
             ('疏散路线交通管制', 'done', 1, 'agent-security'),
             ('临时安置点物资保障', 'in_progress', 2, 'agent-logistics'),
         ]),
     ]),
]

for goal_id, sc_id, title, desc, projects in scenarios_data:
    c.execute("""INSERT INTO goals
        (id, title, description, status, priority, progress, matched_scenario_id, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (goal_id, title, desc, 'in_progress', 'high', 35, sc_id, now, now))
    print(f'Goal: {title}')

    for pid, pname, pst, tasks in projects:
        c.execute("""INSERT INTO projects
            (id, name, description, goal_id, status, priority, members, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (pid, pname, f'项目：{pname}', goal_id, pst, 'high',
             json.dumps([{'agent_id': f'agent-{i}', 'role': 'member'} for i in range(1, 4)]),
             now, now))

        for ttitle, tstatus, tprio, tagent in tasks:
            tid = uid('task-')
            c.execute("""INSERT INTO tasks
                (id, title, description, project_id, goal_id, assigned_agent, status, priority, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (tid, ttitle, f'{ttitle} — 详细执行描述', pid, goal_id, tagent, tstatus, tprio, now, now))

        print(f'  [{pst}] {pname} → {len(tasks)} tasks')

conn.commit()

# 验证
print('\n=== 目标统计 ===')
for t in ['goals', 'projects', 'tasks']:
    c.execute(f'SELECT count(*) FROM {t}')
    print(f'{t}: {c.fetchone()[0]}')

print('\n=== 目标树 ===')
c.execute('SELECT id, title, status FROM goals')
for gid, gt, gs in c.fetchall():
    c.execute('SELECT count(*) FROM projects WHERE goal_id=?', (gid,))
    pc = c.fetchone()[0]
    c.execute('SELECT count(*) FROM tasks WHERE goal_id=?', (gid,))
    tc = c.fetchone()[0]
    print(f'  [{gs}] {gt} → {pc} projects, {tc} tasks')

conn.close()
print('\nDone!')
