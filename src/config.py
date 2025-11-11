"""
配置管理模块
使用 Pydantic Settings 管理环境变量配置
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path


class Config(BaseSettings):
    """应用配置类"""

    # Telegram Bot 配置
    telegram_bot_token: str
    bot_admin_user_id: int

    # 滴答清单 API 配置
    dida_access_token: str
    dida_base_url: str = "https://api.dida365.com"

    # AI Assistant 配置（GLM）
    anthropic_api_key: Optional[str] = None
    anthropic_base_url: str = "https://open.bigmodel.cn/api/anthropic"
    anthropic_model: str = "glm-4.6"

    class Config:
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_config()

    def _validate_config(self):
        """验证配置的完整性"""
        if not self.telegram_bot_token or self.telegram_bot_token == "your_telegram_bot_token_here":
            raise ValueError("TELEGRAM_BOT_TOKEN 未设置或使用默认值")

        if not self.dida_access_token or self.dida_access_token == "your_dida_personal_token_here":
            raise ValueError("DIDA_ACCESS_TOKEN 未设置或使用默认值")

        if not self.bot_admin_user_id:
            raise ValueError("BOT_ADMIN_USER_ID 未设置")

        print(f"配置加载成功:")
        print(f"  Bot Token: {self.telegram_bot_token[:20]}...")
        print(f"  Admin User ID: {self.bot_admin_user_id}")
        print(f"  Dida Token: {self.dida_access_token[:20]}...")

        # AI助手配置检查
        if self.anthropic_api_key:
            print(f"  GLM AI: 已启用 ({self.anthropic_model})")
        else:
            print(f"  AI Assistant: 未启用 (请配置 ANTHROPIC_API_KEY)")


# 全局配置实例函数
def get_config() -> Config:
    """获取配置实例"""
    return Config()