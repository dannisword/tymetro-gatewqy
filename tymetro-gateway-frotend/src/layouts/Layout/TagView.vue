<!-- TagView.vue -->
<script setup lang="ts">
import { onMounted, ref, watch, onUnmounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { storeToRefs } from "pinia";
import { useTagsStore } from "../../store/useTagsStore";
import BaseIcon from "../../components/BaseIcon.vue";
import {
  mdiReload,
  mdiClose,
  mdiCloseCircleMultiple,
  mdiFilterVariantRemove,
  mdiChevronDown,
  mdiChevronLeft,
  mdiChevronRight,
} from "@mdi/js";

const route = useRoute();
const router = useRouter();
const tagsStore = useTagsStore();
const { tags, activePath } = storeToRefs(tagsStore);

const emit = defineEmits<{ (e: "reload"): void }>();

onMounted(() => tagsStore.addByRoute(route));
watch(
  () => route.fullPath,
  () => tagsStore.addByRoute(route),
);

const menuVisible = ref(false);
const menuPosition = ref({ x: 0, y: 0 });
const selectedPath = ref("");

onMounted(() => {
  document.addEventListener("click", closeMenu);
  document.addEventListener("contextmenu", closeMenuOutside);
});
onUnmounted(() => {
  document.removeEventListener("click", closeMenu);
  document.removeEventListener("contextmenu", closeMenuOutside);
});

const onContextMenu = (path: string, e: MouseEvent) => {
  menuVisible.value = true;
  menuPosition.value = { x: e.clientX, y: e.clientY };
  selectedPath.value = path;
};

const closeMenu = () => {
  menuVisible.value = false;
};

const closeMenuOutside = (e: MouseEvent) => {
  // If we're not clicking on a tag, close the menu
  const target = e.target as HTMLElement;
  if (!target.closest(".tag-item")) {
    closeMenu();
  }
};
const scroller = ref<HTMLDivElement | null>(null);

const scrollLeft = () =>
  scroller.value?.scrollBy({ left: -160, behavior: "smooth" });

const scrollRight = () =>
  scroller.value?.scrollBy({ left: 160, behavior: "smooth" });

const go = (path: string) => {
  closeMenu();

  if (activePath.value === path) {
    doReload();
  } else {
    router.push(path);
  }
};

const closeTag = (path: string) => {
  const isAct = activePath.value === path;
  tagsStore.remove(path);
  if (isAct) router.push(tagsStore.activePath);
};
const doReload = () => {
  if (activePath.value !== selectedPath.value) {
    router.push(selectedPath.value);
  }
  emit("reload");
  closeMenu();
};
const doCloseLeft = () => {
  tagsStore.closeLeft(selectedPath.value);
  router.push(tagsStore.activePath);
  closeMenu();
};
const doCloseRight = () => {
  tagsStore.closeRight(selectedPath.value);
  router.push(tagsStore.activePath);
  closeMenu();
};
const doCloseOthers = () => {
  tagsStore.closeOthers(selectedPath.value);
  router.push(tagsStore.activePath);
  closeMenu();
};
const doCloseAll = () => {
  tagsStore.closeAll();
  router.push(tagsStore.activePath);
  closeMenu();
};
const componentClass = computed(() => {
  return `flex items-center gap-2 border-b border-slate-200 bg-white px-2 py-1.5`;
});
const menuClass = computed(() => {
  return "fixed z-[1000] w-56 rounded-lg border border-slate-200 bg-white shadow-xl";
});
const menuItemClass = computed(() => {
  return `flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted-100`;
});
const closeItemClass = computed(() => {
  return `flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50`;
});
</script>

<template>
  <div :class="componentClass">
    <!-- 箭頭控制與捲動區 -->
    <button class="rounded p-1 hover:bg-muted-100" @click.stop="scrollLeft">
      <BaseIcon :path="mdiChevronLeft" />
    </button>

    <div ref="scroller" class="no-scrollbar flex-1 overflow-x-auto">
      <div class="flex items-center gap-1">
        <div
          v-for="t in tags"
          :key="t.path"
          class="tag-item group flex items-center border px-3 py-1.5 text-sm whitespace-nowrap cursor-pointer"
          :class="[
            activePath === t.path
              ? 'border-primary-100 bg-primary-600 text-white'
              : 'border-muted-300 bg-white text-muted-900 hover:bg-muted-100',
          ]"
          @click.stop="go(t.path)"
          @contextmenu.prevent="onContextMenu(t.path, $event)"
        >
          <span class="truncate max-w-[180px] text-sm">{{ t.title }}</span>
          <button
            v-if="t.closable !== false"
            class="ml-2 flex items-center justify-center opacity-60 hover:opacity-100"
            @click.stop="closeTag(t.path)"
            title="關閉"
          >
            <BaseIcon :path="mdiClose" :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- 右邊箭頭 -->
    <button class="rounded p-1 hover:bg-muted-100" @click.stop="scrollRight">
      <BaseIcon :path="mdiChevronRight" />
    </button>

    <!-- Context Menu (Teleport to body recommended for fixed positioning) -->
    <Teleport to="body">
      <div
        v-if="menuVisible"
        :class="menuClass"
        :style="{
          top: `${menuPosition.y}px`,
          left: `${menuPosition.x}px`,
        }"
      >
        <div class="flex flex-col py-1">
          <button :class="menuItemClass" @click="doReload">
            <BaseIcon :path="mdiReload" size="18" />
            <span>重新載入</span>
          </button>

          <div class="my-1 h-px bg-muted-100"></div>
          <button :class="menuItemClass" @click="doCloseLeft">
            <BaseIcon :path="mdiChevronLeft" size="18" /><span
              >關閉左側標籤頁</span
            >
          </button>
          <button :class="menuItemClass" @click="doCloseRight">
            <BaseIcon :path="mdiChevronRight" size="18" /><span
              >關閉右側標籤頁</span
            >
          </button>
          <button :class="menuItemClass" @click="doCloseOthers">
            <BaseIcon :path="mdiFilterVariantRemove" size="18" /><span
              >關閉其它標籤頁</span
            >
          </button>
          <button :class="closeItemClass" @click="doCloseAll">
            <BaseIcon :path="mdiCloseCircleMultiple" size="18" />
            <span>關閉全部標籤頁</span>
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
