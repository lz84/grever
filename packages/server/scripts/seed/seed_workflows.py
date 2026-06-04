"""
Sprint 35-c: 为每个目标创建 Workflow + Steps
"""
import sqlite3, json, uuid

DB = r'D:\work\research\agents-nexus\data\reins.db'
uid = lambda p='': f"{p}{uuid.uuid4().hex[:8]}"
conn = sqlite3.connect(DB)
c = conn.cursor()
now = '2026-04-22 16:35:00'

def make_wf(name, steps):
    """steps = [{'name': str, 'desc': str, 'agents': [...], 'deps': [prev_names]}, ...]"""
    nodes = []
    edges = []
    for i, s in enumerate(steps):
        nid = f'n{i+1}'
        nodes.append({'id': nid, 'name': s['name'], 'type': 'step', 'agents': s['agents']})
        for dep in s.get('deps', []):
            dep_idx = next((j for j, x in enumerate(steps) if x['name'] == dep), -1)
            if dep_idx >= 0:
                edges.append({'source': f'n{dep_idx+1}', 'target': nid})
    return {'name': name, 'steps': steps, 'dag': {'nodes': nodes, 'edges': edges}}

wfs = [
    make_wf('化工危化品泄漏应急响应流程', [
        {'name': '启动应急响应', 'desc': '发布应急指令，成立现场指挥部', 'agents': ['agent-command'], 'deps': []},
        {'name': '泄漏源控制', 'desc': '泄漏物质鉴定、堵漏方案制定与实施', 'agents': ['agent-chemistry', 'agent-hazmat'], 'deps': ['启动应急响应']},
        {'name': '警戒与疏散', 'desc': '划定警戒区，组织人员疏散', 'agents': ['agent-security', 'agent-community'], 'deps': ['启动应急响应']},
        {'name': '环境监测', 'desc': '空气、水体、土壤污染持续监测', 'agents': ['agent-monitor', 'agent-environment'], 'deps': ['泄漏源控制']},
        {'name': '医疗救护', 'desc': '中毒人员洗消和救治', 'agents': ['agent-medical'], 'deps': ['警戒与疏散']},
        {'name': '舆情应对', 'desc': '统一信息发布口径，舆情引导', 'agents': ['agent-comms'], 'deps': []},
        {'name': '事后评估', 'desc': '损失评估、恢复方案制定', 'agents': ['agent-assessment', 'agent-planner'], 'deps': ['环境监测', '医疗救护', '舆情应对']},
    ]),
    make_wf('地震应急救援流程', [
        {'name': '灾情评估', 'desc': '卫星遥感、烈度分析、伤亡统计', 'agents': ['agent-satellite', 'agent-analytics'], 'deps': []},
        {'name': '生命搜救', 'desc': '废墟搜救、生命探测、伤员转运', 'agents': ['agent-rescue', 'agent-search', 'agent-medical'], 'deps': ['灾情评估']},
        {'name': '基础设施抢修', 'desc': '道路抢通、通信电力恢复', 'agents': ['agent-engineer', 'agent-comms', 'agent-power'], 'deps': ['灾情评估']},
        {'name': '物资保障', 'desc': '救灾物资调拨、营地搭建', 'agents': ['agent-logistics', 'agent-shelter'], 'deps': ['灾情评估']},
        {'name': '灾后重建规划', 'desc': '编制重建方案', 'agents': ['agent-planner'], 'deps': ['基础设施抢修', '物资保障']},
    ]),
    make_wf('城市防汛应急响应流程', [
        {'name': '排水调度', 'desc': '泵站全开、管道疏通、水位监控', 'agents': ['agent-drainage', 'agent-inspector', 'agent-monitor'], 'deps': []},
        {'name': '群众转移', 'desc': '危险区域排查、分批转移、安置保障', 'agents': ['agent-community', 'agent-transport', 'agent-logistics'], 'deps': ['排水调度']},
        {'name': '防汛物资调配', 'desc': '沙袋调拨、抽水设备部署', 'agents': ['agent-logistics', 'agent-power'], 'deps': ['排水调度']},
    ]),
    make_wf('森林火灾扑救流程', [
        {'name': '火情侦察', 'desc': '无人机侦察、火势模拟、气象分析', 'agents': ['agent-drone', 'agent-analytics', 'agent-weather'], 'deps': []},
        {'name': '地面灭火', 'desc': '消防队伍部署、隔离带开辟', 'agents': ['agent-fire', 'agent-engineer'], 'deps': ['火情侦察']},
        {'name': '空中支援', 'desc': '直升机洒水、红外监测', 'agents': ['agent-aviation', 'agent-drone'], 'deps': ['火情侦察']},
        {'name': '群众疏散', 'desc': '周边村庄疏散、交通管制', 'agents': ['agent-community', 'agent-security'], 'deps': ['火情侦察']},
        {'name': '灾后评估', 'desc': '过火面积统计、生态损失评估', 'agents': ['agent-assessment', 'agent-environment'], 'deps': ['地面灭火', '空中支援', '群众疏散']},
    ]),
]

goals = ['goal-chemical-leak-001', 'goal-eq-001', 'goal-flood-001', 'goal-fire-001']

for goal_id, wf in zip(goals, wfs):
    wf_id = uid('wf-')
    c.execute('SELECT matched_scenario_id FROM goals WHERE id=?', (goal_id,))
    row = c.fetchone()
    sc_id = row[0] if row else None

    c.execute("""INSERT INTO workflows
        (id, goal_id, status, name, description, dag, created_at, updated_at,
         parent_scenario_id, level, workflow_metadata)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (wf_id, goal_id, 'draft', wf['name'], f'{wf["name"]}详细描述',
         json.dumps(wf['dag']), now, now, sc_id, 'goal',
         json.dumps({'auto_generated': True, 'source': 'scenario_template'})))

    for i, s in enumerate(wf['steps']):
        step_id = uid('ws-')
        dep_names = s.get('deps', [])
        dep_ids = []
        for dep in dep_names:
            dep_idx = next((j for j, x in enumerate(wf['steps']) if x['name'] == dep), -1)
            if dep_idx >= 0:
                dep_ids.append(f'ws-step-{dep_idx+1}')

        c.execute("""INSERT INTO workflow_steps
            (id, workflow_id, name, description, status, dependencies, "order",
             agent_id, retry_count, max_retries, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (step_id, wf_id, s['name'], s['desc'], 'pending',
             json.dumps(dep_ids), i+1, json.dumps(s['agents']), 0, 3, now, now))

    print(f'Workflow: {wf["name"]} ({len(wf["steps"])} steps)')

conn.commit()

# 验证
c.execute('SELECT count(*) FROM workflows')
print(f'workflows: {c.fetchone()[0]}')
c.execute('SELECT count(*) FROM workflow_steps')
print(f'workflow_steps: {c.fetchone()[0]}')

print('\n=== 工作流 ===')
c.execute('SELECT id, goal_id, name, status FROM workflows')
for wf_id, gid, wname, wst in c.fetchall():
    c.execute('SELECT count(*) FROM workflow_steps WHERE workflow_id=?', (wf_id,))
    sc = c.fetchone()[0]
    c.execute('SELECT title FROM goals WHERE id=?', (gid,))
    gt = c.fetchone()
    print(f'  {wname} [{wst}] ({sc} steps) → Goal: {gt[0] if gt else "??"}')

conn.close()
print('\nDone!')
