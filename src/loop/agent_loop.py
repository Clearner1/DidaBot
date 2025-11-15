# -*- coding: utf-8 -*-
"""
Agent循环控制器
借鉴neu-translator的AgentLoop设计，负责控制多轮调用流程
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 添加kosong路径
kosong_path = project_root / "kosong" / "src"
sys.path.insert(0, str(kosong_path))

import kosong
from kosong import StepResult

logger = logging.getLogger(__name__)


class AgentLoop:
    """
    Agent循环控制器

    职责：
    1. 控制多轮调用流程（while循环）
    2. 调用LLM（kosong.step）
    3. 决定何时停止（基于工具调用状态）

    借鉴neu-translator的Actor模型：
    - next()方法执行一轮调用
    - 返回actor状态（agent/user/tool），让外部决定下一步
    """

    def __init__(
        self,
        chat_provider,
        toolset,
        max_iterations: int = 5,
    ):
        """
        初始化循环控制器

        Args:
            chat_provider: LLM提供者（如Anthropic）
            toolset: 工具集
            max_iterations: 最大迭代次数
        """
        self.chat_provider = chat_provider
        self.toolset = toolset
        self.max_iterations = max_iterations

        logger.info(f"AgentLoop初始化，max_iterations={max_iterations}")



    async def next(
        self,
        messages: list,
        context: Any,
        system_prompt: str,
        telegram_bot=None,
        telegram_chat_id=None
    ) -> tuple[str, Optional[str], Optional[list]]:
        """
        执行一轮调用

        借鉴neu-translator的设计：
        - 内部不维护状态，从context自动推导
        - 返回actor状态，让调用方决定下一步

        Args:
            messages: 消息历史
            context: 对话上下文（必须有get_unprocessed_tools方法）
            system_prompt: 系统提示词（由AIAssistant提供）
            telegram_bot: Telegram Bot 实例（可选）
            telegram_chat_id: Telegram 聊天ID（可选）

        Returns:
            (actor, response_text, tool_results)
            actor: "agent" | "user" | "tool"
                   agent: 继续下一轮（有工具调用）
                   user: 结束循环（无工具调用，可直接回复）
                   tool: 执行工具后继续
            response_text: AI的自然语言回复
            tool_results: 工具结果列表（如果无工具调用则为None）
        """
        # 获取未处理工具
        unprocessed_tools = context.get_unprocessed_tools()

        logger.info(f"\n{'='*60}")
        logger.info(f"AgentLoop执行一轮调用（剩余{self.max_iterations}次）")
        logger.info(f"未处理工具数: {len(unprocessed_tools)}")
        logger.info(f"{'='*60}")

        # 调用kosong.step，让AI决定使用什么工具
        result: StepResult = await kosong.step(
            chat_provider=self.chat_provider,
            system_prompt=system_prompt,
            toolset=self.toolset,
            history=messages,
        )

        # 添加AI消息到context
        ai_content = result.message.content
        if ai_content is None:
            ai_content = ""
        self._add_ai_message_to_context(context, ai_content, result.message.tool_calls)

        # 提取AI的自然语言回复
        response_text = ""
        if result.message.content:
            if isinstance(result.message.content, str):
                response_text = result.message.content
            else:
                # 处理内容列表
                response_text = "\n".join(
                    part.text if hasattr(part, "text") else str(part)
                    for part in result.message.content
                    if hasattr(part, "text")
                )

        logger.debug(f"AI回复: {response_text[:100]}...")

        # 记录工具调用
        tool_results = None
        if result.message.tool_calls:
            logger.info(f"[AI决策] 调用 {len(result.message.tool_calls)} 个工具:")
            tool_names = []
            for i, tool_call in enumerate(result.message.tool_calls, 1):
                tool_name = tool_call.function.name
                tool_names.append(tool_name)
                logger.info(f"  {i}. {tool_name}")

            # 发送 Telegram 通知
            if telegram_bot and telegram_chat_id and tool_names:
                try:
                    tool_list = "\n".join([f"  • {name}" for name in tool_names])
                    await telegram_bot.send_message(
                        chat_id=telegram_chat_id,
                        text=f"🔍 AI 正在调用工具:\n{tool_list}"
                    )
                except Exception as e:
                    logger.warning(f"发送 Telegram 通知失败: {e}")

            # 执行工具调用并返回结果
            tool_results = await result.tool_results()

            if tool_results:
                logger.info(f"[工具结果] 收到 {len(tool_results)} 个结果")

                for tool_result in tool_results:
                    # 获取工具执行结果
                    output = tool_result.result.output if hasattr(tool_result.result, 'output') else tool_result.result

                    # 将结果添加到context
                    context.add_tool_result(tool_result.tool_call_id, output)

            # 这一轮有工具调用，actor=agent（继续下一轮）
            actor = "agent"

        else:
            # 没有工具调用，这一轮可以结束
            logger.info("[AI决策] 无工具调用，本轮结束")
            actor = "user"

        return actor, response_text, tool_results

    def _add_ai_message_to_context(self, context, content, tool_calls):
        """将AI消息添加到context"""
        from kosong.message import Message
        context.add_ai_message(
            content=content,
            tool_calls=tool_calls
        )

    async def run(
        self,
        context: Any,
        system_prompt: str,
        max_iterations: Optional[int] = None,
        telegram_bot=None,
        telegram_chat_id=None,
        process_tool_results_callback=None
    ) -> str:
        """
        运行完整的对话循环

        Args:
            context: 对话上下文
            system_prompt: 系统提示词（由AIAssistant提供）
            max_iterations: 最大迭代次数（覆盖默认值）
            telegram_bot: Telegram Bot 实例
            telegram_chat_id: Telegram 聊天ID
            process_tool_results_callback: 工具结果处理回调函数

        Returns:
            AI的最终回复
        """
        if max_iterations is None:
            max_iterations = self.max_iterations

        iteration = 0
        final_response = ""

        while iteration < max_iterations:
            # 执行一轮调用
            actor, response, tool_results = await self.next(
                messages=context.get_messages(),
                context=context,
                system_prompt=system_prompt,
                telegram_bot=telegram_bot,
                telegram_chat_id=telegram_chat_id
            )

            # 保存AI回复（最后一轮的回复）
            if response and response.strip():
                final_response = response

            # 如果有工具结果，调用回调函数处理（ai_assistant负责）
            if tool_results and process_tool_results_callback:
                tool_response = await process_tool_results_callback(tool_results)
                if tool_response:
                    final_response = tool_response

            iteration += 1

            # 决定下一轮行为
            if actor == "user":
                # 无工具调用，结束循环
                logger.info("[循环控制] 无更多工具，准备退出")
                break

            # 检查是否达到最大迭代次数
            if iteration >= max_iterations:
                logger.warning("[循环控制] 达到最大迭代次数，强制退出")
                break

        logger.info(f"\n{'='*60}")
        logger.info(f"对话循环结束，共执行 {iteration} 轮")
        logger.info(f"最终回复长度: {len(final_response)} 字符")
        logger.info(f"{'='*60}")

        return final_response
