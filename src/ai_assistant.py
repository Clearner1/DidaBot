# -*- coding: utf-8 -*-
"""
AI Assistant 主类
使用Kosong框架集成大语言模型和工具调用
"""

import sys
import os
from pathlib import Path

# 添加kosong到Python路径
kosong_path = Path(__file__).parent.parent / "kosong" / "src"
sys.path.insert(0, str(kosong_path))

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from utils.time_utils import TimeUtils

import kosong
from kosong.message import Message
from kosong.tooling.simple import SimpleToolset
from kosong import StepResult

# 修复导入路径
from kosong.contrib.chat_provider.anthropic import Anthropic
from kosong.contrib.context.linear import LinearContext

from dida_client import DidaClient
from tools.dida_tools import (
    GetCurrentTimeTool,
    GetProjectsTool,
    GetTasksTool,
    GetTaskDetailTool,
    CompleteTaskTool,
    CreateTaskTool,
    UpdateTaskTool,
    DeleteTaskTool,
)

# 配置日志
logger = logging.getLogger(__name__)


class AIAssistant:
    """滴答清单AI助手"""

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        anthropic_base_url: str = "https://api.anthropic.com",
        anthropic_model: str = "claude-3-5-sonnet-20241022",
        dida_client: Optional[DidaClient] = None,
        max_iterations: int = 5,
        max_history_length: int = 20,
    ):
        """初始化AI助手

        Args:
            anthropic_api_key: Anthropic兼容API密钥 (GLM等)
            anthropic_base_url: API基础URL
            anthropic_model: 模型名称
            dida_client: 滴答清单客户端实例
            max_iterations: 最多循环次数，避免无限循环
            max_history_length: 对话历史最大长度（滑动窗口）
        """
        self.dida_client = dida_client
        self.max_iterations = max_iterations  # 最多循环次数，避免无限循环
        self.max_history_length = max_history_length  # 对话历史最大长度

        # 追踪未处理的工具调用（轻量级状态追踪）
        self.pending_tool_calls = {}

        # 使用Anthropic(GLM)
        if anthropic_api_key:
            self.chat_provider = Anthropic(
                model=anthropic_model,
                api_key=anthropic_api_key,
                base_url=anthropic_base_url,
                default_max_tokens=4096,  # 设置默认最大token数
            )
            self.provider_type = "anthropic(glm)"
        else:
            raise ValueError("请配置ANTHROPIC_API_KEY")

        # 创建工具集
        self.toolset = SimpleToolset()
        
        # 添加时间工具（不依赖 dida_client）
        self.toolset += GetCurrentTimeTool()
        
        # 添加滴答清单相关工具
        if dida_client:
            self.toolset += GetProjectsTool(dida_client)
            self.toolset += GetTasksTool(dida_client)
            self.toolset += GetTaskDetailTool(dida_client)
            self.toolset += CompleteTaskTool(dida_client)
            self.toolset += CreateTaskTool(dida_client)
            self.toolset += UpdateTaskTool(dida_client)
            self.toolset += DeleteTaskTool(dida_client)

        # 系统提示词
        self.system_prompt = """
你是一个滴答清单智能助手。用户可以向你询问任务和项目信息，也可以让你创建和管理任务。

你的主要能力：
1. 获取当前时间（使用 get_current_time）- 用于处理相对时间表达
2. 查看任务和项目信息（使用 get_projects, get_tasks, get_task_detail）
3. 创建新任务（使用 create_task）- 需要用户提供任务标题和项目
4. 更新已有任务（使用 update_task）- 可以修改标题、描述、优先级、截止时间等
5. 完成任务（使用 complete_task）- 标记任务为已完成（任务保留）
6. 删除任务（使用 delete_task）- 永久删除任务（不可恢复）
7. 分析用户的自然语言，确定意图
8. 用清晰、友好的方式呈现结果

重要规则：
- 优先使用工具获取最新的数据，不要编造数据
- 创建任务必须包含项目ID，如果用户没指定，要先询问用户选择哪个项目
- 时间参数必须使用本地时间（北京时间 UTC+8），格式：2025-11-13T15:00:00+08:00
- 优先级：0=无, 1=低, 3=中, 5=高
- 今天的日期是：{today}

⚠️ 重要：相对时间处理：
- 当用户使用相对时间表达时（如"半小时后"、"2小时后"、"明天"、"下周"），必须先调用 get_current_time 获取当前时间
- 不要猜测当前时间，始终使用 get_current_time 工具获取准确的当前时间
- 基于获取到的当前时间计算相对时间
- 示例：
  * 用户说"半小时后提醒我" → 调用 get_current_time → 当前时间加30分钟
  * 用户说"明天下午3点" → 调用 get_current_time → 计算明天的日期 + 15:00
  * 用户说"2小时后的会议" → 调用 get_current_time → 当前时间加2小时
  * 用户说"下周一" → 调用 get_current_time → 计算下周一的日期

创建任务工作流程：
1. 如果用户提供了项目名称：调用 get_projects 查找对应项目ID，然后直接创建任务
2. 如果用户没有提供项目名称：
   - 调用 get_projects 获取所有项目列表
   - 向用户展示项目列表，询问"要添加到哪个项目？"
   - 等待用户回复项目名称
   - 用户回复后，提取项目ID并调用 create_task 创建任务
3. 调用 create_task 创建任务（提供：title, project_id, 可选：priority, due_date, reminders, repeat_flag等）
4. 向用户确认任务已创建，并展示关键信息（标题、项目、截止时间、优先级）

更新任务工作流程：
1. 识别用户意图（关键词："修改"、"更新"、"改成"、"改为"、"调整"、"设为"等）
2. 确定要更新的任务：
   - 如果用户提供了明确的任务标识（如任务名称）：调用 get_tasks 查找匹配的任务
   - 如果用户说"刚才那个任务"、"上一个任务"：从对话上下文中获取
   - 如果不明确：询问用户"要更新哪个任务？"
3. 提取要更新的字段：
   - 标题修改："把任务改成XX" → title="XX"
   - 优先级修改："设为高优先级" → priority=5
   - 截止时间修改："改到明天" → due_date=明天的日期
   - 状态修改："标记为已完成" → status=2（或使用 complete_task）
   - 描述修改："添加备注XX" → desc="XX"
4. 调用 update_task（提供：task_id, project_id, 以及要更新的字段）
5. 向用户确认更新结果，展示更新了哪些字段和最新的任务信息

重要提示：
- update_task 只更新提供的字段，未提供的字段保持原值
- 如果用户想标记任务完成，可以使用 complete_task 或 update_task(status=2)
- 更新时间字段时，需要计算具体的日期时间（如"明天"要计算成实际日期）

删除任务工作流程：
1. 识别用户意图（关键词："删除"、"删掉"、"移除"、"清除"等）
2. ⚠️ 重要：区分"删除"和"完成"：
   - 用户说"完成任务"、"做完了" → 使用 complete_task（任务保留，标记为已完成）
   - 用户说"删除任务"、"删掉" → 使用 delete_task（永久删除）
3. 确定要删除的任务：
   - 调用 get_tasks 找到匹配的任务
   - 提取 task_id 和 project_id
4. ⚠️ 安全确认（建议）：
   - 如果是重要任务（高优先级、有截止时间、有子任务），建议先向用户显示任务详情
   - 询问用户"确定要删除吗？此操作不可恢复"
   - 只有在用户明确确认后才执行删除
5. 调用 delete_task（提供：task_id, project_id）
6. 向用户确认删除结果

删除 vs 完成：
- complete_task: 任务标记为已完成，仍然保留在列表中，可以查看历史
- delete_task: 任务永久删除，无法恢复，完全消失
- 默认情况下，建议使用 complete_task 而不是 delete_task

日期处理：
- 用户说"明天" → 计算明天的日期
- 用户说"下周一" → 计算下周一的日期
- 用户说"下午3点" → 当天15:00:00
- 总是提供带时区的完整时间：2025-11-13T15:00:00+08:00

提醒设置指南：
- 默认策略：如果任务有明确时间但用户未提及提醒，自动添加开始前15分钟提醒
- 格式：ISO 8601 duration格式 "TRIGGER:P{{天}}DT{{小时}}H{{分钟}}M{{秒}}S"
- 常用示例：
  * 开始前15分钟：["TRIGGER:P0DT15M0S"] （默认）
  * 开始前1小时：["TRIGGER:P0DT1H0M0S"]
  * 开始前1天：["TRIGGER:P1DT0H0M0S"]
  * 开始时立即提醒：["TRIGGER:PT0S"]
- 可设置多个提醒：["TRIGGER:P1DT0H0M0S", "TRIGGER:P0DT1H0M0S"] （提前1天和1小时）
- 用户关键词识别：
  * "提前X分钟/小时/天提醒" → 对应的TRIGGER格式
  * "到时候提醒我" → ["TRIGGER:PT0S"]
  * 未明确提及 → 使用默认15分钟提醒（如果有时间）

重复规则指南：
- 格式：RRULE格式 "RRULE:FREQ={{频率}};[其他参数]"
- 频率类型：DAILY（每天）、WEEKLY（每周）、MONTHLY（每月）、YEARLY（每年）
- 常用示例：
  * 每天：RRULE:FREQ=DAILY
  * 每两天：RRULE:FREQ=DAILY;INTERVAL=2
  * 每周一三五：RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR
  * 工作日（跳过周末和节假日）：RRULE:FREQ=DAILY;TT_SKIP=WEEKEND,HOLIDAY
  * 每月15号：RRULE:FREQ=MONTHLY;BYMONTHDAY=15
  * 每年生日：RRULE:FREQ=YEARLY;BYMONTH=X;BYMONTHDAY=X
- 用户关键词识别：
  * "每天"、"天天"、"日常" → RRULE:FREQ=DAILY
  * "每周X" → RRULE:FREQ=WEEKLY;BYDAY=MO/TU/WE/TH/FR/SA/SU
  * "工作日"、"上班日" → RRULE:FREQ=DAILY;TT_SKIP=WEEKEND
  * "每月X号" → RRULE:FREQ=MONTHLY;BYMONTHDAY=X
  * "每年" → RRULE:FREQ=YEARLY
- 星期映射：周一=MO, 周二=TU, 周三=WE, 周四=TH, 周五=FR, 周六=SA, 周日=SU
""".format(
            today=date.today().isoformat()
        )

    def _is_today_task(self, task: Dict[str, Any]) -> bool:
        """判断任务是否是今天的任务

        Args:
            task: 任务字典

        Returns:
            是否是今天的任务
        """
        try:
            # 获取当前本地日期（与用户界面保持一致）
            today_local = date.today()

            # 检查截止日期（优先）
            due_date = task.get("due_date")
            if due_date:
                # 解析ISO格式日期
                if isinstance(due_date, str):
                    if "T" in due_date:
                        # 包含时间，解析UTC日期然后转换为本地日期
                        task_dt_utc = datetime.fromisoformat(
                            due_date.replace("Z", "+00:00")
                        )
                        # 转换为本地时区日期
                        task_date_local = task_dt_utc.astimezone().date()
                    else:
                        # 只有日期，假设是本地日期
                        task_date_local = datetime.fromisoformat(due_date).date()

                    return task_date_local == today_local

            # 检查开始日期（作为备选）
            start_date = task.get("start_date")
            if start_date:
                if isinstance(start_date, str):
                    if "T" in start_date:
                        task_dt_utc = datetime.fromisoformat(
                            start_date.replace("Z", "+00:00")
                        )
                        task_date_local = task_dt_utc.astimezone().date()
                    else:
                        task_date_local = datetime.fromisoformat(start_date).date()

                    return task_date_local == today_local

            return False

        except Exception as e:
            logger.warning(f"判断任务日期失败: {e}, task={task}")
            return False

    async def chat(
        self,
        user_message: str,
        context: Optional[LinearContext] = None,
        history: Optional[List[Message]] = None,
    ) -> str:
        """与用户对话，处理自然语言请求

        Args:
            user_message: 用户输入的消息
            context: 可选的对话上下文，用于保持多轮对话历史
            history: 对话历史（仅当没有context时使用）

        Returns:
            AI的回复
        """
        try:
            # 准备历史消息
            if context:
                messages = context.history
            else:
                # 确保始终使用传入的history列表，即使它是空列表
                if history is not None:
                    messages = history
                else:
                    messages = []

            # 限制对话历史长度（滑动窗口，避免无限累积）
            if len(messages) > self.max_history_length:
                logger.debug(f"对话历史过长({len(messages)}条)，保留最近{self.max_history_length}条")
                messages = messages[-self.max_history_length:]
                # 如果传入了history列表，更新原始列表
                if history is not None:
                    history.clear()
                    history.extend(messages)

            messages.append(Message(role="user", content=user_message))

            # 重置未处理工具调用追踪
            self.pending_tool_calls.clear()

            # 多轮循环调用：AI可以连续使用多个工具
            final_response = ""
            iteration = 0
            while iteration < self.max_iterations:
                # 检查是否应该继续（第一轮或还有未处理工具）
                # if iteration > 0 and not self.pending_tool_calls:
                #     logger.info(f"[状态检查] 没有未处理工具，准备退出")
                #     break

                logger.info(f"\n{'='*60}")
                logger.info(f"[工具调用] 第 {iteration + 1} 轮开始")
                logger.info(f"  待处理工具: {len(self.pending_tool_calls)} 个")
                if self.pending_tool_calls:
                    tool_names = [t.function.name for t in self.pending_tool_calls.values()]
                    logger.info(f"  工具列表: {tool_names}")
                logger.info(f"{'='*60}")

                # 调用kosong.step，让AI决定使用什么工具
                result: StepResult = await kosong.step(
                    chat_provider=self.chat_provider,
                    system_prompt=self.system_prompt,
                    toolset=self.toolset,
                    history=messages,
                )

                # 将AI的回复加入历史
                messages.append(result.message)

                # 记录工具调用信息
                if result.message.tool_calls:
                    logger.info(f"[AI决策] 将调用 {len(result.message.tool_calls)} 个工具:")
                    for i, tool_call in enumerate(result.message.tool_calls, 1):
                        logger.info(f"  {i}. {tool_call.function.name}")
                        # # 记录参数（简化显示）
                        # if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
                        #     args_str = str(tool_call.function.arguments)[:200]
                        #     logger.info(f"     参数: {args_str}...")

                        # 添加到待处理工具列表
                        self.pending_tool_calls[tool_call.id] = tool_call
                        logger.info(f"  [追踪] 工具 {tool_call.function.name} 已加入待处理列表")
                else:
                    logger.info(f"[AI决策] 无工具调用，将直接回复")
                    break;

                # 获取工具调用结果（如果有）
                tool_results = await result.tool_results()

                # 处理不同类型的工具调用结果
                response_parts = []

                # 如果有工具调用结果，先处理结果
                if tool_results:
                    logger.info(f"[工具结果] 收到 {len(tool_results)} 个工具结果:")
                    for i, tool_result in enumerate(tool_results, 1):
                        # 从待处理列表中移除已完成的工具
                        tool_call_id = tool_result.tool_call_id
                        if tool_call_id in self.pending_tool_calls:
                            tool_call = self.pending_tool_calls[tool_call_id]
                            tool_call_name = tool_call.function.name
                            del self.pending_tool_calls[tool_call_id]
                            logger.info(f"  [追踪] 工具 {tool_call_name} 已完成并从待处理列表移除")

                        # 从ToolOk/ToolError中提取实际结果
                        actual_output = tool_result.result.output if hasattr(tool_result.result, 'output') else tool_result.result
                        error_msg = getattr(tool_result.result, 'message', None)

                        # 显示工具名称
                        if not tool_call_name:
                            # 从原始消息中查找（备用方案）
                            if result.message and result.message.tool_calls:
                                for tc in result.message.tool_calls:
                                    if tc.id == tool_result.tool_call_id:
                                        tool_call_name = tc.function.name
                                        break

                        # 记录结果摘要（构建完整字符串避免换行）
                        if isinstance(actual_output, list):
                            result_summary = f"返回列表，包含 {len(actual_output)} 项"
                        elif isinstance(actual_output, dict):
                            if 'error' in actual_output:
                                result_summary = f"错误: {actual_output['error']}"
                            else:
                                result_summary = f"返回字典，包含 {len(actual_output)} 个字段"
                        elif error_msg:
                            result_summary = f"错误: {error_msg}"
                        else:
                            result_summary = f"返回: {str(actual_output)[:100]}..."

                        logger.info(f"  {i}. {tool_call_name}: {result_summary}")

                        # 处理获取当前时间
                        if isinstance(actual_output, dict) and tool_call_name == "get_current_time":
                            if "error" not in actual_output:
                                current_date = actual_output.get('current_date', '')
                                current_time = actual_output.get('current_time', '')
                                weekday = actual_output.get('weekday', '')
                                
                                # 不在response_parts中显示，AI会自己处理
                                # response_parts.append(f"📅 当前时间: {current_date} {current_time} {weekday}")
                                pass  # AI 会基于这个时间计算相对时间，不需要向用户显示
                            else:
                                response_parts.append(f"获取当前时间失败: {actual_output['error']}")
                            
                            # 将工具结果加入历史
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))
                        
                        # 处理获取项目
                        elif isinstance(actual_output, list) and tool_call_name == "get_projects":
                            if actual_output:
                                response_parts.append("项目列表:")
                                for project in actual_output:
                                    status = "已关闭" if project.get("closed") else "活跃"
                                    response_parts.append(
                                        f"  • {project.get('name')} (ID: {project.get('id')[:8]}..., {status})"
                                    )
                            else:
                                response_parts.append("没有找到项目")

                            # 将工具结果加入历史（转换为JSON字符串，必须包含tool_call_id）
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理获取任务
                        elif isinstance(actual_output, list) and tool_call_name == "get_tasks":
                            if actual_output:
                                # 筛选今日任务（使用 TimeUtils）
                                today_tasks = [task for task in actual_output if TimeUtils.is_today_task(task)]

                                if today_tasks:
                                    response_parts.append("今日任务:")

                                    # 按项目分组
                                    tasks_by_project = {}
                                    for task in today_tasks:
                                        project_id = task.get("project_id", "unknown")
                                        if project_id not in tasks_by_project:
                                            tasks_by_project[project_id] = []
                                        tasks_by_project[project_id].append(task)

                                    # 获取项目信息用于显示名称
                                    try:
                                        projects = await self.dida_client.get_projects()
                                        project_map = {p.id: p.name for p in projects}
                                    except:
                                        project_map = {}

                                    # 显示任务
                                    for project_id, project_tasks in tasks_by_project.items():
                                        project_name = project_map.get(project_id, f"项目 {project_id[:8]}...")
                                        response_parts.append(f"\n项目: {project_name}")

                                        for task in project_tasks:
                                            status = "已完成" if task.get("status") == 2 else "进行中"
                                            title = task.get("title", "无标题")
                                            response_parts.append(f"  • {title} ({status})")
                                else:
                                    response_parts.append("今天没有任务 ✨")
                            else:
                                response_parts.append("没有找到任务")

                            # 将工具结果加入历史（转换为JSON字符串，必须包含tool_call_id）
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理完成任务
                        elif isinstance(actual_output, dict) and tool_call_name == "complete_task":
                            if actual_output.get("success"):
                                response_parts.append("任务已完成！✅")
                            else:
                                response_parts.append(f"完成任务失败: {actual_output.get('message', '未知错误')}")

                            # 将工具结果加入历史（转换为JSON字符串，必须包含tool_call_id）
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理删除任务
                        elif isinstance(actual_output, dict) and tool_call_name == "delete_task":
                            if actual_output.get("success"):
                                task_title = actual_output.get('task_title', '任务')
                                response_parts.append(f"🗑️ 任务'{task_title}'已永久删除")
                                response_parts.append("⚠️ 此操作不可恢复")
                            else:
                                response_parts.append(f"删除任务失败: {actual_output.get('error', '未知错误')}")

                            # 将工具结果加入历史
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理更新任务
                        elif isinstance(actual_output, dict) and tool_call_name == "update_task":
                            if actual_output.get("success"):
                                title = actual_output.get('title', '任务')
                                updated_fields = actual_output.get('updated_fields', '')
                                
                                response_parts.append(f"✅ 任务'{title}'已更新")
                                response_parts.append(f"更新的字段: {updated_fields}")
                                
                                # 显示更新后的信息
                                priority = actual_output.get('priority', 0)
                                priority_names = {0: "⚪ 无", 1: "🔵 低", 3: "🟡 中", 5: "🔴 高"}
                                priority_str = priority_names.get(priority, str(priority))
                                
                                due_date = actual_output.get('due_date')
                                status = actual_output.get('status', 0)
                                status_str = "✅ 已完成" if status == 2 else "⏳ 进行中"
                                
                                response_parts.append(f"\n任务当前状态:")
                                response_parts.append(f"  • 标题: {title}")
                                response_parts.append(f"  • 状态: {status_str}")
                                response_parts.append(f"  • 优先级: {priority_str}")
                                if due_date:
                                    response_parts.append(f"  • 截止时间: {due_date}")
                            else:
                                response_parts.append(f"更新任务失败: {actual_output.get('error', '未知错误')}")

                            # 将工具结果加入历史
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理创建任务
                        elif isinstance(actual_output, dict) and tool_call_name == "create_task":
                            if actual_output.get("success"):
                                title = actual_output.get('title', '任务')
                                response_parts.append(f"✅ 任务'{title}'已创建")
                                
                                # 显示创建的任务信息
                                priority = actual_output.get('priority', 0)
                                priority_names = {0: "⚪ 无", 1: "🔵 低", 3: "🟡 中", 5: "🔴 高"}
                                priority_str = priority_names.get(priority, str(priority))
                                
                                due_date = actual_output.get('due_date')
                                
                                response_parts.append(f"\n任务信息:")
                                response_parts.append(f"  • 标题: {title}")
                                response_parts.append(f"  • 优先级: {priority_str}")
                                if due_date:
                                    response_parts.append(f"  • 截止时间: {due_date}")
                            else:
                                response_parts.append(f"创建任务失败: {actual_output.get('error', '未知错误')}")

                            # 将工具结果加入历史
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理错误情况
                        elif isinstance(actual_output, dict) and "error" in actual_output:
                            response_parts.append(f"执行失败: {actual_output['error']}")
                            # 将工具结果加入历史（转换为JSON字符串，必须包含tool_call_id）
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理ToolError
                        elif error_msg:
                            response_parts.append(f"工具执行失败: {error_msg}")
                            messages.append(Message(
                                role="tool",
                                content=str(error_msg),
                                tool_call_id=tool_result.tool_call_id
                            ))

                        # 处理获取任务详情
                        elif isinstance(actual_output, dict) and tool_call_name == "get_task_detail":
                            if "error" not in actual_output:
                                # 显示任务详细信息
                                title = actual_output.get('title', '无标题')
                                content = actual_output.get('content', '')
                                desc = actual_output.get('desc', '')

                                response_parts.append(f"任务详情:")
                                response_parts.append(f"  标题: {title}")

                                if content:
                                    response_parts.append(f"  内容: {content}")
                                if desc:
                                    response_parts.append(f"  描述: {desc}")

                                due_date = actual_output.get('due_date')
                                if due_date:
                                    # 使用 TimeUtils 转换为本地时间显示
                                    local_due_date = TimeUtils.format_due_date(due_date, style='chinese')
                                    response_parts.append(f"  截止: {local_due_date}")

                                reminders = actual_output.get('reminders', [])
                                if reminders:
                                    response_parts.append(f"  提醒: {reminders}")

                                items = actual_output.get('items', [])
                                if items:
                                    response_parts.append(f"  子任务: {len(items)}个")
                                    for item in items:
                                        item_title = item.get('title', '无标题')
                                        response_parts.append(f"    - {item_title}")
                            else:
                                response_parts.append(f"获取任务详情失败: {actual_output['error']}")

                            # 将工具结果加入历史（转换为JSON字符串，必须包含tool_call_id）
                            import json
                            tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                            messages.append(Message(
                                role="tool",
                                content=tool_result_str,
                                tool_call_id=tool_result.tool_call_id
                            ))

                    # 添加AI的自然语言回复
                    if result.message.content:
                        if isinstance(result.message.content, str):
                            ai_reply = result.message.content
                        else:
                            # 处理内容列表
                            ai_reply = "\n".join(
                                part.text if hasattr(part, "text") else str(part)
                                for part in result.message.content
                                if hasattr(part, "text")
                            )

                        if ai_reply and ai_reply.strip():
                            response_parts.insert(0, ai_reply.strip())

                    # 组合中间回复
                    final_response = "\n\n".join(response_parts)

                # 递增迭代计数器（确保所有路径都增加）
                iteration += 1
                # 继续下一轮（如果有工具调用需要处理）
                if tool_results:
                    continue

            # 循环结束检查未处理工具状态
            if self.pending_tool_calls:
                logger.warning(f"[警告] 循环结束但仍有 {len(self.pending_tool_calls)} 个未处理工具:")
                for tool_id, tool_call in self.pending_tool_calls.items():
                    logger.warning(f"  - {tool_call.function.name} ({tool_id})")

            # 添加AI的自然语言回复
            if result.message.content and not final_response:
                if isinstance(result.message.content, str):
                    ai_reply = result.message.content
                else:
                    # 处理内容列表
                    ai_reply = "\n".join(
                        part.text if hasattr(part, "text") else str(part)
                        for part in result.message.content
                        if hasattr(part, "text")
                    )

                if ai_reply and ai_reply.strip():
                    final_response = ai_reply.strip()

            # 记录最终AI回复
            logger.info(f"\n{'='*60}")
            logger.info(f"[AI最终回复] 长度: {len(final_response)} 字符")
            logger.info(f"内容预览: {final_response[:200]}...")
            logger.info(f"{'='*60}\n")
            return final_response

        except Exception as e:
            logger.error(f"AI助手错误: {e}")
            import traceback
            traceback.print_exc()
            return f"抱歉，处理请求时出错: {str(e)}"


# 测试用例（已禁用）
# 如需测试，请取消注释下面的代码
"""
if __name__ == "__main__":
    import asyncio
    from config import get_config

    async def test():
        打印测试AI助手
        print("=" * 60)
        print("测试AI助手")
        print("=" * 60)

        # 获取配置
        config = get_config()

        # 创建DidaClient
        dida_client = DidaClient(
            access_token=config.dida_access_token,
            base_url=config.dida_base_url
        )

        try:
            # 创建AI助手 - 使用GLM
            if config.anthropic_api_key:
                ai = AIAssistant(
                    anthropic_api_key=config.anthropic_api_key,
                    anthropic_base_url=config.anthropic_base_url,
                    anthropic_model=config.anthropic_model,
                    dida_client=dida_client
                )
                print(f"使用Anthropic GLM模型: {config.anthropic_model}")
            else:
                print("错误：请配置ANTHROPIC_API_KEY")
                return

            # 测试1：查看今日任务
            print("\n测试1：询问今日任务")
            response = await ai.chat("我今天有什么任务？")
            print(f"回复：\n{response}\n")

            # 测试2：查看所有项目
            print("测试2：查看所有项目")
            response = await ai.chat("显示所有项目")
            print(f"回复：\n{response}\n")

            print("=" * 60)
            print("测试完成！")
            print("=" * 60)

        finally:
            await dida_client.close()

    asyncio.run(test())
"""
