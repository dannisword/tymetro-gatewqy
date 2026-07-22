<script setup lang="ts">
import {
  ref,
  onMounted,
  onBeforeUnmount,
  h,
  ComponentPublicInstance,
  watch,
  shallowReactive,
} from "vue";
import { useRoute } from "vue-router";
import { useBasicStore } from "@/store/useBasicStore";
import Sidebar from "./Sidebar.vue";
import AlertsContainer from "../../components/TLAlertsContainer.vue";
import { useTheme } from '../../composables/UseTheme';

import TagsView from "./TagsView.vue";

const route = useRoute();
const { cachedViews, getCachedViews, addVisitedView } = useBasicStore();
const isSidebarOpen = ref(false);
const isDropdownOpen = ref(false);
const { isDark, toggleTheme, initTheme } = useTheme();
const alertsRef = ref<ComponentPublicInstance<{
  addAlert: (type: any, message: any) => void;
}> | null>(null);

const wrapperMap = new Map();
const wrapperVNodes = shallowReactive(new Map());

watch(
  () => route.name,
  (val) => {
    const routerLevel = route.matched.length;
    addVisitedView(route);
  },

  { immediate: true }
);

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside);
});
const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const formatComponentInstance = (ComponentVNode: any, route: any) => {
  if (!ComponentVNode) return null;
  
  const wrapperName = route.path;
  wrapperVNodes.set(wrapperName, ComponentVNode);
  
  if (wrapperMap.has(wrapperName)) {
    return wrapperMap.get(wrapperName);
  }
  
  const wrapper = {
    name: wrapperName,
    render() {
      const vnode = wrapperVNodes.get(wrapperName);
      if (vnode) {
        return h(vnode.type, vnode.props, vnode.children);
      }
      return null;
    },
  };
  
  wrapperMap.set(wrapperName, wrapper);
  return wrapper;
};
// 點擊外部區域自動關閉選單
function handleClickOutside(e: any) {
  if (!e.target.closest(".relative")) {
    isDropdownOpen.value = false;
  }
}

// 可在任何地方呼叫這個方法
const showAlert = (type: any, message: any) => {
  if (alertsRef.value) {
    alertsRef.value.addAlert(type, message);
  }
};

defineExpose({ showAlert });

const menuItems = [
  { icon: "home", label: "Dashboard", url: "/dashboard" },
  { icon: "group", label: "Team", url: "/privage-records" },
  { icon: "folder", label: "Document", url: "/document-templates" },
  { icon: "event", label: "Calendar", url: "" },
  { icon: "description", label: "Documents", url: "" },
  { icon: "bar_chart", label: "Reports", url: "" },
];
const teams = [
  { initial: "H", name: "Favorite" },
  { initial: "T", name: "Tailwind Labs" },
  { initial: "W", name: "Workcation" },
];
</script>

<template>
    <div class="flex h-screen">
        <div v-if="isSidebarOpen" class="fixed inset-0 bg-black bg-opacity-50 z-20"
            @click="isSidebarOpen = !isSidebarOpen"></div>

        <Sidebar :isOpen="isSidebarOpen" :items="menuItems" :teams="teams" @toggle="toggleSidebar" />

        <div class="flex-1">
            <header class="flex items-center h-12 px-3 bg-theme text-white justify-between border-gray-100">
                <!-- 左側區塊 -->
                <div class="flex items-center space-x-4">
                    <button @click="toggleSidebar()" class="material-symbols-outlined cursor-pointer">
                        menu
                    </button>
                    <span class="font-bold text-lg">倉儲管理</span>
                </div>
                <!-- 右側區塊 -->
                <div class="flex items-center space-x-4">
                    <button class="mx-2">
                        <span class="material-symbols-outlined">notifications</span>
                    </button>
                    <!-- 使用者頭像 + 下拉選單 -->
                    <div class="relative">
                        <div class="flex items-center z-50 cursor-pointer" @click="isDropdownOpen = !isDropdownOpen">
                            <img src="https://i.pravatar.cc/40" class="w-8 h-8 rounded-full cursor-pointer" />
                            <span class="px-2">Admin</span>
                        </div>

                        <transition name="fade">
                            <div v-if="isDropdownOpen"
                                class="absolute right-0 mt-2 w-40 border-border bg-card text-fg rounded shadow-lg p-2 z-50">
                                <a href="#" class="flex items-center px-4 py-2 hover:bg-muted">
                                    <span class="material-symbols-outlined text-gray-500">
                                        person
                                    </span>
                                    <span class="px-2">個人</span>
                                </a>
                                <a href="#" class="flex items-center px-4 py-2 hover:bg-muted">
                                    <span class="material-symbols-outlined text-gray-500">
                                        settings
                                    </span>
                                    <span class="px-2">設定</span>
                                </a>
                                <a href="/login" class="flex items-center px-4 py-2 hover:bg-muted border-t">
                                    <span class="material-symbols-outlined text-gray-500">
                                        logout
                                    </span>
                                    <span class="px-2">登出</span>
                                </a>
                                <!-- 亮/暗切換 -->
                                <button class="flex items-center w-full px-4 py-2 text-left hover:bg-muted"
                                    @click="toggleTheme()">
                                    <span v-if="isDark" class="material-symbols-outlined text-yellow-500">
                                        sunny
                                    </span>
                                    <span v-else class="material-symbols-outlined text-gray-500">
                                        dark_mode
                                    </span>
                                    <span class="px-2">{{ isDark ? "亮色" : "暗色" }}</span>
                                </button>
                            </div>
                        </transition>
                    </div>
                </div>
            </header>
            <TagsView />
            <main class="px-4 py-2">
                <router-view v-slot="{ Component, route }">
                    <keep-alive :include="getCachedViews">
                        <component :is="formatComponentInstance(Component, route)" :key="route.fullPath" />
                    </keep-alive>
                </router-view>
            </main>
            <AlertsContainer ref="alertsRef" />
        </div>
    </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined');
</style>
