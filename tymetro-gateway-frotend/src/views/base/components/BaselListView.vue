<script setup lang="ts">
import { 
  mdiStarOutline, 
  mdiLabelVariantOutline, 
  mdiMagnify
} from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";

import { usePermissionStore } from "@/store/usePermissionStore";

interface ListItem {
  id: number;
  [key: string]: any;
  title?: string;
  body?: string;
  date?: string;
}

const props = defineProps<{
  listData: ListItem[];
  loading: boolean;
  selectedIds: Set<number>;
  rowHeight?: string;
}>();

const emit = defineEmits<{
  (e: 'toggleSelection', id: number): void;
  (e: 'action', action: string, item: any): void;
}>();



const permissionStore = usePermissionStore();
const isSelected = (id: number) => props.selectedIds.has(id);
const hasPermission = (permission: string) => permissionStore.hasPermission(permission);
</script>

<template>
  <div class="gmail-list-view flex-1 overflow-y-auto custom-scrollbar bg-white">
    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
    </div>

    <!-- List Items -->
    <div 
      v-for="(item, index) in listData" 
      :key="item.id" 
      class="gmail-list-item flex items-center px-4 py-1.5 cursor-pointer group border-b border-slate-100"
      :class="{'selected': isSelected(item.id)}"
      :style="{ height: rowHeight || '48px' }"
      @click="emit('toggleSelection', item.id)"
    >
      <!-- Left Icons (Standard Gmail Controls) -->
      <div class="flex items-center gap-3 shrink-0 mr-4">
        <div class="w-5 h-5 flex items-center justify-center rounded hover:bg-slate-200" @click.stop>
          <input 
            type="checkbox" 
            :checked="isSelected(item.id)" 
            class="w-3.5 h-3.5 rounded-sm border-slate-400 accent-primary cursor-pointer" 
            @change="emit('toggleSelection', item.id)"
          />
        </div>
        <button class="text-slate-300 hover:text-yellow-400 transition-colors" @click.stop>
          <BaseIcon :path="mdiStarOutline" size="20" />
        </button>
        <button class="text-slate-300 hover:text-slate-500 transition-colors" @click.stop>
          <BaseIcon :path="mdiLabelVariantOutline" size="18" />
        </button>
      </div>

      <!-- Sender / Title Section -->
      <div class="w-40 shrink-0 font-bold text-[14px] text-slate-800 truncate">
        <slot name="sender" :item="item" :hasPermission="hasPermission"></slot>
      </div>

      <!-- Content / Subject Section -->
      <div class="flex-1 min-w-0 text-[14px] flex items-center gap-2 truncate pr-4">
        <span class="font-bold text-slate-700 shrink-0">
          <slot name="subject" :item="item" :hasPermission="hasPermission"></slot>
        </span>
        <span class="text-slate-500 truncate">
          <slot name="snippet" :item="item" :hasPermission="hasPermission"></slot>
        </span>
      </div>

      <!-- Right Side: Date or Actions -->
      <div class="w-40 shrink-0 flex justify-end items-center relative h-full">
        <!-- Static Info (Date/Status) -->
        <div class="text-[12px] font-bold text-slate-500 group-hover:hidden whitespace-nowrap">
          <slot name="date" :item="item" :hasPermission="hasPermission"></slot>
        </div>
        
        <!-- Hover Actions -->
        <div class="hidden group-hover:flex items-center gap-0.5 bg-inherit">
           <slot name="actions" :item="item" :hasPermission="hasPermission"></slot>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="listData.length === 0 && !loading" class="flex flex-col items-center justify-center py-20 text-slate-400">
      <BaseIcon :path="mdiMagnify" size="64" class="opacity-10 mb-4" />
      <p class="font-black uppercase tracking-widest text-xs">目前沒有任何紀錄</p>
    </div>
  </div>
</template>

<style scoped>
.gmail-list-item {
  transition: background-color 0.05s linear;
  background-color: white;
  border-bottom: 1px solid #f1f5f9;
}
.gmail-list-item:hover {
  background-color: #f2f6fc;
  box-shadow: inset 3px 0 0 #3b82f6, 0 1px 3px rgba(60, 64, 67, 0.1);
  z-index: 10;
}
.gmail-list-item.selected {
  background-color: #c2e7ff;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 10px;
}
</style>
