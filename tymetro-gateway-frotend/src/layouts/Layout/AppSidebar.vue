<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRoute, RouterLink } from "vue-router";
import { useAppStore } from "@/store/useAppStore";
import { useSider } from "@/store/useSiderStore";
import { useAuthStore } from "@/store/useAuthStore";
import { storeToRefs } from "pinia";

import { mdiChevronDown, mdiFileDocumentOutline } from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";

const { collapsed } = useSider();
const store = useAppStore();
const authStore = useAuthStore();
const { menus } = storeToRefs(store);
const { accessToken } = storeToRefs(authStore);
const route = useRoute();

interface MenuItem {
  id: any;
  to?: string;
  label: string;
  icon: string;
  children?: MenuItem[];
}

// 改用 computed 確保 Store 更新時這裡會同步
const menuItems = computed<MenuItem[]>(() => (menus.value as any[]) || []);

const bottom: MenuItem[] = [
  {
    id: 9000,
    to: "/document-templates",
    label: "樣板管理",
    icon: mdiFileDocumentOutline,
  },
];

const openKeys = ref<string[]>([]);
const hoverKey = ref<string | null>(null);

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});
onBeforeUnmount(() => {
  document.removeEventListener("click", handleClickOutside);
});

const toggleOpen = (label: string) => {
  if (openKeys.value.includes(label)) {
    openKeys.value = openKeys.value.filter((k) => k !== label);
  } else {
    openKeys.value.push(label);
  }
};

function isActive(path?: string) {
  return !!path && route.path.startsWith(path);
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement;
  if (!target.closest(".sidebar-popover")) {
    hoverKey.value = null;
  }
}

// 側邊欄容器
const siderClass = computed(() =>
  collapsed.value
    ? "flex flex-col border-r border-gray-200 p-2 w-20 transition-all duration-300 relative bg-white"
    : "flex flex-col border-r border-gray-200 p-4 w-64 transition-all duration-300 relative bg-white",
);


// 父層 menu
const menuClass = computed(() => (menu: MenuItem) => [
  "flex items-center transition-all duration-200 p-2 w-full group relative overflow-hidden",
  collapsed.value ? "justify-center" : "gap-3",
  isActive(menu.to)
    ? "bg-blue-50 text-muted-700 font-semibold"
    : "text-muted-600 hover:text-muted-900 hover:bg-slate-100",
]);

// 子層 child
const childClass = computed(() => (child: MenuItem) => [
  "relative flex items-center gap-3 pr-3 pl-5 py-2 transition-all duration-200 w-full group",
  isActive(child.to)
    ? "text-muted-700 bg-blue-50 font-semibold"
    : "text-muted-600 hover:text-muted-900 hover:bg-slate-100",
]);
// 浮動彈出層 child
const childSmallClass = computed(() => (child: MenuItem) => [
  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
  isActive(child.to)
    ? "bg-blue-50 text-muted-700 font-semibold"
    : "text-muted-600 hover:text-muted-900 hover:bg-slate-100 ",
]);

// 單層/底部
const menuLargeClass = computed(() => (menu: MenuItem) => [
  "flex items-center transition-all duration-200 p-2 w-full group relative overflow-hidden",
  collapsed.value ? "justify-center" : "gap-3",
  isActive(menu.to)
    ? "bg-blue-50 text-muted-700 font-semibold"
    : "text-muted-600 hover:text-muted-900 hover:bg-slate-100 ",
]);

const copyToClipboard = async () => {
  try {
    if (accessToken.value) {
      await navigator.clipboard.writeText(accessToken.value);
    }
  } catch (err) {}
};
</script>

<template>
  <aside :class="siderClass">
    <div class="flex items-center py-3 mb-2"
       :class="collapsed ? 'justify-center' : 'gap-3 px-2'">

      <img src="../../assets/logo.webp"
        class="h-10 w-10 cursor-pointer transition-transform hover:scale-105"
        @click="copyToClipboard" />
      <strong v-if="!collapsed" class="text-muted-600 text-xl tracking-wider truncate">
        桃園捷運
      </strong>
    </div>

    <nav class="flex flex-col">
      <template v-for="menu in menuItems" :key="menu.id">
        <div class="relative">
          <div
            v-if="isActive(menu.to) && !collapsed && (!menu.children || menu.children.length === 0)"
            class="absolute left-0 top-0 bottom-0 w-1 bg-blue-600 rounded-r-full z-10"
          ></div>

          <button
            v-if="menu.children && menu.children.length > 0"
            @click="!collapsed && toggleOpen(menu.label)"
            @mouseenter="collapsed && (hoverKey = menu.label)"
            :class="menuClass(menu)"
          >
            <BaseIcon
              :path="menu.icon"
              :class="
                isActive(menu.to)
                  ? 'text-muted-600'
                  : 'text-muted-400 group-hover:text-muted-600'
              "
              w="18"
              h="18"
              size="18"
            />
            <span v-if="!collapsed" class="flex-1 text-left">{{
              menu.label
            }}</span>
            <BaseIcon
              v-if="!collapsed"
              :path="mdiChevronDown"
              class="transition-transform duration-300"
              :class="[
                openKeys.includes(menu.label) ? 'rotate-180' : '',
                isActive(menu.to) ? 'text-muted-600' : 'text-muted-300',
              ]"
              w="16"
              h="16"
              size="16"
            />
          </button>

          <div v-if="menu.children && menu.children.length > 0 && openKeys.includes(menu.label) && !collapsed"
            class="ml-4 mt-1 flex flex-col gap-1 border-l-2 border-slate-100">
            <RouterLink v-for="child in menu.children" :key="child.to" :to="child.to!" :class="childClass(child)">
              <div v-if="isActive(child.to) && !collapsed"
                class="absolute left-0 top-0 bottom-0 w-1 bg-blue-600 rounded-r-full z-10"></div>

              <BaseIcon :path="child.icon" :class="isActive(child.to)
                  ? 'text-muted-900'
                  : 'text-muted-500 group-hover:text-muted-600'
                " w="16" h="16" size="16" />
              <span class="flex-1 text-left">{{ child.label }}</span>
            </RouterLink>
          </div>

          <div
            v-if="menu.children && menu.children.length > 0 && collapsed && hoverKey === menu.label"
            class="sidebar-popover absolute left-full top-0 ml-3 z-50 min-w-[200px] rounded-xl shadow-2xl border border-slate-100 bg-white p-2"
            @mouseleave="hoverKey = null"
          >
            <div
              class="px-3 py-2 text-muted-800 uppercase tracking-widest border-b border-slate-50 mb-1"
            >
              {{ menu.label }}
            </div>
            <div class="flex flex-col gap-1">
              <RouterLink
                v-for="child in menu.children"
                :key="child.to"
                :to="child.to!"
                :class="childSmallClass(child)"
                @click="hoverKey = null"
              >
                <BaseIcon :path="child.icon" w="16" h="16" size="16" />
                <span>{{ child.label }}</span>
              </RouterLink>
            </div>
          </div>

          <!-- 沒有子選單 -->
          <RouterLink
            v-if="!menu.children || menu.children.length === 0"
            :to="menu.to!"
            :class="menuLargeClass(menu)"
          >
            <BaseIcon
              :path="menu.icon"
              :class="
                isActive(menu.to)
                  ? 'text-muted-600'
                  : 'text-muted-500 group-hover:text-muted-600'
              "
              w="18"
              h="18"
              size="18"
            />
            <span v-if="!collapsed">{{ menu.label }}</span>
          </RouterLink>
        </div>
      </template>
    </nav>
    <!-- 最下面選單-->
    <div class="mt-auto border-t border-slate-300 flex flex-col">
      <RouterLink
        v-for="b in bottom"
        :key="b.label"
        :to="b.to!"
        :class="menuLargeClass(b)"
      >
        <BaseIcon
          :path="b.icon"
          :class="
            isActive(b.to)
              ? 'text-muted-500'
              : 'text-muted-500 group-hover:text-muted-600'
          "
          w="18"
          h="18"
          size="18"
        />
        <span v-if="!collapsed">{{ b.label }}</span>
      </RouterLink>
    </div>
  </aside>
</template>

<style scoped>
/* 讓側邊欄切換更加滑順 */
aside {
  will-change: width;
}

/* 自定義捲軸樣式 (如果選單過長) */
nav::-webkit-scrollbar {
  width: 4px;
}
nav::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 10px;
}
</style>
