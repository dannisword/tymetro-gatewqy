<script lang="ts" setup>
import { ref, onMounted, onUnmounted, computed, onBeforeMount } from "vue";
import { useRoute } from "vue-router";
import { 
  mdiTrain, 
  mdiRefresh,
  mdiMonitorDashboard,
  mdiAlertCircle
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import httpOperations from "@/utils/http-operations";
import { routeHandle } from "@/hooks/route-handle";
import { useMQTT } from "@/store/useMQTT";

const route = useRoute();
const navigator = routeHandle().navigation;
const trainCodeParam = computed(() => route.params.trainCode as string);
const { isConnected, connect, subscribe , publish} = useMQTT();

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
  equipmentId: number;
  endPos: number;
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
    const trainCode = trainCodeParam.value;
    if (!trainCode) return;

    // 直接呼叫該車組的專屬組成 API
    const response = await httpOperations.get(`/api/v1/dashboard/composition/${trainCode}`);
    if (!response.success) return;
    
    const carDataList = response.data;

    // 將資料格式化為介面所需的 TrainStatus 結構
    trains.value = [{
      id: 1,
      label: trainCode,
      cars: carDataList.map((car: any) => {
        const u1Obj = car.equipments.find((e: any) => e.endPos === 1) || { sensors: {} };
        const u2Obj = car.equipments.find((e: any) => e.endPos === 2) || { sensors: {} };

        const mapUnit = (equipment: any): HVACUnit => {
          const sensors = equipment.sensors;
          // 輔助函式：根據模式數值轉換文字
          const getModeName = (val: number) => {  
            switch(val) {
              case 1: return '送風';
              case 2: return '制冷';
              default: return '停止';
            }
          };

          return {
            compressors: [
              {
                id: 1,
                status: sensors["壓縮機(1)-啟停狀態"]?.value === 1 ? 'ON' : 'OFF',
                health: sensors["壓縮機(1)-異常狀態"]?.value === 1 ? '正常' : '異常',
                highPress: sensors["壓縮機(1)-高壓數值"]?.value ?? 0,
                lowPress: sensors["壓縮機(1)-低壓數值"]?.value ?? 0,
              },
              {
                id: 2,
                status: sensors["壓縮機(2)-啟停狀態"]?.value === 1 ? 'ON' : 'OFF',
                health: sensors["壓縮機(2)-異常狀態"]?.value === 1 ? '正常' : '異常',
                highPress: sensors["壓縮機(2)-高壓數值"]?.value ?? 0,
                lowPress: sensors["壓縮機(2)-低壓數值"]?.value ?? 0,
              }
            ],
            equipmentId: equipment.equipmentId,
            endPos: equipment.endPos,
            temp: sensors["車廂溫度"]?.value ?? 0,
            setTemp: sensors["設定溫度"]?.value ?? 0,
            mode: getModeName(sensors["運轉模式"]?.value),
          };
        };

        return {
          id: car.carNo,
          label: car.carNo,
          status: mapStatus(car.carStatus),
          unit1: mapUnit(u1Obj),
          unit2: mapUnit(u2Obj),
          lastUpdate: new Date().toLocaleTimeString(),
        };
      })
    }];
  } catch (error) {
    console.error("Failed to fetch dashboard data:", error);
  }
};

// 根據 URL 參數過濾出正確的列車
const currentTrain = computed(() => {
  return trains.value.find(t => t.label === trainCodeParam.value) || trains.value[0] || null;
});

let timeId: any;
onBeforeMount(async () => { 
  await fetchDashboardData(); }
)
onMounted(() => {
  timeId = setInterval(() => { 
    currentTime.value = new Date().toLocaleTimeString(); 
    currentDate.value = new Date().toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' });
  }, 1000);

  const brokerHost = import.meta.env.VITE_MQTT_BROKER;

  connect(`ws://${brokerHost}:9001`);

  subscribe('mtr/pm', (topic: string, data: any) =>{
    console.log("MQTT data received:", data.D4001);
      currentTrain.value.cars[0].unit1.mode = getOptionMode(data.D4001);
      console.log(currentTrain.value.cars[0].unit1 );
      
    if (currentTrain.value && currentTrain.value.cars.length > 0) {
      // 40001	System Operation Mode	主控制模式 (DI 1/2)	0:OFF, 1:Test, 2:Auto, 3:Man-Vent
      currentTrain.value.cars[0].unit1.mode = getOptionMode(data.D4001);
      console.log(currentTrain.value.cars[0].unit1 );
      

      // 40006	Suction Pressure 1	壓縮機 1 吸氣壓力 (AI 2)	Unit: kPa (0~1000 kPa)
      // 40007	Discharge Pressure 1	壓縮機 1 排氣壓力 (AI 3)	Unit: kPa (0~4000 kPa)
      // 40008	Suction Pressure 2	壓縮機 2 吸氣壓力 (AI 4)	Unit: kPa (0~1000 kPa)
      // 40009	Discharge Pressure 2	壓縮機 2 排氣壓力 (AI 5)	Unit: kPa (0~4000 kPa)
      currentTrain.value.cars[0].unit1.compressors[0].highPress = data.D4007/10 || 0;
      currentTrain.value.cars[0].unit1.compressors[0].lowPress = data.D4006/10 || 0;
      currentTrain.value.cars[0].unit1.compressors[1].highPress = data.D4009/10 || 0;
      currentTrain.value.cars[0].unit1.compressors[1].lowPress = data.D4008/10 || 0;

      // 40005	Target Set Temperature	設定溫度 (AI)
      currentTrain.value.cars[0].unit1.temp = data.D4004/10 || 0;
      //currentTrain.value.cars[0].unit1.temp = data.D4020/10 || 0;
    }
  });
});
const getOptionMode = (mode: any) => {
 
  
  switch (mode) {
    case "0": return '停止';
    case "1": return '測試';
    case "2": return '自動';
    case "3": return '送風';
    default: return '未知';
  }
}
onUnmounted(() => { if (timeId) clearInterval(timeId); });

const refreshData = async () => { await fetchDashboardData(); };
const navigateToPage = (car: CarStatus, unit: HVACUnit) => {
  const equipmentId = unit.equipmentId;
  const endPos = unit.endPos;
  navigator(`/equipment-page/${equipmentId}/${endPos}`, `車廂${car.label}-設備${endPos}`);
}
</script>

<template>
  <div class="smart-dashboard p-4 sm:p-6 min-h-screen">
    
    <div class="max-w-[1920px] mx-auto space-y-6">
      
      <!-- HEADER STATS -->
      <header class="flex flex-col md:flex-row justify-between items-center glass-card rounded-[1.5rem] md:rounded-[2rem] border-theme gap-6 animate-fade-in">
        <div class="flex items-center gap-5 w-full md:w-auto">
          <div class="p-3.5 rounded-2xl bg-primary-theme text-white shadow-lg shrink-0">
            <BaseIcon :path="mdiTrain" size="32" />
          </div>
          <div>
            <h1 class="text-xl md:text-2xl font-black text-theme tracking-tight leading-none mb-1">車組監控: {{ trainCodeParam }}</h1>
            <div class="flex items-center gap-3">
              <span class="text-[10px] font-bold text-success-theme flex items-center gap-1.5 uppercase">
                <div class="w-1.5 h-1.5 rounded-full bg-success-theme animate-pulse"></div>
                即時數據
              </span>
              <span class="text-[10px] font-bold text-muted-label">編組識別: {{ currentTrain?.label || '載入中...' }}</span>
            </div>
          </div>
        </div>
        
        <div class="flex items-center gap-4 md:gap-8 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 md:border-l border-border/10 pt-4 md:pt-0 md:pl-8">
           <div class="text-left md:text-right">
              <div class="text-[10px] font-bold text-muted-label uppercase tracking-widest mb-0.5">{{ currentDate }}</div>
              <div class="text-xl md:text-2xl font-mono font-black text-theme leading-none">{{ currentTime }}</div>
           </div>
           <div class="flex gap-4">
              <button @click="refreshData" class="refresh-btn"><BaseIcon :path="mdiRefresh" size="24" /></button>
           </div>
        </div>
      </header>

      <!-- DASHBOARD GRID -->
      <main v-if="currentTrain" class="animate-slide-up space-y-6">
        
        <!-- UNIT 1 DATA -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <div v-for="car in currentTrain.cars" :key="'u1-'+car.id" class="car-data-card">
            <div class="car-card-header">
              <span class="title">{{ car.label }} 車廂</span>
              <button class="side-tag-btn" @click="navigateToPage(car, car.unit1)">
                <BaseIcon :path="mdiMonitorDashboard" size="14" /> 1端
              </button>
            </div>
            
            <div class="data-table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="border-r border-border/10">壓縮機 1</th>
                    <th class="border-r border-border/10">壓縮機 2</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="border-r border-border/10">
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>啟停狀態</span><span class="pill" :class="car.unit1.compressors[0].status">{{ car.unit1.compressors[0].status }}</span></div>
                        <div class="row"><span>異常狀態</span><span class="pill" :class="car.unit1.compressors[0].health === '正常' ? 'ON' : 'OFF'">{{ car.unit1.compressors[0].health }}</span></div>
                        <div class="row"><span>高壓讀值</span><span class="text-error-theme font-mono font-black">{{ car.unit1.compressors[0].highPress.toFixed(0) }} <small>KPa</small></span></div>
                        <div class="row"><span>低壓讀值</span><span class="text-info-theme font-mono font-black">{{ car.unit1.compressors[0].lowPress.toFixed(0) }} <small>KPa</small></span></div>
                      </div>
                    </td>
                    <td>
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>啟停狀態</span><span class="pill" :class="car.unit1.compressors[1].status">{{ car.unit1.compressors[1].status }}</span></div>
                        <div class="row"><span>異常狀態</span><span class="pill" :class="car.unit1.compressors[1].health === '正常' ? 'ON' : 'OFF'">{{ car.unit1.compressors[1].health }}</span></div>
                        <div class="row"><span>高壓讀值</span><span class="text-error-theme font-mono font-black">{{ car.unit1.compressors[1].highPress.toFixed(0) }} <small>KPa</small></span></div>
                        <div class="row"><span>低壓讀值</span><span class="text-info-theme font-mono font-black">{{ car.unit1.compressors[1].lowPress.toFixed(0) }} <small>KPa</small></span></div>
                      </div>
                    </td>
                  </tr>
                  <tr class="shared-rows">
                    <td colspan="2">
                      <div class="flex flex-col border-t border-border/20">
                        <div class="full-row"><span>車廂溫度</span><span class="val">{{ car.unit1.temp.toFixed(1) }} °C</span></div>
                        <div class="full-row"><span>設定溫度</span><span class="val">{{ car.unit1.setTemp.toFixed(1) }} °C</span></div>
                        <div class="full-row no-border items-center">
                          <span>運轉模式</span>
                          <span class="mode-box">{{ car.unit1.mode }}</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>
        </div>

        <!-- UNIT 2 DATA -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <div v-for="car in currentTrain.cars" :key="'u2-'+car.id" class="car-data-card">
            <div class="car-card-header">
              <span class="title">{{ car.label }} 車廂</span>
              <button class="side-tag-btn" @click="navigateToPage(car, car.unit2)">
                <BaseIcon :path="mdiMonitorDashboard" size="14" /> 2端
              </button>
            </div>
            
            <div class="data-table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th class="border-r border-border/10">壓縮機 1</th>
                    <th class="border-r border-border/10">壓縮機 2</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="border-r border-border/10">
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>啟停狀態</span><span class="pill" :class="car.unit2.compressors[0].status">{{ car.unit2.compressors[0].status }}</span></div>
                        <div class="row"><span>異常狀態</span><span class="pill" :class="car.unit2.compressors[0].health === '正常' ? 'ON' : 'OFF'">{{ car.unit2.compressors[0].health }}</span></div>
                        <div class="row"><span>高壓讀值</span><span class="text-error-theme font-mono font-black">{{ car.unit2.compressors[0].highPress.toFixed(0) }} <small>KPa</small></span></div>
                        <div class="row"><span>低壓讀值</span><span class="text-info-theme font-mono font-black">{{ car.unit2.compressors[0].lowPress.toFixed(0) }} <small>KPa</small></span></div>
                      </div>
                    </td>
                    <td>
                      <div class="flex flex-col gap-2 p-2">
                        <div class="row"><span>啟停狀態</span><span class="pill" :class="car.unit2.compressors[1].status">{{ car.unit2.compressors[1].status }}</span></div>
                        <div class="row"><span>異常狀態</span><span class="pill" :class="car.unit2.compressors[1].health === '正常' ? 'ON' : 'OFF'">{{ car.unit2.compressors[1].health }}</span></div>
                        <div class="row"><span>高壓讀值</span><span class="text-error-theme font-mono font-black">{{ car.unit2.compressors[1].highPress.toFixed(0) }} <small>KPa</small></span></div>
                        <div class="row"><span>低壓讀值</span><span class="text-info-theme font-mono font-black">{{ car.unit2.compressors[1].lowPress.toFixed(0) }} <small>KPa</small></span></div>
                      </div>
                    </td>
                  </tr>
                  <tr class="shared-rows">
                    <td colspan="2">
                      <div class="flex flex-col border-t border-border/20">
                        <div class="full-row"><span>車廂溫度</span><span class="val">{{ car.unit2.temp.toFixed(1) }} °C</span></div>
                        <div class="full-row"><span>設定溫度</span><span class="val">{{ car.unit2.setTemp.toFixed(1) }} °C</span></div>
                        <div class="full-row no-border items-center">
                          <span>運轉模式</span>
                          <span class="mode-box">{{ car.unit2.mode }}</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>
        </div>

      </main>

      <div v-else-if="!trains.length" class="flex flex-col items-center justify-center py-20 text-muted-label">
        <BaseIcon :path="mdiRefresh" size="48" class="animate-spin mb-4 opacity-20" />
        <p>正在載入數據...</p>
      </div>
      
      <div v-else class="flex flex-col items-center justify-center py-20 text-muted-label">
        <BaseIcon :path="mdiAlertCircle" size="48" class="mb-4 opacity-20 text-error-theme" />
        <p>找不到對應的列車編組: {{ trainCodeParam }}</p>
        <button @click="navigator('/dashboard', '儀表板')" class="mt-4 text-primary-theme hover:underline">返回主儀表板</button>
      </div>

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
}
[data-theme='dark'] .car-data-card {
  background: rgba(30, 41, 59, 0.8);
  color: #eee;
}

.car-card-header {
  display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 2px solid #1890ff;
}
.car-card-header .title { font-size: 18px; font-weight: 900; color: #1890ff; }
.side-tag-btn { 
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 900; color: #666; background: #eee; 
  padding: 4px 10px; border-radius: 6px; border: 1px solid transparent;
  transition: all 0.3s; cursor: pointer;
}
.side-tag-btn:hover {
  background: #1890ff; color: white; border-color: #1890ff;
  box-shadow: 0 4px 10px rgba(24, 144, 255, 0.3);
}
[data-theme='dark'] .side-tag-btn { background: rgba(255,255,255,0.1); color: #aaa; }
[data-theme='dark'] .side-tag-btn:hover { background: #1890ff; color: white; }

.data-table-wrapper {
  border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 8px; overflow: hidden;
}
.data-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
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

.mode-box {
  background: #f0f0f0;
  color: #333;
  padding: 4px 20px;
  border-radius: 4px;
  font-weight: 900;
  font-size: 13px;
  min-width: 100px;
  text-align: center;
}
[data-theme='dark'] .mode-box { background: rgba(255,255,255,0.1); color: #eee; }

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
