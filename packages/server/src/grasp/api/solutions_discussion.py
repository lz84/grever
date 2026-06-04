from sqlalchemy import text
from fastapi import HTTPException
# -*- coding: utf-8 -*-
from loguru import logger

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from reins.common.database import get_db

from fastapi import APIRouter
router = APIRouter()

def _generate_ai_reply(content: str, goal_id: str, db: Session) -> str:
    """
    MVP: 基于关键词匹配生成 AI 回复（不调用外部 LLM）

    关键词匹配 + 模板回复
    """
    content_lower = content.lower()

    # 关键词匹配表
    keywords_responses = [
        (["开源", "open source", "free"], 
         "建议考虑开源方案替代。开源方案的优势：\n"
         "1. 降低成本，无需商业授权费用\n"
         "2. 社区活跃，迭代快\n"
         "3. 可定制性强\n"
         "需要注意：开源方案的稳定性和长期维护需要评估。"
         "我可以帮你对比开源与商业方案的具体参数差异。"),
        
        (["成本", "费用", "价格", "预算", "cost", "budget", "便宜"],
         "关于成本优化，建议：\n"
         "1. 优先评估轻量级方案，减少资源占用\n"
         "2. 考虑按需付费模式，避免前期大量投入\n"
         "3. 对比不同供应商的定价策略\n"
         "如果你有具体预算范围，我可以针对性推荐方案。"),
        
        (["性能", "速度", "快", "延迟", "performance", "speed", "latency"],
         "性能优化方向：\n"
         "1. 选择高吞吐量、低延迟的架构方案\n"
         "2. 考虑分布式部署提升并发能力\n"
         "3. 优化关键路径减少瓶颈\n"
         "需要我基于当前方案的性能数据做详细分析吗？"),
        
        (["安全", "风险", "合规", "security", "risk", "compliance"],
         "安全合规方面建议关注：\n"
         "1. 数据加密传输与存储\n"
         "2. 权限管控与审计日志\n"
         "3. 第三方组件的安全审查\n"
         "4. 是否符合行业合规要求（如等保、GDPR等）\n"
         "安全系数是方案评估的重要维度，建议在约束中明确最低要求。"),
        
        (["部署", "安装", "环境", "deploy", "install", "environment"],
         "部署方案建议：\n"
         "1. 容器化部署（Docker/K8s）提升可移植性\n"
         "2. CI/CD 自动化减少人工操作\n"
         "3. 多环境配置管理（dev/test/prod）\n"
         "你对部署环境有什么具体要求？我可以据此调整方案约束。"),
        
        (["兼容", "迁移", "集成", "compatibility", "migration", "integration"],
         "兼容性和集成建议：\n"
         "1. 优先选择有标准 API/SDK 的方案\n"
         "2. 评估与现有系统的数据格式兼容性\n"
         "3. 制定渐进式迁移策略\n"
         "如果你告诉我现有系统的技术栈，我可以给出更具体的集成建议。"),
        
        (["文档", "学习", "培训", "documentation", "learning", "training"],
         "文档和学习资源方面：\n"
         "1. 优先选择文档完善的方案\n"
         "2. 评估社区教程和案例数量\n"
         "3. 考虑团队的学习曲线\n"
         "好的文档可以大幅降低实施风险，建议作为评估维度之一。"),
        
        (["社区", "生态", "支持", "community", "ecosystem", "support"],
         "社区和生态评估：\n"
         "1. 查看 GitHub stars/forks 活跃度\n"
         "2. 评估 ISSUE 响应速度\n"
         "3. 关注是否有商业支持选项\n"
         "活跃的社区是方案长期可维护性的重要保障。"),
    ]

    for keywords, response in keywords_responses:
        if any(kw in content_lower for kw in keywords):
            return response

    # 默认回复：分析意图 + 建议
    # 简单分类：问题类 / 建议类 / 其他
    if any(q in content_lower for q in ["为什么", "怎么", "如何", "什么", "?", "？"]):
        return f"这是一个很好的问题。基于当前方案库的情况，我建议：\n" \
               f"1. 先明确你的核心需求优先级\n" \
               f"2. 对比现有方案是否满足\n" \
               f"3. 如有缺口，可以调整约束条件触发新一轮探索\n" \
               f"你可以告诉我具体的需求方向，我来给出针对性建议。"
    elif any(w in content_lower for w in ["好", "不错", "可以", "满意", "ok"]):
        return f"太好了！如果当前方案符合预期，可以考虑：\n" \
               f"1. 标记该方案为最优（is_optimal=1）\n" \
               f"2. 收敛迭代，进入实施阶段\n" \
               f"3. 记录本轮决策作为后续参考"
    elif any(w in content_lower for w in ["不", "不好", "不行", "不满意", "拒绝", "换"]):
        return f"理解你的反馈。我们可以：\n" \
               f"1. 调整约束参数，排除不满意的方案类型\n" \
               f"2. 触发新一轮迭代，探索不同方向\n" \
               f"3. 细化评估维度，更精准筛选\n" \
               f"请告诉我你希望调整哪些约束条件？"
    else:
        return f"收到你的反馈。当前方案库共有 {len(db.execute(text('SELECT COUNT(*) FROM solutions WHERE goal_id = :gid'), {'gid': goal_id}).fetchone())} 个方案。\n" \
               f"你可以：\n" \
               f"• 提出问题（如'能换成开源方案吗？'）\n" \
               f"• 表达偏好（如'成本太高了'、'需要更好的性能'）\n" \
               f"• 要求调整约束参数\n" \
               f"我会根据你的输入给出分析和建议。"

# ============ 迭代端点 ============

