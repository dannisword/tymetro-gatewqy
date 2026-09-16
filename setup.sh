#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway - 階段 1：環境預備與目錄建立腳本 (PFC200)
# 說明: 
# 1. 建立 SD 卡目標目錄結構與內部子目錄
# 2. 將 Docker 儲存路徑 (data-root) 轉移至 SD 卡 (防止 Flash 爆滿)
# 3. 檢查並下載 Docker Compose 至系統路徑
# 4. 配置 PFC200 開機自動等待 SD 卡並啟動服務 (S99autostart-gateway)
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

INSTALL_DIR="${INSTALL_DIR:-/media/sd/tymetro-gateway}"
DOCKER_DATA_ROOT="${DOCKER_DATA_ROOT:-/media/sd/docker-data}"
SD_BIN_DIR="/media/sd/bin"

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🛠️ [階段 1] 建立部署目錄、搬移 Docker 至 SD 卡與開機防護配置${NC}"
echo -e "${GREEN} 📁 部署目標目錄: ${INSTALL_DIR}${NC}"
echo -e "${GREEN} 💾 Docker 儲存路徑: ${DOCKER_DATA_ROOT}${NC}"
echo -e "${GREEN}=====================================================${NC}"

# 1. 檢查權限 (須為 root 權限)
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}錯誤: 請以 root 權限或 sudo 執行此腳本。${NC}"
  exit 1
fi

# 2. 建立 SD 卡目標目錄與內部子結構
echo -e "${YELLOW}[1/4] 建立 SD 卡掛載點與專案目錄結構...${NC}"
mkdir -p "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}/tymetro-gateway-backend/app/logs"
mkdir -p "${INSTALL_DIR}/tymetro-gateway-frotend/dist"
mkdir -p "${INSTALL_DIR}/mosquitto-data"
mkdir -p "${DOCKER_DATA_ROOT}"
mkdir -p "${SD_BIN_DIR}"

# 預防 Docker 誤將檔案掛載為目錄
touch "${INSTALL_DIR}/tymetro-gateway-backend/gateway.db" 2>/dev/null || true

# 設定目錄開放權限 (開放 777 確保 FTP 傳輸使用者能自由寫入與讀取)
echo -e "${YELLOW}設定目錄權限 777 (開放 FTP / SFTP 上傳權限)...${NC}"
chmod -R 777 "${INSTALL_DIR}" 2>/dev/null || true
chmod -R 777 "${DOCKER_DATA_ROOT}" 2>/dev/null || true

echo -e "${GREEN}✓ SD 卡目錄結構與權限設定完成：${INSTALL_DIR}${NC}"

# 3. 搬移 Docker data-root 至 SD 卡 (防止 PFC200 Flash 空間爆滿)
echo -e "${YELLOW}[2/4] 設定 Docker 儲存路徑 (data-root) 至 SD 卡...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}錯誤: 控制器上未檢測到 docker 指令！${NC}"
    echo -e "${YELLOW}請先在 PFC200 網頁管理介面 (WBM) 進入 Configuration -> Docker 勾選啟用 Docker。${NC}"
    exit 1
fi

DOCKER_RESTART_NEEDED=0
mkdir -p /etc/docker

if [ ! -f /etc/docker/daemon.json ]; then
    cat << EOF > /etc/docker/daemon.json
{
  "data-root": "${DOCKER_DATA_ROOT}",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "2m",
    "max-file": "5"
  }
}
EOF
    echo -e "${GREEN}✓ 已建立 /etc/docker/daemon.json 並指定 data-root 為 ${DOCKER_DATA_ROOT}${NC}"
    DOCKER_RESTART_NEEDED=1
elif ! grep -q "${DOCKER_DATA_ROOT}" /etc/docker/daemon.json; then
    # 若 data-root 非 SD 卡路徑，替換或更新
    if grep -q "data-root" /etc/docker/daemon.json; then
        sed -i 's|"data-root": *"[^"]*"|"data-root": "'"${DOCKER_DATA_ROOT}"'"|' /etc/docker/daemon.json 2>/dev/null || true
    else
        sed -i 's/{/{\n  "data-root": "'"${DOCKER_DATA_ROOT}"'",/' /etc/docker/daemon.json 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ 已將 data-root 更新為 SD 卡路徑 (${DOCKER_DATA_ROOT})${NC}"
    DOCKER_RESTART_NEEDED=1
else
    echo -e "${GREEN}✓ /etc/docker/daemon.json 已設定為 SD 卡路徑 (${DOCKER_DATA_ROOT})${NC}"
fi

# 雙重防護：建立 /var/lib/docker 軟連結至 SD 卡
# 避免 WAGO PFC200 韌體的 dockerd 啟動參數指定 /var/lib/docker 而忽略 daemon.json
if [ ! -L /var/lib/docker ]; then
    echo -e "${YELLOW}建立 /var/lib/docker -> ${DOCKER_DATA_ROOT} 軟連結，確保所有容器映像寫入 SD 卡...${NC}"
    /etc/init.d/dockerd stop 2>/dev/null || pkill -9 dockerd 2>/dev/null || true
    sleep 1
    if [ -d /var/lib/docker ]; then
        cp -rn /var/lib/docker/* "${DOCKER_DATA_ROOT}/" 2>/dev/null || true
        rm -rf /var/lib/docker
    fi
    ln -sf "${DOCKER_DATA_ROOT}" /var/lib/docker
    DOCKER_RESTART_NEEDED=1
fi

# 啟動或重啟 Docker 服務
if [ "${DOCKER_RESTART_NEEDED}" = "1" ]; then
    echo -e "${YELLOW}重新啟動 Docker 引擎套用 SD 卡儲存路徑...${NC}"
    if command -v systemctl &> /dev/null; then
        systemctl restart docker 2>/dev/null || systemctl restart dockerd 2>/dev/null || true
    elif [ -f /etc/init.d/dockerd ]; then
        /etc/init.d/dockerd restart 2>/dev/null || true
    elif [ -f /etc/init.d/docker ]; then
        /etc/init.d/docker restart 2>/dev/null || true
    else
        pkill -9 dockerd 2>/dev/null || true
        rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null || true
        sleep 1
        /usr/bin/dockerd > /dev/null 2>&1 &
    fi
else
    if command -v systemctl &> /dev/null; then
        systemctl enable docker 2>/dev/null || true
        systemctl start docker 2>/dev/null || true
    elif [ -f /etc/init.d/dockerd ]; then
        /etc/init.d/dockerd start 2>/dev/null || true
    elif [ -f /etc/init.d/docker ]; then
        /etc/init.d/docker start 2>/dev/null || true
    else
        if ! pgrep dockerd &> /dev/null; then
            /usr/bin/dockerd > /dev/null 2>&1 &
        fi
    fi
fi

# 等待 Docker UNIX Socket 建立就緒
WAIT_SEC=0
while [ ! -S /var/run/docker.sock ] && [ $WAIT_SEC -lt 15 ]; do
    sleep 1
    WAIT_SEC=$((WAIT_SEC + 1))
done

echo -e "${GREEN}✓ Docker 引擎運作正常 (Storage Root: ${DOCKER_DATA_ROOT})${NC}"

# 4. 檢查與自動下載 Docker Compose 至系統路徑 (可選項目，離線時自動略過)
echo -e "${YELLOW}[3/4] 檢測 Docker Compose...${NC}"
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✓ 檢測到 Docker Compose (Plugin 模式)${NC}"
elif command -v docker-compose &> /dev/null && docker-compose version &> /dev/null; then
    echo -e "${GREEN}✓ 檢測到 docker-compose (Standalone 模式)${NC}"
else
    # 快速檢測是否有外網連線 (3 秒連線逾時)，避免離線/工控內網環境卡死
    CAN_CONNECT=0
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 3 --max-time 5 https://github.com &> /dev/null; then
            CAN_CONNECT=1
        fi
    elif command -v wget &> /dev/null; then
        if wget -q --spider --timeout=3 --tries=1 https://github.com &> /dev/null; then
            CAN_CONNECT=1
        fi
    fi

    if [ "${CAN_CONNECT}" = "1" ]; then
        echo -e "${YELLOW}外網連線正常，下載 Docker Compose 至系統路徑 (/usr/bin/docker-compose)...${NC}"
        
        ARCH="$(uname -m)"
        if [ "${ARCH}" = "armv7l" ]; then
            ARCH="armv7"
        fi
        COMPOSE_URL="https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-${ARCH}"
        DEST_BIN="/usr/bin/docker-compose"
        
        if command -v curl &> /dev/null; then
            curl -SL --connect-timeout 5 --max-time 60 "${COMPOSE_URL}" -o "${DEST_BIN}" 2>/dev/null || true
        elif command -v wget &> /dev/null; then
            wget --timeout=15 --tries=2 -O "${DEST_BIN}" "${COMPOSE_URL}" 2>/dev/null || true
        fi

        if [ -s "${DEST_BIN}" ] && chmod +x "${DEST_BIN}" 2>/dev/null && "${DEST_BIN}" version &> /dev/null; then
            echo -e "${GREEN}✓ Docker Compose 成功下載至系統路徑 (/usr/bin/docker-compose)${NC}"
        else
            rm -f "${DEST_BIN}" /bin/docker-compose 2>/dev/null || true
            echo -e "${YELLOW}⚠️ Docker Compose 下載失敗，系統將退回使用標準 docker 命令。${NC}"
        fi
    else
        echo -e "${YELLOW}提示: 控制器無外網存取或連線逾時，自動略過下載。系統將使用標準 docker 命令啟動服務。${NC}"
    fi
fi

# 5. 配置 PFC200 開機自動等待 SD 卡與啟動服務 (S99autostart-gateway，開機直接呼叫 deploy.sh)
echo -e "${YELLOW}[4/4] 配置開機自動啟動守護服務 (等待 SD 卡掛載並呼叫 deploy.sh)...${NC}"

cat << 'EOF' > /etc/init.d/autostart-gateway
#!/bin/sh
### BEGIN INIT INFO
# Provides:          autostart-gateway
# Required-Start:    $all
# Short-Description: Autostart Tymetro Gateway after SD mount
### END INIT INFO

case "$1" in
    start)
        echo "Starting Tymetro Gateway Autostart..."
        (
            INSTALL_DIR="/media/sd/tymetro-gateway"
            LOG_FILE="${INSTALL_DIR}/autostart.log"
            
            # 1. 輪詢等待 SD 卡完全掛載 (最多等待 60 秒)
            MAX_RETRY=60
            RETRY=0
            while [ ! -f "${INSTALL_DIR}/deploy.sh" ] && [ $RETRY -lt $MAX_RETRY ]; do
                sleep 1
                RETRY=$((RETRY + 1))
            done

            # 2. 等待 3 秒確保檔案系統穩定
            sleep 3

            # 3. 直接呼叫 deploy.sh 執行 Docker 喚醒與容器啟動
            if [ -f "${INSTALL_DIR}/deploy.sh" ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] 偵測到 SD 卡就緒，開機呼叫 deploy.sh 啟動服務..." >> "${LOG_FILE}"
                chmod +x "${INSTALL_DIR}/deploy.sh" 2>/dev/null || true
                "${INSTALL_DIR}/deploy.sh" >> "${LOG_FILE}" 2>&1
            fi
        ) &
        ;;
    stop)
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac
exit 0
EOF

chmod +x /etc/init.d/autostart-gateway
mkdir -p /etc/rc.d /etc/rc3.d /etc/rc5.d 2>/dev/null || true
ln -sf /etc/init.d/autostart-gateway /etc/rc.d/S99autostart-gateway 2>/dev/null || true
ln -sf /etc/init.d/autostart-gateway /etc/rc3.d/S99autostart-gateway 2>/dev/null || true
ln -sf /etc/init.d/autostart-gateway /etc/rc5.d/S99autostart-gateway 2>/dev/null || true

# 備援寫入 /etc/rc.local (若系統支援 rc.local)
if [ -f /etc/rc.local ]; then
    if ! grep -q "tymetro-gateway/deploy.sh" /etc/rc.local; then
        echo "(sleep 10 && /media/sd/tymetro-gateway/deploy.sh > /media/sd/tymetro-gateway/autostart.log 2>&1) &" >> /etc/rc.local
    fi
fi

echo -e "${GREEN}✓ PFC200 開機自動等待 SD 卡與啟動服務配置完成 (/etc/init.d/autostart-gateway -> S99)${NC}"

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 [階段 1] 環境預備、Docker 搬移至 SD 卡與開機自啟配置完成！${NC}"
echo -e "${GREEN} --------------------------------------------------- ${NC}"
echo -e "${YELLOW} 📢 請進行 [階段 2]：使用 FTP / SFTP 將專案檔案傳送至：${NC}"
echo -e "${YELLOW}    📂 ${INSTALL_DIR}${NC}"
echo -e "${GREEN} --------------------------------------------------- ${NC}"
echo -e "${YELLOW} 📢 完成 FTP 上傳後，請執行 [階段 3] 部署腳本：${NC}"
echo -e "${YELLOW}    cd ${INSTALL_DIR} && sudo chmod +x deploy.sh && sudo ./deploy.sh${NC}"
echo -e "${GREEN}=====================================================${NC}"
