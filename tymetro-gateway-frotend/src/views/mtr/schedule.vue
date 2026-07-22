<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import ElDialogCustom from '@/components/ElDialogCustom.vue';
import BaseButton from '@/components/BaseButton.vue';
import { useAlert } from '@/composables/TLAlter';
import { useMtrStore } from '@/store/useMtrStore';
import { storeToRefs } from 'pinia';
import AgGridView2 from '@/components/AgGridView2.vue';
import { GridOptions } from 'ag-grid-community';
import {
  getSchedulesList,
  createSchedule,
  updateSchedule,
  deleteSchedule
} from '@/utils/api';
import {
  mdiCalendarSync,
  mdiPlus,
  mdiPencilOutline,
  mdiDeleteOutline,
  mdiClockOutline,
  mdiCheckCircleOutline,
  mdiCloseCircleOutline,
  mdiMagnify,
  mdiClose,
  mdiAlertCircleOutline,
  mdiInformationOutline,
  mdiPlayCircleOutline,
  mdiToggleSwitch,
  mdiToggleSwitchOff,
  mdiRefresh
} from '@mdi/js';

const { TLSuccess, TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '排程設定' }
];

// Schedule Data Interfaces
interface ScheduleItem {
  id: number;
  name: string;
  scheduleType: string; // hourly, minutely, fixed_time, cycle_time, cron
  taskCode?: string;     // SYNC_DEVICE, MONITOR_ALARM, BACKUP_DB, CLEAN_TEMP
  cronExpression?: string;
  minuteOfHour?: number;
  secondOfMinute?: number;
  fixedTime?: string;
  cycleTime?: number;
  isActive: boolean;
  description?: string;
  lastRunAt?: string;
  nextRunAt?: string;
}

const taskOptions = [
  { value: 'SYNC_DEVICE', label: '設備狀態同步 (SYNC_DEVICE)' },
  { value: 'SYNC_SCHEDULE_CONFIG', label: '排程設定同步 (SYNC_SCHEDULE_CONFIG)' },
  { value: 'MONITOR_ALARM', label: '即時警報監測 (MONITOR_ALARM)' },
  { value: 'BACKUP_DB', label: '每日數據備份 (BACKUP_DB)' },
  { value: 'CLEAN_TEMP', label: '暫存快取清理 (CLEAN_TEMP)' },
];

const schedules = ref<ScheduleItem[]>([]);
const loading = ref(false);
const searchKeyword = ref('');
const filterType = ref('');

// Fetch Schedules
const fetchSchedules = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {};
    if (filterType.value) {
      params.scheduleType = filterType.value;
    }
    const res = await getSchedulesList(params);
    if (res && res.data) {
      const dataList = Array.isArray(res.data) ? res.data : (res.data.source || res.data.records || []);
      schedules.value = dataList;
    }
  } catch (error: any) {
    console.error('Fetch schedules error:', error);
    TLError('無法讀取排程設定列表');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchSchedules();
});

const handleReset = () => {
  searchKeyword.value = '';
  filterType.value = '';
  fetchSchedules();
};

// Filter & Search Logic
const filteredSchedules = computed(() => {
  return schedules.value.filter(s => {
    const matchesKeyword = !searchKeyword.value.trim() || 
      s.name.toLowerCase().includes(searchKeyword.value.toLowerCase()) || 
      (s.description && s.description.toLowerCase().includes(searchKeyword.value.toLowerCase()));
    return matchesKeyword;
  });
});

// Stats Computed Properties
const stats = computed(() => {
  const total = schedules.value.length;
  const active = schedules.value.filter(s => s.isActive).length;
  const inactive = total - active;
  return { total, active, inactive };
});

// Modal Dialog States
const showModal = ref(false);
const isEdit = ref(false);
const modalTitle = ref('');

// Form Fields
const formId = ref<number | null>(null);
const formName = ref('');
const formDescription = ref('');
const formScheduleType = ref('hourly');
const formTaskCode = ref('SYNC_DEVICE');
const formIsActive = ref(true);

// Type specific fields
const formCronExpression = ref('');
const formMinuteOfHour = ref<number>(0);
const formSecondOfMinute = ref<number>(0);
const formFixedTime = ref('12:00:00');
const formCycleTime = ref<number>(60);

const mtrStore = useMtrStore();
const { scheduleTypes } = storeToRefs(mtrStore);

const openCreateModal = () => {
  isEdit.value = false;
  modalTitle.value = '新增排程任務';
  formId.value = null;
  formName.value = '';
  formDescription.value = '';
  formScheduleType.value = 'hourly';
  formTaskCode.value = 'SYNC_DEVICE';
  formIsActive.value = true;
  formCronExpression.value = '0 0 * * *';
  formMinuteOfHour.value = 0;
  formSecondOfMinute.value = 0;
  formFixedTime.value = '12:00:00';
  formCycleTime.value = 60;
  showModal.value = true;
};

const openEditModal = (item: ScheduleItem) => {
  isEdit.value = true;
  modalTitle.value = '編輯排程任務';
  formId.value = item.id;
  formName.value = item.name;
  formDescription.value = item.description || '';
  formScheduleType.value = item.scheduleType;
  formTaskCode.value = item.taskCode || 'SYNC_DEVICE';
  formIsActive.value = item.isActive;
  formCronExpression.value = item.cronExpression || '';
  formMinuteOfHour.value = item.minuteOfHour ?? 0;
  formSecondOfMinute.value = item.secondOfMinute ?? 0;
  formFixedTime.value = item.fixedTime || '12:00:00';
  formCycleTime.value = item.cycleTime ?? 60;
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const onDialogClose = (dialogRef: any) => {
  if (dialogRef.success) {
    saveSchedule();
  } else {
    closeModal();
  }
};

// Toggle Schedule Active Status Inline
const toggleActive = async (item: ScheduleItem) => {
  try {
    const payload = {
      isActive: !item.isActive
    };
    await updateSchedule(item.id, payload);
    item.isActive = !item.isActive;
    TLSuccess(`已${item.isActive ? '啟用' : '停用'}排程: ${item.name}`);
    await fetchSchedules();
  } catch (error: any) {
    console.error('Toggle status error:', error);
    TLError('更改狀態失敗');
  }
};

// Save Action
const saveSchedule = async () => {
  if (!formName.value.trim()) {
    TLError('請輸入排程名稱');
    return;
  }

  const payload: Record<string, any> = {
    name: formName.value.trim(),
    scheduleType: formScheduleType.value,
    taskCode: formTaskCode.value || null,
    isActive: formIsActive.value,
    description: formDescription.value.trim() || null
  };

  // Assign parameters based on type
  if (formScheduleType.value === 'cron') {
    if (!formCronExpression.value.trim()) {
      TLError('請輸入 Cron 表達式');
      return;
    }
    payload.cronExpression = formCronExpression.value.trim();
  } else if (formScheduleType.value === 'hourly') {
    payload.minuteOfHour = Number(formMinuteOfHour.value);
  } else if (formScheduleType.value === 'minutely') {
    payload.secondOfMinute = Number(formSecondOfMinute.value);
  } else if (formScheduleType.value === 'fixed_time') {
    if (!formFixedTime.value.trim()) {
      TLError('請輸入固定執行時間');
      return;
    }
    payload.fixedTime = formFixedTime.value.trim();
  } else if (formScheduleType.value === 'cycle_time') {
    payload.cycleTime = Number(formCycleTime.value);
  }

  try {
    if (isEdit.value && formId.value !== null) {
      await updateSchedule(formId.value, payload);
      TLSuccess('更新排程設定成功');
    } else {
      await createSchedule(payload);
      TLSuccess('新增排程設定成功');
    }
    closeModal();
    await fetchSchedules();
  } catch (error: any) {
    console.error('Save schedule error:', error);
    TLError(error.response?.data?.message || '儲存失敗，請重試');
  }
};

// Delete Action
const onDelete = async (item: ScheduleItem) => {
  if (confirm(`確定要刪除排程 [${item.name}] 嗎？`)) {
    try {
      await deleteSchedule(item.id);
      TLSuccess('刪除排程成功');
      await fetchSchedules();
    } catch (error: any) {
      console.error('Delete schedule error:', error);
      TLError('刪除排程失敗');
    }
  }
};

// Helper to format scheduling detail string
const getScheduleDetail = (item: ScheduleItem) => {
  switch (item.scheduleType) {
    case 'hourly':
      return `每小時的第 ${item.minuteOfHour ?? 0} 分鐘`;
    case 'minutely':
      return `每分鐘的第 ${item.secondOfMinute ?? 0} 秒`;
    case 'fixed_time':
      return `每日固定於 ${item.fixedTime}`;
    case 'cycle_time':
      return `每隔 ${item.cycleTime ?? 60} 秒`;
    case 'cron':
      return `Cron: ${item.cronExpression}`;
    default:
      return '未設定';
  }
};

const getTypeLabel = (type: string) => {
  const match = scheduleTypes.value.find(t => t.value === type);
  return match ? match.label : type;
};

const getTypeColor = (type: string) => {
  switch (type) {
    case 'hourly': return 'bg-blue-50 text-blue-700 border-blue-100';
    case 'minutely': return 'bg-cyan-50 text-cyan-700 border-cyan-100';
    case 'fixed_time': return 'bg-amber-50 text-amber-700 border-amber-100';
    case 'cycle_time': return 'bg-orange-50 text-orange-700 border-orange-100';
    case 'cron': return 'bg-purple-50 text-purple-700 border-purple-100';
    default: return 'bg-slate-50 text-slate-700 border-slate-100';
  }
};

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '無記錄';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString('zh-TW', { hour12: false });
  } catch {
    return dateStr;
  }
};

const gridOptions: GridOptions = {
  rowSelection: 'single',
  rowHeight: 56,
  onCellClicked: (params: any) => {
    if (params.colDef.field === 'isActive') {
      toggleActive(params.data);
    }
  },
  autoSizeStrategy: {
    type: 'fitGridWidth',
  }
};

const onGridActionClick = ({ action, data }: any) => {
  if (action.event === 'edit') {
    openEditModal(data);
  } else if (action.event === 'delete') {
    onDelete(data);
  }
};

const gridColumns = ref([
  { headerName: 'ID', field: 'id', flex: 0.5, maxWidth: 80, fontClass: 'font-mono text-slate-400 font-bold' },
  { 
    headerName: '任務名稱', 
    field: 'name', 
    flex: 1.5,
    minWidth: 200,
    cellRenderer: (p: any) => {
      const name = p.data.name;
      const desc = p.data.description || '無描述';
      return `
        <div class="flex flex-col justify-center h-full py-2">
          <div class="font-bold text-slate-800 leading-tight">${name}</div>
          <div class="text-xs text-slate-400 font-semibold mt-0.5 leading-none">${desc}</div>
        </div>
      `;
    }
  },
  {
    headerName: '任務內容',
    field: 'taskCode',
    flex: 1.2,
    minWidth: 300,
    cellRenderer: (p: any) => {
      const code = p.value || '未指定';
      const match = taskOptions.find(t => t.value === code);
      const label = match ? match.label : code;
      return `
        <div class="flex items-center h-full">
          <span class="px-2.5 py-0.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200 inline-block">
            ${label}
          </span>
        </div>
      `;
    }
  },
  { 
    headerName: '排程類型', 
    field: 'scheduleType', 
    flex: 1,
     minWidth: 180,
    cellRenderer: (p: any) => {
      const type = p.value;
      const label = getTypeLabel(type);
      const colorClass = getTypeColor(type);
      return `
        <div class="flex items-center h-full">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-bold shadow-xs border inline-block ${colorClass}">
            ${label}
          </span>
        </div>
      `;
    }
  },
  { 
    headerName: '排程規則', 
    field: 'ruleDetail',
    flex: 1.2,
    minWidth: 180,
    cellRenderer: (p: any) => {
      return `
        <div class="flex items-center h-full font-semibold text-slate-600">
          ${getScheduleDetail(p.data)}
        </div>
      `;
    }
  },
  { 
    headerName: '狀態', 
    field: 'isActive', 
    flex: 0.8,
    cellRenderer: (p: any) => {
      const active = p.value;
      return `
        <div class="flex items-center justify-center h-full cursor-pointer">
          <div class="w-10 h-5.5 rounded-full transition-colors relative duration-200 border ${
            active 
              ? 'bg-[#2a7eb5] border-[#2a7eb5]' 
              : 'bg-slate-200 border-slate-300'
          }">
            <div class="w-4.5 h-4.5 rounded-full bg-white shadow-sm absolute top-0.5 transition-all duration-200 ${
              active ? 'right-0.5' : 'left-0.5'
            }"></div>
          </div>
        </div>
      `;
    }
  },
  { 
    headerName: '上次執行時間', 
    field: 'lastRunAt', 
    flex: 1,
    minWidth: 180,
    cellRenderer: (p: any) => {
      return `
        <div class="flex items-center h-full font-medium text-slate-500">
          ${formatDate(p.value)}
        </div>
      `;
    }
  },
  { 
    headerName: '下次預計執行', 
    field: 'nextRunAt', 
    flex: 1,
    minWidth: 180,
    cellRenderer: (p: any) => {
      return `
        <div class="flex items-center h-full font-medium text-slate-500">
          ${formatDate(p.value)}
        </div>
      `;
    }
  },
  {
    headerName: '操作',
    field: 'actions',
    flex: 0.8,
    cellRenderer: 'AGActionButtonRenderer',
    actionButtons: [
      { label: '編輯', event: 'edit', icon: mdiPencilOutline, iconOnly: true },
      { label: '刪除', event: 'delete', icon: mdiDeleteOutline, iconOnly: true }
    ]
  }
]);
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    <!-- Breadcrumb -->
    <div class="w-full mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <div class="w-full max-w-[1600px] mx-auto space-y-6 px-2">


      <!-- 表格頂端標題與搜尋條件一排 -->
      <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-white rounded-2xl p-4 shadow-xs">
        <!-- 表格頂端標題 -->
        <h3 class="text-slate-800 font-extrabold text-lg flex items-center gap-2 mb-0 shrink-0">
          <BaseIcon :path="mdiCalendarSync" w="20" h="20" size="20" class="text-[#2a7eb5]" />
          排程設定列表
        </h3>

        <!-- 搜尋與按鈕 -->
        <div class="flex flex-wrap items-center gap-4 w-full lg:w-auto justify-end">
          <!-- 關鍵字搜尋 -->
          <div class="flex items-center gap-2">
            <label class="text-xs font-bold text-slate-500 shrink-0 mb-0">搜尋</label>
            <div class="relative w-64">
              <input 
                v-model="searchKeyword"
                type="text" 
                placeholder="搜尋名稱或描述..." 
                class="w-full pl-3 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all text-sm"
              />
              <button
                v-if="searchKeyword"
                @click="searchKeyword = ''"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <BaseIcon :path="mdiClose" w="14" h="14" size="14" />
              </button>
            </div>
          </div>

          <!-- 類型篩選 -->
          <div class="flex items-center gap-2">
            <label class="text-xs font-bold text-slate-500 shrink-0 mb-0">類型</label>
            <div class="relative w-44">
              <select 
                v-model="filterType"
                @change="fetchSchedules"
                class="w-full px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none bg-white transition-all appearance-none text-sm"
              >
                <option value="">全部</option>
                <option v-for="t in scheduleTypes" :key="t.value" :value="t.value">
                  {{ t.label }}
                </option>
              </select>
            </div>
          </div>

          <BaseButton 
            @click="handleReset"
            colorClass="bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 shadow-xs px-4 py-1.5 rounded-lg text-sm font-bold"
            :icon="mdiRefresh"
          >
            重置
          </BaseButton>

          <BaseButton 
            @click="openCreateModal"
            colorClass="bg-[#2a7eb5] hover:bg-[#206796] text-white shadow-xs px-4 py-1.5 rounded-lg text-sm font-bold"
            :icon="mdiPlus"
          >
            新增排程設定
          </BaseButton>
        </div>
      </div>

      <!-- 資料列表表格 (AG Grid) -->
      <div class="h-[calc(100vh-220px)] min-h-[280px]">
        <AgGridView2
          :options="gridOptions"
          :columns="gridColumns"
          :records="filteredSchedules"
          @grid-action-click="onGridActionClick"
        />
      </div>
    </div>

    <!-- 新增 / 修改彈窗 -->
    <ElDialogCustom
      :visible="showModal"
      :title="modalTitle"
      action="確定儲存"
      cancel="取消"
      width="600px"
      minHeight="320px"
      @on-before-close="onDialogClose"
    >
      <div class="space-y-4">
        <!-- 任務名稱 -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-bold text-slate-600">排程名稱 <span class="text-red-500">*</span></label>
          <input 
            v-model="formName" 
            type="text" 
            placeholder="請輸入易懂的排程名稱，例如：車廂數據輪詢" 
            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
          />
        </div>

        <!-- 任務描述 -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-bold text-slate-600">排程描述</label>
          <textarea 
            v-model="formDescription" 
            placeholder="請輸入關於此任務的簡要用途或備註說明..." 
            rows="2"
            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all resize-none"
          ></textarea>
        </div>

        <!-- 任務內容 -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-bold text-slate-600">任務內容 <span class="text-red-500">*</span></label>
          <select 
            v-model="formTaskCode"
            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-bold focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none"
          >
            <option v-for="opt in taskOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- 排程類型 -->
        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-bold text-slate-600">排程類型 <span class="text-red-500">*</span></label>
          <select 
            v-model="formScheduleType"
            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-bold focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none"
          >
            <option v-for="t in scheduleTypes" :key="t.value" :value="t.value">
              {{ t.label }}
            </option>
          </select>
        </div>

        <!-- hourly: 每小時的第幾分鐘 (0-59) -->
        <div v-if="formScheduleType === 'hourly'" class="flex flex-col gap-1.5 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <label class="text-sm font-bold text-slate-600">執行分 (0 - 59)</label>
          <div class="flex items-center gap-3">
            <input 
              v-model="formMinuteOfHour" 
              type="number" min="0" max="59"
              class="w-32 px-4 py-2 rounded-xl border border-slate-200 font-bold focus:border-[#2a7eb5] outline-none"
            />
            <span class="text-xs text-slate-400 font-bold">每小時的第幾分鐘觸發（例：設定 15 即代表每小時的 15 分執行一次）</span>
          </div>
        </div>

        <!-- minutely: 每分鐘的第幾秒 (0-59) -->
        <div v-if="formScheduleType === 'minutely'" class="flex flex-col gap-1.5 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <label class="text-sm font-bold text-slate-600">執行秒 (0 - 59)</label>
          <div class="flex items-center gap-3">
            <input 
              v-model="formSecondOfMinute" 
              type="number" min="0" max="59"
              class="w-32 px-4 py-2 rounded-xl border border-slate-200 font-bold focus:border-[#2a7eb5] outline-none"
            />
            <span class="text-xs text-slate-400 font-bold">每分鐘的第幾秒觸發</span>
          </div>
        </div>

        <!-- fixed_time: 每日固定時間 (HH:mm:ss) -->
        <div v-if="formScheduleType === 'fixed_time'" class="flex flex-col gap-1.5 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <label class="text-sm font-bold text-slate-600">固定時間 (HH:mm:ss)</label>
          <div class="flex items-center gap-3">
            <input 
              v-model="formFixedTime" 
              type="text" placeholder="例如 03:30:00"
              class="w-48 px-4 py-2 rounded-xl border border-slate-200 font-bold focus:border-[#2a7eb5] outline-none"
            />
            <span class="text-xs text-slate-400 font-bold">每天固定此時間執行</span>
          </div>
        </div>

        <!-- cycle_time: 固定週期 (秒數) -->
        <div v-if="formScheduleType === 'cycle_time'" class="flex flex-col gap-1.5 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <label class="text-sm font-bold text-slate-600">間隔秒數 (正整數)</label>
          <div class="flex items-center gap-3">
            <input 
              v-model="formCycleTime" 
              type="number" min="1"
              class="w-32 px-4 py-2 rounded-xl border border-slate-200 font-bold focus:border-[#2a7eb5] outline-none"
            />
            <span class="text-xs text-slate-400 font-bold">秒，系統將會每隔指定秒數循環執行一次任務</span>
          </div>
        </div>

        <!-- cron: Cron Expression -->
        <div v-if="formScheduleType === 'cron'" class="flex flex-col gap-1.5 bg-slate-50 p-4 rounded-xl border border-slate-100">
          <label class="text-sm font-bold text-slate-600">Cron 表達式 (5 或 6 欄位格式)</label>
          <input 
            v-model="formCronExpression" 
            type="text" placeholder="例如 */5 * * * *"
            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-mono font-bold focus:border-[#2a7eb5] outline-none mb-1"
          />
          <div class="text-[11px] text-[#206796] leading-relaxed font-semibold">
            常用格式對照表：<br/>
            • <code class="bg-blue-100/50 px-1 rounded">*/5 * * * *</code> : 每 5 分鐘執行一次<br/>
            • <code class="bg-blue-100/50 px-1 rounded">0 * * * *</code> : 每小時整點執行一次<br/>
            • <code class="bg-blue-100/50 px-1 rounded">0 3 * * *</code> : 每天凌晨 3:00 執行一次<br/>
            • <code class="bg-blue-100/50 px-1 rounded">0 0 * * 1-5</code> : 週一至週五的午夜 00:00 執行一次
          </div>
        </div>

        <!-- 啟用狀態 -->
        <div class="flex items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100">
          <input 
            id="formIsActive"
            v-model="formIsActive" 
            type="checkbox"
            class="w-4 h-4 rounded text-[#2a7eb5] border-slate-300 focus:ring-[#2a7eb5] cursor-pointer"
          />
          <label for="formIsActive" class="text-sm font-bold text-slate-600 cursor-pointer select-none">
            啟用此排程任務 (若停用，背景調度引擎將不會執行它)
          </label>
        </div>
      </div>
    </ElDialogCustom>
  </div>
</template>

<style scoped>
/* Remove number input spin buttons */
input[type=number]::-webkit-inner-spin-button, 
input[type=number]::-webkit-outer-spin-button { 
  -webkit-appearance: none; 
  margin: 0; 
}
input[type=number] {
  -moz-appearance: textfield;
}
</style>
