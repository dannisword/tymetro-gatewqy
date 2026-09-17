import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
// Element-plus自動導入
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import EnvironmentPlugin from "vite-plugin-environment";
import { fileURLToPath, URL } from "node:url";
import { execSync } from "node:child_process";
import fs from "node:fs";

// 取得 Git 資訊 (若無 git 指令環境則嘗試讀取 backend git_version.json 回退)
function getGitInfo() {
  let commit = "unknown";
  let branch = "unknown";
  let date = "";

  try {
    commit = execSync("git rev-parse --short HEAD").toString().trim();
    branch = execSync("git rev-parse --abbrev-ref HEAD").toString().trim();
    date = execSync("git log -1 --format=%cd --date=iso").toString().trim();
  } catch {
    try {
      const backendGitJson = path.resolve(__dirname, "../tymetro-gateway-backend/app/git_version.json");
      if (fs.existsSync(backendGitJson)) {
        const info = JSON.parse(fs.readFileSync(backendGitJson, "utf-8"));
        commit = info.commit || "unknown";
        branch = info.branch || "unknown";
        date = info.date || "";
      }
    } catch {}
  }
  return { commit, branch, date };
}

const gitInfo = getGitInfo();
const appVersion = (() => {
  try {
    const pkg = JSON.parse(fs.readFileSync(new URL("./package.json", import.meta.url), "utf-8"));
    return pkg.version || "1.0.0";
  } catch {
    return "1.0.0";
  }
})();

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  console.log(env.VITE_PROXY_TARGET);
  return {
    define: {
      __APP_VERSION__: JSON.stringify(appVersion),
      __GIT_COMMIT__: JSON.stringify(gitInfo.commit),
      __GIT_BRANCH__: JSON.stringify(gitInfo.branch),
      __GIT_DATE__: JSON.stringify(gitInfo.date),
    },
    plugins: [
      vue(),
      EnvironmentPlugin({
        frontend: gitInfo.commit,
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
