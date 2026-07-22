<script setup lang="ts">
import { computed } from "vue";

type PageChange = {
  page: number; // 0-based
  pageSize: number;
};

const { t } = useI18n();
const props = defineProps<{
  page: number;      // 0-based index
  pageSize: number;
  totalPages: number; // 總頁數 (1-based count, 例如共 10 頁)
  totalRows?: number; 
  pageSizes?: number[];
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: "change", payload: PageChange): void;
  (e: "refresh"): void;
}>();

const sizes = computed(() => props.pageSizes ?? [10, 20, 50, 100]);

// 計算最後一頁的索引，確保不小於 0
const lastPageIndex = computed(() => Math.max(0, props.totalPages - 1));

function go(to: "first" | "prev" | "next" | "last") {
  if (props.disabled) return;
  console.log(to);
  
  let p = props.page;

  if (to === "first") p = 0;
  if (to === "prev") p = Math.max(0, props.page - 1);
  if (to === "next") p = Math.min(lastPageIndex.value, props.page + 1);
  if (to === "last") p = lastPageIndex.value;

  if (p !== props.page) {
    emit("change", { page: p, pageSize: props.pageSize });
  }
}

function onJump(e: Event) {
  const input = e.target as HTMLInputElement;
  const raw = Math.trunc(Number(input.value));

  if (!isNaN(raw)) {
    // 限制輸入範圍在 1 ~ totalPages 之間
    const targetPage = Math.min(props.totalPages, Math.max(1, raw));
    const p = targetPage - 1; // 轉回 0-based

    if (p !== props.page && p >= 0) {
      emit("change", { page: p, pageSize: props.pageSize });
    } else {
      // 若無效或沒變，強制還原輸入框顯示的數字
      input.value = String(props.page + 1);
    }
  }
}

function onSize(e: Event) {
  const size = Number((e.target as HTMLSelectElement).value);
  emit("change", { page: 0, pageSize: size });
}
</script>

<template>
  <div class="ag-pager">
    <div class="left">
      <button :disabled="disabled || page === 0" @click="go('first')">«</button>
      <button :disabled="disabled || page === 0" @click="go('prev')">‹</button>

      <span class="page">
        {{ t("第") }}
        <input
          class="bg-gray-50 border border-gray-300 rounded-md text-center"
          type="number"
          :value="page + 1"
          min="1"
          :max="Math.max(1, totalPages)"
          @change="onJump"
        />
        / {{ Math.max(1, totalPages) }}
      </span>

      <button
        :disabled="disabled || page >= totalPages - 1"
        @click="go('next')"
      >
        ›
      </button>
      <button
        :disabled="disabled || page >= totalPages - 1"
        @click="go('last')"
        
      >
        »
      </button>

      <span class="rows" v-if="typeof totalRows === 'number'">
        ｜ {{ t("共") }} {{ totalRows.toLocaleString() }}
      </span>
    </div>

    <div class="right">
      <label>
        <select
          :value="pageSize"
          @change="onSize"
          class="bg-gray-50 border border-gray-300 rounded-md text-center"
        >
          <option v-for="size in sizes" :key="size" :value="size">
            {{ size }}
          </option>
        </select>
        {{ t("筆/頁") }}
      </label>
      <!-- <button :disabled="disabled" @click="$emit('refresh')">重新整理</button> -->
    </div>
  </div>
</template>

<style scoped>
.ag-pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #e5e7eb;
  background: #fafafa;
  font-size: 14px;
}
.left,
.right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
button {
  padding: 0.25rem 0.5rem;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 0.375rem;
  cursor: pointer;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
input[type="number"] {
  width: 4rem;
  padding: 0.25rem 0.4rem;
}
select {
  padding: 0.25rem 0.4rem;
}
</style>
