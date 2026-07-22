<script setup lang="ts">
import { computed, ref, watchEffect } from "vue"
import type { TreeNode } from "./TreeList.vue"

type Id = string | number

const props = defineProps<{
  node: TreeNode
  expanded: Set<Id>
  isChecked: (id: Id) => boolean
  isIndeterminate: (id: Id) => boolean
}>()

const emit = defineEmits<{
  (e: "toggle-expand", id: Id): void
  (e: "toggle-select", id: Id): void
}>()

const isExpanded = computed(() => props.expanded.has(props.node.id))
const checked = computed(() => props.isChecked(props.node.id))
const indeterminate = computed(() => props.isIndeterminate(props.node.id))

// 這裡用 ref 操控 indeterminate
const checkboxRef = ref<HTMLInputElement | null>(null)
watchEffect(() => {
  if (checkboxRef.value) {
    checkboxRef.value.indeterminate = indeterminate.value
  }
})
</script>

<template>
  <li>
    <div class="flex items-center gap-2">
      <!-- 展開按鈕 -->
      <button
        v-if="node.children?.length"
        class="w-5 h-5 text-gray-500 hover:text-gray-800"
        @click="emit('toggle-expand', node.id)"
      >
        <span v-if="isExpanded">▼</span>
        <span v-else>▶</span>
      </button>
      <span v-else class="w-5 h-5"></span>

      <!-- 勾選框，支援三態 -->
      <input
        ref="checkboxRef"
        type="checkbox"
        :checked="checked"
        @change="emit('toggle-select', node.id)"
      />

      <span
        class="cursor-pointer select-none"
        :class="checked ? 'font-bold text-blue-600' : ''"
        @click="emit('toggle-select', node.id)"
      >
        {{ node.label }}
      </span>
    </div>

    <!-- 子節點 -->
    <ul v-if="isExpanded" class="ml-6 mt-1 space-y-1 border-l pl-3 border-gray-300">
      <TreeItem
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :expanded="expanded"
        :is-checked="isChecked"
        :is-indeterminate="isIndeterminate"
        @toggle-expand="emit('toggle-expand', $event)"
        @toggle-select="emit('toggle-select', $event)"
      />
    </ul>
  </li>
</template>
