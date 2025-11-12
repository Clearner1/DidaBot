# -*- coding: utf-8 -*-
"""
滴答清单 API 客户端
基于官方 OpenAPI 文档：https://api.dida365.com
"""

import httpx
from typing import List, Optional
from pydantic import BaseModel


class Task(BaseModel):
    """任务模型 - 对应滴答清单API任务对象"""

    id: Optional[str] = None
    project_id: Optional[str] = None
    title: str
    content: Optional[str] = None
    desc: Optional[str] = None
    is_all_day: bool = False
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    time_zone: Optional[str] = None
    priority: int = 0  # 0:无, 1:低, 3:中, 5:高
    status: int = 0    # 0:未完成, 2:已完成
    sort_order: Optional[int] = None
    completed_time: Optional[str] = None
    reminders: List[str] = []
    repeat_flag: Optional[str] = None
    items: List[dict] = []

    class Config:
        """字段别名配置 - 处理API返回的驼峰命名"""
        alias_generator = lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        )
        populate_by_name = True


class Project(BaseModel):
    """项目模型 - 对应滴答清单API项目对象"""

    id: Optional[str] = None
    name: str
    color: Optional[str] = None
    closed: bool = False
    group_id: Optional[str] = None
    sort_order: Optional[int] = None
    view_mode: Optional[str] = None  # "list", "kanban", "timeline"
    kind: Optional[str] = None       # "TASK", "NOTE"

    class Config:
        """字段别名配置 - 处理API返回的驼峰命名"""
        alias_generator = lambda field_name: ''.join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split('_'))
        )
        populate_by_name = True


class DidaClient:
    """滴答清单API客户端"""

    def __init__(self, access_token: str, base_url: str = "https://api.dida365.com"):
        """
        初始化客户端

        Args:
            access_token: 访问令牌
            base_url: API基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0
        )

    # ===== 项目操作 =====

    async def get_projects(self) -> List[Project]:
        """
        获取所有项目

        Returns:
            项目列表
        """
        try:
            response = await self.client.get("/open/v1/project")
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: {type(data)}")

            return [Project(**project_data) for project_data in data]

        except httpx.HTTPStatusError as e:
            raise Exception(f"获取项目列表失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"获取项目列表失败: {str(e)}")

    async def get_project(self, project_id: str) -> Project:
        """
        获取单个项目

        Args:
            project_id: 项目ID

        Returns:
            项目对象
        """
        try:
            response = await self.client.get(f"/open/v1/project/{project_id}")
            response.raise_for_status()

            data = response.json()
            return Project(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"项目 {project_id} 不存在")
            raise Exception(f"获取项目详情失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"获取项目详情失败: {str(e)}")

    # ===== 任务操作 =====

    async def get_tasks(self, project_id: Optional[str] = None) -> List[Task]:
        """
        获取任务列表

        Args:
            project_id: 可选项目ID，如果不指定则获取所有项目的任务

        Returns:
            任务列表
        """
        try:
            if project_id:
                # 获取指定项目的任务
                response = await self.client.get(f"/open/v1/project/{project_id}/data")
                response.raise_for_status()

                data = response.json()
                tasks_data = data.get("tasks", [])

                # 为每个任务添加project_id
                tasks = []
                for task_data in tasks_data:
                    task_data["project_id"] = project_id
                    tasks.append(Task(**task_data))

                return tasks
            else:
                # 获取所有任务 - 遍历所有项目获取任务
                projects = await self.get_projects()
                all_tasks = []

                for project in projects:
                    project_tasks = await self.get_tasks(project.id)
                    all_tasks.extend(project_tasks)

                return all_tasks

        except httpx.HTTPStatusError as e:
            raise Exception(f"获取任务列表失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"获取任务列表失败: {str(e)}")

    async def get_task(self, project_id: str, task_id: str) -> Task:
        """
        获取单个任务

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            任务对象
        """
        try:
            response = await self.client.get(f"/open/v1/project/{project_id}/task/{task_id}")
            response.raise_for_status()

            data = response.json()
            data["project_id"] = project_id  # 确保project_id字段存在
            return Task(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"任务 {task_id} 在项目 {project_id} 中不存在")
            raise Exception(f"获取任务详情失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"获取任务详情失败: {str(e)}")

    async def create_task(self, task: Task) -> Task:
        """
        创建任务

        Args:
            task: 任务对象，必须包含 title 和 project_id

        Returns:
            创建后的任务对象，包含服务器生成的 id
        """
        if not task.title:
            raise ValueError("任务标题不能为空")
        if not task.project_id:
            raise ValueError("项目ID不能为空")

        try:
            # 准备请求数据，按照API文档格式
            task_data = {
                "title": task.title,
                "projectId": task.project_id,
            }

            # 添加可选字段
            if task.content:
                task_data["content"] = task.content
            if task.desc:
                task_data["desc"] = task.desc
            if task.is_all_day is not None:
                task_data["isAllDay"] = task.is_all_day
            if task.start_date:
                task_data["startDate"] = task.start_date
            if task.due_date:
                task_data["dueDate"] = task.due_date
            if task.priority:
                task_data["priority"] = task.priority
            if task.reminders:
                task_data["reminders"] = task.reminders
            if task.repeat_flag:
                task_data["repeatFlag"] = task.repeat_flag
            if task.sort_order is not None:
                task_data["sortOrder"] = task.sort_order
            if task.time_zone:
                task_data["timeZone"] = task.time_zone
            if task.items:
                task_data["items"] = task.items

            response = await self.client.post("/open/v1/task", json=task_data)
            response.raise_for_status()

            created_data = response.json()
            created_data["project_id"] = task.project_id  # 确保project_id字段存在
            return Task(**created_data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise Exception(f"创建任务失败: 请求数据格式错误 - {e.response.text}")
            elif e.response.status_code == 403:
                raise Exception(f"创建任务失败: 没有权限在项目 {task.project_id} 中创建任务")
            elif e.response.status_code == 404:
                raise Exception(f"创建任务失败: 项目 {task.project_id} 不存在")
            raise Exception(f"创建任务失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"创建任务失败: {str(e)}")

    async def update_task(self, task: Task) -> Task:
        """
        更新任务

        Args:
            task: 任务对象，必须包含 id 和 project_id

        Returns:
            更新后的任务对象
        """
        if not task.id:
            raise ValueError("任务ID不能为空")
        if not task.project_id:
            raise ValueError("项目ID不能为空")

        try:
            # 准备请求数据，按照API文档格式
            task_data = {
                "id": task.id,
                "projectId": task.project_id,
                "title": task.title,
            }

            # 添加可选字段
            if task.content:
                task_data["content"] = task.content
            if task.desc:
                task_data["desc"] = task.desc
            if task.is_all_day is not None:
                task_data["isAllDay"] = task.is_all_day
            if task.start_date:
                task_data["startDate"] = task.start_date
            if task.due_date:
                task_data["dueDate"] = task.due_date
            if task.priority:
                task_data["priority"] = task.priority
            if task.status:
                task_data["status"] = task.status
            if task.reminders:
                task_data["reminders"] = task.reminders
            if task.repeat_flag:
                task_data["repeatFlag"] = task.repeat_flag
            if task.sort_order is not None:
                task_data["sortOrder"] = task.sort_order
            if task.time_zone:
                task_data["timeZone"] = task.time_zone
            if task.items:
                task_data["items"] = task.items

            response = await self.client.post(f"/open/v1/task/{task.id}", json=task_data)
            response.raise_for_status()

            updated_data = response.json()
            updated_data["project_id"] = task.project_id  # 确保project_id字段存在
            return Task(**updated_data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise Exception(f"更新任务失败: 请求数据格式错误 - {e.response.text}")
            elif e.response.status_code == 403:
                raise Exception(f"更新任务失败: 没有权限更新任务 {task.id}")
            elif e.response.status_code == 404:
                raise Exception(f"更新任务失败: 任务 {task.id} 不存在")
            raise Exception(f"更新任务失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"更新任务失败: {str(e)}")

    async def complete_task(self, project_id: str, task_id: str) -> bool:
        """
        标记任务为完成

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            True 如果成功
        """
        try:
            response = await self.client.post(f"/open/v1/project/{project_id}/task/{task_id}/complete")
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"完成任务失败: 任务 {task_id} 在项目 {project_id} 中不存在")
            elif e.response.status_code == 401:
                raise Exception(f"完成任务失败: 未授权访问")
            raise Exception(f"完成任务失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"完成任务失败: {str(e)}")

    async def delete_task(self, project_id: str, task_id: str) -> bool:
        """
        删除任务

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            True 如果成功删除
        """
        try:
            response = await self.client.delete(f"/open/v1/project/{project_id}/task/{task_id}")
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception(f"删除任务失败: 任务 {task_id} 在项目 {project_id} 中不存在")
            elif e.response.status_code == 403:
                raise Exception(f"删除任务失败: 没有权限删除任务 {task_id}")
            raise Exception(f"删除任务失败: HTTP {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"删除任务失败: {str(e)}")

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()