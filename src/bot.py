# -*- coding: utf-8 -*-
"""
Telegram Bot 主入口
滴答清单机器人的核心控制逻辑
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.error import TelegramError

from config import get_config
from dida_client import DidaClient
from handlers.task_handlers import TaskHandlers
from handlers.project_handlers import ProjectHandlers
from utils.formatter import format_help_message, format_error_message

# AI Assistant（可选）
try:
    from ai_assistant import AIAssistant
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    AIAssistant = None

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 对话状态常量
(IDLE, ACTIVE) = range(2)

# 对话超时时间（秒）
# 设置为 300 表示5分钟无对话自动超时，清除对话历史
CONVERSATION_TIMEOUT = 300


class DidaBot:
    """Telegram Bot 主类"""

    def __init__(self):
        """初始化 Bot"""
        self.config = get_config()
        self.dida_client = None
        self.application = None
        self.task_handlers = None
        self.project_handlers = None
        self.ai_assistant = None
        self._stop_event = None

    async def initialize(self):
        """异步初始化"""
        try:
            print("正在初始化配置...")
            print(f"Bot Token: {self.config.telegram_bot_token[:20]}...")
            print(f"Admin ID: {self.config.bot_admin_user_id}")
            print(f"Dida Token: {self.config.dida_access_token[:20]}...")

            # 初始化滴答清单客户端
            print("正在初始化滴答清单客户端...")
            self.dida_client = DidaClient(
                access_token=self.config.dida_access_token,
                base_url=self.config.dida_base_url
            )

            # 初始化命令处理器
            print("正在初始化命令处理器...")
            self.task_handlers = TaskHandlers(self.dida_client)
            self.project_handlers = ProjectHandlers(self.dida_client)

            # 初始化AI助手（如果配置了API密钥）
            if AI_AVAILABLE and self.config.anthropic_api_key:
                print("正在初始化AI助手...")
                self.ai_assistant = AIAssistant(
                    anthropic_api_key=self.config.anthropic_api_key,
                    anthropic_base_url=self.config.anthropic_base_url,
                    anthropic_model=self.config.anthropic_model,
                    dida_client=self.dida_client,
                    max_history_length=None,  # 不限制对话历史长度，保持完整对话
                )
                print("AI助手已启用")
            elif AI_AVAILABLE:
                print("AI助手未启用：请配置 ANTHROPIC_API_KEY 环境变量")
            else:
                print("AI助手不可用：缺少依赖")

            # 创建 Telegram Application
            print("正在创建Telegram应用...")
            self.application = Application.builder().token(self.config.telegram_bot_token).build()

            # 注册命令处理器
            print("正在注册命令处理器...")
            self._register_handlers()

            print("Bot 初始化成功!")
            return True

        except Exception as e:
            print(f"Bot 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _register_handlers(self):
        """注册所有命令处理器"""
        # 基础命令
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("reset", self._cmd_reset))

        # 项目命令
        self.application.add_handler(CommandHandler("projects", self.project_handlers.cmd_projects))
        self.application.add_handler(CommandHandler("project_info", self.project_handlers.cmd_project_info))

        # 任务命令
        self.application.add_handler(CommandHandler("addtask", self.task_handlers.cmd_addtask))
        self.application.add_handler(CommandHandler("listtasks", self.task_handlers.cmd_listtasks))
        self.application.add_handler(CommandHandler("completetask", self.task_handlers.cmd_completetask))
        self.application.add_handler(CommandHandler("deletetask", self.task_handlers.cmd_deletetask))

        # AI对话处理器（使用ConversationHandler实现上下文窗口）
        if self.ai_assistant:
            # 创建ConversationHandler用于AI对话
            ai_conversation_handler = ConversationHandler(
                entry_points=[
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self._handle_ai_start
                    )
                ],
                states={
                    IDLE: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self._handle_ai_start
                        )
                    ],
                    ACTIVE: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self._handle_ai_active
                        ),
                        CommandHandler("cancel", self._handle_ai_cancel)
                    ],
                    ConversationHandler.TIMEOUT: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self._handle_ai_timeout
                        )
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self._handle_ai_cancel),
                    CommandHandler("stop", self._handle_ai_cancel),
                ],
                conversation_timeout=CONVERSATION_TIMEOUT,
                per_user=True,
                allow_reentry=False
            )
            self.application.add_handler(ai_conversation_handler)
            logger.info("AI对话处理器（ConversationHandler）已注册")

        logger.info("命令处理器注册完成")

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start 命令"""
        # 验证用户权限
        if not await self._check_permission(update):
            return

        user_name = update.effective_user.first_name or update.effective_user.username

        from utils.formatter import escape_markdown

        welcome_message = f"""
欢迎使用滴答清单 Bot，{user_name}！

这是一个连接滴答清单的 Telegram 机器人，帮助您方便地管理任务。

**主要功能：**
• 查看和管理项目
• 创建、完成、删除任务
• 查看任务列表
• 设置任务优先级

**快速开始：**
1. 使用 /projects 查看您的项目
2. 使用 /addtask 项目ID 标题 创建任务
3. 使用 /listtasks 查看任务
4. 使用 /help 查看详细帮助

**提示：** 所有命令都需要提供项目ID，请先用 /projects 查看项目列表。
        """.strip()

        await update.message.reply_text(welcome_message)

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help 命令"""
        # 验证用户权限
        if not await self._check_permission(update):
            return

        help_message = format_help_message()
        await update.message.reply_text(help_message)

    async def _handle_ai_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI对话启动（IDLE状态）"""
        # 验证用户权限
        if not await self._check_permission(update):
            return ConversationHandler.END

        # 检查AI助手是否可用
        if not self.ai_assistant:
            await update.message.reply_text(
                "AI助手未启用。请使用命令：\n"
                "• /projects - 查看项目\n"
                "• /listtasks - 查看任务\n"
                "• /addtask - 添加任务\n"
                "• /help - 查看所有命令"
            )
            return ConversationHandler.END

        # 获取用户消息
        user_message = update.message.text
        logger.info(f"AI对话开始: {user_message[:100]}...")

        # 强制清理旧状态（防御性编程，防止超时后残留数据）
        context.user_data.clear()

        # 初始化对话历史
        context.user_data['conversation_history'] = []

        # 设置状态为ACTIVE
        context.user_data['state'] = ACTIVE

        # 显示正在输入状态（添加异常处理）
        try:
            await update.message.chat.send_action("typing")
        except TelegramError as e:
            logger.warning(f"发送typing状态失败（继续处理）: {e}")

        try:
            # 调用AI助手处理消息，传递对话历史
            from kosong.message import Message
            history = context.user_data['conversation_history']

            # 记录用户输入和开始处理
            logger.info(f"[用户输入] {user_message}")
            logger.info(f"[开始处理] 正在调用AI助手...")

            # 调用AI助手处理消息（传递 Telegram bot 实例用于发送工具调用通知）
            response = await self.ai_assistant.chat(
                user_message,
                history=history,
                telegram_bot=context.application.bot,
                telegram_chat_id=update.effective_chat.id
            )

            # 发送回复（自动分页）
            await self._send_long_message(update, response)

            # 将用户消息和AI回复添加到对话历史
            # 保持对话完整性，不裁剪
            history.append(Message(role="user", content=user_message))
            history.append(Message(role="assistant", content=response))

            # 保存回context.user_data（不裁剪，保持完整对话历史）
            context.user_data['conversation_history'] = history
            logger.info(f"对话历史已更新，当前共 {len(history)} 条消息")

            # 处理完成后保持ACTIVE状态，继续等待下一条消息
            return ACTIVE

        except TelegramError as e:
            logger.error(f"Telegram API错误: {e}")
            try:
                await update.message.reply_text("网络连接不稳定，请稍后再试...")
            except TelegramError:
                logger.error("无法发送错误消息，网络完全断开")
            # 出错时结束对话
            context.user_data.clear()
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"AI对话出错: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(f"对话处理失败: {str(e)}")
            except TelegramError:
                logger.error("无法发送错误消息")
            # 出错时结束对话
            context.user_data.clear()
            return ConversationHandler.END

    async def _handle_ai_active(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI对话继续（ACTIVE状态）"""
        # 验证用户权限
        if not await self._check_permission(update):
            return ConversationHandler.END

        # 获取用户消息
        user_message = update.message.text

        # 检查是否是取消命令（应该在fallback中处理，但这里也做检查）
        if user_message.lower() in ['/cancel', '/stop', '取消', '结束']:
            return await self._handle_ai_cancel(update, context)

        logger.info(f"AI对话继续: {user_message[:100]}...")

        # 显示正在输入状态（添加异常处理）
        try:
            await update.message.chat.send_action("typing")
        except TelegramError as e:
            logger.warning(f"发送typing状态失败（继续处理）: {e}")

        try:
            # 调用AI助手处理消息（使用累积的对话历史）
            from kosong.message import Message
            history = context.user_data.get('conversation_history', [])

            # 记录用户输入和开始处理
            logger.info(f"[用户输入] {user_message}")
            logger.info(f"[继续对话] 正在调用AI助手...")

            # 调用AI助手处理消息（传递 Telegram bot 实例用于发送工具调用通知）
            response = await self.ai_assistant.chat(
                user_message,
                history=history,
                telegram_bot=context.application.bot,
                telegram_chat_id=update.effective_chat.id
            )

            # 发送回复（自动分页）
            await self._send_long_message(update, response)

            # 将用户消息和AI回复添加到对话历史，实现上下文累积
            # 保持对话完整性，不裁剪
            history.append(Message(role="user", content=user_message))
            history.append(Message(role="assistant", content=response))

            # 保存回context.user_data（不裁剪，保持完整对话历史）
            context.user_data['conversation_history'] = history
            logger.info(f"对话历史已更新，当前共 {len(history)} 条消息")

            # 处理完成后保持ACTIVE状态，继续等待下一条消息
            return ACTIVE

        except TelegramError as e:
            logger.error(f"Telegram API错误: {e}")
            try:
                await update.message.reply_text("网络连接不稳定，请稍后再试...")
            except TelegramError:
                logger.error("无法发送错误消息，网络完全断开")
            # 出错时结束对话
            context.user_data.clear()
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"AI对话出错: {e}")
            import traceback
            traceback.print_exc()
            try:
                await update.message.reply_text(f"对话处理失败: {str(e)}")
            except TelegramError:
                logger.error("无法发送错误消息")
            # 出错时结束对话
            context.user_data.clear()
            return ConversationHandler.END

    async def _handle_ai_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI对话取消"""
        # 清理用户数据
        context.user_data.clear()

        # 发送结束消息
        await update.message.reply_text("对话已结束。如需继续，请直接发送新消息。")

        # 返回ConversationHandler.END
        return ConversationHandler.END

    async def _cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/reset 命令 - 重置AI对话历史"""
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 检查是否在AI对话状态中
        current_state = context.user_data.get('state')
        if current_state not in [IDLE, ACTIVE]:
            # 没有活跃对话，直接回复
            await update.message.reply_text("No active AI conversation to reset. Send any message to start a new conversation.")
            return

        # 清理对话历史
        context.user_data.clear()

        # 发送确认消息
        await update.message.reply_text("AI对话历史已重置，让我们开始新的对话吧！")

        # 保持在ACTIVE状态，准备接收新消息
        context.user_data['state'] = ACTIVE
        context.user_data['conversation_history'] = []

    async def _handle_ai_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI对话超时"""
        logger.info(f"对话超时清理 - 用户 {update.effective_user.id}")

        # 清理用户数据
        context.user_data.clear()

        # 发送超时消息
        if update.effective_message:
            await update.effective_message.reply_text(
                "对话已超时（5分钟无活动）。如需继续，请直接发送新消息。"
            )

        return ConversationHandler.END

    async def _send_long_message(self, update: Update, message: str):
        """发送长消息（自动分页，带节奏控制）"""
        if len(message) > 4000:
            chunks = [message[i:i+3800] for i in range(0, len(message), 3800)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(f"第 {i+1}/{len(chunks)} 部分:\n\n{chunk}")
                else:
                    # 添加小延迟避免Telegram速率限制
                    await asyncio.sleep(0.5)
                    await update.message.reply_text(f"第 {i+1}/{len(chunks)} 部分:\n\n{chunk}")
        else:
            await update.message.reply_text(message)

    async def _check_permission(self, update: Update) -> bool:
        """检查用户权限"""
        if update.effective_user.id != self.config.bot_admin_user_id:
            await update.message.reply_text("你没有权限使用此机器人")
            return False
        return True

    async def start(self):
        """启动机器人"""
        if not await self.initialize():
            raise Exception("Bot 初始化失败")

        # 创建停止事件
        self._stop_event = asyncio.Event()

        try:
            # 初始化应用
            await self.application.initialize()

            # 设置Telegram命令菜单
            from telegram import BotCommand
            commands = [
                BotCommand("start", "启动机器人"),
                BotCommand("help", "显示帮助信息"),
                BotCommand("reset", "重置AI对话历史"),
                BotCommand("projects", "查看所有项目"),
                BotCommand("addtask", "添加任务"),
                BotCommand("listtasks", "查看任务列表"),
                BotCommand("completetask", "完成任务"),
                BotCommand("deletetask", "删除任务"),
                BotCommand("project_info", "查看项目详情"),
            ]
            await self.application.bot.set_my_commands(commands)
            logger.info("Telegram命令菜单已设置完成")

            await self.application.start()

            # 启动轮询
            await self.application.updater.start_polling(drop_pending_updates=True)

            logger.info("Bot 已启动，开始处理消息...")

            # 等待停止事件
            await self._stop_event.wait()

        except Exception as e:
            logger.error(f"Bot 启动失败: {e}")
            raise
        finally:
            await self._cleanup()
            self._stop_event = None

    async def stop(self):
        """停止机器人"""
        logger.info("正在停止 Bot...")
        if self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()

    async def _cleanup(self):
        """清理资源"""
        try:
            if self.dida_client:
                await self.dida_client.close()

            if self.application:
                # 先停止 updater（如果存在）
                if hasattr(self.application, 'updater') and self.application.updater:
                    try:
                        await self.application.updater.stop()
                    except:
                        pass

                # 然后停止和关闭 application
                await self.application.stop()
                await self.application.shutdown()

            logger.info("Bot 资源清理完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

    async def stop(self):
        """停止机器人"""
        logger.info("正在停止 Bot...")
        await self._cleanup()


# 全局 Bot 实例（延迟初始化）
bot_instance = None


async def get_bot() -> DidaBot:
    """获取 Bot 实例"""
    global bot_instance
    if bot_instance is None:
        bot_instance = DidaBot()
    return bot_instance


async def main():
    """主入口函数"""
    bot = await get_bot()  # 获取Bot实例
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止 Bot...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())