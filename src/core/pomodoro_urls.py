"""番茄钟API端点配置"""

# 滴答清单API基础域名
DIDA_API_BASE = {
    "api_domain": "https://api.dida365.com",
    "web_domain": "https://dida365.com",
    "ms_domain": "https://ms.dida365.com"
}

# 番茄钟相关API端点
DIDA_POMODORO_APIS = {
    "general_for_desktop": "/pomodoros/statistics/generalForDesktop",
    "focus_distribution": "/pomodoros/statistics/dist",  # /pomodoros/statistics/dist/{start_date}/{end_date}
    "focus_timeline": "/pomodoros/timeline",
    "focus_heatmap": "/pomodoros/statistics/heatmap",  # /pomodoros/statistics/heatmap/{start_date}/{end_date}
    "focus_time_distribution": "/pomodoros/statistics/dist/clockByDay",  # /pomodoros/statistics/dist/clockByDay/{start_date}/{end_date}
    "focus_hour_distribution": "/pomodoros/statistics/dist/clock"  # /pomodoros/statistics/dist/clock/{start_date}/{end_date}
}

# 番茄钟操作API端点
DIDA_FOCUS_APIS = {
    "focus_batch_operation": "/focus/batch/focusOp"
}


def build_dida_api_url(endpoint: str) -> str:
    """
    构建滴答清单API URL

    Args:
        endpoint: API端点路径，如 "/api/v2/projects"

    Returns:
        str: 完整的API URL
    """
    base_url = DIDA_API_BASE["api_domain"]
    return f"{base_url}{endpoint}"


def build_dida_ms_url(endpoint: str) -> str:
    """
    构建滴答清单微服务API URL

    Args:
        endpoint: API端点路径，如 "/api/v2/sync/batch/focusOp"

    Returns:
        str: 完整的微服务API URL
    """
    base_url = DIDA_API_BASE["ms_domain"]
    return f"{base_url}{endpoint}"