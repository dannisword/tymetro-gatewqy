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
import SensorTemplate from "./components/sensor-template.vue";

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
const sensorTemplateRef = ref<any>(null);
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
    // 如果有 SensorTemplate 組件，則處理複製邏輯
    if (sensorTemplateRef.value) {
    
      const selectedEquipmentId = sensorTemplateRef.value.selectedEquipmentId;
    
      if (selectedEquipmentId == null) {
        TLWarning("請選擇設備");
        return;
      }
      const selectedItems = sensorTemplateRef.value.getSelectedItems();
    
      if (selectedItems.length === 0) {
        TLWarning("請至少選擇一項範本");
        return;
      }
      // 這裡可以呼叫您的複製 API
      const data = {
        "equipmentId": selectedEquipmentId,
        "templateIds": selectedItems.map((item: any) => item.id) 
      }
      
      await httpOperations.post('/api/v1/sensor-templates/apply', data);
      TLSuccess(`已成功套用 ${selectedItems.length} 筆範本資料`);
      await read();
      dialog.visible = false;
      return;
    }

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
    console.log(err);
    
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
      :width="'100%'"
      :visible="dialog.visible"
      @on-before-close="onModalClose"
    >
      
      <SensorTemplate ref="sensorTemplateRef" />
    </ElDialogCustom>
  </div>
</template>
