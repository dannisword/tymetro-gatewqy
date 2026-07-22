// src/router/menuToRoutes.ts
import type { RouteRecordRaw } from "vue-router";
import { defineAsyncComponent } from "vue";

export type MenuItem = {
  to: string;
  label: string;
  icon?: string;
  children?: MenuItem[] | null;
};

/** 建立可懶載入的 views 索引（Vite 以專案根為基準） */
const viewModules = import.meta.glob("/src/views/**/*.{vue,tsx}");

type Loader = () => Promise<any>;
const toAsyncComp = (loader: Loader) =>
  defineAsyncComponent(async () => {
    const mod = await loader();
    return mod.default ?? mod;
  });

/** 依你的規則嘗試多個候選檔案 */
function resolveView(absPath: string) {
  // 移除路由參數部分，例如 /map-base/:id => /map-base 
  // 這樣才能正確對應到實體檔案
  const cleanPath = absPath.replace(/:[^/]+/g, "").replace(/\/+/g, "/").replace(/\/$/, "");

  const candidates = [
    `/src/views/base${cleanPath}.vue`,
    `/src/views/cust${cleanPath}.vue`,
    `/src/views${cleanPath}.vue`,
    `/src/views/base${cleanPath}/index.vue`, // 額外支援 index.vue
    `/src/views/cust${cleanPath}/index.vue`,
    `/src/views${cleanPath}/index.vue`,
  ];

  for (const key of candidates) {
    const loader = viewModules[key] as Loader | undefined;
    if (loader) return toAsyncComp(loader);
  }

  console.warn(
    "[menuToRoutes] 未找到對應檔案：",
    absPath,
    "(清理後路徑: " + cleanPath + ")",
    "候選：",
    candidates
  );
  // fallback：給一個通用的 Base 頁面
  return toAsyncComp(() => import("@/views/base/record-base.vue"));
}

/** 攤平成 Layout 的 children（相對路徑） */
export function createChildRoutesFromMenu(items: MenuItem[]): RouteRecordRaw[] {
  const acc: RouteRecordRaw[] = [];

  const walk = (nodes: MenuItem[]) => {
    for (const it of nodes) {
      if (it.to) {
        if (it.to === "/dashboard") continue; // 避免和靜態 Dashboard 重複
        const abs = it.to;
        const rel = abs.replace(/^\//, "");
        const hasParams = rel.includes(":");
        acc.push({
          path: rel, // 相對路徑，渲染到 Layout 的 <router-view/>
          name: rel.replace(/\//g, "-"),
          component: resolveView(abs),
          props: hasParams, // 動態路由自動開啟 props
          meta: {
            title: it.label,
            icon: it.icon,
            affix: true,
            keepAlive: true,
          },
        });
      }
      if (it.children?.length) {
        walk(it.children);
      }
    }
  };

  walk(items);
  return acc;
}
