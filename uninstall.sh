#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway 一鍵解除安裝腳本 (Uninstall / Clean Up)
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${RED}=====================================================${NC}"
echo -e "${RED} 🗑️ 開始移除 HVAC Edge Gateway 服務與相關設定${NC}"
echo -e "${RED}=====================================================${NC}"

# 1. 檢查權限
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}錯誤: 請以 root 權限或 sudo 執行此腳本。${NC}"
  exit 1
fi

INSTALL_DIR="/opt/tymetro-gateway"

# 2. 停止並移除 systemd 服務
echo -e "${YELLOW}[1/4] 停止並移除 tymetro-gateway.service 服務...${NC}"
if systemctl is-active --quiet tymetro-gateway.service 2>/dev/null; then
    systemctl stop tymetro-gateway.service || true
fi

if systemctl is-enabled --quiet tymetro-gateway.service 2>/dev/null; then
    systemctl disable tymetro-gateway.service || true
fi

rm -f /etc/systemd/system/tymetro-gateway.service
systemctl daemon-reload 2>/dev/null || true
echo -e "${GREEN}systemd 服務已移除。${NC}"

# 3. 移除 Nginx 站點設定
echo -e "${YELLOW}[2/4] 清理 Nginx 反向代理設定...${NC}"
rm -f /etc/nginx/sites-enabled/tymetro-gateway
rm -f /etc/nginx/sites-available/tymetro-gateway

if nginx -t &> /dev/null; then
    systemctl restart nginx 2>/dev/null || true
    echo -e "${GREEN}Nginx 設定已還原並重啟。${NC}"
fi

# 4. 移除 Mosquitto Gateway 專用設定
echo -e "${YELLOW}[3/4] 清理 Mosquitto 專屬設定...${NC}"
if [ -f /etc/mosquitto/conf.d/gateway.conf ]; then
    rm -f /etc/mosquitto/conf.d/gateway.conf
    if command -v systemctl &> /dev/null; then
        systemctl restart mosquitto 2>/dev/null || true
    elif [ -f /etc/init.d/mosquitto ]; then
        /etc/init.d/mosquitto restart 2>/dev/null || true
    fi
    echo -e "${GREEN}Mosquitto gateway.conf 設定已移除。${NC}"
fi

# 5. 移除部署目錄 /opt/tymetro-gateway
echo -e "${YELLOW}[4/4] 刪除部署目錄 ${INSTALL_DIR}...${NC}"
if [ -d "${INSTALL_DIR}" ]; then
    rm -rf "${INSTALL_DIR}"
    echo -e "${GREEN}已刪除 ${INSTALL_DIR}${NC}"
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} ✨ HVAC Edge Gateway 已成功完全移除！${NC}"
echo -e "${GREEN}=====================================================${NC}"
