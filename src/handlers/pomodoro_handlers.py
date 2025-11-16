"""番茄钟命令处理器"""

import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from src.services.pomodoro_service import pomodoro_service
from src.utils.time_utils import TimeUtils


async def handle_pomodoro_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_status 命令 - 查看当前番茄钟状态"""
    try:
        # 获取认证令牌
        auth_token = os.getenv('DIDA_T_COOKIE')
        csrf_token = os.getenv('DIDA_CSRF_TOKEN')

        if not auth_token or not csrf_token:
            await update.message.reply_text(
                "❌ 错误：未配置番茄钟认证令牌\n"
                "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN\n"
                "这些令牌需要从滴答清单网页版获取"
            )
            return

        # 验证令牌格式
        if not pomodoro_service._validate_tokens(auth_token, csrf_token):
            await update.message.reply_text(
                "❌ 错误：番茄钟认证令牌格式不正确\n"
                "请检查 .env 文件中的令牌是否完整"
            )
            return

        # 查询当前番茄钟状态
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
                "使用 /pomodoro_start 启动新的番茄钟"
            )
            return

        # 格式化状态信息
        status_map = {
            0: "🟢 运行中",
            1: "🟡 暂停中",
            2: "✅ 已完成",
            3: "⏹️ 已停止"
        }

        status_text = status_map.get(current.get('status'), "❓ 未知状态")

        # 计算剩余时间
        start_time = current.get('startTime', '')
        end_time = current.get('endTime', '')
        duration = current.get('duration', 0)

        time_info = f"时长: {duration}分钟"
        if start_time and current.get('status') == 0:  # 运行中
            try:
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

        # 获取关联任务信息
        task_title = "未指定"
        focus_tasks = current.get('focusTasks', [])
        if focus_tasks:
            task_title = focus_tasks[0].get('title', '未指定')

        # 构建回复消息
        message = (
            f"🍅 番茄钟状态\n\n"
            f"{status_text}\n"
            f"📝 任务: {task_title}\n"
            f"⏰ {time_info}\n"
            f"🆔 ID: {current.get('id', 'N/A')[:12]}..."
        )

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ 查询番茄钟状态时发生错误: {str(e)}")


async def handle_pomodoro_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_start 命令 - 启动番茄钟"""
    try:
        # 获取认证令牌
        auth_token = os.getenv('DIDA_T_COOKIE')
        csrf_token = os.getenv('DIDA_CSRF_TOKEN')

        if not auth_token or not csrf_token:
            await update.message.reply_text(
                "❌ 错误：未配置番茄钟认证令牌\n"
                "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN\n"
                "这些令牌需要从滴答清单网页版获取"
            )
            return

        # 验证令牌格式
        if not pomodoro_service._validate_tokens(auth_token, csrf_token):
            await update.message.reply_text(
                "❌ 错误：番茄钟认证令牌格式不正确\n"
                "请检查 .env 文件中的令牌是否完整"
            )
            return

        # 解析命令参数
        args = context.args

        # 默认参数
        duration = 25  # 默认25分钟
        note = "DidaBot番茄钟"
        task_title = ""

        # 解析时长
        if args and args[0].isdigit():
            duration = int(args[0])
            if duration <= 0 or duration > 120:  # 限制在1-120分钟
                duration = 25
            args = args[1:]  # 移除时长参数

        # 解析任务标题（剩余参数）
        if args:
            task_title = " ".join(args)
            note = f"任务: {task_title}"

        # 启动番茄钟
        result = await pomodoro_service.start_focus(
            auth_token, csrf_token,
            duration=duration,
            note=note,
            focus_on_title=task_title
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
            f"🍅 番茄钟已启动！\n\n"
            f"⏰ 时长: {duration}分钟\n"
            f"📍 结束时间: {end_time_str}\n"
        )

        if task_title:
            message += f"📝 任务: {task_title}\n"

        message += f"\n💡 使用 /pomodoro_pause 暂停\n"
        message += f"💡 使用 /pomodoro_stop 停止"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ 启动番茄钟时发生错误: {str(e)}")


async def handle_pomodoro_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_pause 命令 - 暂停番茄钟"""
    try:
        auth_token = os.getenv('DIDA_T_COOKIE')
        csrf_token = os.getenv('DIDA_CSRF_TOKEN')

        if not auth_token or not csrf_token:
            await update.message.reply_text(
                "❌ 错误：未配置番茄钟认证令牌\n"
                "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN"
            )
            return

        # 验证令牌格式
        if not pomodoro_service._validate_tokens(auth_token, csrf_token):
            await update.message.reply_text(
                "❌ 错误：番茄钟认证令牌格式不正确\n"
                "请检查 .env 文件中的令牌是否完整"
            )
            return

        # 暂停番茄钟
        result = await pomodoro_service.pause_focus(
            auth_token, csrf_token,
            note="用户手动暂停"
        )

        if "error" in result:
            await update.message.reply_text(
                f"❌ 暂停番茄钟失败: {result['error']}\n\n"
                "可能原因：当前没有运行的番茄钟"
            )
            return

        current = result.get("current", {})
        task_title = "未指定"
        focus_tasks = current.get('focusTasks', [])
        if focus_tasks:
            task_title = focus_tasks[0].get('title', '未指定')

        message = (
            f"⏸️ 番茄钟已暂停\n\n"
            f"📝 任务: {task_title}\n"
            f"💡 使用 /pomodoro_continue 继续"
        )

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ 暂停番茄钟时发生错误: {str(e)}")


async def handle_pomodoro_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_continue 命令 - 继续番茄钟"""
    try:
        auth_token = os.getenv('DIDA_T_COOKIE')
        csrf_token = os.getenv('DIDA_CSRF_TOKEN')

        if not auth_token or not csrf_token:
            await update.message.reply_text(
                "❌ 错误：未配置番茄钟认证令牌\n"
                "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN"
            )
            return

        # 验证令牌格式
        if not pomodoro_service._validate_tokens(auth_token, csrf_token):
            await update.message.reply_text(
                "❌ 错误：番茄钟认证令牌格式不正确\n"
                "请检查 .env 文件中的令牌是否完整"
            )
            return

        # 继续番茄钟
        result = await pomodoro_service.continue_focus(
            auth_token, csrf_token,
            note="用户手动继续"
        )

        if "error" in result:
            await update.message.reply_text(
                f"❌ 继续番茄钟失败: {result['error']}\n\n"
                "可能原因：当前没有可继续的番茄钟"
            )
            return

        current = result.get("current", {})
        task_title = "未指定"
        focus_tasks = current.get('focusTasks', [])
        if focus_tasks:
            task_title = focus_tasks[0].get('title', '未指定')

        message = (
            f"▶️ 番茄钟已继续\n\n"
            f"📝 任务: {task_title}\n"
            f"💡 使用 /pomodoro_pause 再次暂停"
        )

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ 继续番茄钟时发生错误: {str(e)}")


async def handle_pomodoro_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_finish 命令 - 完成番茄钟"""
    try:
        auth_token = os.getenv('DIDA_T_COOKIE')
        csrf_token = os.getenv('DIDA_CSRF_TOKEN')

        if not auth_token or not csrf_token:
            await update.message.reply_text(
                "❌ 错误：未配置番茄钟认证令牌\n"
                "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN"
            )
            return

        # 验证令牌格式
        if not pomodoro_service._validate_tokens(auth_token, csrf_token):
            await update.message.reply_text(
                "❌ 错误：番茄钟认证令牌格式不正确\n"
                "请检查 .env 文件中的令牌是否完整"
            )
            return

        # 完成番茄钟
        result = await pomodoro_service.finish_focus(
            auth_token, csrf_token,
            note="用户手动完成"
        )

        if "error" in result:
            await update.message.reply_text(
                f"❌ 完成番茄钟失败: {result['error']}\n\n"
                "可能原因：当前没有运行的番茄钟"
            )
            return

        current = result.get("current", {})
        task_title = "未指定"
        focus_tasks = current.get('focusTasks', [])
        if focus_tasks:
            task_title = focus_tasks[0].get('title', '未指定')

        # 计算实际专注时长
        duration_info = "未知"
        try:
            start_time = current.get('startTime', '')
            end_time = current.get('endTime', '')
            if start_time and end_time:
                start_dt = TimeUtils.parse_dida_datetime(start_time)
                end_dt = TimeUtils.parse_dida_datetime(end_time)
                focus_minutes = int((end_dt - start_dt).total_seconds() / 60)
                duration_info = f"{focus_minutes}分钟"
        except:
            pass

        message = (
            f"🎉 番茄钟已完成！\n\n"
            f"📝 任务: {task_title}\n"
            f"⏰ 专注时长: {duration_info}\n"
            f"🏆 干得不错！"
        )

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ 完成番茄钟时发生错误: {str(e)}")


async def handle_pomodoro_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_stop 命令 - 停止番茄钟"""
    try:
        auth_token = os.getenv('DIDA_T_COOKIE')
        csrf_token = os.getenv('DIDA_CSRF_TOKEN')

        if not auth_token or not csrf_token:
            await update.message.reply_text(
                "❌ 错误：未配置番茄钟认证令牌\n"
                "请确保 .env 文件中包含 DIDA_T_COOKIE 和 DIDA_CSRF_TOKEN"
            )
            return

        # 验证令牌格式
        if not pomodoro_service._validate_tokens(auth_token, csrf_token):
            await update.message.reply_text(
                "❌ 错误：番茄钟认证令牌格式不正确\n"
                "请检查 .env 文件中的令牌是否完整"
            )
            return

        # 停止番茄钟
        result = await pomodoro_service.stop_focus(
            auth_token, csrf_token,
            note="用户手动停止",
            include_exit=True
        )

        if "error" in result:
            await update.message.reply_text(
                f"❌ 停止番茄钟失败: {result['error']}\n\n"
                "可能原因：当前没有运行的番茄钟"
            )
            return

        current = result.get("current", {})
        task_title = "未指定"
        focus_tasks = current.get('focusTasks', [])
        if focus_tasks:
            task_title = focus_tasks[0].get('title', '未指定')

        message = (
            f"⏹️ 番茄钟已停止\n\n"
            f"📝 任务: {task_title}\n"
            f"💡 可以随时启动新的番茄钟"
        )

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"❌ 停止番茄钟时发生错误: {str(e)}")


async def handle_pomodoro_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /pomodoro_help 命令 - 番茄钟帮助信息"""
    help_text = (
        "🍅 番茄钟命令帮助\n\n"
        "基本命令：\n"
        "/pomodoro_status - 查看当前番茄钟状态\n"
        "/pomodoro_start [时长] [任务标题] - 启动番茄钟\n"
        "/pomodoro_pause - 暂停番茄钟\n"
        "/pomodoro_continue - 继续番茄钟\n"
        "/pomodoro_finish - 完成番茄钟\n"
        "/pomodoro_stop - 停止番茄钟\n"
        "/pomodoro_help - 显示此帮助\n\n"
        "使用示例：\n"
        "/pomodoro_start - 启动25分钟番茄钟\n"
        "/pomodoro_start 45 写论文 - 启动45分钟专注写论文\n"
        "/pomodoro_start 15 - 启动15分钟短暂专注\n\n"
        "💡 提示：番茄钟与滴答清单任务自动关联"
    )

    await update.message.reply_text(help_text)