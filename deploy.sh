#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway Docker 一鍵部署腳本 (PFC200 / SD 卡)
# 預設部署路徑: /media/sd/tymetro-gateway
# 說明: 使用 Docker 容器化技術部署後端 Python 服務與 Mosquitto Broker
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🚀 開始 Docker 一鍵部署 HVAC Edge Gateway${NC}"
echo -e "${GREEN} 📁 部署目標目錄: ${INSTALL_DIR:-/media/sd/tymetro-gateway}${NC}"
echo -e "${GREEN}=====================================================${NC}"

# 1. 檢查權限 (須為 root 權限)
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}錯誤: 請以 root 權限或 sudo 執行此安裝腳本。${NC}"
  exit 1
fi

INSTALL_DIR="${INSTALL_DIR:-/media/sd/tymetro-gateway}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. 檢查並建立 SD 卡部署目錄與複製檔案
echo -e "${YELLOW}[1/4] 檢查 SD 卡掛載點與專案目錄...${NC}"
mkdir -p "${INSTALL_DIR}"

if [ "${SCRIPT_DIR}" != "${INSTALL_DIR}" ]; then
    echo -e "${YELLOW}複製專案檔案至 ${INSTALL_DIR}...${NC}"
    cp -r "${SCRIPT_DIR}"/* "${INSTALL_DIR}/" 2>/dev/null || true
fi

cd "${INSTALL_DIR}"

# 3. 檢查並啟動 Docker 引擎
echo -e "${YELLOW}[2/4] 檢查 Docker 服務狀態...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}錯誤: 控制器上未檢測到 docker 指令！${NC}"
    echo -e "${YELLOW}請先在 PFC200 網頁管理介面 (WBM) 進入 Configuration -> Docker 勾選啟用 Docker。${NC}"
    exit 1
fi

# 啟動 Docker 服務 (若尚未啟動)
if command -v systemctl &> /dev/null; then
    systemctl enable docker 2>/dev/null || true
    systemctl start docker 2>/dev/null || true
elif [ -f /etc/init.d/docker ]; then
    /etc/init.d/docker start 2>/dev/null || true
fi

# 4. 判斷 Docker Compose 指令格式
echo -e "${YELLOW}[3/4] 檢測 Docker Compose...${NC}"
DOCKER_COMPOSE_CMD=""

if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# 4.5 確保資料庫檔案存在 (避免 Docker 將未存在的檔案掛載為目錄)
touch "${INSTALL_DIR}/tymetro-gateway-backend/gateway.db" 2>/dev/null || true

# 5. 啟動容器
echo -e "${YELLOW}[4/4] 構建並啟動 Docker 容器 (Mosquitto + Backend API)...${NC}"
if [ -n "${DOCKER_COMPOSE_CMD}" ]; then
    ${DOCKER_COMPOSE_CMD} up -d --build
else
    echo -e "${YELLOW}提示: 未找到 docker-compose，使用標準 docker 命令建置與啟動...${NC}"
    docker build -t tymetro-gateway-backend ./tymetro-gateway-backend
    docker run -d --name tymetro-mosquitto --restart always -p 1883:1883 -v "${INSTALL_DIR}/mosquitto.conf:/etc/mosquitto/conf.d/default.conf" eclipse-mosquitto:2.0 2>/dev/null || true
    docker run -d --name tymetro-gateway-backend --restart always -p 5400:5400 -v "${INSTALL_DIR}/tymetro-gateway-backend/gateway.db:/app/gateway.db" -v "${INSTALL_DIR}/tymetro-gateway-backend/gateway.yaml:/app/gateway.yaml" -v "${INSTALL_DIR}/tymetro-gateway-backend/.env:/app/.env" tymetro-gateway-backend 2>/dev/null || true
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 HVAC Edge Gateway Docker 一鍵部署完成！${NC}"
echo -e "${GREEN} 📁 安裝路徑: ${INSTALL_DIR}${NC}"
echo -e "${GREEN} 🔌 API 端點服務: http://<PFC200_IP>:5400/api/v1/status${NC}"
echo -e "${GREEN} 📡 MQTT Broker: tcp://<PFC200_IP>:1883${NC}"
echo -e "${GREEN} 🔍 容器狀態查詢: docker ps${NC}"
echo -e "${GREEN} 📜 即時日誌監看: docker compose logs -f${NC}"
echo -e "${GREEN}=====================================================${NC}"
