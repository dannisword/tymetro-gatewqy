// src/router/setupLoadingGuard.ts
import type { Router } from "vue-router";
import { useLoadingStore } from "@/store/useLoadingStore";

export function setupLoadingGuard(router: Router) {
  let inflight = 0;
  // 防呆
  let hardStop: ReturnType<typeof setTimeout> | null = null;

  const start = () => {
    inflight++;
    useLoadingStore().start();

    if (!hardStop) {
      hardStop = setTimeout(() => {
        inflight = 0;
        useLoadingStore().set(false);
        hardStop = null;
      }, 300);
    }
  };

  const stop = () => {
    if (inflight > 0) {
      inflight--;
    }
    if (inflight === 0) {
      useLoadingStore().stop();
      if (hardStop) {
        clearTimeout(hardStop);
        hardStop = null;
      }
    }
  };

  router.beforeEach((to, from, next) => {
    if (to.meta?.loading === false) {
      return next();
    }
    // 同一路徑就不啟動畫面（避免某些 replace/同頁跳動）
    if (to.fullPath !== from.fullPath) {
      start();
    }
    next();
  });

  router.afterEach(() => stop());
  router.onError(() => stop());
}
