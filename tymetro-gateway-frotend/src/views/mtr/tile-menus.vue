<script setup lang="ts">
import { routeHandle } from "@/hooks/route-handle";
import BaseIcon from '@/components/BaseIcon.vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import { useMtrStore } from '@/store/useMtrStore';
import { storeToRefs } from 'pinia';

const { navigation } = routeHandle();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單' }
];

const mtrStore = useMtrStore();
const { tools } = storeToRefs(mtrStore);

const handleItemClick = (item: any) => {
  console.log('Clicked tool action:', item.title);
  navigation(item.route, item.title);
};
</script>

<template>
  <div class="w-full">
    
    <!-- Breadcrumb -->
    <div class="w-full mb-10">
      <Breadcrumb title="功能選單設定" :items="breadcrumbItems" />
    </div>

    <!-- 內容區域 -->
    <div class="w-full px-2">

      <!-- 網格區域 -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5 md:gap-6 w-full">
        
        <!-- 單個大方塊 (Tile) -->
        <div 
          v-for="tool in tools" 
          :key="tool.id"
          @click="handleItemClick(tool)"
          class="relative bg-white aspect-[4/3] flex flex-col items-center justify-center p-4 shadow-[0_4px_15px_-6px_rgba(0,0,0,0.12)] hover:shadow-[0_6px_20px_-6px_rgba(0,0,0,0.2)] transition-all cursor-pointer rounded-[2px] group transform hover:-translate-y-1"
        >
          
          <!-- 左上角緞帶 (Ribbon) -->
          <div v-if="tool.step" class="absolute top-4 -left-2 bg-[#2a7eb5] text-white text-[10px] font-extrabold px-2.5 py-1 shadow-sm rounded-r-sm z-10 tracking-widest">
            {{ tool.step }}
            <!-- 緞帶下方摺角 -->
            <div class="absolute top-full left-0 border-t-[5px] border-r-[7px] border-t-[#194f73] border-r-transparent w-0 h-0"></div>
          </div>

          <!-- 圓形背景與圖示 -->
          <div class="w-[70px] h-[70px] rounded-full bg-[#f0f7ff] border border-[#e1f0ff] flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-500 shadow-inner">
             <BaseIcon :path="tool.icon" w="32" h="32" size="32" class="text-[#2a7eb5]" />
          </div>

          <!-- 標題文字 -->
          <h3 class="text-[15px] font-black text-slate-700 text-center font-serif tracking-wide">{{ tool.title }}</h3>
          
        </div>

      </div>
    </div>
  </div>
</template>
