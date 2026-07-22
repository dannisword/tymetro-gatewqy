import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
// Element-plus自動導入
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import EnvironmentPlugin from "vite-plugin-environment";
import { fileURLToPath, URL } from "node:url";


let hash = "";
// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  console.log(env.VITE_PROXY_TARGET);
  return {
    plugins: [
      vue(),
      EnvironmentPlugin({
        frontend: hash,
      }),
      AutoImport({
        include: [
          /\.[tj]sx?$/, // .ts, .tsx, .js, .jsx
          /\.vue$/,
          /\.vue\?vue/, // .vue
          /\.md$/, // .md
        ],
        resolvers: [ElementPlusResolver()],
        imports: [
          "vue",
          "vue-router",
          "vue-i18n",
          "@vueuse/head",
          "@vueuse/core",
          "pinia",
        ],
        dts: "src/auto-imports.d.ts",
        eslintrc: { enabled: true }, // 如果用 eslint 需要這個
      }),
      Components({
        // allow auto load markdown components under `./src/components/`
        extensions: ["vue", "md"],
        // allow auto import and register components used in markdown
        include: [/\.vue$/, /\.vue\?vue/, /\.md$/],
        resolvers: [
          ElementPlusResolver({
            importStyle: "sass",
          }),
        ],
        dts: "src/components.d.ts",
      }),
    ],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          // 優先讀取環境變數 VITE_PROXY_TARGET，預設為 http://backend:8000 (Docker 環境)
          target: env.VITE_PROXY_TARGET || "http://backend:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
