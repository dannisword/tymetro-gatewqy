<template>
  <div class="flex space-x-2">
    <template v-for="(btn, index) in props.params.actions" :key="index">
      <el-button
        size="small"
        :type="btn.type || 'primary'"
        :icon="btn.icon"
        @click="() => btn.onClick(params.data)"
      >
        {{ btn.label }}
      </el-button>
    </template>
  </div>
</template>
<script setup lang="ts">
import { PropType } from "vue";
const props = defineProps({
  params: {} as PropType<any>,
});
</script>
