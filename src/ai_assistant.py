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

            # 多轮循环调用：AI可以连续使用多个工具
            final_response = ""
            iteration = 0
            while iteration < self.max_iterations:
                # 自动推导未处理工具（替代手动pending追踪，借鉴neu设计）
                unprocessed_tools_before = self.context.get_unprocessed_tools()

                logger.info(f"\n{'='*60}")
                logger.info(f"AI调用第 {iteration + 1} 轮")
                logger.info(f"当前未处理工具数: {len(unprocessed_tools_before)}")
                logger.info(f"{'='*60}")

                # 调用kosong.step，让AI决定使用什么工具
                result: StepResult = await kosong.step(
                    chat_provider=self.chat_provider,
                    system_prompt=system_prompt,
                    toolset=self.toolset,
                    history=self.context.get_messages(),
                )

                # 添加AI消息到上下文历史（处理空内容）
                ai_content = result.message.content
                if ai_content is None:
                    ai_content = ""
                    logger.warning("AI返回的内容为空，使用空字符串")

                # 将AI消息添加到上下文历史
                self.context.add_ai_message(
                    content=ai_content,
                    tool_calls=result.message.tool_calls
                )

                # 记录工具调用信息（但不手动pending追踪）
                if result.message.tool_calls:
                    logger.info(f"[AI决策] 将调用 {len(result.message.tool_calls)} 个工具:")

                    # 准备工具名称列表（用于日志和 Telegram）
                    tool_names = []
                    for i, tool_call in enumerate(result.message.tool_calls, 1):
                        tool_name = tool_call.function.name
                        tool_names.append(tool_name)
                        logger.info(f"  {i}. {tool_name}")

                    # 发送 Telegram 通知（如果有 bot 实例）
                    if telegram_bot and telegram_chat_id:
                        try:
                            tool_list = "\n".join([f"  • {name}" for name in tool_names])
                            await telegram_bot.send_message(
                                chat_id=telegram_chat_id,
                                text=f"🔍 AI 正在调用工具:\n{tool_list}"
                            )
                        except Exception as e:
                            logger.warning(f"发送 Telegram 通知失败: {e}")
                else:
                    logger.info(f"[AI决策] 无工具调用，将直接回复")

                # 获取工具调用结果（如果有）
                tool_results = await result.tool_results()

                # 处理不同类型的工具调用结果
                response_parts = []

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

                # 如果有工具调用结果，先处理结果
                if tool_results:
                    logger.info(f"[工具结果] 收到 {len(tool_results)} 个工具结果:")

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

                        # 批量操作时，不加入详细工具结果到历史，避免历史过长
                        # 只加入一个摘要消息
                        if created_tasks:
                            summary = {
                                "batch_create_task": True,
                                "total": len(created_tasks) + failed_count,
                                "success": len(created_tasks),
                                "task_names": created_tasks,
                                "failed": failed_count
                            }
                            # 使用第一个tool_call_id加入摘要
                            self.context.add_tool_result(tool_results[0].tool_call_id, summary)

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

                            # 将工具结果添加到上下文历史
                            self.context.add_tool_result(tool_result.tool_call_id, actual_output)


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

                # 如果有工具调用，继续下一轮
                if tool_results:
                    logger.info(f"[循环控制] 有工具结果，继续下一轮调用（iteration={iteration}）")
                    continue
                else:
                    # 无工具调用，正常结束（无需继续调用AI）
                    logger.info(f"[循环控制] 无工具调用，退出循环（iteration={iteration}）")
                    break

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
