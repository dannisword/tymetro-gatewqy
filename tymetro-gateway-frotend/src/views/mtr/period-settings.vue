<script setup lang="ts">
import { ref, onBeforeMount } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseButton from '@/components/BaseButton.vue';
import { getConfigsByType, updateConfig } from '@/utils/api';
import { useAlert } from '@/composables/TLAlter';
import { 
  mdiWeatherSunny, 
  mdiLightbulbOnOutline,
  mdiCalendarSync
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

const onSave = () => {
  console.log('Saved data:', allSchedules.value);
  if (configId.value) {
    const payload = {
      configType: 'SCHEDULE',
      configContent: JSON.stringify(allSchedules.value)
    };
    updateConfig(configId.value, payload)
      .then(() => {
        TLSuccess('所有時段設定儲存成功！');
      })
      .catch((err) => {
        console.log('Update schedule error:', err);
        TLError('時段設定儲存失敗');
      });
  } else {
    TLError('尚未取得設定代碼，無法儲存');
  }
};

const onClear = () => {
  const currentOption = modeOptions.find(m => m.code === activeMode.value);
  if (confirm(`確定要清除【${currentOption?.label}】的所有時段設定為 0 嗎？`)) {
    const emptyMatrix = Array.from({ length: 24 }, () => Array.from({ length: 7 }, () => 0));
    allSchedules.value[activeMode.value] = emptyMatrix;
    scheduleData.value = emptyMatrix;
  }
};

const onCopy = () => {
  const currentOption = modeOptions.find(m => m.code === activeMode.value);
  navigator.clipboard.writeText(JSON.stringify(scheduleData.value))
    .then(() => TLSuccess(`已複製【${currentOption?.label}】的時段表資料`))
    .catch(() => TLError('複製失敗'));
};

const onPaste = async () => {
  try {
    const text = await navigator.clipboard.readText();
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed) && parsed.length === 24 && Array.isArray(parsed[0]) && parsed[0].length === 7) {
      const currentOption = modeOptions.find(m => m.code === activeMode.value);
      allSchedules.value[activeMode.value] = parsed;
      scheduleData.value = parsed;
      TLSuccess(`已成功貼上至【${currentOption?.label}】`);
    } else {
      TLError('剪貼簿資料格式不符 (需為 24x7 溫度陣列)');
    }
  } catch (e) {
    console.log('Paste error:', e);
    TLError('無法讀取剪貼簿，請確認資料格式或瀏覽器權限');
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
          <h1 class="text-2xl font-bold text-slate-800 tracking-wide font-sans">模式時段設定</h1>
        </div>
        <div class="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          <BaseButton 
            @click="onCopy"
            colorClass="bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-sm" 
            icon="mdiContentCopy"
          >
            複製
          </BaseButton>
          <BaseButton 
            @click="onPaste"
            colorClass="bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-sm" 
            icon="mdiClipboardOutline"
          >
            貼上
          </BaseButton>
          <BaseButton 
            @click="onClear"
            colorClass="bg-white border border-red-200 text-red-500 hover:bg-red-50 hover:border-red-300 shadow-sm" 
            icon="mdiDeleteOutline"
          >
            清除
          </BaseButton>
          <BaseButton 
            @click="onSave"
            colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm px-8" 
          >
            儲存
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
                      <button class="text-blue-400 hover:text-[#2a7eb5] hover:bg-blue-50 p-1 rounded transition-colors focus:outline-none">
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
                       class="w-[70px] px-2 py-1.5 text-center border border-slate-200 rounded-md text-md font-medium text-slate-700 focus:outline-none focus:border-[#2a7eb5] focus:ring-1 focus:ring-[#2a7eb5] transition-all hover:border-slate-300"
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
          提示：設定每小時的目標溫度，控制器將依設定自動運行。
        </p>
      </div>

    </div>
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
