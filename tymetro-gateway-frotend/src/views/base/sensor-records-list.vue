<script setup lang="ts">
import { ref, onMounted, reactive } from "vue";
import { 
  mdiMagnify, 
  mdiRefresh, 
  mdiChevronLeft,
  mdiChevronRight,
  mdiFilterVariant,
  mdiHelpCircleOutline,
  mdiCogOutline,
  mdiDotsVertical,
  mdiChevronDown,
  mdiPencilOutline,
  mdiDeleteOutline,
  mdiTagOutline,
  mdiClockOutline
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import BaselListView from "./components/BaselListView.vue";
import httpOperations from "@/utils/http-operations";
import { useAlert } from "@/composables/TLAlter";

const { TLWarning, TLSuccess } = useAlert();

interface SensorRecord {
  id: number;
  trainCode: string;
  carNo: number;
  carVin: string;
  equipmentName: string;
  endPos: number;
  sensorType: string;
  sensorCode: string;
  sensorName: string;
  value: number;
}

const loading = ref(false);
const listData = ref<SensorRecord[]>([]);
const total = ref(0);
const selectedIds = ref<Set<number>>(new Set());

const queryForm = reactive({
  trainCode: "",
  equipmentName: "",
  pageIndex: 1,
  pageSize: 100
});

const fetchRecords = async () => {
  loading.value = true;
  selectedIds.value.clear(); // 切換頁面或重新整理時清空選取
  try {
    const params = {
      pageIndex: queryForm.pageIndex - 1,
      pageSize: queryForm.pageSize,
      propertyName: "id",
      trainCode: queryForm.trainCode,
      equipmentName: queryForm.equipmentName
    };
    const response = await httpOperations.get("/api/v1/sensors", params);
    if (response.success) {
      console.log(response.data.source);
      listData.value = response.data.source || [];
      total.value = response.data.total || 0;
    }
  } catch (error) {
    console.error("Failed to fetch sensor records:", error);
    TLWarning("無法取得感測器紀錄");
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  queryForm.pageIndex = 1;
  fetchRecords();
};

const toggleSelection = (id: number) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id);
  } else {
    selectedIds.value.add(id);
  }
};

const toggleSelectAll = () => {
  if (selectedIds.value.size === listData.value.length && listData.value.length > 0) {
    selectedIds.value.clear();
  } else {
    listData.value.forEach(item => selectedIds.value.add(item.id));
  }
};

const handleAction = (action: string, item: any) => {
  if (action === 'edit') {
    TLSuccess(`準備編輯: ${item.equipmentName}`);
  } else if (action === 'delete') {
    TLSuccess(`已刪除: ${item.id}`);
    listData.value = listData.value.filter(i => i.id !== item.id);
  }
};

const handleBatchDelete = () => {
  TLSuccess(`已成功批量刪除 ${selectedIds.value.size} 筆紀錄`);
  listData.value = listData.value.filter(item => !selectedIds.value.has(item.id));
  selectedIds.value.clear();
};

onMounted(() => {
  fetchRecords();
});
</script>

<template>
  <div class="sensor-records-list p-0 flex flex-col h-screen bg-white">
    <!-- Gmail Style Top Search Bar -->
    <header class="h-16 flex items-center px-4 shrink-0 border-b border-transparent">
      <div class="flex-1 max-w-3xl mx-auto relative group">
        <div class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 z-10">
          <BaseIcon :path="mdiMagnify" size="20" />
        </div>
        <input 
          v-model="queryForm.equipmentName"
          type="text" 
          placeholder="搜尋感測器或設備..." 
          class="w-full h-12 bg-slate-100 rounded-full pl-12 pr-12 text-sm focus:bg-white focus:shadow-md outline-none transition-all border border-transparent focus:border-slate-200"
          @keyup.enter="handleSearch"
        />
        <button class="absolute right-4 top-1/2 -translate-y-1/2 p-1.5 rounded-full hover:bg-slate-200 text-slate-500 transition-colors">
          <BaseIcon :path="mdiFilterVariant" size="20" />
        </button>
      </div>
      
      <!-- Right Side Icons -->
      <div class="flex items-center gap-3 ml-4">
        <button class="p-2 rounded-full hover:bg-slate-100 text-slate-600"><BaseIcon :path="mdiHelpCircleOutline" size="22" /></button>
        <button class="p-2 rounded-full hover:bg-slate-100 text-slate-600"><BaseIcon :path="mdiCogOutline" size="22" /></button>
        <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center font-bold text-sm">C</div>
      </div>
    </header>

    <!-- Sub-Toolbar (Actions & Pagination) -->
    <div class="h-12 flex items-center justify-between px-4 shrink-0 border-b border-slate-100">
      <div class="flex items-center gap-1">
        <div class="p-2 rounded hover:bg-slate-100 text-slate-600 cursor-pointer flex items-center" @click="toggleSelectAll">
           <input 
             type="checkbox" 
             class="w-4 h-4 rounded border-slate-300 mr-1 accent-primary cursor-pointer" 
             :checked="listData.length > 0 && selectedIds.size === listData.length"
           />
           <BaseIcon :path="mdiChevronDown" size="14" />
        </div>

        <!-- Default Actions -->
        <template v-if="selectedIds.size === 0">
          <button @click="fetchRecords" class="p-2 rounded-full hover:bg-slate-100 text-slate-600" title="重新整理">
            <BaseIcon :path="mdiRefresh" size="20" />
          </button>
          <button class="p-2 rounded-full hover:bg-slate-100 text-slate-600">
            <BaseIcon :path="mdiDotsVertical" size="20" />
          </button>
        </template>

        <!-- Batch Actions -->
        <template v-else>
          <button @click="handleBatchDelete" class="p-2 rounded-full hover:bg-red-50 text-red-500 transition-colors" title="刪除選中項">
            <BaseIcon :path="mdiDeleteOutline" size="20" />
          </button>
          <button class="p-2 rounded-full hover:bg-slate-100 text-slate-600" title="標記">
            <BaseIcon :path="mdiTagOutline" size="20" />
          </button>
          <button class="p-2 rounded-full hover:bg-slate-100 text-slate-600" title="更多">
            <BaseIcon :path="mdiDotsVertical" size="20" />
          </button>
          <span class="ml-2 text-xs font-bold text-slate-400">已選取 {{ selectedIds.size }} 項</span>
        </template>
      </div>

      <div class="flex items-center gap-4 text-[13px] text-slate-600">
        <div class="font-medium">
          {{ (queryForm.pageIndex - 1) * queryForm.pageSize + 1 }}–{{ Math.min(queryForm.pageIndex * queryForm.pageSize, total) }} 筆 (共 {{ total }} 筆)
        </div>
        <div class="flex items-center gap-1">
          <button 
            class="p-2 rounded-full hover:bg-slate-100 disabled:opacity-30 transition-colors" 
            :disabled="queryForm.pageIndex === 1"
            @click="queryForm.pageIndex--; fetchRecords()"
          >
            <BaseIcon :path="mdiChevronLeft" size="20" />
          </button>
          <button 
            class="p-2 rounded-full hover:bg-slate-100 disabled:opacity-30 transition-colors" 
            :disabled="queryForm.pageIndex >= Math.ceil(total / queryForm.pageSize)"
            @click="queryForm.pageIndex++; fetchRecords()"
          >
            <BaseIcon :path="mdiChevronRight" size="20" />
          </button>
        </div>
      </div>
    </div>

    <!-- Reusable Gmail List View -->
    <BaselListView 
      :listData="listData" 
      :loading="loading" 
      :selectedIds="selectedIds"
      @toggleSelection="toggleSelection"
      @action="handleAction"
    >
      <!-- Field Mappings via Slots -->
      <template #sender="{ item }">
        {{ item.trainCode }} - {{ item.carNo }}車
      </template>

      <template #subject="{ item }">
        {{ item.equipmentName }}
      </template>

      <template #snippet="{ item }">
        | {{ item.sensorName }}: <span class="font-bold text-slate-700">{{ item.value }}</span> 
      </template>

      <template #date="{ item }">
        {{ item.sensorStatusName }}
      </template>

      <template #actions="{ item }">
         <button class="w-9 h-9 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-600 transition-colors" @click.stop="handleAction('edit', item)">
           <BaseIcon :path="mdiPencilOutline" size="20" />
         </button>
         <button class="w-9 h-9 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-600 transition-colors" @click.stop="handleAction('delete', item)">
           <BaseIcon :path="mdiDeleteOutline" size="20" />
         </button>
         <button class="w-9 h-9 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-600 transition-colors">
           <BaseIcon :path="mdiTagOutline" size="20" />
         </button>
         <button class="w-9 h-9 flex items-center justify-center rounded-full hover:bg-slate-200 text-slate-600 transition-colors">
           <BaseIcon :path="mdiClockOutline" size="20" />
         </button>
      </template>
    </BaselListView>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 10px;
}
</style>
