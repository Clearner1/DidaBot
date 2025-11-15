# -*- coding: utf-8 -*-
"""
工具结果格式化函数
将工具返回的数据格式化为用户友好的文本
"""

import json
from typing import Any, Dict, List
from utils.time_utils import TimeUtils


async def format_get_projects(projects: List[Dict[str, Any]]) -> str:
    """格式化获取项目列表的结果"""
    if not projects:
        return "没有找到项目"

    response_parts = ["项目列表:"]
    for project in projects:
        status = "已关闭" if project.get("closed") else "活跃"
        response_parts.append(f"  • {project.get('name')} (ID: {project.get('id')[:8]}..., {status})")

    return "\n".join(response_parts)


async def format_get_tasks(tasks: List[Dict[str, Any]], dida_client=None) -> str:
    """格式化获取任务列表的结果"""
    if not tasks:
        return "没有找到任务"

    # 筛选今日任务
    today_tasks = [task for task in tasks if TimeUtils.is_today_task(task)]

    if not today_tasks:
        return "今天没有任务 ✨"

    response_parts = ["今日任务:"]

    # 按项目分组
    tasks_by_project = {}
    for task in today_tasks:
        project_id = task.get("project_id", "unknown")
        if project_id not in tasks_by_project:
            tasks_by_project[project_id] = []
        tasks_by_project[project_id].append(task)

    # 获取项目信息用于显示名称（直接使用 await）
    project_map = {}
    if dida_client:
        try:
            projects = await dida_client.get_projects()
            project_map = {p.id: p.name for p in projects}
        except Exception as e:
            # 获取失败，使用默认的项目ID显示
            pass

    # 显示任务
    for project_id, project_tasks in tasks_by_project.items():
        project_name = project_map.get(project_id, f"项目 {project_id[:8]}...")
        response_parts.append(f"\n项目: {project_name}")

        for task in project_tasks:
            status = "已完成" if task.get("status") == 2 else "进行中"
            title = task.get("title", "无标题")
            response_parts.append(f"  • {title} ({status})")

    return "\n".join(response_parts)


async def format_get_task_detail(task_detail: Dict[str, Any]) -> str:
    """格式化获取任务详情的结果"""
    if "error" in task_detail:
        return f"获取任务详情失败: {task_detail['error']}"

    title = task_detail.get('title', '无标题')
    content = task_detail.get('content', '')
    desc = task_detail.get('desc', '')

    response_parts = ["任务详情:"]

    # 基本信息
    response_parts.append(f"  标题: {title}")
    response_parts.append(f"  任务ID: {task_detail.get('id', 'N/A')}")
    response_parts.append(f"  项目ID: {task_detail.get('project_id', 'N/A')}")

    # 内容信息
    if content:
        response_parts.append(f"  内容: {content}")
    if desc:
        response_parts.append(f"  描述: {desc}")

    # 时间信息
    start_date = task_detail.get('start_date')
    if start_date:
        local_start_date = TimeUtils.format_due_date(start_date, style='chinese')
        response_parts.append(f"  开始: {local_start_date}")

    due_date = task_detail.get('due_date')
    if due_date:
        local_due_date = TimeUtils.format_due_date(due_date, style='chinese')
        response_parts.append(f"  截止: {local_due_date}")

    completed_time = task_detail.get('completed_time')
    if completed_time:
        local_completed_time = TimeUtils.format_due_date(completed_time, style='chinese')
        response_parts.append(f"  完成时间: {local_completed_time}")

    # 状态信息
    priority = task_detail.get('priority', 0)
    priority_names = {0: "无", 1: "低", 3: "中", 5: "高"}
    priority_str = priority_names.get(priority, str(priority))
    response_parts.append(f"  优先级: {priority_str}")

    status = task_detail.get('status', 0)
    status_names = {0: "进行中", 1: "已放弃", 2: "已完成"}
    status_str = status_names.get(status, str(status))
    response_parts.append(f"  状态: {status_str}")

    response_parts.append(f"  全天事件: {'是' if task_detail.get('is_all_day') else '否'}")

    sort_order = task_detail.get('sort_order')
    if sort_order is not None:
        response_parts.append(f"  排序: {sort_order}")

    # 时区
    time_zone = task_detail.get('time_zone')
    if time_zone:
        response_parts.append(f"  时区: {time_zone}")

    # 重复规则
    repeat_flag = task_detail.get('repeat_flag')
    if repeat_flag:
        response_parts.append(f"  重复规则: {repeat_flag}")

    # 提醒
    reminders = task_detail.get('reminders', [])
    if reminders:
        response_parts.append(f"  提醒: {reminders}")

    # 子任务
    items = task_detail.get('items', [])
    if items:
        response_parts.append(f"  子任务: {len(items)}个")
        for item in items:
            item_title = item.get('title', '无标题')
            item_status = item.get('status', 0)
            item_status_str = '已完成' if item_status == 1 else '未完成'
            response_parts.append(f"    - {item_title} ({item_status_str})")

    return "\n".join(response_parts)


async def format_complete_task(result: Dict[str, Any]) -> str:
    """格式化完成任务的结果"""
    if result.get("success"):
        return "任务已完成！✅"
    else:
        return f"完成任务失败: {result.get('message', '未知错误')}"


async def format_delete_task(result: Dict[str, Any]) -> str:
    """格式化删除任务的结果"""
    if result.get("success"):
        task_title = result.get('task_title', '任务')
        return f"🗑️ 任务'{task_title}'已永久删除\n⚠️ 此操作不可恢复"
    else:
        return f"删除任务失败: {result.get('error', '未知错误')}"


async def format_update_task(result: Dict[str, Any]) -> str:
    """格式化更新任务的结果"""
    if not result.get("success"):
        return f"更新任务失败: {result.get('error', '未知错误')}"

    title = result.get('title', '任务')
    updated_fields = result.get('updated_fields', '')

    response_parts = [f"✅ 任务'{title}'已更新", f"更新的字段: {updated_fields}"]

    # 显示更新后的信息
    priority = result.get('priority', 0)
    priority_names = {0: "⚪ 无", 1: "🔵 低", 3: "🟡 中", 5: "🔴 高"}
    priority_str = priority_names.get(priority, str(priority))

    due_date = result.get('due_date')
    status = result.get('status', 0)
    status_str = "✅ 已完成" if status == 2 else "⏳ 进行中"

    response_parts.extend([
        "\n任务当前状态:",
        f"  • 标题: {title}",
        f"  • 状态: {status_str}",
        f"  • 优先级: {priority_str}"
    ])

    if due_date:
        response_parts.append(f"  • 截止时间: {due_date}")

    return "\n".join(response_parts)


async def format_create_task(result: Dict[str, Any]) -> str:
    """格式化创建任务的结果"""
    if not result.get("success"):
        return f"创建任务失败: {result.get('error', '未知错误')}"

    title = result.get('title', '任务')
    priority = result.get('priority', 0)
    priority_names = {0: "⚪ 无", 1: "🔵 低", 3: "🟡 中", 5: "🔴 高"}
    priority_str = priority_names.get(priority, str(priority))

    due_date = result.get('due_date')

    response_parts = [
        f"✅ 任务'{title}'已创建",
        "\n任务信息:",
        f"  • 标题: {title}",
        f"  • 优先级: {priority_str}"
    ]

    if due_date:
        response_parts.append(f"  • 截止时间: {due_date}")

    return "\n".join(response_parts)


async def format_current_time(time_info: Dict[str, Any]) -> str:
    """格式化获取当前时间的结果"""
    # 对于get_current_time，AI会自己处理时间计算，不向用户显示
    return None


async def format_error(error_dict: Dict[str, Any]) -> str:
    """格式化错误信息"""
    if "error" in error_dict:
        return f"执行失败: {error_dict['error']}"
    return None

