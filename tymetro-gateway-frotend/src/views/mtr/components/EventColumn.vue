<script setup lang="ts">
import { PropType } from 'vue';
import { mdiChevronUp, mdiChevronDown } from '@mdi/js';
import BaseIcon from '@/components/BaseIcon.vue';

const props = defineProps({
  groups: {
    type: Array as PropType<any[]>,
    required: true
  }
});

const handleGroupClick = (group: any) => {
  group.isOpen = !group.isOpen;
};

const getErrorCount = (events: any[]) => {
  return events.filter(e => e.status === 'red').length;
};

const getNormalCount = (events: any[]) => {
  return events.filter(e => e.status === 'green').length;
};
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- 每個群組呈現為獨立卡片 -->
    <div 
      v-for="(group, gIdx) in groups" 
      :key="'g-'+gIdx"
      class="bg-white rounded-lg border border-blue-200 shadow-sm overflow-hidden flex flex-col transition-all hover:shadow-md"
    >
      <!-- 卡片標題列 -->
      <div 
        @click="handleGroupClick(group)"
        class="px-4 py-3.5 cursor-pointer transition-colors flex justify-between items-center border-b hover:bg-blue-50 border-blue-100"
      >
        <div class="flex items-center gap-3">
          <span class="font-bold text-[15px] tracking-wide text-blue-700">
            {{ group.name }}
          </span>
        </div>
        
        <div class="flex items-center gap-3">
          <div class="flex gap-1.5">
            <span 
              v-if="getErrorCount(group.events) > 0" 
              class="min-w-[20px] h-8 px-3 rounded-full bg-red-500 text-white text-[13px] font-bold flex justify-center items-center "
              title="異常數量"
            >
              {{ getErrorCount(group.events) }}
            </span>
            <span 
              v-if="getNormalCount(group.events) > 0" 
              class="min-w-[20px] h-8 px-3 rounded-full bg-green-600 text-white text-[13px] font-bold flex justify-center items-center"
              title="正常數量"
            >
              {{ getNormalCount(group.events) }}
            </span>
          </div>
          <BaseIcon 
            :path="group.isOpen ? mdiChevronUp : mdiChevronDown" 
            size="20" 
            class="text-blue-400 transition-transform duration-200" 
          />
        </div>
      </div>
      
      <!-- 卡片內容區 (Tile 顯示) -->
      <div v-show="group.isOpen" class="p-3 bg-white border-t border-slate-50">
        <div class="grid grid-cols-2 gap-2.5">
          <div 
            v-for="(event, eIdx) in group.events" 
            :key="'e-'+eIdx"
            class="relative px-3 py-2.5 rounded-md transition-all flex items-center justify-center cursor-default shadow-sm border"
            :class="event.status === 'green' 
              ? 'text-gray-500 border-green-300' 
              : 'text-red-500 border-red-300 animate-pulse'"
          >
            <!-- 事件名稱 -->
            <span class="text font-bold leading-snug text-center tracking-wide">
              {{ event.name }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
