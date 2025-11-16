"""任务与番茄钟联动处理器"""

import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from src.services.pomodoro_service import pomodoro_service
from src.dida_client import DidaClient
from src.utils.time_utils import TimeUtils
from src.utils.formatter import format_task


class TaskPomodoroHandlers:
    """任务与番茄钟联动处理器"""

    def __init__(self, dida_client: DidaClient):
        self.dida_client = dida_client

    async def _check_permission(self, update: Update) -> bool:
        """检查用户权限"""
        # 这里可以添加权限检查逻辑
        return True

    async def cmd_task_pomodoro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        为任务启动番茄钟命令

        用法：
        /task_pomodoro 任务ID [时长]
        /task_pomodoro 任务ID 45

        示例：
        /task_pomodoro task_12345 25 - 为任务task_12345启动25分钟番茄钟
        """
        try:
            if not await self._check_permission(update):
                return

            # 解析参数
            if not context.args or len(context.args) < 1:
                await update.message.reply_text(
                    "❌ 缺少参数\n\n"
                    "用法：\n"
                    "/task_pomodoro 任务ID [时长(分钟)]\n\n"
                    "示例：\n"
                    "/task_pomodoro task_12345 25\n"
                    "/task_pomodoro task_abcde"
                )
                return

            task_id = context.args[0]
            duration = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 25

            # 获取认证令牌
            auth_token = os.getenv('DIDA_T_COOKIE')
            csrf_token = os.getenv('DIDA_CSRF_TOKEN')

            if not auth_token or not csrf_token:
                await update.message.reply_text(
                    "❌ 错误：未配置番茄钟认证令牌\n"
                    "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN"
                )
                return

            # 获取任务信息
            try:
                task = await self.dida_client.get_task(task_id)
                if not task:
                    await update.message.reply_text(f"❌ 未找到任务: {task_id}")
                    return

                task_title = task.title
                project_id = task.project_id

            except Exception as e:
                await update.message.reply_text(f"❌ 获取任务信息失败: {str(e)}")
                return

            # 启动番茄钟，关联到具体任务
            result = await pomodoro_service.start_focus(
                auth_token, csrf_token,
                duration=duration,
                note=f"任务: {task_title}",
                focus_on_id=task_id,
                focus_on_title=task_title,
                focus_on_type=0  # 0表示任务类型
            )

            if "error" in result:
                await update.message.reply_text(
                    f"❌ 启动番茄钟失败: {result['error']}"
                )
                return

            current = result.get("current", {})

            # 计算结束时间
            end_time_str = "未知"
            try:
                end_time = current.get('endTime', '')
                if end_time:
                    end_time_local = TimeUtils.utc_to_local_str(end_time, "%H:%M")
                    end_time_str = end_time_local
            except:
                pass

            # 构建成功消息
            message = (
                f"🍅 任务番茄钟已启动！\n\n"
                f"📝 任务: {task_title}\n"
                f"🆔 任务ID: {task_id}\n"
                f"⏰ 时长: {duration}分钟\n"
                f"📍 结束时间: {end_time_str}\n\n"
                f"💡 番茄钟与任务已关联\n"
                f"💡 使用 /task_pomodoro_status 查看状态"
            )

            await update.message.reply_text(message)

        except Exception as e:
            await update.message.reply_text(f"❌ 启动任务番茄钟时发生错误: {str(e)}")

    async def cmd_task_pomodoro_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看当前番茄钟状态（包含关联任务信息）"""
        try:
            if not await self._check_permission(update):
                return

            auth_token = os.getenv('DIDA_T_COOKIE')
            csrf_token = os.getenv('DIDA_CSRF_TOKEN')

            if not auth_token or not csrf_token:
                await update.message.reply_text("❌ 未配置番茄钟认证令牌")
                return

            # 查询番茄钟状态
            result = await pomodoro_service.query_focus_state(auth_token, csrf_token)

            if "error" in result:
                await update.message.reply_text(
                    f"❌ 查询状态失败: {result['error']}"
                )
                return

            current = result.get("current")
            if not current:
                await update.message.reply_text(
                    "📊 当前无活跃番茄钟\n\n"
                    "使用 /task_pomodoro 任务ID 启动任务番茄钟"
                )
                return

            # 状态映射
            status_map = {
                0: "🟢 运行中",
                1: "🟡 暂停中",
                2: "✅ 已完成",
                3: "⏹️ 已停止"
            }

            status_text = status_map.get(current.get('status'), "❓ 未知状态")

            # 获取关联任务信息
            task_id = current.get('focusOnLogs', [{}])[0].get('id', '')
            task_title = "未指定"

            if task_id:
                try:
                    # 尝试从滴答清单获取任务详情
                    task = await self.dida_client.get_task(task_id)
                    if task:
                        task_title = task.title
                        project_id = task.project_id
                    else:
                        task_title = f"任务ID: {task_id} (未找到详情)"
                except:
                    task_title = f"任务ID: {task_id} (获取失败)"
            else:
                # 从focusTasks获取标题
                focus_tasks = current.get('focusTasks', [])
                if focus_tasks:
                    task_title = focus_tasks[0].get('title', '未指定')

            # 计算剩余时间
            time_info = f"时长: {current.get('duration', 0)}分钟"
            try:
                start_time = current.get('startTime', '')
                end_time = current.get('endTime', '')
                if start_time and current.get('status') == 0:  # 运行中
                    start_dt = TimeUtils.parse_dida_datetime(start_time)
                    end_dt = TimeUtils.parse_dida_datetime(end_time)
                    now = datetime.now(start_dt.tzinfo)

                    if now < end_dt:
                        remaining = (end_dt - now).total_seconds() / 60
                        time_info = f"剩余: {int(remaining)}分钟"
                    else:
                        time_info = "应该已结束"
            except:
                pass

            # 构建回复消息
            message = (
                f"🍅 任务番茄钟状态\n\n"
                f"{status_text}\n"
                f"📝 任务: {task_title}\n"
                f"🆔 任务ID: {task_id or '无'}\n"
                f"⏰ {time_info}\n"
                f"🍅 番茄钟ID: {current.get('id', 'N/A')[:12]}..."
            )

            await update.message.reply_text(message)

        except Exception as e:
            await update.message.reply_text(f"❌ 查询任务番茄钟状态时发生错误: {str(e)}")

    async def cmd_create_task_pomodoro(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        创建任务并立即启动番茄钟

        用法：
        /create_task_pomodoro 项目ID 任务标题 [时长]
        /create_task_pomodoro proj123 写论文 45

        示例：
        /create_task_pomodoro proj123 完成报告 - 创建任务并启动25分钟番茄钟
        /create_task_pomodoro proj456 编程学习 60 - 创建任务并启动60分钟番茄钟
        """
        try:
            if not await self._check_permission(update):
                return

            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "❌ 缺少参数\n\n"
                    "用法：\n"
                    "/create_task_pomodoro 项目ID 任务标题 [时长(分钟)]\n\n"
                    "示例：\n"
                    "/create_task_pomodoro proj123 完成报告\n"
                    "/create_task_pomodoro proj456 编程学习 45"
                )
                return

            project_id = context.args[0]
            task_title = " ".join(context.args[1:-1]) if len(context.args) > 2 else " ".join(context.args[1:])
            duration = int(context.args[-1]) if len(context.args) > 2 and context.args[-1].isdigit() else 25

            # 创建任务
            try:
                task = await self.dida_client.create_task(
                    project_id=project_id,
                    title=task_title
                )

                if not task:
                    await update.message.reply_text("❌ 创建任务失败")
                    return

                task_id = task.id
                await update.message.reply_text(
                    f"✅ 任务创建成功\n"
                    f"📝 任务: {task_title}\n"
                    f"🆔 任务ID: {task_id}\n"
                    f"🔄 正在启动番茄钟..."
                )

            except Exception as e:
                await update.message.reply_text(f"❌ 创建任务失败: {str(e)}")
                return

            # 短暂延迟后启动番茄钟
            await asyncio.sleep(1)

            # 启动番茄钟
            await self._start_pomodoro_for_task(update, task_id, task_title, duration)

        except Exception as e:
            await update.message.reply_text(f"❌ 创建任务并启动番茄钟时发生错误: {str(e)}")

    async def _start_pomodoro_for_task(self, update: Update, task_id: str, task_title: str, duration: int):
        """为指定任务启动番茄钟的辅助方法"""
        try:
            auth_token = os.getenv('DIDA_T_COOKIE')
            csrf_token = os.getenv('DIDA_CSRF_TOKEN')

            if not auth_token or not csrf_token:
                await update.message.reply_text("❌ 未配置番茄钟认证令牌")
                return

            # 启动番茄钟
            result = await pomodoro_service.start_focus(
                auth_token, csrf_token,
                duration=duration,
                note=f"任务: {task_title}",
                focus_on_id=task_id,
                focus_on_title=task_title,
                focus_on_type=0
            )

            if "error" in result:
                await update.message.reply_text(
                    f"❌ 启动番茄钟失败: {result['error']}"
                )
                return

            current = result.get("current", {})

            # 计算结束时间
            end_time_str = "未知"
            try:
                end_time = current.get('endTime', '')
                if end_time:
                    end_time_local = TimeUtils.utc_to_local_str(end_time, "%H:%M")
                    end_time_str = end_time_local
            except:
                pass

            message = (
                f"🍅 任务番茄钟启动成功！\n\n"
                f"📝 任务: {task_title}\n"
                f"⏰ 时长: {duration}分钟\n"
                f"📍 结束时间: {end_time_str}\n"
                f"💡 任务与番茄钟已完美关联！"
            )

            await update.message.reply_text(message)

        except Exception as e:
            await update.message.reply_text(f"❌ 启动番茄钟时发生错误: {str(e)}")