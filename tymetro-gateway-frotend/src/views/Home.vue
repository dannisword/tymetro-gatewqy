<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { 
  mdiTrain, 
  mdiDotsVertical, 

  mdiRefresh,
  mdiMagnify,

  mdiChevronRight,
  mdiChevronDown,

} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import httpOperations from "@/utils/http-operations";
import { routeHandle } from "@/hooks/route-handle";
import { useAlert } from "@/composables/TLAlter";

const { TLSuccess, TLWarning } = useAlert();
const navigator = routeHandle().navigation;

interface Car {
  id: number;
  carNo: string;
  carVin: string;
  trainCode: string;
  trainType: string;
  trainTypeName: string;
  status: 'OPERATING' | 'MAINTENANCE' | 'OFFLINE' | 'ABNORMAL';
  isActive: boolean;
  remark: string;
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
const expandedTrains = ref<Set<string>>(new Set());
const loading = ref(false);
const searchQuery = ref("");
const statusFilter = ref("ALL");

const toggleTrain = (trainCode: string) => {
  if (expandedTrains.value.has(trainCode)) {
    expandedTrains.value.delete(trainCode);
  } else {
    expandedTrains.value.add(trainCode);
  }
};

const dialog = ref({
  title: "編輯車廂資訊",
  visible: false,
});
const currentCar = ref<Partial<Car>>({});
const formRef = ref<any>(null);

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

const filteredTrains = computed(() => {
  const term = searchQuery.value.toLowerCase();
  
  return trains.value.map(train => {
    // Filter cars within the train
    const matchedCars = train.cars.filter(car => {
      const matchesSearch = car.carVin.toLowerCase().includes(term) || 
                           car.trainCode.toLowerCase().includes(term) ||
                           car.carNo.toString().includes(term);
      const matchesStatus = statusFilter.value === "ALL" || car.status === statusFilter.value;
      return matchesSearch && matchesStatus;
    });

    if (matchedCars.length > 0) {
      return { ...train, cars: matchedCars };
    }
    return null;
  }).filter((t): t is Train => t !== null);
});

const fetchCars = async () => {
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
          trainCode: t.trainCode,
          trainType: t.carType,
          trainTypeName: t.carTypeName,
          status: c.carStatus,
          isActive: true,
          remark: "",
          lastUpdate: new Date().toLocaleTimeString()
        }))
      }));
    }
  } catch (error) {
    console.error("Failed to fetch trains:", error);
    TLWarning("無法取得即時資料");
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchCars();
});

const getStatusLabel = (status: string) => {
  const map: any = { 
    'OPERATING': '營運中', 
    'MAINTENANCE': '維保中', 
    'OFFLINE': '離線', 
    'ABNORMAL': '異常' 
  };
  return map[status] || status;
};

const getStatusBgClass = (status: string) => {
  switch (status) {
    case 'OPERATING': return 'bg-[#10B981]';
    case 'MAINTENANCE': return 'bg-[#F59E0B]';
    case 'OFFLINE': return 'bg-[#64748b]';
    case 'ABNORMAL': return 'bg-[#EF4444]';
    default: return 'bg-muted-500';
  }
};
const onNavigatorTrain = (train: Train) => {
  navigator(`/car-page/${train.trainCode}`, `監控(${train.trainCode})`);
}
const onNavigatorCar = (train: Train, car: Car) => {
  navigator(`/equipment-mgmt/${car.id}`, `詳情(${train.trainCode}-${car.carNo})`);
}
</script>

<template>
  <div class="car-mgmt-container p-4 md:p-6 flex flex-col h-screen overflow-hidden">
    <!-- Header & Stats -->
    <header class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 animate-fade-in">
      <div>
        <h1 class="text-2xl font-bold text-theme flex items-center gap-3">
          <div class="p-2 bg-primary/10 rounded-xl">
            <BaseIcon :path="mdiTrain" class="text-primary" size="28" />
          </div>
          車輛資訊列表
        </h1>
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
          <p class="text-xs text-muted-500 font-medium italic">總計 {{ stats.total }} 個車廂</p>
          <div class="hidden sm:block h-3 w-[1px] bg-white/10"></div>
          <div class="flex items-center gap-3">
            <div v-for="s in ['OPERATING', 'MAINTENANCE', 'ABNORMAL', 'OFFLINE']" :key="s" class="flex items-center gap-1.5">
              <div class="w-2 h-2 rounded-full" :class="getStatusBgClass(s)"></div>
              <span class="text-[11px] text-muted-500 font-bold uppercase tracking-tight">
                {{ getStatusLabel(s) }}: {{ (stats as any)[s.toLowerCase()] }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button @click="fetchCars" class="p-2 rounded-xl glass-card hover:bg-primary/10 text-primary transition-all active:scale-95" title="重新整理">
          <BaseIcon :path="mdiRefresh" :class="{'animate-spin': loading}" size="22" />
        </button>
      </div>
    </header>

    <!-- Search & Filters -->
    <div class="filter-section glass-card p-4 rounded-2xl border border-white/10 mb-6 flex flex-col md:flex-row items-center gap-4 animate-fade-in">
      <div class="relative flex-1 w-full">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="快速搜尋 車組/序號/識別碼..." 
          class="search-input w-full"
        />
        <div class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-500">
          <BaseIcon :path="mdiMagnify" size="20" />
        </div>
      </div>

      <div class="status-filters flex items-center bg-white/5 p-1 rounded-xl border border-white/10 w-full md:w-auto overflow-x-auto whitespace-nowrap">
        <button 
          v-for="s in ['ALL', 'OPERATING', 'MAINTENANCE', 'ABNORMAL', 'OFFLINE']" 
          :key="s"
          @click="statusFilter = s"
          class="filter-btn"
          :class="statusFilter === s ? 'active' : ''"
        >
          {{ s === 'ALL' ? '全部' : getStatusLabel(s) }}
        </button>
      </div>
    </div>

    <!-- Group List View -->
    <div class="flex-1 overflow-y-auto pt-1 pr-2 custom-scrollbar">
      <div v-if="filteredTrains.length > 0" class="space-y-6 pb-10">
        <section 
          v-for="train in filteredTrains" 
          :key="train.trainCode" 
          class="animate-fade-in p-4 rounded-[1rem] border transition-all duration-300"
          :class="[
            expandedTrains.has(train.trainCode) ? 'bg-white/[0.02]' : '',
            train.carType === 'EXPRESS' ? 'border-purple-300' : 'border-blue-300'
          ]"
        >
          <!-- Train Header (Clickable for dropdown) -->
          <div 
            @click="toggleTrain(train.trainCode)"
            class="flex items-center gap-3 mb-2 px-3 py-2 rounded-xl hover:bg-white/5 cursor-pointer transition-all group/header"
          >
            <h2 class="text-xl font-bold text-theme tracking-tight flex items-center gap-2">
              <BaseIcon 
                :path="mdiTrain" 
                size="24" 
                :class="train.carType === 'EXPRESS' ? 'text-purple-500' : 'text-blue-500'" 
              />
              <span :class="train.carType === 'EXPRESS' ? 'text-purple-500' : 'text-blue-500'">{{ train.trainCode }}</span>
              <span 
                class="px-3 py-1 rounded-xl font-black text-xs text-white shadow-lg"
                :class="train.carType === 'EXPRESS' 
                  ? 'bg-gradient-to-br from-purple-500 to-purple-700 shadow-purple-500/20' 
                  : 'bg-gradient-to-br from-blue-500 to-blue-700 shadow-blue-500/20'"
              >
                {{ train.carTypeName }}
              </span>
            </h2>

            <div class="ml-auto flex items-center gap-6">
              <div class="hidden md:flex items-center gap-4">
                <div v-for="(count, status) in train.statusCounts" :key="status" class="flex items-center gap-1.5 opacity-60">
                  <div class="w-3 h-3 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.2)]" :class="getStatusBgClass(status)"></div>
                  <span class="text-xs font-bold uppercase">{{ getStatusLabel(status) }}: {{ count }}</span>
                </div>
              </div>
              <BaseIcon 
                :path="mdiDotsVertical"
                size="24"
                class="text-muted-500 transition-transform duration-300"
                @click.stop="onNavigatorTrain(train)"
              />
              <BaseIcon 
                :path="mdiChevronDown" 
                size="24" 
                class="text-muted-500 transition-transform duration-300"
                :class="expandedTrains.has(train.trainCode) ? 'rotate-180 text-primary' : ''"
              />
            </div>
          </div>

          <!-- Cars List within Train (Collapsible) -->
          <transition name="expand">
            <div v-show="expandedTrains.has(train.trainCode)" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 mt-4 origin-top">
                <div 
                  v-for="car in train.cars" 
                  :key="car.id"
                  class="car-list-item group relative glass-card rounded-[1.5rem] p-5 flex flex-col gap-4 overflow-hidden border transition-all duration-500 hover:-translate-y-1"
                  :class="train.carType === 'EXPRESS' 
                    ? 'border-purple-500/20 hover:border-purple-500/50 hover:shadow-[0_20px_40px_-15px_rgba(168,85,247,0.25)]' 
                    : 'border-blue-500/20 hover:border-blue-500/50 hover:shadow-[0_20px_40px_-15px_rgba(59,130,246,0.25)]'"
                >
                  <!-- Top Row: Number & Status -->
                  <div class="flex items-start justify-between">
                    <div 
                      class="w-12 h-12 rounded-2xl flex items-center justify-center text-xl font-black shadow-inner"
                      :class="train.carType === 'EXPRESS' 
                        ? 'bg-gradient-to-br from-purple-500 to-purple-700 text-white shadow-purple-500/20' 
                        : 'bg-gradient-to-br from-blue-500 to-blue-700 text-white shadow-blue-500/20'"
                    >
                      {{ car.carNo }}
                    </div>
                    
                    <div class="flex flex-col items-end gap-1">
                      <div 
                        class="px-2.5 py-1 rounded-lg text-xs font-black text-white shadow-lg shadow-black/10"
                        :class="[
                          car.status === 'OPERATING' ? 'bg-gradient-to-br from-[#10B981] to-[#059669]' : 
                          car.status === 'MAINTENANCE' ? 'bg-gradient-to-br from-[#F59E0B] to-[#D97706]' : 
                          car.status === 'ABNORMAL' ? 'bg-gradient-to-br from-[#EF4444] to-[#DC2626]' :
                          'bg-gradient-to-br from-[#64748b] to-[#475569]'
                        ]"
                      >
                        {{ getStatusLabel(car.status) }}
                      </div>
                      <span class="text-[10px] font-mono text-muted-900 uppercase tracking-tighter">{{ car.lastUpdate }}</span>
                    </div>
                  </div>
                  
                  <!-- Middle: VIN & ID -->
                  <div class="flex flex-col gap-0.5 mt-1">
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-bold text-muted-500 uppercase tracking-widest">車輛識別碼</span>
                      <span v-if="car.carVin" class="text-xs font-mono font-bold text-theme">#{{ car.carVin }}</span>
                    </div>
                    <div class="h-[1px] w-full bg-gradient-to-r from-transparent via-white/10 to-transparent my-2"></div>
                  </div>

                  <!-- Bottom: Actions & Label -->
                  <div class="flex items-center justify-between mt-auto pt-2 border-t border-white/5">
                    <div class="flex flex-col">
                      <span class="text-xs text-muted-600 font-bold uppercase">車廂編號</span>
                      <span class="text-sm font-black text-theme">{{ train.trainCode }}-{{ car.carNo }}</span>
                    </div>
                    <div class="flex items-center gap-1">
                      <div class="p-1 text-muted-500 group-hover:text-theme group-hover:translate-x-1 transition-all duration-300" @click="onNavigatorCar(train, car)">
                        <BaseIcon :path="mdiChevronRight" size="20" />
                      </div>
                    </div>
                  </div>

                  <!-- Decorative Background Glow -->
                  <div 
                    class="absolute -bottom-10 -right-10 w-24 h-24 blur-[50px] -z-10 transition-opacity duration-500 opacity-0 group-hover:opacity-100"
                    :class="train.carType === 'EXPRESS' ? 'bg-blue-500/20' : 'bg-blue-500/20'"
                  ></div>
                </div>
            </div>
          </transition>
        </section>
      </div>

      <!-- Empty State -->
      <div v-else class="flex flex-col items-center justify-center py-20 text-muted-500 animate-fade-in">
        <BaseIcon :path="mdiMagnify" size="48" class="mb-4 opacity-20" />
        <p class="font-bold tracking-widest uppercase">找不到符合條件的車輛組群</p>
        <button @click="searchQuery = ''; statusFilter = 'ALL'" class="mt-4 text-xs text-primary font-bold hover:underline">清除搜尋條件</button>
      </div>
    </div>

  </div>
</template>

<style scoped>
.text-theme { color: rgb(var(--fg)); }
.glass-card {
  background-color: rgb(var(--card) / 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.text-success { color: rgb(var(--success)); }
.text-warning { color: rgb(var(--warning)); }
.text-error { color: rgb(var(--error)); }
.text-primary { color: rgb(var(--primary)); }
.text-purple-500 { color: #A855F7; }
.text-blue-500 { color: #3B82F6; }
.bg-blue-500\/10 { background-color: rgba(168, 85, 247, 0.1); }
.bg-blue-500\/10 { background-color: rgba(59, 130, 246, 0.1); }
.border-purple-500\/20 { border-color: rgba(168, 85, 247, 0.2); }
.border-blue-500\/20 { border-color: rgba(59, 130, 246, 0.2); }
.border-purple-500\/30 { border-color: rgba(168, 85, 247, 0.3); }
.border-blue-500\/30 { border-color: rgba(59, 130, 246, 0.3); }
.bg-primary\/10 { background-color: rgb(var(--primary) / 0.1); }

.search-input {
  background-color: rgb(255 255 255 / 0.05);
  border: 1px solid rgb(var(--primary) / 0.3);
  border-radius: 0.75rem;
  padding: 0.625rem 1rem 0.625rem 2.5rem;
  color: rgb(var(--fg));
  outline: none;
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 200ms;
  width: 100%;
}
.search-input:focus {
  border-color: rgb(var(--primary));
  box-shadow: 0 0 0 2px rgb(var(--primary) / 0.1);
}

.filter-btn {
  padding: 0.375rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  transition: all 0.2s;
  color: rgb(var(--fg) / 0.5);
}
.filter-btn:hover {
  color: rgb(var(--fg));
}
.filter-btn.active {
  background-color: rgb(var(--primary));
  color: white;
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

.car-list-item {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  background-color: rgb(var(--card) / 0.6);
  margin-bottom: 0.875rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
}

.car-list-item:hover {
  border-color: rgb(var(--primary) / 0.4);
  background-color: rgb(var(--card) / 0.9);
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
  transform: translateY(-2px);
}

.action-btn {
  display: flex;
  items-center: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.75rem;
  background-color: rgb(255 255 255 / 0.05);
  border: 1px solid rgb(255 255 255 / 0.05);
  font-size: 0.75rem;
  font-weight: 700;
  color: rgb(var(--fg));
  transition: all 0.2s;
}
.action-btn:hover {
  background-color: rgb(var(--primary));
  color: white;
}

.form-input {
  background-color: rgb(255 255 255 / 0.05);
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 0.75rem;
  padding: 0.5rem 0.75rem;
  color: rgb(var(--fg));
  outline: none;
  width: 100%;
}
.form-input:focus {
  border-color: rgb(var(--primary) / 0.5);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgb(var(--border) / 0.5);
  border-radius: 10px;
}
.expand-enter-active, .expand-leave-active {
  transition: all 0.3s ease-out;
  max-height: 1000px;
}
.expand-enter-from, .expand-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-10px);
}
</style>