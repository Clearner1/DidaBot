# ai_assistant.py 改进方案
document: ai_assistant_alert.md
created: 2025-11-15 15:31:50

## 方案概述

本方案基于neu-translator框架的设计理念，重构tg-dida中的工具调用追踪机制。核心是从手动维护的`pending_tool_calls`字典，改为基于消息历史的自动推导，解决状态不一致的问题。

## neu-translator框架的核心设计

### 1. 状态自动推导（而非手动维护）

neu的核心创新：不存储待处理列表，每次调用时从完整历史推导。

```typescript
// neu-translator/packages/core/src/agent.ts:140-165
private async getUnprocessedToolCalls(): Promise<ToolCallPart[]> {
    const messages = this.context.getMessages();
    const parts: Record<string, ToolCallPart> = {};

    // 收集所有工具调用
    for (const m of messages) {
        if (m.role === "assistant" && Array.isArray(m.content)) {
            for (const part of m.content) {
                if (part.type === "tool-call") {
                    if (!parts[part.toolCallId]) {
                        parts[part.toolCallId] = part;
                    }
                }
            }
        }

        // 移除已有结果的工具调用
        if (m.role === "tool") {
            for (const part of m.content) {
                if (part.type === "tool-result") {
                    delete parts[part.toolCallId];
                }
            }
        }
    }

    return Object.values(parts);
}
```

**优势**:
- ✅ **幂等**: 多次调用结果相同
- ✅ **容错**: 出错后重新计算即可恢复
- ✅ **简单**: 无需考虑状态同步
- ✅ **无记忆污染**: 永远与历史保持一致

### 2. Actor控制流模式

```typescript
// neu清晰的actor转换逻辑
if (lastMessage.role === "assistant") {
    actor = "user";  // AI回复后，等待用户
}
if (toolCalls.length > 0) {
    actor = "agent";  // 有工具调用，继续处理
}
```

### 3. Tool定义与执行分离

```typescript
// 定义（Schema + 描述）
this.toolDefs = {
    translate: translateTool,  // Zod schema
    read: readTool,
}

// 执行器（纯函数）
this.toolExecutors = {
    translate: translateExecutor,
    read: readExecutor,
}
```

### 4. 迭代器模式（非循环）

```typescript
// 内部返回状态
public async next(): Promise<{ actor, unprocessedToolCalls }>

// 外部控制流程
while (actor !== "user") {
    const { actor } = await agent.next();
}
```

## tg-dida当前实现的问题

### 当前代码（src/ai_assistant.py）

```python
class AIAssistant:
    def __init__(self, ...):
        # 手动维护pending状态
        self.pending_tool_calls = {}  # {tool_call_id: tool_call}

    async def chat(self, user_message, history=None):
        # ...

        # 多轮循环
        iteration = 0
        while iteration < self.max_iterations:
            result = await kosong.step(...)

            # 手动追踪pending
            for tool_call in result.message.tool_calls or []:
                self.pending_tool_calls[tool_call.id] = tool_call

            # 手动移除pending
            for tool_result in tool_results:
                if tool_result.tool_call_id in self.pending_tool_calls:
                    del self.pending_tool_calls[tool_result.tool_call_id]

            iteration += 1
            if tool_results:
                continue
```

### 三大痛点

1. **状态不一致风险**
   - 如果工具执行失败，pending_tool_calls残留
   - 如果中途异常退出，状态无法恢复
   - 多轮循环逻辑复杂，容易出错

2. **记忆污染**
   - 滑动窗口裁剪历史但不清除pending状态
   - 可能导致工具调用和结果不匹配

3. **难以调试**
   - pending状态无法实时查看（私有字典）
   - 只能加日志，无法从消息历史推导

## 改进方案

### Phase 1: 核心重构（必须做）

用自动推导替代pending字典。

**修改src/ai_assistant.py**

```python
# 第1步：删除pending_tool_calls（约第40行）
# self.pending_tool_calls = {}  # DELETE THIS LINE

# 第2步：添加推导函数（约第200行，chat方法之前）
def get_unprocessed_tools(self, messages: List[Message]) -> Dict[str, ToolCall]:
    """
    基于消息历史自动推导未处理工具调用。
    借鉴neu的getUnprocessedToolCalls()设计。

    Args:
        messages: 完整的消息历史

    Returns:
        未处理的工具调用映射 {tool_call_id: tool_call}
    """
    tool_calls: Dict[str, ToolCall] = {}
    tool_results: Set[str] = set()

    for msg in messages:
        # 收集所有工具调用
        if msg.role == "assistant" and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls[tc.id] = tc

        # 收集所有工具结果ID
        if msg.role == "tool" and hasattr(msg, 'tool_call_id') and msg.tool_call_id:
            tool_results.add(msg.tool_call_id)

    # 移除已有结果的工具调用
    for tool_call_id in tool_results:
        tool_calls.pop(tool_call_id, None)

    return tool_calls

# 第3步：重构chat方法中的循环（约第260-340行）
async def chat(self, user_message: str, ...):
    # ...初始化messages...

    # 删除: self.pending_tool_calls.clear()

    iteration = 0
    while iteration < self.max_iterations:
        # 自动推导未处理工具（替代手动pending追踪）
        unprocessed_tools_before = self.get_unprocessed_tools(messages)

        logger.info(f"\n{'='*60}")
        logger.info(f"AI调用第 {iteration + 1} 轮")
        logger.info(f"当前未处理工具数: {len(unprocessed_tools_before)}")

        # 调用LLM
        result: StepResult = await kosong.step(
            chat_provider=self.chat_provider,
            system_prompt=self.system_prompt,
            toolset=self.toolset,
            history=messages,
        )

        # 添加AI消息到历史
        if hasattr(result, 'message') and result.message:
            messages.append(result.message)

            # 记录工具调用（但不手动pending）
            if result.message.tool_calls:
                for tool_call in result.message.tool_calls:
                    logger.info(f"[工具调用] {tool_call.id}: {tool_call.name}")

        # 获取工具结果
        if hasattr(result, 'tool_results') and callable(result.tool_results):
            tool_results = await result.tool_results()

            if tool_results:
                # 处理工具结果到messages（kosong会自动添加）
                logger.info(f"[工具结果] 成功处理 {len(tool_results)} 个工具")

                # 验证工具一致性（可选但推荐）
                unprocessed_after = self.get_unprocessed_tools(messages)
                if unprocessed_after:
                    logger.warning(f"仍有 {len(unprocessed_after)} 个工具未处理")

        iteration += 1

        # 决定下一轮行为（模仿neu的actor逻辑）
        current_unprocessed = self.get_unprocessed_tools(messages)
        if not current_unprocessed and iteration > 0:
            logger.info("[状态检查] 没有未处理工具，准备退出")
            break

    # ...后续处理...
```

**预估改动量**：删除5行，添加40行，修改20行。约30分钟完成。

---

### Phase 2: 增强错误处理（推荐做）

添加工具一致性验证，防止记忆污染。

```python
def validate_tool_consistency(self, messages: List[Message]) -> bool:
    """
    验证工具调用和结果的一致性，检测孤立结果或调用。

    Args:
        messages: 消息历史

    Returns:
        True: 一致，False: 存在问题
    """
    tool_calls: Set[str] = set()
    tool_results: Set[str] = set()

    for msg in messages:
        if msg.role == "assistant" and hasattr(msg, 'tool_calls'):
            tool_calls.update(tc.id for tc in msg.tool_calls)
        elif msg.role == "tool" and hasattr(msg, 'tool_call_id'):
            tool_results.add(msg.tool_call_id)

    # 检查孤立的工具结果（没有对应调用的结果）
    orphaned_results = tool_results - tool_calls
    if orphaned_results:
        logger.error(f"发现孤立的工具结果: {orphaned_results}")
        return False

    return True

# 在chat方法的循环中使用
def chat(...):
    # ...
    for msg in messages:
        # ... 处理消息
        pass

    # 在处理完成后验证
    if not self.validate_tool_consistency(messages):
        logger.warning("[一致性检查] 消息历史存在不一致，可能已记忆污染")
    # ...
```

---

### Phase 3: Actor控制流（可选做）

引入actor概念，让控制流更清晰。

```python
class ConversationActor:
    """对话角色常量"""
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"

def determine_next_actor(self, messages: List[Message]) -> str:
    """
    确定下一轮对话的actor，模仿neu的设计。

    Args:
        messages: 消息历史

    Returns:
        actor: USER/AGENT/TOOL
    """
    if not messages:
        return self.ConversationActor.USER

    last_msg = messages[-1]

    if last_msg.role == "user":
        return self.ConversationActor.AGENT
    elif last_msg.role == "assistant":
        # 检查是否有未处理工具
        unprocessed = self.get_unprocessed_tools(messages)
        return self.ConversationActor.TOOL if unprocessed else self.ConversationActor.USER
    elif last_msg.role == "tool":
        return self.ConversationActor.AGENT

    return self.ConversationActor.USER

# 在chat()中使用
actor = self.determine_next_actor(messages)
iteration = 0
while actor != self.ConversationActor.USER and iteration < self.max_iterations:
    # ...处理逻辑...

    # 更新actor
    actor = self.determine_next_actor(messages)
}
```

---

### Phase 4: 分离Tool定义和执行（长期优化）

重构为neu风格：定义与执行分离。

```python
# src/tools/tool_definitions.py
class ToolDefinition(BaseModel):
    """工具定义：仅含元数据"""
    name: str
    description: str
    parameters: dict  # JSON schema

class ReadToolDefinition(ToolDefinition):
    name = "read"
    description = "读取文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "文件路径"}
        },
        "required": ["file_path"]
    }

# src/tools/tool_executors.py
class ReadToolExecutor:
    """工具执行器：仅含逻辑"""
    def __init__(self, dida_client):
        self.dida_client = dida_client

    async def execute(self, input: dict) -> dict:
        file_path = input["file_path"]
        return await self.dida_client.read_file(file_path)

# 在ai_assistant.py中注册
def setup_tools(self):
    self.tool_definitions = {
        "read": ReadToolDefinition(),
    }
    self.tool_executors = {
        "read": ReadToolExecutor(self.dida_client),
    }
    self.toolset = SimpleToolset()
    for name, definition in self.tool_definitions.items():
        self.toolset += definition.to_callable_tool()
```

---

## 实施优先级

| Phase | 改动量 | 风险 | 收益 | 优先级 | 预估工时 |
|-------|--------|------|------|--------|----------|
| 1: 核心重构 | 小 | 低 | 高 | ⭐⭐⭐⭐⭐ | 30分钟 |
| 2: 错误处理 | 中 | 低 | 中 | ⭐⭐⭐⭐ | 20分钟 |
| 3: Actor控制流 | 中 | 中 | 中 | ⭐⭐⭐ | 40分钟 |
| 4: 分离定义执行 | 大 | 高 | 中 | ⭐⭐ | 2小时 |

**建议顺序**：1 → 2 → 3 → 4

Phase 1和2可以合并，在1小时内完成，完全消除pending_tool_calls带来的状态不一致风险。

---

## 测试用例

### Phase 1测试

```python
# test_ai_assistant_refactor.py

async def test_unprocessed_tools():
    """测试未处理工具推导功能"""
    assistant = AIAssistant(...)

    # 场景1：空历史
    messages = []
    assert assistant.get_unprocessed_tools(messages) == {}

    # 场景2：有工具调用但无结果
    tool_call = {"id": "test-123", "name": "get_tasks"}
    messages = [
        Message(role="assistant", tool_calls=[tool_call])
    ]
    result = assistant.get_unprocessed_tools(messages)
    assert "test-123" in result

    # 场景3：有调用也有结果
    messages = [
        Message(role="assistant", tool_calls=[tool_call]),
        Message(role="tool", tool_call_id="test-123", content="结果")
    ]
    result = assistant.get_unprocessed_tools(messages)
    assert "test-123" not in result

    # 场景4：多个工具，部分完成
    # ...

    print("✅ 所有测试通过")
```

---

## neu-translator与tg-dida核心差异

| 维度 | neu-translator (TS) | tg-dida (Python) |
|------|---------------------|------------------|
| **状态管理** | 自动推导 | 手动维护 |
| **控制流** | Actor模型 (user/agent) | 显式循环 |
| **Tool架构** | 定义与执行分离 | 定义与执行耦合 |
| **并发** | Promise.all并发执行 | 顺序执行 |
| **日志** | 轻量 | 详细 |
| **容错** | 幂等推导 | 状态易损 |
| **复杂度** | 高 | 低 |

**核心结论**：neu通过增加代码复杂度换取了状态管理的健壮性和可预测性，这是大型Agent系统必须做的取舍。tg-dida目前简单但脆弱，Phase 1的改造能在保持可读性的前提下提升健壮性。

---

## 参考文献

- neu-translator/packages/core/src/agent.ts
- neu-translator/packages/core/src/context.ts
- neu-translator/packages/core/src/types.ts
- tg-dida/src/ai_assistant.py
