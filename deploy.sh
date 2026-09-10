#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway - 階段 3：Docker 一鍵部署與服務啟動腳本 (PFC200)
# 說明: 負責喚醒 Docker 守護程序、構建並啟動所有 Docker 容器
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

INSTALL_DIR="${INSTALL_DIR:-/media/sd/tymetro-gateway}"

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🚀 [階段 3] 開始檢查與啟動 Docker 服務容器${NC}"
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

# 3. 確保 Docker Daemon (dockerd) 正常運行 (防護開機後或異常退出導致第一次執行失敗)
echo -e "${YELLOW}檢查 Docker 守護進程 (dockerd) 運作狀態...${NC}"
if ! docker info &> /dev/null; then
    echo -e "${YELLOW}Docker 守護進程尚未運行，正在自動喚醒 dockerd...${NC}"
    pkill -9 dockerd 2>/dev/null || true
    rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null || true
    sleep 1
    
    if [ -f /etc/init.d/dockerd ]; then
        /etc/init.d/dockerd restart 2>/dev/null || true
    elif [ -f /etc/init.d/docker ]; then
        /etc/init.d/docker restart 2>/dev/null || true
    elif command -v systemctl &> /dev/null; then
        systemctl restart docker 2>/dev/null || true
    else
        /usr/bin/dockerd > /dev/null 2>&1 &
    fi

    # 輪詢等待 socket 建立 (最多等待 30 秒)
    WAIT_SEC=0
    while [ ! -S /var/run/docker.sock ] && [ $WAIT_SEC -lt 30 ]; do
        sleep 1
        WAIT_SEC=$((WAIT_SEC + 1))
    done

    if ! docker info &> /dev/null; then
        echo -e "${RED}錯誤: Docker 守護進程啟動超時或失敗！${NC}"
        echo -e "${YELLOW}請確認 WBM 控制器介面中 Docker 是否勾選啟用，或手動執行 /usr/bin/dockerd 檢查錯誤。${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker 守護進程已成功啟動就緒！${NC}"
else
    echo -e "${GREEN}✓ Docker 守護進程運作正常${NC}"
fi

# 4. 確保必備檔案與目錄結構存在並開放權限
mkdir -p "${INSTALL_DIR}/tymetro-gateway-backend/app/logs"
mkdir -p "${INSTALL_DIR}/mosquitto-data"
touch "${INSTALL_DIR}/tymetro-gateway-backend/gateway.db" 2>/dev/null || true

# 處理異常斷電導致的 mosquitto.db 毀損防護 (若檔案為空，自動刪除防死鎖)
if [ -f "${INSTALL_DIR}/mosquitto-data/mosquitto.db" ]; then
    if [ ! -s "${INSTALL_DIR}/mosquitto-data/mosquitto.db" ]; then
        echo -e "${YELLOW}偵測到異常斷電產生的空 mosquitto.db 損毀檔，正在自動清除以防啟動失敗...${NC}"
        rm -f "${INSTALL_DIR}/mosquitto-data/mosquitto.db"
    fi
fi

# 處理異常斷電導致的 Docker JSON 日誌損毀 (Error grabbing logs: invalid character '\x00')
DOCKER_DATA_DIR="/media/sd/docker-data"
if [ -d "${DOCKER_DATA_DIR}/containers" ]; then
    echo -e "${YELLOW}正在清理因斷電可能損毀的 Docker 容器日誌檔 (*-json.log)...${NC}"
    find "${DOCKER_DATA_DIR}/containers/" -name "*-json.log" -exec truncate -s 0 {} \; 2>/dev/null || true
fi

# 若缺少 mosquitto.conf 則自動填入完整配置 (含 1883 TCP 與 9001 WebSocket)
if [ ! -f "${INSTALL_DIR}/mosquitto.conf" ]; then
    cat << 'EOF' > "${INSTALL_DIR}/mosquitto.conf"
listener 1883 0.0.0.0
allow_anonymous true

listener 9001 0.0.0.0
protocol websockets

# 持久化設定 (設定為 false 改用純記憶體運作，避免任何異常斷電磁碟寫入導致的損毀)
persistence false
EOF
fi

chmod -R 777 "${INSTALL_DIR}" 2>/dev/null || true

# 5. 檢測 Docker Compose 指令
echo -e "${YELLOW}檢測 Docker Compose 命令...${NC}"
DOCKER_COMPOSE_CMD=""

if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# 判斷是否需要進行映像檔構建 (--build)
# 1. 使用者帶入 --build 或 -b 參數時強制構建
# 2. 本地尚無 tymetro-gateway-backend 映像檔時自動構建（初次部署）
# 3. 若映像檔已存在且未帶參數，則直接以已構建映像檔快速拉起（避免離線環境因連不上 Docker Hub 報錯閃退）
BUILD_OPT=""
if [ "$1" = "--build" ] || [ "$1" = "-b" ]; then
    echo -e "${YELLOW}偵測到指定 --build 參數，將重新構建後端映像檔...${NC}"
    BUILD_OPT="--build"
elif ! docker image inspect tymetro-gateway-backend &> /dev/null; then
    echo -e "${YELLOW}未檢測到本機後端映像檔，將進行初次構建...${NC}"
    BUILD_OPT="--build"
else
    echo -e "${GREEN}✓ 檢測到已存在的後端映像檔，跳過重新構建以實現秒級啟動 (若需重新構建請執行 ./deploy.sh --build)${NC}"
fi

# 6. 清除舊容器衝突並啟動服務
echo -e "${YELLOW}清除舊有重名容器衝突並啟動 Docker 服務 (Mosquitto + Backend API + Frontend Nginx)...${NC}"
docker rm -f tymetro-mosquitto tymetro-gateway-backend tymetro-gateway-frontend 2>/dev/null || true

if [ -n "${DOCKER_COMPOSE_CMD}" ]; then
    ${DOCKER_COMPOSE_CMD} up -d ${BUILD_OPT}
else
    echo -e "${YELLOW}提示: 未找到 docker-compose，使用標準 docker 命令建置與啟動...${NC}"
    if [ -n "${BUILD_OPT}" ]; then
        docker build -t tymetro-gateway-backend ./tymetro-gateway-backend
    fi
    docker network create tymetro-net 2>/dev/null || true
    
    echo -e "${YELLOW}啟動 Mosquitto 容器...${NC}"
    docker rm -f tymetro-mosquitto 2>/dev/null || true
    docker run -d --name tymetro-mosquitto \
      --security-opt seccomp=unconfined \
      --network tymetro-net \
      --restart always \
      -p 1883:1883 -p 9001:9001 \
      -v "${INSTALL_DIR}/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
      -v "${INSTALL_DIR}/mosquitto-data:/mosquitto/data" \
      --log-driver local \
      --log-opt max-size=10m \
      --log-opt max-file=3 \
      eclipse-mosquitto:2.0

    echo -e "${YELLOW}啟動 Backend 容器...${NC}"
    docker rm -f tymetro-gateway-backend 2>/dev/null || true
    docker run -d --name tymetro-gateway-backend \
      --network tymetro-net \
      --network-alias backend \
      --restart always \
      -p 5400:5400 \
      -v "${INSTALL_DIR}/tymetro-gateway-backend:/app" \
      --log-driver local \
      --log-opt max-size=10m \
      --log-opt max-file=3 \
      tymetro-gateway-backend

    echo -e "${YELLOW}啟動 Frontend Nginx 容器...${NC}"
    docker rm -f tymetro-gateway-frontend 2>/dev/null || true
    docker run -d --name tymetro-gateway-frontend \
      --security-opt seccomp=unconfined \
      --network tymetro-net \
      --restart always \
      -p 8000:8080 \
      -v "${INSTALL_DIR}/tymetro-gateway-frotend/dist:/usr/share/nginx/html" \
      -v "${INSTALL_DIR}/tymetro-gateway-frotend/nginx.conf:/etc/nginx/conf.d/default.conf" \
      --log-driver local \
      --log-opt max-size=10m \
      --log-opt max-file=3 \
      nginx:alpine
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 HVAC Edge Gateway 服務部署啟動完成！${NC}"
echo -e "${GREEN} 📁 部署路徑: ${INSTALL_DIR}${NC}"
echo -e "${GREEN} 🌐 Web UI 主頁面: http://<PFC200_IP>:8000${NC}"
echo -e "${GREEN} 🔌 REST API 文件: http://<PFC200_IP>:8000/docs${NC}"
echo -e "${GREEN} 📡 MQTT Broker: tcp://<PFC200_IP>:1883 | ws://<PFC200_IP>:9001${NC}"
echo -e "${GREEN} 🔍 容器狀態查詢: docker ps${NC}"
echo -e "${GREEN} 📜 即時日誌監看: docker compose logs -f${NC}"
echo -e "${GREEN}=====================================================${NC}"
