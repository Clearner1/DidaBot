# -*- coding: utf-8 -*-
"""
滴答清单 Telegram Bot 主启动脚本
运行命令：python main.py
"""

import asyncio
import signal
import sys
import logging
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from bot import main as bot_main

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dida_bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """处理系统信号"""
    logger.info(f"收到信号 {sig}，正在优雅关闭 Bot...")
    sys.exit(0)


async def main():
    """主入口函数"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("BOT 滴答清单 Bot 正在启动...")

    # 启动 Bot（现在会正常结束）
    await bot_main()

    logger.info("HI Bot 已关闭")


def cli():
    """CLI 入口点"""
    try:
        # 检查 Python 版本
        if sys.version_info < (3, 8):
            print("[ERROR] 需要 Python 3.8 或更高版本")
            sys.exit(1)

        # 运行主程序
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nHI Bot 已关闭")
    except Exception as e:
        print(f"[ERROR] 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()