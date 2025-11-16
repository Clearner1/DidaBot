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

from src.utils.time_utils import TimeUtils

import kosong
from kosong.message import Message
from kosong.tooling.simple import SimpleToolset
from kosong import StepResult

# 修复导入路径
from kosong.contrib.chat_provider.anthropic import Anthropic
from kosong.contrib.context.linear import LinearContext

from src.dida_client import DidaClient

# 导入重构后的模块
from src.context.conversation_context import ConversationContext
from src.loop.agent_loop import AgentLoop
from src.prompts import system_prompt
from src.formatter import (
    format_get_projects,
    format_get_tasks,
    format_get_task_detail,
    format_complete_task,
    format_delete_task,
    format_update_task,
    format_create_task,
    format_current_time,
    format_get_project_columns,
)
from src.tools.dida_tools import (
    GetCurrentTimeTool,
    GetProjectsTool,
    GetTasksTool,
    GetTaskDetailTool,
    CompleteTaskTool,
    CreateTaskTool,
    UpdateTaskTool,
    DeleteTaskTool,
    GetProjectColumnsTool,
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
        max_iterations: int = 20,
        max_history_length: Optional[int] = None,
    ):
        """初始化AI助手

        Args:
            anthropic_api_key: Anthropic兼容API密钥 (GLM等)
            anthropic_base_url: API基础URL
            anthropic_model: 模型名称
            dida_client: 滴答清单客户端实例
            max_iterations: 最多循环次数，避免无限循环（工具调用最大轮数）
            max_history_length: 对话历史最大长度（设置为None表示不限制，保持完整对话）
        """
        self.dida_client = dida_client
        self.max_iterations = max_iterations  # 最多工具调用轮数
        self.max_history_length = max_history_length  # 对话历史最大长度（None=不限制）

        # 初始化聊天提供者（需要优先创建，供AgentLoop使用）
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
            self.toolset += GetProjectColumnsTool(dida_client)
            self.toolset += CompleteTaskTool(dida_client)
            self.toolset += CreateTaskTool(dida_client)
            self.toolset += UpdateTaskTool(dida_client)
            self.toolset += DeleteTaskTool(dida_client)

        # 创建对话上下文管理器（Phase 1: 替代手动pending_tool_calls）
        # 借鉴neu-translator设计：自动推导状态，不手动维护
        self.context = ConversationContext(max_history_length=max_history_length)
        logger.info(f"ConversationContext创建完成（Phase 1）")

        # 创建Agent循环控制器（Phase 3: 抽取循环逻辑）
        # 借鉴neu-translator的AgentLoop设计
        self.agent_loop = AgentLoop(
            chat_provider=self.chat_provider,
            toolset=self.toolset,
            max_iterations=self.max_iterations
        )
        logger.info(f"AgentLoop创建完成（Phase 3）")

        # 创建工具格式化器映射（Phase 4: 消除if/elif重复）
        # 借鉴neu-translator设计：通过字典映射代替条件分支
        # 借鉴neu-translator设计：通过字典映射代替条件分支
        self.tool_formatters = {
            "get_current_time": format_current_time,
            "get_projects": format_get_projects,
            "get_tasks": format_get_tasks,
            "get_task_detail": format_get_task_detail,
            "get_project_columns": format_get_project_columns,
            "complete_task": format_complete_task,
            "delete_task": format_delete_task,
            "update_task": format_update_task,
            "create_task": format_create_task,
        }
        logger.info(f"Tool formatter映射创建完成（Phase 4）")

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
        telegram_bot=None,
        telegram_chat_id=None,
    ) -> str:
        """与用户对话，处理自然语言请求

        Args:
            user_message: 用户输入的消息
            context: 可选的对话上下文，用于保持多轮对话历史（Telegram ConversationHandler使用）
            history: 对话历史（仅当没有context时使用）
            telegram_bot: Telegram Bot 实例（用于发送工具调用通知）
            telegram_chat_id: Telegram 聊天ID

        Returns:
            AI的回复
        """
        try:
            # 准备历史消息：优先使用context（Telegram传递的history），否则使用history
            if context:
                self.context.messages = context.history
            else:
                self.context.messages = history or []

            # 添加用户消息到上下文（不裁剪，保持对话完整性）
            self.context.add_user_message(user_message)

            # 多轮循环调用：使用AgentLoop进行循环控制
            final_response = ""
            iteration = 0
            while iteration < self.max_iterations:
                # 使用AgentLoop执行一轮调用（包含kosong.step和基础工具处理）
                actor, response_text, tool_results = await self.agent_loop.next(
                    messages=self.context.get_messages(),
                    context=self.context,
                    system_prompt=system_prompt,
                    telegram_bot=telegram_bot,
                    telegram_chat_id=telegram_chat_id
                )

                # 保存AI回复（最后一轮的回复）
                if response_text and response_text.strip():
                    final_response = response_text

                # 递增迭代计数器
                iteration += 1
                logger.info(f"[循环控制] 已完成第{iteration}轮，actor={actor}")

                # 处理工具结果（AIAssistant负责格式化等逻辑）
                if tool_results:
                    tool_response = await self._process_tool_results(tool_results)
                    if tool_response:
                        final_response = tool_response

                # 决定下一轮行为
                if actor == "user":
                    # 无工具调用，结束循环
                    logger.info("[循环控制] 无更多工具，准备退出")
                    break

                # 检查是否达到最大迭代次数
                if iteration >= self.max_iterations:
                    logger.warning("[循环控制] 达到最大迭代次数，强制退出")
                    break

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

    async def _process_tool_results(self, tool_results: list) -> Optional[str]:
        """
        处理工具结果（从主循环中提取）

        Args:
            tool_results: 工具结果列表

        Returns:
            处理后的回复文本
        """
        if not tool_results:
            return None

        logger.info(f"[工具结果] 收到 {len(tool_results)} 个工具结果:")

        # 检测批量操作：如果有多个相同类型的工具调用，进行摘要化处理
        tool_names = []
        for tool_result in tool_results:
            for msg in self.context.get_messages():
                if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.id == tool_result.tool_call_id:
                            tool_names.append(tc.function.name)
                            break

        # 统计每种工具类型的数量
        from collections import Counter
        tool_counts = Counter(tool_names)
        is_batch_operation = any(count > 1 for count in tool_counts.values())

        response_parts = []

        # 批量创建任务摘要处理
        if is_batch_operation and "create_task" in tool_counts and tool_counts["create_task"] > 1:
            logger.info("检测到批量创建任务，进行摘要化处理")

            # 收集所有创建任务结果
            created_tasks = []
            failed_count = 0

            for i, tool_result in enumerate(tool_results, 1):
                # 自动推导工具名称
                tool_call_id = tool_result.tool_call_id
                tool_call_name = "unknown"

                # 从历史中查找对应的工具调用
                for msg in self.context.get_messages():
                    if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            if tc.id == tool_call_id:
                                tool_call_name = tc.function.name
                                break

                # 提取结果
                actual_output = tool_result.result.output if hasattr(tool_result.result, 'output') else tool_result.result

                if tool_call_name == "create_task":
                    if isinstance(actual_output, dict) and not actual_output.get("error"):
                        created_tasks.append(actual_output.get("title", "未知任务"))
                    else:
                        failed_count += 1

                # 处理其他工具结果（get_projects, get_current_time）
                else:
                    formatter = self.tool_formatters.get(tool_call_name)
                    if formatter:
                        if tool_call_name == "get_tasks":
                            formatted = await formatter(actual_output, self.dida_client)
                        else:
                            formatted = await formatter(actual_output)
                        if formatted:
                            response_parts.append(formatted)

            # 添加批量创建任务的摘要
            if created_tasks:
                response_parts.append(f"批量创建任务完成！已成功创建 {len(created_tasks)} 个任务：{', '.join(created_tasks)}")
            if failed_count > 0:
                response_parts.append(f"有 {failed_count} 个任务创建失败")

            # 批量操作时，也将工具结果添加到历史（模仿原版本）
            # 不同于之前，现在批量创建也需要完整记录到messages中
            import json
            from kosong.message import Message

            # 为每个创建任务结果创建Message
            for tool_result in tool_results:
                actual_output = tool_result.result.output if hasattr(tool_result.result, 'output') else tool_result.result
                tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                self.context.messages.append(Message(
                    role="tool",
                    content=tool_result_str,
                    tool_call_id=tool_result.tool_call_id
                ))

        # 非批量操作，按原逻辑处理
        else:
            for i, tool_result in enumerate(tool_results, 1):
                # 自动推导工具名称
                tool_call_id = tool_result.tool_call_id
                tool_call_name = "unknown"

                # 从历史中查找对应的工具调用
                for msg in self.context.get_messages():
                    if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            if tc.id == tool_call_id:
                                tool_call_name = tc.function.name
                                break

                if tool_call_name == "unknown":
                    logger.warning(f"无法找到工具调用信息: {tool_call_id}")

                # 提取结果
                actual_output = tool_result.result.output if hasattr(tool_result.result, 'output') else tool_result.result
                error_msg = getattr(tool_result.result, 'message', None)

                # 记录结果摘要
                if isinstance(actual_output, list):
                    result_summary = f"返回列表，包含 {len(actual_output)} 项"
                elif isinstance(actual_output, dict):
                    result_summary = f"返回字典，包含 {len(actual_output)} 个字段"
                    if 'error' in actual_output:
                        result_summary = f"错误: {actual_output['error']}"
                elif error_msg:
                    result_summary = f"错误: {error_msg}"
                else:
                    result_summary = f"返回: {str(actual_output)[:100]}..."

                logger.info(f"  {i}. {tool_call_name}: {result_summary}")

                # 使用formatter映射处理结果
                formatter = self.tool_formatters.get(tool_call_name)
                if formatter:
                    # get_tasks需要dida_client参数
                    if tool_call_name == "get_tasks":
                        formatted = await formatter(actual_output, self.dida_client)
                    else:
                        formatted = await formatter(actual_output)
                    if formatted:
                        response_parts.append(formatted)

                # 将工具结果添加到上下文历史（模仿原版本：转换为Message对象）
                # 这是关键：需要将工具结果作为Message对象添加到context，而不是普通字典
                import json
                tool_result_str = json.dumps(actual_output, ensure_ascii=False, indent=2)
                from kosong.message import Message
                self.context.messages.append(Message(
                    role="tool",
                    content=tool_result_str,
                    tool_call_id=tool_result.tool_call_id
                ))
                logger.debug(f"工具 {tool_call_name} 结果已添加到messages历史")

        return "\n\n".join(response_parts) if response_parts else None


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
