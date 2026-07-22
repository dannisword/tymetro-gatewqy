<script setup lang="ts">
import { PropType, ref } from "vue";

const props = defineProps({
  items: { type: Array as PropType<any[]>, default: () => [] },
  current: { type: String, default: false },
  isCollapsed: { type: Boolean, default: false },
});
const emit = defineEmits(["update"]);
const onClick = (item: any) => {
  //current.value = item.label;
  emit("update", item);
};
</script>

<template>
  <nav class="flex-1 px-2 py-4 space-y-2 bg-card">
    <a v-for="item in items" :key="item.label"
      class="flex items-center py-2 text-sm font-medium rounded-md hover:bg-theme hover:text-white cursor-pointer transition-all"
      :class="[
        current === item.label ? 'bg-theme text-white' : 'text-slate-600',
        isCollapsed ? 'justify-center px-0' : 'px-2'
      ]" @click="onClick(item)">

      <span class="material-symbols-outlined" :class="{ 'mr-2': !isCollapsed }">
        {{ item.icon }}
      </span>

      <span v-show="!isCollapsed" class="truncate">
        {{ item.label }}
      </span>

    </a>
  </nav>
</template>
