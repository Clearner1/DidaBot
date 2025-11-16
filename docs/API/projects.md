# 项目 API (Projects)

## 概述

项目（Project）是滴答清单中组织任务的容器。每个项目可以包含多个任务，并支持不同的视图模式和类型。

## 项目类型

### 按功能分类

- **TASK**：任务项目，用于管理待办事项和工作任务
- **NOTE**：笔记项目，用于记录想法、日记、会议内容等

### 按视图模式分类

- **list**：列表视图（传统列表显示）
- **kanban**：看板视图（类似 Trello 的看板管理）
- **timeline**：时间轴视图（按时间顺序展示）

## 获取项目

### 获取所有项目

```bash
curl -X GET "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应示例：**

```json
[
  {
    "id": "6226ff9877acee87727f6bca",
    "name": "工作项目",
    "color": "#F18181",
    "closed": false,
    "groupId": "6436176a47fd2e05f26ef56e",
    "viewMode": "kanban",
    "permission": "write",
    "kind": "TASK"
  },
  {
    "id": "675fc6d7eba6f4000000018a",
    "name": "日记本",
    "color": "#F678AC",
    "viewMode": "kanban",
    "kind": "NOTE"
  }
]
```

### 获取单个项目详情

```bash
curl -X GET "https://api.dida365.com/open/v1/project/{projectId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 获取项目完整数据

获取项目及其所有任务、列信息：

```bash
curl -X GET "https://api.dida365.com/open/v1/project/{projectId}/data" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应示例：**

```json
{
  "project": {
    "id": "6226ff9877acee87727f6bca",
    "name": "项目名称",
    "color": "#F18181",
    "closed": false,
    "groupId": "6436176a47fd2e05f26ef56e",
    "viewMode": "kanban",
    "kind": "TASK"
  },
  "tasks": [
    {
      "id": "64a5c8b9e1a2c3d4e5f67890",
      "title": "任务标题",
      "status": 0,
      "priority": 1
    }
  ],
  "columns": [
    {
      "id": "64a5c8b9e1a2c3d4e5f67891",
      "name": "待办",
      "sortOrder": 0
    },
    {
      "id": "64a5c8b9e1a2c3d4e5f67892",
      "name": "进行中",
      "sortOrder": 1
    }
  ]
}
```

## 创建项目

### 创建基本项目

```bash
curl -X POST "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "新项目名称"
  }'
```

### 创建带属性的项目

```bash
curl -X POST "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "软件开发项目",
    "color": "#4CAF50",
    "viewMode": "kanban",
    "kind": "TASK",
    "sortOrder": 100
  }'
```

## 更新项目

```bash
curl -X POST "https://api.dida365.com/open/v1/project/{projectId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "更新后的项目名称",
    "color": "#FF5722",
    "viewMode": "list"
  }'
```

## 删除项目

```bash
curl -X DELETE "https://api.dida365.com/open/v1/project/{projectId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**警告**：删除项目会同时删除项目中的所有任务！

## 字段详解

### 必需字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | string | 项目名称 |

### 可选字段

| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `id` | string | 自动生成 | 项目ID（更新时必需） |
| `color` | string | "transparent" | 项目颜色（十六进制） |
| `sortOrder` | int | 0 | 排序值 |
| `closed` | boolean | false | 是否已关闭 |
| `groupId` | string | null | 项目组ID |
| `viewMode` | string | "list" | 视图模式：list、kanban、timeline |
| `kind` | string | "TASK" | 项目类型：TASK、NOTE |
| `permission` | string | "write" | 权限：read、write、comment |

## 颜色代码

常用颜色代码：

| 颜色 | 代码 | 用途 |
|------|------|------|
| 红色 | `#F18181` | 重要项目 |
| 绿色 | `#4CAF50` | 成功/完成 |
| 蓝色 | `#4682B4` | 工作/学习 |
| 橙色 | `#FF9800` | 提醒/警告 |
| 紫色 | `#9C27B0` | 创意/设计 |
| 粉色 | `#E91E63` | 生活/个人 |
| 灰色 | `#9E9E9E` | 其他 |

## 看板模式（Kanban）

看板模式提供类似 Trello 的可视化任务管理。

### 看板列

看板项目包含 `columns` 数组，每列代表一个状态：

```json
{
  "columns": [
    {
      "id": "64a5c8b9e1a2c3d4e5f67891",
      "projectId": "6226ff9877acee87727f6bca",
      "name": "待办",
      "sortOrder": 0
    },
    {
      "id": "64a5c8b9e1a2c3d4e5f67892",
      "projectId": "6226ff9877acee87727f6bca",
      "name": "进行中",
      "sortOrder": 1
    },
    {
      "id": "64a5c8b9e1a2c3d4e5f67893",
      "projectId": "6226ff9877acee87727f6bca",
      "name": "已完成",
      "sortOrder": 2
    }
  ]
}
```

### 在看板列中创建任务

创建任务时指定 `columnId`：

```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "在待办列中创建任务",
    "projectId": "6226ff9877acee87727f6bca",
    "columnId": "64a5c8b9e1a2c3d4e5f67891"
  }'
```

### 在看板列间移动任务

更新任务的 `columnId`：

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "任务ID",
    "projectId": "项目ID",
    "title": "任务标题",
    "columnId": "新列ID"
  }'
```

## 项目组

### 概念

项目可以归属于项目组（groupId），用于组织相关项目。

### 常用项目组结构

```
工作项目组
├── 公司项目
├── 个人项目
└── 团队协作

学习项目组
├── 编程学习
├── 读书笔记
└── 课程作业
```

### 获取项目组中的项目

```bash
# 获取所有项目后按 groupId 过滤
curl -s "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | \
  jq '.[] | select(.groupId == "YOUR_GROUP_ID")'
```

## Python 示例

### 基础项目管理

```python
import httpx

class ProjectManager:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def get_projects(self) -> list:
        """获取所有项目"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.dida365.com/open/v1/project",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_project_data(self, project_id: str) -> dict:
        """获取项目完整数据"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.dida365.com/open/v1/project/{project_id}/data",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def create_project(
        self, name: str, kind: str = "TASK",
        view_mode: str = "list", color: str = "transparent"
    ) -> dict:
        """创建项目"""
        data = {
            "name": name,
            "kind": kind,
            "viewMode": view_mode,
            "color": color
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dida365.com/open/v1/project",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def update_project(
        self, project_id: str, name: str = None,
        color: str = None, view_mode: str = None
    ) -> dict:
        """更新项目"""
        data = {"id": project_id}
        if name:
            data["name"] = name
        if color:
            data["color"] = color
        if view_mode:
            data["viewMode"] = view_mode

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.dida365.com/open/v1/project/{project_id}",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.dida365.com/open/v1/project/{project_id}",
                headers=self.headers
            )
            return response.status_code in [200, 204]

# 使用示例
async def main():
    manager = ProjectManager("YOUR_ACCESS_TOKEN")

    # 获取所有项目
    projects = await manager.get_projects()
    print(f"共有 {len(projects)} 个项目")

    # 创建新项目
    project = await manager.create_project(
        name="我的学习项目",
        kind="NOTE",
        view_mode="kanban",
        color="#4CAF50"
    )
    print(f"创建项目成功: {project['id']}")

    # 获取项目数据
    project_data = await manager.get_project_data(project['id'])
    print(f"项目包含 {len(project_data['tasks'])} 个任务")
    print(f"项目有 {len(project_data['columns'])} 个列")

    # 更新项目
    updated = await manager.update_project(
        project['id'],
        name="学习与成长",
        color="#2196F3"
    )
    print("项目更新成功")

    # 删除项目
    # success = await manager.delete_project(project['id'])
    # print("项目已删除" if success else "删除失败")
```

### 看板项目管理

```python
class KanbanProjectManager:
    """看板项目管理"""

    async def create_kanban_project(
        self, name: str, columns: list, color: str = "#4CAF50"
    ) -> dict:
        """创建带默认列的看板项目"""
        # 先创建项目
        project = await self.create_project(
            name=name,
            kind="TASK",
            view_mode="kanban",
            color=color
        )

        # 为每个任务设置 columnId
        return project

    async def move_task_to_column(
        self, task_id: str, project_id: str, column_id: str
    ) -> dict:
        """将任务移动到指定列"""
        data = {
            "id": task_id,
            "projectId": project_id,
            "columnId": column_id
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.dida365.com/open/v1/task/{task_id}",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_tasks_by_column(self, project_id: str) -> dict:
        """按列分组获取任务"""
        project_data = await self.get_project_data(project_id)
        columns = {col['id']: col['name'] for col in project_data['columns']}

        tasks_by_column = {col_id: [] for col_id in columns}
        for task in project_data['tasks']:
            column_id = task.get('columnId', '')
            if column_id in tasks_by_column:
                tasks_by_column[column_id].append(task)

        return {columns[col_id]: tasks for col_id, tasks in tasks_by_column.items()}
```

## 最佳实践

### 1. 项目命名规范

- 使用清晰、简洁的名称
- 避免过长的名称（建议不超过 20 字符）
- 使用统一的项目命名规范

### 2. 项目类型选择

- **TASK 项目**：用于工作计划、待办事项、项目管理
- **NOTE 项目**：用于日记、学习笔记、会议记录、思考总结

### 3. 视图模式选择

- **list 视图**：适合传统的任务列表管理
- **kanban 视图**：适合工作流管理、项目进度跟踪
- **timeline 视图**：适合时间线管理、长期规划

### 4. 颜色使用

- 为不同类型项目使用不同颜色
- 保持颜色使用的一致性
- 避免使用过多鲜艳颜色

### 5. 项目组织

- 合理使用项目组组织相关项目
- 定期归档已完成的项目
- 保持项目数量在可管理范围内

## 常见问题

**Q: 一个用户可以创建多少个项目？**

A: 官方没有明确限制，但建议保持在合理范围内（通常不超过 100 个）。

**Q: 如何备份项目数据？**

A: 定期导出项目数据，或通过 API 定期同步到本地存储。

**Q: 删除的项目可以恢复吗？**

A: 不可以，删除操作不可逆。

**Q: 如何批量移动任务到另一个项目？**

A: API 不支持批量操作，需要逐个更新任务的 `projectId` 字段。

**Q: 看板列的数量有限制吗？**

A: 官方没有明确说明，建议不超过 10 个列以保持良好的可用性。

---

**文档版本**: 1.0
**最后更新**: 2025年11月16日
**相关文档**: [任务](tasks.md) | [子任务](subtasks.md)
