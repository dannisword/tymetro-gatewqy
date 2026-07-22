<script setup lang="ts">
import { ref, onMounted, reactive } from "vue";
import { 
  mdiMagnify, 
  mdiRefresh, 
  mdiPlus,
  mdiPencilOutline,
  mdiDeleteOutline,
  mdiClockOutline,
  mdiFileDocumentOutline,
  mdiChevronDown
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import BaselListView from "./BaselListView.vue";
import httpOperations from "@/utils/http-operations";
import { useAlert } from "@/composables/TLAlter";
import { usePermissionStore } from "@/store/usePermissionStore";

const { TLWarning, TLSuccess } = useAlert();
const permissionStore = usePermissionStore();

const hasPermission = (p: string) => permissionStore.hasPermission(p);

interface SensorTemplate {
  id: number;
  templateName: string;
  templateCode: string;
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}

interface ApiResponse<T> {
  success: boolean;
  data: {
    source: T[];
    total: number;
  };
}

const loading = ref(false);
const listData = ref<SensorTemplate[]>([]);
const total = ref(0);
const selectedEquipmentId = ref<number | null>(null);
const selectedIds = ref<Set<number>>(new Set());

const queryForm = reactive({
  templateName: "",
  pageIndex: 1,
  pageSize: 1000
});

const equipmentOptions = ref<{ value: string; id: number }[]>([]);

const querySearch = (queryString: string, cb: any) => {
  const results = queryString
    ? equipmentOptions.value.filter(option => 
        option.value.toLowerCase().includes(queryString.toLowerCase())
      )
    : equipmentOptions.value;
  cb(results);
};

const fetchEquipments = async () => {
  try {
    const response = await httpOperations.get<any>("/api/v1/equipments");
    if (response.success && response.data) {
      equipmentOptions.value = response.data.source.map((e: any) => ({
        value: `${e.equipmentName} (${e.trainCode}-${e.carNo})`,
        id: e.id
      }));
    }
  } catch (error) {
    console.error("Failed to fetch equipments:", error);
  }
};

const fetchTemplates = async () => {
  loading.value = true;
  selectedIds.value.clear();
  try {
    const params = {
      pageIndex: queryForm.pageIndex - 1,
      pageSize: queryForm.pageSize,
      propertyName: "id",
      order: "DESC",
      templateName: queryForm.templateName
    };
    const response = await httpOperations.get<ApiResponse<SensorTemplate>>("/api/v1/sensor-templates", params);
    if (response.success) {
      listData.value = response.data.source || [];
      total.value = response.data.total || 0;
    }
  } catch (error) {
    console.error("Failed to fetch sensor templates:", error);
    TLWarning("無法取得感測器範本");
  } finally {
    loading.value = false;
  }
};

const handleSelect = (item: any) => {
  selectedEquipmentId.value = item.id;
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

const handleBatchDelete = () => {
  TLSuccess(`已成功批量刪除 ${selectedIds.value.size} 筆範本`);
  listData.value = listData.value.filter(item => !selectedIds.value.has(item.id));
  selectedIds.value.clear();
};

const handleAction = (action: string, item: any) => {
  if (action === 'edit') {
    TLSuccess(`準備編輯範本: ${item.templateName}`);
  } else if (action === 'delete') {
    TLSuccess(`已刪除範本: ${item.id}`);
    listData.value = listData.value.filter(i => i.id !== item.id);
  }
};

const createTemplate = () => {
  TLSuccess("開始建立新範本");
};

onMounted(() => {
  fetchEquipments();
  fetchTemplates();
});

const getSelectedItems = () => listData.value.filter(item => selectedIds.value.has(item.id));

// 暴露給父組件的方法與資料
defineExpose({
  selectedEquipmentId,
  selectedIds,
  getSelectedItems,
  refresh: fetchTemplates
});
</script>

<template>
  <div class="sensor-template-view flex flex-col h-full bg-white border border-slate-200 overflow-hidden">
    <!-- Header -->
    <header class="h-14 flex items-center justify-between px-4 border-b border-slate-100 bg-slate-50/50">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <BaseIcon :path="mdiFileDocumentOutline" size="20" />
        </div>
        <h2 class="text-sm font-bold text-slate-700 uppercase tracking-wider">感測器複製</h2>
      </div>
      
      <div class="flex items-center gap-2">
        <div class="relative">
          <el-autocomplete
            v-model="queryForm.templateName"
            :fetch-suggestions="querySearch"
            placeholder="搜尋並選擇設備..."
            clearable
            class="w-64"
            @select="handleSelect"
          >
            <template #default="{ item }">
              <div class="text-[13px] py-1">{{ item.value }}</div>
            </template>
          </el-autocomplete>
        </div>
        
        <button 
          @click="fetchTemplates" 
          class="w-9 h-9 flex items-center justify-center rounded-lg border border-slate-200 hover:bg-white hover:text-primary transition-all text-slate-500"
          title="重新整理"
        >
          <BaseIcon :path="mdiRefresh" size="18" />
        </button>
        
        <button 
          v-if="hasPermission('SENSOR_TEMPLATE_CREATE')"
          @click="createTemplate"
          class="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-white text-xs font-bold hover:shadow-lg hover:shadow-primary/30 active:scale-95 transition-all"
        >
          <BaseIcon :path="mdiPlus" size="18" />
          <span>建立範本</span>
        </button>
      </div>
    </header>

    <!-- Sub-Toolbar (Selection & Batch Actions) -->
    <div class="h-10 flex items-center px-4 shrink-0 border-b border-slate-50 bg-slate-50/30">
      <div class="flex items-center gap-1">
        <div class="p-1.5 rounded hover:bg-slate-100 text-slate-500 cursor-pointer flex items-center group/all" @click="toggleSelectAll">
           <input 
             type="checkbox" 
             class="w-3.5 h-3.5 rounded border-slate-300 mr-1 accent-primary cursor-pointer" 
             :checked="listData.length > 0 && selectedIds.size === listData.length"
           />
           <BaseIcon :path="mdiChevronDown" size="12" class="opacity-0 group-hover/all:opacity-100 transition-opacity" />
        </div>

        <template v-if="selectedIds.size > 0">
          <div class="w-px h-4 bg-slate-200 mx-2"></div>
          <button 
            v-if="hasPermission('SENSOR_TEMPLATE_DELETE')"
            @click="handleBatchDelete" 
            class="h-8 px-3 flex items-center gap-2 rounded-lg hover:bg-red-50 text-red-500 text-xs font-bold transition-colors"
          >
            <BaseIcon :path="mdiDeleteOutline" size="16" />
            <span>批量刪除 ({{ selectedIds.size }})</span>
          </button>
        </template>
      </div>
    </div>

    <!-- Content (Scrollable Area) -->
    <div class="flex-1 overflow-hidden relative flex flex-col">
      <BaselListView 
        :listData="listData" 
        :loading="loading" 
        :selectedIds="selectedIds"
        row-height="56px"
        @toggleSelection="toggleSelection"
        @action="handleAction"
      >
        <!-- Field Mappings via Slots -->
        <template #sender="{ item }">
          <div class="flex flex-col leading-tight">
            <span class="text-[13px] font-bold text-slate-700">{{ item.templateName }}</span>
            <span class="text-[11px] text-slate-400 font-mono">{{ item.templateCode }}</span>
          </div>
        </template>

        <template #subject="{ item }">
          <span class="text-slate-500 text-[13px]">{{ item.sensorTypeName || '-' }}</span>
        </template>

        <template #snippet="{ item }">
          <span class="text-slate-500 text-[13px]">{{ item.sensorCode || '-' }}</span>
          <span class="text-slate-500 text-[13px]"> | </span>
          <span class="text-slate-500 text-[13px]">{{ item.sensorName || '-' }}</span>
        </template>

        <template #date="{ item }">
          <div class="flex items-center gap-1.5 text-slate-400">
            <BaseIcon :path="mdiClockOutline" size="14" />
            <span class="text-[11px] font-medium">{{ item.createdAt ? new Date(item.createdAt).toLocaleDateString() : 'N/A' }}</span>
          </div>
        </template>

        <template #actions="{ item, hasPermission }">
           <button 
             class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white hover:text-primary hover:shadow-sm border border-transparent hover:border-slate-100 text-slate-400 transition-all" 
             @click.stop="handleAction('edit', item)"
           >
             <BaseIcon :path="mdiPencilOutline" size="18" />
           </button>
           <button 
             class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white hover:text-red-50 hover:shadow-sm border border-transparent hover:border-red-100 text-slate-400 transition-all" 
             @click.stop="handleAction('delete', item)"
           >
             <BaseIcon :path="mdiDeleteOutline" size="18" />
           </button>
        </template>
      </BaselListView>
    </div>

    <!-- Footer / Pagination -->
    <footer class="h-10 px-4 flex items-center justify-between bg-slate-50 border-t border-slate-100 text-[11px] text-slate-500 font-bold uppercase tracking-widest">
      <div>已選取 {{ selectedIds.size }} 個範本</div>
      <div class="flex items-center gap-4">
        <span>共 {{ total }} 個結果</span>
        <div class="flex items-center gap-2">
          <span>第 {{ queryForm.pageIndex }} 頁</span>
          <!-- Simple Pagination can be added here if needed -->
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.sensor-template-view {
  animation: slide-in 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slide-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Scrollbar Styling */
:deep(.custom-scrollbar::-webkit-scrollbar) {
  width: 8px;
}
:deep(.custom-scrollbar::-webkit-scrollbar-track) {
  background: #f8fafc;
}
:deep(.custom-scrollbar::-webkit-scrollbar-thumb) {
  background: #cbd5e1;
  border-radius: 10px;
  border: 2px solid #f8fafc;
}
:deep(.custom-scrollbar::-webkit-scrollbar-thumb:hover) {
  background: #94a3b8;
}

/* 強制滿版：移除彈窗的預設 Padding */
:global(.el-dialog.is-fullscreen .el-dialog__body) {
  padding: 0 !important;
}
:global(.el-dialog.is-fullscreen .dialog-content) {
  height: calc(100vh - 120px); /* 扣除 Header 與 Footer */
}
</style>
