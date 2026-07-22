# 捷運智慧運維系統 - 前端開發與編譯部署說明文件

本文件旨在說明前端專案的開發環境架構、本地開發步驟、編譯打包指令、環境變數配置以及 Docker 與 Nginx 部署設定。

---

## 🛠 1. 技術棧與依賴 (Technology Stack)

本前端專案採用現代化的 Web 技術開發：
- **核心框架**: [Vue 3](https://vuejs.org/) (Composition API, `<script setup>`)
- **程式語言**: [TypeScript](https://www.typescriptlang.org/)
- **建構工具**: [Vite](https://vite.dev/) (提供極速的開發熱更新與 Rollup 打包)
- **UI 元件庫**: [Element Plus](https://element-plus.org/) & [Tailwind CSS](https://tailwindcss.com/) (自訂語義化 Light/Dark 模式主題)
- **狀態管理**: [Pinia](https://pinia.vuejs.org/) (搭配持久化套件 `pinia-plugin-persistedstate`)
- **路由管理**: [Vue Router](https://router.vuejs.org/)
- **其他套件**:
  - `mqtt`: 用於即時感測器數據的訂閱與通訊。
  - `ag-grid-vue3`: 渲染高效能的資料表格。
  - `echarts`: 視覺化圖表繪製。
  - `axios`: API 請求封裝。
  - `xlsx`: 報表匯出與 Excel 處理。

---

## 💻 2. 開發環境準備 (Prerequisites)

- **Node.js**: 建議安裝 **v18 或以上** 的 LTS 版本。
- **套件管理器**: 專案中附帶了 `yarn.lock` 與 `package-lock.json`。推薦使用 **Yarn** 進行套件管理。

### 📦 安裝依賴步驟
在專案根目錄下執行：
```bash
yarn install
# 或者使用 npm
npm install
```

---

## 🚀 3. 本地開發與常用指令 (Scripts)

在 `package.json` 中配置了以下腳本命令：

| 命令 | 實際執行內容 | 說明 |
| :--- | :--- | :--- |
| **`yarn dev`** | `vite --mode development` | 啟動本地開發伺服器，載入 `.env.development` 設定。 |
| **`yarn stage`** | `vite --mode stage` | 啟動測試環境的本地開發服務，載入 `.env.stage` 設定。 |
| **`yarn build:pro`** | `vite build --mode production` | 編譯正式環境的靜態檔案（不進行型別檢查，速度較快），載入 `.env.production` 設定。 |
| **`yarn build`** | `vue-tsc -b && vite build` | 先執行 TypeScript 靜態型別檢查，再進行標準生產環境打包。 |
| **`yarn preview`** | `vite preview` | 本地預覽編譯後（`dist` 目錄）的靜態網站效果。 |

### 💡 本地開發啟動
```bash
yarn dev
```
啟動後預設連線網址為 `http://localhost:5173/`。

---

## ⚙️ 4. 環境變數配置 (Environment Variables)

專案提供三種主要環境設定檔，主要參數如下：

### 📝 欄位說明

- `VITE_BASE_API`: 前端 API 請求之基礎路徑 (通常為 `/`)。
- `VITE_PROXY_TARGET`: 開發階段 Vite Dev Server 代理轉發 API 的目標後端地址。
- `VITE_MQTT_BROKER` / `VITE_MQTT_PORT` / `VITE_MQTT_PROTOCOL`: 即時 MQTT 連線資訊。
- `VITE_LOG_LEVEL`: 控制前端日誌輸出等級 (`debug`、`info`、`error`)。

### 1. 本地開發環境 (`.env.development`)
```ini
ENV = 'development'
NODE_ENV = 'development'
VITE_BASE_API = /
VITE_PROXY_TARGET = http://127.0.0.1:5400 # 轉發至本地運行之 API 後端服務
VITE_MQTT_BROKER = "220.133.144.73"
VITE_MQTT_PORT = "9001"
VITE_MQTT_PROTOCOL = "ws"
VITE_LAYOUT_MODE = 1-column-layout
VITE_LOG_LEVEL = debug
```

### 2. 正式環境 (`.env.production`)
```ini
ENV = 'production'
NODE_ENV = 'production'
VITE_BASE_API = /
VITE_PROXY_TARGET = http://127.0.0.1:5400
VITE_MQTT_BROKER = "220.133.144.73"
VITE_MQTT_PORT = "9001"
VITE_MQTT_PROTOCOL = "ws"
VITE_LAYOUT_MODE = 1-column-layout
VITE_LOG_LEVEL = error
```

---

## 🐳 5. 編譯與 Docker 部署 (Build & Docker Deployment)

生產環境的部署採用 **Docker + Nginx** 的靜態託管架構。

### 📁 Nginx 代理配置 (`nginx.conf`)
前端 SPA 需要特別注意路由重新整理 404 問題，Nginx 透過 `try_files` 將所有未知路徑重導向至 `index.html`。
同時配置了 `/api` 請求的反向代理至後端：
```nginx
server {
    listen       8080;
    server_name  localhost;

    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # 反向代理前端 API 請求至後端容器
    location /api {
        proxy_pass http://127.0.0.1:5400; # 建議在 compose 中改為後端 container 名稱與 port
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    error_page   500 502 503 504  /50x.html;
    location = /50x.html {
        root   /usr/share/nginx/html;
    }
}
```

### 📦 專案打包與 Docker 鏡像建置

#### 方式 A：外部編譯 + Docker 複製 (目前 `Dockerfile` 實作)
此方式下，編譯動作於 Docker 外部進行，可以減少 Docker 映像檔的建置時間與雜訊：

1. **在實體主機上執行編譯**
   ```bash
   yarn build:pro
   ```
   這會產生 `dist` 資料夾，內含壓縮優化過後的 HTML/JS/CSS 靜態資源。

2. **建置 Docker 鏡像**
   使用目錄下的 `Dockerfile`：
   ```dockerfile
   FROM nginx:alpine
   COPY dist /usr/share/nginx/html
   COPY nginx.conf /etc/nginx/conf.d/default.conf
   EXPOSE 80
   ```
   建置指令：
   ```bash
   docker build -t tymetro-frontend:latest .
   ```

#### 方式 B：多階段編譯 (推薦改版方向)
若要在 CI/CD 伺服器或無 Node 環境的環境中建置，可使用多階段 Dockerfile（先 Build 再 Copy）：
```dockerfile
# 階段 1: 編譯
FROM node:18-alpine AS build-stage
WORKDIR /app
COPY package.json yarn.lock ./
RUN yarn install
COPY . .
RUN yarn build:pro

# 階段 2: 部署
FROM nginx:alpine
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

---

## 🤖 6. CI/CD 自動化工作流 (GitHub Actions)

專案預置了 GitHub Workflow `.github/workflows/deploy.yml`（配置在遠端倉庫中），其自動化部署流程如下：
1. **觸發條件**: 推送 (Push) 程式碼至 `main` 主分支。
2. **自動建置**: 於 GitHub Runner 中啟動 Node 環境，拉取相依套件並執行前端編譯 (`yarn build:pro` 或多階段編譯)。
3. **推送映像檔**: 將建置完成的 Docker Image 推送至 GitHub Container Registry (GHCR)。
4. **觸發更版**: 調用 Portainer Webhook 網址，通知 Portainer 服務拉取最新的 Image 並重新部署前端容器。
