#!/bin/bash
# 查看所有 Dreamina 账号容器状态

echo "=========================================="
echo "Dreamina 账号容器状态"
echo "=========================================="
echo ""

for container in $(docker ps -a --format '{{.Names}}' | grep "^dreamina-"); do
    status=$(docker inspect --format '{{.State.Status}}' "$container" 2>/dev/null)
    config_dir=$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/root/.dreamina_cli"}}{{.Source}}{{end}}{{end}}' "$container" 2>/dev/null)

    echo "容器: $container"
    echo "  状态: $status"
    echo "  配置: $config_dir"

    # 检查是否已登录
    if docker exec "$container" test -f /root/.dreamina_cli/credential.json 2>/dev/null; then
        echo "  登录: ✅ 已登录"
    else
        echo "  登录: ❌ 未登录"
        echo "  登录命令: docker exec -it $container dreamina login"
    fi
    echo ""
done

if [ -z "$(docker ps -a --format '{{.Names}}' | grep '^dreamina-')" ]; then
    echo "没有发现 dreamina 容器"
    echo ""
    echo "创建新容器: ./add-account.sh <账号名>"
fi