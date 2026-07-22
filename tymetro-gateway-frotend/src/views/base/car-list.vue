<script lang="ts" setup>
import { ref, onMounted, onUnmounted, computed, onBeforeMount } from "vue";
import { 
  mdiTrain, mdiRefresh, mdiClockOutline, mdiMonitorDashboard, mdiAlertCircle
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import httpOperations from "@/utils/http-operations";
import { routeHandle } from "@/hooks/route-handle";

const navigator = routeHandle().navigation;

interface Compressor {
  id: number;
  status: 'ON' | 'OFF';
  health: '正常' | '異常';
  highPress: number;
  lowPress: number;
}

interface HVACUnit {
  compressors: Compressor[];
  temp: number;
  setTemp: number;
  mode: string;
}

interface CarStatus {
  id: number;
  label: string;
  status: 'normal' | 'warning' | 'offline';
  unit1: HVACUnit;
  unit2: HVACUnit;
  lastUpdate: string;
}

interface TrainStatus {
  id: number;
  label: string;
  cars: CarStatus[];
}

const trains = ref<TrainStatus[]>([]);
const currentTime = ref(new Date().toLocaleTimeString());
const currentDate = ref(new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' }));

const carInfo = ref<any>({
  totalCars: 0,
  totalCarsOperating: 0,
  totalCarsMaintenance: 0,
  totalCarsOffline: 0,
  totalCarsCompositions: []
});

const mapStatus = (status: string) => {
  switch (status) {
    case 'OPERATING': return 'normal';
    case 'MAINTENANCE': return 'warning';
    case 'OFFLINE': return 'offline';
    default: return 'normal';
  }
};

const fetchDashboardData = async () => {
  try {
    const response = await httpOperations.get('/api/v1/dashboard/stats');
    carInfo.value = response.data;
    const rawTrains = carInfo.value.totalCarsCompositions;

    trains.value = rawTrains.map((t: any, index: number) => ({
      id: index + 1,
      label: t.trainCode,
      cars: t.composition.map((car: any) => {
        const u1Obj = car.equipments.find((e: any) => e.endPos === 1) || { sensors: {} };
        const u2Obj = car.equipments.find((e: any) => e.endPos === 2) || { sensors: {} };

        const mapUnit = (sensors: any): HVACUnit => ({
          compressors: [
            {
              id: 1,
              status: sensors.HIGH_PRESSURE?.value > 1000 ? 'ON' : 'OFF',
              health: '正常',
              highPress: sensors.HIGH_PRESSURE?.value ?? 0,
              lowPress: sensors.LOW_PRESSURE?.value ?? 0,
            },
            {
              id: 2,
              status: sensors.HIGH_PRESSURE?.value > 1050 ? 'ON' : 'OFF',
              health: '正常',
              highPress: (sensors.HIGH_PRESSURE?.value ?? 0) * 0.98,
              lowPress: (sensors.LOW_PRESSURE?.value ?? 0) * 1.02,
            }
          ],
          temp: sensors.RETURN_AIR_TEMP?.value ?? 0,
          setTemp: sensors.SETTING_TEMP?.value ?? 22,
          mode: sensors.HIGH_PRESSURE?.value > 100 ? '製冷' : '通風',
        });

        return {
          id: car.carNo,
          label: car.carNo,
          status: mapStatus(car.carStatus),
          unit1: mapUnit(u1Obj.sensors),
          unit2: mapUnit(u2Obj.sensors),
          lastUpdate: new Date().toLocaleTimeString(),
        };
      })
    }));
  } catch (error) {
    console.error("Failed to fetch dashboard data:", error);
  }
};

const currentTrain = computed(() => trains.value[0] || null);

let timeId: any;
onBeforeMount(async () => { await fetchDashboardData(); })
onMounted(() => {
  timeId = setInterval(() => { 
    currentTime.value = new Date().toLocaleTimeString(); 
    currentDate.value = new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' });
  }, 1000);
});
onUnmounted(() => { if (timeId) clearInterval(timeId); });

const refreshData = async () => { await fetchDashboardData(); };
const navigateToPage = (car: CarStatus) => {
  navigator(`/equipment-mgmt/${car.id}`, `分析(${car.label})`);
}
</script>

<template>
  <div class="smart-dashboard p-4 sm:p-6 min-h-screen">
    
    <div class="max-w-[1920px] mx-auto space-y-6">
      
      <!-- HEADER STATS (RWD) -->
      <header class="flex flex-col md:flex-row justify-between items-center glass-card p-6 rounded-[1.5rem] md:rounded-[2rem] border-theme gap-6 animate-fade-in">
        <div class="flex items-center gap-5 w-full md:w-auto">
          <div class="p-3.5 rounded-2xl bg-primary-theme text-white shadow-lg shrink-0">
            <BaseIcon :path="mdiTrain" size="32" />
          </div>
          <div>
            <h1 class="text-xl md:text-2xl font-black text-theme tracking-tight leading-none mb-1">空調智能監控中心</h1>
            <div class="flex items-center gap-3">
              <span class="text-[10px] font-bold text-success-theme flex items-center gap-1.5 uppercase">
                <div class="w-1.5 h-1.5 rounded-full bg-success-theme animate-pulse"></div>
                即時聯網
              </span>
              <span class="text-[10px] font-bold text-muted-label">列車編組: {{ currentTrain?.label || '載入中' }}</span>
            </div>
          </div>
        </div>
        
        <div class="flex items-center gap-4 md:gap-8 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 md:border-l border-border/10 pt-4 md:pt-0 md:pl-8">
           <div class="text-left md:text-right">
              <div class="text-[10px] font-bold text-muted-label uppercase tracking-widest mb-0.5">{{ currentDate }}</div>
              <div class="text-xl md:text-2xl font-mono font-black text-theme leading-none">{{ currentTime }}</div>
           </div>
           <div class="flex gap-4">
              <div class="stat-pill">營運: {{ carInfo.totalCarsOperating }}</div>
              <div class="stat-pill warning">異常: {{ carInfo.totalCarsMaintenance }}</div>
              <button @click="refreshData" class="refresh-btn"><BaseIcon :path="mdiRefresh" size="24" /></button>
           </div>
        </div>
      </header>

      <!-- DASHBOARD GRID (RWD) -->
      <main v-if="currentTrain" class="dashboard-triple-grid animate-slide-up space-y-6">
        
        <!-- TOP ROW: UNIT 1 DATA -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <div v-for="car in currentTrain.cars" :key="'u1-'+car.id" class="car-data-card">
            <div class="car-card-header">
              <span class="title">{{ car.label }} 車廂</span>
              <span class="side-tag">1端</span>
            </div>
            
            <div class="data-table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="border-r border-border/10">壓縮機 1</th>
                    <th>壓縮機 2</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="border-r border-border/10">
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>狀態</span><span class="pill" :class="car.unit1.compressors[0].status">{{ car.unit1.compressors[0].status }}</span></div>
                        <div class="row"><span>異常</span><span class="pill" :class="car.unit1.compressors[0].health === '正常' ? 'ON' : 'OFF'">{{ car.unit1.compressors[0].health }}</span></div>
                        <div class="row"><span>高壓</span><span class="text-error-theme font-mono font-black">{{ car.unit1.compressors[0].highPress.toFixed(0) }}</span></div>
                        <div class="row"><span>低壓</span><span class="text-info-theme font-mono font-black">{{ car.unit1.compressors[0].lowPress.toFixed(0) }}</span></div>
                      </div>
                    </td>
                    <td>
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>狀態</span><span class="pill" :class="car.unit1.compressors[1].status">{{ car.unit1.compressors[1].status }}</span></div>
                        <div class="row"><span>異常</span><span class="pill" :class="car.unit1.compressors[1].health === '正常' ? 'ON' : 'OFF'">{{ car.unit1.compressors[1].health }}</span></div>
                        <div class="row"><span>高壓</span><span class="text-error-theme font-mono font-black">{{ car.unit1.compressors[1].highPress.toFixed(0) }}</span></div>
                        <div class="row"><span>低壓</span><span class="text-info-theme font-mono font-black">{{ car.unit1.compressors[1].lowPress.toFixed(0) }}</span></div>
                      </div>
                    </td>
                  </tr>
                  <tr class="shared-rows">
                    <td colspan="2">
                      <div class="flex flex-col border-t border-border/20">
                        <div class="full-row"><span>車廂溫度</span><span class="val">{{ car.unit1.temp.toFixed(1) }} °C</span></div>
                        <div class="full-row no-border"><span>設定溫度</span><span class="val">{{ car.unit1.setTemp }} °C</span></div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <button class="sys-diagram-btn" @click="navigateToPage(car)">
               <BaseIcon :path="mdiMonitorDashboard" size="16" /> 系統圖
            </button>
          </div>
        </div>

        <!-- BOTTOM ROW: UNIT 2 DATA -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <div v-for="car in currentTrain.cars" :key="'u2-'+car.id" class="car-data-card">
            <div class="car-card-header">
              <span class="title">{{ car.label }} 車廂</span>
              <span class="side-tag">2端</span>
            </div>
            
            <div class="data-table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="border-r border-border/10">壓縮機 1</th>
                    <th>壓縮機 2</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="border-r border-border/10">
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>狀態</span><span class="pill" :class="car.unit2.compressors[0].status">{{ car.unit2.compressors[0].status }}</span></div>
                        <div class="row"><span>異常</span><span class="pill" :class="car.unit2.compressors[0].health === '正常' ? 'ON' : 'OFF'">{{ car.unit2.compressors[0].health }}</span></div>
                        <div class="row"><span>高壓</span><span class="text-error-theme font-mono font-black">{{ car.unit2.compressors[0].highPress.toFixed(0) }}</span></div>
                        <div class="row"><span>低壓</span><span class="text-info-theme font-mono font-black">{{ car.unit2.compressors[0].lowPress.toFixed(0) }}</span></div>
                      </div>
                    </td>
                    <td>
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>狀態</span><span class="pill" :class="car.unit2.compressors[1].status">{{ car.unit2.compressors[1].status }}</span></div>
                        <div class="row"><span>異常</span><span class="pill" :class="car.unit2.compressors[1].health === '正常' ? 'ON' : 'OFF'">{{ car.unit2.compressors[1].health }}</span></div>
                        <div class="row"><span>高壓</span><span class="text-error-theme font-mono font-black">{{ car.unit2.compressors[1].highPress.toFixed(0) }}</span></div>
                        <div class="row"><span>低壓</span><span class="text-info-theme font-mono font-black">{{ car.unit2.compressors[1].lowPress.toFixed(0) }}</span></div>
                      </div>
                    </td>
                  </tr>
                  <tr class="shared-rows">
                    <td colspan="2">
                      <div class="flex flex-col border-t border-border/20">
                        <div class="full-row"><span>車廂溫度</span><span class="val">{{ car.unit2.temp.toFixed(1) }} °C</span></div>
                        <div class="full-row no-border"><span>設定溫度</span><span class="val">{{ car.unit2.setTemp }} °C</span></div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <button class="sys-diagram-btn" @click="navigateToPage(car)">
               <BaseIcon :path="mdiMonitorDashboard" size="16" /> 系統圖
            </button>
          </div>
        </div>

      </main>
    </div>
  </div>
</template>

<style scoped>
.smart-dashboard {
  background-color: rgb(var(--bg));
  background-image: radial-gradient(circle at 20% 20%, rgba(var(--primary), 0.03) 0%, transparent 40%);
}

.text-theme { color: rgb(var(--fg)); }
.text-primary-theme { color: rgb(var(--primary)); }
.text-success-theme { color: rgb(var(--success)); }
.text-error-theme { color: #ff4d4f; }
.text-info-theme { color: #1890ff; }
.text-muted-label { color: rgba(var(--fg), 0.6); }

.bg-primary-theme { background-color: rgb(var(--primary)); }
.bg-success-theme { background-color: rgb(var(--success)); }

.glass-card {
  background: rgba(var(--card), 0.85);
  backdrop-filter: blur(24px) saturate(180%);
}
.border-theme { border: 1px solid rgba(var(--fg), 0.08); }

.stat-pill {
  display: flex; align-items: center; gap: 8px; padding: 6px 16px; border-radius: 12px; background-color: rgba(var(--fg), 0.05);
  font-size: 11px; font-weight: 900; color: rgba(var(--fg), 0.6); text-transform: uppercase; border: 1px solid rgba(255, 255, 255, 0.05);
}
.stat-pill.warning { color: rgb(var(--warning)); background-color: rgba(var(--warning), 0.1); border-color: rgba(var(--warning), 0.2); }

.refresh-btn {
  width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  color: rgb(var(--primary)); transition: all 0.3s; cursor: pointer; background: rgba(var(--card), 0.75); border: 1px solid rgba(var(--fg), 0.08);
}
.refresh-btn:hover { background-color: rgb(var(--primary)); color: white; }

.car-data-card {
  padding: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #333;
  width: 100%;
}
[data-theme='dark'] .car-data-card {
  background: rgba(30, 41, 59, 0.8);
  color: #eee;
}

.car-card-header {
  display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 2px solid #1890ff;
}
.car-card-header .title { font-size: 18px; font-weight: 900; color: #1890ff; }
.car-card-header .side-tag { font-size: 12px; font-weight: 900; color: #666; background: #eee; padding: 2px 8px; border-radius: 4px; }

.data-table-wrapper {
  border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 8px; overflow: hidden;
}
.data-table { width: 100%; border-collapse: collapse; }
.data-table thead th {
  padding: 8px; background: rgba(var(--primary), 0.05); font-size: 12px; font-weight: 900; color: #555; text-align: center;
}
[data-theme='dark'] .data-table thead th { color: #aaa; background: rgba(255,255,255,0.05); }

.data-table .row {
  display: flex; justify-content: space-between; align-items: center; font-size: 11px; padding: 2px 0;
}
.data-table .row span:first-child { color: #888; font-weight: 700; }

.pill { padding: 2px 10px; border-radius: 6px; font-size: 10px; font-weight: 900; text-transform: uppercase; }
.pill.ON { background: #e6f7ff; color: #1890ff; }
.pill.OFF { background: #f6ffed; color: #52c41a; }

.full-row {
  display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid rgba(0, 0, 0, 0.05); font-size: 12px;
}
.full-row span:first-child { color: #666; font-weight: 700; }
.full-row .val { font-weight: 900; font-family: monospace; }
.full-row.no-border { border-bottom: none; }

.sys-diagram-btn {
  width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #1890ff; background: white; color: #1890ff;
  font-size: 13px; font-weight: 900; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.3s;
}
.sys-diagram-btn:hover { background: #1890ff; color: white; }

/* 動畫 */
@keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
.animate-fade-in { animation: fadeIn 0.8s ease-out forwards; }
.animate-slide-up { animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
</style>