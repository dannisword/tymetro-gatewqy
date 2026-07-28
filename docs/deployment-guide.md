# WAGO PFC200 HVAC Edge Gateway Docker 部署指南 (3 階段最新版)

本指南專為 **WAGO PFC200 控制器** 設計，採用 **Docker 容器化架構** 部署 HVAC Edge Gateway 全套服務（MQTT Broker + Backend FastAPI + Frontend Vue 3/Nginx）。

---

## 🏗️ 系統架構簡介

- **部署根目錄**：`/media/sd/tymetro-gateway` (SD 卡)
- **Docker Data Root**：`/media/sd/docker-data` (將容器與 Image 移至 SD 卡，避免填滿 PFC200 內建 Flash)
- **MQTT Broker**：`eclipse-mosquitto:2.0` 容器 (Port `1883`)
- **後端 API 與 Polling 服務**：FastAPI / Uvicorn 容器 (Port `5400`)
- **前端 Web UI & Nginx 反向代理**：`nginx:alpine` 容器 (Port `8080`)
  - `http://<PFC200_IP>:8080` ➔ Vue 3 SPA 網頁
  - `http://<PFC200_IP>:8080/docs` ➔ Swagger API 文件
  - `http://<PFC200_IP>:8080/api/...` ➔ RESTful API 轉發至 `backend:5400`
- **前端免編譯機制**：電腦端執行 `npm run build` 後僅上傳 `dist/` 與 `nginx.conf`，無須在 PFC200 安裝 Node.js 或編譯。

---

## 🛠️ 事前準備：啟用 PFC200 Docker

1. 開啟瀏覽器存取 WAGO 控制器網頁管理介面 (WBM)：`https://<PFC200_IP>` *(預設帳號: `admin` / 密碼: `wago`)*
2. 進入左側選單 **Configuration** ➔ **Docker**。
3. 勾選 **Enable Docker**，並點擊 **Submit** 儲存套用。

---

## 🚀 三階段極速部署流程

```text
[階段 1: 環境預備]  ──>  [階段 2: FTP 傳送 dist/ 與後端檔]  ──>  [階段 3: 一鍵啟動]
 (setup.sh 腳本)             (上傳至 SD 卡)                (deploy.sh 腳本)
```

---

### 1️⃣ 階段一：環境預備與 Docker 搬移至 SD 卡 (PFC200 端)

透過 SSH 登入 PFC200 控制器，上傳並執行 `setup.sh` 腳本：

```bash
sudo chmod +x setup.sh
sudo ./setup.sh
```

**`setup.sh` 自動完成的項目**：
1. 建立 SD 卡目標目錄與結構：
   - `/media/sd/tymetro-gateway`
   - `/media/sd/tymetro-gateway/tymetro-gateway-frotend/dist`
   - `/media/sd/tymetro-gateway/tymetro-gateway-backend/app/logs`
2. 將 Docker 數據根目錄 (`data-root`) 自動配置並移至 `/media/sd/docker-data`，保護 Flash 不爆滿。
3. 自動下載並配置 `docker-compose` 二進位檔至 SD 卡 (`/media/sd/bin/docker-compose`)。
4. 設定專案目錄權限 `chmod -R 777`，確保後續 FTP 上傳與 Docker 讀寫完全無權限障礙。

---

### 2️⃣ 階段二：電腦端編譯與 FTP 上傳 (電腦端手動)

#### Step 1: 電腦端產出前端 `dist/` 靜態包
在開發電腦的前端目錄執行：
```bash
cd tymetro-gateway-frotend
npm run build
# 產出 dist/ 目錄
```

#### Step 2: 透過 FTP / SFTP 上傳檔案
使用 FTP 工具 (如 FileZilla, WinSCP) 將專案檔案傳送至 PFC200 的 `/media/sd/tymetro-gateway/`：

```text
/media/sd/tymetro-gateway/
├── deploy.sh                        # 部署腳本
├── docker-compose.yml               # 容器編排檔
├── mosquitto.conf                   # MQTT 設定檔
├── tymetro-gateway-backend/         # 後端服務檔
│   ├── Dockerfile
│   ├── main.py
│   ├── gateway.yaml
│   ├── .env
│   ├── requirements.txt
│   └── app/
└── tymetro-gateway-frotend/         # 前端發佈檔 (僅需上傳 dist 與 nginx.conf)
    ├── dist/                        # 👈 前端編譯產出物
    └── nginx.conf                   # 👈 Nginx 反向代理設定
```

---

### 3️⃣ 階段三：構建與啟動 Docker 容器 (PFC200 端)

登入 PFC200 終端機，執行一鍵啟動腳本：

```bash
cd /media/sd/tymetro-gateway
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

**`deploy.sh` 自動完成的項目**：
1. 自動檢測 `docker compose` 環境。
2. 啟動 `mosquitto` (Port 1883)、構建啟動 `backend` (Port 5400) 與載入 `frontend` Nginx (Port 80)。
3. 輸出服務驗證 URL。

---

## 🔍 驗證部署與監控

### 1. 檢查容器運行狀態
```bash
docker ps
```
*應顯示 `tymetro-mosquitto`、`tymetro-gateway-backend` 與 `tymetro-gateway-frontend` 三個容器狀況為 `Up`。*

### 2. 測試網頁與 API 存取
* **Web UI 介面**：`http://<PFC200_IP>:8080`
* **Swagger API 文件**：`http://<PFC200_IP>:8080/docs`
* **REST API 檢查**：`curl http://<PFC200_IP>:8080/api/v1/status`

### 3. 查看即時服務日誌
```bash
docker compose logs -f
```

---

## 🔄 日常更版與維護

### 更新前端頁面 (UI Fix / 調整)
1. 電腦端重新 `npm run build`。
2. FTP 將最新的 `dist/` 覆蓋至 `/media/sd/tymetro-gateway/tymetro-gateway-frotend/dist/`。
3. 重啟前端容器 (1 秒完成)：
   ```bash
   docker compose restart frontend
   ```

### 更新 Python 後端程式碼
1. FTP 覆蓋後端更新檔案。
2. 重建後端容器（**前端與 Mosquitto 不會中斷**）：
   ```bash
   docker compose up -d --build backend
   ```

---

## 🗑️ 完全卸載 (Uninstallation)

若需清理容器與刪除 SD 卡部署目錄，執行：

```bash
cd /media/sd/tymetro-gateway
sudo chmod +x uninstall.sh
sudo ./uninstall.sh
```
