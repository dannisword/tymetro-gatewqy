<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, h, watch, computed, shallowReactive } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import AppSidebar from "./AppSidebar.vue";
import AppTopbar from "./AppTopbar.vue";
import TagView from "./TagView.vue";
import LoadingOverlay from "../../components/LoadingOverlay.vue";
import AlertsContainer from "../../components/TLAlertsContainer.vue";

import { useSider } from "../../store/useSiderStore";
import { useTagsStore } from "../../store/useTagsStore";
import { useMtrStore } from "../../store/useMtrStore";

const tagsStore = useTagsStore();
const { tags } = storeToRefs(tagsStore);
const { attachAutoResize } = useSider();
const route = useRoute();
const mtrStore = useMtrStore();

const getCachedViews = computed(() => {
  // 只快取 keepAlive 為 true 的標籤
  return tags.value
    .filter(tag => tag.keepAlive !== false)
    .map((tag) => tag.path);
});

watch(
  () => route.fullPath,
  () => {
    tagsStore.addByRoute(route);
  },
  { immediate: true },
);
let detach: (() => void) | undefined;

onMounted(() => {
  detach = attachAutoResize();
  mtrStore.fetchSystemIp();
});

onBeforeUnmount(() => {
  detach && detach();
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

function reloadView() {
  viewKey.value++;
}
</script>
<template>
  <div class="flex h-screen bg-gray-50 text-gray-800">
    <div class="flex h-full w-full flex-1 overflow-hidden">
      <AppSidebar />

      <section class="flex min-w-0 flex-1 flex-col">
        <AppTopbar />

        <div class="bg-white border-b border-gray-100">
          <TagView @reload="reloadView" />
        </div>

        <main class="flex-1 overflow-auto">
          <div class="h-full relative">
            <router-view :key="viewKey" v-slot="{ Component, route }">
              <transition name="fade-transform">
                <keep-alive :include="getCachedViews">
                  <component
                    :is="formatComponentInstance(Component, route)"
                    :key="route.fullPath"
                  />
                </keep-alive>
              </transition>
            </router-view>
          </div>
        </main>
      </section>
    </div>

    <LoadingOverlay />
    <AlertsContainer ref="alertsRef" />
  </div>
</template>

<style scoped>
/* 使用最保險的動畫定義 */
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: opacity 0.1s linear !important;
}

.fade-transform-enter-from,
.fade-transform-leave-to {
  opacity: 0 !important;
}

/* 強制確保進入後是可見的 */
.fade-transform-enter-to,
.fade-transform-leave-from {
  opacity: 1 !important;
}
</style>
