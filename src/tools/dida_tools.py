# -*- coding: utf-8 -*-
"""
滴答清单工具定义
用于Kosong AI框架的工具调用
"""

from typing import Optional, List
from pydantic import BaseModel
from dida_client import DidaClient, Task
from kosong.tooling import CallableTool2, ToolOk, ToolReturnType
from kosong.utils.typing import JsonType


class GetCurrentTimeParams(BaseModel):
    """获取当前时间参数（无参数）"""
    pass


class GetProjectsParams(BaseModel):
    """获取项目列表参数"""
    pass


class GetTasksParams(BaseModel):
    """获取任务列表参数"""
    project_id: Optional[str] = None
    """项目ID，如果不提供则获取所有项目的任务"""


class GetTaskDetailParams(BaseModel):
    """获取任务详情参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""


class CompleteTaskParams(BaseModel):
    """完成任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""


class DeleteTaskParams(BaseModel):
    """删除任务参数"""
    project_id: str
    """项目ID"""
    task_id: str
    """任务ID"""


class CreateTaskParams(BaseModel):
    """创建任务参数"""
    title: str
    """任务标题"""
    project_id: str
    """项目ID"""
    content: Optional[str] = None
    """任务内容（子任务、备注等）"""
    priority: Optional[int] = 0
    """优先级：0=无, 1=低, 3=中, 5=高"""
    due_date: Optional[str] = None
    """截止日期（本地时间，ISO 8601格式，带时区，如 2025-11-13T15:00:00+08:00）"""
    start_date: Optional[str] = None
    """开始日期（本地时间，ISO 8601格式）"""
    is_all_day: Optional[bool] = False
    """是否全天任务"""
    reminders: Optional[List[str]] = None
    """提醒时间列表（ISO 8601 duration格式）"""
    repeat_flag: Optional[str] = None
    """重复规则（RRULE格式）"""
    time_zone: Optional[str] = "Asia/Shanghai"
    """时区，默认 Asia/Shanghai"""


class UpdateTaskParams(BaseModel):
    """更新任务参数"""
    task_id: str
    """任务ID（必需）"""
    project_id: str
    """项目ID（必需）"""
    
    # 以下字段都是可选的，只更新提供的字段
    title: Optional[str] = None
    """任务标题"""
    content: Optional[str] = None
    """任务内容"""
    desc: Optional[str] = None
    """任务描述"""
    priority: Optional[int] = None
    """优先级：0=无, 1=低, 3=中, 5=高"""
    due_date: Optional[str] = None
    """截止日期（本地时间，ISO 8601格式，如 2025-11-13T15:00:00+08:00）"""
    start_date: Optional[str] = None
    """开始日期（本地时间，ISO 8601格式）"""
    is_all_day: Optional[bool] = None
    """是否全天任务"""
    status: Optional[int] = None
    """状态：0=未完成, 2=已完成"""
    reminders: Optional[List[str]] = None
    """提醒时间列表（ISO 8601 duration格式）"""
    repeat_flag: Optional[str] = None
    """重复规则（RRULE格式）"""
    time_zone: Optional[str] = None
    """时区"""


class GetCurrentTimeTool(CallableTool2[GetCurrentTimeParams]):
    """获取当前时间（北京时间 UTC+8）"""

    name: str = "get_current_time"
    description: str = """获取当前的日期和时间（北京时间 UTC+8）。
    
    使用场景：
    - 当用户使用相对时间表达时（如"半小时后"、"2小时后"、"明天"、"下周"）
    - 需要计算具体时间时，先调用此工具获取当前时间
    - 创建或更新任务时需要设置相对时间
    
    返回信息：
    - current_datetime: 当前完整时间（ISO格式，带时区）
    - current_date: 当前日期（YYYY-MM-DD）
    - current_time: 当前时间（HH:MM:SS）
    - weekday: 星期几（中文）
    - timestamp: Unix时间戳
    
    示例：
    - 用户说"半小时后提醒我" → 先调用此工具获取当前时间，然后加30分钟
    - 用户说"明天下午3点" → 先获取当前日期，然后计算明天的日期
    - 用户说"2小时后的会议" → 先获取当前时间，然后加2小时
    """
    params: type[GetCurrentTimeParams] = GetCurrentTimeParams

    def __init__(self):
        super().__init__()

    async def __call__(self, params: GetCurrentTimeParams) -> ToolReturnType:
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            
            # 获取北京时间（UTC+8）
            beijing_tz = ZoneInfo("Asia/Shanghai")
            now = datetime.now(beijing_tz)
            
            # 星期映射
            weekday_map = {
                0: "星期一",
                1: "星期二", 
                2: "星期三",
                3: "星期四",
                4: "星期五",
                5: "星期六",
                6: "星期日"
            }
            
            result = {
                "current_datetime": now.isoformat(),  # 完整时间（ISO格式）
                "current_date": now.strftime("%Y-%m-%d"),  # 日期
                "current_time": now.strftime("%H:%M:%S"),  # 时间
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
                "weekday": weekday_map[now.weekday()],  # 星期几
                "weekday_number": now.weekday() + 1,  # 星期几（数字1-7）
                "timestamp": int(now.timestamp()),  # Unix时间戳
                "timezone": "Asia/Shanghai",
                "formatted": now.strftime("%Y年%m月%d日 %H:%M:%S %A")  # 中文格式
            }
            
            return ToolOk(output=result)
        
        except Exception as e:
            return ToolOk(output={
                "error": f"获取当前时间失败: {str(e)}"
            })


class GetProjectsTool(CallableTool2[GetProjectsParams]):
    """获取所有滴答清单项目"""

    name: str = "get_projects"
    description: str = "获取滴答清单中的所有项目列表，返回项目名称和ID"
    params: type[GetProjectsParams] = GetProjectsParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: GetProjectsParams) -> ToolReturnType:
        try:
            projects = await self.dida_client.get_projects()
            result = []
            for project in projects:
                result.append({
                    "id": project.id,
                    "name": project.name,
                    "closed": project.closed,
                })
            return ToolOk(output=result)
        except Exception as e:
            return ToolOk(output={"error": f"获取项目失败: {str(e)}"})


class GetTasksTool(CallableTool2[GetTasksParams]):
    """获取滴答清单任务"""

    name: str = "get_tasks"
    description: str = "获取滴答清单中的任务，可以指定项目ID获取特定项目的任务，或者不指定获取所有任务"
    params: type[GetTasksParams] = GetTasksParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: GetTasksParams) -> ToolReturnType:
        try:
            tasks = await self.dida_client.get_tasks(params.project_id)
            result = []
            for task in tasks:
                task_info = {
                    "id": task.id,
                    "title": task.title,
                    "project_id": task.project_id,
                    "status": task.status,  # 0:未完成, 2:已完成
                    "priority": task.priority,  # 0:无, 1:低, 3:中, 5:高
                    "is_all_day": task.is_all_day,
                }
                if task.due_date:
                    task_info["due_date"] = task.due_date
                if task.start_date:
                    task_info["start_date"] = task.start_date
                result.append(task_info)
            return ToolOk(output=result)
        except Exception as e:
            return ToolOk(output={"error": f"获取任务失败: {str(e)}"})


class CompleteTaskTool(CallableTool2[CompleteTaskParams]):
    """完成滴答清单任务"""

    name: str = "complete_task"
    description: str = "将滴答清单中的任务标记为已完成，需要提供项目ID和任务ID"
    params: type[CompleteTaskParams] = CompleteTaskParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: CompleteTaskParams) -> ToolReturnType:
        try:
            success = await self.dida_client.complete_task(
                params.project_id, params.task_id
            )
            if success:
                return ToolOk(output={"success": True, "message": "任务已完成"})
            else:
                return ToolOk(output={"success": False, "message": "完成任务失败"})
        except Exception as e:
            return ToolOk(output={"error": f"完成任务失败: {str(e)}"})


class GetTaskDetailTool(CallableTool2[GetTaskDetailParams]):
    """获取任务详细信息"""

    name: str = "get_task_detail"
    description: str = "获取滴答清单中特定任务的完整详细信息，包括任务内容、描述、提醒、子任务等所有字段"
    params: type[GetTaskDetailParams] = GetTaskDetailParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: GetTaskDetailParams) -> ToolReturnType:
        try:
            task = await self.dida_client.get_task(params.project_id, params.task_id)
            return ToolOk(output=task.model_dump())
        except Exception as e:
            return ToolOk(output={"error": f"获取任务详情失败: {str(e)}"})


class CreateTaskTool(CallableTool2[CreateTaskParams]):
    """在滴答清单中创建新任务"""

    name: str = "create_task"
    description: str = """在滴答清单中创建新任务。

    时间参数说明（重要）：
    - due_date/start_date 应该提供**本地时间**（北京时间 UTC+8）
    - 格式1（推荐）：ISO 8601格式，带时区 "2025-11-15T14:30:00+08:00"
    - 格式2：只有日期 "2025-11-15"（将默认为当天23:59:59）
    - 格式3：日期+时间（无时区）"2025-11-15 14:30"（将假设为本地时间）

    工具会自动将本地时间转换为UTC时间发送给滴答清单API。

    自然语言示例：
    - 用户说"明天下午3点" → 你应该计算明天的日期，提供 "2025-11-13T15:00:00+08:00"
    - 用户说"下周一" → 计算日期，提供 "2025-11-18T23:59:59+08:00"
    - 用户说"11月20号上午10点" → 提供 "2025-11-20T10:00:00+08:00"

    优先级关键词映射：
    - "无"、"普通"、"一般" → 0
    - "低"、"不急" → 1
    - "中"、"中等" → 3
    - "高"、"重要"、"紧急" → 5

    提醒 (reminders) 参数说明：
    - 格式：ISO 8601 duration格式 "TRIGGER:P{{天}}DT{{小时}}H{{分钟}}M{{秒}}S"
    - 常用示例：
      * 开始前15分钟：["TRIGGER:P0DT15M0S"]
      * 开始前1小时：["TRIGGER:P0DT1H0M0S"]
      * 开始前1天：["TRIGGER:P1DT0H0M0S"]
      * 开始时立即提醒：["TRIGGER:PT0S"]
    - 可设置多个提醒：["TRIGGER:P1DT0H0M0S", "TRIGGER:P0DT1H0M0S"]（提前1天和1小时）
    - 默认策略：如果任务有明确时间但用户未提及提醒，建议添加开始前15分钟提醒

    重复规则 (repeat_flag) 参数说明：
    - 格式：RRULE格式 "RRULE:FREQ={{频率}};[其他参数]"
    - 频率类型：DAILY（每天）、WEEKLY（每周）、MONTHLY（每月）、YEARLY（每年）
    - 常用示例：
      * 每天重复：RRULE:FREQ=DAILY
      * 每两天：RRULE:FREQ=DAILY;INTERVAL=2
      * 每周一三五：RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR
      * 工作日（跳过周末）：RRULE:FREQ=DAILY;TT_SKIP=WEEKEND
      * 每月15号：RRULE:FREQ=MONTHLY;BYMONTHDAY=15
      * 每年1月1日：RRULE:FREQ=YEARLY;BYMONTH=1;BYMONTHDAY=1
    - 用户关键词映射：
      * "每天"、"天天" → RRULE:FREQ=DAILY
      * "每周" + 星期 → RRULE:FREQ=WEEKLY;BYDAY=...
      * "工作日"、"上班日" → RRULE:FREQ=DAILY;TT_SKIP=WEEKEND
      * "每月" + 日期 → RRULE:FREQ=MONTHLY;BYMONTHDAY=...
    """
    params: type[CreateTaskParams] = CreateTaskParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: CreateTaskParams) -> ToolReturnType:
        try:
            from utils.time_utils import TimeUtils
            from datetime import datetime, date
            from zoneinfo import ZoneInfo

            # 处理截止日期（如果提供）
            utc_due_date = None
            if params.due_date:
                # 情况1：AI已经提供了ISO格式的日期
                if "T" in params.due_date:
                    # 检查是否包含时区信息
                    if "+08:00" in params.due_date or "Asia/Shanghai" in params.due_date:
                        # 本地时间，需要转换为UTC
                        local_dt = datetime.fromisoformat(params.due_date)
                        utc_due_date = TimeUtils.local_to_utc_str(local_dt)
                    elif "+00:00" in params.due_date or params.due_date.endswith("Z"):
                        # 已经是UTC时间
                        utc_due_date = params.due_date
                    else:
                        # 没有时区信息，假设是本地时间
                        dt = datetime.fromisoformat(params.due_date)
                        dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                        utc_due_date = TimeUtils.local_to_utc_str(dt)
                else:
                    # 情况2：只有日期没有时间，如 "2025-11-15"
                    # 默认设为当天23:59:59
                    dt = datetime.strptime(params.due_date, "%Y-%m-%d")
                    dt = dt.replace(hour=23, minute=59, second=59)
                    dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                    utc_due_date = TimeUtils.local_to_utc_str(dt)

            # 同样处理开始日期
            utc_start_date = None
            if params.start_date:
                if "T" in params.start_date:
                    if "+08:00" in params.start_date:
                        local_dt = datetime.fromisoformat(params.start_date)
                        utc_start_date = TimeUtils.local_to_utc_str(local_dt)
                    elif "+00:00" in params.start_date or params.start_date.endswith("Z"):
                        utc_start_date = params.start_date
                    else:
                        dt = datetime.fromisoformat(params.start_date)
                        dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                        utc_start_date = TimeUtils.local_to_utc_str(dt)
                else:
                    # 只有日期，默认当天 00:00:00
                    dt = datetime.strptime(params.start_date, "%Y-%m-%d")
                    dt = dt.replace(hour=0, minute=0, second=0)
                    dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                    utc_start_date = TimeUtils.local_to_utc_str(dt)

            # 构建Task对象（使用转换后的UTC时间）
            task = Task(
                title=params.title,
                project_id=params.project_id,
                content=params.content,
                priority=params.priority or 0,
                due_date=utc_due_date,
                start_date=utc_start_date,
                is_all_day=params.is_all_day or False,
                reminders=params.reminders or [],
                repeat_flag=params.repeat_flag,
                time_zone=params.time_zone or "Asia/Shanghai"
            )

            # 创建任务
            created_task = await self.dida_client.create_task(task)

            # 返回时显示本地时间（用户友好）
            display_due_date = None
            if created_task.due_date:
                display_due_date = TimeUtils.format_due_date(
                    created_task.due_date,
                    style="chinese"
                )

            return ToolOk(output={
                "success": True,
                "message": f"✅ 任务'{created_task.title}'已创建",
                "task_id": created_task.id,
                "project_id": created_task.project_id,
                "title": created_task.title,
                "due_date": display_due_date,
                "priority": created_task.priority
            })

        except Exception as e:
            return ToolOk(output={
                "success": False,
                "error": f"创建任务失败: {str(e)}"
            })


class UpdateTaskTool(CallableTool2[UpdateTaskParams]):
    """更新滴答清单中的任务"""

    name: str = "update_task"
    description: str = """更新滴答清单中已有任务的信息（部分更新）。
    
    功能说明：
    - 只更新用户明确要求修改的字段，其他字段保持不变
    - 必须提供 task_id 和 project_id
    - 可更新的字段包括：标题、描述、优先级、截止时间、状态、提醒、重复规则等
    
    使用场景：
    - 用户说"修改任务标题"、"更新截止时间"、"提升优先级"等
    - 用户说"把XX任务改成XX"
    - 用户说"将XX任务的截止时间改到XX"
    
    时间参数说明（重要）：
    - due_date/start_date 应该提供**本地时间**（北京时间 UTC+8）
    - 格式1（推荐）：ISO 8601格式，带时区 "2025-11-15T14:30:00+08:00"
    - 格式2：只有日期 "2025-11-15"（将默认为当天23:59:59）
    - 格式3：日期+时间（无时区）"2025-11-15 14:30"（将假设为本地时间）
    
    工具会自动将本地时间转换为UTC时间发送给滴答清单API。
    
    优先级关键词映射：
    - "无"、"普通"、"一般" → 0
    - "低"、"不急" → 1
    - "中"、"中等" → 3
    - "高"、"重要"、"紧急" → 5
    
    状态说明：
    - 0 = 未完成
    - 2 = 已完成
    
    提醒和重复规则格式与创建任务相同。
    """
    params: type[UpdateTaskParams] = UpdateTaskParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: UpdateTaskParams) -> ToolReturnType:
        try:
            from utils.time_utils import TimeUtils
            from datetime import datetime
            from zoneinfo import ZoneInfo
            
            # 第一步：获取现有任务的所有信息
            try:
                existing_task = await self.dida_client.get_task(
                    params.project_id, 
                    params.task_id
                )
            except Exception as e:
                return ToolOk(output={
                    "success": False,
                    "error": f"获取任务失败: {str(e)}，请检查 task_id 和 project_id 是否正确"
                })
            
            # 第二步：合并更新 - 只更新提供的字段
            updated_fields = []  # 记录更新了哪些字段（用于返回消息）
            
            if params.title is not None:
                existing_task.title = params.title
                updated_fields.append("标题")
            
            if params.content is not None:
                existing_task.content = params.content
                updated_fields.append("内容")
            
            if params.desc is not None:
                existing_task.desc = params.desc
                updated_fields.append("描述")
            
            if params.priority is not None:
                existing_task.priority = params.priority
                priority_names = {0: "无", 1: "低", 3: "中", 5: "高"}
                priority_name = priority_names.get(params.priority, str(params.priority))
                updated_fields.append(f"优先级({priority_name})")
            
            if params.status is not None:
                existing_task.status = params.status
                status_name = "已完成" if params.status == 2 else "未完成"
                updated_fields.append(f"状态({status_name})")
            
            if params.is_all_day is not None:
                existing_task.is_all_day = params.is_all_day
                updated_fields.append("全天任务")
            
            if params.reminders is not None:
                existing_task.reminders = params.reminders
                updated_fields.append("提醒")
            
            if params.repeat_flag is not None:
                existing_task.repeat_flag = params.repeat_flag
                updated_fields.append("重复规则")
            
            if params.time_zone is not None:
                existing_task.time_zone = params.time_zone
                updated_fields.append("时区")
            
            # 第三步：处理截止日期（如果提供）- 本地时间转UTC
            display_due_date = None
            if params.due_date is not None:
                # 转换本地时间为UTC
                if "T" in params.due_date:
                    if "+08:00" in params.due_date or "Asia/Shanghai" in params.due_date:
                        local_dt = datetime.fromisoformat(params.due_date)
                        existing_task.due_date = TimeUtils.local_to_utc_str(local_dt)
                    elif "+00:00" in params.due_date or params.due_date.endswith("Z"):
                        existing_task.due_date = params.due_date
                    else:
                        dt = datetime.fromisoformat(params.due_date)
                        dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                        existing_task.due_date = TimeUtils.local_to_utc_str(dt)
                else:
                    # 只有日期，默认当天23:59:59
                    dt = datetime.strptime(params.due_date, "%Y-%m-%d")
                    dt = dt.replace(hour=23, minute=59, second=59)
                    dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                    existing_task.due_date = TimeUtils.local_to_utc_str(dt)
                
                # 格式化显示（本地时间）
                display_due_date = TimeUtils.format_due_date(
                    existing_task.due_date, 
                    style="chinese"
                )
                updated_fields.append(f"截止时间({display_due_date})")
            
            # 第四步：处理开始日期（如果提供）
            if params.start_date is not None:
                if "T" in params.start_date:
                    if "+08:00" in params.start_date:
                        local_dt = datetime.fromisoformat(params.start_date)
                        existing_task.start_date = TimeUtils.local_to_utc_str(local_dt)
                    elif "+00:00" in params.start_date or params.start_date.endswith("Z"):
                        existing_task.start_date = params.start_date
                    else:
                        dt = datetime.fromisoformat(params.start_date)
                        dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                        existing_task.start_date = TimeUtils.local_to_utc_str(dt)
                else:
                    dt = datetime.strptime(params.start_date, "%Y-%m-%d")
                    dt = dt.replace(hour=0, minute=0, second=0)
                    dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                    existing_task.start_date = TimeUtils.local_to_utc_str(dt)
                
                updated_fields.append("开始时间")
            
            # 第五步：调用API更新任务
            updated_task = await self.dida_client.update_task(existing_task)
            
            # 第六步：准备返回结果
            fields_str = "、".join(updated_fields) if updated_fields else "无变化"
            
            # 格式化当前截止时间（用于显示）
            current_due_date = None
            if updated_task.due_date:
                current_due_date = TimeUtils.format_due_date(
                    updated_task.due_date,
                    style="chinese"
                )
            
            return ToolOk(output={
                "success": True,
                "message": f"✅ 任务'{updated_task.title}'已更新",
                "updated_fields": fields_str,
                "task_id": updated_task.id,
                "project_id": updated_task.project_id,
                "title": updated_task.title,
                "due_date": current_due_date,
                "priority": updated_task.priority,
                "status": updated_task.status
            })
        
        except Exception as e:
            return ToolOk(output={
                "success": False,
                "error": f"更新任务失败: {str(e)}"
            })


class DeleteTaskTool(CallableTool2[DeleteTaskParams]):
    """删除滴答清单中的任务"""

    name: str = "delete_task"
    description: str = """从滴答清单中永久删除任务。
    
    ⚠️ 警告：此操作不可逆！删除后无法恢复任务。
    
    功能说明：
    - 必须提供 task_id 和 project_id
    - 删除后任务将永久从滴答清单中移除
    - 建议在删除前先向用户确认
    
    使用场景：
    - 用户明确说"删除任务"、"删掉XX任务"
    - 用户说"把XX任务删了"
    - 用户确认删除操作后执行
    
    安全建议：
    - 删除前最好先显示任务详情，让用户确认
    - 如果用户只是想完成任务，应该使用 complete_task 而不是 delete_task
    - 对于重要任务，建议二次确认
    
    与 complete_task 的区别：
    - complete_task: 标记为已完成，任务仍然保留在列表中
    - delete_task: 永久删除，任务完全消失
    """
    params: type[DeleteTaskParams] = DeleteTaskParams

    def __init__(self, dida_client: DidaClient):
        super().__init__()
        object.__setattr__(self, 'dida_client', dida_client)

    async def __call__(self, params: DeleteTaskParams) -> ToolReturnType:
        try:
            # 第一步：先获取任务信息（用于确认和返回消息）
            try:
                task = await self.dida_client.get_task(
                    params.project_id, 
                    params.task_id
                )
                task_title = task.title
            except Exception as e:
                return ToolOk(output={
                    "success": False,
                    "error": f"获取任务失败: {str(e)}，请检查 task_id 和 project_id 是否正确"
                })
            
            # 第二步：调用API删除任务
            try:
                success = await self.dida_client.delete_task(
                    params.project_id,
                    params.task_id
                )
                
                if success:
                    return ToolOk(output={
                        "success": True,
                        "message": f"🗑️ 任务'{task_title}'已删除",
                        "task_title": task_title,
                        "task_id": params.task_id,
                        "project_id": params.project_id
                    })
                else:
                    return ToolOk(output={
                        "success": False,
                        "error": "删除任务失败，API返回失败状态"
                    })
            
            except Exception as e:
                return ToolOk(output={
                    "success": False,
                    "error": f"删除任务失败: {str(e)}"
                })
        
        except Exception as e:
            return ToolOk(output={
                "success": False,
                "error": f"删除任务过程出错: {str(e)}"
            })

