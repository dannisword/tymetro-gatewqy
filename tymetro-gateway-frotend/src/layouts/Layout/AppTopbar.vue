<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useSider } from "../../store/useSiderStore";
import {
  mdiMagnify,
  mdiMenu,
  mdiPinOutline,
  mdiPinOffOutline,
  mdiBellOutline,
} from "@mdi/js";
import BaseIcon from "../../components/BaseIcon.vue";
import UserDropdown from "./UserDropdown.vue";

import { useMtrStore } from "../../store/useMtrStore";

const route = useRoute();
const { state, toggle } = useSider();
const mtrStore = useMtrStore();
const componentClass = computed(() => {
  return `flex items-center justify-between border-b border-slate-200 px-1 py-0`;
});
</script>

<template>
    <header :class="componentClass">
        <!-- 左邊：sider 控制 -->
        <div class="flex items-center gap-2">
            <!-- 展開/收合 -->
            <button class="rounded-lg p-2 hover:bg-muted-100" @click="toggle()">
                <BaseIcon :path="mdiMenu" w="32" h="32" size="22" />
            </button>
        </div>

        <!-- 右邊：使用者 -->
        <div class="flex items-center gap-2 mr-2">
            <!-- IP Address -->
            <span class="text-[11px] font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-md border border-slate-200/60 font-mono mr-1 select-none">
              IP: {{ mtrStore.localIp }}
            </span>
            <!-- 通知 -->
            <button class="rounded-lg p-2 text-slate-600 hover:bg-muted-100 flex items-center justify-center">
                <BaseIcon :path="mdiBellOutline" w="32" h="32" size="20" class="text-slate-600"/>
            </button>
            <UserDropdown />
        </div>
    </header>
</template>
