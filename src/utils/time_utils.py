# -*- coding: utf-8 -*-
"""
时间处理工具类
用于处理滴答清单API返回的UTC时间，转换为本地时间显示
"""

from datetime import datetime, date
from typing import Dict, Any, Optional


class TimeUtils:
    """时间处理工具类"""

    @staticmethod
    def parse_dida_datetime(utc_str: str) -> datetime:
        """解析滴答清单UTC时间字符串为datetime对象

        Args:
            utc_str: 时间字符串，如 "2025-11-11T16:00:00.000+0000" 或 "2025-11-11T16:00:00+0000"

        Returns:
            datetime对象（会自动转换为本地时区）

        Raises:
            ValueError: 如果时间格式不正确
        """
        if not utc_str:
            raise ValueError("时间字符串不能为空")

        # 处理带毫秒的格式
        if "." in utc_str:
            # 移除毫秒部分以兼容 fromisoformat
            if utc_str.endswith("+0000"):
                # 格式：2025-11-11T16:00:00.000+0000
                base_str = utc_str.replace(".000", "")
            else:
                # 其他格式
                base_str = utc_str
        else:
            base_str = utc_str

        # 统一添加时区信息
        if base_str.endswith("+0000"):
            base_str = base_str.replace("+0000", "+00:00")
        elif not base_str.endswith("Z"):
            # 如果没有时区信息，添加UTC
            base_str = base_str + "+00:00"

        return datetime.fromisoformat(base_str)

    @staticmethod
    def utc_to_local_str(utc_str: str, format_str: str = "%Y-%m-%d %H:%M") -> str:
        """将滴答清单UTC时间字符串转换为本地时间字符串

        Args:
            utc_str: UTC时间字符串
            format_str: 输出格式，默认为 "%Y-%m-%d %H:%M"

        Returns:
            本地时间字符串
        """
        try:
            dt_utc = TimeUtils.parse_dida_datetime(utc_str)
            dt_local = dt_utc.astimezone()
            return dt_local.strftime(format_str)
        except Exception as e:
            # 如果解析失败，返回原始字符串
            return utc_str

    @staticmethod
    def utc_to_local_date(utc_str: str) -> date:
        """将滴答清单UTC时间字符串转换为本地日期

        Args:
            utc_str: UTC时间字符串

        Returns:
            本地日期对象
        """
        try:
            dt_utc = TimeUtils.parse_dida_datetime(utc_str)
            dt_local = dt_utc.astimezone()
            return dt_local.date()
        except Exception as e:
            # 如果解析失败，返回今天的日期
            return date.today()

    @staticmethod
    def is_today_task(task: Dict[str, Any]) -> bool:
        """判断任务是否是今天的任务（使用统一的时间处理）

        Args:
            task: 任务字典，包含 due_date, start_date 等字段

        Returns:
            是否是今天的任务
        """
        try:
            # 获取当前本地日期（与用户界面保持一致）
            today_local = date.today()

            # 检查截止日期（优先）
            due_date = task.get("due_date")
            if due_date:
                try:
                    task_date_local = TimeUtils.utc_to_local_date(due_date)
                    return task_date_local == today_local
                except Exception as e:
                    pass  # 继续检查开始日期

            # 检查开始日期（作为备选）
            start_date = task.get("start_date")
            if start_date:
                try:
                    task_date_local = TimeUtils.utc_to_local_date(start_date)
                    return task_date_local == today_local
                except Exception as e:
                    pass

            return False

        except Exception as e:
            return False

    @staticmethod
    def format_due_date(due_date: str, style: str = "chinese") -> str:
        """格式化截止日期显示

        Args:
            due_date: UTC时间字符串
            style: 显示样式
                - "chinese": "11月12日 00:00"
                - "full": "2025-11-12 00:00"
                - "time_only": "00:00"

        Returns:
            格式化后的日期字符串
        """
        if not due_date:
            return "未设置"

        if style == "chinese":
            # 中文格式：11月12日 00:00
            return TimeUtils.utc_to_local_str(due_date, "%m月%d日 %H:%M")
        elif style == "full":
            # 完整格式：2025-11-12 00:00
            return TimeUtils.utc_to_local_str(due_date, "%Y-%m-%d %H:%M")
        elif style == "time_only":
            # 仅时间：00:00
            return TimeUtils.utc_to_local_str(due_date, "%H:%M")
        else:
            # 默认格式
            return TimeUtils.utc_to_local_str(due_date)

    @staticmethod
    def local_to_utc_str(local_datetime: datetime, format_iso: bool = True) -> str:
        """将本地时间转换为UTC时间字符串（用于滴答清单API）

        Args:
            local_datetime: 本地时间的datetime对象（需要带时区信息）
            format_iso: 是否使用ISO格式，默认True

        Returns:
            UTC时间字符串，格式：
            - ISO: "2025-11-13T07:00:00+0000"（滴答API格式）

        Example:
            >>> from datetime import datetime
            >>> from zoneinfo import ZoneInfo
            >>> local_dt = datetime(2025, 11, 13, 15, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
            >>> TimeUtils.local_to_utc_str(local_dt)
            "2025-11-13T07:00:00+0000"
        """
        from zoneinfo import ZoneInfo

        # 如果没有时区信息，假设是本地时区
        if local_datetime.tzinfo is None:
            # 获取系统本地时区（通常是Asia/Shanghai）
            local_datetime = local_datetime.replace(tzinfo=ZoneInfo("Asia/Shanghai"))

        # 转换为UTC
        utc_datetime = local_datetime.astimezone(ZoneInfo("UTC"))

        if format_iso:
            # 格式化为滴答清单API格式
            return utc_datetime.strftime("%Y-%m-%dT%H:%M:%S+0000")
        else:
            return utc_datetime.isoformat()


# 测试函数
if __name__ == "__main__":
    # 测试解析
    test_cases = [
        "2025-11-11T16:00:00.000+0000",
        "2025-11-11T16:00:00+0000",
        "2025-11-11T16:00:00Z"
    ]

    print("测试 TimeUtils:")
    for utc_str in test_cases:
        print(f"\n输入: {utc_str}")
        print(f"  解析为datetime: {TimeUtils.parse_dida_datetime(utc_str)}")
        print(f"  本地时间: {TimeUtils.utc_to_local_str(utc_str)}")
        print(f"  中文格式: {TimeUtils.format_due_date(utc_str, 'chinese')}")

    # 测试任务判断
    task = {
        "due_date": "2025-11-11T16:00:00.000+0000",
        "title": "测试任务"
    }
    print(f"\n任务判断: {TimeUtils.is_today_task(task)}")
