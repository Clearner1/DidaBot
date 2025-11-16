# -*- coding: utf-8 -*-
"""
番茄钟工具结果格式化函数
将AI工具调用的结果格式化为用户友好的文本
"""

from typing import Dict, Any


def format_start_task_pomodoro(result: Dict[str, Any]) -> str:
    """格式化启动任务番茄钟结果"""
    if "error" in result:
        return f" 启动任务番茄钟失败: {result['error']}"

    if result.get("success"):
        message = result.get("message", "")
        duration = result.get("duration", 0)
        end_time = result.get("end_time", "")
        task_title = result.get("task_title", "")

        response = f" {message}\n\n"
        response += f" 时长: {duration}分钟\n"

        if end_time and end_time != "未知":
            response += f" 结束时间: {end_time}\n"

        response += f" 任务与番茄钟已完美关联！\n"

        return response

    return " 启动任务番茄钟时发生未知错误"
