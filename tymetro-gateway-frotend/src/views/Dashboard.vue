<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { 
  mdiTrain, 
  mdiAlertCircle, 
  mdiRefresh,
  mdiCheckCircle,
  mdiClockOutline,
  mdiChevronRight,
  mdiTools,
  mdiPowerOff,
  mdiInformation,
  mdiOpenInNew,
  mdiThermometer
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import httpOperations from "@/utils/http-operations";
import { routeHandle } from "@/hooks/route-handle";
import { useAlert } from "@/composables/TLAlter";
import { useMQTT } from "@/store/useMQTT";

const { TLWarning } = useAlert();
const navigator = routeHandle().navigation;
const { isConnected, connect, subscribe , publish} = useMQTT();

interface Car {
  id: number;
  carNo: string;
  carVin: string;
  status: string;
  lastUpdate: string;
}

interface Train {
  trainCode: string;
  carType: string;
  carTypeName: string;
  trainStatus: string;
  statusCounts: Record<string, number>;
  cars: Car[];
}

const trains = ref<Train[]>([]);
const loading = ref(false);
const lastUpdated = ref(new Date().toLocaleTimeString());

// MQTT Test Tool State
const bitValues = ref(new Array(16).fill(false));
const targetTemp = ref(24);

const testWordValue = computed(() => {
  return bitValues.value.reduce((acc, val, i) => acc + (val ? Math.pow(2, i) : 0), 0);
});


const sendMqttTest = () => {
  const D40003 =bitValues.value.reduce((acc, val, i) => acc + (val ? Math.pow(2, i) : 0), 0);

  publish('mtr/test', { 
    D40003: D40003,
    D40020: targetTemp.value * 10,
    timestamp: new Date().toISOString()
  });
};

const sendValueDirectly = (val: number) => {
  publish('tymetro/test/word', { 
    value: val,
    hex: '0x' + val.toString(16).toUpperCase().padStart(4, '0'),
    timestamp: new Date().toISOString(),
    isQuickSend: true
  });
};

const expressTrains = computed(() => trains.value.filter(t => t.carType === 'EXPRESS'));
const commuterTrains = computed(() => trains.value.filter(t => t.carType !== 'EXPRESS'));

const stats = computed(() => {
  let total = 0, operating = 0, maintenance = 0, offline = 0, abnormal = 0;
  trains.value.forEach(t => {
    total += t.cars.length;
    operating += t.statusCounts['OPERATING'] || 0;
    maintenance += t.statusCounts['MAINTENANCE'] || 0;
    offline += t.statusCounts['OFFLINE'] || 0;
    abnormal += t.statusCounts['ABNORMAL'] || 0;
  });
  return { total, operating, maintenance, offline, abnormal };
});

const fetchDashboardData = async () => {
  loading.value = true;
  try {
    const response = await httpOperations.get('/api/v1/dashboard/groups');
    if (response.success && Array.isArray(response.data)) {
      trains.value = response.data.map((t: any) => ({
        trainCode: t.trainCode,
        carType: t.carType,
        carTypeName: t.carTypeName,
        trainStatus: t.trainStatus,
        statusCounts: t.statusCounts,
        cars: t.cars.map((c: any) => ({
          id: c.carNo,
          carNo: c.carNo.toString(),
          carVin: c.carVin || "",
          status: c.carStatus,
          lastUpdate: new Date().toLocaleTimeString()
        }))
      }));
      lastUpdated.value = new Date().toLocaleTimeString();
    }
  } catch (error) {
    console.error("Failed to fetch dashboard:", error);
    TLWarning("無法取得即時資料");
  } finally {
    loading.value = false;
  }
};

const handleRealtimeUpdate = (topic: string, data: any) => {
  console.log("Realtime update received:", data);
  // Expecting { trainCode: string, carNo: string, status: string }
  const { trainCode, carNo, status } = data;
  
  const train = trains.value.find(t => t.trainCode === trainCode);
  if (train) {
    const car = train.cars.find(c => c.carNo === carNo.toString());
    if (car) {
      const oldStatus = car.status;
      car.status = status;
      car.lastUpdate = new Date().toLocaleTimeString();
      
      // Update status counts for the train
      if (oldStatus !== status) {
        train.statusCounts[oldStatus] = Math.max(0, (train.statusCounts[oldStatus] || 1) - 1);
        train.statusCounts[status] = (train.statusCounts[status] || 0) + 1;
      }
    }
  }
};

const onGoToTrain = (trainCode: string) => {
  navigator('/mtr/train-list', '車廂列表');
};

onMounted(() => {
  fetchDashboardData();
  
  // MQTT Connection
  // const brokerHost = window.location.hostname;
  const brokerHost = import.meta.env.VITE_MQTT_BROKER;

  connect(`ws://${brokerHost}:9001`);
  subscribe('tymetro/dashboard/status', handleRealtimeUpdate);
});

const getStatusColor = (status: string) => {
  switch (status) {
    case 'OPERATING': return '#10B981';
    case 'MAINTENANCE': return '#F59E0B';
    case 'OFFLINE': return '#64748B';
    case 'ABNORMAL': return '#EF4444';
    default: return '#94A3B8';
  }
};
</script>

<template>
  <div class="dashboard-container p-6 bg-slate-50 min-h-screen">
    <!-- Top Header -->
    <header class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
          系統總覽控制台
          <span class="text-xs font-bold bg-slate-200 text-slate-500 px-2 py-1 rounded uppercase tracking-widest">REAL-TIME</span>
        </h1>
        <div class="flex items-center gap-4 mt-1">
          <p class="text-sm text-slate-400 font-medium">最後更新時間: {{ lastUpdated }}</p>
          <div class="flex items-center gap-1.5 px-2 py-0.5 bg-slate-100 rounded-full border border-slate-200">
            <div :class="['w-2 h-2 rounded-full', isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300']"></div>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">MQTT: {{ isConnected ? 'Online' : 'Offline' }}</span>
          </div>
        </div>
      </div>
      <button 
        @click="fetchDashboardData" 
        class="flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md transition-all active:scale-95 group"
      >
        <BaseIcon :path="mdiRefresh" :class="{'animate-spin': loading}" size="20" class="text-primary" />
        <span class="text-sm font-bold text-slate-600">刷新數據</span>
      </button>
    </header>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
      <!-- Total -->
      <div class="stat-card group flex items-center justify-between">
        <div class="p-4 bg-blue-50 rounded-2xl text-blue-500 group-hover:rotate-6 transition-transform">
          <BaseIcon :path="mdiTrain" size="32" />
        </div>
        <div class="text-right">
          <div class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-1">Total Units</div>
          <div class="text-4xl font-black text-slate-800 leading-none">{{ stats.total }}</div>
          <div class="text-xs font-bold text-slate-400 mt-2">總載客車廂</div>
        </div>
      </div>

      <!-- Operating -->
      <div class="stat-card group flex items-center justify-between">
        <div class="p-4 bg-emerald-50 rounded-2xl text-emerald-500 group-hover:rotate-6 transition-transform">
          <BaseIcon :path="mdiCheckCircle" size="32" />
        </div>
        <div class="text-right">
          <div class="inline-block px-2 py-0.5 bg-emerald-100 text-emerald-600 text-[10px] font-black rounded mb-1">NORMAL</div>
          <div class="text-4xl font-black text-emerald-600 leading-none">{{ stats.operating }}</div>
          <div class="text-xs font-bold text-slate-400 mt-2">營運中</div>
        </div>
      </div>

      <!-- Abnormal -->
      <div class="stat-card group flex items-center justify-between border-red-100 bg-red-50/10">
        <div class="p-4 bg-red-50 rounded-2xl text-red-500 group-hover:rotate-6 transition-transform">
          <BaseIcon :path="mdiAlertCircle" size="32" />
        </div>
        <div class="text-right">
          <div v-if="stats.abnormal > 0" class="inline-block px-2 py-0.5 bg-red-100 text-red-600 text-[10px] font-black rounded mb-1 animate-pulse">CRITICAL</div>
          <div v-else class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-1">Alerts</div>
          <div class="text-4xl font-black text-red-600 leading-none">{{ stats.abnormal }}</div>
          <div class="text-xs font-bold text-slate-400 mt-2">異常報警</div>
        </div>
      </div>

      <!-- Maintenance -->
      <div class="stat-card group flex items-center justify-between">
        <div class="p-4 bg-amber-50 rounded-2xl text-amber-500 group-hover:rotate-6 transition-transform">
          <BaseIcon :path="mdiTools" size="32" />
        </div>
        <div class="text-right">
          <div class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-1">Service</div>
          <div class="text-4xl font-black text-amber-600 leading-none">{{ stats.maintenance }}</div>
          <div class="text-xs font-bold text-slate-400 mt-2">維修保養中</div>
        </div>
      </div>

      <!-- Offline -->
      <div class="stat-card group flex items-center justify-between">
        <div class="p-4 bg-slate-100 rounded-2xl text-slate-500 group-hover:rotate-6 transition-transform">
          <BaseIcon :path="mdiPowerOff" size="32" />
        </div>
        <div class="text-right">
          <div class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-1">Idle</div>
          <div class="text-4xl font-black text-slate-400 leading-none">{{ stats.offline }}</div>
          <div class="text-xs font-bold text-slate-400 mt-2">設備離線</div>
        </div>
      </div>
    </div>

    <!-- Main Content Area: Grouped Train Cards -->
    <div class="space-y-10 pb-20">
      <!-- 直達車分組 -->
      <section v-if="expressTrains.length > 0">
        <div class="flex items-center gap-3 mb-4 px-2">

          <h2 class="text-xl font-black text-slate-800 tracking-tight">直達車 Express <span class="ml-2 text-sm text-slate-400 font-bold">({{ expressTrains.length }} 組)</span></h2>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div 
            v-for="train in expressTrains" 
            :key="train.trainCode"
            @click="onGoToTrain(train.trainCode)"
            class="train-card bg-white rounded-xl p-3 border border-slate-100 shadow-sm hover:shadow-xl transition-all cursor-pointer group relative overflow-hidden flex flex-col"
          >
            <!-- Type Badge -->
            <div class="absolute top-0 right-0 px-1.5 py-0.5 text font-black text-white rounded-bl-md bg-blue-500">直達</div>

            <!-- Card Header -->
            <div class="flex items-center gap-1.5 mb-2.5">
              <div class="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-100 text-purple-800 shrink-0">
                <BaseIcon :path="mdiTrain" size="16" />
              </div>
              <div class="min-w-0">
                <div class="text font-black text-slate-800 leading-none truncate">{{ train.trainCode }}</div>
                <div class="text-xs font-bold text-gray-500 mt-0.5 uppercase tracking-tighter truncate">{{ train.carTypeName }}</div>
              </div>
            </div>

            <!-- Cars Status (Circles) -->
            <div class="flex flex-wrap gap-2 mb-3 justify-center">
              <div 
                v-for="car in train.cars" 
                :key="car.id"
                class="w-8 h-8 rounded-full flex items-center justify-center border-2 border-white shadow-md transition-all hover:scale-110 hover:shadow-lg"
                :style="{ backgroundColor: getStatusColor(car.status) }"
                :title="`車廂 ${car.carNo}`"
              >
                <span class="text-sm font-black text-white leading-none">{{ car.carNo }}</span>
              </div>
            </div>

            <!-- Footer Info -->
            <div class="flex justify-between items-center mt-auto pt-2 border-t border-slate-50">
              <div class="flex items-center gap-1">
                <div v-for="(count, status) in train.statusCounts" :key="status" class="flex items-center">
                  <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: getStatusColor(status) }"></div>
                  <span class="text font-bold text-slate-400 ml-0.5">{{ count }}</span>
                </div>
              </div>
              <BaseIcon :path="mdiChevronRight" size="12" class="text-slate-300 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </div>
        </div>
      </section>

      <!-- 普通車分組 -->
      <section v-if="commuterTrains.length > 0">
        <div class="flex items-center gap-3 mb-4 px-2">

          <h2 class="text-xl font-black text-slate-800 tracking-tight">普通車 Commuter <span class="ml-2 text-sm text-slate-400 font-bold">({{ commuterTrains.length }} 組)</span></h2>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div 
            v-for="train in commuterTrains" 
            :key="train.trainCode"
            @click="onGoToTrain(train.trainCode)"
            class="train-card bg-white rounded-xl p-3 border border-slate-100 shadow-sm hover:shadow-xl transition-all cursor-pointer group relative overflow-hidden flex flex-col"
          >
            <!-- Type Badge -->
            <div class="absolute top-0 right-0 px-1.5 py-0.5 text font-black text-white rounded-bl-md bg-blue-500">普通</div>

            <!-- Card Header -->
            <div class="flex items-center gap-1.5 mb-2.5">
              <div class="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-100 text-blue-800 shrink-0">
                <BaseIcon :path="mdiTrain" size="16" />
              </div>
              <div class="min-w-0">
                <div class="text font-black text-slate-800 leading-none truncate">{{ train.trainCode }}</div>
                <div class="text-xs font-bold text-gray-500 mt-0.5 uppercase tracking-tighter truncate">{{ train.carTypeName }}</div>
              </div>
            </div>

            <!-- Cars Status (Circles) -->
            <div class="flex flex-wrap gap-2 mb-3 justify-center">
              <div 
                v-for="car in train.cars" 
                :key="car.id"
                class="w-8 h-8 rounded-full flex items-center justify-center border-2 border-white shadow-md transition-all hover:scale-110 hover:shadow-lg"
                :style="{ backgroundColor: getStatusColor(car.status) }"
                :title="`車廂 ${car.carNo}`"
              >
                <span class="text-sm font-black text-white leading-none">{{ car.carNo }}</span>
              </div>
            </div>

            <!-- Footer Info -->
            <div class="flex justify-between items-center mt-auto pt-2 border-t border-slate-50">
              <div class="flex items-center gap-1">
                <div v-for="(count, status) in train.statusCounts" :key="status" class="flex items-center">
                  <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: getStatusColor(status) }"></div>
                  <span class="text font-bold text-slate-400 ml-0.5">{{ count }}</span>
                </div>
              </div>
              <BaseIcon :path="mdiChevronRight" size="12" class="text-slate-300 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </div>
        </div>
      </section>


      <!-- MQTT Control Panel Section -->
      <section class="mt-16 pt-10 border-t-2 border-slate-200">
        <div class="flex items-center justify-between mb-8">
          <div class="flex items-center gap-4">
            <div class="w-10 h-10 rounded-2xl bg-primary-500 flex items-center justify-center text-white shadow-lg">
              <BaseIcon :path="mdiTools" size="24" />
            </div>
            <div>
              <h2 class="text-2xl font-black text-slate-800 tracking-tight">空調系統控制測試</h2>
              <p class="text-sm font-bold text-slate-400 uppercase tracking-widest">Control Panel - Word D40003</p>
            </div>
          </div>
          <div class="flex gap-4">
            <!-- Temp Control -->
            <div class="bg-white rounded-2xl px-6 py-2 flex items-center gap-4 shadow-lg border border-slate-100">
              <div class="flex flex-col">
                <span class="text-[10px] font-black text-slate-400 uppercase">Target Temp (D40020)</span>
                <span class="text-xl font-black text-primary-500">{{ targetTemp }}°C</span>
              </div>
              <div class="flex gap-1">
                <button @click="targetTemp--" class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center hover:bg-slate-200 active:scale-90 transition-all">-</button>
                <button @click="targetTemp++" class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center hover:bg-slate-200 active:scale-90 transition-all">+</button>
              </div>
            </div>
            
            <div class="bg-slate-900 rounded-2xl px-6 py-3 text-center shadow-lg border border-slate-800">
              <div class="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-0.5">Decimal</div>
              <div class="text-xl font-black text-white">{{ testWordValue }}</div>
            </div>
            <div class="bg-slate-800 rounded-2xl px-6 py-3 text-center shadow-lg border border-slate-700">
              <div class="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-0.5">HEX</div>
              <div class="text-xl font-black text-emerald-400 font-mono">0x{{ testWordValue.toString(16).toUpperCase().padStart(4, '0') }}</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-[2rem] p-8 shadow-xl border border-slate-100">
          <!-- 16-bit DO Control Grid -->
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div class="text-sm font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-primary-500"></div>
                數位輸出控制 (DO 1 - DO 16)
              </div>
              <div class="text-xs font-bold text-slate-400">Word D40003 Bitmask Control</div>
            </div>
            
            <div class="grid grid-cols-4 gap-4">
              <div 
                v-for="(item, idx) in [
                  { bit: 0, label: 'DO 1', sub: '啟動緊急換流器', desc: 'Enable EM-INV' },
                  { bit: 1, label: 'DO 2', sub: '緊急供氣風扇', desc: 'EM-Supply Fan' },
                  { bit: 2, label: 'DO 3', sub: '一般送風機', desc: 'Supply Fan' },
                  { bit: 3, label: 'DO 4', sub: '冷凝扇低速', desc: 'Cond. Fan Low' },
                  { bit: 4, label: 'DO 5', sub: '冷凝扇高速', desc: 'Cond. Fan High' },
                  { bit: 5, label: 'DO 6', sub: '壓縮機 1', desc: 'Comp. Motor 1' },
                  { bit: 6, label: 'DO 7', sub: '壓縮機 2', desc: 'Comp. Motor 2' },
                  { bit: 7, label: 'DO 8', sub: '冷媒電磁閥 1', desc: 'Evap. Solenoid 1' },
                  { bit: 8, label: 'DO 9', sub: '冷媒電磁閥 2', desc: 'Evap. Solenoid 2' },
                  { bit: 9, label: 'DO 10', sub: '回風風門', desc: 'Return Air Damper' },
                  { bit: 10, label: 'DO 11', sub: '緊急供氣風門', desc: 'EM-Air Damper' },
                  { bit: 11, label: 'DO 12', sub: '外氣 25%', desc: 'Flash Air Damper 1' },
                  { bit: 12, label: 'DO 13', sub: '外氣 50%', desc: 'Flash Air Damper 2' },
                  { bit: 13, label: 'DO 14', sub: '外氣 75%', desc: 'Flash Air Damper 3' },
                  { bit: 14, label: 'DO 15', sub: '外氣 100%', desc: 'Flash Air Damper 4' },
                  { bit: 15, label: 'DO 16', sub: '系統綜合故障', desc: 'System Fault' }
                ]" 
                :key="item.bit"
                @click="bitValues[item.bit] = !bitValues[item.bit]"
                :class="[
                  'p-4 rounded-2xl border-2 cursor-pointer transition-all flex flex-col gap-2 group',
                  bitValues[item.bit] ? 'bg-emerald-50 border-emerald-300 shadow-md translate-y-[-2px]' : 'bg-slate-50/50 border-slate-100 hover:border-slate-200 hover:bg-white'
                ]"
              >
                <div class="flex justify-between items-start">
                  <div :class="['text-sm font-black', bitValues[item.bit] ? 'text-emerald-700' : 'text-slate-500']">{{ item.label }}</div>
                  <div :class="['w-10 h-5 rounded-full relative transition-all shrink-0', bitValues[item.bit] ? 'bg-emerald-500 shadow-inner' : 'bg-slate-200']">
                    <div :class="['absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-300', bitValues[item.bit] ? 'translate-x-5' : '']"></div>
                  </div>
                </div>
                <div class="min-w-0">
                  <div :class="['text-base font-black truncate', bitValues[item.bit] ? 'text-emerald-900' : 'text-slate-800']">{{ item.sub }}</div>
                  <div class="text-[10px] font-bold text-slate-400 truncate">{{ item.desc }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom Action Bar -->
          <div class="mt-8 pt-6 border-t border-slate-100 flex gap-6">
             <button 
              @click="bitValues = new Array(16).fill(false)"
              class="px-10 py-5 bg-slate-100 text-slate-500 rounded-3xl font-black hover:bg-slate-200 transition-all active:scale-95"
             >
               全部重置 (Reset All)
             </button>
             <button 
              @click="sendMqttTest"
              :disabled="!isConnected"
              class="flex-1 py-5 bg-primary-500 text-white rounded-3xl font-black hover:opacity-90 transition-all shadow-2xl shadow-primary-500/30 flex items-center justify-center gap-4 active:scale-[0.98] disabled:opacity-30 disabled:grayscale"
             >
               <BaseIcon :path="mdiChevronRight" size="28" />
               <span class="text-xl">發送 MQTT 控制指令 (D40003 & D40020)</span>
             </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>


<style scoped>
.stat-card {
  @apply bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1;
}

.train-card {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.stat-card .mdi-icon {
  @apply transition-transform duration-500;
}

.stat-card:hover .mdi-icon {
  @apply rotate-12 scale-110;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.dashboard-container {
  animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}

:deep(.train-details-dialog) {
  overflow: auto;
}
:deep(.train-details-dialog .el-dialog__header) {
  padding: 20px 24px 0;
  margin-right: 0;
}
:deep(.train-details-dialog .el-dialog__title) {
  font-weight: 900;
  color: #1e293b;
}
:deep(.train-details-dialog .el-dialog__body) {
  padding: 24px;
}
</style>
