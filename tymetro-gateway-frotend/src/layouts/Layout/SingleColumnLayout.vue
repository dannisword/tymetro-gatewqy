<script setup lang="ts">
import { computed, ref, watch, h, shallowReactive, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useTagsStore } from "../../store/useTagsStore";
import { useAppStore } from "../../store/useAppStore";
import { useMtrStore } from "../../store/useMtrStore";
import { mdiBellOutline, mdiTrainCar, mdiChevronDown } from "@mdi/js";
import BaseIcon from "../../components/BaseIcon.vue";
import UserDropdown from "./UserDropdown.vue";
import LoadingOverlay from "../../components/LoadingOverlay.vue";
import AlertsContainer from "../../components/TLAlertsContainer.vue";

const tagsStore = useTagsStore();
const { tags } = storeToRefs(tagsStore);
const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const mtrStore = useMtrStore();

onMounted(() => {
  mtrStore.fetchSystemIp();
});

const handleLogout = () => {
  appStore.logout();
  router.push('/login');
};

// 控制手機版選單開關
const mobileMenuOpen = ref(false);

// 導覽列選單資料 (JSON)
const navLinks = [
  { name: '首頁', path: '/mtr/train-list' },
  { name: '即時事件', path: '/mtr/events' },
  { name: '功能選單', path: '/mtr/tile-menus' }
];

watch(
  () => route.fullPath,
  () => {
    tagsStore.addByRoute(route);
  },
  { immediate: true },
);

const getCachedViews = computed(() => {
  return tags.value
    .filter((tag) => tag.keepAlive !== false)
    .map((tag) => tag.path);
});

const wrapperMap = new Map();
const wrapperVNodes = shallowReactive(new Map());

const formatComponentInstance = (ComponentVNode: any, route: any) => {
  if (!ComponentVNode) return null;
  
  const wrapperName = route.fullPath;
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

const viewKey = ref(0);
</script>

<template>
  <div class="flex flex-col h-screen w-screen overflow-hidden bg-slate-50 font-sans">
    
    <!-- Navbar / Header -->
    <header class="w-full bg-[#003775] text-white shadow-md z-50 shrink-0"> 
      <div class="w-full px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between max-w-[1920px] mx-auto">
        <!-- Left: Logo & Brand -->
        <div class="flex items-center gap-3 cursor-pointer select-none" @click="router.push('/')">

          <div class="flex flex-col">
            <span class="text-lg font-extrabold tracking-tight leading-none">桃園捷運監控系統</span>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-[11px] text-white/70 font-semibold tracking-wider">Metro Monitoring System</span>
              <span class="text-[10px] text-white/60 bg-white/10 px-1.5 py-0.5 rounded border border-white/10 font-mono font-bold">IP: {{ mtrStore.localIp }}</span>
            </div>
          </div>
        </div>

        <!-- Center: Navigation Links (Desktop) -->
        <nav class="hidden md:flex items-center gap-1 lg:gap-2 bg-white/10 p-1.5 rounded-xl border border-white/10 shadow-inner">
          <router-link 
            v-for="link in navLinks" 
            :key="link.path + link.name"
            :to="link.path" 
            class="px-4 py-1.5 text-md font-bold text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-all"
          >
            {{ link.name }}
          </router-link>
        </nav>

        <!-- Right: Actions & Mobile Menu Toggle -->
        <div class="flex items-center gap-2 sm:gap-3">
          <!-- 切換車廂下拉選單 (免登入即可看到) -->
          <!-- <div class="relative flex items-center bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg px-2.5 py-1.5 transition-all shadow-sm">
            <BaseIcon :path="mdiTrainCar" size="20" class="text-white mr-1.5" />
            <select 
              v-model="mtrStore.activeCarId" 
              class="bg-transparent text-white font-bold text-sm pr-2 focus:outline-none cursor-pointer appearance-none [&>option]:text-slate-800 [&>option]:bg-white"
            >
              <option v-for="car in mtrStore.carList" :key="car.id" :value="car.id">
                {{ car.name }}
              </option>
            </select>
            <BaseIcon :path="mdiChevronDown" size="18" class="text-white/80 pointer-events-none ml-0.5" />
          </div> -->

          <template v-if="appStore.isAuthenticated">
            <!-- 通知 -->
            <button class="hidden md:flex rounded-full p-2 text-white/90 hover:bg-white/10 items-center justify-center transition-colors">
                <BaseIcon :path="mdiBellOutline" w="32" h="32" size="20" class="text-white"/>
            </button>
            <div class="hidden md:block">
              <UserDropdown dark />
            </div>
          </template>
          <button v-else @click="router.push('/login')" class="hidden md:block px-5 py-1.5 bg-[#003775] hover:bg-[#00234a] rounded-md text-sm font-bold text-white border border-white/20 transition-all shadow-sm active:scale-95">
            登入
          </button>
          
          <!-- Mobile Menu Button -->
          <button @click="mobileMenuOpen = !mobileMenuOpen" class="md:hidden p-2 text-white hover:bg-[#003775] rounded-lg transition-colors focus:outline-none">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path v-if="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- Mobile Nav Dropdown -->
      <transition 
        enter-active-class="transition duration-200 ease-out" 
        enter-from-class="transform -translate-y-2 opacity-0" 
        enter-to-class="transform translate-y-0 opacity-100" 
        leave-active-class="transition duration-150 ease-in" 
        leave-from-class="transform translate-y-0 opacity-100" 
        leave-to-class="transform -translate-y-2 opacity-0"
      >
        <div v-show="mobileMenuOpen" class="md:hidden bg-[#003775]/95 backdrop-blur shadow-lg border-t border-white/20 absolute w-full px-4 py-4 space-y-3 z-40">
          <router-link 
            v-for="link in navLinks" 
            :key="link.path + link.name"
            @click="mobileMenuOpen = false" 
            :to="link.path" 
            class="block text-base font-bold text-white/90 hover:text-white p-3 rounded-lg hover:bg-[#003775] transition-colors"
          >
            {{ link.name }}
          </router-link>
          <div class="pt-3 border-t border-white/10 mt-2">
            <template v-if="appStore.isAuthenticated">
              <div class="text-center text-sm font-bold text-white/90 mb-3">
                目前登入：{{ appStore.user?.account || appStore.user?.name || appStore.user?.userName || '管理員' }}
              </div>
              <button @click="handleLogout" class="w-full text-center px-4 py-3 bg-[#00234a] hover:bg-[#00234a] rounded-lg text-base font-bold text-white shadow-inner transition-colors">
                登出
              </button>
            </template>
            <template v-else>
              <button @click="router.push('/login')" class="w-full text-center px-4 py-3 bg-[#00234a] hover:bg-[#00234a] rounded-lg text-base font-bold text-white shadow-inner transition-colors">
                登入
              </button>
            </template>
          </div>
        </div>
      </transition>
    </header>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-x-hidden overflow-y-auto bg-white relative w-full">
      <div class="min-h-full relative px-4 py-2 md:px-6 max-w-7xl mx-auto w-full">
        <router-view :key="viewKey" v-slot="{ Component, route }">
            <keep-alive :include="getCachedViews">
              <component
                :is="Component"
                :key="route.fullPath"
              />
            </keep-alive>
        </router-view>
      </div>
    </main>

    <LoadingOverlay />
    <AlertsContainer ref="alertsRef" />
  </div>
</template>

<style scoped>
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: opacity 0.1s linear !important;
}

.fade-transform-enter-from,
.fade-transform-leave-to {
  opacity: 0 !important;
}

.fade-transform-enter-to,
.fade-transform-leave-from {
  opacity: 1 !important;
}
</style>
