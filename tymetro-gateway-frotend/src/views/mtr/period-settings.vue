<script setup lang="ts">
import { ref, onBeforeMount } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseButton from '@/components/BaseButton.vue';
import ElDialogCustom from '@/components/ElDialogCustom.vue';
import { 
  getConfigsByType, 
  upsertConfig, 
  getTimePeriodTemplateOptions, 
  downloadTimePeriodTemplate 
} from '@/utils/api';
import { useAlert } from '@/composables/TLAlter';
import { 
  mdiWeatherSunny, 
  mdiLightbulbOnOutline,
  mdiCalendarSync,
  mdiCloudDownloadOutline
} from '@mdi/js';

const { TLSuccess, TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '時段設定' }
];

const days = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
const hours = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);

interface ModeOption {
  code: string;
  label: string;
}

const modeOptions: ModeOption[] = [
  { code: 'spring1', label: '春1模式' },
  { code: 'spring2', label: '春2模式' },
  { code: 'summer1', label: '夏1模式' },
  { code: 'summer2', label: '夏2模式' },
  { code: 'autumn1', label: '秋1模式' },
  { code: 'autumn2', label: '秋2模式' },
  { code: 'winter1', label: '冬1模式' },
  { code: 'winter2', label: '冬2模式' }
];

const activeMode = ref(modeOptions[0].code);
const configId = ref<number | null>(null);
const allSchedules = ref<Record<string, number[][]>>({});

// 樣板下載彈窗狀態
const isDialogVisible = ref(false);
const templateOptions = ref<any[]>([]);
const selectedTemplateCode = ref('');
const currentVersion = ref('');

// 預設產生單一模式的 24x7 矩陣
const createDefaultMatrix = () => {
  return Array.from({ length: 24 }, (_, h) => 
    Array.from({ length: 7 }, (_, d) => {
      if (d === 0 || d === 6) {
        return h === 0 ? 24.5 : 0;
      }
      if (h >= 7 && h <= 19) {
        return h === 7 || h === 8 || h === 17 || h === 18 || h === 19 ? 23.5 : 24.5;
      }
      return 24.5;
    })
  );
};

// 初始化預設所有模式結構
modeOptions.forEach(m => {
  allSchedules.value[m.code] = createDefaultMatrix();
});

const scheduleData = ref<number[][]>(allSchedules.value[modeOptions[0].code]);

onBeforeMount(() => {
  getConfigsByType('SCHEDULE')
    .then((response: any) => {
      if (response.data && response.data.id) {
        configId.value = response.data.id;
      }
      if (response.data && response.data.version) {
        currentVersion.value = response.data.version;
      }
      if (response.data && response.data.configContent) {
        try {
          const content = JSON.parse(response.data.configContent);
          modeOptions.forEach(m => {
            if (content[m.code]) {
              allSchedules.value[m.code] = content[m.code];
            } else if (content[m.label]) {
              // 相容舊的中文 key
              allSchedules.value[m.code] = content[m.label];
            }
          });
          scheduleData.value = allSchedules.value[activeMode.value];
        } catch (e) {
          console.log('Parse schedule content error:', e);
        }
      }
    })
    .catch((error) => {
      console.log('Get schedule error:', error);
    });
});

const selectMode = (code: string) => {
  activeMode.value = code;
  scheduleData.value = allSchedules.value[code];
};

const openDownloadDialog = async () => {
  selectedTemplateCode.value = '';
  isDialogVisible.value = true;
  try {
    const res = await getTimePeriodTemplateOptions('SCHEDULE');
    if (res.success && res.data && res.data.source) {
      templateOptions.value = res.data.source;
    } else {
      TLError('獲取時段樣板選項失敗');
    }
  } catch (err) {
    console.error('Fetch template options error:', err);
    TLError('獲取時段樣板選項時發生錯誤');
  }
};

const handleDialogClose = async (dialogRef: any) => {
  if (!dialogRef.success) {
    isDialogVisible.value = false;
    return;
  }
  if (!selectedTemplateCode.value) {
    TLError('請選擇一個時段樣板');
    return;
  }
  try {
    const res = await downloadTimePeriodTemplate(selectedTemplateCode.value);
    if (res.success && res.data && res.data.payload) {
      const payload = res.data.payload;
      const configPayload = {
        configType: 'SCHEDULE',
        configContent: JSON.stringify(payload),
        version: res.data.version || '1.0.0'
      };
      const upsertRes = await upsertConfig(configPayload);
      if (upsertRes.success) {
        TLSuccess('樣板下載並儲存至本機成功！');
        // 更新前端展示
        modeOptions.forEach(m => {
          if (payload[m.code]) {
            allSchedules.value[m.code] = payload[m.code];
          } else if (payload[m.label]) {
            allSchedules.value[m.code] = payload[m.label];
          }
        });
        scheduleData.value = allSchedules.value[activeMode.value];
        if (upsertRes.data && upsertRes.data.id) {
          configId.value = upsertRes.data.id;
        }
        if (upsertRes.data && upsertRes.data.version) {
          currentVersion.value = upsertRes.data.version;
        } else {
          currentVersion.value = configPayload.version;
        }
      } else {
        TLError('樣板儲存至設定資料表失敗');
      }
    } else {
      TLError('下載樣板失敗：' + (res.message || '無效的資料格式'));
    }
  } catch (err: any) {
    console.error('Download template error:', err);
    TLError('下載樣板發生錯誤：' + (err.message || err));
  } finally {
    isDialogVisible.value = false;
  }
};
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    <div class="w-full mb-10">
      <Breadcrumb title="時段設定" :items="breadcrumbItems" />
    </div>

    <div class="w-full px-2 max-w-[1400px] mx-auto">
      <!-- 頂部標題列 -->
      <div class="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-6">
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-slate-800 tracking-wide font-sans">
            模式時段設定
            <span v-if="currentVersion" class="text-sm font-normal text-slate-500 ml-2">(版本: {{ currentVersion }})</span>
          </h1>
        </div>
        <div class="flex flex-wrap items-center gap-3 w-full lg:w-auto">

          <BaseButton 
            @click="openDownloadDialog"
            colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm px-8" 
            :icon="mdiCloudDownloadOutline"
          >
            下載後端時段樣板
          </BaseButton>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
        <!-- 模式切換 Tabs -->
        <div class="flex overflow-x-auto bg-[#2a7eb5] p-1 rounded-lg border border-[#206796] shadow-inner scrollbar-hide max-w-full">
          <BaseButton 
            v-for="item in modeOptions" 
            :key="item.code"
            @click="selectMode(item.code)"
            :colorClass="activeMode === item.code 
              ? 'bg-white text-[#2a7eb5] font-bold shadow-sm border border-white/20' 
              : 'text-white/70 hover:text-white bg-transparent border-transparent shadow-none hover:bg-white/10'"
            class="shrink-0 !px-4 sm:!px-6 !py-1.5 !h-auto text-md"
          >
            {{ item.label }}
          </BaseButton>
        </div>
      </div>

      <!-- 課表/時段 網格 -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col w-full">
        <div class="overflow-auto [scrollbar-width:thin] w-full max-h-[65vh]">
          <table class="w-full text-center border-collapse min-w-[900px]">
            <thead>
              <tr class="border-b border-slate-200 bg-slate-50/50">
                <th class="py-4 px-3 font-medium text-slate-500 w-[100px] border-r border-slate-100 shrink-0 sticky top-0 left-0 bg-slate-50 z-30 shadow-[1px_1px_0_rgba(226,232,240,1)]">
                  <div class="text-md font-bold text-slate-700 mb-0.5">時間設定</div>
                  <div class="text-sm text-slate-400 font-normal">24 小時</div>
                </th>
                <th 
                  v-for="(day, dIdx) in days" 
                  :key="dIdx" 
                  class="py-4 px-3 border-r border-slate-100 font-bold text-slate-700 min-w-[110px] sticky top-0 bg-slate-50 z-20 shadow-[0_1px_0_rgba(226,232,240,1)]"
                >
                   <div class="flex items-center justify-center gap-2.5">
                      <BaseIcon 
                        v-if="dIdx === 0" 
                        :path="mdiWeatherSunny" 
                        size="18" 
                        class="text-amber-500" 
                      />
                      <span class="tracking-widest">{{ day }}</span>
                      <button class="text-blue-400 hover:text-[#2a7eb5] hover:bg-blue-50 p-1 rounded transition-colors focus:outline-none" disabled>
                        <BaseIcon :path="mdiCalendarSync" size="16" />
                      </button>
                   </div>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="(hour, hIdx) in hours" 
                :key="hIdx" 
                class="border-b border-slate-100 hover:bg-slate-50/50 transition-colors group"
              >
                <td class="py-2.5 px-3 font-medium text-slate-600 text-sm border-r border-slate-100 sticky left-0 bg-white group-hover:bg-slate-50/50 z-10 shadow-[1px_0_0_rgba(241,245,249,1)]">
                  {{ hour }}
                </td>
                <td 
                  v-for="(day, dIdx) in days" 
                  :key="dIdx" 
                  class="py-2.5 px-3 border-r border-slate-100"
                >
                   <div class="flex items-center justify-center gap-2">
                     <input 
                       type="number" 
                       step="0.5"
                       v-model="scheduleData[hIdx][dIdx]" 
                       disabled
                       class="w-[70px] px-2 py-1.5 text-center border border-slate-200 rounded-md text-md font-medium text-slate-500 bg-slate-50 cursor-not-allowed"
                     />
                     <span class="text-[11px] text-slate-400 font-bold shrink-0">°C</span>
                   </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 提示框 -->
      <div class="mt-6 flex items-start gap-3 p-4 bg-blue-50/50 border border-blue-100 rounded-lg w-full shadow-sm">
        <BaseIcon :path="mdiLightbulbOnOutline" size="24" class="text-[#2a7eb5] shrink-0" />
        <p class="text-sm text-[#206796] leading-relaxed font-medium pt-0.5 tracking-wide">
          提示：已改為下載後端時段樣板，本頁面目前為唯讀狀態。
        </p>
      </div>

    </div>

    <!-- 下載樣板選擇彈窗 -->
    <ElDialogCustom
      v-model:visible="isDialogVisible"
      title="選擇下載時段樣板"
      width="480px"
      minHeight="120px"
      action="確認下載"
      @on-before-close="handleDialogClose"
    >
      <div class="py-4 px-2">
        <label class="block text-sm font-semibold text-slate-700 mb-2">時段樣板：</label>
        <el-select v-model="selectedTemplateCode" placeholder="請選擇時段樣板" class="w-full" size="large">
          <el-option
            v-for="item in templateOptions"
            :key="item.code"
            :label="`${item.name} (${item.code})`"
            :value="item.code"
          >
            <div class="flex justify-between items-center w-full">
              <span class="font-medium text-slate-700">{{ item.name }}</span>
              <span class="text-xs text-slate-400">版本: {{ item.version }}</span>
            </div>
          </el-option>
        </el-select>
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

</style>
