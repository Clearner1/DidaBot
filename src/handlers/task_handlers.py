"""
任务命令处理器
处理所有与任务相关的 Telegram Bot 命令
"""

import re
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from dida_client import DidaClient, Task
from utils.formatter import format_task_list, format_task, format_error_message, format_success_message


class TaskHandlers:
    """任务命令处理器"""

    def __init__(self, dida_client: DidaClient):
        self.dida_client = dida_client

    async def cmd_addtask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /addtask 命令 - 添加任务

        用法：
        /addtask 项目ID 任务标题
        /addtask 项目ID 任务标题 | 任务描述
        /addtask 项目ID 任务标题 | 描述 | 优先级(0/1/3/5)

        示例：
        /addtask proj123 买菜
        /addtask proj123 完成报告 | 需要包含数据分析和结论 | 5
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 解析参数
        if not context.args:
            await update.message.reply_text(
                "缺少参数\n\n"
                "用法：\n"
                "/addtask 项目ID 任务标题\n"
                "/addtask 项目ID 任务标题 | 描述\n"
                "/addtask 项目ID 任务标题 | 描述 | 优先级"
            )
            return

        # 解析命令参数
        args_text = ' '.join(context.args)
        parts = args_text.split('|', 2)

        # 解析项目ID和标题
        first_part = parts[0].strip()
        if ' ' not in first_part:
            await update.message.reply_text("格式错误：需要提供项目ID和标题")
            return

        project_id, title = first_part.split(' ', 1)
        project_id = project_id.strip()
        title = title.strip()

        if not title:
            await update.message.reply_text("标题不能为空")
            return

        # 可选参数
        content = parts[1].strip() if len(parts) > 1 else None

        priority = 0
        if len(parts) > 2:
            try:
                priority = int(parts[2].strip())
                if priority not in [0, 1, 3, 5]:
                    await update.message.reply_text("优先级必须是 0, 1, 3, 或 5")
                    return
            except ValueError:
                await update.message.reply_text("优先级必须是数字")
                return

        try:
            # 创建任务
            new_task = Task(
                title=title,
                project_id=project_id,
                content=content,
                priority=priority
            )

            created = await self.dida_client.create_task(new_task)

            # 获取项目名称用于显示
            try:
                projects = await self.dida_client.get_projects()
                project_map = {p.id: p.name for p in projects}
                project_name = project_map.get(project_id, f"项目 {project_id[:8]}...")
            except:
                project_name = f"项目 {project_id[:8]}..."

            # 格式化回复
            task_info = format_task(created, project_name=project_name)

            await update.message.reply_text(
                f"任务创建成功！\n\n{task_info}"
            )

        except Exception as e:
            error_msg = f"创建任务失败: {str(e)}"
            await update.message.reply_text(format_error_message(error_msg))

    async def cmd_listtasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /listtasks 命令 - 列出任务

        用法：
        /listtasks          - 列出所有任务
        /listtasks 项目ID   - 列出指定项目的任务
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 可选参数
        project_id = None
        if context.args:
            project_id = context.args[0]

        try:
            # 获取任务
            tasks = await self.dida_client.get_tasks(project_id)

            if not tasks:
                msg = "目前没有任务"
                if project_id:
                    msg += f" 在项目 {project_id} 中"
                await update.message.reply_text(msg)
                return

            # 获取项目信息用于显示
            projects = await self.dida_client.get_projects()
            project_map = {p.id: p.name for p in projects}

            # 格式化任务列表
            task_list_text = format_task_list(tasks, project_map)

            # 分页（如果消息太长）
            if len(task_list_text) > 4000:
                # Telegram 消息长度限制为 4096 字符
                chunks = self._split_long_message(task_list_text, 3800)

                await update.message.reply_text(
                    f"任务列表（{len(tasks)} 个）：\n"
                    f"第一部分（{len(chunks)} 部分）：\n\n{chunks[0]}"
                )

                # 发送后续部分
                for i, chunk in enumerate(chunks[1:], 2):
                    await update.message.reply_text(
                        f"第 {i} 部分：\n\n{chunk}"
                    )
            else:
                await update.message.reply_text(
                    f"任务列表（{len(tasks)} 个）：\n\n{task_list_text}"
                )

        except Exception as e:
            error_msg = f"获取任务失败: {str(e)}"
            await update.message.reply_text(format_error_message(error_msg))

    async def cmd_completetask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /completetask 命令 - 完成任务

        用法：
        /completetask 项目ID 任务ID

        示例：
        /completetask proj123 task456
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 验证参数
        if len(context.args) != 2:
            await update.message.reply_text(
                "需要提供项目ID和任务ID\n\n"
                "用法：/completetask 项目ID 任务ID"
            )
            return

        project_id = context.args[0]
        task_id = context.args[1]

        try:
            success = await self.dida_client.complete_task(project_id, task_id)

            if success:
                await update.message.reply_text(format_success_message("任务已完成！"))
            else:
                await update.message.reply_text("完成任务失败")

        except Exception as e:
            error_msg = f"完成任务失败: {str(e)}"
            await update.message.reply_text(format_error_message(error_msg))

    async def cmd_deletetask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /deletetask 命令 - 删除任务

        用法：
        /deletetask 项目ID 任务ID

        示例：
        /deletetask proj123 task456
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 验证参数
        if len(context.args) != 2:
            await update.message.reply_text(
                "需要提供项目ID和任务ID\n\n"
                "用法：/deletetask 项目ID 任务ID"
            )
            return

        project_id = context.args[0]
        task_id = context.args[1]

        try:
            success = await self.dida_client.delete_task(project_id, task_id)

            if success:
                await update.message.reply_text(format_success_message("任务已删除！"))
            else:
                await update.message.reply_text("删除任务失败")

        except Exception as e:
            error_msg = f"删除任务失败: {str(e)}"
            await update.message.reply_text(format_error_message(error_msg))

    # ===== 辅助方法 =====

    async def _check_permission(self, update: Update) -> bool:
        """检查用户权限"""
        from config import get_config
        from utils.formatter import escape_markdown

        config = get_config()
        if update.effective_user.id != config.bot_admin_user_id:
            await update.message.reply_text("你没有权限使用此机器人")
            return False
        return True

    def _split_long_message(self, text: str, max_length: int = 3800) -> list[str]:
        """分割长消息"""
        lines = text.split('\n')
        chunks = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n' + line
                else:
                    current_chunk = line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks