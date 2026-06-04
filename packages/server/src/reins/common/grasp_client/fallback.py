"""
Grasp 本地降级引擎 (Local Fallback Engine)

当 Grasp 服务不可用时，使用本地规则引擎提供降级服务。
实现 Grasp 的核心能力：
1. 意图理解 (intent_understanding) - 基于关键词模板匹配
2. 智能体匹配 (agent_matching) - 基于能力标签匹配
3. 任务认知抽取 (dispatch_cognition) - 从本地知识库检索
4. 认知反馈 (cognitive_feedback) - 本地记录
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# 认知数据文件路径
COGNITIONS_FILE = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "skills" / "grasp" / "memory" / "grasp" / "cognitions.jsonl"
if not COGNITIONS_FILE.exists():
    COGNITIONS_FILE = Path(__file__).parent.parent.parent / "data" / "cognitions.jsonl"

# ============================================================
# 意图理解模板库
# ============================================================

INTENT_TEMPLATES = [
    {
        "pattern": r"(开发|实现|创建|编写|构建|写|做|完成).*?(系统|平台|功能|模块|接口|API|页面|服务)",
        "intent": "development",
        "domain": "engineering",
        "confidence": 0.7,
        "suggested_tasks": [
            {"task_template": "需求分析", "priority": 1, "required_capabilities": ["analysis"]},
            {"task_template": "架构设计", "priority": 2, "required_capabilities": ["design"]},
            {"task_template": "编码实现", "priority": 3, "required_capabilities": ["coding"]},
            {"task_template": "测试验证", "priority": 4, "required_capabilities": ["testing"]},
        ],
    },
    {
        "pattern": r"(设计|规划|架构|方案).*?(系统|平台|架构|流程|结构|模型)",
        "intent": "design",
        "domain": "architecture",
        "confidence": 0.7,
        "suggested_tasks": [
            {"task_template": "需求调研", "priority": 1, "required_capabilities": ["research"]},
            {"task_template": "方案设计", "priority": 2, "required_capabilities": ["design"]},
            {"task_template": "方案评审", "priority": 3, "required_capabilities": ["review"]},
        ],
    },
    {
        "pattern": r"(调研|研究|分析|评估|对比|了解|学习).*?(技术|方案|工具|产品|市场)",
        "intent": "research",
        "domain": "research",
        "confidence": 0.65,
        "suggested_tasks": [
            {"task_template": "信息收集", "priority": 1, "required_capabilities": ["search"]},
            {"task_template": "对比分析", "priority": 2, "required_capabilities": ["analysis"]},
            {"task_template": "调研报告", "priority": 3, "required_capabilities": ["writing"]},
        ],
    },
    {
        "pattern": r"(修复|解决|处理|排查).*?(bug|错误|问题|异常|故障|崩溃)",
        "intent": "troubleshoot",
        "domain": "maintenance",
        "confidence": 0.75,
        "suggested_tasks": [
            {"task_template": "问题复现", "priority": 1, "required_capabilities": ["testing"]},
            {"task_template": "根因分析", "priority": 2, "required_capabilities": ["analysis"]},
            {"task_template": "修复实现", "priority": 3, "required_capabilities": ["coding"]},
            {"task_template": "回归测试", "priority": 4, "required_capabilities": ["testing"]},
        ],
    },
    {
        "pattern": r"(部署|发布|上线|配置|安装|搭建|初始化).*?(环境|服务|系统|服务器|数据库)",
        "intent": "deployment",
        "domain": "devops",
        "confidence": 0.7,
        "suggested_tasks": [
            {"task_template": "环境准备", "priority": 1, "required_capabilities": ["devops"]},
            {"task_template": "配置部署", "priority": 2, "required_capabilities": ["devops"]},
            {"task_template": "功能验证", "priority": 3, "required_capabilities": ["testing"]},
        ],
    },
    {
        "pattern": r"(优化|改进|提升|加速|减少|降低|增强).*?(性能|速度|效率|质量|成本|体验)",
        "intent": "optimization",
        "domain": "engineering",
        "confidence": 0.6,
        "suggested_tasks": [
            {"task_template": "性能分析", "priority": 1, "required_capabilities": ["analysis"]},
            {"task_template": "瓶颈定位", "priority": 2, "required_capabilities": ["profiling"]},
            {"task_template": "优化实现", "priority": 3, "required_capabilities": ["coding"]},
        ],
    },
    {
        "pattern": r"(测试|验证|检查|确认).*?(功能|接口|页面|流程|系统)",
        "intent": "testing",
        "domain": "qa",
        "confidence": 0.7,
        "suggested_tasks": [
            {"task_template": "测试用例设计", "priority": 1, "required_capabilities": ["testing"]},
            {"task_template": "自动化测试", "priority": 2, "required_capabilities": ["automation"]},
            {"task_template": "测试报告", "priority": 3, "required_capabilities": ["writing"]},
        ],
    },
    {
        "pattern": r"(文档|手册|说明|指南|教程|规范|标准).*?(编写|撰写|整理|更新|完善)",
        "intent": "documentation",
        "domain": "documentation",
        "confidence": 0.65,
        "suggested_tasks": [
            {"task_template": "资料收集", "priority": 1, "required_capabilities": ["research"]},
            {"task_template": "文档编写", "priority": 2, "required_capabilities": ["writing"]},
            {"task_template": "审核发布", "priority": 3, "required_capabilities": ["review"]},
        ],
    },
]

# ============================================================
# 本地知识库
# ============================================================

def _load_local_cognitions() -> List[dict]:
    """从本地文件加载认知"""
    if not COGNITIONS_FILE.exists():
        return []
    cognitions = []
    try:
        with open(COGNITIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        cognitions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return cognitions

# ============================================================
# 降级引擎
# ============================================================

class GraspFallbackEngine:
    """
    Grasp 本地降级引擎
    
    当 Grasp 服务不可用时，提供以下降级能力:
    - 意图理解: 基于正则模板匹配
    - 智能体匹配: 基于能力标签匹配
    - 认知抽取: 从本地知识库关键词检索
    """
    
    def __init__(self):
        self._cognitions = _load_local_cognitions()
    
    def reload(self):
        """重新加载本地知识库"""
        self._cognitions = _load_local_cognitions()
    
    def intent_understanding(
        self,
        user_goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        意图理解降级
        
        基于正则模板匹配用户意图，返回分解建议
        
        :param user_goal: 用户目标描述
        :param context: 上下文信息
        :return: 意图分析结果
        """
        best_match = None
        best_score = 0.0
        
        for template in INTENT_TEMPLATES:
            if re.search(template["pattern"], user_goal, re.IGNORECASE):
                # 匹配度计算：匹配到的关键词数量
                match = re.search(template["pattern"], user_goal, re.IGNORECASE)
                matched_text = match.group(0) if match else ""
                score = template["confidence"] * min(1.0, len(matched_text) / len(user_goal))
                
                if score > best_score:
                    best_score = score
                    best_match = template
        
        if best_match:
            return {
                "intent": {
                    "type": best_match["intent"],
                    "domain": best_match["domain"],
                    "confidence": round(best_score, 2),
                },
                "domain_context": {
                    "fallback": True,
                    "source": "local_template_engine",
                    "matched_pattern": best_match["pattern"][:50],
                },
                "suggested_tasks": best_match["suggested_tasks"],
                "fallback": True,
            }
        
        # 无匹配，返回通用分解
        return {
            "intent": {
                "type": "general",
                "domain": "general",
                "confidence": 0.3,
            },
            "domain_context": {
                "fallback": True,
                "source": "local_template_engine",
                "message": "未能匹配到特定意图模板，使用通用分解",
            },
            "suggested_tasks": [
                {"task_template": "需求分析", "priority": 1, "required_capabilities": ["analysis"]},
                {"task_template": "方案制定", "priority": 2, "required_capabilities": ["planning"]},
                {"task_template": "执行实施", "priority": 3, "required_capabilities": ["execution"]},
                {"task_template": "验证确认", "priority": 4, "required_capabilities": ["verification"]},
            ],
            "fallback": True,
        }
    
    def agent_matching(
        self,
        task_requirements: Dict[str, Any],
        available_agents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        智能体匹配降级
        
        基于能力标签匹配最佳 Agent
        
        :param task_requirements: 任务需求
        :param available_agents: 可用 Agent 列表
        :return: 匹配结果
        """
        required_caps = task_requirements.get("required_capabilities", [])
        task_type = task_requirements.get("task_type", "general")
        
        # 按能力匹配度排序
        scored_agents = []
        for agent in available_agents:
            agent_caps = set(agent.get("capabilities", []))
            required_set = set(required_caps)
            
            if required_set:
                match_score = len(agent_caps & required_set) / len(required_set)
            else:
                # 无特定需求时，根据任务类型匹配
                type_cap_map = {
                    "coding": {"coding", "programming"},
                    "design": {"design", "architecture"},
                    "testing": {"testing", "qa"},
                    "devops": {"devops", "deployment"},
                    "research": {"research", "analysis"},
                    "writing": {"writing", "documentation"},
                    "general": set(),
                }
                caps_for_type = type_cap_map.get(task_type, set())
                match_score = len(agent_caps & caps_for_type) / max(1, len(caps_for_type))
            
            scored_agents.append({
                "agent": agent,
                "score": round(match_score, 2),
            })
        
        scored_agents.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "matched_agents": [
                {
                    "agent_id": a["agent"].get("id", "unknown"),
                    "agent_name": a["agent"].get("name", "unknown"),
                    "match_score": a["score"],
                }
                for a in scored_agents[:3]
            ],
            "best_match": scored_agents[0] if scored_agents else None,
            "fallback": True,
            "source": "local_capability_matching",
        }
    
    def dispatch_cognition(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        max_cognitions: int = 5
    ) -> Dict[str, Any]:
        """
        任务认知抽取降级
        
        从本地知识库中关键词检索相关认知
        
        :param task_id: 任务 ID
        :param task_title: 任务标题
        :param task_description: 任务描述
        :param task_type: 任务类型
        :param context: 上下文
        :param max_cognitions: 最大返回认知数量
        :return: 认知抽取结果
        """
        # 提取关键词
        keywords = self._extract_keywords(task_title + " " + (task_description or ""))
        
        # 从本地知识库检索
        scored_cognitions = []
        for cog in self._cognitions:
            content = cog.get("content", "")
            tags = cog.get("tags", [])
            cog_type = cog.get("type", "")
            
            score = 0.0
            # 关键词匹配
            for kw in keywords:
                if kw in content.lower():
                    score += 0.3
                if kw in [t.lower() for t in tags]:
                    score += 0.5
                if kw in cog_type.lower():
                    score += 0.2
            
            if score > 0:
                scored_cognitions.append({
                    "cognition": cog,
                    "score": round(score, 2),
                })
        
        scored_cognitions.sort(key=lambda x: x["score"], reverse=True)
        top_cognitions = scored_cognitions[:max_cognitions]
        
        return {
            "cognitions": [
                {
                    "cognition_id": c["cognition"].get("cognition_id"),
                    "content": c["cognition"].get("content", ""),
                    "type": c["cognition"].get("type"),
                    "tags": c["cognition"].get("tags", []),
                    "relevance_score": c["score"],
                }
                for c in top_cognitions
            ],
            "total": len(scored_cognitions),
            "has_more": len(scored_cognitions) > max_cognitions,
            "fallback": True,
            "source": "local_keyword_search",
            "keywords_used": keywords,
        }
    
    def cognitive_feedback(
        self,
        task_id: str,
        execution_result: Dict[str, Any],
        learnings: Dict[str, Any]
    ) -> bool:
        """
        认知反馈降级
        
        本地记录反馈，等待 Grasp 恢复后同步
        
        :param task_id: 任务 ID
        :param execution_result: 执行结果
        :param learnings: 学习到的知识
        :return: 是否记录成功
        """
        # 本地记录（可后续扩展为持久化）
        feedback_entry = {
            "task_id": task_id,
            "execution_result": execution_result,
            "learnings": learnings,
            "recorded_at": __import__("datetime").datetime.now().isoformat(),
            "pending_sync": True,
        }
        
        # 简单记录到内存，后续可扩展为持久化存储
        if not hasattr(self, '_feedback_buffer'):
            self._feedback_buffer = []
        self._feedback_buffer.append(feedback_entry)
        
        return True
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """从文本中提取关键词"""
        # 移除标点
        text = re.sub(r'[,.!?;:，。！？；：、\(\)\[\]{}"\'\\]', ' ', text)
        # 按空格分割
        words = [w.strip().lower() for w in text.split() if len(w.strip()) > 1]
        # 常见停用词
        stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
            '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你',
            '会', '着', '没有', '看', '这', '那', '里', '什么', '怎么',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'shall', 'can',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'and', 'or', 'not', 'but', 'if', 'then', 'than', 'so', 'as',
        }
        return [w for w in words if w not in stopwords]
