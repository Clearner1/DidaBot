#!/bin/bash

echo "🚀 Docker网络性能测试脚本"
echo "=================================="

# 1. DNS解析速度测试
echo "📡 DNS解析速度测试："
echo "测试 Google DNS (8.8.8.8):"
time dig 8.8.8.8 google.com

echo -e "\n测试 Cloudflare DNS (1.1.1.1):"
time dig 1.1.1.1 google.com

echo -e "\n测试 阿里DNS (223.5.5.5):"
time dig 223.5.5.5 google.com

# 2. API延迟测试
echo -e "\n🌐 API延迟测试："
echo "测试HTTP连接延迟到常见API端点:"

# 测试连接到OpenAI API（如果可用）
echo -n "OpenAI API连接时间: "
time curl -s --connect-timeout 5 -w "%{time_connect}\n" https://api.openai.com/v1/models -o /dev/null 2>&1 || echo "连接失败"

# 测试连接到百度
echo -n "百度API连接时间: "
time curl -s --connect-timeout 5 -w "%{time_connect}\n" https://www.baidu.com -o /dev/null 2>&1 || echo "连接失败"

# 3. 容器网络信息
echo -e "\n📊 容器网络信息："
echo "当前网络配置:"
ip route show

echo -e "\nDNS配置:"
cat /etc/resolv.conf

echo -e "\n网络接口:"
ip addr show

echo -e "\nTCP连接统计:"
ss -s

# 4. 系统资源使用
echo -e "\n💻 系统资源使用："
echo "内存使用:"
free -h

echo -e "\nCPU负载:"
uptime

echo -e "\n网络连接数:"
ss -tuln | wc -l

echo -e "\n✅ 测试完成！"
echo "如果DNS解析时间>100ms或API连接时间>500ms，需要进一步优化网络配置。"