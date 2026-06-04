"""连接性检查模块

MAK-214: Agent 派发机制 - 模型连通性检查
"""

import time as time_module
import requests
from loguru import logger

def check_model_connectivity(address: str, timeout: float = 3.0) -> tuple[bool, int, str]:
    """
    检查 agent model endpoint 的连通性
    
    参数：
    - address: Agent 地址
    - timeout: 超时时间（秒）
    
    返回：
    - connectivity_verified: 是否连通
    - duration_ms: 检查耗时（毫秒）
    - error_message: 错误信息（如有）
    """
    if not address:
        return False, 0, "No address provided"
    
    # 确保地址格式正确
    base_url = address.rstrip("/")
    
    # 尝试的端点列表
    endpoints = ["/health", "/api/status"]
    
    start_time = time_module.time()
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=timeout)
            duration_ms = int((time_module.time() - start_time) * 1000)
            if response.status_code < 500:
                return True, duration_ms, ""
        except requests.exceptions.Timeout:
            duration_ms = int((time_module.time() - start_time) * 1000)
            return False, duration_ms, f"Connection timeout ({timeout}s) to {endpoint}"
        except requests.exceptions.ConnectionError:
            duration_ms = int((time_module.time() - start_time) * 1000)
            continue  # 尝试下一个端点
        except Exception as e:
            duration_ms = int((time_module.time() - start_time) * 1000)
            return False, duration_ms, str(e)
    
    duration_ms = int((time_module.time() - start_time) * 1000)
    return False, duration_ms, f"Could not connect to any endpoint ({', '.join(endpoints)})"