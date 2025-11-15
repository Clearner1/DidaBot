# -*- coding: utf-8 -*-
"""
对话上下文管理模块
借鉴neu-translator的Context设计，提供消息历史管理和自动状态推导
"""

from typing import List, Dict, Any, Optional
import json
import logging
from pathlib import Path
import sys

# 添加项目根路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 添加kosong路径
kosong_path = project_root / "kosong" / "src"
sys.path.insert(0, str(kosong_path))

from kosong.message import Message

logger = logging.getLogger(__name__)


class ConversationContext:
    """
    对话上下文管理类

    职责：
    1. 管理消息历史列表
    2. 自动维护滑动窗口（避免历史过长）
    3. 自动推导未处理工具调用（核心功能，替代手动pending字典）

    借鉴neu-translator的设计：不手动维护pending状态，而是从消息历史自动推导
    """

    def __init__(self, max_history_length: Optional[int] = None):
        """
        初始化对话上下文

        Args:
            max_history_length: 消息历史最大长度（设置为None表示不限制，保持完整对话）
        """
        self.messages: List[Message] = []
        self.max_history_length = max_history_length
        logger.info(f"ConversationContext初始化，max_history_length={max_history_length or '不限制'}")

    def add_user_message(self, content: str):
        """添加用户消息到历史"""
        self.add_message(Message(role="user", content=content))
        logger.debug(f"添加用户消息: {content[:50]}...")

    def add_ai_message(self, content: Any, tool_calls: Optional[List] = None):
        """添加AI助手的回复到历史"""
        msg = Message(role="assistant", content=content)
        if tool_calls:
            msg.tool_calls = tool_calls
        self.add_message(msg)
        logger.debug(f"添加AI消息，工具调用数: {len(tool_calls) if tool_calls else 0}")

    def add_tool_result(self, tool_call_id: str, result: Any):
        """添加工具执行结果到历史"""
        # 将结果序列化为JSON字符串
        content = json.dumps(result, ensure_ascii=False, indent=2)
        self.add_message(Message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id
        ))
        logger.debug(f"添加工具结果，tool_call_id={tool_call_id}")

    def add_message(self, message: Message):
        """
        添加消息到历史（不裁剪，保留所有消息）

        Args:
            message: 要添加的消息
        """
        self.messages.append(message)
        logger.debug(f"消息历史长度: {len(self.messages)}")

    def get_unprocessed_tools(self) -> Dict[str, Any]:
        """
        核心方法：从消息历史自动推导未处理的工具调用

        借鉴neu-translator的getUnprocessedToolCalls()设计：
        - 不手动维护pending字典
        - 每次调用时从完整历史推导
        - 幂等、容错、简单

        Returns:
            未处理的工具调用映射: {tool_call_id: tool_call}
            如果所有工具调用都有对应结果，返回空字典
        """
        tool_calls: Dict[str, Any] = {}
        tool_results: set = set()

        logger.debug(f"开始推导未处理工具，消息历史长度: {len(self.messages)}")

        # 遍历所有消息
        for msg in self.messages:
            # 收集工具调用（assistant消息中的tool_calls字段）
            if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls[tc.id] = tc
                    logger.debug(f"收集工具调用: {tc.function.name} ({tc.id})")

            # 收集工具结果ID（tool消息中的tool_call_id字段）
            if msg.role == "tool" and hasattr(msg, "tool_call_id") and msg.tool_call_id:
                tool_results.add(msg.tool_call_id)
                logger.debug(f"收集工具结果: {msg.tool_call_id}")

        # 移除已有结果的工具调用
        processed = 0
        for tool_call_id in tool_results:
            if tool_call_id in tool_calls:
                tool_calls.pop(tool_call_id)
                processed += 1

        unprocessed_count = len(tool_calls)
        logger.info(f"未处理工具推导完成: 总计={len(self.messages)}条消息, "
                   f"工具调用={len(tool_calls) + processed}个, "
                   f"已处理={processed}个, "
                   f"未处理={unprocessed_count}个")

        if unprocessed_count > 0:
            tool_names = [tc.function.name for tc in tool_calls.values()]
            logger.info(f"未处理工具列表: {tool_names}")

        return tool_calls

    def get_messages(self) -> List[Message]:
        """获取所有消息（用于传递给LLM）"""
        return self.messages

    def clear(self):
        """清空消息历史（重置对话）"""
        self.messages.clear()
        logger.info("对话上下文已清空")

    def validate_consistency(self) -> bool:
        """
        验证消息历史的工具一致性

        检测孤立的工具结果（没有对应调用的结果）或调用（没有结果）

        Returns:
            True: 一致，False: 存在问题
        """
        tool_calls: set = set()
        tool_results: set = set()

        for msg in self.messages:
            if msg.role == "assistant" and hasattr(msg, "tool_calls"):
                tool_calls.update(tc.id for tc in msg.tool_calls)
            elif msg.role == "tool" and hasattr(msg, "tool_call_id"):
                tool_results.add(msg.tool_call_id)

        # 检查孤立的工具结果
        orphaned_results = tool_results - tool_calls
        if orphaned_results:
            logger.error(f"[一致性检查] 发现孤立的工具结果: {orphaned_results}")
            return False

        logger.debug("[一致性检查] 消息历史一致")
        return True
