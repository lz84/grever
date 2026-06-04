"""
目标分解辅助函数与提示词
从 goal_decompose.py 拆分出的 helpers 模块
"""
from loguru import logger
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from models.scenario import Scenario

def _get_scenario_guide(goal_id: str, goal_title: str, goal_description: Optional[str], db: Session) -> Optional[Dict[str, Any]]:
    """从场景库获取相关场景的标准操作指南并注入 LLM"""
    try:
        search_keywords = [goal_title]
        if goal_description:
            search_keywords.append(goal_description)

        scenario = db.query(Scenario).order_by(Scenario.usage_count.desc()).first()

        if not scenario:
            return None

        scenario_guide = {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "steps": scenario.steps if hasattr(scenario, 'steps') else [],
        }

        return scenario_guide

    except Exception as e:
        logger.info(f"[goal_decompose] 获取场景指南失败: {e}")
        return None

def _build_decomposition_prompt_with_scenario(
    goal_title: str,
    goal_description: Optional[str],
    scenario_guide: Optional[Dict[str, Any]]
) -> str:
    """构建含场景注入的分解提示词"""
    user_prompt = f"""
请分析以下目标并将其分解为可执行的项目：

## 目标
- 名称：{goal_title}
- 描述：{goal_description or '无'}
"""
    if scenario_guide:
        user_prompt += f"""
## 参考场景：{scenario_guide.get('name', 'unnamed')}
{scenario_guide.get('description', '')}
"""
        steps = scenario_guide.get('steps', [])
        if steps:
            if isinstance(steps, list):
                user_prompt += "\n标准操作步骤：\n"
                for i, step in enumerate(steps):
                    if isinstance(step, dict):
                        user_prompt += f"{i+1}. {step.get('title', step.get('name', str(step)))}: {step.get('description', '')}\n"
                    else:
                        user_prompt += f"{i+1}. {step}\n"

    user_prompt += """
请将上述目标分解为 3-8 个项目，每个项目代表一个可独立交付的工作包。

返回严格的 JSON 格式：
{
  "projects": [
    {
      "name": "项目名称",
      "description": "项目详细描述",
      "priority": "high|medium|low",
      "category": "research|design|implementation|testing|review|other",
      "depends_on": [依赖的项目索引，从 0 开始]
    }
  ]
}
"""
    return user_prompt

DECOMPOSITION_SYSTEM_PROMPT = """你是一位专业的项目分解专家。你的任务是将一个高层目标（Goal）分解为可执行的、逻辑连贯的子项目（Project）列表。

要求
1. 每个子项目应该是具体的、有明确交付物的独立项目
2. 子项目之间应建立合理的依赖关系（形成 DAG 结构）
3. 考虑研究/设计/实施/验证等完整项目流程
4. 项目粒度通常在 3-8 个之间，不要过度分解
5. 为每个子项目指定优先级：low/medium/high
6. 为每个子项目指定类型：research/design/implementation/testing/review/other
7. 如有提供相关场景指南，请参考其中的标准操作流程

返回格式：严格的详细 JSON：
{
  "projects": [
    {
      "name": "项目名称",
      "description": "项目详细描述",
      "priority": "high|medium|low",
      "category": "research|design|implementation|testing|review|other",
      "depends_on": [依赖的项目索引，从 0 开始]
    }
  ]
}

注意：
- depends_on 使用项目列表中的索引（0-based），多个依赖用数组
- 第一个项目通常没有依赖
- 确保依赖关系不形成循环"""
