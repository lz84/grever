"""
飞书通知服务

提供向飞书发送任务通知的功能
当任务进入 waiting_human 状态时发送通知给相关人类用户
"""

import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

class FeishuNotificationService:
    """飞书通知服务类"""
    
    def __init__(self, webhook_url: Optional[str] = None, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        """
        初始化飞书通知服务
        
        Args:
            webhook_url: 飞书群机器人webhook URL (用于简单消息)
            app_id: 飞书应用ID (用于更复杂的消息发送)
            app_secret: 飞书应用密钥
        """
        self.webhook_url = webhook_url
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.token_expire_time = None
        
    def _get_access_token(self) -> Optional[str]:
        """
        获取飞书应用访问令牌
        """
        if self.access_token and self.token_expire_time and datetime.now() < self.token_expire_time:
            # 令牌仍在有效期内
            return self.access_token
            
        if not self.app_id or not self.app_secret:
            logger.warning("飞书应用ID或密钥未配置，无法获取访问令牌")
            return None
            
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            data = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                # 设置过期时间为提前5分钟刷新
                import time
                self.token_expire_time = datetime.fromtimestamp(time.time() + result.get("expire", 7200) - 300)
                return self.access_token
            else:
                logger.error(f"获取飞书访问令牌失败: {result}")
                return None
        except Exception as e:
            logger.error(f"获取飞书访问令牌异常: {e}")
            return None
    
    def send_task_waiting_human_notification(self, task_id: str, task_title: str, task_description: str, 
                                           user_id: str = None, user_email: str = None, 
                                           task_link: str = None, submit_link: str = None) -> bool:
        """
        发送任务等待人类输入的通知
        
        Args:
            task_id: 任务ID
            task_title: 任务标题
            task_description: 任务描述
            user_id: 用户ID (可选)
            user_email: 用户邮箱 (可选)
            task_link: 任务详情链接
            submit_link: 提交入口链接
            
        Returns:
            bool: 发送成功返回True，否则返回False
        """
        try:
            # 构建通知消息
            message = self._build_task_waiting_human_message(
                task_id, task_title, task_description, user_id, user_email, task_link, submit_link
            )
            
            # 发送消息
            if self.webhook_url:
                return self._send_via_webhook(message)
            elif self.app_id and self.app_secret:
                return self._send_via_app_access_token(message, user_id, user_email)
            else:
                logger.warning("未配置飞书通知方式，跳过发送")
                return False
                
        except Exception as e:
            logger.error(f"发送飞书通知异常: {e}")
            return False
    
    def _build_task_waiting_human_message(self, task_id: str, task_title: str, task_description: str,
                                        user_id: str = None, user_email: str = None,
                                        task_link: str = None, submit_link: str = None) -> Dict[str, Any]:
        """
        构建任务等待人类输入的消息内容
        """
        title = f"任务需要您处理 - {task_title}"
        
        content = f"任务需要您的输入\n\n"
        content += f"任务ID: {task_id}\n"
        content += f"任务标题: {task_title}\n"
        content += f"任务描述: {task_description}\n\n"
        
        if task_link:
            content += f"任务详情: {task_link}\n"
        if submit_link:
            content += f"提交入口: {submit_link}\n"
        
        content += f"请及时处理，谢谢！"
        
        # 返回富文本格式的消息
        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "template": "yellow",
                    "title": {
                        "content": title,
                        "tag": "plain_text"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": content,
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "content": "查看任务详情",
                                    "tag": "plain_text"
                                },
                                "type": "default"
                            }
                        ]
                    }
                ]
            }
        }
    
    def _send_via_webhook(self, message: Dict[str, Any]) -> bool:
        """
        通过Webhook发送消息
        """
        try:
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.post(self.webhook_url, headers=headers, json=message, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("StatusCode") == 0 or result.get("code") == 0:
                logger.info(f"飞书Webhook通知发送成功")
                return True
            else:
                logger.error(f"飞书Webhook通知发送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"飞书Webhook通知发送异常: {e}")
            return False
    
    def _send_via_app_access_token(self, message: Dict[str, Any], user_id: str = None, user_email: str = None) -> bool:
        """
        通过应用访问令牌发送消息
        """
        access_token = self._get_access_token()
        if not access_token:
            logger.error("无法获取飞书访问令牌，发送失败")
            return False
        
        try:
            # 确定接收者
            receiver_id = None
            if user_id:
                receiver_id = user_id
            elif user_email:
                # 通过邮箱获取用户ID
                user_info = self._get_user_by_email(user_email, access_token)
                if user_info:
                    receiver_id = user_info.get("user_id")
            
            if not receiver_id:
                logger.warning("未指定接收者，发送至默认群组")
                # 发送到默认群组
                url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
                data = {
                    "receive_id": "default_chat_id",  # 应该从配置中获取
                    "content": json.dumps(message.get("card", {})),
                    "msg_type": "interactive"
                }
            else:
                # 发送给指定用户
                url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id"
                data = {
                    "receive_id": receiver_id,
                    "content": json.dumps(message.get("card", {})),
                    "msg_type": "interactive"
                }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"飞书应用通知发送成功")
                return True
            else:
                logger.error(f"飞书应用通知发送失败: {result}")
                return False
        except Exception as e:
            logger.error(f"飞书应用通知发送异常: {e}")
            return False
    
    def _get_user_by_email(self, email: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        通过邮箱获取用户信息
        """
        try:
            url = f"https://open.feishu.cn/open-apis/user/v1/batch_get_id?emails={email}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                users = result.get("data", {}).get("user_list", [])
                if users:
                    return users[0]
            return None
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None

# 全局通知服务实例
_feishu_service = None

def get_feishu_notification_service() -> Optional[FeishuNotificationService]:
    """
    获取飞书通知服务实例
    
    从环境变量或配置中加载必要的参数
    """
    global _feishu_service
    
    if _feishu_service is None:
        import os
        # 从环境变量获取配置
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        
        # 只有在配置了必要参数时才初始化服务
        if webhook_url or (app_id and app_secret):
            _feishu_service = FeishuNotificationService(webhook_url=webhook_url, app_id=app_id, app_secret=app_secret)
        else:
            logger.warning("飞书通知服务未配置，请设置 FEISHU_WEBHOOK_URL 或 FEISHU_APP_ID/FEISHU_APP_SECRET 环境变量")
    
    return _feishu_service

def notify_task_waiting_human(task_id: str, task_title: str, task_description: str, 
                            user_id: str = None, user_email: str = None,
                            task_link: str = None, submit_link: str = None) -> bool:
    """
    便捷函数：发送任务等待人类输入的通知
    
    Args:
        task_id: 任务ID
        task_title: 任务标题
        task_description: 任务描述
        user_id: 用户ID (可选)
        user_email: 用户邮箱 (可选)
        task_link: 任务详情链接
        submit_link: 提交入口链接
        
    Returns:
        bool: 发送成功返回True，否则返回False
    """
    service = get_feishu_notification_service()
    if service:
        return service.send_task_waiting_human_notification(
            task_id, task_title, task_description, user_id, user_email, task_link, submit_link
        )
    else:
        logger.warning(f"飞书通知服务未初始化，跳过发送任务 {task_id} 的通知")
        return False