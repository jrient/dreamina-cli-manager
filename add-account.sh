#!/bin/bash
# 新增 Dreamina 账号容器并登录
# 用法: ./add-account.sh <账号名>

set -e

ACCOUNT_NAME=${1:-}

if [ -z "$ACCOUNT_NAME" ]; then
    echo "用法: ./add-account.sh <账号名>"
    echo "示例: ./add-account.sh alice"
    exit 1
fi

CONTAINER_NAME="dreamina-${ACCOUNT_NAME}"
CONFIG_DIR="./dreamina-configs/${ACCOUNT_NAME}"

# 检查容器是否已存在
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "错误: 容器 ${CONTAINER_NAME} 已存在"
    echo "如需重新登录，请执行: docker exec -it ${CONTAINER_NAME} dreamina login"
    exit 1
fi

# 创建配置目录
mkdir -p "${CONFIG_DIR}"
echo "创建配置目录: ${CONFIG_DIR}"

# 启动容器
echo "启动容器 ${CONTAINER_NAME}..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --network jm-auto_dreamina-net \
    -v "$(pwd)/accounts:/app/accounts:ro" \
    -v "$(pwd)/db:/app/db" \
    -v "$(pwd)/uploads:/app/uploads" \
    -v "$(pwd)/backend:/app" \
    -v "$(realpath ${CONFIG_DIR}):/root/.dreamina_cli" \
    -e ACCOUNTS_DIR=/app/accounts \
    -e CONFIG_BASE=/app/configs \
    -e DB_PATH=/app/db/tasks.db \
    -e UPLOAD_DIR=/app/uploads \
    -e POLL_INTERVAL=10 \
    --restart unless-stopped \
    jm-auto-backend

echo ""
echo "=========================================="
echo "容器 ${CONTAINER_NAME} 已启动"
echo "=========================================="
echo ""
echo "现在请在容器内登录 dreamina："
echo ""
echo "  docker exec -it ${CONTAINER_NAME} dreamina login"
echo ""
echo "登录成功后，容器将自动可用。"
echo "配置文件持久化在: ${CONFIG_DIR}"
echo ""