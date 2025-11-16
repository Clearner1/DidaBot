# 子任务机制 (Subtasks)

## 概述

滴答清单提供完整的**子任务**功能，通过 `items` 字段实现。子任务与父任务紧密集成，提供一体化的任务管理体验。

## 核心特性

### ✅ 设计优势
- **官方推荐**：这是滴答清单官方支持的唯一子任务机制
- **数据一致性**：子任务与父任务自动同步，无需手动维护
- **完整 CRUD**：支持创建、读取、更新、删除所有操作
- **自动 ID 管理**：系统自动生成和管理子任务ID
- **状态跟踪**：支持完成状态和完成时间记录
- **灵活排序**：可调整子任务显示顺序

### 📊 技术规格
- **任务类型**：包含子任务的父任务自动设置为 `kind="CHECKLIST"`
- **子任务存储**：作为父任务的 `items` 数组字段存储
- **状态值**：`0` (未完成)、`1` (已完成)
- **ID 管理**：子任务ID由系统自动生成，无需手动指定

## 创建带子任务的任务

### 请求示例

```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "项目开发计划",
    "content": "详细的开发任务分解",
    "projectId": "YOUR_PROJECT_ID",
    "priority": 3,
    "items": [
      {
        "title": "需求分析",
        "sortOrder": 1
      },
      {
        "title": "系统设计",
        "sortOrder": 2
      },
      {
        "title": "编码实现",
        "sortOrder": 3
      }
    ]
  }'
```

### 响应示例

```json
{
  "id": "64a5c8b9e1a2c3d4e5f67890",
  "title": "项目开发计划",
  "kind": "CHECKLIST",
  "projectId": "YOUR_PROJECT_ID",
  "content": "详细的开发任务分解",
  "priority": 3,
  "status": 0,
  "items": [
    {
      "id": "64a5c8b9e1a2c3d4e5f67891",
      "title": "需求分析",
      "status": 0,
      "sortOrder": 1
    },
    {
      "id": "64a5c8b9e1a2c3d4e5f67892",
      "title": "系统设计",
      "status": 0,
      "sortOrder": 2
    }
  ]
}
```

## 完整操作指南

### 1️⃣ 查看任务和子任务

```bash
curl -X GET "https://api.dida365.com/open/v1/project/{projectId}/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 2️⃣ 更新子任务状态

将指定子任务标记为完成：

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "父任务ID",
    "projectId": "项目ID",
    "title": "任务标题",
    "items": [
      {
        "id": "子任务ID",
        "title": "子任务标题",
        "status": 1,
        "completedTime": "2025-11-16T09:00:00.000+0000",
        "sortOrder": 1
      }
    ]
  }'
```

### 3️⃣ 添加新子任务

在现有任务中添加新的子任务：

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "父任务ID",
    "projectId": "项目ID",
    "title": "任务标题",
    "items": [
      {
        "id": "现有子任务ID",
        "title": "现有子任务",
        "status": 0,
        "sortOrder": 1
      },
      {
        "title": "新子任务标题",
        "sortOrder": 2
      }
    ]
  }'
```

**重要提示**：新增的子任务**无需**指定 `id` 字段，系统会自动生成。

### 4️⃣ 删除子任务

从任务中删除指定子任务（只需从 `items` 数组中移除）：

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "父任务ID",
    "projectId": "项目ID",
    "title": "任务标题",
    "items": [
      {
        "id": "保留的子任务ID",
        "title": "保留的子任务",
        "status": 0,
        "sortOrder": 1
      }
      // 要删除的子任务直接从 items 数组中移除
    ]
  }'
```

### 5️⃣ 调整子任务顺序

重新排列子任务的显示顺序：

```bash
curl -X POST "https://api.dida365.com/open/v1/task/{taskId}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "父任务ID",
    "projectId": "项目ID",
    "title": "任务标题",
    "items": [
      {
        "id": "子任务1_ID",
        "title": "第一个任务",
        "sortOrder": 10
      },
      {
        "id": "子任务2_ID",
        "title": "第二个任务",
        "sortOrder": 20
      }
    ]
  }'
```

## 实用示例

### 项目管理场景

```json
{
  "title": "网站重构项目",
  "content": "对现有网站进行全面重构和优化",
  "projectId": "项目ID",
  "priority": 5,
  "items": [
    {"title": "需求调研和分析", "sortOrder": 1},
    {"title": "技术方案设计", "sortOrder": 2},
    {"title": "前端开发", "sortOrder": 3},
    {"title": "后端API开发", "sortOrder": 4},
    {"title": "数据库设计", "sortOrder": 5},
    {"title": "测试和调试", "sortOrder": 6},
    {"title": "部署上线", "sortOrder": 7}
  ]
}
```

### 学习计划场景

```json
{
  "title": "Python深度学习课程",
  "content": "系统学习Python机器学习和深度学习",
  "projectId": "项目ID",
  "priority": 3,
  "items": [
    {"title": "Python基础巩固", "sortOrder": 1},
    {"title": "NumPy和Pandas学习", "sortOrder": 2},
    {"title": "机器学习算法理论", "sortOrder": 3},
    {"title": "TensorFlow/PyTorch实践", "sortOrder": 4},
    {"title": "项目实战", "sortOrder": 5}
  ]
}
```

## 最佳实践

### ✅ 正确做法

1. **始终包含完整的 items 数组**
   - 更新时必须包含所有现有子任务
   - 新增子任务无需指定 ID（系统自动生成）

2. **保持 sortOrder 的唯一性**
   - 每个子任务应有不同的 sortOrder 值
   - 建议使用 10、20、30 的间隔值便于插入

3. **合理设置 completedTime**
   - 仅当 status 为 1 时设置 completedTime
   - 使用 ISO 8601 格式：`"2025-11-16T09:00:00.000+0000"`

### ❌ 错误做法

1. **不要尝试单独操作子任务**
   - 子任务不是独立对象，不能单独查询
   - 所有操作都必须通过父任务进行

2. **不要忽略必需字段**
   - 更新时必须提供 `id` 和 `projectId`
   - `title` 字段通常也是必需的

## Python 代码示例

### 创建任务管理类

```python
import httpx
from typing import List, Dict

class DidaSubtaskManager:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.dida365.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def create_task_with_subtasks(
        self, title: str, project_id: str,
        subtasks: List[str], priority: int = 0
    ) -> Dict:
        """创建带子任务的任务"""
        items = [
            {"title": subtask, "sortOrder": i+1}
            for i, subtask in enumerate(subtasks)
        ]

        data = {
            "title": title,
            "projectId": project_id,
            "priority": priority,
            "items": items
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/open/v1/task",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def complete_subtask(
        self, task_id: str, project_id: str,
        subtask_id: str, items: List[Dict]
    ) -> Dict:
        """完成指定子任务"""
        for item in items:
            if item["id"] == subtask_id:
                item["status"] = 1
                item["completedTime"] = "2025-11-16T09:00:00.000+0000"
                break

        data = {
            "id": task_id,
            "projectId": project_id,
            "title": "任务标题",  # 实际使用时应该获取当前标题
            "items": items
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/open/v1/task/{task_id}",
                json=data,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# 使用示例
async def main():
    manager = DidaSubtaskManager("YOUR_ACCESS_TOKEN")

    # 创建带子任务的任务
    subtasks = ["需求分析", "系统设计", "编码实现", "测试部署"]
    task = await manager.create_task_with_subtasks(
        title="软件开发项目",
        project_id="YOUR_PROJECT_ID",
        subtasks=subtasks,
        priority=3
    )

    print(f"创建任务成功: {task['id']}")
    print(f"包含 {len(task['items'])} 个子任务")
```

## 进度统计

### 计算完成进度

```python
def calculate_progress(items: List[Dict]) -> Dict:
    """计算子任务完成进度"""
    total = len(items)
    completed = sum(1 for item in items if item.get("status") == 1)
    progress = (completed / total * 100) if total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "progress_percent": round(progress, 1)
    }

# 使用示例
items = [
    {"id": "1", "title": "任务1", "status": 1},
    {"id": "2", "title": "任务2", "status": 0},
    {"id": "3", "title": "任务3", "status": 1}
]

progress = calculate_progress(items)
print(f"进度: {progress['completed']}/{progress['total']} ({progress['progress_percent']}%)")
# 输出: 进度: 2/3 (66.7%)
```

## 常见问题

**Q: 如何批量更新多个子任务？**

A: 在更新时，将所有子任务（包括已完成和未完成的）都包含在 `items` 数组中。

**Q: 能否单独查询某个子任务？**

A: 不能。子任务不是独立对象，必须通过父任务查询和管理。

**Q: 删除父任务会同时删除子任务吗？**

A: 是的。删除父任务会同时删除其所有子任务。

## 总结

滴答清单的子任务功能通过 `items` 字段提供了完整而可靠的项目管理能力：

- **简单易用**：通过数组方式管理子任务，直观明了
- **功能完整**：支持完整的 CRUD 操作和状态管理
- **数据一致**：子任务与父任务自动同步，无需手动维护
- **灵活性强**：支持动态添加、删除、重排序子任务

遵循本指南的最佳实践，您可以充分利用滴答清单的子任务功能进行高效的项目管理和任务跟踪。

---

**文档版本**: 2.0
**最后更新**: 2025年11月16日
**适用版本**: 滴答清单 Open API v1
