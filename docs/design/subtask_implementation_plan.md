# 子任务功能实现方案设计文档

## 文档信息

- **文档版本**: v1.0
- **创建日期**: 2025-11-16
- **最后更新**: 2025-11-16
- **作者**: Claude Code Assistant

---

## 1. 项目概述

基于前期对滴答清单 API 的深入测试和分析，我们已经确定了子任务的正确实现机制（使用 `items` 字段）。本方案将指导在现有 Telegram Bot 项目中完整实现子任务功能。

### 1.1 核心发现

通过实际 API 测试，我们发现：
- ✅ **官方推荐机制**：使用 `items` 数组实现子任务
- ✅ **数据一致性**：子任务与父任务自动同步
- ✅ **完整 CRUD**：支持所有子任务操作
- ❌ **避免使用**：parentId/childIds 机制存在数据一致性问题

### 1.2 项目现状

**已有资源**：
- [x] `src/dida_client.py` - Task 模型已支持 items 字段
- [x] `docs/API/subtasks.md` - 完整的 API 文档
- [x] API 认证凭据（.env 文件）
- [x] 基础的 Telegram Bot 框架

**待开发功能**：
- [ ] 子任务专用 API 客户端方法
- [ ] 子任务 AI 工具
- [ ] 子任务命令处理器
- [ ] 子任务格式化器
- [ ] 用户界面集成

---

## 2. 架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                   Telegram Bot                          │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐    │
│  │  Task Handlers  │    │   Subtask Handlers       │    │
│  │                 │    │                          │    │
│  │ • /addtask      │    │ • /addsubtask            │    │
│  │ • /listtasks    │    │ • /completesubtask       │    │
│  │ • /completetask │    │ • /deletesubtask         │    │
│  │ • /deletetask   │    │ • /listsubtasks          │    │
│  └─────────────────┘    │ • /reordersubtasks       │    │
│         │                └──────────────────────────┘    │
│         │                          │                     │
│         └──────────┬───────────────┘                     │
│                  │                                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │           AI Assistant (Kosong Framework)        │  │
│  │                                                  │  │
│  │  ┌──────────────────┐   ┌────────────────────┐   │  │
│  │  │  Task Tools      │   │  Subtask Tools     │   │  │
│  │  │                  │   │                    │   │  │
│  │  │ • create_task    │   │ • add_subtask      │   │  │
│  │  │ • update_task    │   │ • complete_subtask │   │  │
│  │  │ • delete_task    │   │ • delete_subtask   │   │  │
│  │  │ • get_task       │   │ • list_subtasks    │   │  │
│  │  └──────────────────┘   │ • reorder_subtasks │   │  │
│  │                           └────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
│                             │                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │             DidaClient (API Layer)               │  │
│  │                                                  │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  Task Operations                        │   │  │
│  │  │  • create_task()                        │   │  │
│  │  │  • update_task()                        │   │  │
│  │  │  • delete_task()                        │   │  │
│  │  │  • get_task()                           │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  │                                                  │  │
│  │  ┌──────────────────────────────────────────┐   │  │
│  │  │  Subtask Operations (NEW)                │   │  │
│  │  │  • add_subtask_to_task()                 │   │  │
│  │  │  • complete_subtask()                    │   │  │
│  │  │  • delete_subtask_from_task()            │   │  │
│  │  │  • reorder_subtasks()                    │   │  │
│  │  │  • get_subtasks()                        │   │  │
│  │  └──────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────┘  │
│                             │                           │
└─────────────────────────────┼───────────────────────────┘
                              │
                              ▼
                  ┌──────────────────────┐
                  │  Dida365 Open API   │
                  │                      │
                  │  • /open/v1/task    │
                  │  • GET/POST/DELETE  │
                  └──────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 主要文件 |
|------|------|----------|
| **API 层** | 封装滴答清单 API 调用，处理子任务相关操作 | `src/dida_client.py` |
| **工具层** | 提供 AI 工具接口，支持自然语言交互 | `src/tools/dida_tools.py` |
| **处理器层** | 处理 Telegram 命令，调用工具执行操作 | `src/handlers/subtask_handlers.py` |
| **格式化层** | 格式化输出信息，显示子任务列表和进度 | `src/utils/formatter.py` |

---

## 3. 详细设计方案

### 3.1 API 层增强 (src/dida_client.py)

#### 3.1.1 新增方法列表

```python
class DidaClient:
    # 现有方法...

    async def add_subtask_to_task(
        self,
        project_id: str,
        task_id: str,
        subtask_title: str,
        sort_order: Optional[int] = None
    ) -> Task:
        """向现有任务添加子任务

        Args:
            project_id: 项目ID
            task_id: 任务ID
            subtask_title: 子任务标题
            sort_order: 排序顺序（可选，默认追加到最后）

        Returns:
            更新后的任务对象

        工作流程：
        1. 获取当前任务的完整信息（包括 items）
        2. 解析现有子任务，确定新的 sort_order
        3. 创建新的子任务项（无需指定 id，系统自动生成）
        4. 将新子任务添加到 items 数组
        5. 调用 update_task() 更新任务
        """

    async def complete_subtask(
        self,
        project_id: str,
        task_id: str,
        subtask_id: str
    ) -> Task:
        """标记子任务为完成

        Args:
            project_id: 项目ID
            task_id: 任务ID
            subtask_id: 子任务ID

        Returns:
            更新后的任务对象

        工作流程：
        1. 获取任务当前状态
        2. 查找指定的子任务
        3. 更新子任务 status = 1
        4. 添加 completedTime 字段
        5. 更新任务
        """

    async def delete_subtask_from_task(
        self,
        project_id: str,
        task_id: str,
        subtask_id: str
    ) -> Task:
        """从任务中删除子任务

        Args:
            project_id: 项目ID
            task_id: 任务ID
            subtask_id: 子任务ID

        Returns:
            更新后的任务对象

        工作流程：
        1. 获取任务当前状态
        2. 从 items 数组中移除指定子任务
        3. 更新任务
        """

    async def reorder_subtasks(
        self,
        project_id: str,
        task_id: str,
        subtask_orders: List[Dict[str, str]]
    ) -> Task:
        """重新排序子任务

        Args:
            project_id: 项目ID
            task_id: 任务ID
            subtask_orders: 子任务ID和新的sortOrder列表

        Returns:
            更新后的任务对象

        示例:
            subtask_orders = [
                {"id": "subtask1", "sortOrder": 10},
                {"id": "subtask2", "sortOrder": 20}
            ]
        """

    async def get_subtasks(
        self,
        project_id: str,
        task_id: str
    ) -> List[Dict]:
        """获取任务的所有子任务

        Args:
            project_id: 项目ID
            task_id: 任务ID

        Returns:
            子任务列表（按 sortOrder 排序）

        注意:
            不直接调用 API，通过 get_task() 提取 items
        """

    def calculate_subtask_progress(self, task: Task) -> Dict:
        """计算子任务完成进度

        Args:
            task: 任务对象

        Returns:
            包含 total, completed, pending, progress_percent 的字典
        """
```

#### 3.1.2 实施细节

**关键实现要点**：

1. **add_subtask_to_task**：
   - 必须先获取完整任务信息
   - 新增子任务时**不指定 id**（系统自动生成）
   - 自动计算 sort_order（使用间隔值如 10, 20, 30）
   - 必须传递完整的 items 数组

2. **complete_subtask**：
   - 需要添加 `completedTime` 字段（ISO 8601 格式）
   - 仅当 status = 1 时设置 completedTime

3. **delete_subtask_from_task**：
   - 使用数组过滤而非直接删除
   - 保持其他子任务不变

4. **reorder_subtasks**：
   - 接受 {id, sortOrder} 列表
   - 更新整个 items 数组

### 3.2 工具层增强 (src/tools/dida_tools.py)

#### 3.2.1 新增工具类

```python
# 子任务相关参数模型
class AddSubtaskParams(BaseModel):
    """添加子任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""
    subtask_title: str
    """子任务标题"""
    sort_order: Optional[int] = None
    """排序顺序（可选）"""

class CompleteSubtaskParams(BaseModel):
    """完成子任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""
    subtask_id: str
    """子任务ID"""

class DeleteSubtaskParams(BaseModel):
    """删除子任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""
    subtask_id: str
    """子任务ID"""

class ListSubtasksParams(BaseModel):
    """列出子任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""

class ReorderSubtasksParams(BaseModel):
    """重新排序子任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""
    subtask_orders: List[Dict[str, str]]
    """子任务ID和新的排序列表"""

# 子任务工具类
class AddSubtaskTool(CallableTool2[AddSubtaskParams]):
    """添加子任务到指定任务"""
    name: str = "add_subtask"
    description: str = """向现有任务添加新的子任务。

    功能说明：
    - 在已有任务中添加子任务
    - 子任务会显示在父任务下方
    - 自动分配排序号（除非指定）

    使用场景：
    - 用户说"给XX任务添加子任务：XX"
    - 用户说"在XX任务下新建子任务XX"

    参数说明：
    - project_id: 任务所在的项目ID
    - task_id: 父任务的ID
    - subtask_title: 要添加的子任务标题
    - sort_order: 可选的排序号（默认自动分配）
    """
    params: type[AddSubtaskParams] = AddSubtaskParams

class CompleteSubtaskTool(CallableTool2[CompleteSubtaskParams]):
    """完成指定子任务"""
    name: str = "complete_subtask"
    description: str = """标记指定子任务为已完成状态。

    功能说明：
    - 将子任务标记为已完成
    - 记录完成时间
    - 自动计算父任务进度

    使用场景：
    - 用户说"完成XX任务的子任务XX"
    - 用户说"标记XX子任务为完成"

    参数说明：
    - project_id: 任务所在的项目ID
    - task_id: 父任务的ID
    - subtask_id: 要完成的子任务ID
    """
    params: type[CompleteSubtaskParams] = CompleteSubtaskParams

class DeleteSubtaskTool(CallableTool2[DeleteSubtaskParams]):
    """删除子任务"""
    name: str = "delete_subtask"
    description: str = """从任务中删除指定子任务。

    ⚠️ 警告：此操作不可逆！删除后无法恢复子任务。

    功能说明：
    - 永久删除指定子任务
    - 其他子任务不受影响
    - 建议删除前向用户确认

    使用场景：
    - 用户说"删除XX任务的子任务XX"
    - 用户说"把XX子任务删了"

    参数说明：
    - project_id: 任务所在的项目ID
    - task_id: 父任务的ID
    - subtask_id: 要删除的子任务ID
    """
    params: type[DeleteSubtaskParams] = DeleteSubtaskParams

class ListSubtasksTool(CallableTool2[ListSubtasksParams]):
    """列出任务的所有子任务"""
    name: str = "list_subtasks"
    description: str = """获取并显示任务的所有子任务及其状态。

    功能说明：
    - 显示所有子任务列表
    - 标记完成状态
    - 显示完成进度
    - 按排序号显示

    使用场景：
    - 用户说"查看XX任务的子任务"
    - 用户说"显示XX任务下的所有子任务"

    返回信息：
    - 子任务列表（包含ID、标题、状态、排序）
    - 完成进度统计
    - 完成/未完成数量

    参数说明：
    - project_id: 任务所在的项目ID
    - task_id: 父任务的ID
    """
    params: type[ListSubtasksParams] = ListSubtasksParams

class ReorderSubtasksTool(CallableTool2[ReorderSubtasksParams]):
    """重新排序子任务"""
    name: str = "reorder_subtasks"
    description: str = """调整子任务的显示顺序。

    功能说明：
    - 重新排列子任务的顺序
    - 使用 sortOrder 字段控制显示顺序
    - 可以批量调整多个子任务

    使用场景：
    - 用户说"调整XX任务的子任务顺序"
    - 用户说"把子任务XX移到最后"

    参数说明：
    - project_id: 任务所在的项目ID
    - task_id: 父任务的ID
    - subtask_orders: 子任务ID和新的排序列表
      格式：[{"id": "子任务ID", "sortOrder": 10}, ...]
      建议使用间隔值（如10, 20, 30）便于后续插入
    """
    params: type[ReorderSubtasksParams] = ReorderSubtasksParams
```

#### 3.2.2 工具实施要点

**1. 错误处理**：
- 验证任务是否存在
- 验证子任务是否存在（完成/删除时）
- 处理并发更新冲突

**2. 用户友好消息**：
- 返回详细的状态信息
- 显示进度百分比
- 格式化时间显示

**3. 自然语言支持**：
- 支持中文输入
- 智能识别任务和子任务名称
- 上下文感知（根据最近操作的任务）

### 3.3 处理器层新增 (src/handlers/subtask_handlers.py)

#### 3.3.1 命令设计

```python
class SubtaskHandlers:
    """子任务命令处理器"""

    def __init__(self, dida_client: DidaClient):
        self.dida_client = dida_client

    async def cmd_addsubtask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加子任务命令

        用法：
        /addsubtask 项目ID 任务ID 子任务标题
        /addsubtask 项目ID 任务ID 子任务标题 | 排序号

        示例：
        /addsubtask proj123 task456 设计界面
        /addsubtask proj123 task456 完成测试 | 30
        """
        pass

    async def cmd_completesubtask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """完成子任务命令

        用法：
        /completesubtask 项目ID 任务ID 子任务ID

        示例：
        /completesubtask proj123 task456 subtask789
        """
        pass

    async def cmd_deletesubtask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除子任务命令

        用法：
        /deletesubtask 项目ID 任务ID 子任务ID

        示例：
        /deletesubtask proj123 task456 subtask789
        """
        pass

    async def cmd_listsubtasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """列出子任务命令

        用法：
        /listsubtasks 项目ID 任务ID

        示例：
        /listsubtasks proj123 task456
        """
        pass

    async def cmd_reordersubtasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """重新排序子任务命令

        用法：
        /reordersubtasks 项目ID 任务ID 子任务ID1:排序号1 子任务ID2:排序号2 ...

        示例：
        /reordersubtasks proj123 task456 subtask1:10 subtask2:20 subtask3:30
        """
        pass
```

#### 3.3.2 交互流程设计

**添加子任务流程**：
1. 验证用户权限
2. 解析参数（项目ID、任务ID、子任务标题、可选排序号）
3. 调用 add_subtask 工具
4. 显示结果（包含子任务ID和进度）

**完成子任务流程**：
1. 验证用户权限
2. 解析参数（项目ID、任务ID、子任务ID）
3. 调用 complete_subtask 工具
4. 显示结果（包含进度更新）

**删除子任务流程**：
1. 验证用户权限
2. 解析参数（项目ID、任务ID、子任务ID）
3. 二次确认（重要操作）
4. 调用 delete_subtask 工具
5. 显示结果

**列出子任务流程**：
1. 验证用户权限
2. 解析参数（项目ID、任务ID）
3. 调用 list_subtasks 工具
4. 格式化显示（列表 + 进度）

### 3.4 格式化层增强 (src/utils/formatter.py)

#### 3.4.1 新增格式化函数

```python
def format_subtask_list(task: Task, project_name: str = None) -> str:
    """格式化子任务列表显示

    Args:
        task: 任务对象（包含 items 字段）
        project_name: 项目名称（可选）

    Returns:
        格式化的子任务列表文本

    显示格式：
    📋 任务标题 (进度: 2/5 完成, 40%)
    ├─ ☑️ 子任务1 (已完成)
    ├─ ☐ 子任务2
    ├─ ☐ 子任务3
    └─ ☑️ 子任务4 (已完成)
    """

def format_subtask_progress(items: List[Dict]) -> str:
    """格式化子任务进度显示

    Args:
        items: 子任务列表

    Returns:
        格式化的进度文本

    示例：
    📊 进度: 3/7 完成 (42.9%)
    ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 42.9%
    """

def format_single_subtask(subtask: Dict, index: int = None) -> str:
    """格式化单个子任务显示

    Args:
        subtask: 子任务字典
        index: 索引号（可选）

    Returns:
        格式化的子任务文本

    显示格式：
    ☑️ 需求分析 (已完成) [ID: xxx]
    ☐ 系统设计
    """

def format_add_subtask_success(
    parent_task: Task,
    subtask: Dict,
    project_name: str = None
) -> str:
    """格式化添加子任务成功消息

    Args:
        parent_task: 父任务对象
        subtask: 新添加的子任务
        project_name: 项目名称

    Returns:
        格式化的成功消息
    """

def format_complete_subtask_success(
    parent_task: Task,
    subtask: Dict,
    progress: Dict
) -> str:
    """格式化完成子任务成功消息

    Args:
        parent_task: 父任务对象
        subtask: 完成的子任务
        progress: 进度信息

    Returns:
        格式化的成功消息
    """
```

#### 3.4.2 显示规范

**符号约定**：
- `☐` - 未完成子任务
- `☑️` - 已完成子任务
- `├─` - 中间子任务（带分支线）
- `└─` - 最后一个子任务（带结尾线）

**颜色标记**（可选）：
- 🔴 高优先级任务
- 🟡 中优先级任务
- 🟢 低优先级任务

**信息层次**：
1. 任务标题和进度（第一行）
2. 子任务列表（缩进显示）
3. 统计信息（最后一行）

### 3.5 集成配置 (src/bot.py)

#### 3.5.1 注册处理器

```python
from handlers.task_handlers import TaskHandlers
from handlers.subtask_handlers import SubtaskHandlers  # 新增

async def main():
    # 初始化 DidaClient
    dida_client = DidaClient(
        access_token=config.dida_access_token,
        base_url=config.dida_base_url
    )

    # 注册处理器
    application.add_handler(CommandHandler("addtask", TaskHandlers(dida_client).cmd_addtask))
    application.add_handler(CommandHandler("listtasks", TaskHandlers(dida_client).cmd_listtasks))
    application.add_handler(CommandHandler("completetask", TaskHandlers(dida_client).cmd_completetask))
    application.add_handler(CommandHandler("deletetask", TaskHandlers(dida_client).cmd_deletetask))

    # 注册子任务处理器（新增）
    application.add_handler(CommandHandler("addsubtask", SubtaskHandlers(dida_client).cmd_addsubtask))
    application.add_handler(CommandHandler("completesubtask", SubtaskHandlers(dida_client).cmd_completesubtask))
    application.add_handler(CommandHandler("deletesubtask", SubtaskHandlers(dida_client).cmd_deletesubtask))
    application.add_handler(CommandHandler("listsubtasks", SubtaskHandlers(dida_client).cmd_listsubtasks))
    application.add_handler(CommandHandler("reordersubtasks", SubtaskHandlers(dida_client).cmd_reordersubtasks))

    # 注册 AI 工具（新增子任务工具）
    tools = [
        # 现有任务工具...
        CreateTaskTool(dida_client),
        UpdateTaskTool(dida_client),
        DeleteTaskTool(dida_client),

        # 新增子任务工具
        AddSubtaskTool(dida_client),
        CompleteSubtaskTool(dida_client),
        DeleteSubtaskTool(dida_client),
        ListSubtasksTool(dida_client),
        ReorderSubtasksTool(dida_client),
    ]
```

---

## 4. 用户交互设计

### 4.1 命令行界面

**基本命令**：

```bash
# 添加子任务
/addsubtask 项目ID 任务ID 子任务标题

# 完成子任务
/completesubtask 项目ID 任务ID 子任务ID

# 删除子任务
/deletesubtask 项目ID 任务ID 子任务ID

# 列出子任务
/listsubtasks 项目ID 任务ID

# 重新排序
/reordersubtasks 项目ID 任务ID 子任务ID1:10 子任务ID2:20
```

**示例交互**：

```
用户: /addsubtask 6833e03c 项目开发 设计数据库模型

机器人: ✅ 子任务添加成功！

📋 项目开发
📊 进度: 1/4 完成 (25.0%)
├─ ☐ 需求分析
├─ ☑️ 设计数据库模型 (刚刚完成)
├─ ☐ 接口开发
└─ ☐ 测试部署

子任务ID: 64a5c8b9e1a2c3d4e5f67891
```

### 4.2 自然语言交互

**AI 助手支持**：

```
用户: 给"项目开发"任务添加一个子任务叫"部署上线"

AI: 已为"项目开发"任务添加子任务"部署上线"

📋 项目开发
📊 进度: 2/5 完成 (40.0%)
├─ ☐ 需求分析
├─ ☑️ 设计数据库模型
├─ ☐ 接口开发
├─ ☐ 测试调试
└─ ☑️ 部署上线 (刚刚完成)
```

### 4.3 智能提示

**命令补全**：
- 自动补全项目名称
- 自动补全任务标题
- 显示子任务列表供选择

**快捷操作**：
- `!!` - 重复上一步操作
- `!!完成` - 完成最近添加的子任务
- `/l` - 列出最近任务的所有子任务

---

## 5. 数据流设计

### 5.1 添加子任务数据流

```
用户输入 (/addsubtask)
    ↓
SubtaskHandlers.cmd_addsubtask
    ↓
解析参数 (项目ID, 任务ID, 子任务标题)
    ↓
调用 AddSubtaskTool
    ↓
DidaClient.add_subtask_to_task()
    ↓
1. get_task() - 获取当前任务
    ↓
2. 解析现有 items
    ↓
3. 计算新 sort_order
    ↓
4. 创建新子任务项 (不含 id)
    ↓
5. update_task() - 提交更新
    ↓
返回更新后的任务
    ↓
格式化显示 (format_subtask_list)
    ↓
发送响应给用户
```

### 5.2 完成子任务数据流

```
用户输入 (/completesubtask)
    ↓
SubtaskHandlers.cmd_completesubtask
    ↓
解析参数 (项目ID, 任务ID, 子任务ID)
    ↓
调用 CompleteSubtaskTool
    ↓
DidaClient.complete_subtask()
    ↓
1. get_task() - 获取当前任务
    ↓
2. 查找指定子任务
    ↓
3. 更新 status = 1
    ↓
4. 添加 completedTime
    ↓
5. update_task() - 提交更新
    ↓
计算进度 (calculate_subtask_progress)
    ↓
格式化显示 (format_complete_subtask_success)
    ↓
发送响应给用户
```

### 5.3 错误处理流程

```
API 调用失败
    ↓
捕获异常 (HTTPStatusError, Exception)
    ↓
记录错误日志
    ↓
返回用户友好错误消息
    ↓
提示可能的解决方案
```

**常见错误类型**：
- 任务不存在 (404)
- 无权限访问 (403)
- 数据格式错误 (400)
- 网络连接超时

---

## 6. 测试策略

### 6.1 单元测试

**DidaClient 子任务方法测试**：

```python
import pytest
from dida_client import DidaClient

class TestSubtaskOperations:
    @pytest.fixture
    async def client(self):
        async with DidaClient("test_token") as client:
            yield client

    async def test_add_subtask_to_task(self, client):
        """测试添加子任务"""
        # 创建测试任务
        # 添加子任务
        # 验证返回结果

    async def test_complete_subtask(self, client):
        """测试完成子任务"""
        # 创建带子任务的任务
        # 完成其中一个子任务
        # 验证状态更新和进度计算

    async def test_delete_subtask(self, client):
        """测试删除子任务"""
        # 创建带多个子任务的任务
        # 删除一个子任务
        # 验证其他子任务不受影响

    async def test_reorder_subtasks(self, client):
        """测试重新排序"""
        # 创建子任务
        # 调整顺序
        # 验证排序结果
```

**工具测试**：

```python
from tools.dida_tools import AddSubtaskTool

class TestSubtaskTools:
    def test_add_subtask_tool_params(self):
        """测试工具参数验证"""
        # 验证必需参数
        # 验证可选参数
        # 验证参数格式

    async def test_add_subtask_tool_execution(self):
        """测试工具执行"""
        # Mock DidaClient
        # 执行工具
        # 验证返回结果
```

### 6.2 集成测试

**完整用户流程测试**：

```python
class TestSubtaskWorkflow:
    async def test_full_workflow(self):
        """测试完整的子任务工作流"""
        # 1. 创建任务
        # 2. 添加多个子任务
        # 3. 完成部分子任务
        # 4. 重新排序
        # 5. 删除子任务
        # 6. 验证最终状态
```

### 6.3 手动测试场景

**场景 1：项目管理**
- 创建"网站重构"任务
- 添加子任务：需求分析、设计、开发、测试、部署
- 依次完成各阶段
- 查看进度统计

**场景 2：学习计划**
- 创建"Python 学习"任务
- 添加子任务：基础语法、面向对象、库使用、项目实战
- 完成部分学习任务
- 调整学习顺序

**场景 3：错误处理**
- 尝试删除不存在的子任务
- 尝试完成已完成的子任务
- 网络中断时的处理

### 6.4 性能测试

**测试指标**：
- 子任务数量对性能的影响（100+ 子任务）
- 并发操作测试
- API 响应时间

**性能优化**：
- 批量更新减少 API 调用
- 缓存常用任务信息
- 异步并发处理

---

## 7. 实施计划

### 7.1 开发阶段划分

| 阶段 | 任务 | 预计时间 | 依赖关系 |
|------|------|----------|----------|
| **阶段 1** | API 层开发 | 2 小时 | 无 |
| | - 增强 DidaClient | | |
| | - 实现 5 个子任务方法 | | |
| | - 单元测试 | | |
| **阶段 2** | 工具层开发 | 2 小时 | 阶段 1 |
| | - 定义参数模型 | | |
| | - 实现 5 个工具类 | | |
| | - 工具测试 | | |
| **阶段 3** | 格式化层开发 | 1 小时 | 阶段 1 |
| | - 新增格式化函数 | | |
| | - 格式化测试 | | |
| **阶段 4** | 处理器层开发 | 2 小时 | 阶段 1, 2, 3 |
| | - 实现 5 个命令处理器 | | |
| | - 集成测试 | | |
| **阶段 5** | 集成与测试 | 2 小时 | 所有阶段 |
| | - 注册处理器和工具 | | |
| | - 端到端测试 | | |
| | - Bug 修复 | | |
| **总计** | | **9 小时** | |

### 7.2 优先级划分

**高优先级** (必须实现)：
1. `add_subtask` - 添加子任务
2. `complete_subtask` - 完成子任务
3. `list_subtasks` - 列出子任务
4. 基础格式化显示

**中优先级** (重要功能)：
1. `delete_subtask` - 删除子任务
2. `reorder_subtasks` - 重新排序
3. 进度统计显示

**低优先级** (增强体验)：
1. 智能提示
2. 快捷命令
3. 高级格式化

### 7.3 风险评估

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| API 变更 | 高 | 低 | 监控 API 文档更新，保持兼容性 |
| 数据不一致 | 高 | 中 | 充分测试，使用事务性操作 |
| 性能问题 | 中 | 中 | 批量操作，缓存优化 |
| 用户误操作 | 中 | 高 | 二次确认，撤销机制 |

---

## 8. 技术细节

### 8.1 ID 管理

**子任务 ID**：
- 自动生成，无需手动指定
- 格式：24 字符十六进制字符串
- 全局唯一

**父任务关联**：
- 通过 `items` 字段关联
- 无需 parentId 字段
- 数据自动同步

### 8.2 状态管理

**子任务状态**：
```python
class SubtaskStatus:
    PENDING = 0      # 未完成
    COMPLETED = 1    # 已完成
```

**完成时间**：
- 仅 status = 1 时设置
- ISO 8601 格式：`2025-11-16T09:00:00.000+0000`
- UTC 时区

### 8.3 排序机制

**sortOrder 字段**：
- 整数类型
- 不要求连续，但需唯一
- 建议使用间隔值（10, 20, 30）
- 支持负数和零

**排序算法**：
```python
def calculate_sort_order(items: List[Dict]) -> int:
    """计算新的 sortOrder"""
    if not items:
        return 10

    existing_orders = [item.get("sortOrder", 0) for item in items]
    max_order = max(existing_orders)

    return max_order + 10
```

### 8.4 数据一致性

**更新策略**：
1. 先获取完整任务
2. 本地修改 items
3. 提交完整 items 数组
4. 验证更新结果

**并发控制**：
- 最后写入生效
- 可考虑乐观锁机制
- 冲突时提示用户重试

### 8.5 错误处理

**API 错误处理**：

```python
try:
    result = await client.add_subtask(...)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        raise Exception(f"任务 {task_id} 不存在")
    elif e.response.status_code == 403:
        raise Exception(f"没有权限在项目 {project_id} 中操作")
    elif e.response.status_code == 400:
        raise Exception(f"请求数据格式错误: {e.response.text}")
    else:
        raise Exception(f"API 错误: HTTP {e.response.status_code}")
```

**用户友好消息**：
- 避免暴露技术细节
- 提供解决方案建议
- 支持重试机制

---

## 9. 未来扩展

### 9.1 高级功能

**子任务依赖**：
- 定义子任务之间的依赖关系
- 前置任务未完成时阻塞后续任务
- 自动计算可执行任务

**子任务分配**：
- 指定子任务负责人
- 多用户协作
- 进度通知

**子任务时间管理**：
- 为子任务设置截止时间
- 里程碑管理
- 时间追踪

**子任务附件**：
- 支持文件附件
- 图片、文档链接
- 评论功能

### 9.2 视图增强

**甘特图视图**：
- 子任务时间线显示
- 进度可视化
- 依赖关系图

**看板视图**：
- 按状态列分组显示子任务
- 拖拽式操作
- 状态变更自动化

**日历视图**：
- 子任务截止时间日历显示
- 任务密度可视化
- 时间冲突检测

### 9.3 报告与分析

**进度报告**：
- 自动化进度报告
- 邮件/消息通知
- 里程碑达成统计

**效率分析**：
- 子任务完成速度统计
- 延迟分析
- 效率趋势

**数据导出**：
- 导出为 Excel/CSV
- 自定义报告模板
- 定期自动导出

---

## 10. 总结

### 10.1 核心价值

本实施方案将为项目带来以下价值：

1. **完整的子任务管理**：通过 items 机制提供可靠的子任务功能
2. **自然语言交互**：支持 AI 助手进行智能任务分解和管理
3. **直观的用户界面**：清晰的进度显示和操作反馈
4. **高效的命令支持**：完整的 Telegram 命令行操作
5. **可扩展架构**：为未来功能扩展预留空间

### 10.2 实施要点

1. **严格遵循 API 规范**：使用官方推荐的 items 机制
2. **充分测试**：覆盖所有操作场景和边界情况
3. **用户友好**：提供清晰的错误消息和操作反馈
4. **性能优化**：避免不必要的 API 调用，提高响应速度
5. **代码质量**：保持代码清晰、可维护、可测试

### 10.3 成功标准

实施成功的标准：

- [ ] 所有 5 个子任务操作方法正常工作
- [ ] 命令行界面响应正确
- [ ] AI 工具能够处理自然语言请求
- [ ] 格式化显示清晰易懂
- [ ] 错误处理完善
- [ ] 单元测试覆盖率 > 90%
- [ ] 端到端测试通过
- [ ] 用户文档完整

### 10.4 下一步行动

立即开始实施：

1. **阶段 1**：开发 API 层增强方法
2. **阶段 2**：实现 AI 工具类
3. **阶段 3**：开发命令处理器
4. **阶段 4**：集成测试
5. **阶段 5**：文档完善

预计总开发时间：**9 小时**

---

**文档结束**

本设计文档为子任务功能的完整实现提供了详细的技术方案和指导。遵循本方案，可以确保功能实现的正确性、完整性和可维护性。
