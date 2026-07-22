<!-- components/ActionButtonRenderer.vue -->
<script setup lang="ts">
import {
  PropType,
  ref,
  reactive,
  onMounted,
  onBeforeMount,
  watch,
  computed,
} from "vue";

const props = defineProps({
  params: {} as PropType<any>,
});

const label = props.params.label || "操作";

const data = reactive({});
onBeforeMount(() => {
  //console.log('ActionButtonRenderer',props.params.colDef);
});

const handleClick = (action: any, data: any) => {
  props.params.onAction(action, data);
};

const getButtonColorClass = (action: any) => {
  const type = action.type || (action.event === 'delete' ? 'danger' : 'primary');
  
  if (type === 'danger') {
    return 'text-red-500 hover:text-red-600 hover:bg-red-50/80 bg-transparent border-0';
  }
  if (type === 'success') {
    return 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50/80 bg-transparent border-0';
  }
  if (type === 'warning') {
    return 'text-amber-500 hover:text-amber-600 hover:bg-amber-50/80 bg-transparent border-0';
  }
  // 預設與編輯：同色系（鋼藍色系統）
  return 'text-[#2a7eb5] hover:text-[#206796] hover:bg-blue-50/60 bg-transparent border-0';
};
</script>

<template>
  <div class="flex justify-center align-middles m-1 gap-1">
    <template v-for="(action, index) in props.params.actions" :key="index">
      <span class="inline-flex flex-nowrap">
        <BaseButton
          :size="'sm'"
          :icon="action.icon"
          :icon-only="action.iconOnly"
          :colorClass="getButtonColorClass(action)"
          @click="() => handleClick(action, props.params.data)"
        >
        {{ action.label }}
        </BaseButton>
      </span>
    </template>
  </div>
</template>
