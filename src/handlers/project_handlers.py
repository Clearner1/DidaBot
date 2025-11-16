"""
项目命令处理器
处理所有与项目相关的 Telegram Bot 命令
"""

from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from src.dida_client import DidaClient, Project
from utils.formatter import format_project_list, format_error_message


class ProjectHandlers:
    """项目命令处理器"""

    def __init__(self, dida_client: DidaClient):
        self.dida_client = dida_client

    async def cmd_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /projects 命令 - 列出所有项目

        用法：
        /projects    - 列出所有项目
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        try:
            # 获取所有项目
            projects = await self.dida_client.get_projects()

            if not projects:
                await update.message.reply_text(format_error_message("目前没有项目"))
                return

            # 格式化项目列表
            project_list_text = format_project_list(projects)

            # 分页（如果消息太长）
            if len(project_list_text) > 4000:
                # Telegram 消息长度限制为 4096 字符
                chunks = self._split_long_message(project_list_text, 3800)

                # 不使用MarkdownV2，避免转义问题
                await update.message.reply_text(
                    f"项目列表（{len(projects)} 个）：\n"
                    f"第一部分（{len(chunks)} 部分）：\n\n{chunks[0]}"
                )

                # 发送后续部分
                for i, chunk in enumerate(chunks[1:], 2):
                    await update.message.reply_text(
                        f"第 {i} 部分：\n\n{chunk}"
                    )
            else:
                await update.message.reply_text(project_list_text)

        except Exception as e:
            error_msg = f"获取项目失败: {str(e)}"
            await update.message.reply_text(format_error_message(error_msg))

    async def cmd_project_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /project_info 命令 - 显示项目详细信息

        用法：
        /project_info 项目ID

        示例：
        /project_info proj123
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 验证参数
        if not context.args:
            await update.message.reply_text(
                format_error_message("需要提供项目ID\n\n用法: /project_info 项目ID")
            )
            return

        project_id = context.args[0]

        try:
            # 获取项目信息
            project = await self.dida_client.get_project(project_id)

            # 获取项目中的任务数量
            tasks = await self.dida_client.get_tasks(project_id)
            active_tasks = [t for t in tasks if t.status == 0]
            completed_tasks = [t for t in tasks if t.status == 2]

            # 构建项目信息
            lines = []
            lines.append(f"{escape_markdown('FOLDER')} **项目详情**\n")
            lines.append(f"**{escape_markdown('名称')}：** {escape_markdown(project.name)}")
            lines.append(f"**{escape_markdown('ID')}：** `{escape_markdown(project.id)}`")

            # 状态
            status = escape_markdown("CLOSED 已关闭" if project.closed else "OPEN 活跃")
            lines.append(f"**{escape_markdown('状态')}：** {status}")

            # 颜色
            if project.color:
                lines.append(f"**{escape_markdown('颜色')}：** {escape_markdown(project.color)}")

            # 视图模式
            if project.view_mode:
                view_mode_text = {
                    "list": "列表视图",
                    "kanban": "看板视图",
                    "timeline": "时间线视图"
                }.get(project.view_mode, project.view_mode)
                lines.append(f"视图模式：{view_mode_text}")

            # 项目类型
            if project.kind:
                kind_text = {
                    "TASK": "任务清单",
                    "NOTE": "笔记清单"
                }.get(project.kind, project.kind)
                lines.append(f"类型：{kind_text}")

            # 任务统计
            lines.append(f"\n任务统计：")
            lines.append(f"• 活跃任务：{len(active_tasks)} 个")
            lines.append(f"• 已完成任务：{len(completed_tasks)} 个")
            lines.append(f"• 总计：{len(tasks)} 个")

            # 使用提示
            if not project.closed:
                lines.append(f"\n快速操作：")
                lines.append(f"• 添加任务：/addtask {project_id} 标题")
                lines.append(f"• 查看任务：/listtasks {project_id}")

            message = "\n".join(lines)
            await update.message.reply_text(message)

        except Exception as e:
            error_msg = f"获取项目信息失败: {str(e)}"
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