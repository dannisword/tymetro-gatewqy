<!-- src/components/ButtonGroup.vue -->
<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from "vue";

type Orientation = "horizontal" | "vertical";

const props = withDefaults(
  defineProps<{
    attached?: boolean; // true: segmented 相連；false: 留間距
    orientation?: Orientation; // 水平/垂直
    justified?: boolean; // 等寬
    ariaLabel?: string;
  }>(),
  {
    attached: true,
    orientation: "horizontal",
    justified: false,
  }
);

const root = ref<HTMLElement | null>(null);

// 簡易 roving focus：方向鍵在群組內切換焦點
const onKeydown = (e: KeyboardEvent) => {
  if (!root.value) return;
  const btns = Array.from(
    root.value.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")
  );
  if (btns.length === 0) return;
  const idx = btns.findIndex((b) => b === document.activeElement);
  const horiz = props.orientation === "horizontal";
  const prevKey = horiz ? "ArrowLeft" : "ArrowUp";
  const nextKey = horiz ? "ArrowRight" : "ArrowDown";
  if (e.key !== prevKey && e.key !== nextKey) return;
  e.preventDefault();
  const next =
    e.key === nextKey
      ? (idx + 1) % btns.length
      : (idx - 1 + btns.length) % btns.length;
  btns[next]?.focus();
};

onMounted(() => root.value?.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => root.value?.removeEventListener("keydown", onKeydown));
</script>

<template>
  <div
    ref="root"
    role="group"
    :aria-label="ariaLabel"
    :class="[
      'inline-flex',
      orientation === 'vertical' ? 'flex-col' : 'flex-row',
      // 分佈
      !attached && 'gap-2',
      justified && '[&>button]:flex-1 w-full',
      // segmented（相連）樣式：圓角/重疊邊框/提升 focus z-index
      attached &&
        orientation === 'horizontal' && [
          '[&>button]:rounded-none',
          '[&>button]:-ml-px [&>button:first-child]:ml-0',
          '[&>button:first-child]:rounded-l-md',
          '[&>button:last-child]:rounded-r-md',
          '[&>button:focus-visible]:z-10',
        ],
      attached &&
        orientation === 'vertical' && [
          '[&>button]:rounded-none',
          '[&>button]:-mt-px [&>button:first-child]:mt-0',
          '[&>button:first-child]:rounded-t-md',
          '[&>button:last-child]:rounded-b-md',
          '[&>button:focus-visible]:z-10',
        ],
    ]"
  >
    <!-- 放任何按鈕（AppButton、el-button…） -->
    <slot />
  </div>
</template>
