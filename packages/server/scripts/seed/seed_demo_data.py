"""填充 Goal → Project → Task 三级演示数据"""
import sqlite3
import uuid
from datetime import datetime, timedelta

DB = r'D:\work\research\agents-nexus\data\reins.db'

def uid(prefix=''):
    return f"{prefix}{uuid.uuid4().hex[:8]}"

now = datetime.utcnow()

# 清理重复地震目标（保留1个有数据的）
# 先删掉孤立的重复目标
goals_to_remove = [
    'goal-9ad15a67b364', 'goal-643d131680c5', 'goal-7e8d884f9983',
    'goal-2a47fb331bd1', 'goal-47bf0ef11c62',
]

# 定义 5 个真实目标，每个有项目和任务
goals = [
    {
        'id': 'goal-1bb69fa86bfa',
        'title': '某地7.2级地震救援',
        'desc': '某省某市发生7.2级地震，震源深度10km，需紧急开展救援工作',
        'status': 'in_progress',
        'priority': 'high',
        'projects': [
            {
                'name': '灾情评估与态势感知',
                'desc': '快速评估震区灾情，建立指挥体系',
                'status': 'completed',
                'tasks': [
                    {'title': '卫星遥感影像分析', 'status': 'done', 'priority': 1, 'agent': 'agent-satellite'},
                    {'title': '震区人口热力分析', 'status': 'done', 'priority': 1, 'agent': 'agent-analytics'},
                    {'title': '建立前线指挥部', 'status': 'done', 'priority': 2, 'agent': 'agent-command'},
                    {'title': '灾情初步报告生成', 'status': 'done', 'priority': 2, 'agent': 'agent-reporter'},
                ]
            },
            {
                'name': '生命搜救与医疗救护',
                'desc': '组织搜救力量开展人员搜救和伤员救治',
                'status': 'in_progress',
                'tasks': [
                    {'title': '搜救力量部署', 'status': 'done', 'priority': 1, 'agent': 'agent-rescue'},
                    {'title': '重点区域生命探测', 'status': 'in_progress', 'priority': 1, 'agent': 'agent-search'},
                    {'title': '野战医院搭建', 'status': 'in_progress', 'priority': 2, 'agent': 'agent-medical'},
                    {'title': '重伤员后送转运', 'status': 'todo', 'priority': 2, 'agent': 'agent-transport'},
                ]
            },
            {
                'name': '物资调配与后勤保障',
                'desc': '保障灾区基本生活物资供应',
                'status': 'active',
                'tasks': [
                    {'title': '应急物资需求评估', 'status': 'done', 'priority': 1, 'agent': 'agent-logistics'},
                    {'title': '物资仓库调拨', 'status': 'in_progress', 'priority': 2, 'agent': 'agent-logistics'},
                    {'title': '临时安置点设置', 'status': 'todo', 'priority': 3, 'agent': 'agent-shelter'},
                ]
            },
        ]
    },
    {
        'id': uid('goal-'),
        'title': '城市内涝防汛应急响应',
        'desc': '连续暴雨导致城市多处内涝，需启动防汛应急响应',
        'status': 'in_progress',
        'priority': 'high',
        'projects': [
            {
                'name': '排水系统应急调度',
                'desc': '启动所有排水泵站，疏通管道',
                'status': 'in_progress',
                'tasks': [
                    {'title': '排水泵站全开运行', 'status': 'done', 'priority': 1, 'agent': 'agent-drainage'},
                    {'title': '易涝点巡查监测', 'status': 'in_progress', 'priority': 1, 'agent': 'agent-inspector'},
                    {'title': '管道淤塞紧急疏通', 'status': 'todo', 'priority': 2, 'agent': 'agent-maintenance'},
                ]
            },
            {
                'name': '群众转移安置',
                'desc': '转移低洼地区和危险区域群众',
                'status': 'active',
                'tasks': [
                    {'title': '危险区域人员排查', 'status': 'done', 'priority': 1, 'agent': 'agent-community'},
                    {'title': '转移路线规划', 'status': 'in_progress', 'priority': 1, 'agent': 'agent-planner'},
                    {'title': '安置点物资准备', 'status': 'todo', 'priority': 2, 'agent': 'agent-logistics'},
                ]
            },
        ]
    },
    {
        'id': uid('goal-'),
        'title': '化工园区危化品泄漏处置',
        'desc': '化工园区储罐区发生危化品泄漏，需紧急处置',
        'status': 'planned',
        'priority': 'high',
        'projects': [
            {
                'name': '泄漏源控制',
                'desc': '封堵泄漏点，防止扩散',
                'status': 'active',
                'tasks': [
                    {'title': '泄漏物质鉴定', 'status': 'todo', 'priority': 1, 'agent': 'agent-chemistry'},
                    {'title': '泄漏点封堵方案', 'status': 'todo', 'priority': 1, 'agent': 'agent-engineer'},
                    {'title': '应急堵漏作业', 'status': 'todo', 'priority': 1, 'agent': 'agent-hazmat'},
                ]
            },
            {
                'name': '环境监测与预警',
                'desc': '持续监测周边环境和空气质量',
                'status': 'active',
                'tasks': [
                    {'title': '空气质量监测布点', 'status': 'todo', 'priority': 2, 'agent': 'agent-environment'},
                    {'title': '地下水污染检测', 'status': 'todo', 'priority': 2, 'agent': 'agent-environment'},
                    {'title': '居民疏散预警发布', 'status': 'todo', 'priority': 1, 'agent': 'agent-alert'},
                ]
            },
        ]
    },
    {
        'id': uid('goal-'),
        'title': '森林火灾扑救行动',
        'desc': '山区发生森林火灾，火势蔓延迅速',
        'status': 'planned',
        'priority': 'high',
        'projects': [
            {
                'name': '火情侦察与态势研判',
                'desc': '确定火场位置和蔓延趋势',
                'status': 'active',
                'tasks': [
                    {'title': '无人机火场侦察', 'status': 'todo', 'priority': 1, 'agent': 'agent-drone'},
                    {'title': '火势蔓延模拟', 'status': 'todo', 'priority': 1, 'agent': 'agent-simulator'},
                    {'title': '气象条件分析', 'status': 'todo', 'priority': 2, 'agent': 'agent-weather'},
                ]
            },
            {
                'name': '灭火力量部署',
                'desc': '组织地面和空中灭火力量',
                'status': 'active',
                'tasks': [
                    {'title': '消防力量集结', 'status': 'todo', 'priority': 1, 'agent': 'agent-fire'},
                    {'title': '空中洒水灭火', 'status': 'todo', 'priority': 1, 'agent': 'agent-aviation'},
                    {'title': '隔离带开辟', 'status': 'todo', 'priority': 2, 'agent': 'agent-engineer'},
                ]
            },
        ]
    },
    {
        'id': uid('goal-'),
        'title': '重大活动安保任务',
        'desc': '国际峰会期间安全保障工作',
        'status': 'draft',
        'priority': 'medium',
        'projects': [
            {
                'name': '安全风险评估',
                'desc': '全面评估活动安全风险',
                'status': 'active',
                'tasks': [
                    {'title': '威胁情报收集', 'status': 'todo', 'priority': 1, 'agent': 'agent-intel'},
                    {'title': '场地安全检测', 'status': 'todo', 'priority': 1, 'agent': 'agent-inspector'},
                    {'title': '应急预案制定', 'status': 'todo', 'priority': 2, 'agent': 'agent-planner'},
                ]
            },
            {
                'name': '安保力量部署',
                'desc': '部署警力和技术安保力量',
                'status': 'active',
                'tasks': [
                    {'title': '核心区域布控', 'status': 'todo', 'priority': 1, 'agent': 'agent-security'},
                    {'title': '外围巡控路线规划', 'status': 'todo', 'priority': 2, 'agent': 'agent-patrol'},
                    {'title': '技防系统调试', 'status': 'todo', 'priority': 2, 'agent': 'agent-tech'},
                ]
            },
        ]
    },
]

conn = sqlite3.connect(DB)
c = conn.cursor()

# 清理旧数据（保留 goal-001 和它的 projects/tasks 作为测试用）
# 删除没有关联项目的重复地震目标
for gid in goals_to_remove:
    c.execute('DELETE FROM goals WHERE id = ?', (gid,))
    print(f'Deleted duplicate goal: {gid}')

# 插入新目标
for g in goals:
    ts = now.isoformat()
    c.execute('''INSERT OR REPLACE INTO goals 
        (id, title, description, status, priority, progress, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (g['id'], g['title'], g['desc'], g['status'], g['priority'], 0, ts, ts))
    print(f'Goal: {g["id"]} - {g["title"]} ({g["status"]})')

# 为每个目标创建项目和任务
total_tasks = 0
for g in goals:
    for pi, proj in enumerate(g['projects']):
        pid = uid('proj-')
        ts = now.isoformat()
        c.execute('''INSERT INTO projects 
            (id, name, description, goal_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (pid, proj['name'], proj['desc'], g['id'], proj['status'], ts, ts))
        print(f'  Project: {pid} - {proj["name"]}')

        for ti, task in enumerate(proj['tasks']):
            tid = uid('task-')
            c.execute('''INSERT INTO tasks 
                (id, title, description, status, priority, goal_id, project_id, 
                 assigned_agent, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (tid, task['title'], f'{task["title"]} - 详细描述',
                 task['status'], task['priority'],
                 g['id'], pid, task['agent'],
                 ts, ts))
            total_tasks += 1
            print(f'    Task: {tid} - {task["title"]} ({task["status"]})')

conn.commit()

# 统计
c.execute('SELECT count(*) FROM goals')
gc = c.fetchone()[0]
c.execute('SELECT count(*) FROM projects')
pc = c.fetchone()[0]
c.execute('SELECT count(*) FROM tasks')
tc = c.fetchone()[0]

print(f'\n=== 数据统计 ===')
print(f'Goals: {gc}')
print(f'Projects: {pc}')
print(f'Tasks: {tc}')

conn.close()
