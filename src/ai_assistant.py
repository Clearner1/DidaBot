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

import kosong
from kosong.chat_provider.openai_legacy import OpenAILegacy
from kosong.message import Message
from kosong.tooling.simple import SimpleToolset
from kosong import StepResult

from dida_client import DidaClient
from tools.dida_tools import (
    GetProjectsTool,
    GetTasksTool,
    CompleteTaskTool,
)

# 配置日志
logger = logging.getLogger(__name__)


class AIAssistant:
    """滴答清单AI助手"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.ai/v1",
        model: str = "kimi-k2-turbo-preview",
        dida_client: Optional[DidaClient] = None,
    ):
        """初始化AI助手

        Args:
            api_key: AI API密钥
            base_url: API基础URL，支持OpenAI兼容格式
            model: 模型名称
            dida_client: 滴答清单客户端实例
        """
        self.dida_client = dida_client

        # 创建聊天提供商（支持OpenAI兼容API）
        self.chat_provider = OpenAILegacy(
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        # 创建工具集
        self.toolset = SimpleToolset()
        if dida_client:
            self.toolset += GetProjectsTool(dida_client)
            self.toolset += GetTasksTool(dida_client)
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
            # 检查是否是全天任务
            if task.get("is_all_day"):
                return True

            # 检查截止日期
            due_date = task.get("due_date")
            if due_date:
                # 解析ISO格式日期
                if isinstance(due_date, str):
                    if "T" in due_date:
                        # 包含时间，解析日期部分
                        task_date = datetime.fromisoformat(
                            due_date.replace("Z", "+00:00")
                        ).date()
                    else:
                        # 只有日期
                        task_date = datetime.fromisoformat(due_date).date()

                    today = date.today()
                    return task_date == today

            return False
        except Exception as e:
            logger.warning(f"判断任务日期失败: {e}, task={task}")
            return False

    async def chat(self, user_message: str, history: Optional[List[Message]] = None) -> str:
        """与用户对话，处理自然语言请求

        Args:
            user_message: 用户输入的消息
            history: 对话历史

        Returns:
            AI的回复
        """
        try:
            # 准备历史消息
            messages = history or []
            messages.append(Message(role="user", content=user_message))

            # 调用kosong.step，让AI决定使用什么工具
            result: StepResult = await kosong.step(
                chat_provider=self.chat_provider,
                system_prompt=self.system_prompt,
                toolset=self.toolset,
                history=messages,
            )

            # 获取工具调用结果（如果有）
            tool_results = await result.tool_results()

            # 处理不同类型的工具调用结果
            response_parts = []

            # 1. 如果有工具调用结果，先处理结果
            for tool_result in tool_results:
                if not tool_result.is_ok:
                    response_parts.append(f"执行失败: {tool_result.error}")
                    continue

                output = tool_result.output

                # 处理获取项目
                if isinstance(output, list) and tool_result.tool_call.function.name == "get_projects":
                    if output:
                        response_parts.append("项目列表:")
                        for project in output:
                            status = "已关闭" if project.get("closed") else "活跃"
                            response_parts.append(
                                f"  • {project.get('name')} (ID: {project.get('id')[:8]}..., {status})"
                            )
                    else:
                        response_parts.append("没有找到项目")

                # 处理获取任务
                elif isinstance(output, list) and tool_result.tool_call.function.name == "get_tasks":
                    if output:
                        # 筛选今日任务
                        today_tasks = [task for task in output if self._is_today_task(task)]

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

                # 处理完成任务
                elif isinstance(output, dict) and tool_result.tool_call.function.name == "complete_task":
                    if output.get("success"):
                        response_parts.append("任务已完成！✅")
                    else:
                        response_parts.append(f"完成任务失败: {output.get('message', '未知错误')}")

            # 2. 添加AI的自然语言回复
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

            # 组合最终回复
            final_response = "\n\n".join(response_parts)

            logger.info(f"AI回复: {final_response[:200]}...")
            return final_response

        except Exception as e:
            logger.error(f"AI助手错误: {e}")
            import traceback
            traceback.print_exc()
            return f"抱歉，处理请求时出错: {str(e)}"


# 测试用例
if __name__ == "__main__":
    import asyncio
    from config import get_config

    async def test():
        """测试AI助手"""
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
            # 创建AI助手
            ai = AIAssistant(
                api_key="your_api_key",  # 需要替换为实际API密钥
                base_url="https://api.moonshot.ai/v1",
                model="kimi-k2-turbo-preview",
                dida_client=dida_client
            )

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
