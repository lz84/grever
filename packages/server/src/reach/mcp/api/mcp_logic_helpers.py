"""
MCP Server 匹配辅助逻辑
从 mcp_logic.py 拆分
"""

from typing import List, Dict, Any

class MCPMatchHelpers:
    """关键词匹配与评分计算"""

    def _keyword_matching(self, desc: str, text: str) -> List[str]:
        """关键词匹配：检查 description 中的关键词是否在 text 中出现"""
        if not desc or not text:
            return []

        separators = ['，', '、', '.', '。', ' ', '和', '与', '或', '以及', '的', '是', '在', '对', '向', '从', '到']
        keywords = [desc]

        for sep in separators:
            new_keywords = []
            for kw in keywords:
                parts = [k.strip() for k in kw.split(sep) if k.strip()]
                new_keywords.extend(parts)
            keywords = new_keywords

        final_keywords = []
        for kw in keywords:
            if len(kw) >= 2:
                final_keywords.append(kw)
                if len(kw) >= 4 and all('\u4e00' <= c <= '\u9fa5' for c in kw):
                    for n in [2, 3]:
                        for i in range(len(kw) - n + 1):
                            gram = kw[i:i + n]
                            if gram not in final_keywords:
                                final_keywords.append(gram)

        matched = []
        for kw in final_keywords:
            if len(kw) >= 2:
                if kw.lower() in text.lower():
                    matched.append(kw)

        return matched

    def _calculate_match_score(self, agent_description: str, server: Dict[str, Any],
                               tools: List[Dict[str, Any]]) -> tuple:
        """计算 Agent 与 MCP Server 的匹配分数"""
        score = 0
        reasons = []

        server_name = server.get('name', '')
        server_desc = server.get('description', '')

        matched_names = self._keyword_matching(agent_description, server_name)
        if matched_names:
            score += 30
            reasons.append(f"MCP name matches: {', '.join(matched_names)}")

        matched_desc = self._keyword_matching(agent_description, server_desc)
        if matched_desc:
            score += 20
            reasons.append(f"MCP description matches: {', '.join(matched_desc)}")

        for tool in tools:
            tool_name = tool.get('name', '')
            tool_desc = tool.get('description', '')

            matched_tool_names = self._keyword_matching(agent_description, tool_name)
            if matched_tool_names:
                score += 10
                reasons.append(f"tool '{tool_name}' matches")

            matched_tool_desc = self._keyword_matching(agent_description, tool_desc)
            if matched_tool_desc:
                score += 5
                reasons.append(f"tool '{tool_name}' description matches: {', '.join(matched_tool_desc)}")

        return score, reasons
