"""ID生成工具"""
import time
import uuid
import random
import string


def generate_object_id() -> str:
    """生成类似滴答清单的对象ID格式

    Returns:
        str: 24位随机字符串
    """
    # 生成16位随机字符
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    # 加上8位时间戳
    timestamp_part = f"{int(time.time() * 1000):08x}"[:8]
    return random_part + timestamp_part


def generate_trace_id() -> str:
    """生成TraceID用于请求追踪

    Returns:
        str: TraceID字符串
    """
    timestamp_hex = f"{int(time.time() * 1000):x}"
    random_suffix = uuid.uuid4().hex[:8]
    return f"{timestamp_hex}{random_suffix}"