# 修复对话历史无法持久化的问题

## 问题描述

ConversationHandler集成后，AI无法记住之前的对话历史，每次都是全新对话：
- 输入"你好" → AI介绍自己
- 再次输入"你好" → AI又介绍自己（应该记住已经介绍过）
- 询问任务后，再次询问 → 又重新获取所有数据（应该基于之前的上下文回答）

## 根本原因

在`src/ai_assistant.py`的chat方法中，history处理逻辑有bug：

```python
# 原来的代码（有问题）
messages = history or []
```

当history是空列表`[]`时，`history or []`会返回`[]`（新列表），而不是使用传入的history列表。这意味着即使传递了conversation_history，ai_assistant也会创建全新列表，历史记录不会被保存。

## 修复方案

### 修复1：ai_assistant.py

修改`src/ai_assistant.py`第175-176行：

```python
# 修复后的代码
if history is not None:
    messages = history  # 确保始终使用传入的列表
else:
    messages = []
```

这样即使history是空列表，也会使用它而不是创建新列表。

### 修复2：bot.py

在ConversationHandler的回调函数中，传递对话历史：

```python
# 在_handle_ai_start和_handle_ai_active中
# 初始化对话历史
if 'conversation_history' not in context.user_data:
    context.user_data['conversation_history'] = []

# 传递历史到AI助手
history = context.user_data['conversation_history']
response = await self.ai_assistant.chat(user_message, history=history)
```

## 工作原理

1. **初始状态**：conversation_history为空列表
2. **第一次对话**：
   - bot.py传递空的history列表
   - ai_assistant使用这个列表并添加用户消息、AI回复等
   - **重要**：ai_assistant修改的是bot.py中的同一个列表对象（Python引用传递）
3. **第二次对话**：
   - bot.py再次传递同一个列表（现在包含之前的对话）
   - ai_assistant基于历史对话做出回应
4. **持续累积**：每次对话都基于之前的历史

## 测试验证

运行测试脚本验证：
```bash
python test_history_persistence.py
```

预期结果：
- ✓ 历史记录成功累积
- ✓ 用户消息、AI回复、工具调用都有记录
- ✓ AI能够记住之前的对话并基于上下文回答

## 实际效果

修复后，用户体验应该：
1. 第一次说"你好" → AI介绍自己
2. 第二次说"你好" → AI回应"我们刚才已经认识了"或类似的话
3. 询问任务后，再次询问 → AI基于之前的结果回答，而不是重新获取所有数据
4. 多轮对话保持上下文连贯

## 注意事项

- conversation_history列表会在对话过程中不断增长
- 超时或取消时，context.user_data会被清空，历史记录丢失
- 这是正常行为，因为ConversationHandler会在对话结束时清理状态
