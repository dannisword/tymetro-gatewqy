# HVAC Edge Gateway (PFC200 控制器邊緣閘道系統)

本專案專為 **WAGO PFC200 控制器** 設計，提供 HVAC 邊緣感測數據收集、Modbus 輪詢、SQLite 批次儲存、桃捷雲 Cloud MQTT 抛轉與 Vue 3 監控網頁。

---

## ⚡ 快速 3 階段 Docker 部署指南

完整的部署說明請參閱 [docs/deployment-guide.md](file:///Users/dannis/Documents/Repositories/dannis/wago/tymetro-gateway/docs/deployment-guide.md)。

```text
[階段 1: 環境預備]  ──>  [階段 2: FTP 傳送檔案]  ──>  [階段 3: 一鍵啟動]
 (setup.sh 腳本)          (電腦端上傳至 SD 卡)         (deploy.sh 腳本)
```

### 1️⃣ 階段一：環境預備 (PFC200 端)
將 `setup.sh` 上傳至 PFC200 並執行：
```bash
sudo chmod +x setup.sh
sudo ./setup.sh
```
> *自動建立 `/media/sd/tymetro-gateway` 目錄結構，將 Docker `data-root` 搬移至 SD 卡（保護 Flash 不爆滿），並自動下載 Docker Compose。*

---

### 2️⃣ 階段二：電腦端編譯與 FTP 上傳 (電腦端)
1. 在電腦端執行前端編譯：
   ```bash
   cd tymetro-gateway-frotend && npm run build
   ```
2. 透過 FTP 將專案檔案傳送至 PFC200 控制器的 `/media/sd/tymetro-gateway/`。
   *(前端僅需上傳 `tymetro-gateway-frotend/dist` 目錄與 `nginx.conf`)*

---

### 3️⃣ 階段三：一鍵構建與啟動容器 (PFC200 端)
在 PFC200 控制器執行：
```bash
cd /media/sd/tymetro-gateway
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

---

## 🌐 服務存取位址

部署完成後可透過瀏覽器與工具存取：
- **前端 Web UI 監控網頁**：`http://<PFC200_IP>:8080`
- **FastAPI Swagger API 文件**：`http://<PFC200_IP>:8080/docs`
- **MQTT Broker**：`tcp://<PFC200_IP>:1883`

---

## 🛠️ 常見運維指令

- **查看容器運行狀態**：`docker ps`
- **即時日誌監看**：`docker compose logs -f`
- **熱重啟前端 (更新 dist)**：`docker compose restart frontend`
- **更新後端服務**：`docker compose up -d --build backend`
- **一鍵解除安裝清理**：`sudo ./uninstall.sh`
