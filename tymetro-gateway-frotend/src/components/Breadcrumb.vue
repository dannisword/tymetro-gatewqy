<script setup lang="ts">
interface BreadcrumbItem {
  label: string;
  to?: string;
}

defineProps<{
  items: BreadcrumbItem[];
}>();
</script>

<template>
  <div class="w-full flex flex-col md:flex-row md:items-center md:justify-between gap-2">
    <!-- 麵包屑導航 (桌機版置左) -->
    <nav class="flex items-center text-sm md:text-md font-medium text-slate-500 order-2 md:order-1">
      <template v-for="(item, index) in items" :key="index">
        <!-- 連結節點 -->
        <router-link 
          v-if="item.to" 
          :to="item.to" 
          class="hover:text-[#2a7eb5] transition-colors"
        >
          {{ item.label }}
        </router-link>
        
        <!-- 當前節點 (無連結) -->
        <span 
          v-else 
          class="text-slate-600 font-semibold"
        >
          {{ item.label }}
        </span>

        <!-- 分隔符號 (非最後一個項目才顯示) -->
        <svg 
          v-if="index < items.length - 1" 
          class="w-4 h-4 mx-2 text-slate-400" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </template>
    </nav>
  </div>
</template>
