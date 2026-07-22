<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import Breadcrumb from '@/components/Breadcrumb.vue';
import { mdiRefresh, mdiHistory, mdiHeartPulse, mdiServer, mdiClockOutline } from '@mdi/js';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseButton from '@/components/BaseButton.vue';
import { getHealthStatus } from '@/utils/api';
import type { GatewayHealth } from '@/utils/types';

const router = useRouter();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '即時事件' }
];
const healthData = ref<GatewayHealth | null>(null);
const pollingInterval = ref<number | null>(null);

onMounted(() => {
  fetchHealthStatus();
  pollingInterval.value = window.setInterval(() => {
    fetchHealthStatus();
  }, 3000);
});

onBeforeUnmount(() => {
  if (pollingInterval.value) {
    window.clearInterval(pollingInterval.value);
  }
});

const fetchHealthStatus = async () => {
  try {
    const res = await getHealthStatus();
    if (res && res.success) {
      healthData.value = res.data;
    }
  } catch (error) {
    console.error('Failed to fetch health status:', error);
  }
};


const formatUptime = (seconds: number): string => {
  if (!seconds || isNaN(seconds)) return '0秒';
  const d = Math.floor(seconds / (3600 * 24));
  const h = Math.floor((seconds % (3600 * 24)) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  const parts = [];
  if (d > 0) parts.push(`${d}天`);
  if (h > 0) parts.push(`${h}小時`);
  if (m > 0) parts.push(`${m}分`);
  if (s > 0 || parts.length === 0) parts.push(`${s}秒`);
  return parts.join(' ');
};

const col1Groups = ref([
  {
    name: '斷路器與過載警報',
    isOpen: true,
    events: [
      { name: '壓縮機1斷路器關斷警報', status: 'green' },
      { name: '壓縮機2斷路器關斷警報', status: 'green' },
      { name: '冷凝風扇1過載或斷路器跳脫', status: 'green' },
      { name: '送風斷路器關斷警報', status: 'green' },
      { name: '冷凝風扇2過載或斷路器跳脫', status: 'green' },
      { name: '緊急送風扇斷路器關斷警報', status: 'green' },
    ]
  },
  {
    name: '感測器與跳脫警報',
    isOpen: true,
    events: [
      { name: '壓縮機1高壓跳脫警報', status: 'green' },
      { name: '壓縮機1低壓跳脫警報', status: 'green' },
      { name: '壓縮機2高壓跳脫警報', status: 'green' },
      { name: '壓縮機2低壓跳脫警報', status: 'green' },
      { name: '壓縮機1高壓感測器異常', status: 'green' },
      { name: '壓縮機1低壓感測器異常', status: 'green' },
      { name: '壓縮機2高壓感測器異常', status: 'green' },
      { name: '壓縮機2低壓感測器異常', status: 'green' },
      { name: '回風溫度感測器異常', status: 'green' },
    ]
  },
  {
    name: '系統異常與失敗',
    isOpen: true,
    events: [
      { name: '緊急換流器異常警報', status: 'green' },
      { name: '泵集失敗', status: 'green' },
      { name: '外氣風門關閉異常', status: 'green' },
    ]
  }
]);

const col2Groups = ref([
  {
    name: '壓力與溫度偏離',
    isOpen: true,
    events: [
      { name: '外氣風門開啟極限', status: 'green' },
      { name: '壓縮機1高壓偏高', status: 'green' },
      { name: '壓縮機1低壓偏低', status: 'green' },
      { name: '壓縮機2高壓偏高', status: 'green' },
      { name: '壓縮機2低壓偏低', status: 'green' },
      { name: '車內溫度過高警報', status: 'green' },
      { name: '壓縮機1高低壓差過低', status: 'green' },
      { name: '壓縮機2高低壓差過低', status: 'green' },
    ]
  },
  {
    name: '系統運轉與切換',
    isOpen: true,
    events: [
      { name: '壓縮機1啟動頻繁', status: 'green' },
      { name: '壓縮機2啟動頻繁', status: 'green' },
      { name: '整合切換獨立模式', status: 'red' },
      { name: 'SIV-1電源中斷', status: 'red' },
      { name: 'SIV-2電源中斷', status: 'red' },
      { name: '緊急換流器啟動', status: 'red' },
    ]
  },
  {
    name: '電源與重置狀態',
    isOpen: true,
    events: [
      { name: '電源開啟', status: 'green' },
      { name: 'PLC Watch Dog Reset', status: 'green' },
      { name: 'PLC Power Reset', status: 'green' },
    ]
  }
]);

const allGroups = computed(() => [...col1Groups.value, ...col2Groups.value]);
const activeGroupIndex = ref(0);
const activeGroup = computed(() => allGroups.value[activeGroupIndex.value]);

const totalNormalCount = computed(() => {
  let count = 0;
  allGroups.value.forEach(g => {
    count += g.events.filter((e: any) => e.status === 'green').length;
  });
  return count;
});

const totalErrorCount = computed(() => {
  let count = 0;
  allGroups.value.forEach(g => {
    count += g.events.filter((e: any) => e.status === 'red').length;
  });
  return count;
});

const onHistory = () => {
  console.log('歷史事件');
};
const onClearAlarm = () => {
  console.log('清除警報');
};
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    <!-- Breadcrumb -->
    <div class="w-full mb-10">
      <Breadcrumb title="即時事件狀態" :items="breadcrumbItems" />
    </div>

    <!-- 內容區域 -->
    <div class="w-full px-2">
      <!-- 標題與操作按鈕 -->
      <div class="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-4 mb-6 border-b border-gray-100 pb-4">
        <div class="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 w-full lg:w-auto">
          <h2 class="text-2xl font-bold text-[#2a7eb5] tracking-wide font-sans mb-0 shrink-0">
            即時事件狀態
          </h2>
          <div class="flex flex-wrap gap-2.5">
            <!-- 異常總數 -->
            <div 
              v-if="totalErrorCount > 0"
              class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 border border-red-200 text-red-600 shadow-sm"
            >
              <div class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
              <span class="text-sm font-bold tracking-wider">異常 {{ totalErrorCount }}</span>
            </div>
            
            <!-- 正常總數 -->
            <div 
              class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 shadow-sm"
            >
              <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
              <span class="text-sm font-bold tracking-wider">正常 {{ totalNormalCount }}</span>
            </div>
          </div>
        </div>
        <div class="flex flex-wrap gap-3 w-full lg:w-auto">
          <BaseButton 
            @click="onClearAlarm"
            colorClass="bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:text-amber-600 hover:border-amber-500 shadow-sm"
            icon="mdiRefresh"
            title="警報復歸鍵，功能同面板上的 RESET 按"
          >
            清除警報
          </BaseButton>
          <BaseButton 
            @click="onHistory"
            colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm"
            icon="mdiHistory"
          >
            歷史事件
          </BaseButton>
        </div>
      </div>

      <!-- 第三大區塊：系統服務健康狀態 -->
      <div v-if="healthData" class="flex flex-col gap-4 mt-2">
        <div class="flex items-center justify-between px-2">
          <div class="font-bold text-slate-800 text-lg tracking-wide flex items-center gap-2.5">
            <BaseIcon :path="mdiHeartPulse" :w="'8'" :h="'8'" size="32" class="text-[#2a7eb5] animate-pulse" />
            系統服務健康狀態
          </div>
          <span class="text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
            版本 v{{ healthData.version }}
          </span>
        </div>

        <!-- 網格佈局：1個大卡片(基礎資訊) + 各個服務狀態卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <!-- 閘道器基本資訊 -->
          <div class="bg-gradient-to-br from-[#003775] to-[#2a7eb5] text-white p-5 rounded-2xl shadow-sm flex flex-col justify-between min-h-[160px] relative overflow-hidden group">
            <div class="absolute right-[-20px] bottom-[-20px] opacity-10 group-hover:scale-110 transition-transform duration-500">
              <BaseIcon :path="mdiServer" size="120" />
            </div>
            <div class="z-10">
              <div class="flex items-center justify-between mb-2">
                <span class="text-[11px] font-bold text-white/70 uppercase tracking-wider">閘道器系統</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-white/20 text-white tracking-widest">
                  {{ healthData.app_mode }}
                </span>
              </div>
              <h4 class="text-lg font-black tracking-wide leading-snug mb-1">{{ healthData.gateway_name }}</h4>
              <p class="text-xs font-medium text-white/80 font-mono">ID: {{ healthData.gateway_id }}</p>
            </div>
            <div class="z-10 mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
              <span class="text-[11px] font-bold text-white/70 flex items-center gap-1">
                <BaseIcon :path="mdiClockOutline" size="14" /> 運行時間
              </span>
              <span class="text-sm font-bold font-mono">{{ formatUptime(healthData.uptime_seconds) }}</span>
            </div>
          </div>

          <!-- 各個服務狀態卡片 -->
          <div 
            v-for="(service, code) in healthData.services" 
            :key="code"
            class="bg-white p-5 rounded-2xl border border-slate-100 shadow-xs flex flex-col justify-between min-h-[160px]"
          >
            <div>
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-md font-extrabold text-slate-800 tracking-wide mb-0">{{ service.name }}</h4>
                
                <!-- 狀態 Badge -->
                <span 
                  class="px-2.5 py-0.5 rounded-full text-xs font-black shadow-xs inline-block tracking-wider"
                  :class="{
                    'bg-emerald-50 text-emerald-700 border border-emerald-200/50': service.status === 'connected' || service.status === 'running' || service.status === 'online',
                    'bg-amber-50 text-amber-700 border border-amber-200/50': service.status === 'disconnected' || service.status === 'stopped',
                    'bg-rose-50 text-rose-700 border border-rose-200/50': service.status === 'error'
                  }"
                >
                  {{ 
                    service.status === 'connected' ? '已連線' : 
                    service.status === 'running' ? '運行中' : 
                    service.status === 'disconnected' ? '未連線' :
                    service.status === 'stopped' ? '已停止' : 
                    service.status === 'error' ? '異常' : service.status
                  }}
                </span>
              </div>

              <!-- 服務屬性 -->
              <div class="space-y-1 text-xs text-slate-500 font-medium">
                <div v-if="service.host" class="font-mono">IP: {{ service.host }}:{{ service.port }}</div>
                <div v-if="service.device_id !== undefined" class="font-mono">Device ID: {{ service.device_id }}</div>
                <div v-if="service.path" class="truncate font-mono" :title="service.path">DB: {{ service.path.split('/').pop() }}</div>
              </div>
            </div>

            <!-- 狀態訊息 -->
            <div class="mt-3 pt-3 border-t border-slate-50 text-xs text-slate-400 truncate font-semibold" :title="service.message">
              {{ service.message || '無狀態訊息' }}
            </div>
          </div>

        </div>
      </div>
      
      <!-- 群組標籤 (Tabs) -->
      <div class="flex overflow-x-auto sm:flex-wrap gap-2 sm:gap-3 mb-6 pb-2 sm:pb-0 scrollbar-hide snap-x w-full [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <button 
          v-for="(group, gIdx) in allGroups" 
          :key="'tab-'+gIdx"
          @click="activeGroupIndex = gIdx"
          class="shrink-0 snap-start px-4 sm:px-5 py-2 sm:py-2.5 rounded-md font-bold text transition-colors border flex items-center gap-1.5 sm:gap-2 outline-none focus:outline-none"
          :class="activeGroupIndex === gIdx 
            ? 'bg-[#2a7eb5] text-white border-[#2a7eb5] shadow-sm' 
            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:text-gray-800'"
        >
          {{ group.name }} 
          <span :class="activeGroupIndex === gIdx ? 'text-white/80' : 'text-gray-400 font-normal'">
            ({{ group.events.length }})
          </span>
          <!-- 異常徽章 -->
          <span 
            v-if="group.events.filter(e => e.status === 'red').length > 0"
            class="flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-bold ml-1"
            :class="activeGroupIndex === gIdx ? 'bg-white text-[#ef4444]' : 'bg-[#ef4444] text-white'"
          >
            {{ group.events.filter(e => e.status === 'red').length }}
          </span>
        </button>
      </div>

      <!-- 事件網格 (Grid) -->
      <div v-if="activeGroup" class="bg-white border border-gray-200 rounded-xl p-4 sm:p-6 shadow-sm min-h-[300px] sm:min-h-[400px]">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4">
          <div 
            v-for="(event, eIdx) in activeGroup.events" 
            :key="'evt-'+eIdx"
            class="bg-white border rounded px-4 py-3 flex items-center justify-between transition-all hover:shadow-sm gap-2"
            :class="event.status === 'green' ? 'border-gray-200 hover:border-gray-300' : 'border-red-300 shadow-[inset_0_0_0_1px_rgba(239,68,68,0.2)] bg-red-50/20'"
          >
            <span class="font-medium text leading-snug truncate" :class="event.status === 'green' ? 'text-gray-700' : 'text-red-700'" :title="event.name">
              {{ event.name }}
            </span>
            <div 
              class="shrink-0 px-2 py-0.5 rounded text font-bold border"
              :class="event.status === 'green' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 'bg-red-500 text-white border-red-600 animate-pulse'"
            >
              {{ event.status === 'green' ? '正常' : '異常' }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
