# Docker网络优化指南

## 问题描述
Docker容器中访问外部API（如AI服务）出现10秒级延迟，而直接在服务器运行时延迟仅为毫秒级。

## 主要原因
1. **Docker默认bridge网络**：多了一层NAT转换
2. **DNS解析缓慢**：容器内默认DNS转发机制效率低
3. **TCP参数未优化**：默认配置不适合高频API调用

## 优化方案

### 方案一：使用Host网络（推荐）
```bash
# 使用优化的docker-compose启动
docker-compose up -d
```

**优点**：
- 消除NAT层，直接使用宿主机网络栈
- DNS解析直接使用宿主机配置
- 性能提升最明显

**缺点**：
- 失去网络隔离性
- 端口冲突风险

### 方案二：优化Bridge网络
如果不能用host网络，修改docker-compose.yml：

```yaml
services:
  didabot:
    build: .
    dns:
      - 8.8.8.8        # Google DNS
      - 1.1.1.1        # Cloudflare DNS
      - 223.5.5.5      # 阿里DNS（国内更快）
    networks:
      - app-network
```

### 方案三：Docker运行时优化
```bash
# 直接运行容器时添加参数
docker run -d \
  --network host \
  --dns 8.8.8.8 \
  --dns 1.1.1.1 \
  --name didabot \
  your-image
```

## 性能测试

### 1. 运行网络测试
```bash
# 在容器内运行测试脚本
docker exec -it didabot /app/test_network.sh
```

### 2. 关键指标
- **DNS解析时间**：< 100ms
- **API连接时间**：< 500ms
- **首次请求延迟**：< 1s

### 3. 对比测试
```bash
# 测试host网络模式
docker-compose up -d
time curl http://localhost:your-port/api/test

# 测试bridge网络模式（注释掉network_mode: host）
# 重新构建并测试性能差异
```

## 进一步优化

### 1. 系统级优化（宿主机执行）
```bash
# 增加网络缓冲区
echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_rmem = 4096 65536 16777216' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_wmem = 4096 65536 16777216' >> /etc/sysctl.conf
sysctl -p
```

### 2. Docker daemon优化
编辑 `/etc/docker/daemon.json`：
```json
{
  "dns": ["8.8.8.8", "1.1.1.1"],
  "iptables": false,
  "userland-proxy": false
}
```

重启Docker：
```bash
systemctl restart docker
```

### 3. 应用层优化
- 使用连接池复用HTTP连接
- 设置合理的超时时间
- 实现请求重试机制
- 考虑本地缓存常用数据

## 故障排除

### 如果host网络模式不可用
1. 检查端口是否冲突
2. 使用不同端口启动服务
3. 回退到优化bridge网络模式

### 如果DNS仍然缓慢
1. 尝试不同的DNS服务器
2. 配置本地DNS缓存
3. 使用IP直连（如果可能）

### 监控性能
```bash
# 实时监控网络延迟
watch -n 1 'ping -c 1 8.8.8.8'

# 监控容器资源使用
docker stats didabot
```

## 预期效果
- API响应时间从10s降低到100ms以内
- DNS解析时间从秒级降低到毫秒级
- 整体用户体验接近直接在服务器运行