#!/bin/bash
# 自动提交脚本 - 在每次AI任务完成后调用
# 使用方法: ./scripts/auto-commit.sh [commit message]

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取当前时间戳
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet; then
    echo -e "${YELLOW}[$TIMESTAMP] 没有检测到变更，跳过提交${NC}"
    exit 0
fi

# 显示变更文件
echo -e "${GREEN}[$TIMESTAMP] 检测到以下变更:${NC}"
git status --short

# 添加所有变更
git add -A

# 生成提交信息
if [ -z "$1" ]; then
    # 自动生成提交信息
    CHANGED_FILES=$(git diff --cached --name-only | wc -l)
    COMMIT_MSG="Auto commit: 修改了 $CHANGED_FILES 个文件"
else
    COMMIT_MSG="$1"
fi

# 执行提交
echo -e "${GREEN}[$TIMESTAMP] 正在提交...${NC}"
git commit -m "$COMMIT_MSG"

# 显示提交结果
echo -e "${GREEN}[$TIMESTAMP] 提交成功!${NC}"
git log -1 --oneline