<!-- src/components/StatsCard.vue -->
<script setup lang="ts">
import BaseIcon from "@/components/BaseIcon.vue";

const props = withDefaults(
  defineProps<{
    title: string;
    value: string | number;
    subtext: string;
    icon: string;
    iconSize?: number;
    // 版面配置：'left' 表示 icon 在左、文字在右且靠右對齊；'right' 表示文字在左、icon 在右且靠左對齊
    layout?: "left" | "right";
    cardClass?: string;
    iconBgClass?: string;
    iconColorClass?: string;
    valueColorClass?: string;
    badge?: string;
    badgeClass?: string;
  }>(),
  {
    iconSize: 32,
    layout: "left",
    cardClass: "",
    iconBgClass: "",
    iconColorClass: "",
    valueColorClass: "text-slate-800",
    badge: "",
    badgeClass: "",
  }
);
</script>

<template>
  <div 
    :class="[
      'bg-white shadow-sm flex items-center justify-between group transition-all border',
      layout === 'left' 
        ? 'stat-card p-6 rounded-[2rem] border-slate-100 hover:shadow-xl hover:-translate-y-1' 
        : 'p-5 rounded-2xl border-slate-100 hover:shadow-md transition-shadow',
      props.cardClass
    ]"
  >
    <!-- Layout 'left' (用在控制台/儀表板): 圖示在左，文字在右 (text-right) -->
    <template v-if="layout === 'left'">
      <div 
        :class="[
          'p-4 rounded-2xl group-hover:rotate-6 transition-transform duration-500 shrink-0 mdi-icon-wrapper',
          props.iconBgClass,
          props.iconColorClass
        ]"
      >
        <BaseIcon :path="icon" :size="iconSize" class="mdi-icon" />
      </div>
      <div class="text-right">
        <div 
          v-if="badge" 
          :class="[
            'inline-block px-2 py-0.5 text-[10px] font-black rounded mb-1',
            props.badgeClass
          ]"
        >
          {{ badge }}
        </div>
        <div 
          v-else 
          class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-1"
        >
          {{ title }}
        </div>
        <div :class="['text-4xl font-black leading-none', props.valueColorClass]">
          {{ value }}
        </div>
        <div class="text-xs font-bold text-slate-400 mt-2">
          {{ subtext }}
        </div>
      </div>
    </template>

    <!-- Layout 'right' (用在端點狀態總覽): 文字在左，圖示在右 -->
    <template v-else>
      <div class="space-y-1">
        <div 
          v-if="badge" 
          :class="[
            'inline-block px-2 py-0.5 text-[10px] font-black rounded mb-1',
            props.badgeClass
          ]"
        >
          {{ badge }}
        </div>
        <span 
          v-else 
          class="text-[10px] font-black text-slate-300 uppercase tracking-wider block"
        >
          {{ title }}
        </span>
        <span :class="['text-3xl font-black leading-none block', props.valueColorClass]">
          {{ value }}
        </span>
        <span class="text-xs font-semibold text-slate-400 block">
          {{ subtext }}
        </span>
      </div>
      <div 
        :class="[
          'p-3.5 rounded-2xl group-hover:scale-110 transition-transform shrink-0',
          props.iconBgClass,
          props.iconColorClass
        ]"
      >
        <BaseIcon :path="icon" :size="iconSize" />
      </div>
    </template>
  </div>
</template>

<style scoped>
/* 為了讓 Dashboard 元件能繼承 hover 動畫 */
.mdi-icon-wrapper :deep(.mdi-icon),
.mdi-icon {
  transition: transform 0.5s;
}
.group:hover .mdi-icon-wrapper :deep(.mdi-icon),
.group:hover .mdi-icon {
  transform: rotate(12deg) scale(1.1);
}
</style>
