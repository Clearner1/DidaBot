# 子任务功能实现 - 快速参考

## 📋 概述

基于我们之前对滴答清单 API 的深入测试，已经确定了**使用 `items` 字段**是实现子任务的正确方式。本文档提供实现子任务功能的核心要点和快速参考。

## 🎯 核心发现（来自 API 测试）

### ✅ 正确机制：items 数组
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

### ❌ 避免使用：parentId 机制
- 存在数据一致性问题
- childIds 是只读字段
- 不推荐使用

## 🏗️ 实现架构

```
用户命令 (/addsubtask, /completesubtask 等)
    ↓
SubtaskHandlers (新增)
    ↓
AI Tools (AddSubtaskTool, CompleteSubtaskTool 等)
    ↓
DidaClient (增强现有类)
    ↓
滴答清单 API
```

## 📦 需要开发的组件

### 1. API 层增强 (src/dida_client.py)

**新增 5 个方法**：

| 方法 | 功能 | 状态 |
|------|------|------|
| `add_subtask_to_task()` | 添加子任务 | ⏳ |
| `complete_subtask()` | 完成子任务 | ⏳ |
| `delete_subtask_from_task()` | 删除子任务 | ⏳ |
| `reorder_subtasks()` | 重新排序 | ⏳ |
| `get_subtasks()` | 获取子任务列表 | ⏳ |
| `calculate_subtask_progress()` | 计算进度 | ⏳ |

**核心实现要点**：

```python
async def add_subtask_to_task(self, project_id, task_id, subtask_title, sort_order=None):
    # 1. 获取当前任务（包含 items）
    task = await self.get_task(project_id, task_id)

    # 2. 计算新 sort_order
    if not sort_order and task.items:
        max_order = max(item.get("sortOrder", 0) for item in task.items)
        sort_order = max_order + 10

    # 3. 创建新子任务（⚠️ 不指定 id！）
    new_item = {"title": subtask_title, "sortOrder": sort_order}

    # 4. 添加到 items 数组
    task.items.append(new_item)

    # 5. 更新任务（必须包含完整的 items）
    return await self.update_task(task)
```

### 2. AI 工具层 (src/tools/dida_tools.py)

**新增 5 个工具类**：

| 工具类 | 命令名称 | 功能 |
|--------|----------|------|
| `AddSubtaskTool` | `add_subtask` | 添加子任务 |
| `CompleteSubtaskTool` | `complete_subtask` | 完成子任务 |
| `DeleteSubtaskTool` | `delete_subtask` | 删除子任务 |
| `ListSubtasksTool` | `list_subtasks` | 列出子任务 |
| `ReorderSubtasksTool` | `reorder_subtasks` | 重新排序 |

### 3. 命令处理器层 (src/handlers/subtask_handlers.py)

**新增 5 个命令**：

| 命令 | 语法 | 示例 |
|------|------|------|
| `/addsubtask` | `/addsubtask 项目ID 任务ID 子任务标题` | `/addsubtask proj123 task456 设计界面` |
| `/completesubtask` | `/completesubtask 项目ID 任务ID 子任务ID` | `/completesubtask proj123 task456 sub789` |
| `/deletesubtask` | `/deletesubtask 项目ID 任务ID 子任务ID` | `/deletesubtask proj123 task456 sub789` |
| `/listsubtasks` | `/listsubtasks 项目ID 任务ID` | `/listsubtasks proj123 task456` |
| `/reordersubtasks` | `/reordersubtasks 项目ID 任务ID ID1:序号1 ID2:序号2` | `/reordersubtasks proj123 task456 s1:10 s2:20` |

### 4. 格式化层增强 (src/utils/formatter.py)

**新增格式化函数**：

```python
def format_subtask_list(task: Task) -> str:
    """格式化显示子任务列表

    📋 项目开发计划 (进度: 2/5 完成, 40%)
    ├─ ☐ 需求分析
    ├─ ☑️ 系统设计 (已完成)
    ├─ ☐ 编码实现
    └─ ☐ 测试部署
    """

def format_subtask_progress(items: List[Dict]) -> str:
    """格式化进度条
    📊 进度: 3/7 完成 (42.9%)
    ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 42.9%
    """
```

## 🔄 核心操作流程

### 添加子任务
```
用户输入 → 解析参数 → 调用 API → 更新任务 → 返回结果
```

### 完成子任务
```
用户输入 → 解析参数 → 查找子任务 → 更新状态 → 添加完成时间 → 返回结果
```

### 删除子任务
```
用户输入 → 二次确认 → 从数组移除 → 更新任务 → 返回结果
```

## 📊 进度计算公式

```python
def calculate_progress(items):
    total = len(items)
    completed = sum(1 for item in items if item.get("status") == 1)
    progress = (completed / total * 100) if total > 0 else 0
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "progress_percent": round(progress, 1)
    }
```

## ⚠️ 重要注意事项

### ✅ 正确做法
1. **始终包含完整的 items 数组** - 更新时必须包含所有子任务
2. **新增子任务不指定 id** - 系统自动生成
3. **使用间隔排序值** - 如 10, 20, 30 便于后续插入
4. **完成时设置 completedTime** - 仅 status=1 时

### ❌ 错误做法
1. **不要单独操作子任务** - 子任务不是独立对象
2. **不要忽略必需字段** - 更新时必须提供 id 和 projectId
3. **不要尝试修改 childIds** - 这是只读字段
4. **不要删除父任务后期望保留子任务** - 会同时删除

## 🧪 测试策略

### 必须测试的场景
1. ✅ 创建带子任务的任务
2. ✅ 添加新子任务到现有任务
3. ✅ 完成子任务（状态更新 + 完成时间）
4. ✅ 删除子任务
5. ✅ 重新排序子任务
6. ✅ 进度计算正确性
7. ✅ 错误处理（任务不存在、无权限等）

### 测试命令
```bash
# 1. 创建测试任务
curl -X POST "https://api.dida365.com/open/v1/task" \
  -H "Authorization: Bearer $DIDA_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "测试任务", "projectId": "YOUR_PROJECT_ID"}'

# 2. 添加子任务
# (使用新的 add_subtask_to_task 方法)

# 3. 完成子任务
# (使用新的 complete_subtask 方法)
```

## 🚀 实施时间线

| 阶段 | 任务 | 时间 | 优先级 |
|------|------|------|--------|
| 1 | DidaClient 增强 (5 个方法) | 2h | 高 |
| 2 | AI 工具开发 (5 个工具类) | 2h | 高 |
| 3 | 格式化函数开发 | 1h | 高 |
| 4 | 命令处理器开发 | 2h | 高 |
| 5 | 集成与测试 | 2h | 高 |
| **总计** | | **9h** | |

## 📚 相关文档

- **API 文档**：`docs/API/subtasks.md` - 完整的子任务 API 说明
- **详细设计**：`docs/design/subtask_implementation_plan.md` - 完整的技术设计文档
- **测试记录**：`sub_task.md` - 之前 API 测试的详细记录

## 🎯 成功标准

实施完成后，应该能够：

- [x] 通过命令行添加/完成/删除子任务
- [x] 通过 AI 助手进行自然语言操作
- [x] 实时查看子任务进度
- [x] 重新排序子任务
- [x] 所有操作都有清晰的反馈

## 💡 下一步

现在我们可以开始实施：

1. **立即开始**：按照实施计划开发 API 层增强
2. **逐步推进**：完成一个阶段后进行测试
3. **持续集成**：每个组件完成后立即集成测试

---

**快速参考结束**

详细技术规范请参考：`docs/design/subtask_implementation_plan.md`
