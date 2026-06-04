"""
EvidenceParser — 解析验证智能体的原始输出。

优先尝试 JSON 解析，失败后降级到正则匹配，最终返回统一的
结构化 dict：{"passed": bool, "message": str, "evidence": list}。
"""

import json
import re

class EvidenceParser:
    """将验证智能体的原始输出转换为结构化证据结果。"""

    # 用于降级解析的关键词（避免使用 \b，因为中文没有 word boundary）
    _PASS_PATTERNS = re.compile(
        r"(passed|pass|success|successful|通过|成功)", re.IGNORECASE
    )
    _FAIL_PATTERNS = re.compile(
        r"(failed|fail|failure|失败)"
    )

    @staticmethod
    def parse(raw_output: str) -> dict:
        """解析验证输出，返回结构化结果。

        解析策略：
        1. 优先 JSON 解析：尝试从 raw_output 中提取并解析 JSON。
        2. 降级正则匹配：扫描 passed/failed 关键词判断结果。
        3. 兜底：返回默认失败结果。

        Args:
            raw_output: 验证智能体的原始输出文本。

        Returns:
            dict，包含：
              - passed (bool):   是否通过
              - message (str):   简要说明
              - evidence (list): 证据条目列表
        """
        if not raw_output or not raw_output.strip():
            return {
                "passed": False,
                "message": "验证输出为空",
                "evidence": [],
            }

        # ── 策略 1：JSON 解析 ─────────────────────────────
        json_result = EvidenceParser._try_parse_json(raw_output)
        if json_result is not None:
            return json_result

        # ── 策略 2：正则降级 ──────────────────────────────
        return EvidenceParser._parse_fallback(raw_output)

    # ── 内部方法 ──────────────────────────────────────────

    @staticmethod
    def _try_parse_json(raw: str) -> dict | None:
        """尝试从文本中提取 JSON 并规范化字段。"""
        text = raw.strip()

        # 1) 直接解析
        parsed = EvidenceParser._safe_load(text)
        if parsed is not None:
            return EvidenceParser._normalize(parsed)

        # 2) 去掉 markdown 代码围栏
        stripped = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        stripped = re.sub(r"\s*```\s*$", "", stripped, flags=re.MULTILINE).strip()
        if stripped and stripped != text:
            parsed = EvidenceParser._safe_load(stripped)
            if parsed is not None:
                return EvidenceParser._normalize(parsed)

        # 3) 从文本中找第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            parsed = EvidenceParser._safe_load(text[start : end + 1])
            if parsed is not None:
                return EvidenceParser._normalize(parsed)

        return None

    @staticmethod
    def _safe_load(text: str) -> dict | None:
        """安全 JSON 加载，失败返回 None。"""
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    @staticmethod
    def _normalize(obj: dict) -> dict:
        """确保返回 dict 包含 passed / message / evidence 三个键。"""
        passed = obj.get("passed")
        if not isinstance(passed, bool):
            # 尝试从字符串推断
            passed = str(passed).lower() in ("true", "1", "yes", "pass", "通过")

        message = obj.get("message", "")
        if not isinstance(message, str):
            message = str(message)

        evidence = obj.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []

        return {
            "passed": passed,
            "message": message,
            "evidence": evidence,
        }

    @staticmethod
    def _parse_fallback(raw: str) -> dict:
        """正则降级：从纯文本中判断 passed/failed。"""
        has_pass = bool(EvidenceParser._PASS_PATTERNS.search(raw))
        has_fail = bool(EvidenceParser._FAIL_PATTERNS.search(raw))

        if has_fail and not has_pass:
            passed = False
            message = "文本中包含失败关键词，判定为未通过"
        elif has_pass:
            passed = True
            message = "文本中包含通过关键词，判定为通过"
        else:
            passed = False
            message = "无法从文本中识别通过/失败关键词，默认未通过"

        return {
            "passed": passed,
            "message": message,
            "evidence": [{"finding": raw[:500]}],
        }
