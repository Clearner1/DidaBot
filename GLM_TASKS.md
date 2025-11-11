# GLM 开发任务说明文档

**项目**: Telegram Dida Bot - 基础功能实现
**开发**: GLM 负责实现
**协作**: Claude 已提供框架，GLM 完成细节实现

---

## 📋 任务清单

### 一、完成 DidaClient 功能

**文件**: `src/dida_client.py`

当前状态：
- ✅ `get_projects()` - 已实现
- ✅ `get_tasks()` - 已实现
- ⏳ `create_task()` - 待实现
- ⏳ `update_task()` - 待实现
- ⏳ `complete_task()` - 待实现
- ⏳ `delete_task()` - 待实现

**需要实现的函数**：

#### 1.1 `create_task(task: Task) -> Task`
```python
"""
创建新任务

Args:
    task: 任务对象，必须包含 title 和 project_id

Returns:
    创建后的任务对象，包含服务器生成的 id

使用示例:
    new_task = Task(
        title="买菜",
        project_id="proj123",
        content="购买晚餐食材",
        priority=3
    )
    created = await client.create_task(new_task)
    print(f"任务创建成功: {created.id}")
"""
```

**实现要点**：
- POST 请求到 `/open/v1/task`
- 请求体只需要发送必要字段（参考 API 文档）
- 响应解析为 Task 对象
- 错误处理：网络错误、400错误、权限错误

#### 1.2 `update_task(task: Task) -> Task`
```python
"""
更新任务

Args:
    task: 任务对象，必须包含 id 和 project_id

Returns:
    更新后的任务对象

使用示例:
    task.title = "更新后的标题"
    task.priority = 5
    updated = await client.update_task(task)
"""
```

**实现要点**：
- POST 请求到 `/open/v1/task/{task_id}`
- 请求体必须包含 id 和 project_id
- 只发送需要更新的字段
- 错误处理：404（任务不存在）、403（权限不足）

#### 1.3 `complete_task(project_id: str, task_id: str) -> bool`
```python
"""
标记任务为完成

Args:
    project_id: 项目ID
    task_id: 任务ID

Returns:
    True 如果成功，False 如果失败

注意：滴答清单的任务完成是 POST 到 /open/v1/project/{projectId}/task/{taskId}/complete
"""
```

**实现要点**：
- POST 请求（无请求体）
- 成功返回 200 状态码
- 错误处理：404（任务不存在）、401（未授权）

#### 1.4 `delete_task(project_id: str, task_id: str) -> bool`
```python
"""
删除任务

Args:
    project_id: 项目ID
    task_id: 任务ID

Returns:
    True 如果成功删除

注意：DELETE 请求到 /open/v1/project/{projectId}/task/{taskId}
"""
```

**实现要点**：
- DELETE 请求
- 成功返回 200 或 204
- 错误处理：404（任务不存在）、403（权限不足）

#### 1.5 辅助方法：`_format_datetime_for_api(dt: datetime) -> str`
时间格式化为 API 要求的格式：`yyyy-MM-dd'T'HH:mm:ssZ`

---

### 二、实现 Telegram Bot 主框架

**文件**: `src/bot.py`

#### 2.1 核心功能

创建 Bot 应用，配置所有的命令处理器：

```python
from telegram.ext import Application, CommandHandler
from src.config import get_config
from src.dida_client import DidaClient

class DidaBot:
    """Telegram Bot 主类"""

    def __init__(self):
        self.config = get_config()
        self.dida_client = DidaClient(
            access_token=self.config.dida_access_token
        )
        self.application = None

    async def start(self):
        """启动 Bot"""
        # 创建 Application
        self.application = Application.builder().token(self.config.telegram_bot_token).build()

        # 注册命令处理器
        self._register_handlers()

        # 启动 Bot
        await self.application.initialize()
        await self.application.start()

        # 启动轮询
        await self.application.updater.start_polling()

        # 保持运行
        await self.application.updater.idle()

    def _register_handlers(self):
        """注册所有命令处理器"""
        # 从 task_handlers 导入
        from src.handlers.task_handlers import TaskHandlers

        task_handlers = TaskHandlers(self.dida_client)

        # 注册命令
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("projects", self._cmd_projects))
        self.application.add_handler(CommandHandler("addtask", task_handlers.cmd_addtask))
        self.application.add_handler(CommandHandler("listtasks", task_handlers.cmd_listtasks))
        self.application.add_handler(CommandHandler("completetask", task_handlers.cmd_completetask))
        self.application.add_handler(CommandHandler("deletetask", task_handlers.cmd_deletetask))

    async def _cmd_start(self, update, context):
        """/start 命令"""
        # 验证用户权限
        if update.effective_user.id != self.config.bot_admin_user_id:
            await update.message.reply_text("⚠️ 你没有权限使用此机器人")
            return

        await update.message.reply_text(
            "👋 欢迎使用 Dida Bot！\n\n"
            "可用命令：\n"
            "/projects - 查看所有项目\n"
            "/addtask <项目ID> <标题> - 添加任务\n"
            "/listtasks [项目ID] - 列出任务\n"
            "/completetask <项目ID> <任务ID> - 完成任务\n"
            "/deletetask <项目ID> <任务ID> - 删除任务\n"
            "/help - 显示帮助"
        )

    async def _cmd_help(self, update, context):
        """/help 命令"""
        # 验证用户权限
        if update.effective_user.id != self.config.bot_admin_user_id:
            await update.message.reply_text("⚠️ 你没有权限使用此机器人")
            return

        # 显示详细帮助...
        pass

    async def _cmd_projects(self, update, context):
        """/projects 命令 - 列出所有项目"""
        # 验证用户权限
        if update.effective_user.id != self.config.bot_admin_user_id:
            await update.message.reply_text("⚠️ 你没有权限使用此机器人")
            return

        try:
            projects = await self.dida_client.get_projects()

            if not projects:
                await update.message.reply_text("目前没有项目")
                return

            # 构建消息
            message = "📁 项目列表：\n\n"
            for project in projects:
                status = "🗂️ 已关闭" if project.closed else "📂 活跃"
                message += f"• {project.name}\n"
                message += f"  ID: `{project.id}`\n"
                message += f"  状态: {status}\n\n"

            message += "使用 `/addtask 项目ID 标题` 添加任务"

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"❌ 获取项目失败: {str(e)}")
```

#### 2.2 启动脚本

**文件**: `main.py`

```python
import asyncio
import signal
import sys
from src.bot import DidaBot

async def main():
    """主入口"""
    bot = DidaBot()

    # 注册信号处理
    def signal_handler(sig, frame):
        print("\n👋 正在关闭 Bot...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🤖 Dida Bot 正在启动...")
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot 已关闭")
```

---

### 三、实现任务命令处理器

**文件**: `src/handlers/task_handlers.py`

#### 3.1 完整的命令处理器

```python
import re
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from src.dida_client import DidaClient, Task
from src.utils.formatter import format_task_list, format_task


class TaskHandlers:
    """任务命令处理器"""

    def __init__(self, dida_client: DidaClient):
        self.dida_client = dida_client

    async def cmd_addtask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /addtask 命令 - 添加任务

        用法：
        /addtask 项目ID 任务标题
        /addtask 项目ID 任务标题 | 任务描述
        /addtask 项目ID 任务标题 | 描述 | 优先级(0/1/3/5)

        示例：
        /addtask proj123 买菜
        /addtask proj123 完成报告 | 需要包含数据分析和结论 | 5
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 解析参数
        if not context.args:
            await update.message.reply_text(
                "❌ 缺少参数\n\n"
                "用法：\n"
                "/addtask 项目ID 任务标题\n"
                "/addtask 项目ID 任务标题 | 描述\n"
                "/addtask 项目ID 任务标题 | 描述 | 优先级"
            )
            return

        # 解析命令参数
        args_text = ' '.join(context.args)
        parts = args_text.split('|', 2)

        # 解析项目ID和标题
        first_part = parts[0].strip()
        if ' ' not in first_part:
            await update.message.reply_text("❌ 格式错误：需要提供项目ID和标题")
            return

        project_id, title = first_part.split(' ', 1)
        project_id = project_id.strip()
        title = title.strip()

        if not title:
            await update.message.reply_text("❌ 标题不能为空")
            return

        # 可选参数
        content = parts[1].strip() if len(parts) > 1 else None

        priority = 0
        if len(parts) > 2:
            try:
                priority = int(parts[2].strip())
                if priority not in [0, 1, 3, 5]:
                    await update.message.reply_text("❌ 优先级必须是 0, 1, 3, 或 5")
                    return
            except ValueError:
                await update.message.reply_text("❌ 优先级必须是数字")
                return

        try:
            # 创建任务
            new_task = Task(
                title=title,
                project_id=project_id,
                content=content,
                priority=priority
            )

            created = await self.dida_client.create_task(new_task)

            # 格式化回复
            task_info = format_task(created, project_name=project_id)

            await update.message.reply_text(
                f"✅ 任务创建成功！\n\n{task_info}",
                parse_mode="Markdown"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ 创建任务失败: {str(e)}")

    async def cmd_listtasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /listtasks 命令 - 列出任务

        用法：
        /listtasks          - 列出所有任务
        /listtasks 项目ID   - 列出指定项目的任务
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 可选参数
        project_id = None
        if context.args:
            project_id = context.args[0]

        try:
            # 获取任务
            tasks = await self.dida_client.get_tasks(project_id)

            if not tasks:
                msg = "目前没有任务"
                if project_id:
                    msg += f" 在项目 `{project_id}` 中"
                await update.message.reply_text(msg)
                return

            # 获取项目信息用于显示
            projects = await self.dida_client.get_projects()
            project_map = {p.id: p.name for p in projects}

            # 格式化任务列表
            task_list_text = format_task_list(tasks, project_map)

            # 分页（如果消息太长）
            if len(task_list_text) > 4000:
                # Telegram 消息长度限制为 4096 字符
                chunks = self._split_long_message(task_list_text, 3800)

                await update.message.reply_text(
                    f"📋 任务列表（共 {len(tasks)} 个）:\n"
                    f"第一部分（共 {len(chunks)} 部分）:\n\n{chunks[0]}",
                    parse_mode="Markdown"
                )

                # 发送后续部分
                for i, chunk in enumerate(chunks[1:], 2):
                    await update.message.reply_text(
                        f"第 {i} 部分:\n\n{chunk}",
                        parse_mode="Markdown"
                    )
            else:
                await update.message.reply_text(
                    f"📋 任务列表（共 {len(tasks)} 个）:\n\n{task_list_text}",
                    parse_mode="Markdown"
                )

        except Exception as e:
            await update.message.reply_text(f"❌ 获取任务失败: {str(e)}")

    async def cmd_completetask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /completetask 命令 - 完成任务

        用法：
        /completetask 项目ID 任务ID

        示例：
        /completetask proj123 task456
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 验证参数
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ 需要提供项目ID和任务ID\n\n"
                "用法：/completetask 项目ID 任务ID"
            )
            return

        project_id = context.args[0]
        task_id = context.args[1]

        try:
            success = await self.dida_client.complete_task(project_id, task_id)

            if success:
                await update.message.reply_text("✅ 任务已完成！")
            else:
                await update.message.reply_text("❌ 完成任务失败")

        except Exception as e:
            await update.message.reply_text(f"❌ 完成任务失败: {str(e)}")

    async def cmd_deletetask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /deletetask 命令 - 删除任务

        用法：
        /deletetask 项目ID 任务ID

        示例：
        /deletetask proj123 task456
        """
        # 验证用户权限
        if not await self._check_permission(update):
            return

        # 验证参数
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ 需要提供项目ID和任务ID\n\n"
                "用法：/deletetask 项目ID 任务ID"
            )
            return

        project_id = context.args[0]
        task_id = context.args[1]

        try:
            success = await self.dida_client.delete_task(project_id, task_id)

            if success:
                await update.message.reply_text("✅ 任务已删除！")
            else:
                await update.message.reply_text("❌ 删除任务失败")

        except Exception as e:
            await update.message.reply_text(f"❌ 删除任务失败: {str(e)}")

    # ===== 辅助方法 =====

    async def _check_permission(self, update: Update) -> bool:
        """检查用户权限"""
        from src.config import get_config
        config = get_config()

        if update.effective_user.id != config.bot_admin_user_id:
            await update.message.reply_text("⚠️ 你没有权限使用此机器人")
            return False
        return True

    def _split_long_message(self, text: str, max_length: int = 3800) -> list[str]:
        """分割长消息"""
        lines = text.split('\n')
        chunks = []
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n' + line
                else:
                    current_chunk = line

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

```

---

### 四、实现消息格式化工具

**文件**: `src/utils/formatter.py`

```python
from typing import Dict, List
from src.dida_client import Task, Project


def format_task(task: Task, project_name: str = "未知项目") -> str:
    """
    格式化单个任务显示

    Args:
        task: 任务对象
        project_name: 项目名称（可选）

    Returns:
        格式化后的字符串
    """
    # 优先级图标
    priority_icons = {
        0: "⚪",
        1: "🔵",
        3: "🟡",
        5: "🔴"
    }
    priority_text = {
        0: "无",
        1: "低",
        3: "中",
        5: "高"
    }

    # 状态图标
    status_icon = "✅" if task.status == 2 else "⏳"

    # 构建消息
    lines = []
    lines.append(f"{status_icon} **{task.title}**")
    lines.append(f"任务ID: `{task.id}`")
    lines.append(f"项目: {project_name}")

    # 优先级
    priority_icon = priority_icons.get(task.priority, "⚪")
    priority_name = priority_text.get(task.priority, "无")
    lines.append(f"优先级: {priority_icon} {priority_name}")

    # 截止日期
    if task.due_date:
        lines.append(f"📅 截止: {task.due_date}")

    # 描述/内容
    if task.desc:
        lines.append(f"\n📝 描述:\n{task.desc}")
    elif task.content:
        lines.append(f"\n📝 内容:\n{task.content}")

    # 子任务（如果有）
    if task.items:
        lines.append(f"\n📌 子任务 ({len(task.items)}个):")
        for item in task.items[:5]:  # 最多显示5个
            item_status = "✅" if item.status == 1 else "⏳"
            lines.append(f"  {item_status} {item.title}")
        if len(task.items) > 5:
            lines.append(f"  ... 还有 {len(task.items) - 5} 个")

    return "\n".join(lines)


def format_task_list(tasks: List[Task], projects: Dict[str, str]) -> str:
    """
    格式化任务列表

    Args:
        tasks: 任务列表
        projects: 项目ID到名称的映射字典

    Returns:
        格式化后的字符串
    """
    if not tasks:
        return "没有任务"

    # 按项目和状态分组
    active_tasks = [t for t in tasks if t.status == 0]
    completed_tasks = [t for t in tasks if t.status == 2]

    lines = []

    # 活跃任务
    if active_tasks:
        lines.append(f"**活跃任务 ({len(active_tasks)}个):**\n")

        # 按项目分组
        tasks_by_project = {}
        for task in active_tasks:
            project_id = task.project_id or "unknown"
            if project_id not in tasks_by_project:
                tasks_by_project[project_id] = []
            tasks_by_project[project_id].append(task)

        # 显示每个项目的任务
        for project_id, project_tasks in tasks_by_project.items():
            project_name = projects.get(project_id, f"项目 {project_id[:8]}")
            lines.append(f"📁 {project_name}:")

            # 按优先级排序
            project_tasks.sort(key=lambda t: t.priority, reverse=True)

            for task in project_tasks:
                # 优先级图标
                priority_icons = {5: "🔴", 3: "🟡", 1: "🔵", 0: "⚪"}
                priority_icon = priority_icons.get(task.priority, "⚪")

                # 截止信息
                due_info = ""
                if task.due_date:
                    due_info = f"📅 {task.due_date[:10]}"  # 只显示日期

                # 任务行
                task_line = f"  ⏳ {priority_icon} {task.title}"
                if due_info:
                    task_line += f" {due_info}"

                lines.append(task_line)
            lines.append("")

    # 已完成任务（简要显示）
    if completed_tasks:
        lines.append(f"**已完成 ({len(completed_tasks)}个):**\n")

        # 只显示最近完成的5个
        show_completed = completed_tasks[-5:]
        for task in show_completed:
            project_name = projects.get(task.project_id, "未知项目")
            lines.append(f"  ✅ {task.title} ({project_name})")

        if len(completed_tasks) > 5:
            lines.append(f"  ... 还有 {len(completed_tasks) - 5} 个")

    return "\n".join(lines)


def format_project_list(projects: List[Project]) -> str:
    """
    格式化项目列表

    Args:
        projects: 项目列表

    Returns:
        格式化后的字符串
    """
    if not projects:
        return "没有项目"

    lines = []
    lines.append(f"📁 项目列表 ({len(projects)}个):\n")

    # 按名称排序
    projects.sort(key=lambda p: p.name)

    for i, project in enumerate(projects, 1):
        status = "🗂️ 已关闭" if project.closed else "📂 活跃"
        color = project.color or "🎨"

        lines.append(f"{i}. **{project.name}**")
        lines.append(f"   ID: `{project.id}`")
        lines.append(f"   状态: {status}")

        if project.view_mode:
            view_mode_text = {
                "list": "列表视图",
                "kanban": "看板视图",
                "timeline": "时间线视图"
            }.get(project.view_mode, project.view_mode)
            lines.append(f"   视图: {view_mode_text}")

        lines.append("")

    lines.append("使用 `/addtask 项目ID 标题` 添加任务")
    lines.append("使用 `/listtasks 项目ID` 查看项目任务")

    return "\n".join(lines)


def escape_markdown(text: str) -> str:
    """转义 Markdown 特殊字符"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断长文本并添加省略号"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
```

---

### 五、编写测试用例

**文件**: `tests/test_dida_client.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.dida_client import DidaClient, Task, Project
import httpx


@pytest.fixture
def mock_client():
    """创建模拟的 DidaClient"""
    return DidaClient(access_token="test_token")


@pytest.mark.asyncio
async def test_get_projects_success(mock_client):
    """测试获取项目列表成功"""
    mock_response = AsyncMock()
    mock_response.json.return_value = [
        {"id": "proj1", "name": "项目1", "closed": False},
        {"id": "proj2", "name": "项目2", "closed": False}
    ]
    mock_response.raise_for_status = Mock()

    with patch.object(mock_client.client, 'get', return_value=mock_response):
        projects = await mock_client.get_projects()

        assert len(projects) == 2
        assert projects[0].name == "项目1"
        assert projects[1].name == "项目2"


@pytest.mark.asyncio
async def test_get_tasks_without_project(mock_client):
    """测试获取所有任务"""
    # 模拟项目列表
    mock_response_projects = AsyncMock()
    mock_response_projects.json.return_value = [
        {"id": "proj1", "name": "项目1", "closed": False}
    ]

    # 模拟任务列表
    mock_response_tasks = AsyncMock()
    mock_response_tasks.json.return_value = {
        "project": {"id": "proj1", "name": "项目1"},
        "tasks": [
            {
                "id": "task1",
                "title": "任务1",
                "projectId": "proj1",
                "status": 0
            }
        ],
        "columns": []
    }

    with patch.object(mock_client.client, 'get') as mock_get:
        mock_get.side_effect = [mock_response_projects, mock_response_tasks]

        tasks = await mock_client.get_tasks()

        assert len(tasks) == 1
        assert tasks[0].title == "任务1"
        assert tasks[0].project_id == "proj1"


@pytest.mark.asyncio
async def test_create_task(mock_client):
    """测试创建任务"""
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "id": "new_task_id",
        "title": "新任务",
        "projectId": "proj1",
        "status": 0
    }

    with patch.object(mock_client.client, 'post', return_value=mock_response):
        task = Task(title="新任务", project_id="proj1")
        created = await mock_client.create_task(task)

        assert created.id == "new_task_id"
        assert created.title == "新任务"


@pytest.mark.asyncio
async def test_complete_task(mock_client):
    """测试完成任务"""
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch.object(mock_client.client, 'post', return_value=mock_response):
        result = await mock_client.complete_task("proj1", "task1")
        assert result is True


# 更多测试用例...
```

**文件**: `tests/test_formatter.py`

```python
import pytest
from src.dida_client import Task, Project
from src.utils.formatter import format_task, format_task_list, format_project_list


def test_format_task_single():
    """测试格式化单个任务"""
    task = Task(
        id="task1",
        title="测试任务",
        project_id="proj1",
        priority=3,
        status=0
    )

    result = format_task(task, project_name="测试项目")

    assert "测试任务" in result
    assert "task1" in result
    assert "测试项目" in result


def test_format_task_with_due_date():
    """测试格式化有截止日期的任务"""
    task = Task(
        id="task1",
        title="测试任务",
        project_id="proj1",
        due_date="2024-01-15T10:00:00+0000"
    )

    result = format_task(task)

    assert "截止" in result
    assert "2024-01-15" in result


# 更多测试用例...
```

---

### 六、最终实现检查清单（GLM）

在开始编码前，请确认：

- [ ] 已阅读 `README.md` 了解项目整体
- [ ] 已查看 `src/dida_client.py` 已实现的代码
- [ ] 理解每个待实现函数的要求

完成所有任务后，请进行：

1. **功能测试**
   - [ ] 所有命令都能正确执行
   - [ ] 错误处理正常工作
   - [ ] 权限控制有效

2. **代码质量**
   - [ ] 添加了必要的注释
   - [ ] 遵循 Python PEP 8 规范
   - [ ] 处理了所有可能的异常

3. **集成检查**
   - [ ] 所有模块能正常导入
   - [ ] 主程序能正常启动
   - [ ] 配置读取正确

---

### 七、协作提醒

1. **遇到问题？**
   - 查看 `didaAPI.md` 中的 API 文档
   - 检查已实现的 `get_projects` 和 `get_tasks` 作为示例
   - 询问 Claude 获取帮助

2. **需要 Claude 做什么？**
   - 代码审查
   - 架构建议
   - 复杂逻辑设计

3. **不要修改的部分**
   - `config.py` - Claude 已实现
   - `dida_client.py` 的 Task/Project 模型 - Claude 已实现

---

**祝编码愉快！** 🚀
