<template>
  <RouterView />
  <AlertContainer />
</template>
<script setup lang="ts">
import { watch } from "vue";
import { useRouter, Router } from "vue-router";
import AlertContainer from "./components/TLAlertsContainer.vue";
import { useAppStore } from "../src/store/useAppStore";
import { createChildRoutesFromMenu as toChildRoutes } from "@/router/menuToRoutes";

const appStore = useAppStore();
const router = useRouter();

// 記錄已注入的 route name，避免重複
const injected = new Set<string>();

watch(
  () => appStore.menus,
  (menus) => {
    if (!menus || menus.length === 0) return;

    const children = toChildRoutes(menus); // => 只包含 children 的 RouteRecordRaw[]
    children.forEach((r: any) => {
      const name = r.name as string | undefined;
      if (!name) return;
      if (injected.has(name) || router.hasRoute(name)) return;

      router.addRoute("Layout", r); // ⬅️ 關鍵：加到已存在的 Layout 底下
      injected.add(name);
    });

    // 若目前所在的路徑是新注入的路由，強制重新解析一次
    const cur = router.currentRoute.value.fullPath;
    const resolved = router.resolve(cur);
    if (!resolved.matched.length) {
      router.replace(cur).catch(() => {});
    }
  },
  { immediate: true }
);
</script>
