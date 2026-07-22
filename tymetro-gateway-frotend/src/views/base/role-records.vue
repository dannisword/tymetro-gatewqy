<script setup lang="ts">
import { onBeforeMount, ref, reactive } from "vue";
import { DocumentHandle } from "../../hooks/document-handle";
import ElDialogCustom from "../../components/ElDialogCustom.vue";
import ElFormCustom from "../../components/ElFormCustom.vue";
import ElSearchCustom from "../../components/ElSearchCustom.vue";
import TreeList, { type TreeNode } from "../../components/TreeList.vue";
import { arrayToObject } from "@/utils";
import { FormMode } from "../../utils/enums";
import { routeHandle } from "../../hooks/route-handle";
import { GridOptions } from "ag-grid-community";
import httpOperations from "@/utils/http-operations";
const { pageName } = routeHandle();
const { instance, loadDocument, cleanData, setData, read, create, update, cleanSearch } =
  DocumentHandle();
/**
 * 原始 row data
 */
const formRef = ref<InstanceType<typeof ElFormCustom> | null>(null);
const opts: GridOptions = {
  rowSelection: "multiple",
  pagination: true,
  paginationPageSize: 20,
};
const nodes = ref<TreeNode[]>([]);
const selectedNodes = ref<(string | number)[]>([]);
const dialog = reactive({
  title: "",
  visible: false,
});

onBeforeMount(async () => {
  await loadDocument();
  await read();
});
const onActionClick = (event: any) => {
  cleanData();
  httpOperations.get("api/v1/roles/menus").then((response: any) => {
    selectedNodes.value = [];
    nodes.value = toTreeNodes(response.data);
  });
  dialog.visible = true;
};

const onGridActionClick = async ({ action, data }: any) => {
  if (action.event == FormMode.Edit) {
    // 再抓一次後端最新資料
    await setData(data);
    nodes.value = toTreeNodes(instance.form.dto.rolePermissions);

    const defaults = collectSelectedIds(
      instance.form.dto.rolePermissions,
      /* leafOnly */ false,
    );
    selectedNodes.value = defaults;
    dialog.visible = true;
  }
};
const onModalClose = async (dialogRef: any) => {
  const page = pageName();
  if (dialogRef.close == true || dialogRef.success == false) {
    dialog.visible = false;
    return;
  }
  const isValid = await formRef.value?.validate();

  if (isValid == true) {
    return;
  }
  dialog.visible = false;
  arrayToObject(instance.form.dto, instance.form.schemas);
  // 更新選取資料
  applySelectedIds(instance.form.dto.rolePermissions, selectedNodes.value);

  if (instance.form.dto.id == 0) {
    await create(instance.form.dto);
  } else {
    await update(instance.form.dto);
  }

  await read();
};
const onSelectAll = () => {
  const ids: (string | number)[] = [];
  const walk = (list: any[]) => {
    list.forEach((n) => {
      ids.push(n.id);
      if (n.children) walk(n.children);
    });
  };
  walk(nodes.value);
  selectedNodes.value = ids;
};

function collectSelectedIds(
  input: any[],
  leafOnly = true,
): (string | number)[] {
  const out: (string | number)[] = [];
  const walk = (n: any) => {
    const kids = n.children ?? [];
    const isLeaf = kids.length === 0;
    if (n.isSelected) {
      if (!leafOnly || isLeaf) {
        out.push(n.id);
      }
    }
    kids.forEach(walk);
  };
  input.forEach(walk);
  return out;
}

function toTreeNodes(input: any[]): TreeNode[] {
  const mapNode = (n: any): TreeNode => ({
    id: n.id,
    label: n.label,
    children: (n.children ?? [])?.map(mapNode),
  });
  return input.map(mapNode);
}

function applySelectedIds(list: any[], selectedIds: (string | number)[]) {
  if (list == null || list.length === 0) {
    return;
  }
  const set = new Set(selectedIds);

  const walk = (node: any): boolean => {
    // 1. 先判斷當前節點本身是否在選中名單中
    let selfSelected = set.has(node.id);

    // 2. 遞迴處理子節點
    let childrenSelected = false;
    if (node.children && node.children.length > 0) {
      // 只要任何一個子節點回傳 true，父節點的 childrenSelected 就會是 true
      node.children.forEach((child: any) => {
        if (walk(child)) {
          childrenSelected = true;
        }
      });
    }

    // 💡 核心邏輯：本身被選中 OR 子節點有被選中 = 該節點為 true
    node.isSelected = selfSelected || childrenSelected;

    // 回傳給上一層父節點參考
    return node.isSelected;
  };

  list.forEach(walk);
}
</script>

<template>
  <!-- h-[calc(100vh-280px)] -->
  <div class="flex flex-col h-[calc(100vh-260px)]">
    <main class="flex-1">
      <ElSearchCustom
        :schemas="instance.search.schemas"
        @confirm="read"
        @clear="cleanSearch"
      ></ElSearchCustom>

      <AgGridView2
        :options="opts"
        :columns="instance.table.columns"
        :actions="instance.table.actions"
        :records="instance.table.records"
        :pagination="instance.pagination"
        @action-click="onActionClick"
        @grid-action-click="onGridActionClick"
      >
      </AgGridView2>
    </main>

    <ElDialogCustom
      :title="dialog.title"
      :width="'30%'"
      :height="'300px'"
      :visible="dialog.visible"
      @on-before-close="onModalClose"
    >
      <ElFormCustom
        ref="formRef"
        :colNum="instance.form.colNum"
        :model="instance.form.dto"
        :schemas="instance.form.schemas"
      />
      <div
        class="flex items-center justify-between mb-2 mt-4 px-2 border-b pb-2"
      >
        <span class="text-xs font-bold text-slate-500 uppercase tracking-widest"
          >權限分配設定</span
        >
        <div class="flex gap-4">
          <button
            type="button"
            @click="selectedNodes = []"
            class="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            清除全部
          </button>
          <button
            type="button"
            @click="onSelectAll"
            class="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            全選
          </button>
        </div>
      </div>
      <TreeList
        :nodes="nodes"
        :multiple="true"
        v-model:selected="selectedNodes"
      />
    </ElDialogCustom>
  </div>
</template>
