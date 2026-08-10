#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway - 階段 1：環境預備與目錄建立腳本 (PFC200)
# 說明: 
# 1. 建立 SD 卡目標目錄結構與內部子目錄
# 2. 將 Docker 儲存路徑 (data-root) 轉移至 SD 卡 (防止 Flash 爆滿)
# 3. 檢查並下載 Docker Compose 至 SD 卡 / 系統路徑
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
echo -e "${GREEN} 🛠️ [階段 1] 建立部署目錄、搬移 Docker 至 SD 卡與環境預備${NC}"
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

# 啟動或重啟 Docker 服務
if [ "${DOCKER_RESTART_NEEDED}" = "1" ]; then
    echo -e "${YELLOW}重新啟動 Docker 引擎套用 SD 卡儲存路徑...${NC}"
    if command -v systemctl &> /dev/null; then
        systemctl restart docker 2>/dev/null || true
    elif [ -f /etc/init.d/docker ]; then
        /etc/init.d/docker restart 2>/dev/null || true
    fi
else
    if command -v systemctl &> /dev/null; then
        systemctl enable docker 2>/dev/null || true
        systemctl start docker 2>/dev/null || true
    elif [ -f /etc/init.d/docker ]; then
        /etc/init.d/docker start 2>/dev/null || true
    fi
fi
echo -e "${GREEN}✓ Docker 引擎運作正常 (Storage Root: ${DOCKER_DATA_ROOT})${NC}"

# 4. 檢查與自動下載 Docker Compose 至系統路徑
echo -e "${YELLOW}[3/3] 檢測/安裝 Docker Compose...${NC}"
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✓ 檢測到 Docker Compose (Plugin 模式)${NC}"
elif command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓ 檢測到 docker-compose (Standalone 模式)${NC}"
else
    echo -e "${YELLOW}未檢測到 Docker Compose，下載至系統路徑 (/usr/bin/docker-compose)...${NC}"
    
    ARCH="$(uname -m)"
    if [ "${ARCH}" = "armv7l" ]; then
        ARCH="armv7"
    fi
    COMPOSE_URL="https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-${ARCH}"
    DEST_BIN="/usr/bin/docker-compose"
    
    if command -v curl &> /dev/null; then
        curl -SL "${COMPOSE_URL}" -o "${DEST_BIN}" 2>/dev/null || true
    elif command -v wget &> /dev/null; then
        wget -O "${DEST_BIN}" "${COMPOSE_URL}" 2>/dev/null || true
    fi

    if [ -f "${DEST_BIN}" ]; then
        chmod +x "${DEST_BIN}"
        echo -e "${GREEN}✓ Docker Compose 成功下載至系統路徑 (/usr/bin/docker-compose)${NC}"
    else
        echo -e "${YELLOW}⚠️ 下載失敗 (無外網存取)，系統將退回使用標準 docker 命令。${NC}"
    fi
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 [階段 1] 環境預備、Docker 搬移至 SD 卡完成！${NC}"
echo -e "${GREEN} --------------------------------------------------- ${NC}"
echo -e "${YELLOW} 📢 請進行 [階段 2]：使用 FTP / SFTP 將專案檔案傳送至：${NC}"
echo -e "${YELLOW}    📂 ${INSTALL_DIR}${NC}"
echo -e "${GREEN} --------------------------------------------------- ${NC}"
echo -e "${YELLOW} 📢 完成 FTP 上傳後，請執行 [階段 3] 部署腳本：${NC}"
echo -e "${YELLOW}    cd ${INSTALL_DIR} && sudo chmod +x deploy.sh && sudo ./deploy.sh${NC}"
echo -e "${GREEN}=====================================================${NC}"
