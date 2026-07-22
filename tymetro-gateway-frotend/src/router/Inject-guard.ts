// src/router/guard.inject.ts
import type { Router } from "vue-router";
import { useAppStore } from "@/store/useAppStore";
import { useAuthStore } from "@/store/useAuthStore";
import { createChildRoutesFromMenu } from "@/router/menuToRoutes";

export function injectGuard(router: Router) {
  let injected = false;

  router.beforeEach(async (to, from, next) => {
    const store = useAppStore();
    const authStore = useAuthStore();
    const isAuthed = Boolean(authStore.isAuthenticated ?? false);

    // 檢查該路由是否需要登入權限（支援繼承自父路由的 meta 設定，且子路由若顯式設定則優先覆蓋）
    const requiresAuth = to.meta.requiresAuth === true;

    // 1. 未登入且路由需要登入：導向 Login，並帶上 redirect
    if (requiresAuth && !isAuthed) {
      return next({
        name: "Login",
        query: { redirect: to.fullPath },
        replace: true,
      });
    }

    // 2. 已登入又進入 Login：直接回首頁
    if (isAuthed && String(to.name) === "Login") {
      return next({ path: "/", replace: true });
    }

    // 3. 已登入但尚未注入動態路由：執行注入
    if (isAuthed && !injected) {
      const children = createChildRoutesFromMenu(store.menus);
      children.forEach((r) => router.addRoute("Layout", r));
      injected = true;
      // 讓當前目標重新解析一次（避免 matched 為空）
      return next({ ...to, replace: true });
    }

    // 4. 其他情況（免登入路由，或是已登入且已完成注入）：直接放行
    next();
  });
}
