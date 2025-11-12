# -*- coding: utf-8 -*-
"""
滴答清单工具定义
用于Kosong AI框架的工具调用
"""

from typing import Optional
from pydantic import BaseModel
from dida_client import DidaClient, Task
from kosong.tooling import CallableTool2, ToolOk, ToolReturnType
from kosong.utils.typing import JsonType


class GetProjectsParams(BaseModel):
    """获取项目列表参数"""
    pass


class GetTasksParams(BaseModel):
    """获取任务列表参数"""
    project_id: Optional[str] = None
    """项目ID，如果不提供则获取所有项目的任务"""


class GetTaskDetailParams(BaseModel):
    """获取任务详情参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""


class CompleteTaskParams(BaseModel):
    """完成任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""


class GetProjectsTool(CallableTool2[GetProjectsParams]):
    """获取所有滴答清单项目"""

    name: str = "get_projects"
    description: str = "获取滴答清单中的所有项目列表，返回项目名称和ID"
    params: type[GetProjectsParams] = GetProjectsParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: GetProjectsParams) -> ToolReturnType:
        try:
            projects = await self.dida_client.get_projects()
            result = []
            for project in projects:
                result.append({
                    "id": project.id,
                    "name": project.name,
                    "closed": project.closed,
                })
            return ToolOk(output=result)
        except Exception as e:
            return ToolOk(output={"error": f"获取项目失败: {str(e)}"})


class GetTasksTool(CallableTool2[GetTasksParams]):
    """获取滴答清单任务"""

    name: str = "get_tasks"
    description: str = "获取滴答清单中的任务，可以指定项目ID获取特定项目的任务，或者不指定获取所有任务"
    params: type[GetTasksParams] = GetTasksParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: GetTasksParams) -> ToolReturnType:
        try:
            tasks = await self.dida_client.get_tasks(params.project_id)
            result = []
            for task in tasks:
                task_info = {
                    "id": task.id,
                    "title": task.title,
                    "project_id": task.project_id,
                    "status": task.status,  # 0:未完成, 2:已完成
                    "priority": task.priority,  # 0:无, 1:低, 3:中, 5:高
                    "is_all_day": task.is_all_day,
                }
                if task.due_date:
                    task_info["due_date"] = task.due_date
                if task.start_date:
                    task_info["start_date"] = task.start_date
                result.append(task_info)
            return ToolOk(output=result)
        except Exception as e:
            return ToolOk(output={"error": f"获取任务失败: {str(e)}"})


class CompleteTaskTool(CallableTool2[CompleteTaskParams]):
    """完成滴答清单任务"""

    name: str = "complete_task"
    description: str = "将滴答清单中的任务标记为已完成，需要提供项目ID和任务ID"
    params: type[CompleteTaskParams] = CompleteTaskParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: CompleteTaskParams) -> ToolReturnType:
        try:
            success = await self.dida_client.complete_task(
                params.project_id, params.task_id
            )
            if success:
                return ToolOk(output={"success": True, "message": "任务已完成"})
            else:
                return ToolOk(output={"success": False, "message": "完成任务失败"})
        except Exception as e:
            return ToolOk(output={"error": f"完成任务失败: {str(e)}"})


class GetTaskDetailTool(CallableTool2[GetTaskDetailParams]):
    """获取任务详细信息"""

    name: str = "get_task_detail"
    description: str = "获取滴答清单中特定任务的完整详细信息，包括任务内容、描述、提醒、子任务等所有字段"
    params: type[GetTaskDetailParams] = GetTaskDetailParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: GetTaskDetailParams) -> ToolReturnType:
        try:
            task = await self.dida_client.get_task(params.project_id, params.task_id)
            return ToolOk(output=task.model_dump())
        except Exception as e:
            return ToolOk(output={"error": f"获取任务详情失败: {str(e)}"})

