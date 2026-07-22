<script setup lang="ts">
import Layout from './Layout.vue';
import SingleColumnLayout from './SingleColumnLayout.vue';

// 判斷是否為單欄模式 (沒有側邊欄與頂部導覽列)
const isOneColumn = import.meta.env.VITE_LAYOUT_MODE === '1-column-layout';

</script>

<template>
  <SingleColumnLayout v-if="isOneColumn" />
  <Layout v-else />
</template>
