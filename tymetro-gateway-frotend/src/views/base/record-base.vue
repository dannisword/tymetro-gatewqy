<script setup lang="ts">
import { onBeforeMount, ref, reactive, computed } from "vue";
import { useRouter } from "vue-router";
import { DocumentHandle } from "../../hooks/document-handle";
import ElDialogCustom from "../../components/ElDialogCustom.vue";
import ElFormCustom from "../../components/ElFormCustom.vue";
import ElSearchCustom from "../../components/ElSearchCustom.vue";
import {
  arrayToObject,
  OrderType,
  CommandSource,
  CommandStatus,
  objectToArray,
} from "@/utils/index";
import { FormMode } from "../../utils/enums";
import { useAlert } from "../../composables/TLAlter";
import { routeHandle } from "../../hooks/route-handle";
import { GridOptions } from "ag-grid-community";
import httpOperations from "@/utils/http-operations";
import {
  AnySection,
  ParamsSection,
  TableSection,
  SearchSection,
  FormSection,
  DialogSection,
} from "../../types/document-config";
import { cloneDeep } from "lodash";

const { TLSuccess, TLWarning, TLError, TLInfo } = useAlert();
const router = useRouter();
const { pageName } = routeHandle();
const {
  instance,
  getSection,
  loadDocument,
  cleanData,
  setData,
  read,
  cleanSearch,
  create,
  update,
} = DocumentHandle();
/**
 * 原始 row data
 */
const formRef = ref<InstanceType<typeof ElFormCustom> | null>(null);

const isUserDialog = ref<Boolean>(false);
const userRoles = ref<any[]>([]);
const rowData = ref<any[]>([]);
const opts: GridOptions = {
  rowSelection: "multiple",
  pagination: true,
  paginationPageSize: 20,
};
const dialog = reactive({
  title: "編輯",
  visible: false,
});
const sections = ref<AnySection[]>([]);

const userRoleDialog = computed<DialogSection | null>(
  () => getSection<DialogSection>(sections.value, "Dialog", "UserRole") ?? null,
);
const page = pageName();

onBeforeMount(async () => {
  await loadDocument();
  // 呼叫更簡潔的方法
  instance.setColumnOptions('isActive', [
    { label: "啟用", value: true },
    { label: "停用", value: false }
  ]);
  await read();
});
const onActionClick = (event: any) => {
  cleanData();
  dialog.visible = true;
};

const onGridActionClick = async ({ action, data }: any) => {
  if (action.event == FormMode.Edit) {
    setData(data);
    dialog.visible = true;
    // router.push(`/organize-base/${data.id}`);
  }
  // 選單
  if (action.event == FormMode.Menu) {
    if (userRoleDialog.value) {
      isUserDialog.value = false;

      if (userRoleDialog.value?.table?.options) {
        // 取得使用者權限
        const url = `${userRoleDialog.value?.table?.options.api}/${data.id}`;
        const response = (await httpOperations.get(url)) as any;
        userRoles.value = response?.data;
      }

      isUserDialog.value = false;
      userRoleDialog.value.visible = true;
    }
  }
  // 命令取消
  if (action.event == FormMode.Cancel) {
    instance.form.dto = cloneDeep(data);
    instance.form.dto.commandStatus = CommandStatus.CANCEL;
    await update(instance.form.dto);
    await read();
  }
};

const onModalClose = async (dialogRef: any) => {
  
  if (dialogRef.close == true || dialogRef.success == false) {
    dialog.visible = false;
    return;
  }
  const isValid = await formRef.value?.validate();

  if (isValid == true) {
    TLWarning("請檢查欄位");
    return;
  }

  try {
  
    if (instance.form.dto.id == 0) {
      await create(instance.form.dto);
      TLSuccess("新增成功");
    } else {
      await update(instance.form.dto);
      TLSuccess("更新成功");
    }
    dialog.visible = false;
    await read();
  } catch (err) {
    TLWarning("操作失敗，請稍後重試");
  }
};

const onPaginationChange = (state: any) => {
  console.log("onPaginationChange", state);
  read(state);
};

const onSelectionChanged = (data: any) => {
  rowData.value = data;
};
</script>

<template>
  <!-- h-[calc(100vh-280px)] -->
  <div class="flex flex-col h-[calc(100vh-250px)] p-3">
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
        @pagination-change="onPaginationChange"
      >
      </AgGridView2>
    </main>

    <ElDialogCustom
      :title="dialog.title"
      :width="'50%'"
      :visible="dialog.visible"
      @on-before-close="onModalClose"
    >
      <ElFormFlex
        ref="formRef"
        :colNum="instance.form.colNum"
        :model="instance.form.dto"
        :schemas="instance.form.schemas"
      />
    </ElDialogCustom>

    <ElDialogCustom
      :title="userRoleDialog?.title"
      :name="userRoleDialog?.title"
      :width="'50%'"
      :visible="userRoleDialog?.visible ?? false"
      @on-before-close="onModalClose"
    >
      <div class="h-[65vh] flex flex-col min-h-0">
        <AgGridView2
          :options="opts"
          :columns="userRoleDialog?.table?.columns"
          :actions="userRoleDialog?.table?.actions"
          v-model:records="userRoles"
          @selectionChanged="onSelectionChanged"
        >
        </AgGridView2>
      </div>
    </ElDialogCustom>
  </div>
</template>
