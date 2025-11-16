# 番茄钟API文档

## 概述

番茄钟API提供完整的番茄钟功能，包括启动、暂停、继续、完成和停止番茄钟。这些API与滴答清单Web端使用相同的认证机制，需要有效的用户会话。

## 认证

番茄钟API使用Cookie-based认证，需要以下两个令牌：
- `auth_token` (t cookie): 用户会话令牌
- `csrf_token` (_csrf_token cookie): CSRF防护令牌

从 `.env` 文件中获取：
```python
import os
from dotenv import load_dotenv

load_dotenv()
auth_token = os.getenv('t')
csrf_token = os.getenv('_csrf_token')
```

## 核心类和方法

### PomodoroService

番茄钟服务的主要类，提供所有番茄钟操作功能。

#### 主要方法

##### `start_focus(auth_token, csrf_token, **kwargs)` - 启动番茄钟

启动一个新的番茄钟会话。

**参数：**
- `auth_token` (str): 认证令牌
- `csrf_token` (str): CSRF令牌
- `duration` (int): 持续时间（分钟），默认25
- `auto_pomo_left` (int): 自动番茄钟剩余次数，默认5
- `pomo_count` (int): 番茄钟计数，默认1
- `manual` (bool): 手动模式，默认True
- `note` (str): 备注信息
- `focus_on_id` (str): 关联任务ID
- `focus_on_type` (int): 关联任务类型
- `focus_on_title` (str): 关联任务标题

**返回：**
```python
{
    'point': 1763290520633,
    'current': {
        'id': 'gz03ps8FseSiOcdX19a8c4e1',
        'type': 0,
        'status': 0,  # 0=运行中, 1=暂停中, 2=已完成, 3=已停止
        'valid': True,
        'exited': False,
        'firstId': 'gz03ps8FseSiOcdX19a8c4e1',
        'duration': 25,
        'startTime': '2025-11-16T10:55:19.774+0000',
        'endTime': '2025-11-16T11:18:07.353+0000',
        'autoPomoLeft': 5,
        'pomoCount': 1,
        'focusTasks': [{'id': '', 'title': 'Python测试任务', 'startTime': '2025-11-16T10:55:19.774+0000'}]
    }
}
```

##### `pause_focus(auth_token, csrf_token, **kwargs)` - 暂停番茄钟

暂停当前运行的番茄钟。

**参数：**
- `auth_token` (str): 认证令牌
- `csrf_token` (str): CSRF令牌
- `manual` (bool): 手动模式
- `note` (str): 备注信息
- `focus_on_type` (int): 关联任务类型
- `focus_on_title` (str): 关联任务标题

##### `continue_focus(auth_token, csrf_token, **kwargs)` - 继续番茄钟

继续已暂停的番茄钟。

**参数：**
- 同暂停方法

##### `finish_focus(auth_token, csrf_token, **kwargs)` - 完成番茄钟

正常完成番茄钟（记录为成功完成）。

**参数：**
- 同暂停方法

##### `stop_focus(auth_token, csrf_token, **kwargs)` - 停止番茄钟

强制停止番茄钟（用于提前结束）。

**参数：**
- `include_exit` (bool): 是否发送exit操作，默认True

##### `query_focus_state(auth_token, csrf_token, **kwargs)` - 查询当前状态

获取当前番茄钟的状态，不执行任何操作。

**返回：**
- 当前活跃番茄钟的完整状态信息

## 使用示例

### 基本用法

```python
import asyncio
from src.services.pomodoro_service import pomodoro_service

async def pomodoro_example():
    # 获取认证令牌
    auth_token = "your_auth_token"
    csrf_token = "your_csrf_token"

    # 1. 启动番茄钟
    result = await pomodoro_service.start_focus(
        auth_token, csrf_token,
        duration=25,
        note="学习Python",
        focus_on_title="编程学习"
    )
    print(f"番茄钟启动: {result['current']['id']}")

    # 2. 暂停番茄钟
    await asyncio.sleep(10)  # 工作10秒
    result = await pomodoro_service.pause_focus(
        auth_token, csrf_token,
        note="休息一下"
    )
    print(f"番茄钟状态: {result['current']['status']}")

    # 3. 停止番茄钟
    result = await pomodoro_service.stop_focus(
        auth_token, csrf_token,
        note="提前结束"
    )
    print(f"番茄钟已停止")

# 运行示例
asyncio.run(pomodoro_example())
```

### 与任务关联

```python
# 启动与特定任务关联的番茄钟
result = await pomodoro_service.start_focus(
    auth_token, csrf_token,
    duration=45,  # 45分钟深度工作
    note="写论文",
    focus_on_id="task_12345",  # 滴答清单任务ID
    focus_on_title="写论文第三章"
)
```

### 状态检查

```python
# 检查当前是否有活跃番茄钟
state = pomodoro_service.get_focus_state_snapshot()

if state.focus_id:
    print(f"当前番茄钟: {state.focus_id}")
    print(f"状态: {state.status}")
    print(f"关联任务: {state.focus_on_title}")
else:
    print("当前无活跃番茄钟")
```

## 状态码说明

| 状态码 | 说明 |
|--------|------|
| 0 | 运行中 |
| 1 | 暂停中 |
| 2 | 已完成 |
| 3 | 已停止 |

## 错误处理

常见错误及其解决方法：

### 1. 认证失败
```
{'error': 'HTTP 401', 'text': 'Unauthorized'}
```
**解决：** 检查认证令牌是否有效，重新登录获取新的cookie。

### 2. 无活跃番茄钟
```
{'error': 'no_active_focus', 'message': '当前没有正在运行的番茄钟'}
```
**解决：** 先启动番茄钟才能进行暂停/继续操作。

### 3. API端点错误
```
{'error': 'HTTP 404', 'text': 'Not Found'}
```
**解决：** 检查API端点URL是否正确。

## 注意事项

1. **会话管理**：番茄钟服务会自动维护本地状态，包括focus_id、last_point等
2. **指针同步**：每次操作都会更新同步指针，确保状态一致性
3. **时间计算**：所有时间都使用UTC格式，自动处理时区转换
4. **资源清理**：使用完毕后调用 `pomodoro_service.close()` 清理连接

## 集成到DidaBot

番茄钟功能可以与DidaBot的任务管理功能完美集成：

1. **智能番茄钟**：AI根据任务自动建议番茄钟时长
2. **任务关联**：自动将番茄钟与滴答清单任务关联
3. **进度跟踪**：记录每个任务的番茄钟使用情况
4. **智能提醒**：基于番茄钟状态提供智能提醒

## 相关文件

- `src/services/pomodoro_service.py` - 番茄钟核心服务
- `src/models/pomodoro_models.py` - 数据模型定义
- `src/core/pomodoro_urls.py` - API端点配置
- `src/utils/id_utils.py` - ID生成工具