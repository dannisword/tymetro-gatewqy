<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { routeHandle } from "../../hooks/route-handle";
import SidebarMenu from "./SidebarMenu.vue";
import { useRouter, useRoute } from "vue-router";

const { navigation } = routeHandle();
const router = useRouter();
const props = defineProps({
  isOpen: Boolean,
  items: { type: Array, default: () => [] },
  isCollapsed: { type: Boolean, default: false },
});
const emit = defineEmits(["toggle"]);
const current = ref("Dashboard");
const onUpdate = (item: any) => {
  // navigation(item.url);
  //     const path = `${url}`;
  router.push({ path: item.url });

  current.value = item.label;
};
</script>

<template>
  <div class="fixed top-0 left-0 z-50 w-64 h-full bg-card flex flex-col transition-all duration-300"
    :class="isOpen ? 'translate-x-0' : '-translate-x-full'">
    <!-- hedaer-->
    <div class="flex items-center justify-between p-3 bg-theme text-white">
      <span class="font-bold">TyMetro</span>
      <button @click="$emit('toggle')" class="material-symbols-outlined">close</button>
    </div>

    <SidebarMenu :items="items" :current="current" :isCollapsed="isCollapsed" @update="onUpdate" />
    <div class="border-t border-gray-300 px-2 py-2">
      <a href="#" class="flex items-center px-2 py-2 text-sm hover:bg-theme hover:text-white rounded-md">
        <span class="material-symbols-outlined mr-2">settings</span> Settings
      </a>
    </div>
  </div>
</template>
