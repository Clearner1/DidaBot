# 小滴の记忆系统 - 设计方案

> 版本：v1.0
> 日期：2025-11-16
> 状态：设计阶段，暂不执行

## 项目背景

### 问题

Telegram Bot中的对话是一次性的，用户执行`/reset`或对话超时后，上下文会被清除，AI无法记住之前的重要信息。

### 目标

利用滴答清单的NOTE条目和Column功能，构建一个分层记忆系统，让AI能够：

1. 在对话结束后保存重要信息
2. 在新对话开始时加载相关记忆
3. 通过时间维度管理记忆生命周期

---

## 核心架构

### 1. 项目结构

```
项目名称：小滴の记忆
项目类型：kind = "TASK"（支持看板功能）
视图模式：viewMode = "kanban"（看板视图）
项目颜色：#7E57C2（紫色）
```

### 2. Column分层设计

使用3个Column（看板列）模拟人类记忆系统：

```
┌──────────────────────────────────────────────────────┐
│  Column 1: 短期记忆 (Short-term Memory)              │
├──────────────────────────────────────────────────────┤
│  时间跨度：1-7天                                      │
│  用途：                                               │
│    - 最近对话的要点                                   │
│    - 临时性信息                                       │
│    - 待确认的内容                                     │
│  特点：                                               │
│    - 高频访问，快速检索                               │
│    - 到期时间：创建后7天                              │
│    - 遗忘曲线：ERULE:NAME=FORGETTINGCURVE;CYCLE=0    │
│    - 提醒：到期前9小时                                │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Column 2: 中期记忆 (Medium-term Memory)             │
├──────────────────────────────────────────────────────┤
│  时间跨度：1周-1月                                    │
│  用途：                                               │
│    - 重要对话摘要                                     │
│    - 阶段性决策                                       │
│    - 工作流程                                         │
│  特点：                                               │
│    - 中频访问，主题检索                               │
│    - 到期时间：移入后30天                             │
│    - 重复规则：RRULE:FREQ=WEEKLY;INTERVAL=2          │
│    - 提醒：到期前1天                                  │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  Column 3: 长期记忆 (Long-term Memory)               │
├──────────────────────────────────────────────────────┤
│  时间跨度：永久保留                                   │
│  用途：                                               │
│    - 用户核心偏好                                     │
│    - 重要约定                                         │
│    - 不变的事实                                       │
│  特点：                                               │
│    - 每次对话都加载                                   │
│    - 到期时间：移入后90天（季度复习）                 │
│    - 重复规则：RRULE:FREQ=MONTHLY;INTERVAL=3         │
│    - 提醒：到期前1周                                  │
└──────────────────────────────────────────────────────┘
```

---

## 记忆数据格式

### NOTE条目结构

每条记忆都是一个NOTE类型的条目：

```json
{
  "title": "记忆标题（简短描述）",
  "content": "记忆详细内容（markdown格式）",
  "kind": "NOTE",
  "projectId": "小滴の记忆的项目ID",
  "columnId": "对应列的ID（短期/中期/长期）",
  "priority": 0-5,
  "dueDate": "下次复习时间（ISO 8601格式）",
  "reminders": ["提醒规则"],
  "repeatFlag": "重复规则或遗忘曲线",
  "status": 0,
  "timeZone": "Asia/Shanghai"
}
```

### 记忆内容模板

```markdown
# 记忆详情

## 类型
- 用户偏好 / 重要事实 / 对话摘要 / 知识片段

## 内容
[具体的记忆内容]

## 上下文
- 时间：2025-11-16 15:30
- 来源：对话#123
- 话题：项目设计讨论

## 标签
#工作 #Python #滴答清单

## 关联
- 相关记忆ID: note_abc123
- 相关任务ID: task_xyz789
```

### 优先级定义

```
priority = 5: 核心记忆，每次对话必加载（用户偏好、重要约定）
priority = 3: 重要记忆，相关话题时加载（工作流程、阶段决策）
priority = 1: 普通记忆，按需检索（对话摘要、临时信息）
priority = 0: 低优先级，即将遗忘
```

---

## 功能设计

### 1. 保存记忆（两种方式）

#### 方式A：自动保存（对话结束时）

**触发时机**：

- 用户执行 `/reset` 命令
- 对话超时（5分钟无活动）

**执行流程**：

```
对话结束
  ↓
AI分析对话历史
  ↓
判断是否有重要信息
  ├─→ 有：提炼关键内容
  │     ↓
  │   创建NOTE条目
  │     ↓
  │   保存到"短期记忆"列
  │
  └─→ 无：直接清空对话
  ↓
清空临时对话历史
```

**示例**：

```
对话内容：
用户："我想用Column来管理记忆"
AI："好主意！可以分成短期、中期、长期三列"
用户："对，就这样"
[用户执行 /reset]

自动保存的记忆：
{
  "title": "对话摘要-2025-11-16-Column分层设计",
  "content": "讨论了记忆系统的Column分层设计\n- 确定使用3列：短期、中期、长期\n- 记忆类型为NOTE条目",
  "kind": "NOTE",
  "columnId": "short_term_column_id",
  "priority": 1,
  "dueDate": "2025-11-23T09:00:00+08:00"
}
```

#### 方式B：手动保存（对话过程中）

**触发方式**：
用户在对话中说：

- "记住这个"
- "保存到记忆"
- "这个很重要"
- "把这个写下来"

**执行流程**：

```
用户发出保存请求
  ↓
AI识别保存意图
  ↓
调用 save_memory 工具
  ↓
提取用户想保存的内容
  ↓
判断记忆重要性
  ├─→ 核心偏好：保存到"长期记忆"，priority=5
  ├─→ 重要信息：保存到"中期记忆"，priority=3
  └─→ 普通信息：保存到"短期记忆"，priority=1
  ↓
创建NOTE条目
  ↓
回复用户：已保存到[列名]
```

**示例**：

```
对话中：
用户："我每周一不喜欢被打扰，记住这个"

AI识别：
- 这是用户偏好
- 持久性信息
- 重要程度：高

执行：
调用 save_memory(
  title="用户偏好-周一不打扰",
  content="用户明确表示每周一不希望被打扰",
  column="long_term",
  priority=5
)

回复："已记住：每周一不打扰你（保存到长期记忆）"
```

### 2. 加载记忆（新对话开始时）

**触发时机**：
用户发送新消息开始对话

**加载策略**：

```
从"小滴の记忆"项目获取NOTE条目
  ↓
按Column分类
  ↓
选择加载的记忆：
  ├─→ 长期记忆：全部加载（通常不超过10条）
  ├─→ 中期记忆：最近5条，按priority排序
  └─→ 短期记忆：最近2条
  ↓
格式化成系统提示
  ↓
注入到对话开始
```

**系统提示示例**：

```
你是一个有记忆的AI助手。以下是你对用户的记忆：

【长期记忆】
1. 用户偏好：Windows系统，不使用emoji
2. 用户偏好：每周一不打扰
3. 项目信息：正在开发Telegram滴答清单机器人

【中期记忆】
1. 对话摘要-2025-11-15：讨论了遗忘曲线的应用
2. 决策记录：采用Column分层方案

【短期记忆】
1. 对话摘要-2025-11-16：确定了3列结构设计

请基于这些记忆与用户自然对话，保持连贯性。
```

---

## 记忆生命周期管理

### 核心机制：Human in the Loop

利用滴答清单的**提醒功能 + 遗忘曲线**，让用户决策记忆的去留。

```
记忆创建 → 设置到期时间和提醒 → 到期时滴答清单提醒 → 用户决策
```

### 短期记忆生命周期（7天）

```
Day 0: 创建记忆到"短期记忆"列
  - dueDate: 7天后
  - reminders: ["TRIGGER:P0DT9H0M0S"]
  - repeatFlag: "ERULE:NAME=FORGETTINGCURVE;CYCLE=0"

Day 6: 滴答清单提前9小时提醒
  "记忆即将到期：[记忆标题]"

Day 7: 用户收到提醒，做出决策

用户的选择：
  ├─→ 选项1：在滴答清单中拖动到"中期记忆"列
  ├─→ 选项2：在Telegram告诉AI："把XXX升级到中期"
  ├─→ 选项3：标记完成（归档）
  └─→ 选项4：不理睬（记忆保持在原列，继续显示到期状态）
```

**用户在Telegram的交互示例**：

```
用户："有个记忆到期了，关于Column方案的，我觉得挺重要的，升级到中期吧"

AI执行：
1. 搜索标题包含"Column方案"的记忆
2. 调用 move_memory 工具
3. 移动到"中期记忆"列
4. 更新 dueDate 为30天后
5. 更新 repeatFlag 为每2周复习
6. 回复："已将记忆'Column方案'升级到中期记忆"
```

### 中期记忆生命周期（30天）

```
Day 0: 移入"中期记忆"列
  - dueDate: 30天后
  - reminders: ["TRIGGER:P1DT0H0M0S"]
  - repeatFlag: "RRULE:FREQ=WEEKLY;INTERVAL=2"

Day 29: 滴答清单提前1天提醒

Day 30: 用户决策

用户的选择：
  ├─→ 核心偏好/重要事实 → 升级到"长期记忆"
  ├─→ 不太重要 → 标记完成（归档）
  └─→ 延期 → 推迟30天
```

**判断标准**：

- 是用户的固定偏好吗？→ 长期
- 是不变的重要事实吗？→ 长期
- 是阶段性的信息吗？→ 归档
- 还需要保留一段时间吗？→ 延期

### 长期记忆生命周期（90天复习）

```
Day 0: 移入"长期记忆"列
  - priority: 5（最高优先级）
  - dueDate: 90天后
  - reminders: ["TRIGGER:P7DT0H0M0S"]
  - repeatFlag: "RRULE:FREQ=MONTHLY;INTERVAL=3"

Day 83: 滴答清单提前1周提醒

Day 90: 季度复习

用户的选择：
  ├─→ 仍然有效 → 推迟90天（继续保留）
  ├─→ 已过时 → 归档
  └─→ 需要更新 → 编辑内容后推迟
```

**复习场景示例**：

```
滴答清单提醒："长期记忆复习：项目信息-开发Telegram机器人"

用户思考：
"项目还在开发中"
→ 点击推迟，延期3个月

或者：
"项目已经完成了"
→ 标记完成，归档
→ 或者更新内容："项目已完成于2026年3月，可供参考"
```

### AI辅助决策（可选）

当用户忽略提醒3天以上，AI可以在下次对话时主动提醒：

```
AI："有2条记忆待处理，要看看吗？"

用户："看看"

AI：
"1. 记忆：'Column方案讨论'（短期，已到期7天）
   - 我的建议：升级到中期
   - 理由：这7天内你提到过3次这个话题

 2. 记忆：'临时笔记-测试想法'（短期，已到期7天）
   - 我的建议：归档
   - 理由：30天内未使用过"

用户可以：
- 接受AI建议："按你说的办"
- 自己决定："第一个升级，第二个删除"
- 稍后处理："等会儿再说"
```

---

## 需要实现的工具

### 1. save_memory（保存记忆）

```python
功能：在对话过程中主动保存记忆

参数：
- title: str（必需）- 记忆标题
- content: str（必需）- 记忆内容
- memory_type: str（可选）- 记忆类型（preference/fact/decision/conversation）
- column: str（可选）- 目标列（short_term/medium_term/long_term，默认short_term）
- priority: int（可选）- 优先级（0-5，默认1）
- tags: List[str]（可选）- 标签列表
- related_ids: List[str]（可选）- 关联的记忆/任务ID

返回：
- success: bool
- message: str - "记忆已保存到[列名]"
- memory_id: str - 创建的记忆ID
```

### 2. move_memory（移动记忆）

```python
功能：将记忆移动到不同的Column

参数：
- memory_id: str（必需）- 记忆ID
- target_column: str（必需）- 目标列（short_term/medium_term/long_term）
- reason: str（可选）- 移动原因

返回：
- success: bool
- message: str - "记忆已移动到[列名]"
```

### 3. archive_memory（归档记忆）

```python
功能：将记忆标记为完成（归档）

参数：
- memory_id: str（必需）- 记忆ID

返回：
- success: bool
- message: str - "记忆已归档"
```

### 4. search_memories（检索记忆）

```python
功能：搜索记忆

参数：
- query: str（可选）- 搜索关键词
- columns: List[str]（可选）- 限制搜索的列
- limit: int（可选）- 返回数量限制，默认10

返回：
- memories: List[Memory] - 匹配的记忆列表
- count: int - 总数量
```

### 5. get_expired_memories（获取到期记忆）

```python
功能：获取已到期待处理的记忆

参数：
- days_overdue: int（可选）- 过期天数，默认0（今天到期）

返回：
- memories: List[Memory] - 到期的记忆列表
- suggestions: List[dict] - AI对每条记忆的处理建议
```

---

## 实现优先级

### 第一版（MVP - 核心功能）

必须实现：

1. 创建"小滴の记忆"项目和3个Column
2. 实现 `save_memory` 工具（手动保存）
3. 实现自动对话总结和保存（对话结束时）
4. 实现记忆加载（新对话开始时）
5. 在记忆创建时设置正确的dueDate、reminders、repeatFlag

测试目标：

- 用户可以手动保存重要信息
- 对话结束后自动生成摘要
- 新对话能加载之前的记忆
- 滴答清单能正常提醒到期记忆

### 第二版（增强功能）

可选实现：

1. `move_memory` 工具（在Telegram中移动记忆）
2. `archive_memory` 工具（在Telegram中归档记忆）
3. `search_memories` 工具（搜索历史记忆）
4. AI辅助建议（分析到期记忆并给出建议）
5. 记忆统计（查看记忆总数、分布等）

### 第三版（高级功能）

未来扩展：

1. 记忆自动分类（AI判断应该放在哪个列）
2. 记忆相似度检测（合并重复记忆）
3. 记忆网络可视化（展示记忆之间的关联）
4. 定期记忆报告（每周生成记忆回顾）
5. 语义检索（基于内容相似度检索记忆）

---

## 技术要点

### 1. Column ID 的获取

```python
# 获取项目数据（包含columns）
response = await dida_client.client.get(
    f"/open/v1/project/{memory_project_id}/data"
)
project_data = response.json()

columns = project_data.get("columns", [])

# 建立映射
column_map = {}
for col in columns:
    name = col.get("name")
    if "短期记忆" in name:
        column_map["short_term"] = col.get("id")
    elif "中期记忆" in name:
        column_map["medium_term"] = col.get("id")
    elif "长期记忆" in name:
        column_map["long_term"] = col.get("id")
```

### 2. 创建带Column的记忆

```python
# 注意：创建时需要在请求中包含columnId
task_data = {
    "title": "记忆标题",
    "content": "记忆内容",
    "kind": "NOTE",
    "projectId": memory_project_id,
    "columnId": column_map["short_term"],  # 指定列ID
    "priority": 1,
    "dueDate": "2025-11-23T09:00:00+08:00",
    "reminders": ["TRIGGER:P0DT9H0M0S"],
    "repeatFlag": "ERULE:NAME=FORGETTINGCURVE;CYCLE=0",
    "timeZone": "Asia/Shanghai"
}
```

### 3. 移动记忆到不同Column

```python
# 通过更新任务来改变columnId
update_data = {
    "id": memory_id,
    "projectId": memory_project_id,
    "columnId": column_map["medium_term"],  # 新的列ID
    # 同时更新其他字段
    "dueDate": new_due_date,
    "repeatFlag": new_repeat_flag
}

response = await dida_client.client.post(
    f"/open/v1/task/{memory_id}",
    json=update_data
)
```

### 4. 时间计算

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

beijing_tz = ZoneInfo("Asia/Shanghai")
now = datetime.now(beijing_tz)

# 短期记忆：7天后到期
short_term_due = now + timedelta(days=7)
short_term_due_str = short_term_due.strftime("%Y-%m-%dT%H:%M:%S+08:00")

# 中期记忆：30天后到期
medium_term_due = now + timedelta(days=30)

# 长期记忆：90天后到期
long_term_due = now + timedelta(days=90)
```

---

## 用户体验流程示例

### 完整的记忆生命周期

```
第1天（对话结束）：
用户："今天讨论得不错"
用户执行 /reset
AI自动保存对话摘要到"短期记忆"，设置7天后到期

第8天（短期到期）：
滴答清单提醒："记忆-讨论Column方案 已到期"
用户在Telegram："把Column方案那个记忆升级到中期"
AI执行移动，设置30天后到期

第38天（中期到期）：
滴答清单提醒："记忆-讨论Column方案 即将到期"
用户判断："这是核心设计，很重要"
用户拖动到"长期记忆"列，设置90天后复习

第128天（长期复习）：
滴答清单提醒："长期记忆复习：Column方案"
用户查看："项目还在用这个方案"
用户点击推迟90天

第218天（再次复习）：
滴答清单提醒："长期记忆复习：Column方案"
用户："项目已完成，可以归档了"
用户标记完成
```

---

## 注意事项

### 1. 隐私和安全

- 记忆存储在用户自己的滴答清单账号中
- 不会上传到第三方服务器
- 用户可以随时在滴答清单中查看、编辑、删除记忆

### 2. 性能考虑

- 长期记忆数量应控制在20条以内
- 中期记忆数量应控制在30条以内
- 短期记忆定期清理，避免堆积
- 记忆加载时使用缓存，减少API调用

### 3. 用户体验

- 记忆的标题应清晰易懂
- 自动生成的记忆摘要应简洁准确
- 提醒时间应符合用户习惯（如工作日早上9点）
- AI的建议应该是建议，而非强制执行

### 4. 边界情况

- 如果用户长期不处理到期记忆怎么办？
  → 保持原状，不自动删除，定期提醒
- 如果记忆内容冲突怎么办？
  → 保留最新的，标记旧的为"已更新"
- 如果用户删除了Column怎么办？
  → 检测到后提醒用户重新创建

---

## 总结

### 核心创新点

1. **利用滴答清单原生功能**：Column分层 + 遗忘曲线 + 提醒系统
2. **Human in the loop**：记忆管理的决策权在用户手中
3. **自然的生命周期**：模拟人类记忆的遗忘和强化过程
4. **透明可控**：用户可以直接在滴答清单中看到和管理AI的记忆

### 设计原则

1. **简单优先**：第一版实现最核心功能，逐步迭代
2. **用户主导**：AI辅助，但不替代用户决策
3. **灵活可扩展**：架构支持未来添加更多功能
4. **符合习惯**：利用用户熟悉的滴答清单交互方式

---

## 下一步行动

- [ ] 在滴答清单中手动创建"小滴の记忆"项目
- [ ] 设置项目为看板模式（viewMode=kanban）
- [ ] 创建3个Column：短期记忆、中期记忆、长期记忆
- [ ] 实现 `save_memory` 工具
- [ ] 实现对话结束时的自动总结和保存
- [ ] 实现对话开始时的记忆加载
- [ ] 测试完整流程

---

**文档版本历史**：

- v1.0 (2025-11-16): 初始设计方案
