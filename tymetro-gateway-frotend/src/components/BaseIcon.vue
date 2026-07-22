<script setup lang="ts">
import { computed } from "vue";
import * as icons from "@mdi/js";
const props = defineProps({
  path: {
    type: String,
    required: false,
    default: null,
  },
  w: {
    type: String,
    default: "w-4",
  },
  h: {
    type: String,
    default: "h-4",
  },
  size: {
    type: [String, Number],
    default: null,
  },
});

const spanClass = computed(
  () =>
    `inline-flex justify-center items-center cursor-pointer ${props.w} ${props.h}`,
);

const iconSize = computed(() => props.size ?? 16);

// const getIcon = (path: any) => {
//   if (path && path.includes("mdi")) {
//     return (icons as Record<string, string>)[path];
//   }
//   return "";
// };
const getIcon = (path: any): string => {
  if (!path) return "";
  
  let result = path;
  // 如果字串包含 mdi，嘗試從庫中尋找 (相容舊有邏輯)
  if (typeof path === 'string' && path.includes("mdi")) {
    result = (icons as Record<string, string>)[path];
  }
  
  // 關鍵修復：只有當結果是有效的 SVG 路徑 (以 M/m 開頭) 時才回傳
  // 這樣像 "setting" 或是找不到的名稱就不會被填入 d 屬性導致報錯
  if (result && typeof result === 'string' && (result.startsWith("M") || result.startsWith("m"))) {
    return result;
  }
  return ""; 
};
</script>

<template>
  <span v-if="path" :class="spanClass">
    <svg
      viewBox="0 0 24 24"
      :width="iconSize"
      :height="iconSize"
      class="inline-block"
    >
      <path fill="currentColor" :d="getIcon(path)" />
    </svg>
    <slot />
  </span>
</template>
