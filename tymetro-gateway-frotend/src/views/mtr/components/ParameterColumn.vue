<script setup lang="ts">
import { PropType } from 'vue';
import { mdiChevronUp, mdiChevronDown } from '@mdi/js';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseButton from '@/components/BaseButton.vue';

const props = defineProps({
  items: {
    type: Array as PropType<any[]>,
    required: true
  }
});

const emit = defineEmits(['save']);

const handleItemClick = (item: any) => {
  item.isOpen = !item.isOpen;
};

const handleSave = (name: string, formData: any) => {
  emit('save', name, formData);
};
</script>

<template>
  <div class="flex flex-col gap-5">
    <div 
      v-for="(item, index) in items" 
      :key="'param-'+index"
      class="bg-white rounded-lg border border-blue-200 shadow-sm overflow-hidden flex flex-col transition-all hover:shadow-md"
    >
      <!-- 卡片標題列 -->
      <div 
        @click="handleItemClick(item)"
        class="px-4 py-3.5 cursor-pointer transition-colors flex justify-between items-center border-b bg-[#2a7eb5] "
      >
        <span class="font-bold text-[15px] tracking-wide text-white">
          {{ item.name }}
        </span>
        <BaseIcon 
          :path="item.isOpen ? mdiChevronUp : mdiChevronDown" 
          size="20" 
          class="text-white transition-transform duration-200" 
        />
      </div>
      
      <!-- 折疊內容區塊 -->
      <div v-show="item.isOpen" class="p-4 bg-white text-sm text-slate-600">
    
          
          <!-- 針對有設定 fields 的項目動態渲染表單 -->
          <template v-if="item.fields && item.fields.length > 0">
            <div class="flex flex-col gap-4 mt-1">
              
              <!-- 動態渲染每個欄位 -->
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div v-for="field in item.fields" :key="field.key">
                  <label class="block font-semibold mb-1 tracking-wide">
                    {{ field.label }}
                  </label>
                  <input 
                    :type="field.type" 
                    :placeholder="field.placeholder" 
                    v-model="item.formData![field.key]"
                    class="w-full px-3 py-2 bg-white border border-slate-300 rounded-md shadow-sm focus:outline-none focus:border-[#2a7eb5] focus:ring-1 focus:ring-[#2a7eb5] transition-all"
                  >
                </div>
              </div>

              <!-- 儲存按鈕 -->
              <div class="flex justify-end pt-2">
                <BaseButton 
                  @click.stop="handleSave(item.name, item.formData)"
                  colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm"
                >
                  儲存設定
                </BaseButton>
              </div>
            </div>
          </template>

          <!-- 其他項目的預設佔位 -->
          <template v-else>
            <p class="mb-2 font-bold text-slate-700">{{ item.name }} 詳細設定</p>
            <p class="text-slate-500">此處可放置表單、開關或參數輸入框...</p>
          </template>

        
      </div>
    </div>
  </div>
</template>
