<script setup lang="ts">
import { ref, onBeforeMount, watch } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import { getConfigsByType, updateConfig } from '@/utils/api';
import { useAlert } from '@/composables/TLAlter';
import BaseButton from '@/components/BaseButton.vue';
import ParameterColumn from './components/ParameterColumn.vue';
import { useMtrStore } from '@/store/useMtrStore';

const { TLSuccess, TLError } = useAlert();
const mtrStore = useMtrStore();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '參數設定' }
];

interface FieldConfig {
  label: string;
  key: string;
  type: string;
  placeholder: string;
}

interface ParameterItem {
  name: string;
  code: string;
  isOpen: boolean;
  fields?: FieldConfig[];
  formData?: Record<string, any>;
}

const leftItems = ref<ParameterItem[]>([]);
const rightItems = ref<ParameterItem[]>([]);

const emit = defineEmits(['save']);
const configId = ref<number | null>(null);

const fetchConfig = () => {

  getConfigsByType('MTR_PARAMS')
  .then((response : any) => {
    if (response.data && response.data.id) {
      configId.value = response.data.id;
    }
    if (response.data && response.data.configContent) {
      const content = JSON.parse(response.data.configContent);
      if (content.leftItems && Array.isArray(content.leftItems)) {
        leftItems.value = content.leftItems;
      }
      if (content.rightItems && Array.isArray(content.rightItems)) {
        rightItems.value = content.rightItems;
      }
    }
  })
  .catch((error) => {
    console.log(error)
  })
};

watch(() => mtrStore.activeCarId, () => {
  fetchConfig();
});

onBeforeMount(() => {
  fetchConfig();
});

const saveCurrentConfig = () => {
  if (configId.value) {
    const payload = {
      configType: 'MTR_PARAMS',
      configContent: JSON.stringify({
        leftItems: leftItems.value,
        rightItems: rightItems.value
      })
    };
    updateConfig(configId.value, payload)
      .then((res: any) => {
        TLSuccess('參數設定儲存成功！');
      })
      .catch((err: any) => {
        TLError('參數設定儲存失敗');
      });
  } else {
    TLError('尚未取得設定代碼，無法儲存');
  }
};

const onSave = (name: string, data: any) => {
  saveCurrentConfig();
};

const onRemoteUpdate = () => {
  saveCurrentConfig();
};
</script>

<template>
  <div class="w-full">
    <!-- Breadcrumb -->
    <div class="w-full mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <!-- 內容區域 -->
    <div class="w-full px-2">
      <!-- 標題與操作按鈕 -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 mb-6 border-b border-gray-100 pb-4">
        <h2 class="text-2xl font-bold text-[#2a7eb5] tracking-wide font-sans mb-0">
          設備與參數管理
        </h2>
        <div class="flex gap-3">
          <BaseButton 
            colorClass="bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:text-[#2a7eb5] hover:border-[#2a7eb5] shadow-sm"
            icon="mdiCog"
          >
            PLC 設定
          </BaseButton>
          <BaseButton 
            colorClass="bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:text-[#2a7eb5] hover:border-[#2a7eb5] shadow-sm"
            icon="mdiDownload"
          >
            下載資料
          </BaseButton>
          <BaseButton 
            @click="onRemoteUpdate"
            colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm"
            icon="mdiCloudUpload"
          >
            遠端更新
          </BaseButton>
        </div>
      </div>

      <!-- 兩欄列表 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 mt-4">
        <ParameterColumn :items="leftItems" @save="onSave" />
        <ParameterColumn :items="rightItems" @save="onSave" />
      </div>
    </div>
  </div>
</template>
