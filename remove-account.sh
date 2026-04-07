#!/bin/bash
# 删除 Dreamina 账号容器
# 用法: ./remove-account.sh <账号名>

set -e

ACCOUNT_NAME=${1:-}

if [ -z "$ACCOUNT_NAME" ]; then
    echo "用法: ./remove-account.sh <账号名>"
    echo "示例: ./remove-account.sh alice"
    echo ""
    echo "现有容器:"
    docker ps -a --format '{{.Names}}' | grep "^dreamina-" | sed 's/dreamina-/  - /'
    exit 1
fi

CONTAINER_NAME="dreamina-${ACCOUNT_NAME}"
CONFIG_DIR="./dreamina-configs/${ACCOUNT_NAME}"

# 检查容器是否存在
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "错误: 容器 ${CONTAINER_NAME} 不存在"
    exit 1
fi

echo "即将删除容器: ${CONTAINER_NAME}"
read -p "是否同时删除配置目录 ${CONFIG_DIR}? (y/N): " -n 1 -r
echo ""

# 停止并删除容器
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true
echo "容器 ${CONTAINER_NAME} 已删除"

# 可选删除配置目录
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "${CONFIG_DIR}"
    echo "配置目录 ${CONFIG_DIR} 已删除"
fi

echo "完成"