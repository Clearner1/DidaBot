# 滴答清单开放 API 文档

## 欢迎使用滴答清单开放 API

滴答清单开放 API 提供完整的任务和项目管理功能，帮助开发者构建自己的任务管理应用、自动化工具和集成系统。

API Base URL: `https://api.dida365.com`

---

## 快速导航

### 核心概念
- **[任务 (Tasks)](tasks.md)** - 创建、管理和跟踪任务
- **[项目 (Projects)](projects.md)** - 组织和管理任务项目
- **[子任务 (Subtasks)](subtasks.md)** - 通过 `items` 字段实现的完整子任务机制

### 认证授权
- **[授权流程](authentication.md)** - OAuth 2.0 完整实现指南

### 实用指南
- **[实用示例](examples.md)** - 真实场景的完整代码示例

---

## 核心特性

### 任务管理
- ✅ 创建、读取、更新、删除任务
- ✅ 支持多种任务类型：普通任务、笔记、子任务
- ✅ 完整的优先级、提醒、重复规则支持
- ✅ 批量操作和智能提醒

### 子任务系统
- ✅ **官方推荐方式**：使用 `items` 字段
- ✅ 完整的 CRUD 操作
- ✅ 自动状态同步
- ✅ 灵活排序和进度跟踪

### 项目组织
- ✅ 多种视图模式：列表、看板、时间轴
- ✅ 项目组管理
- ✅ 看板列功能
- ✅ 颜色分类

### 授权安全
- ✅ OAuth 2.0 标准协议
- ✅ 细粒度权限控制
- ✅ 安全的令牌管理

---

## 快速开始

### 1. 获取访问令牌

```python
import asyncio
import httpx

async def get_access_token():
    """获取访问令牌的简化流程"""
    # 详细的 OAuth 流程请参考 authentication.md

    # 步骤1：用户授权后获取授权码
    code = "USER_AUTHORIZATION_CODE"

    # 步骤2：交换访问令牌
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://dida365.com/oauth/token",
            # 详细的请求参数请参考 authentication.md
        )
        token_data = response.json()
        return token_data["access_token"]

# 获取访问令牌
access_token = asyncio.run(get_access_token())
```

### 2. 创建第一个任务

```python
import httpx

async def create_first_task():
    """创建第一个任务"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.dida365.com/open/v1/task",
            headers=headers,
            json={
                "title": "我的第一个任务",
                "projectId": "YOUR_PROJECT_ID"
            }
        )
        task = response.json()
        print(f"任务创建成功: {task['title']}")
        return task

# 运行示例
task = asyncio.run(create_first_task())
```

### 3. 创建带子任务的任务

```python
async def create_task_with_subtasks():
    """创建带子任务的任务"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.dida365.com/open/v1/task",
            headers=headers,
            json={
                "title": "项目开发计划",
                "projectId": "YOUR_PROJECT_ID",
                "kind": "CHECKLIST",
                "items": [
                    {"title": "需求分析", "sortOrder": 1},
                    {"title": "系统设计", "sortOrder": 2},
                    {"title": "编码实现", "sortOrder": 3}
                ]
            }
        )
        task = response.json()
        print(f"创建任务: {task['title']}")
        print(f"包含 {len(task['items'])} 个子任务")
        return task

# 运行示例
task = asyncio.run(create_task_with_subtasks())
```

---

## 重要概念

### 任务类型

| 类型 | 描述 | 使用场景 |
|------|------|----------|
| `TEXT` | 普通任务（默认） | 待办事项、工作任务 |
| `NOTE` | 笔记条目 | 会议记录、学习笔记、想法记录 |
| `CHECKLIST` | 包含子任务的任务 | 项目管理、复杂任务分解 |

### 子任务机制（重点）

**滴答清单使用 `items` 字段实现子任务功能：**

```json
{
  "title": "项目开发",
  "kind": "CHECKLIST",
  "items": [
    {
      "id": "subtask_id_1",
      "title": "需求分析",
      "status": 0,
      "sortOrder": 1
    },
    {
      "id": "subtask_id_2",
      "title": "系统设计",
      "status": 1,
      "completedTime": "2025-11-16T09:00:00.000+0000",
      "sortOrder": 2
    }
  ]
}
```

**子任务操作：**
- ✅ **创建**：在 `items` 数组中添加新项（新子任务无需指定 `id`）
- ✅ **更新**：更新 `items` 数组中的特定项
- ✅ **完成**：设置 `status: 1` 并添加 `completedTime`
- ✅ **删除**：从 `items` 数组中移除

**重要提示**：
- 子任务不是独立对象，必须通过父任务管理
- 更新时必须包含完整的 `items` 数组
- 不要尝试单独操作子任务

---

## 常见操作

### 获取项目列表

```bash
curl "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 获取项目任务

```bash
curl "https://api.dida365.com/open/v1/project/{projectId}/data" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 完成任务

```bash
curl -X POST "https://api.dida365.com/open/v1/project/{projectId}/task/{taskId}/complete" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 更新任务

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "taskId",
    "projectId": "projectId",
    "title": "更新后的标题",
    "priority": 5
  }'
```

---

## 实用工具

### Python 客户端

```python
import httpx
from typing import List, Optional

class DidaClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def get_projects(self) -> List[dict]:
        """获取所有项目"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.dida365.com/open/v1/project",
                headers=self.headers
            )
            return response.json()

    async def create_task(self, **kwargs) -> dict:
        """创建任务"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dida365.com/open/v1/task",
                json=kwargs,
                headers=self.headers
            )
            return response.json()

    async def get_tasks(self, project_id: str) -> List[dict]:
        """获取项目任务"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.dida365.com/open/v1/project/{project_id}/data",
                headers=self.headers
            )
            return response.json()["tasks"]

# 使用示例
async def main():
    client = DidaClient("YOUR_ACCESS_TOKEN")

    # 获取项目
    projects = await client.get_projects()
    print(f"共有 {len(projects)} 个项目")

    # 创建任务
    task = await client.create_task(
        title="示例任务",
        project_id=projects[0]["id"],
        priority=3
    )
    print(f"创建任务: {task['title']}")

asyncio.run(main())
```

### 实用脚本

#### 批量导入任务

```python
import csv
import asyncio

async def import_tasks_from_csv(csv_file: str, project_id: str):
    """从 CSV 导入任务"""
    client = DidaClient("YOUR_ACCESS_TOKEN")

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            await client.create_task(
                title=row['title'],
                project_id=project_id,
                content=row.get('content', ''),
                priority=int(row.get('priority', 0))
            )

# 运行
asyncio.run(import_tasks_from_csv("tasks.csv", "PROJECT_ID"))
```

#### 项目备份

```python
import json
from datetime import datetime

async def backup_project(project_id: str):
    """备份项目数据"""
    client = DidaClient("YOUR_ACCESS_TOKEN")

    # 获取项目信息和任务
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.dida365.com/open/v1/project/{project_id}/data",
            headers=self.headers
        )
        data = response.json()

    # 保存到文件
    filename = f"backup_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"项目数据已备份到: {filename}")

# 运行
asyncio.run(backup_project("PROJECT_ID"))
```

---

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
    except Exception as e:
        return {"error": f"错误: {str(e)}"}
```

### 2. 速率限制

```python
from asyncio import Semaphore

# 限制并发请求数
semaphore = Semaphore(5)

async def limited_request(func, *args, **kwargs):
    async with semaphore:
        return await safe_api_call(func, *args, **kwargs)
```

### 3. 数据验证

```python
from pydantic import BaseModel

class TaskCreateModel(BaseModel):
    title: str
    project_id: str
    priority: int = 0

def validate_task_data(data: dict) -> dict:
    validated = TaskCreateModel(**data)
    return validated.dict()
```

---

## API 端点速查

| 端点 | 方法 | 描述 |
|------|------|------|
| `/open/v1/project` | GET | 获取所有项目 |
| `/open/v1/project/{id}` | GET | 获取项目详情 |
| `/open/v1/project/{id}/data` | GET | 获取项目完整数据 |
| `/open/v1/project` | POST | 创建项目 |
| `/open/v1/project/{id}` | POST | 更新项目 |
| `/open/v1/project/{id}` | DELETE | 删除项目 |
| `/open/v1/task` | POST | 创建任务 |
| `/open/v1/task/{id}` | GET | 获取任务详情 |
| `/open/v1/task/{id}` | POST | 更新任务 |
| `/open/v1/project/{projectId}/task/{taskId}/complete` | POST | 完成任务 |
| `/open/v1/project/{projectId}/task/{taskId}` | DELETE | 删除任务 |

---

## 错误代码

| HTTP 状态码 | 描述 |
|-------------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（访问令牌无效或已过期） |
| 403 | 没有权限访问指定资源 |
| 404 | 指定的资源不存在 |
| 429 | 请求频率过高 |
| 500 | 服务器内部错误 |

---

## 支持与反馈

- **开发者中心**: [https://developer.dida365.com/manage](https://developer.dida365.com/manage)
- **支持邮箱**: support@dida365.com
- **API 文档更新**: 本文档会根据 API 更新及时调整

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 2.0 | 2025-11-16 | 模块化文档重构，突出子任务 items 机制 |
| 1.0 | - | 初始版本 |

---

## 许可证

本文档遵循 MIT 许可证。详细信息请参考 LICENSE 文件。

---

## 开始使用

1. **阅读 [授权流程](authentication.md)** - 了解如何获取访问令牌
2. **查看 [任务文档](tasks.md)** - 学习任务基础操作
3. **学习 [子任务文档](subtasks.md)** - 掌握完整的子任务机制
4. **浏览 [实用示例](examples.md)** - 获取真实场景的代码示例

**祝您使用愉快！**
