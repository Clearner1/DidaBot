"""番茄钟相关数据模型"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class FocusOperation:
    """番茄钟操作项"""
    id: str
    oId: str  # 焦点ID
    oType: int = 0  # 对象类型，0表示番茄钟
    op: str = ""  # 操作类型：start, pause, continue, finish, drop, exit
    duration: int = 25  # 持续时间（分钟）
    firstFocusId: Optional[str] = None
    focusOnId: str = ""
    focusOnType: Optional[int] = None
    focusOnTitle: Optional[str] = None
    autoPomoLeft: int = 0
    pomoCount: int = 0
    manual: bool = True
    note: str = ""
    time: str = ""
    createdTime: int = 0


@dataclass
class FocusOperationRequest:
    """番茄钟操作请求"""
    lastPoint: int = 0
    opList: List[FocusOperation] = None

    def __post_init__(self):
        if self.opList is None:
            self.opList = []


@dataclass
class FocusStartOptions:
    """开始番茄钟的配置选项"""
    duration: int = 25
    auto_pomo_left: int = 5
    pomo_count: int = 1
    manual: bool = True
    note: str = ""
    focus_on_id: str = ""
    focus_on_type: Optional[int] = None
    focus_on_title: Optional[str] = None
    last_point: Optional[int] = None


@dataclass
class FocusControlOptions:
    """番茄钟控制选项（暂停、继续、完成）"""
    manual: bool = True
    note: str = ""
    focus_on_type: Optional[int] = None
    focus_on_title: Optional[str] = None
    last_point: Optional[int] = None


@dataclass
class FocusStopOptions:
    """停止番茄钟的选项"""
    manual: bool = True
    note: str = ""
    focus_on_type: Optional[int] = None
    focus_on_title: Optional[str] = None
    last_point: Optional[int] = None
    include_exit: bool = True


@dataclass
class FocusSessionState:
    """本地缓存的番茄钟会话状态"""
    last_point: int = 0
    focus_id: Optional[str] = None
    first_focus_id: Optional[str] = None
    duration: int = 25
    auto_pomo_left: int = 0
    pomo_count: int = 0
    manual: bool = True
    note: str = ""
    focus_on_id: str = ""
    focus_on_type: Optional[int] = None
    focus_on_title: Optional[str] = None
    status: Optional[int] = None
    raw_current: Dict[str, Any] = None

    def __post_init__(self):
        if self.raw_current is None:
            self.raw_current = {}

    def reset_session(self) -> None:
        """清理当前番茄会话，但保留指针与历史信息"""
        self.focus_id = None
        self.first_focus_id = None
        self.focus_on_id = ""
        self.focus_on_type = None
        self.focus_on_title = None
        self.status = None
        self.raw_current = {}