<script setup lang="ts">
import { PropType, reactive, watch } from "vue";
import { mdiMagnify, mdiClose } from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";

const props = defineProps({
  schemas: { type: Array as PropType<any[]>, required: true },
  advanced: { type: Array as PropType<any[]>, required: false },
  actions: { type: Array as PropType<any[]>, required: false },
});

const emit = defineEmits(["confirm", "clear", "change", "select-change"]);

const data = reactive({
  component: [] as any[],
  docStatus: {} as any,
  execName: "查詢",
  moreName: "更多",
});

watch(
  () => props.schemas,
  (val) => {
    if (val) {
      data.component = props.schemas;
    }
    if (props.actions && props.actions.length > 0) {
      data.execName = props.actions[0].name;
    }
  },
  { immediate: true },
);

const onClear = () => emit("clear");
const onConfirm = () => emit("confirm", props.actions);
const onChange = (val: any) => emit("change", val);
const onSelectChange = (prop: any, val: any) => {
  emit("select-change", prop, val);
};
</script>

<template>
  <div class="search-container bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm mb-4 px-6 py-4">
    <el-form
      label-width="auto"
      :inline="true"
      class="search-form"
      @submit.prevent
    >
      <div class="flex flex-wrap items-center gap-x-8 gap-y-4">
        <!-- 動態渲染搜尋欄位 -->
        <el-form-item
          v-for="schema in props.schemas"
          :key="schema.prop"
          :label="schema.label"
          class="custom-search-item !mb-0"
        >
          <div class="item-inner">
            <!-- Select -->
            <el-select
              v-if="schema.type == 'select'"
              v-model="schema.value"
              :disabled="schema.disabled"
              placeholder="請選擇"
              @change="onSelectChange(schema.prop, schema.value)"
              clearable
              filterable
              class="w-[200px]"
              @keyup.enter="onConfirm"
            >
              <el-option
                v-for="option in schema.options"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <!-- Multiple Select -->
            <el-select
              v-else-if="schema.type == 'multiple-select'"
              v-model="schema.value"
              multiple
              placeholder="請選擇"
              @change="onSelectChange(schema.prop, schema.value)"
              clearable
              filterable
              collapse-tags
              class="w-[220px]"
              @keyup.enter="onConfirm"
            >
              <el-option
                v-for="option in schema.options"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <!-- Date Range -->
            <el-date-picker
              v-else-if="schema.type == 'date'"
              v-model="schema.value"
              type="daterange"
              range-separator="-"
              start-placeholder="開始"
              end-placeholder="結束"
              class="!w-[280px]"
              @keyup.enter="onConfirm"
            />

            <!-- Input / Text -->
            <el-input
              v-else-if="schema.type == 'text' || schema.type == 'input'"
              v-model="schema.value"
              placeholder="請輸入"
              clearable
              class="w-[200px]"
              @keyup.enter="onConfirm"
            />

            <!-- Checkbox Group -->
            <el-checkbox-group
              v-else-if="schema.type == 'checkboxs'"
              v-model.lazy="schema.value"
              :disabled="schema.disabled"
              @change="onChange"
            >
              <el-checkbox
                v-for="option in schema.options"
                :key="option.value"
                :label="option.value"
              >
                {{ option.label }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </el-form-item>

        <!-- 操作按鈕區 -->
        <div class="flex items-center gap-3 ml-auto pt-1">
          <el-button 
            type="primary" 
            @click="onConfirm" 
            class="!px-6 !bg-primary !border-primary shadow-sm hover:translate-y-[-1px] transition-all"
          >
            <el-icon class="mr-1.5"><Search /></el-icon>
            {{ data.execName }}
          </el-button>
          
          <el-button 
            @click="onClear" 
            class="!px-6 hover:!text-primary hover:!bg-primary-50 transition-all font-normal"
          >
            <el-icon class="mr-1.5"><Close /></el-icon>
            清除
          </el-button>
        </div>
      </div>
    </el-form>
  </div>
</template>

<style scoped>
.search-container {
  transition: all 0.3s ease;
}

.search-container:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #475569;
  padding-right: 12px;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px #e2e8f0 inset !important;
  border-radius: 8px;
  background-color: #f8fafc;
}

:deep(.dark .el-input__wrapper),
:deep(.dark .el-select__wrapper) {
  background-color: #0f172a;
  box-shadow: 0 0 0 1px #334155 inset !important;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

/* 為了讓搜尋按鈕組在行動端也好看 */
@media (max-width: 768px) {
  .ml-auto {
    margin-left: 0;
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
