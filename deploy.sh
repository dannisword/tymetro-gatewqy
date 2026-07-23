#!/usr/bin/env bash
# =================================================================
# HVAC Edge Gateway 一鍵部署與安裝腳本 (PFC200 / Linux Native)
# =================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🚀 開始安裝 HVAC Edge Gateway (Native systemd + Nginx)${NC}"
echo -e "${GREEN}=====================================================${NC}"

# 1. 檢查是否以 root 權限執行
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}錯誤: 請以 root 權限或 sudo 執行此安裝腳本。${NC}"
  exit 1
fi

INSTALL_DIR="/opt/tymetro-gateway"
BACKEND_DIR="${INSTALL_DIR}/tymetro-gateway-backend"
FRONTEND_DIR="${INSTALL_DIR}/tymetro-gateway-frotend"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. 更新系統套件庫並安裝必備元件
echo -e "${YELLOW}[1/6] 安裝系統依賴套件 (Python3, Nginx, SQLite3, Node.js)...${NC}"
if command -v apt-get &> /dev/null; then
    apt-get update -y
    apt-get install -y python3 python3-venv python3-pip nginx sqlite3 curl
elif command -v opkg &> /dev/null; then
    # WAGO PFC200 OpenWrt/Linux opkg
    opkg update
    opkg install python3 python3-venv python3-pip nginx sqlite3-cli
fi

# 3. 部署專案程式碼至 /opt/tymetro-gateway
echo -e "${YELLOW}[2/6] 部署專案檔案至 ${INSTALL_DIR}...${NC}"
mkdir -p "${INSTALL_DIR}"
cp -r "${SCRIPT_DIR}/tymetro-gateway-backend" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/tymetro-gateway-frotend" "${INSTALL_DIR}/"

# 4. 建立 Python 虛擬環境與安裝 Python 依賴
echo -e "${YELLOW}[3/6] 設定 Python 虛擬環境與安裝依賴...${NC}"
cd "${BACKEND_DIR}"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# 5. 編譯 Vue 3 前端靜態資源 (如果有 Node.js/npm)
echo -e "${YELLOW}[4/6] 檢查並編譯 Vue 3 前端網頁...${NC}"
if command -v npm &> /dev/null; then
    cd "${FRONTEND_DIR}"
    npm install
    npm run build
    echo -e "${GREEN}Vue 3 前端編譯成功！${NC}"
else
    echo -e "${YELLOW}警告: 未檢測到 npm/node，若已有預先編譯好的 dist 目錄將直接使用。${NC}"
fi

# 6. 設定 systemd 服務
echo -e "${YELLOW}[5/6] 配置 systemd 背景常駐服務 (tymetro-gateway.service)...${NC}"
cat << 'EOF' > /etc/systemd/system/tymetro-gateway.service
[Unit]
Description=HVAC Edge Gateway Backend & Polling Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tymetro-gateway/tymetro-gateway-backend
ExecStart=/opt/tymetro-gateway/tymetro-gateway-backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 5400 --workers 1
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable tymetro-gateway.service
systemctl restart tymetro-gateway.service

# 7. 配置 Nginx 反向代理
echo -e "${YELLOW}[6/6] 配置 Nginx 網頁伺服器與 WebSocket 代理...${NC}"
mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

cat << 'EOF' > /etc/nginx/sites-available/tymetro-gateway
server {
    listen 80;
    server_name _;

    location / {
        root /opt/tymetro-gateway/tymetro-gateway-frotend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5400;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api/v1/ws/ {
        proxy_pass http://127.0.0.1:5400;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
EOF

ln -sf /etc/nginx/sites-available/tymetro-gateway /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

if nginx -t &> /dev/null; then
    systemctl restart nginx
    echo -e "${GREEN}Nginx 啟動成功！${NC}"
else
    echo -e "${RED}Nginx 設定驗證失敗，請檢查設定檔。${NC}"
fi

echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN} 🎉 HVAC Edge Gateway 一鍵部署完成！${NC}"
echo -e "${GREEN} 🌐 Web 管理介面: http://<PFC200_IP>${NC}"
echo -e "${GREEN} 🔍 服務狀態查詢: sudo systemctl status tymetro-gateway${NC}"
echo -e "${GREEN} 📜 即時日誌監看: sudo journalctl -u tymetro-gateway -f${NC}"
echo -e "${GREEN}=====================================================${NC}"
