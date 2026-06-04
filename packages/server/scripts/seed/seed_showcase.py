"""
Sprint 35: 完整演示数据
场景库：化工危化品预案 + 3个其他场景
三级数据：1个旗舰目标 → 6个项目 → 32个任务
"""
import sqlite3, json, uuid

DB = r'D:\work\research\agents-nexus\data\reins.db'
uid = lambda p='': f"{p}{uuid.uuid4().hex[:8]}"
conn = sqlite3.connect(DB)
c = conn.cursor()
now = '2026-04-22 16:00:00'

# ============================================================  清空
for t in ['goals','projects','tasks','scenarios','scenario_steps','scenario_versions']:
    c.execute(f'DELETE FROM {t}')
print('Cleared.')

# ============================================================  场景库 - 旗舰化工预案
sc_id = 'scenario-chemical-001'
c.execute("""INSERT INTO scenarios (
    id,name,category,status,version,description,scenario_desc,triggers,
    total_executions,success_count,failed_count,success_rate,
    avg_duration_ms,min_duration_ms,max_duration_ms,
    avg_conflicts,avg_step_completion,usage_count,versions,
    created_at,updated_at,execution_log,level,template_dag,agent_requirements,trust_level,source
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
    sc_id, '化工园区储罐区危化品泄漏应急处置预案',
    'chemical','active','v1.2',
    '某化工园区储罐区管道法兰发生苯乙烯泄漏，有毒且易燃，风向东南，下风口有居民区约2000人',
    '本预案覆盖：泄漏发现→响应启动→泄漏控制→警戒疏散→环境监测→医疗救护→舆情应对→事后恢复',
    json.dumps(['储罐区异味','可燃气体报警','人员报告']),
    23,21,2,91.3,2850000,1800000,4200000,1.2,94.5,47,
    json.dumps([{'v':'v1.0','d':'2025-10-01'},{'v':'v1.1','d':'2026-01-15'},{'v':'v1.2','d':'2026-03-01'}]),
    now, now,
    json.dumps([{'ts':'2026-04-10T09:15:00','event':'启动预案','agent':'agent-command','status':'success'}]),
    '省级',
    json.dumps({'nodes':[{'id':'n1','type':'step','name':'启动应急响应'},{'id':'n2','type':'step','name':'泄漏源控制'},{'id':'n3','type':'step','name':'警戒与疏散'},{'id':'n4','type':'step','name':'环境监测'},{'id':'n5','type':'step','name':'医疗救护'},{'id':'n6','type':'step','name':'舆情应对'},{'id':'n7','type':'step','name':'事后评估'}],'edges':[{'source':'n1','target':'n2'},{'source':'n1','target':'n3'},{'source':'n2','target':'n4'},{'source':'n3','target':'n5'},{'source':'n4','target':'n7'},{'source':'n5','target':'n7'},{'source':'n6','target':'n7'}]}),
    json.dumps([{'type':'command','count':1},{'type':'hazmat','count':2},{'type':'security','count':3}]),
    '4.5','官方预案',
))
print(f'Scenario: {sc_id}')

for order,name,agent_type,caps in [
    (1,'启动应急响应','command','["应急指挥","快速决策"]'),
    (2,'泄漏源控制与封堵','hazmat','["危化品处置","堵漏技术"]'),
    (3,'警戒区划定与疏散','security','["警戒设置","疏散规划"]'),
    (4,'环境与气象监测','monitoring','["环境检测","数据分析"]'),
    (5,'中毒人员医疗救护','medical','["急救处置","伤员转运"]'),
    (6,'舆情应对与信息发布','comms','["信息发布","舆情引导"]'),
    (7,'事后评估与恢复','assessment','["影响评估","恢复规划"]'),
]:
    c.execute('INSERT INTO scenario_steps (id,scenario_id,"order",name,agent_type,required_capabilities) VALUES (?,?,?,?,?,?)',
        (uid('ss-'),sc_id,order,name,agent_type,caps))
print(f'  7 steps added')

# 额外3个场景
for sid,sname,cat,ver,total,success,failed,rate in [
    ('scenario-eq-001','某省7.2级地震应急救援预案','earthquake','v2.1',58,55,3,94.8),
    ('scenario-flood-001','城市内涝防汛应急响应预案','flood','v1.5',35,31,4,88.6),
    ('scenario-fire-001','森林火灾扑救应急行动预案','fire','v1.3',28,25,3,89.3),
]:
    c.execute("""INSERT INTO scenarios (
        id,name,category,status,version,description,scenario_desc,triggers,
        total_executions,success_count,failed_count,success_rate,
        avg_duration_ms,avg_step_completion,usage_count,versions,created_at,updated_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        sid,sname,cat,'active',ver,
        sname,f'{sname}详细描述',json.dumps(['报警']),
        total,success,failed,rate,3000000,90.0,total-5,
        json.dumps([{'v':ver,'d':'2026-01-01'}]),now,now
    ))
    print(f'Scenario: {sid}')

# ============================================================  旗舰目标
goal_id = 'goal-chemical-leak-001'
c.execute("""INSERT INTO goals
    (id,title,description,status,priority,progress,matched_scenario_id,created_at,updated_at)
    VALUES (?,?,?,?,?,?,?,?,?)""", (
    goal_id,
    '某化工园区储罐区危化品泄漏应急处置',
    '某化工园区内储罐区管道法兰发生苯乙烯泄漏，有毒易燃。风向东南，下风口2000米内有居民区约2000人',
    'in_progress','high',65,sc_id,now,now
))
print(f'\nGoal: {goal_id}')

# 6个项目
proj_ids = ['proj-001','proj-002','proj-003','proj-004','proj-005','proj-006']
proj_names = [
    '应急响应启动与指挥部建设',
    '泄漏源控制与风险评估',
    '警戒区划定与人员疏散',
    '环境应急监测与预警',
    '中毒人员医疗救护',
    '舆情应对与事后恢复',
]
proj_status = ['completed','in_progress','in_progress','active','active','active']

for pid,pname,pst in zip(proj_ids,proj_names,proj_status):
    c.execute("""INSERT INTO projects
        (id,name,description,goal_id,status,priority,members,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (pid,pname,f'项目：{pname}',goal_id,pst,'high',
         json.dumps([{'agent_id':f'agent-{j}','role':'member'} for j in range(1,4)]),
         now,now))
    print(f'  [{pst}] {pname}')

# 32个任务
tasks_raw = [
    ('proj-001','发布应急启动指令','done',1,'agent-command'),
    ('proj-001','成立现场应急指挥部','done',1,'agent-command'),
    ('proj-001','调度首批应急队伍和装备','done',2,'agent-logistics'),
    ('proj-001','建立信息通信链路','done',2,'agent-commander'),
    ('proj-002','泄漏物质鉴定与MSDS查询','done',1,'agent-chemistry'),
    ('proj-002','泄漏范围扩散趋势研判','in_progress',1,'agent-analytics'),
    ('proj-002','堵漏方案制定与审批','in_progress',1,'agent-engineer'),
    ('proj-002','堵漏作业实施','todo',2,'agent-hazmat'),
    ('proj-002','二次防护屏障设置','todo',2,'agent-hazmat'),
    ('proj-002','实时可燃气体监测','in_progress',2,'agent-monitor'),
    ('proj-003','确定警戒区范围（500m）','done',1,'agent-security'),
    ('proj-003','警戒线和警示标识设置','done',1,'agent-security'),
    ('proj-003','疏散路线规划与广播','done',1,'agent-planner'),
    ('proj-003','居民区挨家挨户疏散','in_progress',2,'agent-community'),
    ('proj-003','安置点物资和生活保障','todo',2,'agent-logistics'),
    ('proj-003','特殊人群转运','todo',3,'agent-medical'),
    ('proj-004','下风口空气质量实时监测','in_progress',1,'agent-monitor'),
    ('proj-004','周边水体污染监测','todo',1,'agent-environment'),
    ('proj-004','地下水采样分析','todo',2,'agent-environment'),
    ('proj-004','气象条件动态跟踪','todo',1,'agent-weather'),
    ('proj-004','扩散预警信息发布','in_progress',2,'agent-alert'),
    ('proj-005','现场急救点设置','done',1,'agent-medical'),
    ('proj-005','中毒人员洗消作业','in_progress',1,'agent-medical'),
    ('proj-005','重伤员转运至医院','in_progress',2,'agent-transport'),
    ('proj-005','野战医院搭建','todo',2,'agent-medical'),
    ('proj-005','中毒数据统计上报','todo',3,'agent-reporter'),
    ('proj-006','官方信息统一口径制定','in_progress',1,'agent-comms'),
    ('proj-006','新闻发布会筹备','todo',2,'agent-comms'),
    ('proj-006','社交媒体舆情监测','in_progress',1,'agent-monitor'),
    ('proj-006','泄漏区域环境损失评估','todo',2,'agent-assessment'),
    ('proj-006','恢复生产方案制定','todo',3,'agent-planner'),
    ('proj-006','应急演练总结报告','todo',3,'agent-reporter'),
]

for pid,title,status,priority,agent in tasks_raw:
    c.execute("""INSERT INTO tasks
        (id,title,description,project_id,goal_id,assigned_agent,status,priority,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (uid('task-'),title,f'{title} — 详细执行描述',pid,goal_id,agent,status,priority,now,now))

print(f'  {len(tasks_raw)} tasks created')

conn.commit()

# 验证
print('\n=== 最终数据 ===')
for t_name in ['scenarios','goals','projects','tasks']:
    c.execute(f'SELECT count(*) FROM {t_name}')
    print(f'  {t_name}: {c.fetchone()[0]}')

print('\n=== 目标树 ===')
c.execute('SELECT id,title,status,progress FROM goals')
for gid,gtitle,gst,gprog in c.fetchall():
    print(f'\n[{gst.upper()} {gprog}%] {gtitle}')
    c.execute('SELECT id,name,status FROM projects WHERE goal_id=?',(gid,))
    for prid,pname,pst in c.fetchall():
        c.execute('SELECT count(*) FROM tasks WHERE project_id=?',(prid,))
        tc=c.fetchone()[0]
        print(f'  ├─ [{pst}] {pname} ({tc}个任务)')
        c.execute('SELECT title,status,assigned_agent FROM tasks WHERE project_id=?',(prid,))
        for ttitle,tstatus,tagent in c.fetchall():
            print(f'  │   ├─ [{tstatus}] {ttitle} @{tagent}')

conn.close()
print('\nAll done!')
