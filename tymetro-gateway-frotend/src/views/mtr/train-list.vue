<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useMtrStore } from '@/store/useMtrStore';
import { useMQTT } from '@/store/useMQTT';
import { CompressorStatus } from '@/utils/enums';
import { EndpointStatus, TrainCarStatus, MetroConfig } from '@/utils/types';
import { 
  mdiTrain, 
  mdiAlertCircle, 
  mdiCheckCircle, 
  mdiWifiOff
} from '@mdi/js';

import PageHeader from '@/components/PageHeader.vue';
import StatsCard from '@/components/StatsCard.vue';
import EndpointCard from '@/components/EndpointCard.vue';
import { logger, updateEndpointData } from '@/utils';

// 麵包屑設定
const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '列車狀態列表' }
];

const mtrStore = useMtrStore();
const { isConnected, connect, subscribe } = useMQTT();

const metroConfig = ref<MetroConfig>({
  trainNo: null,
  carNo: null,
  carVins: []
});
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
  let _totalEndpoints = 0;
  let _onlineEndpoints = 0;
  let _abnormalEndpoints = 0;
  let _warningEndpoints = 0;
  
  metroConfig.value.carVins.forEach(car => {
    car.endpoints.forEach(ep => {
      _totalEndpoints++;
      if (ep.isConnected) {
        _onlineEndpoints++;
        if (ep.status === 'abnormal') _abnormalEndpoints++;
        else if (ep.status === 'warning') _warningEndpoints++;
      }
    });
  });
  return {
    total: _totalEndpoints,
    online: _onlineEndpoints,
    offline: _totalEndpoints - _onlineEndpoints,
    abnormal: _abnormalEndpoints,
    warning: _warningEndpoints,
    normal: _onlineEndpoints - _abnormalEndpoints - _warningEndpoints
  };
});

// 載入車廂設定
const loadFromConfig = async () => {
  if (!mtrStore.carConfigs || mtrStore.carConfigs.length === 0) {
    await mtrStore.loadConfig();
  }

  const _trainNo = metroConfig.value.trainNo || 101;
  const _type = Math.floor(_trainNo / 100);
  const _num = _trainNo % 100;

  if (mtrStore.carConfigs && mtrStore.carConfigs.length > 0) {
    metroConfig.value.carVins = mtrStore.carConfigs.map((car: any, index: number) => {
      const carIndex = index + 1; // 1 ~ 4 車
      const carNo = _type * 1000 + carIndex * 100 + _num;
      const name = `${carNo} 車廂`;
      
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
        carNo: carNo,
        name: name,
        endpoints: endpoints
      };
    });
  }
};

// 解析 MQTT 訊息並更新狀態
const handleMqttMessage = (topic: string, data: any) => {
  if (!data) return;
  const _topic_prefix = import.meta.env.VITE_MQTT_TOPIC_PREFIX || 'TYMC/AIR';
  
  // 支援巢狀 data.register 或扁平的 data
  const _reg = data.register || data || {};
  
  // 從 MQTT 訊息或主題路徑動態取得列車編號 (trainNo)
  let parsedTrainNo = data.trainNo !== undefined ? Number(data.trainNo) : undefined;
  if (!parsedTrainNo) {
    const parts = topic.split('/');
    const prefixPartsLength = _topic_prefix.split('/').length;
    const trainNoPart = Number(parts[prefixPartsLength]);
    if (!isNaN(trainNoPart)) {
      parsedTrainNo = trainNoPart;
    }
  }
  if (parsedTrainNo && metroConfig.value.trainNo !== parsedTrainNo) {
    logger.info(`[MQTT] Detected trainNo changed from ${metroConfig.value.trainNo} to ${parsedTrainNo}. Re-mapping car VINS.`);
    metroConfig.value.trainNo = parsedTrainNo;
    const type = Math.floor(parsedTrainNo / 100);
    const num = parsedTrainNo % 100;
    metroConfig.value.carVins.forEach((car, index) => {
      const carIndex = index + 1; // 1 ~ 4 車
      car.trainNo = parsedTrainNo;
      car.carNo = type * 1000 + carIndex * 100 + num;
      car.name = `${car.carNo} 車廂`;
    });
  }

  // 優先從 data.carNo, data.carVin 或主題路徑解析車廂號碼
  let _carNo = data.carNo !== undefined 
    ? Number(data.carNo) 
    : (data.carVin !== undefined ? Number(data.carVin) : undefined);
  
  if (!_carNo) {
    const parts = topic.split('/');
    const prefixPartsLength = _topic_prefix.split('/').length;
    const carNoPart = Number(parts[prefixPartsLength + 1]);
    if (!isNaN(carNoPart)) {
      _carNo = carNoPart;
    }
  }
  
  if (_carNo) {
    metroConfig.value.carNo = _carNo;
    // 比對 carNo 欄位
    const targetCar = metroConfig.value.carVins.find(c => c.carNo === _carNo);
    
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
        updateEndpointData(targetEp,  _reg);
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

  // 載入 config.json 車廂配置
  await loadFromConfig();

  // 啟動心跳檢測：每 5 秒檢查一次是否超過 60 秒未收到訊息
  heartbeatInterval = setInterval(() => {
    const now = Date.now();
    metroConfig.value.carVins.forEach(car => {
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

  const _topic_prefix = import.meta.env.VITE_MQTT_TOPIC_PREFIX || 'TYMC/AIR';
  logger.info("Subscribing to MQTT topic: ", `${_topic_prefix}/#`);
  subscribe(`${_topic_prefix}/#`, handleMqttMessage);
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
        :count="metroConfig.carVins.reduce((acc, car) => acc + car.endpoints.length, 0)"
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
          v-for="car in metroConfig.carVins" 
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
                <h2 class="text-lg font-black text-slate-800 leading-none">
                  {{ car.name }}
                </h2>
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
              :car-no="car.carNo"
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
