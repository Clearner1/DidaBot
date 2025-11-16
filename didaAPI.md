# 滴答清单开放 API 文档

> **重要更新**: API 文档已重构为模块化结构，请参考 `docs/` 目录中的新文档。

## 新文档结构

### 核心文档
- **[docs/README.md](docs/README.md)** - 文档总览和快速开始
- **[docs/authentication.md](docs/authentication.md)** - 授权与认证完整指南
- **[docs/tasks.md](docs/tasks.md)** - 任务操作 API 详解
- **[docs/projects.md](docs/projects.md)** - 项目操作 API 详解
- **[docs/subtasks.md](docs/subtasks.md)** - 子任务机制（重点推荐）

### 实用指南
- **[docs/examples.md](docs/examples.md)** - 实用示例集和最佳实践

## 快速导航

### 子任务机制（重要）
**滴答清单使用 `items` 字段实现子任务功能**：

```json
{
  "title": "项目开发",
  "kind": "CHECKLIST",
  "items": [
    {"id": "subtask1", "title": "需求分析", "status": 0, "sortOrder": 1},
    {"id": "subtask2", "title": "系统设计", "status": 1, "sortOrder": 2}
  ]
}
```

详细说明请参考：[docs/subtasks.md](docs/subtasks.md)

### 常用 API 端点

| 功能 | 端点 | 方法 |
|------|------|------|
| 获取项目列表 | `/open/v1/project` | GET |
| 获取任务列表 | `/open/v1/project/{id}/data` | GET |
| 创建任务 | `/open/v1/task` | POST |
| 更新任务 | `/open/v1/task/{id}` | POST |
| 完成任务 | `/open/v1/project/{projectId}/task/{taskId}/complete` | POST |
| 删除任务 | `/open/v1/project/{projectId}/task/{taskId}` | DELETE |

### 认证
```bash
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## 主要特性

✅ **完整任务管理** - CRUD 操作、优先级、提醒、重复规则
✅ **官方子任务机制** - 使用 `items` 字段，功能完整可靠
✅ **多种项目类型** - TASK、NOTE 项目
✅ **多种视图模式** - 列表、看板、时间轴
✅ **OAuth 2.0 认证** - 安全的标准授权流程

## 快速开始

### 1. 获取访问令牌
参考：[docs/authentication.md](docs/authentication.md)

### 2. 创建任务
```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新任务",
    "projectId": "PROJECT_ID"
  }'
```

### 3. 创建带子任务的任务
```bash
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "项目计划",
    "projectId": "PROJECT_ID",
    "kind": "CHECKLIST",
    "items": [
      {"title": "需求分析", "sortOrder": 1},
      {"title": "系统设计", "sortOrder": 2}
    ]
  }'
```

## 重要提示

### 子任务机制
- ✅ **推荐使用 items 方式** - 官方支持，功能完整
- ❌ **不要使用 parentId 方式** - 存在数据一致性问题

### 子任务操作
- **创建**：新增子任务无需指定 `id`（系统自动生成）
- **更新**：必须包含完整的 `items` 数组
- **完成**：设置 `status: 1` 并添加 `completedTime`
- **删除**：从 `items` 数组中移除

## 最佳实践

1. **始终使用 HTTPS** 进行所有 API 调用
2. **安全存储访问令牌**，避免泄露
3. **处理速率限制**，避免频繁请求
4. **实现错误处理**，处理网络异常和 API 错误
5. **定期备份数据**，避免数据丢失

## 完整示例

### Python 客户端示例
```python
import httpx
import asyncio

class DidaClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def get_projects(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.dida365.com/open/v1/project",
                headers=self.headers
            )
            return response.json()

    async def create_task(self, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dida365.com/open/v1/task",
                json=kwargs,
                headers=self.headers
            )
            return response.json()

# 使用示例
async def main():
    client = DidaClient("YOUR_ACCESS_TOKEN")

    # 获取项目
    projects = await client.get_projects()
    print(f"共有 {len(projects)} 个项目")

    # 创建任务
    task = await client.create_task(
        title="示例任务",
        project_id=projects[0]["id"]
    )
    print(f"创建任务: {task['title']}")

asyncio.run(main())
```

更多示例请参考：[docs/examples.md](docs/examples.md)

## 支持与反馈

- **开发者中心**: [https://developer.dida365.com/manage](https://developer.dida365.com/manage)
- **支持邮箱**: support@dida365.com
- **文档问题反馈**: 请提交 Issue 到项目仓库

## 文档更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2025-11-16 | 2.0 | 模块化文档重构，突出子任务 items 机制 |
| - | 1.0 | 初始文档版本 |

---

**建议优先阅读**：
1. [docs/README.md](docs/README.md) - 快速开始
2. [docs/subtasks.md](docs/subtasks.md) - 子任务机制详解
3. [docs/examples.md](docs/examples.md) - 实用示例

