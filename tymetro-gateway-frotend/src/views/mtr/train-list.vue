<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useMtrStore } from '@/store/useMtrStore';
import { useMQTT } from '@/store/useMQTT';
import httpOperations from '@/utils/http-operations';
import { SYSTEM_MODE_MAP, SystemModeKey, CompressorStatus} from '@/utils/enums';
import { EndpointStatus, TrainCarStatus } from '@/utils/types';
import { 
  mdiTrain, 
  mdiAlertCircle, 
  mdiCheckCircle, 
  mdiWifiOff
} from '@mdi/js';

import PageHeader from '@/components/PageHeader.vue';
import StatsCard from '@/components/StatsCard.vue';
import EndpointCard from '@/components/EndpointCard.vue';

// 麵包屑設定
const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '車廂狀態列表' }
];

const mtrStore = useMtrStore();
const { isConnected, connect, subscribe } = useMQTT();

const trainNo = ref(101);
const carVin = ref(1101);
const carVins = ref<TrainCarStatus[]>([]);
// 紀錄每個端點最後收到 MQTT 訊息的時間與檢測計時器
const lastMsgTime = ref<Record<string, number>>({});
const lastUpdated = ref(new Date().toLocaleTimeString());
let heartbeatInterval: any = null;
let lastUpdatedTimer: any = null;

const triggerLastUpdated = () => {
  if (lastUpdatedTimer) {
    return;
  }
  lastUpdatedTimer = setTimeout(() => {
    lastUpdated.value = new Date().toLocaleTimeString();
    lastUpdatedTimer = null;
  }, 300);
};

// 統計資訊
const stats = computed(() => {
  let totalEndpoints = 0;
  let onlineEndpoints = 0;
  let abnormalEndpoints = 0;
  let warningEndpoints = 0;
  
  carVins.value.forEach(car => {
    car.endpoints.forEach(ep => {
      totalEndpoints++;
      if (ep.isConnected) {
        onlineEndpoints++;
        if (ep.status === 'abnormal') abnormalEndpoints++;
        else if (ep.status === 'warning') warningEndpoints++;
      }
    });
  });
  return {
    total: totalEndpoints,
    online: onlineEndpoints,
    offline: totalEndpoints - onlineEndpoints,
    abnormal: abnormalEndpoints,
    warning: warningEndpoints,
    normal: onlineEndpoints - abnormalEndpoints - warningEndpoints
  };
});

// 轉換壓縮機運行指標與狀態
const updateCompressorStatus = (targetEp: EndpointStatus, reg: any) => {
  const D40002 = reg.D40002 !== undefined ? Number(reg.D40002) : undefined;
  if (D40002 !== undefined) {
    if (targetEp.compressors[0]) {
      targetEp.compressors[0].status = ((D40002 >> 4) & 1) === 1 ? CompressorStatus.ON : CompressorStatus.OFF;
    }
    if (targetEp.compressors[1]) {
      targetEp.compressors[1].status = ((D40002 >> 5) & 1) === 1 ? CompressorStatus.ON : CompressorStatus.OFF;
    }
  }

  // 轉換壓縮機 1 高低壓
  const highP1 = reg.D40006 !== undefined ? reg.D40006 : undefined;
  const lowP1 = reg.D40005 !== undefined ? reg.D40005 : undefined;
  if (targetEp.compressors[0]) {
    if (highP1 !== undefined) targetEp.compressors[0].highPress = Math.round(Number(highP1));
    if (lowP1 !== undefined) targetEp.compressors[0].lowPress = Math.round(Number(lowP1));
  }

  // 轉換壓縮機 2 高低壓
  const highP2 = reg.D40008 !== undefined ? reg.D40008 : undefined;
  const lowP2 = reg.D40007 !== undefined ? reg.D40007 : undefined;
  if (targetEp.compressors[1]) {
    if (highP2 !== undefined) targetEp.compressors[1].highPress = Math.round(Number(highP2));
    if (lowP2 !== undefined) targetEp.compressors[1].lowPress = Math.round(Number(lowP2));
  }
};

// 統一更新端點數值邏輯
const updateEndpointData = (targetEp: EndpointStatus, reg: any) => {
  // 轉換模式
  if (reg.D40001 !== undefined) {
    const modeKey = reg.D40001.toString() as SystemModeKey;
    targetEp.mode = SYSTEM_MODE_MAP[modeKey] || '未知';
  }
  // 轉換回風溫度 (可能為字串，需轉型為 Number)
  if (reg.D40004 !== undefined) {
    targetEp.returnTemp = parseFloat((Number(reg.D40004) / 10).toFixed(1));
  }
  // 轉換設定溫度 (可能為字串，需轉型為 Number)
  if (reg.D40201 !== undefined) {
    targetEp.setTemp = parseFloat((Number(reg.D40201) / 10).toFixed(1));
  }
  // 轉換壓縮機運行指標與狀態
  updateCompressorStatus(targetEp, reg);
};

// 載入車廂設定
const loadFromConfig = async (reg: Record<string, any>) => {
  if (!mtrStore.carConfigs || mtrStore.carConfigs.length === 0) {
    await mtrStore.loadConfig();
  }

  let _trainNo = 101;
  if (reg.D40054 !== undefined) {
    _trainNo = Number(reg.D40054);
    trainNo.value = _trainNo;
  }
  if (reg.D40055 !== undefined) {
    carVin.value = Number(reg.D40055);
  }

  const type = Math.floor(_trainNo / 100);
  const num = _trainNo % 100;

  if (mtrStore.carConfigs && mtrStore.carConfigs.length > 0) {
    carVins.value = mtrStore.carConfigs.map((car: any, index: number) => {
      const carIndex = index + 1; // 1 ~ 4 車
      const resolvedCarVin = type * 1000 + carIndex * 100 + num;
      const name = car.name.includes('車廂') ? `第 ${car.id} 節車廂` : car.name;
      
      const endpoints = (car.equipment || []).map((eq: any) => ({
        id: eq.endPosId || eq.id || 1,
        name: eq.name || `端點 ${eq.id}`,
        address: eq.address || '127.0.0.1',
        isConnected: false,
        mode: '-',
        returnTemp: 0,
        setTemp: 0,
        status: 'normal',
        statusName: '正常營運',
        compressors: [
          { id: 1, status: CompressorStatus.OFF, health: '正常', highPress: 0, lowPress: 0 },
          { id: 2, status: CompressorStatus.OFF, health: '正常', highPress: 0, lowPress: 0 }
        ]
      }));
      
      return {
        id: car.id,
        trainNo: _trainNo,
        carVin: resolvedCarVin,
        name: name,
        endpoints: endpoints
      };
    });
  }
};

// 處理初始資料套用
const applyInitialData = (reg: Record<string, any>) => {
  const endpointPos = 1;
  const _trainNo = reg.D40054 !== undefined ? Number(reg.D40054) : undefined;
  const _carVin = reg.D40055 !== undefined ? Number(reg.D40055) : undefined;
  
  if (_trainNo) {
    trainNo.value = _trainNo;
    const type = Math.floor(_trainNo / 100);
    const num = _trainNo % 100;
    
    carVins.value.forEach((car, index) => {
      const carIndex = index + 1; // 1 ~ 4 車
      car.trainNo = _trainNo;
      car.carVin = type * 1000 + carIndex * 100 + num;
    });
  }
  
  if (_carVin) {
    carVin.value = _carVin;
  }
  
  if (carVin.value) {
    const targetCar = carVins.value.find(c => c.carVin === Number(carVin.value));
    if (targetCar) {
      const targetEp = targetCar.endpoints.find(e => e.id === endpointPos);
      if (targetEp) {
        targetEp.isConnected = false;
        updateEndpointData(targetEp, reg);
      }
    }
  }
};

// 訂閱 MQTT 即時訊息
onMounted(async() => {
  const brokerHost = import.meta.env.VITE_MQTT_BROKER;
  const brokerPort = import.meta.env.VITE_MQTT_PORT || '9001';
  const brokerProtocol = import.meta.env.VITE_MQTT_PROTOCOL || 'ws';
  
  // 連線 MQTT
  connect(`${brokerProtocol}://${brokerHost}:${brokerPort}`);

  // 一次性讀取初始暫存器資料
  let initialRegs: Record<string, any> = {};
  try {
    const res = await httpOperations.get('/api/v1/sensors/by-group', { registerGroup: 'initial' }, { meta: { loading: false } });
    if (res && res.success) {
      const list = res.data || [];
      list.forEach((item: any) => {
        if (item.sensorCode && item.sensorValue !== null && item.sensorValue !== undefined) {
          initialRegs[item.sensorCode] = Number(item.sensorValue);
        }
      });
    }
  } catch (error) {
    console.error("Fetch initial sensors error:", error);
  }

  // 載入 config.json 車廂配置
  await loadFromConfig(initialRegs);

  // 讀取 sensors 初始值
  applyInitialData(initialRegs);

  // 啟動心跳檢測：每 5 秒檢查一次是否超過 60 秒未收到訊息
  heartbeatInterval = setInterval(() => {
    const now = Date.now();
    carVins.value.forEach(car => {
      car.endpoints.forEach(ep => {
        const key = `${car.id}_${ep.id}`;
        const lastTime = lastMsgTime.value[key];
        if (ep.isConnected && lastTime && (now - lastTime > 60000)) {
          console.warn(`[Heartbeat Timeout] Car ${car.id} Endpoint ${ep.id} exceeded 60s without MQTT data. Setting offline.`);
          ep.isConnected = false;
        }
      });
    });
  }, 5000);

  subscribe(`TYMC/AIR/${trainNo.value}/#`, (topic: string, data: any) => {
    if (data) {
      // 支援巢狀 data.register 或扁平的 data
      const reg = data.register || data || {};
      
      // 從 data.carVin 或 reg.D40055 獲取車廂代號 (carVin)
      const _carVin = data.carVin !== undefined ? Number(data.carVin) : (reg.D40055 !== undefined ? Number(reg.D40055) : undefined);
      
      if (_carVin) {
        // 比對 carVin 欄位
        const targetCar = carVins.value.find(c => c.carVin === _carVin);
        
        // 獲取端點位置
        let endPosNum = data.endPos !== undefined ? Number(data.endPos) : undefined;
        if (!endPosNum) {
          const parts = topic.split('/');
          const lastPart = Number(parts[parts.length - 1]);
          if (!isNaN(lastPart)) {
            endPosNum = lastPart;
          }
        }
        
        if (targetCar && endPosNum) {
          const targetEp = targetCar.endpoints.find(e => e.id === endPosNum);
          if (targetEp) {
            targetEp.isConnected = true;
            // 更新最後收到 MQTT 訊息的時間戳記
            lastMsgTime.value[`${targetCar.id}_${targetEp.id}`] = Date.now();
            triggerLastUpdated();
            updateEndpointData(targetEp, reg);
          }
        }
      }
    }
  });
});

onUnmounted(() => {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
  }
  if (lastUpdatedTimer) {
    clearTimeout(lastUpdatedTimer);
  }
});
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    <!-- 導航麵包屑 -->
    <div class="w-full mb-6">
      <Breadcrumb title="車廂狀態列表" :items="breadcrumbItems" />
    </div>

    <div class="w-full px-4 max-w-[1600px] mx-auto space-y-6">
      
      <!-- 標題與工具列 -->
      <PageHeader
        title="車廂空調端點狀態總覽"
        :count="carVins.reduce((acc, car) => acc + car.endpoints.length, 0)"
        count-unit="Endpoints"
        subtitle="系統即時數據監控"
        :last-updated="lastUpdated"
        :is-connected="isConnected"
      />

      <!-- 統計面板 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <!-- 正常端點 -->
        <StatsCard
          title="Online & Normal"
          :value="stats.normal"
          subtext="正常運行端點"
          :icon="mdiCheckCircle"
          icon-bg-class="bg-emerald-50"
          icon-color-class="text-emerald-500"
          value-color-class="text-emerald-600"
        />

        <!-- 警示端點 -->
        <StatsCard
          title="Warnings"
          :value="stats.warning"
          subtext="預警提醒端點"
          :icon="mdiAlertCircle"
          icon-bg-class="bg-amber-50"
          icon-color-class="text-amber-500"
          value-color-class="text-amber-500"
        />

        <!-- 異常端點 -->
        <StatsCard
          title="Abnormal / Alarms"
          :value="stats.abnormal"
          subtext="故障或嚴重異常"
          :icon="mdiAlertCircle"
          card-class="border-red-100 bg-red-50/10"
          icon-bg-class="bg-rose-50"
          icon-color-class="text-rose-500"
          value-color-class="text-rose-500"
        />

        <!-- 離線端點 -->
        <StatsCard
          title="Offline / Disconnect"
          :value="stats.offline"
          subtext="無法連線端點"
          :icon="mdiWifiOff"
          icon-bg-class="bg-slate-50"
          icon-color-class="text-slate-400"
          value-color-class="text-slate-400"
        />
      </div>

      <!-- 車廂列表網格 (4 車廂卡片，每卡片包含 2 個端點資訊，共 8 個端點) -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div 
          v-for="car in carVins" 
          :key="car.id" 
          class="bg-white rounded-3xl p-6 border border-slate-100 shadow-sm flex flex-col gap-5 hover:shadow-lg transition-all duration-300"
        >
          <!-- 車廂標題 -->
          <div class="flex justify-between items-center pb-3 border-b border-slate-100 shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-[#2a7eb5] text-white flex items-center justify-center shadow-md">
                <BaseIcon :path="mdiTrain" size="20" />
              </div>
              <div>
                <h2 class="text-lg font-black text-slate-800 leading-none">{{ car.name }}</h2>
              </div>
            </div>
            <div class="flex gap-2">
              <span class="px-2.5 py-0.5 bg-blue-50 border border-blue-100 text-[#2a7eb5] text-md font-black rounded-lg uppercase tracking-wider">
                雙端空調
              </span>
            </div>
          </div>

          <!-- 端點卡片 (1端與2端) -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <EndpointCard
              v-for="ep in car.endpoints"
              :key="ep.id"
              :endpoint="ep"
              :car-id="car.carVin"
            />
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.stat-card {
  @apply bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.w-full {
  animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
