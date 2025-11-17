FROM python:3.13-slim

# 网络和性能优化配置
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai \
    # 优化TCP参数
    TCP_FASTOPEN=1 \
    # 优化Python网络性能
    PYTHONASYNCIODEBUG=0

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app \
    && apt-get update && apt-get install -y \
    tzdata \
    # 网络优化工具
    curl \
    dnsutils \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    # 系统网络优化
    && echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf \
    && echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.conf \
    && echo 'net.ipv4.tcp_rmem = 4096 65536 16777216' >> /etc/sysctl.conf \
    && echo 'net.ipv4.tcp_wmem = 4096 65536 16777216' >> /etc/sysctl.conf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R app:app /app

USER app
CMD ["python", "-u", "main.py"]
