<script setup lang="ts">
import type { ICellRendererParams } from "ag-grid-community";
import { shallowRef } from "vue";

// refresh 時可更新
const props = defineProps<{ params: ICellRendererParams }>();
const params = shallowRef(props.params);

// AG Grid 可能呼叫 refresh 更新資料；回傳 true 表示用現有 DOM 更新
function refresh(newParams: ICellRendererParams) {
  params.value = newParams;
  return true;
}
defineExpose({ refresh });

// 顯示字串或從 params 取 formatter 後結果
const getValueText = () => {
  const v = params.value.value;
  return v == null || v === "" ? "-" : String(v);
};
const getButtonClass = (colDef: any) => {
  const map: Record<string, string> = {
    primary:
      "!bg-primary-500 !border-primary-500 !text-white hover:!bg-primary-600 focus:!ring-2 focus:!ring-primary-200",
    success:
      "!bg-success-500 !border-success-500 !text-white hover:!bg-success-600 focus:!ring-2 focus:!ring-success-200",
    warning:
      "!bg-warning-500 !border-warning-500 !text-white hover:!bg-warning-600 focus:!ring-2 focus:!ring-warning-200",
    danger:
      "!bg-error-500 !border-error-500 !text-white hover:!bg-error-600 focus:!ring-2 focus:!ring-error-200",
    info: "!bg-info-500 !border-info-500 !text-white hover:!bg-info-600 focus:!ring-2 focus:!ring-info-200",
  };
  return map[colDef.type] || map.primary;
};
</script>

<template>
  <span
    class="inline-flex items-center rounded px-2 py-0.5 text-xs border"
    :class="getButtonClass(params.colDef)"
  >
    {{ getValueText() }}
  </span>
</template>

