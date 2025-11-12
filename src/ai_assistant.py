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
    GetProjectsTool,
    GetTasksTool,
    GetTaskDetailTool,
    CompleteTaskTool,
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
    ):
        """初始化AI助手

        Args:
            anthropic_api_key: Anthropic兼容API密钥 (GLM等)
            anthropic_base_url: API基础URL
            anthropic_model: 模型名称
            dida_client: 滴答清单客户端实例
        """
        self.dida_client = dida_client
        self.max_iterations = max_iterations  # 最多循环次数，避免无限循环

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
        if dida_client:
            self.toolset += GetProjectsTool(dida_client)
            self.toolset += GetTasksTool(dida_client)
            self.toolset += GetTaskDetailTool(dida_client)
            self.toolset += CompleteTaskTool(dida_client)

        # 系统提示词
        self.system_prompt = """
你是一个滴答清单智能助手。用户可以向你询问任务、项目等信息，你需要通过工具调用获取数据。

你的主要职责：
1. 帮助用户查看任务和项目信息
2. 分析用户的自然语言，确定意图
3. 使用提供的工具获取数据
4. 用清晰、友好的方式呈现结果

重要规则：
- 优先使用工具获取最新的数据
- 不要编造数据
- 如果用户没有指定项目，默认查看所有项目的任务
- 今天的日期是：{today}
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
            messages.append(Message(role="user", content=user_message))

            # 重置未处理工具调用追踪
            self.pending_tool_calls.clear()

            # 多轮循环调用：AI可以连续使用多个工具
            final_response = ""
            iteration = 0
            while iteration < self.max_iterations:
                # 检查是否应该继续（第一轮或还有未处理工具）
                if iteration > 0 and not self.pending_tool_calls:
                    logger.info(f"[状态检查] 没有未处理工具，准备退出")
                    break

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
                        # 记录参数（简化显示）
                        if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
                            args_str = str(tool_call.function.arguments)[:200]
                            logger.info(f"     参数: {args_str}...")

                        # 添加到待处理工具列表
                        self.pending_tool_calls[tool_call.id] = tool_call
                        logger.info(f"  [追踪] 工具 {tool_call.function.name} 已加入待处理列表")
                else:
                    logger.info(f"[AI决策] 无工具调用，将直接回复")

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

                        # 处理获取项目
                        if isinstance(actual_output, list) and tool_call_name == "get_projects":
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
