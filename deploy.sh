#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway - 階段 3：Docker 一鍵部署與服務啟動腳本 (PFC200)
# 說明: 於 FTP 上傳檔案後執行，負責構建並啟動所有 Docker 容器
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

INSTALL_DIR="${INSTALL_DIR:-/media/sd/tymetro-gateway}"

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🚀 [階段 3] 開始構建與啟動 Docker 服務容器${NC}"
echo -e "${GREEN} 📁 專案目錄: ${INSTALL_DIR}${NC}"
echo -e "${GREEN}=====================================================${NC}"

# 1. 檢查權限 (須為 root 權限)
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}錯誤: 請以 root 權限或 sudo 執行此腳本。${NC}"
  exit 1
fi

# 2. 切換至部署目錄
if [ -d "${INSTALL_DIR}" ]; then
    cd "${INSTALL_DIR}"
else
    echo -e "${RED}錯誤: 找不到部署目錄 ${INSTALL_DIR}！${NC}"
    echo -e "${YELLOW}請先執行 [階段 1] 腳本 ./setup.sh 建立目錄並上傳專案檔案。${NC}"
    exit 1
fi

# 3. 確保必備檔案與目錄結構存在並開放權限
mkdir -p "${INSTALL_DIR}/tymetro-gateway-backend/app/logs"
touch "${INSTALL_DIR}/tymetro-gateway-backend/gateway.db" 2>/dev/null || true
chmod -R 777 "${INSTALL_DIR}" 2>/dev/null || true

# 4. 檢測 Docker Compose 指令
echo -e "${YELLOW}檢測 Docker Compose 命令...${NC}"
DOCKER_COMPOSE_CMD=""

if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# 5. 構建並啟動 Docker 服務容器
echo -e "${YELLOW}構建並啟動 Docker 容器 (Mosquitto + Backend API + Frontend Nginx)...${NC}"
if [ -n "${DOCKER_COMPOSE_CMD}" ]; then
    ${DOCKER_COMPOSE_CMD} up -d --build
else
    echo -e "${YELLOW}提示: 未找到 docker-compose，使用標準 docker 命令建置與啟動...${NC}"
    docker build -t tymetro-gateway-backend ./tymetro-gateway-backend
    docker network create tymetro-net 2>/dev/null || true
    docker run -d --name tymetro-mosquitto --network tymetro-net --restart always -p 1883:1883 -v "${INSTALL_DIR}/mosquitto.conf:/mosquitto/config/mosquitto.conf" eclipse-mosquitto:2.0 2>/dev/null || true
    docker run -d --name tymetro-gateway-backend --network tymetro-net --restart always -p 5400:5400 -v "${INSTALL_DIR}/tymetro-gateway-backend/gateway.db:/app/gateway.db" -v "${INSTALL_DIR}/tymetro-gateway-backend/gateway.yaml:/app/gateway.yaml" -v "${INSTALL_DIR}/tymetro-gateway-backend/.env:/app/.env" tymetro-gateway-backend 2>/dev/null || true
    docker run -d --name tymetro-gateway-frontend --network tymetro-net --restart always -p 8080:8080 -v "${INSTALL_DIR}/tymetro-gateway-frotend/dist:/usr/share/nginx/html" -v "${INSTALL_DIR}/tymetro-gateway-frotend/nginx.conf:/etc/nginx/conf.d/default.conf" nginx:alpine 2>/dev/null || true
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 HVAC Edge Gateway 服務部署啟動完成！${NC}"
echo -e "${GREEN} 📁 部署路徑: ${INSTALL_DIR}${NC}"
echo -e "${GREEN} 🌐 Web UI 主頁面: http://<PFC200_IP>:8080${NC}"
echo -e "${GREEN} 🔌 REST API 文件: http://<PFC200_IP>:8080/docs${NC}"
echo -e "${GREEN} 📡 MQTT Broker: tcp://<PFC200_IP>:1883${NC}"
echo -e "${GREEN} 🔍 容器狀態查詢: docker ps${NC}"
echo -e "${GREEN} 📜 即時日誌監看: docker compose logs -f${NC}"
echo -e "${GREEN}=====================================================${NC}"
