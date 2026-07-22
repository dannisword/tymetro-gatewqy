# Vue 3 + TypeScript + Vite

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).


## router
yarn add vue-router
yarn add vite-plugin-environment

## element plus
yarn add element-plus

## tailwindcss
npm install -D tailwindcss@3 postcss autoprefixer 
npm install postcss-loader

## pinia
yarn add pinia
yarn add pinia-plugin-persistedstate
yarn add unplugin-auto-import
yarn add unplugin-vue-components
## axios
yarn add axios
## dayjs
yarn add dayjs
## lodash
yarn add lodash
## i18n
yarn add vue-i18n
## mdi icon
yarn add @mdi/js


## ag grid
yarn add ag-grid-vue3
yarn add ag-grid-community



{
  "templateCode": "org-records",
  "templateName": "組織",
  "content": {},
  "component": "",
  "version": "1.0",
  "id": 0
}


# Tailwind CSS Config 說明

此專案使用 [Tailwind CSS](https://tailwindcss.com/) 作為 UI 樣式框架，並自訂了主題顏色與 Light/Dark 模式。以下說明 `tailwind.config.js` 的設定與使用方式。

## 📂 設定檔位置

```
/tailwind.config.js
```

內容摘要：
```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // 靜態色（不隨主題切換）
        primary: { ... },
        secondary: { ... },
        danger: { ... },
        warning: { ... },
        success: { ... },
        muted: { ... },

        // 語義色（使用 CSS 變數，會隨 light/dark 切換）
        bg: 'rgb(var(--bg) / <alpha-value>)',
        text: 'rgb(var(--fg) / <alpha-value>)',
        card: 'rgb(var(--card) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',
        theme: 'rgb(var(--primary) / <alpha-value>)',

        success: 'rgb(var(--success) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        error: 'rgb(var(--error) / <alpha-value>)',
        info: 'rgb(var(--info) / <alpha-value>)',

        bgSecondary: 'rgb(var(--bg-secondary) / <alpha-value>)',
        input: 'rgb(var(--input) / <alpha-value>)',
        ringc: 'rgb(var(--ring) / <alpha-value>)',

        primaryBrand: 'rgb(var(--primary-brand) / <alpha-value>)',
      },
    },
  },
  plugins: [],
};
```

---

## 🌗 Light / Dark 模式

- 設定 `darkMode: 'class'`  
  → 代表只要在 HTML 或外層元素加上 `.dark` class，即可切換至 Dark 模式。

範例：
```html
<html class="dark">
  <body class="bg-bg text-text">
    <div class="bg-card border border-border p-4">
      <h1 class="text-theme">Hello World</h1>
    </div>
  </body>
</html>
```

---

## 🎨 顏色說明

### 1. 靜態色 (不會因主題切換而變動)
- `primary`：主品牌色  
- `secondary`：次要色  
- `danger`：危險/錯誤色  
- `warning`：警告色  
- `success`：成功色  
- `muted`：中性色階（灰階）

使用範例：
```html
<button class="bg-primary-500 text-white px-4 py-2 rounded">
  Primary Button
</button>

<p class="text-danger-500">刪除操作不可恢復</p>
```

---

### 2. 語義色 (由 CSS 變數控制，隨 Light/Dark 切換)
這些顏色對應到 `:root` 與 `.dark` 模式下的 CSS 變數，可自由調整。

| 顏色名稱       | CSS 變數           | 用途           |
|----------------|--------------------|----------------|
| `bg`           | `--bg`             | 背景色         |
| `text`         | `--fg`             | 文字顏色       |
| `card`         | `--card`           | 卡片背景       |
| `border`       | `--border`         | 邊框顏色       |
| `theme`        | `--primary`        | 主色調         |
| `success`      | `--success`        | 成功提示       |
| `warning`      | `--warning`        | 警告提示       |
| `error`        | `--error`          | 錯誤提示       |
| `info`         | `--info`           | 資訊提示       |
| `bgSecondary`  | `--bg-secondary`   | 次背景色       |
| `input`        | `--input`          | 輸入框背景     |
| `ringc`        | `--ring`           | 聚焦框陰影顏色 |
| `primaryBrand` | `--primary-brand`  | 品牌主色       |

---

## 🛠 使用方式

### CSS 變數定義範例
```css
:root {
  --bg: 255 255 255;      /* 白色背景 */
  --fg: 15 23 42;         /* 深色文字 */
  --card: 241 245 249;    /* 卡片背景 */
  --border: 203 213 225;  /* 邊框顏色 */
  --primary: 121 77 255;  /* 主品牌色 */
}

.dark {
  --bg: 15 23 42;         /* 深色背景 */
  --fg: 248 250 252;      /* 淺色文字 */
  --card: 30 41 59;       /* 卡片背景 */
  --border: 71 85 105;    /* 邊框顏色 */
  --primary: 167 132 255; /* 主品牌色 (Dark 模式較亮) */
}
```

### 元件範例
```html
<div class="bg-card text-text border border-border rounded-xl p-6">
  <h2 class="text-theme font-bold text-lg">卡片標題</h2>
  <p class="text-muted-500">這是一段文字內容</p>
  <button class="mt-4 px-4 py-2 bg-success text-white rounded">
    確認
</button>
</div>
```

---

## 🚀 開發建議

1. **優先使用語義色**  
   - 方便在 Light/Dark 模式下保持一致性。
   - 例如：`bg-bg`、`text-text`、`border-border`。

2. **靜態色適合品牌元素**  
   - Logo、主要按鈕、固定的品牌識別度。

3. **搭配 Tailwind 工具類別**  
   - 例：`hover:bg-primary-600`、`focus:ring-2 focus:ringc`。


#  #40518


### 修改內容說明：
1. **`nginx.conf`**: 針對 Vue/Vite 的 SPA 架構配置，確保 Vue Router 的 History Mode 在重新整理時不會出現 404 錯誤。
2. **`Dockerfile`**: 採用多階段編譯（Multi-stage build），先在 Node 環境編譯專案，再將靜態檔案部署至輕量化的 Nginx 映像中。
3. **`docker-compose.yml`**: 定義服務與通訊。預設連結到 `well-network` 外部網路，以便與後端微服務溝通（請確保 Portainer/Docker 中已有此網路）。
4. **`.github/workflows/deploy.yml`**: 自動化部署工作流。內容包括：
    - 當推送至 `main` 分支時，觸發自動編譯。
    - 將映像推送到 GitHub Container Registry (GHCR)。
    - 完成後觸發 Portainer Webhook 進行自動部署。

### 部署建議步驟：
1. **GitHub Secrets 設定**:
   請至 GitHub 專案的 `Settings > Secrets and variables > Actions` 加入以下 Secret：
   - `PORTAINER_WEBHOOK_URL`: 您在 Portainer Stack 或 Container 中產生的 Webhook 連結。

2. **Portainer 設定**:
   如果您是透過 Portainer 直接連接 GitHub Repo 建立 Stack，請確保 Portainer 能夠讀取 `docker-compose.yml`；如果是透過映像部署，請將映像位置指向 `ghcr.io/您的帳號/well.frontend:latest`。

如果您有任何特定的 Portainer 連結或特定的網路名稱需求，可以隨時告訴我！