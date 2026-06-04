"""
LLM 服务模块

提供统一的 LLM 调用接口，支持 OpenAI 兼容 API。
用于目标分解、任务生成等智能功能。
"""

import json
import os
from loguru import logger
from typing import Optional, List, Dict, Any

from openai import OpenAI, AsyncOpenAI

class LLMConfig:
    """LLM 配置"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        timeout: float = 120.0,  # BUG-008: 增加超时到 120s
    ):
        # 优先读入参，其次读 .env（通过 ReinsConfig 读取），最后用默认值
        from reins.common.config import ReinsConfig
        _cfg = ReinsConfig()
        self.api_key = api_key or _cfg.llm_api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or _cfg.llm_base_url or os.getenv(
            "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = model or _cfg.llm_model or os.getenv("LLM_MODEL", "qwen-plus")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

class LLMService:
    """LLM 服务 - 同步版本"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        调用 LLM 聊天补全

        Args:
            messages: 消息列表
            model: 模型名称（可选覆盖）
            temperature: 温度参数（可选覆盖）
            max_tokens: 最大 token 数（可选覆盖）
            response_format: 响应格式，如 {"type": "json_object"}

        Returns:
            LLM 响应的文本内容
        """
        try:
            kwargs: Dict[str, Any] = {
                "model": model or self.config.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            logger.info(f"LLM 调用成功，模型: {model or self.config.model}")
            return content or ""
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

class AsyncLLMService:
    """LLM 服务 - 异步版本"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
        return self._client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """异步调用 LLM 聊天补全"""
        try:
            kwargs: Dict[str, Any] = {
                "model": model or self.config.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            logger.info(f"LLM 异步调用成功，模型: {model or self.config.model}")
            return content or ""
        except Exception as e:
            logger.error(f"LLM 异步调用失败: {e}")
            raise

# 全局单例
_default_config = LLMConfig()
llm_service = LLMService(_default_config)
async_llm_service = AsyncLLMService(_default_config)
