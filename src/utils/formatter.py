"""
消息格式化工具
用于将滴答清单的数据格式化为适合 Telegram 显示的格式
"""

from typing import Dict, List
from dida_client import Task, Project


def format_task(task: Task, project_name: str = "未知项目") -> str:
    """
    格式化单个任务显示（纯文本格式）

    Args:
        task: 任务对象
        project_name: 项目名称（可选）

    Returns:
        格式化后的字符串
    """
    # 优先级文本
    priority_text = {
        0: "无",
        1: "低",
        3: "中",
        5: "高"
    }

    # 状态
    status = "已完成" if task.status == 2 else "未完成"

    # 构建消息
    lines = []
    lines.append(f"任务: {task.title}")
    lines.append(f"任务ID: {task.id}")
    lines.append(f"项目: {project_name}")

    # 优先级
    priority_name = priority_text.get(task.priority, "无")
    lines.append(f"优先级: {priority_name}")

    # 状态
    lines.append(f"状态: {status}")

    # 截止日期
    if task.due_date:
        # 格式化日期显示
        try:
            from datetime import datetime
            if isinstance(task.due_date, str):
                # 尝试解析ISO格式日期
                if 'T' in task.due_date:
                    dt = datetime.fromisoformat(task.due_date.replace('Z', '+00:00'))
                    due_str = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    due_str = task.due_date
                lines.append(f"截止: {due_str}")
        except:
            lines.append(f"截止: {task.due_date}")

    # 描述/内容
    if task.desc:
        lines.append(f"\n描述:\n{task.desc}")
    elif task.content:
        lines.append(f"\n内容:\n{task.content}")

    # 子任务（如果有）
    if task.items:
        lines.append(f"\n子任务 ({len(task.items)}个):")
        for item in task.items[:5]:  # 最多显示5个
            item_status = "已完成" if item.get('status') == 1 else "未完成"
            item_title = item.get('title', '无标题')
            lines.append(f"  {item_status} {item_title}")
        if len(task.items) > 5:
            lines.append(f"  ... 还有 {len(task.items) - 5} 个")

    return "\n".join(lines)


def format_task_list(tasks: List[Task], projects: Dict[str, str]) -> str:
    """
    格式化任务列表（纯文本格式）

    Args:
        tasks: 任务列表
        projects: 项目ID到名称的映射字典

    Returns:
        格式化后的字符串
    """
    if not tasks:
        return "没有任务"

    # 按项目和状态分组
    active_tasks = [t for t in tasks if t.status == 0]
    completed_tasks = [t for t in tasks if t.status == 2]

    lines = []

    # 活跃任务
    if active_tasks:
        lines.append(f"活跃任务 ({len(active_tasks)}个):\n")

        # 按项目分组
        tasks_by_project = {}
        for task in active_tasks:
            project_id = task.project_id or "unknown"
            if project_id not in tasks_by_project:
                tasks_by_project[project_id] = []
            tasks_by_project[project_id].append(task)

        # 显示每个项目的任务
        for project_id, project_tasks in tasks_by_project.items():
            project_name = projects.get(project_id, f"项目 {project_id[:8]}...")
            lines.append(f"项目: {project_name}:")

            # 按优先级排序
            project_tasks.sort(key=lambda t: t.priority, reverse=True)

            for task in project_tasks:
                # 优先级
                priority_text = {5: "高", 3: "中", 1: "低", 0: "无"}
                priority_name = priority_text.get(task.priority, "无")

                # 截止信息
                due_info = ""
                if task.due_date:
                    try:
                        from datetime import datetime
                        if isinstance(task.due_date, str) and 'T' in task.due_date:
                            dt = datetime.fromisoformat(task.due_date.replace('Z', '+00:00'))
                            due_info = f"截止: {dt.strftime('%m-%d')}"
                        else:
                            due_info = f"截止: {str(task.due_date)[:10]}"
                    except:
                        due_info = f"截止: {str(task.due_date)[:10]}"

                # 任务行
                title = truncate_text(task.title, 50)
                task_line = f"  - {priority_name} {title}"
                if due_info:
                    task_line += f" {due_info}"

                lines.append(task_line)
            lines.append("")

    # 已完成任务（简要显示）
    if completed_tasks:
        lines.append(f"已完成 ({len(completed_tasks)}个):\n")

        # 只显示最近完成的5个
        show_completed = completed_tasks[-5:]
        for task in show_completed:
            project_name = projects.get(task.project_id, "未知项目")
            title = truncate_text(task.title, 40)
            lines.append(f"  - {title} ({project_name})")

        if len(completed_tasks) > 5:
            lines.append(f"  ... 还有 {len(completed_tasks) - 5} 个")

    return "\n".join(lines)


def format_project_list(projects: List[Project]) -> str:
    """
    格式化项目列表（纯文本格式）

    Args:
        projects: 项目列表

    Returns:
        格式化后的字符串
    """
    if not projects:
        return "没有项目"

    lines = []
    lines.append(f"项目列表 ({len(projects)}个):\n")

    # 按名称排序
    projects.sort(key=lambda p: p.name)

    for i, project in enumerate(projects, 1):
        status = "CLOSED 已关闭" if project.closed else "OPEN 活跃"
        color = project.color or "COLOR"

        lines.append(f"{i}. {project.name}")
        lines.append(f"  ID: {project.id}")
        lines.append(f"  状态: {status}")

        if project.view_mode:
            view_mode_text = {
                "list": "列表视图",
                "kanban": "看板视图",
                "timeline": "时间线视图"
            }.get(project.view_mode, project.view_mode)
            lines.append(f"  视图: {view_mode_text}")

        lines.append("")

    lines.append("使用 /addtask 项目ID 标题 添加任务")
    lines.append("使用 /listtasks 项目ID 查看项目任务")

    return "\n".join(lines)


def escape_markdown(text: str) -> str:
    """
    转义 Markdown 特殊字符
    适用于 Telegram 的 MarkdownV2 格式
    处理所有用户的输入和动态内容，包括emoji、中文和特殊字符
    """
    if not text:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # 确保文本是Unicode字符串（处理Windows下的编码问题）
    # Telegram MarkdownV2 需要转义的字符
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!', '\\']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    截断长文本并添加省略号

    Args:
        text: 要截断的文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    # 确保不会在单词中间截断
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.8:  # 如果最后一个空格位置合理
        truncated = truncated[:last_space]

    return truncated + "..."


def format_error_message(error: str) -> str:
    """
    格式化错误消息（纯文本格式）

    Args:
        error: 错误信息

    Returns:
        格式化后的错误消息
    """
    return f"[ERROR] {error}"


def format_success_message(message: str) -> str:
    """
    格式化成功消息（纯文本格式）

    Args:
        message: 成功信息

    Returns:
        格式化后的成功消息
    """
    return f"[OK] {message}"


def format_help_message() -> str:
    """
    生成帮助消息（纯文本格式）

    Returns:
        帮助消息文本
    """
    help_text = """
滴答清单 Bot 使用指南

AI 助手（智能对话）：
直接发送自然语言消息，AI会自动理解并执行操作
• "我今天有什么任务？" - 查看今日任务
• "显示所有项目" - 查看项目列表
• "完成滴答AI项目的项目总结" - 完成指定任务

基本命令：
• /start - 启动机器人
• /help - 显示此帮助信息
• /reset - 重置AI对话历史
• /projects - 查看所有项目

任务管理：
• /addtask 项目ID 标题 - 添加任务
• /addtask 项目ID 标题 | 描述 - 添加带描述的任务
• /addtask 项目ID 标题 | 描述 | 优先级 - 添加带优先级的任务 (0/1/3/5)

• /listtasks - 列出所有任务
• /listtasks 项目ID - 列出指定项目的任务

• /completetask 项目ID 任务ID - 完成任务
• /deletetask 项目ID 任务ID - 删除任务

优先级说明：
• 0 - 无优先级
• 1 - 低优先级
• 3 - 中优先级
• 5 - 高优先级

使用示例：
/addtask proj123 买菜
/addtask proj123 完成报告 | 需要包含数据分析 | 5
/listtasks proj123
/completetask proj123 task456

提示：使用 /projects 查看项目ID
""".strip()

    return help_text