<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import * as mdiIcons from "@mdi/js";
import BaseIcon from "../../components/BaseIcon.vue";
import { routeHandle } from "../../hooks/route-handle";
import { useAppStore } from "../../store/useAppStore";
import { useMtrStore } from "../../store/useMtrStore";

const { navigation } = routeHandle();
const mtrStore = useMtrStore();

const props = defineProps<{
  dark?: boolean;
}>();

const open = ref(false);
const dropdownRef = ref<HTMLElement | null>(null);

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() =>
  document.removeEventListener("click", handleClickOutside)
);

const toggle = () => {
  open.value = !open.value;
};
const close = () => {
  open.value = false;
};

const handleClickOutside = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (dropdownRef.value && !dropdownRef.value.contains(target)) {
    close();
  }
};
const onLogout = () => {
  close();
  useAppStore().logout();
  navigation("/dashboard");
};

const getIcon = (iconName?: string) => {
  if (!iconName) return "";
  return (mdiIcons as Record<string, string>)[iconName] || "";
};

const dropdownClass = computed(() => {
  return `absolute right-0 mt-2 w-48 rounded-lg border border-slate-200 bg-white shadow-lg z-50`;
});

const itemClass = computed(() => {
  return `flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100`;
});
const specItemClass = computed(() => {
  return `flex items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 w-full text-left`;
});

const iconClass = computed(() => {
  return `text-muted-400 hover:font-semibold`;
});

const buttonClass = computed(() => {
  return [
    'flex h-fit items-center gap-2 rounded-full p-2 focus:outline-none transition-colors',
    props.dark ? 'hover:bg-white/10' : 'hover:bg-slate-50'
  ].join(' ');
});

const iconTextColor = computed(() => props.dark ? 'text-white' : 'text-slate-600');
const textColor = computed(() => props.dark ? 'text-white' : 'text-slate-700');
</script>

<template>
  <div class="relative" ref="dropdownRef">
    <!-- avatar 按鈕 -->
    <button @click.stop="toggle" :class="buttonClass">
      <BaseIcon :path="mdiIcons.mdiAccountCircleOutline" w="32" h="32" size="22" :class="iconTextColor" />
      <strong class="pointer-events-none" :class="textColor">
        {{ useAppStore().user.userName || useAppStore().user.account || useAppStore().user.name || '管理員' }}
      </strong>
    </button>

    <!-- dropdown -->
    <div v-if="open" :class="dropdownClass">
      <div class="flex flex-col py-1">
        <template v-for="(item, idx) in mtrStore.userDropdown" :key="idx">
          <div v-if="item.divider" class="border-t border-slate-200 my-1"></div>
          <button
            v-else-if="item.action === 'logout'"
            @click="onLogout"
            :class="specItemClass"
          >
            <BaseIcon :path="getIcon(item.icon)" w="32" h="32" size="22" :class="iconClass" />
            <span>{{ item.label }}</span>
          </button>
          <button
            v-else
            @click="close(); navigation(item.to)"
            :class="specItemClass"
          >
            <BaseIcon :path="getIcon(item.icon)" w="32" h="32" size="22" :class="iconClass" />
            <span>{{ item.label }}</span>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
