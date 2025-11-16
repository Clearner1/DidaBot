# 任务 API (Tasks)

## 概述

任务（Task）是滴答清单的核心概念，用于表示用户需要完成的具体工作项。每个任务可以包含标题、内容、描述、时间信息、优先级等属性。

## 任务类型

滴答清单支持三种任务类型：

- **TEXT**：普通任务（默认）
- **NOTE**：笔记条目，用于记录想法、会议内容等
- **CHECKLIST**：包含子任务的任务（详见 [子任务文档](subtasks.md)）

## 获取任务

### 获取单个任务

获取指定项目的特定任务。

**请求：**

```bash
curl -X GET "https://api.dida365.com/open/v1/project/{projectId}/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**

```json
{
  "id": "64a5c8b9e1a2c3d4e5f67890",
  "projectId": "6226ff9877acee87727f6bca",
  "title": "任务标题",
  "content": "任务内容",
  "desc": "任务描述",
  "kind": "TEXT",
  "isAllDay": false,
  "startDate": "2019-11-13T03:00:00.000+0000",
  "dueDate": "2019-11-14T03:00:00.000+0000",
  "timeZone": "Asia/Shanghai",
  "reminders": ["TRIGGER:P0DT1H0M0S"],
  "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
  "priority": 1,
  "status": 0,
  "completedTime": null,
  "sortOrder": 12345
}
```

### 获取任务列表

#### 获取指定项目的所有任务

```bash
curl -X GET "https://api.dida365.com/open/v1/project/{projectId}/data" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

返回包含项目信息和任务列表的完整数据。

#### 获取所有任务（跨项目）

```bash
# 方式1：遍历所有项目
for project in $(curl -s "https://api.dida365.com/open/v1/project" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | jq -r '.[].id'); do
  curl -s "https://api.dida365.com/open/v1/project/$project/data" \
    -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
done
```

## 创建任务

### 基本任务创建

创建简单的文字任务：

```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新任务标题",
    "projectId": "6226ff9877acee87727f6bca"
  }'
```

### 创建笔记条目

创建 NOTE 类型的任务：

```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "会议记录",
    "projectId": "6226ff9877acee87727f6bca",
    "kind": "NOTE",
    "content": "会议讨论内容..."
  }'
```

### 创建带完整属性的任务

```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "重要会议",
    "projectId": "6226ff9877acee87727f6bca",
    "content": "讨论项目进展",
    "desc": "需要准备演示材料",
    "kind": "TEXT",
    "isAllDay": false,
    "startDate": "2025-11-17T14:00:00.000+0000",
    "dueDate": "2025-11-17T16:00:00.000+0000",
    "timeZone": "Asia/Shanghai",
    "reminders": ["TRIGGER:P0DT1H0M0S", "TRIGGER:PT0S"],
    "priority": 5,
    "sortOrder": 100
  }'
```

## 更新任务

### 部分更新

只更新指定的字段：

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "任务ID",
    "projectId": "项目ID",
    "title": "更新后的任务标题",
    "priority": 3
  }'
```

### 更新任务类型

```bash
# 转换为笔记条目
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "任务ID",
    "projectId": "项目ID",
    "title": "任务标题",
    "kind": "NOTE",
    "content": "转换为笔记内容"
  }'
```

## 完成任务

将任务标记为已完成：

```bash
curl -X POST "https://api.dida365.com/open/v1/project/{projectId}/task/{taskId}/complete" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**注意**：完成任务后，任务状态将变为 `status: 2`，并记录 `completedTime`。

## 删除任务

永久删除任务：

```bash
curl -X DELETE "https://api.dida365.com/open/v1/project/{projectId}/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**警告**：删除操作不可逆！

## 字段详解

### 必需字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `title` | string | 任务标题 |
| `projectId` | string | 所属项目ID |

### 可选字段

#### 基础字段

| 字段 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `id` | string | 自动生成 | 任务ID（更新时必需） |
| `content` | string | null | 任务内容/描述 |
| `desc` | string | null | 任务详细描述 |
| `kind` | string | "TEXT" | 任务类型：TEXT、NOTE、CHECKLIST |
| `status` | int | 0 | 状态：0(未完成)、2(已完成) |

#### 时间相关

| 字段 | 类型 | 描述 |
|------|------|------|
| `isAllDay` | boolean | 是否全天任务 |
| `startDate` | string | 开始时间（ISO 8601 格式） |
| `dueDate` | string | 截止时间（ISO 8601 格式） |
| `timeZone` | string | 时区，如 "Asia/Shanghai" |

**时间格式示例**：
- `"2025-11-17T14:00:00.000+0000"` - 完整 ISO 格式
- `"2025-11-17T14:00:00+08:00"` - 带时区偏移

#### 管理字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `priority` | int | 优先级：0(无)、1(低)、3(中)、5(高) |
| `sortOrder` | int | 排序值（数值越大越靠前） |
| `completedTime` | string | 完成时间（自动设置） |
| `columnId` | string | 看板列ID（看板模式） |

#### 提醒和重复

| 字段 | 类型 | 描述 |
|------|------|------|
| `reminders` | array | 提醒列表 |
| `repeatFlag` | string | 重复规则 |

## 提醒格式

提醒使用 ISO 8601 持续时间格式：

```
TRIGGER:P{天}DT{小时}H{分钟}M{秒}S
```

### 常用提醒示例

| 提醒时间 | 格式 |
|----------|------|
| 立即提醒 | `["TRIGGER:PT0S"]` |
| 15分钟前 | `["TRIGGER:P0DT15M0S"]` |
| 1小时前 | `["TRIGGER:P0DT1H0M0S"]` |
| 1天前 | `["TRIGGER:P1DT0H0M0S"]` |
| 多重提醒 | `["TRIGGER:P1DT0H0M0S", "TRIGGER:P0DT1H0M0S"]` |

## 重复规则

使用 RFC 5545 格式：

```
RRULE:FREQ={频率};[参数]
```

### 频率类型

- **DAILY**：每日
- **WEEKLY**：每周
- **MONTHLY**：每月
- **YEARLY**：每年

### 常用示例

| 规则 | 格式 |
|------|------|
| 每天 | `"RRULE:FREQ=DAILY"` |
| 每2天 | `"RRULE:FREQ=DAILY;INTERVAL=2"` |
| 工作日 | `"RRULE:FREQ=DAILY;TT_SKIP=WEEKEND"` |
| 每周一三五 | `"RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"` |
| 每月15号 | `"RRULE:FREQ=MONTHLY;BYMONTHDAY=15"` |
| 每年1月1日 | `"RRULE:FREQ=YEARLY;BYMONTH=1;BYMONTHDAY=1"` |

## Python 示例

### 基础任务管理

```python
import httpx
from datetime import datetime, timedelta

class TaskManager:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def create_task(
        self, title: str, project_id: str,
        content: str = None,
        priority: int = 0,
        due_date: str = None
    ) -> dict:
        """创建任务"""
        data = {
            "title": title,
            "projectId": project_id,
            "priority": priority
        }
        if content:
            data["content"] = content
        if due_date:
            data["dueDate"] = due_date

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dida365.com/open/v1/task",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def complete_task(self, project_id: str, task_id: str) -> bool:
        """完成任务"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.dida365.com/open/v1/project/{project_id}/task/{task_id}/complete",
                headers=self.headers
            )
            return response.status_code == 200

    async def get_tasks(self, project_id: str) -> list:
        """获取项目任务"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.dida365.com/open/v1/project/{project_id}/data",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()["tasks"]

# 使用示例
async def main():
    manager = TaskManager("YOUR_ACCESS_TOKEN")

    # 创建任务
    task = await manager.create_task(
        title="完成项目报告",
        project_id="PROJECT_ID",
        content="需要包含数据分析",
        priority=3,
        due_date="2025-11-20T18:00:00.000+0000"
    )
    print(f"任务创建成功: {task['id']}")

    # 获取任务列表
    tasks = await manager.get_tasks("PROJECT_ID")
    print(f"项目共有 {len(tasks)} 个任务")

    # 完成任务
    success = await manager.complete_task("PROJECT_ID", task['id'])
    print("任务完成" if success else "完成任务失败")
```

## 常见问题

**Q: 如何批量操作任务？**

A: 滴答清单 API 不支持批量操作，需要逐个调用 API。

**Q: 任务状态有哪些？**

A: 主要状态：`0` (未完成)、`2` (已完成)。

**Q: 如何处理时区？**

A: 建议始终使用 UTC 时间（Z 结尾），系统会自动转换为本地时区显示。

**Q: 可以创建空任务吗？**

A: 不可以，`title` 字段是必需的。

## 最佳实践

1. **合理使用优先级**：将真正重要的任务设置为高优先级
2. **设置适当提醒**：避免设置过多提醒导致信息过载
3. **定期清理**：及时完成或删除不需要的任务
4. **使用重复规则**：对于定期任务使用重复规则而非手动创建
5. **保持任务具体**：每个任务应该有明确的目标和完成标准

---

**文档版本**: 1.0
**最后更新**: 2025年11月16日
**相关文档**: [子任务](subtasks.md) | [项目](projects.md)
