<script setup lang="ts">
import { ref, watchEffect, watch } from "vue";

export interface TreeNode {
  id: string | number;
  label: string;
  children?: TreeNode[];
}

type Id = string | number;

const props = defineProps<{
  nodes: TreeNode[];
  selected?: Id[]; // v-model:selected
}>();

const emit = defineEmits<{
  (e: "update:selected", value: Id[]): void;
}>();

const expanded = ref<Set<Id>>(new Set());
const selected = ref<Set<Id>>(new Set(props.selected ?? []))
// ===== 索引 =====
const childrenMap = new Map<Id, Id[]>();
const parentMap = new Map<Id, Id | null>();

function buildIndex(list: TreeNode[], parent: Id | null = null) {
  for (const n of list) {
    parentMap.set(n.id, parent);
    if (n.children?.length) {
      const kids = n.children.map((c) => c.id);
      childrenMap.set(n.id, kids);
      buildIndex(n.children, n.id);
    } else {
      childrenMap.set(n.id, []);
    }
  }
}
buildIndex(props.nodes);

// ===== 工具 =====
function getDescendants(id: Id): Id[] {
  const out: Id[] = [];
  const stack = [...(childrenMap.get(id) ?? [])];
  while (stack.length) {
    const cur = stack.pop() as Id;
    out.push(cur);
    stack.push(...(childrenMap.get(cur) ?? []));
  }
  return out;
}

function getAncestors(id: Id): Id[] {
  const res: Id[] = [];
  let p = parentMap.get(id);
  while (p != null) {
    res.push(p);
    p = parentMap.get(p);
  }
  return res;
}

// ===== 狀態判斷 =====
function isChecked(id: Id): boolean {
  return selected.value.has(id);
}
function isIndeterminate(id: Id): boolean {
  const kids = childrenMap.get(id) ?? [];
  if (kids.length === 0) return false;
  const any = kids.some((k) => isChecked(k) || isIndeterminate(k));
  const all =
    kids.length > 0 && kids.every((k) => isChecked(k) && !isIndeterminate(k));
  return any && !all;
}

// ===== 動作 =====
function toggleExpand(id: Id) {
  expanded.value.has(id) ? expanded.value.delete(id) : expanded.value.add(id);
}

function toggleSelect(id: Id) {
  const willCheck = !isChecked(id);

  if (willCheck) {
    selected.value.add(id);
    for (const d of getDescendants(id)) selected.value.add(d);
  } else {
    selected.value.delete(id);
    for (const d of getDescendants(id)) selected.value.delete(d);
  }

  for (const p of getAncestors(id)) {
    const kids = childrenMap.get(p) ?? [];
    const all = kids.length > 0 && kids.every((k) => isChecked(k));
    const none = kids.every((k) => !isChecked(k));
    if (all) {
      selected.value.add(p);
    } else if (none) {
      selected.value.delete(p);
    } else {
      selected.value.delete(p); // indeterminate 交給 isIndeterminate
    }
  }

  emit("update:selected", Array.from(selected.value));
}
// 父元件改變 selected -> 內部同步
watch(
  () => props.selected,
  val => {
    if (!val) return
    // 清掉不存在的
    selected.value.forEach(id => {
      if (!val.includes(id)) selected.value.delete(id)
    })
    // 新增新的
    val.forEach(id => selected.value.add(id))
  },
  { immediate: true }
)
watchEffect(() => {
  emit("update:selected", Array.from(selected.value));
});
</script>

<template>
  <ul class="space-y-1">
    <TreeItem
      v-for="n in nodes"
      :key="n.id"
      :node="n"
      :expanded="expanded"
      :is-checked="isChecked"
      :is-indeterminate="isIndeterminate"
      @toggle-expand="toggleExpand"
      @toggle-select="toggleSelect"
    />
  </ul>
</template>
