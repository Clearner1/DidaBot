# Telegram Dida Bot

一个基于 Telegram 的滴答清单任务管理机器人，支持通过 Telegram 管理滴答清单任务。

## 功能特性

- ✅ 查看所有项目和项目详情
- ✅ 列出任务（所有任务或指定项目任务）
- ✅ 添加任务（支持标题、描述、优先级）
- ✅ 完成任务
- ✅ 删除任务
- ✅ 任务优先级管理（0:无, 1:低, 3:中, 5:高）
- ✅ 用户权限控制（仅管理员可使用）
- ✅ 友好的消息格式化
- ⏳ AI 智能解析（下一阶段）

## 项目结构

```
tg-dida/
├── src/                          # 主源代码
│   ├── __init__.py
│   ├── bot.py                    # Telegram Bot 主入口（✅ 已实现）
│   ├── config.py                 # 配置管理（✅ 已实现）
│   ├── dida_client.py           # Dida API 客户端（✅ 已实现）
│   ├── handlers/                # 命令处理器
│   │   ├── __init__.py
│   │   ├── task_handlers.py     # 任务命令处理器（✅ 已实现）
│   │   └── project_handlers.py  # 项目命令处理器（✅ 已实现）
│   ├── keyboards/               # Telegram 键盘（预留）
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       └── formatter.py         # 消息格式化工具（✅ 已实现）
├── tests/                       # 测试（预留）
├── .env.example                # 环境变量模板（✅ 已实现）
├── main.py                     # 启动脚本（✅ 已实现）
├── pyproject.toml              # 项目配置（✅ 已实现）
├── requirements.txt            # 依赖列表（✅ 已实现）
└── README.md                   # 项目说明（✅ 已实现）
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd tg-dida

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BOT_ADMIN_USER_ID=your_telegram_user_id

# 滴答清单（Dida365）
DIDA_ACCESS_TOKEN=your_dida_personal_token_here

# 如何获取这些token请参考下方说明
```

### 3. 配置说明

#### 获取 Telegram Bot Token

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 命令创建新机器人
3. 按照提示设置机器人名称和用户名
4. 保存 BotFather 提供的 `token`

#### 获取 Dida Access Token

1. 访问 [滴答清单开放平台](https://developer.dida365.com/)
2. 登录并进入"个人 token"页面
3. 生成新的个人 token（无需 OAuth）
4. 复制并保存 token

#### 获取 Telegram User ID

1. 在 Telegram 中搜索 `@userinfobot`
2. 发送任意消息给机器人
3. 机器人会返回你的用户信息，其中包含 `Id`（用户 ID）
4. 复制这个 ID

### 4. 运行机器人

```bash
# 启动机器人
python main.py

# 或使用 pip 安装后运行
pip install -e .
tg-dida
```

启动成功后，你会在控制台看到：
```
🤖 滴答清单 Bot 正在启动...
Bot 初始化成功
命令处理器注册完成
Bot 已启动，开始处理消息...
```

## 使用示例

### 基础操作

```bash
# 查看所有项目
/projects

# 查看帮助
/help

# 查看所有任务
/listtasks

# 查看特定项目的任务
/listtasks proj123
```

### 任务管理

```bash
# 添加简单任务
/addtask proj123 买菜

# 添加带描述的任务
/addtask proj123 完成报告 | 需要包含数据分析和结论

# 添加高优先级任务
/addtask proj123 紧急会议 | 下午3点与客户开会 | 5

# 完成任务
/completetask proj123 task456

# 删除任务
/deletetask proj123 task456
```

### 项目管理

```bash
# 查看项目详情
/project_info proj123
```

### 优先级说明

- `0` - 无优先级 ⚪
- `1` - 低优先级 🔵
- `3` - 中优先级 🟡
- `5` - 高优先级 🔴

### 消息格式示例

Bot 会返回格式化的任务信息：

```
📋 任务列表（共 3 个）：

**活跃任务 (2个):**

📁 工作:
  ⏳ 🔴 完成项目报告 📅 11-15
  ⏳ 🟡 团队会议

📁 个人:
  ⏳ ⚪ 买菜

**已完成 (1个):**
  ✅ 代码审查 (工作)
```

## 核心功能实现状态

### 已完成（✅）

1. **项目初始化**
   - ✅ 项目目录结构创建
   - ✅ 配置文件（`config.py`）
   - ✅ 环境模板（`.env.example`）
   - ✅ 项目依赖（`requirements.txt`, `pyproject.toml`）

2. **DidaClient API 客户端**
   - ✅ `Task` 和 `Project` 数据模型
   - ✅ 获取所有项目列表（`get_projects()`）
   - ✅ 获取单个项目（`get_project()`）
   - ✅ 获取任务列表（`get_tasks()`）
   - ✅ 获取单个任务（`get_task()`）
   - ✅ 创建任务（`create_task()`）
   - ✅ 更新任务（`update_task()`）
   - ✅ 完成任务（`complete_task()`）
   - ✅ 删除任务（`delete_task()`）

3. **Telegram Bot 框架**
   - ✅ Bot 主入口（`bot.py`）
   - ✅ 启动脚本（`main.py`）
   - ✅ 基础命令（`/start`, `/help`）
   - ✅ 权限控制（仅管理员可使用）

4. **命令处理器**
   - ✅ 任务命令处理器（`task_handlers.py`）
   - ✅ 项目命令处理器（`project_handlers.py`）
   - ✅ 完整的错误处理和用户反馈

5. **工具函数**
   - ✅ 消息格式化工具（`formatter.py`）
   - ✅ MarkdownV2 格式支持
   - ✅ 长消息分页处理

### 下一阶段（⏭️）

- [ ] 测试用例编写（`tests/`）
- [ ] AI 智能解析集成（`kosong` 框架）
- [ ] 自然语言任务创建
- [ ] 对话式任务管理
- [ ] 内联键盘支持

## 接口说明

### DidaClient API

```python
from src.dida_client import DidaClient, Task, Project

# 初始化客户端
client = DidaClient(
    access_token="your_dida_token"
)

# 获取所有项目
projects = await client.get_projects()
# projects: List[Project]

# 获取所有任务
tasks = await client.get_tasks()
# tasks: List[Task]

# 获取指定项目的任务
tasks = await client.get_tasks(project_id="project_id_here")
# tasks: List[Task]
# 每个任务都会有 project_id 字段
```

### 数据模型

#### Task

```python
class Task(BaseModel):
    id: Optional[str]              # 任务ID
    project_id: Optional[str]      # 项目ID（自动填充）
    title: str                     # 任务标题
    content: Optional[str]         # 任务内容
    desc: Optional[str]            # 任务描述
    is_all_day: bool               # 是否全天任务
    start_date: Optional[str]      # 开始时间（ISO格式）
    due_date: Optional[str]        # 截止时间（ISO格式）
    time_zone: Optional[str]       # 时区
    priority: int                  # 优先级：0=无, 1=低, 3=中, 5=高
    status: int                    # 状态：0=未完成, 2=已完成
    sort_order: Optional[int]      # 排序值
    completed_time: Optional[str]  # 完成时间
```

#### Project

```python
class Project(BaseModel):
    id: Optional[str]         # 项目ID
    name: str                 # 项目名称
    color: Optional[str]      # 颜色（十六进制）
    closed: bool              # 是否已关闭
    group_id: Optional[str]   # 项目组ID
    sort_order: Optional[int] # 排序值
    view_mode: Optional[str]  # 视图模式: "list", "kanban", "timeline"
    kind: Optional[str]       # 类型: "TASK", "NOTE"
```

## 协作开发说明

### Claude 负责部分

已由 Claude 实现：
- 项目结构和基础配置
- `DidaClient` 核心框架
- 获取任务和项目列表功能

### GLM 负责部分

GLM 需要实现：
1. 完成 DidaClient 的剩余方法
2. 实现 Telegram Bot 框架
3. 实现所有命令处理器
4. 编写测试用例
5. 集成所有模块

### 开发顺序建议

1. **第一阶段（基础功能）**
   - GLM 完成 DidaClient 的所有 CRUD 方法
   - GLM 实现 Telegram Bot 基础框架
   - GLM 实现基本命令处理器

2. **第二阶段（集成测试）**
   - 集成所有模块
   - 编写测试用例
   - 手动测试所有功能

3. **第三阶段（AI功能）**
   - 集成 kosong 框架
   - 实现自然语言处理

## 注意事项

1. **个人 Token 安全**
   - 不要将 `.env` 文件提交到版本控制
   - 使用强个人 token
   - Bot 仅对 `BOT_ADMIN_USER_ID` 用户响应（安全限制）

2. **API 限制**
   - 滴答清单 API 有调用频率限制
   - 本机器人按需调用，不会频繁请求

3. **错误处理**
   - 已实现基本错误处理
   - 调用失败时会返回错误信息

## 项目状态

**当前版本**: v0.1.0（基础功能开发中）

**开发进度**: 50% - 核心框架已完成，待实现完整 Bot 功能

**下一个版本**: v0.2.0 - 完整 Bot 功能

---

## 贡献说明

本仓库由 Claude 和 GLM 协作开发：

- **Claude**: 负责架构设计、核心框架、代码审查
- **GLM**: 负责功能实现、集成测试、Bug修复

**协作方式**：
1. Claude 提供详细设计方案
2. CLM 根据设计编码实现
3. 双方进行代码审查
4. 共同测试和优化

---

## 许可证

本项目仅供学习和个人使用。滴答清单 API 使用需遵守其服务条款。
