<!-- src/components/AppButton.vue -->
<script setup lang="ts">
import { computed } from "vue";
import { mdiLoading } from "@mdi/js";
import * as icons from "@mdi/js";
type Variant =
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "danger"
  | "error"
  | "info"
  | "default";
type Mode = "solid" | "outline" | "ghost" | "link";
type Size = "sm" | "md" | "lg";

const props = withDefaults(
  defineProps<{
    variant?: Variant;
    colorClass?: string;
    mode?: Mode;
    size?: Size;
    block?: boolean;
    loading?: boolean;
    iconOnly?: boolean;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
    circle?: boolean;
    /** 傳入 @mdi/js 的 path（如 mdiPlus） */
    icon?: string;
    iconRight?: string;
  }>(),
  {
    variant: "primary",
    mode: "solid",
    size: "md",
    block: false,
    loading: false,
    iconOnly: false,
    disabled: false,
    type: "button",
  },
);

/* Tailwind 固定類（focus ring 用你的語義色 `ring`） */
const base =
  "inline-flex items-center justify-center gap-2 font-medium transition-colors " +
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-ring disabled:cursor-not-allowed";

/* 尺寸 */
const sizeClass: Record<Size, string> = {
  sm: "text-sm px-3 h-8",
  md: "text-sm px-3.5 h-9",
  lg: "text-base px-4 h-11",
};
const sizeIconOnly: Record<Size, string> = {
  sm: "h-8 w-8",
  md: "h-9 w-9",
  lg: "h-12 w-12",
};

/* 依照你的 tailwind.config 定義顏色（全部用明文 class，避免 purge） */
const palette: Record<
  Variant,
  {
    solid: string;
    outline: string;
    ghost: string;
    link: string;
  }
> = {
  // primary 有完整色階
  primary: {
    solid: "bg-primary-600 hover:bg-primary-700 text-white",
    outline:
      "border border-primary-600 text-primary-700 hover:bg-primary-50 bg-white",
    ghost: "text-primary-700 hover:bg-primary-100/60 bg-transparent",
    link: "bg-transparent text-primary-600 underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  // secondary 只有 100 / 500（以 500 當主色）
  secondary: {
    solid: "bg-secondary-500 hover:bg-secondary-500/90 text-white",
    outline:
      "border border-secondary-500 text-secondary-500 hover:bg-secondary-100 bg-white",
    ghost: "text-secondary-500 hover:bg-secondary-100/60 bg-transparent",
    link: "bg-transparent text-secondary-500 underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  // 以下語義色使用 DEFAULT（css var）＋ 500 階對應
  success: {
    solid: "bg-success hover:bg-success/90 text-white",
    outline:
      "border border-success-500 text-success hover:bg-success/10 bg-white",
    ghost: "text-success hover:bg-success/10 bg-transparent",
    link: "bg-transparent text-success underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  warning: {
    solid: "bg-warning hover:bg-warning/90 text-white",
    outline:
      "border border-warning-500 text-warning hover:bg-warning/10 bg-white",
    ghost: "text-warning hover:bg-warning/10 bg-transparent",
    link: "bg-transparent text-warning underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  danger: {
    solid: "bg-danger-500 hover:bg-danger-500/60 text-white",
    outline: "border border-danger-500 text-danger hover:bg-danger/10 bg-white",
    ghost: "text-danger hover:bg-danger/10 bg-transparent",
    link: "bg-transparent text-danger underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  error: {
    solid: "bg-error hover:bg-error/90 text-white",
    outline: "border border-error-500 text-error hover:bg-error/10 bg-white",
    ghost: "text-error hover:bg-error/10 bg-transparent",
    link: "bg-transparent text-error underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  info: {
    solid: "bg-info-100 hover:bg-info-100/90 border border-primary-500 text-muted-600",
    outline: "border border-info-500 text-info hover:bg-info/10 bg-white",
    ghost: "text-info hover:bg-info/10 bg-transparent",
    link: "bg-transparent text-info underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
  default: {
    solid:
      "bg-default hover:bg-default-100 border border-default-500 text-gray-500",
    outline:
      "border border-default-100 text-black hover:bg-default/10 bg-white",
    ghost: "text-black hover:bg-default/10 bg-transparent",
    link: "bg-transparent text-black underline underline-offset-4 hover:no-underline px-0 h-auto",
  },
};

const modeClass = computed(() => palette[props.variant][props.mode]);

const classes = computed(() => {
  const clz = [
    base,
    // modeClass.value,
    props.colorClass ? props.colorClass : modeClass.value,
    props.iconOnly ? sizeIconOnly[props.size] : sizeClass[props.size],
    props.circle ? "rounded-full" : "rounded-md",
  ];

  if (props.block && props.mode !== "link") {
    clz.push("w-full");
  }
  if (props.loading) {
    clz.push("opacity-80 pointer-events-none");
  }
  return clz;
});

const getIcon = (path: any) => {
  if (path.includes("mdi")) {
    return (icons as Record<string, string>)[path];
  }
  return path;
};
</script>

<template>
  <button
    :type="type"
    :class="classes"
    :disabled="disabled || loading"
    :aria-busy="loading ? 'true' : undefined"
  >
    <!-- 左 icon（mdi path） -->
    <svg
      v-if="iconOnly && icon && !loading"
      class="h-6 w-6 shrink-0"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path :d="getIcon(icon)" />
    </svg>
    <svg
      v-else-if="!iconOnly && icon && !loading"
      class="h-6 w-6 shrink-0"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path :d="getIcon(icon)" />
    </svg>
    <!-- <slot name="icon" v-else-if="!iconOnly && !loading" /> -->

    <!-- Loading（mdiLoading） -->
    <svg
      v-if="loading"
      class="h-4 w-4 shrink-0 animate-spin"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path :d="mdiLoading" />
    </svg>

    <!-- 文字（iconOnly 時隱藏）-->
    <span v-if="!iconOnly"><slot /></span>

    <!-- 右 icon -->
    <svg
      v-if="!iconOnly && iconRight && !loading"
      class="h-4 w-4 shrink-0"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path :d="iconRight" />
    </svg>
    <slot name="icon-right" v-else-if="!iconOnly && !loading" />
  </button>
</template>
