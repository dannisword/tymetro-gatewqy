# HVAC Edge Gateway (PFC200 / Linux) 原生 Native 部署指南

本指南專為 **WAGO PFC200 控制器** 或 **嵌入式 Linux 主機** 設計。本架構已完全移除了 Docker Compose 與 MQTT Broker，改採 Linux 原生 **systemd + Nginx + Python venv + Unix Domain Socket IPC**，能節省超過 **60% RAM 與 CPU** 開銷並大幅延長 SD 卡/Flash 壽命。

---

## 🏗️ 系統架構簡介

- **前端 (Web UI)**: Vue 3 靜態編譯包，由 **Nginx** 託管 (Port 80/443)。
- **後端 (API & Polling Service)**: Python 3.10+ FastAPI 服務，透過 **systemd** 常駐執行。
- **邊緣 IPC 通訊**: Unix Domain Socket (`/tmp/hvac_ipc.sock`)，< 0.2ms 超低延遲。
- **儲存**: SQLite WAL 模式 + Store & Forward 暫存佇列。

## ⚡ 極速一鍵安裝 (One-Click Auto Install)

在 PFC200 控制器或 Linux 主機上複製專案後，直接執行專案根目錄下的 `deploy.sh` 即可完成全自動部署：

```bash
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

一鍵腳本會自動完成：
1. 套件依賴安裝 (`python3`, `nginx`, `sqlite3`...)
2. Python venv 虛擬環境建立與 `requirements.txt` 安裝
3. Vue 3 前端編譯 (npm build)
4. systemd 背景常駐服務配置與啟動 (`tymetro-gateway.service`)
5. Nginx Web 伺服器與 API / WebSocket 反向代理配置

---

## 🛠️ 第一步：手動環境預備 (Prerequisites)

在 Linux / PFC200 上安裝必要套件：

```bash
# Ubuntu / Debian / PFC200 (OpenWrt/Linux)
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx sqlite3
```

---

## 📦 第二步：部署專案碼與虛擬環境

### 1. 複製與放置程式碼
將專案放置於 `/opt/tymetro-gateway` 目錄：

```bash
sudo mkdir -p /opt/tymetro-gateway
sudo chown -R $USER:$USER /opt/tymetro-gateway
cd /opt/tymetro-gateway

# 複製後端與前端源碼至 /opt/tymetro-gateway
```

### 2. 建立 Python 虛擬環境與安裝依賴
```bash
cd /opt/tymetro-gateway/tymetro-gateway-backend

# 建立 venv
python3 -m venv .venv
source .venv/bin/activate

# 安裝依賴套件 (含 PyYAML, FastAPI, uvicorn...)
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ 第三步：配置檔設定 (`gateway.yaml` & `.env`)

### 1. 編輯 `.env` (環境變數)
```bash
cat << 'EOF' > /opt/tymetro-gateway/tymetro-gateway-backend/.env
APP_MODE=production
SERVER_HOST=127.0.0.1
SERVER_PORT=5400
LOG_PATH=app/logs/gateway.log
SQLITE_DB_PATH=gateway.db
SECRET_KEY=your-production-secret-key-change-me
EOF
```

### 2. 編輯 `gateway.yaml` (邊緣與 PFC 控制器點位)
```yaml
gateway:
  id: "GW-TAU-01"
  name: "桃園捷運 冰水機房 Gateway 01"
  location: "桃機 T2 冰水主機房"
  poll_interval_ms: 1000

network:
  central_server:
    host: "10.200.1.50"
    port: 9001
    tls_enabled: false
    reconnect_delay_sec: 5
  ipc_socket_path: "/tmp/hvac_ipc.sock"

database:
  db_path: "gateway.db"
  batch_flush_sec: 10

devices:
  - id: "PFC001"
    name: "AHU-01 冰水風機"
    ip: "192.168.10.101"
    port: 502
    slave_id: 1
    registers:
      - name: "temp"
        address: 0
        type: "INT16"
        scale: 0.1
        unit: "°C"
      - name: "humidity"
        address: 1
        type: "INT16"
        scale: 0.1
        unit: "%"
```

---

## 🚀 第四步：建立 systemd 服務 (背景常駐)

建立 `/etc/systemd/system/tymetro-gateway.service` 服務檔：

```bash
sudo cat << 'EOF' | sudo tee /etc/systemd/system/tymetro-gateway.service
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
```

### 啟動並設定開機自動執行：
```bash
sudo systemctl daemon-reload
sudo systemctl enable tymetro-gateway
sudo systemctl start tymetro-gateway

# 檢查狀態
sudo systemctl status tymetro-gateway
```

---

## 🌐 第五步：部署前端與 Nginx 反向代理

### 1. 編譯前端網頁 (Vue 3)
```bash
cd /opt/tymetro-gateway/tymetro-gateway-frotend
npm install
npm run build
# 編譯產出位於 dist/
```

### 2. 設定 Nginx (`/etc/nginx/sites-available/tymetro-gateway`)
```nginx
server {
    listen 80;
    server_name _;

    # 1. 靜態網頁 (Vue 3)
    location / {
        root /opt/tymetro-gateway/tymetro-gateway-frotend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 2. REST API 代理至 Backend
    location /api/ {
        proxy_pass http://127.0.0.1:5400;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 3. Native WebSocket 差分推播代理
    location /api/v1/ws/ {
        proxy_pass http://127.0.0.1:5400;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

### 3. 啟用 Nginx 站點
```bash
sudo ln -sf /etc/nginx/sites-available/tymetro-gateway /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔍 第六步：驗證部署

1. **瀏覽器訪問**: 打開 `http://<PFC200_IP>` 即可看到 Vue 3 狀態網頁。
2. **API 健康檢查**: `curl http://127.0.0.1:5400/api/v1/status`
3. **IPC Socket 檢查**: `ls -l /tmp/hvac_ipc.sock` (回應權限與狀態)。
4. **即時日誌監看**: `journalctl -u tymetro-gateway -f`
