# Docker Compose 分檔案架構與營運維護指南 (WAGO PFC300)

為利於在 WAGO PFC300 進行**分階段初次安裝**與**日後獨立更版**，專案已被拆分為以下 Docker Compose 檔案結構：

---

## 📁 檔案結構說明

| 設定檔名稱 | 涵蓋服務 (Services) | 用途說明 |
| :--- | :--- | :--- |
| **`docker-compose.infra.yml`** | `mosquitto`, `portainer`, `redis`, `nginx` | **基礎設施層 (Infra)**：底層服務、MQTT Broker、監控與網關。建立獨立橋接網路 `tymetro-net`。 |
| **`docker-compose.apps.yml`** | `backend`, `frontend` | **應用程式層 (Apps)**：閘道器業務邏輯後端與前端 SPA UI。加入 `tymetro-net` 網路。 |
| **`docker-compose.yml`** | 上述所有 6 個服務 | **完整單一設定檔**：適合一口氣完成全系統安裝。 |

---

## 🚀 拆檔營運與更版操作情境 (Operational Use Cases)

### 情境 1：初次安裝 (首次部署)

若要一口氣安裝整個 Gateway 系統：

```bash
docker compose up -d --build
```

---

### 情境 2：只更新/重構應用程式 (Frontend / Backend 更版)

**最常見的日後維護情境**！當前端或後端程式碼變更時，完全不需要重啟 Mosquitto、Redis 或 Portainer：

```bash
# 僅重新構建與升級 Backend & Frontend (不影響基礎設施)
docker compose -f docker-compose.apps.yml up -d --build
```

若只想單獨更版**後端**或**前端**：
```bash
# 僅更新後端
docker compose -f docker-compose.apps.yml up -d --build backend

# 僅更新前端
docker compose -f docker-compose.apps.yml up -d --build frontend
```

---

### 情境 3：基礎設施單獨維護

當需要變更 `nginx.conf` 或 `mosquitto.conf` 等底層設定時：

```bash
docker compose -f docker-compose.infra.yml up -d
```

---

### 情境 4：查看個別模組日誌

```bash
# 僅查看應用程式 (Backend/Frontend) 日誌
docker compose -f docker-compose.apps.yml logs -f

# 僅查看基礎設施 (Mosquitto/Redis/Nginx) 日誌
docker compose -f docker-compose.infra.yml logs -f
```
