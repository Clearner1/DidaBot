# 实用示例集 (Examples)

## 概述

本文档提供滴答清单 API 的实用示例，涵盖常见使用场景和最佳实践。每个示例都包含完整的代码实现，可以直接使用。

## 快速开始示例

### 1. 基础任务管理

```python
import httpx
import asyncio
from datetime import datetime, timedelta

class DidaClient:
    """滴答清单 API 客户端"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.dida365.com"

    async def create_task(self, title: str, project_id: str, **kwargs):
        """创建任务"""
        data = {
            "title": title,
            "projectId": project_id,
            **kwargs
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/open/v1/task",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_tasks(self, project_id: str = None):
        """获取任务列表"""
        if project_id:
            url = f"{self.base_url}/open/v1/project/{project_id}/data"
        else:
            url = f"{self.base_url}/open/v1/project"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if project_id:
                return data.get("tasks", [])
            else:
                # 获取所有项目的任务
                all_tasks = []
                for project in data:
                    project_tasks = await self.get_tasks(project["id"])
                    all_tasks.extend(project_tasks)
                return all_tasks

    async def complete_task(self, project_id: str, task_id: str):
        """完成任务"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/open/v1/project/{project_id}/task/{task_id}/complete",
                headers=self.headers
            )
            return response.status_code == 200

# 使用示例
async def main():
    client = DidaClient("YOUR_ACCESS_TOKEN")

    # 创建任务
    task = await client.create_task(
        title="学习 Python",
        project_id="YOUR_PROJECT_ID",
        priority=3,
        due_date="2025-11-20T18:00:00.000+0000"
    )
    print(f"创建任务: {task['title']}")

    # 获取任务列表
    tasks = await client.get_tasks("YOUR_PROJECT_ID")
    print(f"项目共有 {len(tasks)} 个任务")

    # 完成任务
    success = await client.complete_task("YOUR_PROJECT_ID", task['id'])
    print("任务完成" if success else "完成任务失败")

asyncio.run(main())
```

### 2. 子任务管理示例

```python
class SubtaskManager:
    """子任务管理器"""

    def __init__(self, client: DidaClient):
        self.client = client

    async def create_task_with_subtasks(
        self,
        title: str,
        project_id: str,
        subtasks: list,
        **kwargs
    ):
        """创建带子任务的任务"""
        items = [
            {"title": subtask, "sortOrder": i + 1}
            for i, subtask in enumerate(subtasks)
        ]

        return await self.client.create_task(
            title=title,
            project_id=project_id,
            items=items,
            kind="CHECKLIST",
            **kwargs
        )

    async def complete_subtask(
        self,
        project_id: str,
        task_id: str,
        subtask_id: str
    ):
        """完成指定子任务"""
        # 获取任务详情
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.client.base_url}/open/v1/project/{project_id}/task/{task_id}",
                headers=self.client.headers
            )
            response.raise_for_status()
            task = response.json()

        # 找到并更新子任务
        for item in task.get("items", []):
            if item["id"] == subtask_id:
                item["status"] = 1
                item["completedTime"] = datetime.now().isoformat() + "Z"
                break

        # 更新任务
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.client.base_url}/open/v1/task/{task_id}",
                json=task,
                headers=self.client.headers
            )
            response.raise_for_status()
            return response.json()

    async def add_subtask(
        self,
        project_id: str,
        task_id: str,
        subtask_title: str
    ):
        """添加新子任务"""
        # 获取任务详情
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.client.base_url}/open/v1/project/{project_id}/task/{task_id}",
                headers=self.client.headers
            )
            response.raise_for_status()
            task = response.json()

        # 添加新子任务
        new_sort_order = max(
            [item.get("sortOrder", 0) for item in task.get("items", [])],
            default=0
        ) + 10

        task["items"].append({
            "title": subtask_title,
            "sortOrder": new_sort_order,
            "status": 0
        })

        # 更新任务
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.client.base_url}/open/v1/task/{task_id}",
                json=task,
                headers=self.client.headers
            )
            response.raise_for_status()
            return response.json()

# 使用示例
async def main():
    client = DidaClient("YOUR_ACCESS_TOKEN")
    subtask_mgr = SubtaskManager(client)

    # 创建带子任务的任务
    project_id = "YOUR_PROJECT_ID"
    subtasks = ["需求分析", "系统设计", "编码实现", "测试部署"]
    task = await subtask_mgr.create_task_with_subtasks(
        title="软件开发项目",
        project_id=project_id,
        subtasks=subtasks,
        priority=5
    )
    print(f"创建任务: {task['title']}")
    print(f"包含 {len(task['items'])} 个子任务")

    # 完成第一个子任务
    await subtask_mgr.complete_subtask(
        project_id,
        task['id'],
        task['items'][0]['id']
    )
    print("已完成第一个子任务")

    # 添加新子任务
    await subtask_mgr.add_subtask(
        project_id,
        task['id'],
        "文档编写"
    )
    print("已添加新子任务")
```

## 实际应用场景

### 场景 1：项目管理

```python
class ProjectManager:
    """项目管理"""

    def __init__(self, client: DidaClient):
        self.client = client

    async def create_project_with_template(
        self,
        name: str,
        project_type: str = "TASK",
        view_mode: str = "kanban"
    ):
        """创建带模板的项目"""
        # 创建项目
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.client.base_url}/open/v1/project",
                json={
                    "name": name,
                    "kind": project_type,
                    "viewMode": view_mode
                },
                headers=self.client.headers
            )
            response.raise_for_status()
            project = response.json()

        # 如果是看板模式，创建默认列
        if view_mode == "kanban":
            columns = ["待办", "进行中", "已完成"]
            for i, column_name in enumerate(columns):
                # 注意：列的创建需要单独的 API，但这里只展示概念
                pass

        return project

    async def get_project_summary(self, project_id: str):
        """获取项目摘要"""
        data = await self.client.get_tasks(project_id)
        tasks = data.get("tasks", []) if isinstance(data, dict) else data

        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("status") == 2)
        high_priority_tasks = sum(1 for t in tasks if t.get("priority") >= 3)

        progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "progress": round(progress, 1),
            "high_priority_tasks": high_priority_tasks
        }

    async def archive_completed_tasks(self, project_id: str):
        """归档已完成的任务"""
        data = await self.client.get_tasks(project_id)
        tasks = data.get("tasks", []) if isinstance(data, dict) else data

        completed_count = 0
        for task in tasks:
            if task.get("status") == 2:
                async with httpx.AsyncClient() as client:
                    response = await client.delete(
                        f"{self.client.base_url}/open/v1/project/{project_id}/task/{task['id']}",
                        headers=self.client.headers
                    )
                    if response.status_code == 200:
                        completed_count += 1

        return completed_count

# 使用示例
async def project_example():
    client = DidaClient("YOUR_ACCESS_TOKEN")
    proj_mgr = ProjectManager(client)

    # 创建项目
    project = await proj_mgr.create_project_with_template(
        name="我的学习计划",
        project_type="TASK",
        view_mode="kanban"
    )
    print(f"创建项目: {project['name']}")

    # 获取项目摘要
    summary = await proj_mgr.get_project_summary(project['id'])
    print(f"项目进度: {summary['progress']}%")
```

### 场景 2：学习计划管理

```python
class LearningPlanManager:
    """学习计划管理"""

    def __init__(self, client: DidaClient):
        self.client = client

    async def create_learning_plan(
        self,
        subject: str,
        study_items: list,
        project_id: str
    ):
        """创建学习计划"""
        task = await self.client.create_task(
            title=f"{subject}学习计划",
            project_id=project_id,
            content=f"系统学习{subject}",
            priority=3,
            kind="CHECKLIST",
            items=[
                {
                    "title": item,
                    "sortOrder": i + 1,
                    "status": 0
                }
                for i, item in enumerate(study_items)
            ]
        )
        return task

    async def track_daily_progress(
        self,
        project_id: str,
        date: str = None
    ):
        """跟踪每日进度"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        data = await self.client.get_tasks(project_id)
        tasks = data.get("tasks", []) if isinstance(data, dict) else data

        daily_tasks = [
            t for t in tasks
            if t.get("dueDate", "").startswith(date)
        ]

        completed = sum(1 for t in daily_tasks if t.get("status") == 2)
        total = len(daily_tasks)
        progress = (completed / total * 100) if total > 0 else 0

        return {
            "date": date,
            "total_tasks": total,
            "completed_tasks": completed,
            "progress": round(progress, 1)
        }

# 使用示例
async def learning_example():
    client = DidaClient("YOUR_ACCESS_TOKEN")
    learning_mgr = LearningPlanManager(client)

    # 创建学习计划
    python_study = [
        "Python基础语法",
        "面向对象编程",
        "异常处理",
        "文件操作",
        "数据库操作",
        "Web开发",
        "项目实战"
    ]

    task = await learning_mgr.create_learning_plan(
        subject="Python",
        study_items=python_study,
        project_id="YOUR_PROJECT_ID"
    )
    print(f"创建学习计划: {task['title']}")

    # 跟踪进度
    progress = await learning_mgr.track_daily_progress("YOUR_PROJECT_ID")
    print(f"今日进度: {progress['progress']}%")
```

### 场景 3：习惯跟踪

```python
class HabitTracker:
    """习惯跟踪器"""

    def __init__(self, client: DidaClient):
        self.client = client

    async def create_habit(self, habit_name: str, project_id: str):
        """创建习惯跟踪任务"""
        return await self.client.create_task(
            title=habit_name,
            project_id=project_id,
            content=f"每日{habit_name}",
            priority=1,
            repeat_flag="RRULE:FREQ=DAILY"
        )

    async def check_in(self, project_id: str, task_id: str):
        """签到（完成任务）"""
        return await self.client.complete_task(project_id, task_id)

    async def get_habit_stats(
        self,
        project_id: str,
        start_date: str,
        end_date: str
    ):
        """获取习惯统计数据"""
        data = await self.client.get_tasks(project_id)
        tasks = data.get("tasks", []) if isinstance(data, dict) else data

        # 筛选时间范围内的任务
        range_tasks = []
        for task in tasks:
            due_date = task.get("dueDate", "")
            if start_date <= due_date <= end_date:
                range_tasks.append(task)

        total_checkins = sum(1 for t in range_tasks if t.get("status") == 2)
        total_days = len(range_tasks)

        streak = self._calculate_streak(tasks)

        return {
            "total_days": total_days,
            "completed_days": total_checkins,
            "completion_rate": round(total_checkins / total_days * 100, 1) if total_days > 0 else 0,
            "current_streak": streak
        }

    def _calculate_streak(self, tasks: list) -> int:
        """计算连续签到天数"""
        completed_tasks = [
            t for t in tasks
            if t.get("status") == 2 and t.get("completedTime")
        ]

        if not completed_tasks:
            return 0

        # 按完成时间倒序排列
        completed_tasks.sort(
            key=lambda x: x.get("completedTime", ""),
            reverse=True
        )

        streak = 1
        last_date = datetime.fromisoformat(
            completed_tasks[0]["completedTime"].replace("Z", "+00:00")
        ).date()

        for task in completed_tasks[1:]:
            completed_date = datetime.fromisoformat(
                task["completedTime"].replace("Z", "+00:00")
            ).date()

            if (last_date - completed_date).days == 1:
                streak += 1
                last_date = completed_date
            else:
                break

        return streak

# 使用示例
async def habit_example():
    client = DidaClient("YOUR_ACCESS_TOKEN")
    tracker = HabitTracker(client)

    # 创建习惯
    habit = await tracker.create_habit("每日阅读", "YOUR_PROJECT_ID")
    print(f"创建习惯: {habit['title']}")

    # 签到
    await tracker.check_in("YOUR_PROJECT_ID", habit['id'])
    print("今日已签到")

    # 查看统计数据
    stats = await tracker.get_habit_stats(
        "YOUR_PROJECT_ID",
        "2025-11-01",
        "2025-11-30"
    )
    print(f"本月完成率: {stats['completion_rate']}%")
    print(f"当前连续: {stats['current_streak']} 天")
```

## 数据导入导出

### 导入 CSV 任务

```python
import csv
from typing import List

async def import_tasks_from_csv(
    client: DidaClient,
    csv_file: str,
    project_id: str
):
    """从 CSV 文件导入任务"""
    imported_count = 0
    errors = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                await client.create_task(
                    title=row['title'],
                    project_id=project_id,
                    content=row.get('content', ''),
                    priority=int(row.get('priority', 0))
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"导入失败 - {row.get('title', 'Unknown')}: {str(e)}")

    return {
        "imported": imported_count,
        "errors": errors
    }

# CSV 格式示例
"""
title,content,priority
任务1,描述1,3
任务2,描述2,5
"""
```

### 导出任务到 JSON

```python
import json

async def export_tasks_to_json(
    client: DidaClient,
    project_id: str,
    output_file: str
):
    """导出任务到 JSON 文件"""
    data = await client.get_tasks(project_id)
    tasks = data.get("tasks", []) if isinstance(data, dict) else data

    export_data = {
        "project_id": project_id,
        "export_date": datetime.now().isoformat(),
        "tasks": tasks
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return len(tasks)
```

## 高级功能

### 批量操作

```python
class BatchOperation:
    """批量操作"""

    def __init__(self, client: DidaClient):
        self.client = client

    async def batch_update_priority(
        self,
        project_id: str,
        task_updates: list
    ):
        """批量更新任务优先级"""
        results = []

        for update in task_updates:
            try:
                task_id = update['task_id']
                priority = update['priority']

                # 获取当前任务
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.client.base_url}/open/v1/project/{project_id}/task/{task_id}",
                        headers=self.client.headers
                    )
                    response.raise_for_status()
                    task = response.json()

                # 更新优先级
                task['priority'] = priority

                # 保存更新
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.client.base_url}/open/v1/task/{task_id}",
                        json=task,
                        headers=self.client.headers
                    )
                    response.raise_for_status()

                results.append({
                    "task_id": task_id,
                    "status": "success",
                    "priority": priority
                })

            except Exception as e:
                results.append({
                    "task_id": update.get('task_id', 'unknown'),
                    "status": "error",
                    "error": str(e)
                })

        return results

# 使用示例
async def batch_example():
    client = DidaClient("YOUR_ACCESS_TOKEN")
    batch_op = BatchOperation(client)

    updates = [
        {"task_id": "task1", "priority": 5},
        {"task_id": "task2", "priority": 3},
        {"task_id": "task3", "priority": 1}
    ]

    results = await batch_op.batch_update_priority(
        "YOUR_PROJECT_ID",
        updates
    )

    for result in results:
        print(f"任务 {result['task_id']}: {result['status']}")
```

### 智能提醒

```python
class SmartReminder:
    """智能提醒管理"""

    def __init__(self, client: DidaClient):
        self.client = client

    async def set_smart_reminders(
        self,
        project_id: str,
        task_id: str,
        due_date: str
    ):
        """设置智能提醒"""
        due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        now = datetime.now()

        if due_datetime > now:
            time_until_due = due_datetime - now

            # 计算提醒时间
            reminders = []

            # 提前1天提醒
            if time_until_due > timedelta(days=1):
                reminders.append("TRIGGER:P1DT0H0M0S")

            # 提前1小时提醒
            if time_until_due > timedelta(hours=1):
                reminders.append("TRIGGER:P0DT1H0M0S")

            # 提前15分钟提醒
            if time_until_due > timedelta(minutes=15):
                reminders.append("TRIGGER:P0DT15M0S")

            # 任务开始时提醒
            reminders.append("TRIGGER:PT0S")

            # 更新任务
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.client.base_url}/open/v1/project/{project_id}/task/{task_id}",
                    headers=self.client.headers
                )
                response.raise_for_status()
                task = response.json()

            task['reminders'] = reminders

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.client.base_url}/open/v1/task/{task_id}",
                    json=task,
                    headers=self.client.headers
                )
                response.raise_for_status()

            return reminders

        return []

# 使用示例
async def reminder_example():
    client = DidaClient("YOUR_ACCESS_TOKEN")
    reminder_mgr = SmartReminder(client)

    reminders = await reminder_mgr.set_smart_reminders(
        "YOUR_PROJECT_ID",
        "YOUR_TASK_ID",
        "2025-11-20T14:00:00.000+0000"
    )

    print(f"设置了 {len(reminders)} 个提醒")
```

## 最佳实践

### 1. 错误处理

```python
async def safe_api_call(func, *args, **kwargs):
    """安全调用 API"""
    try:
        return await func(*args, **kwargs)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": "资源不存在"}
        elif e.response.status_code == 403:
            return {"error": "没有权限"}
        elif e.response.status_code == 401:
            return {"error": "未授权访问"}
        else:
            return {"error": f"HTTP错误: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}"}
```

### 2. 速率限制

```python
import asyncio
from asyncio import Semaphore

class RateLimitedClient:
    """带速率限制的客户端"""

    def __init__(self, access_token: str, max_concurrent: int = 5):
        self.client = DidaClient(access_token)
        self.semaphore = Semaphore(max_concurrent)

    async def limited_request(self, func, *args, **kwargs):
        """限制并发请求"""
        async with self.semaphore:
            return await safe_api_call(func, *args, **kwargs)
```

### 3. 数据验证

```python
from pydantic import BaseModel, ValidationError

class TaskCreateModel(BaseModel):
    """任务创建数据模型"""
    title: str
    project_id: str
    priority: int = 0
    due_date: str = None

    class Config:
        validate_assignment = True

def validate_task_data(data: dict) -> dict:
    """验证任务数据"""
    try:
        validated = TaskCreateModel(**data)
        return validated.dict()
    except ValidationError as e:
        raise ValueError(f"数据验证失败: {e}")
```

## 故障排除

### 常见问题和解决方案

1. **认证失败**
   - 检查访问令牌是否有效
   - 确认令牌未过期
   - 验证授权范围

2. **权限错误**
   - 确认应用有正确的权限
   - 检查用户是否授权了应用

3. **任务创建失败**
   - 验证项目ID是否存在
   - 检查必填字段是否完整

4. **子任务问题**
   - 确保更新时包含完整的items数组
   - 新增子任务不要指定id

---

**文档版本**: 1.0
**最后更新**: 2025年11月16日
**相关文档**: [任务](tasks.md) | [子任务](subtasks.md) | [项目](projects.md)
