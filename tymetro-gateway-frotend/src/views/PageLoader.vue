<!-- src/views/_PageLoader.vue -->
<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { defineAsyncComponent } from "vue";

// 掃描所有可載入的 view（Vite 會在編譯期建立索引）
const modules = import.meta.glob("/src/views/**/*.{vue,tsx}");

/** 把 loader 轉成真正元件（處理 ESM default） */
const toAsyncComp = (loader: () => Promise<any>) =>
  defineAsyncComponent({
    loader: async () => (await loader()).default,
    delay: 150,
    timeout: 20000,
    suspensible: true,
  });

/** 依命名規則挑檔案；找不到就用通用 Base 頁面當 fallback */
function pick(abs: string) {
  const candidates = [
    `/src/views/base${abs}.vue`, // e.g. /base/role-records.vue
    `/src/views${abs}.vue`, // e.g. /role-records.vue
    `/src/views${abs}/index.vue`, // e.g. /role-records/index.vue
  ];
  for (const k of candidates) {
    const loader = modules[k];
    if (loader) return toAsyncComp(loader as any);
  }
  console.warn(
    "[PageLoader] 找不到頁面，使用通用 Base 頁面 fallback：",
    abs,
    candidates
  );
  // fallback：給一個通用的 Base 頁面（或改成 NotFound）
  return toAsyncComp(() => import("@/views/base/record-base.vue"));

  //return toAsyncComp(() => import("@/views/NotFound.vue"))
}

const route = useRoute();

/** 由 catch-all 參數推回要載入的實際 path */
const absPath = computed(() => {
  const rest = String(route.params.rest ?? "").replace(/^\/+/, "");
  return rest ? `/${rest}` : "/dashboard";
});

const Comp = computed(() => pick(absPath.value));
</script>

<template>
  <Suspense>
    <component :is="Comp" />
    <template #fallback>
      <div class="p-4 text-gray-500">Loading…</div>
    </template>
  </Suspense>
</template>
