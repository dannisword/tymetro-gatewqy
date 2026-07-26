#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway 一鍵解除安裝腳本 (Docker / Uninstall / Clean Up)
# 預設刪除目標: /media/sd/tymetro-gateway
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${RED}=====================================================${NC}"
echo -e "${RED} 🗑️ 開始移除 HVAC Edge Gateway Docker 服務與相關設定${NC}"
echo -e "${RED}=====================================================${NC}"

# 1. 檢查權限
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}錯誤: 請以 root 權限或 sudo 執行此腳本。${NC}"
  exit 1
fi

INSTALL_DIR="${INSTALL_DIR:-/media/sd/tymetro-gateway}"

# 2. 停止並刪除 Docker 容器
echo -e "${YELLOW}[1/3] 停止並清理 Docker 容器服務...${NC}"
if [ -d "${INSTALL_DIR}" ]; then
    cd "${INSTALL_DIR}"
    if docker compose version &> /dev/null; then
        docker compose down 2>/dev/null || true
    elif command -v docker-compose &> /dev/null; then
        docker-compose down 2>/dev/null || true
    fi
fi

docker rm -f tymetro-gateway-backend tymetro-mosquitto 2>/dev/null || true
echo -e "${GREEN}Docker 容器服務已停止並移除。${NC}"

# 3. 停止並移除 systemd 服務 (若先前有安裝原生服務)
echo -e "${YELLOW}[2/3] 清理傳統 systemd / Nginx 設定 (若存在)...${NC}"
if systemctl is-active --quiet tymetro-gateway.service 2>/dev/null; then
    systemctl stop tymetro-gateway.service || true
    systemctl disable tymetro-gateway.service || true
fi
rm -f /etc/systemd/system/tymetro-gateway.service
systemctl daemon-reload 2>/dev/null || true

rm -f /etc/nginx/sites-enabled/tymetro-gateway /etc/nginx/sites-available/tymetro-gateway
rm -f /etc/mosquitto/conf.d/gateway.conf

# 4. 移除部署目錄 (預設 /media/sd/tymetro-gateway)
echo -e "${YELLOW}[3/3] 刪除部署目錄 ${INSTALL_DIR}...${NC}"
if [ -d "${INSTALL_DIR}" ]; then
    rm -rf "${INSTALL_DIR}"
    echo -e "${GREEN}已刪除 ${INSTALL_DIR}${NC}"
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} ✨ HVAC Edge Gateway 已成功完全移除！${NC}"
echo -e "${GREEN}=====================================================${NC}"
