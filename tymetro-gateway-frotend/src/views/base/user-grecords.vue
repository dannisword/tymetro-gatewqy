<script setup lang="ts">
import { onBeforeMount, ref, reactive, computed } from "vue";
import { GridOptions } from "ag-grid-community";
import { PageHandle, AnySection } from "../../hooks";
import {
  ParamsSection,
  TableSection,
  SearchSection,
  FormSection,
  DialogSection,
} from "../../types/document-config";

import AgGridView from "../../components/AgGridView.vue";
import ElDialogCustom from "../../components/ElDialogCustom.vue";
import ElFormCustom from "../../components/ElFormCustom.vue";
import ElSearchCustom from "../../components/ElSearchCustom.vue";

import httpOperations from "../../utils/http-operations";
import { FormMode } from "../../utils/enums";

const {
  getSections,
  getSection,
  clearSchemas,
  assignSchemas,
  fetchDto,
  read,
  create,
  update,
} = PageHandle();

/**
 * 原始 row data
 */
const formCustomRef = ref<InstanceType<typeof ElFormCustom> | null>(null);

const opts: GridOptions = {
  rowSelection: "multiple",
  pagination: true,
  paginationPageSize: 20,
};

const isUserDialog = ref<Boolean>(false);
const userRoles = ref<any[]>([]);
const rowData = ref<any[]>([]);

const sections = ref<AnySection[]>([]);
const paramsRef = ref<ParamsSection>();
const formRef = ref<FormSection>({} as FormSection);
const searchRef = ref<SearchSection>({} as SearchSection);
const tableRef = ref<TableSection>({} as TableSection);

const userDialog = computed<DialogSection | null>(
  () => getSection<DialogSection>(sections.value, "Dialog", "User") ?? null
);

const userRoleDialog = computed<DialogSection | null>(
  () => getSection<DialogSection>(sections.value, "Dialog", "UserRole") ?? null
);

onBeforeMount(async () => {
  sections.value = await getSections();
  paramsRef.value = getSection(sections.value, "Params") as ParamsSection;
  formRef.value = getSection(sections.value, "Form") as FormSection;
  searchRef.value = getSection(sections.value, "Search") as SearchSection;
  tableRef.value = getSection(sections.value, "Table") as TableSection;

  await read(tableRef.value);
});

const onActionClick = async (event: any) => {
  formRef.value = (await clearSchemas()) as FormSection;
  if (userDialog.value) {
    isUserDialog.value = true;
    userDialog.value.visible = true;
  }
};

const onGridActionClick = async ({ action, data }: any) => {
  formRef.value = (await assignSchemas(data)) as FormSection;
  //  編輯
  if (action.event == FormMode.Edit) {
    if (userDialog.value) {
      isUserDialog.value = true;
      userDialog.value.visible = true;
    }
  }
  // 選單
  if (action.event == "Menu") {
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
};

const onModalClose = async (dialogRef: any) => {
  const isValid = await formCustomRef.value?.validate();
  if (isValid == true) {
    return;
  }

  if (dialogRef.close == true || dialogRef.success == false) {
    if (userDialog.value) {
      userDialog.value.visible = false;
    }
    if (userRoleDialog.value) {
      userRoleDialog.value.visible = false;
    }
    return;
  }

  if (userDialog.value) {
    userDialog.value.visible = false;
  }
  if (userRoleDialog.value) {
    userRoleDialog.value.visible = false;
  }
  // user
  const dto = await fetchDto(formRef.value);
  if (isUserDialog.value == true) {
    if (dto.id == 0) {
      await create(dto);
    } else {
      await update(dto);
    }
    await read(tableRef.value);
  } else {
    const url = `api/User/role/${dto.id}`;
    if (userRoles.value) {
      const response = await httpOperations.put(url, userRoles.value);
    }
  }
};

const onSelectionChanged = (data: any) => {
  rowData.value = data;
};
</script>

<template>
  <!-- h-[calc(100vh-280px)] -->
  <div class="flex flex-col h-[calc(100vh-260px)]">
    <main class="flex-1">
      <ElSearchCustom
        :schemas="searchRef.schemas"
        @confirm="read(tableRef)"
      ></ElSearchCustom>

      <AgGridView2
        :options="opts"
        :columns="tableRef?.columns"
        :actions="tableRef?.actions"
        :records="tableRef?.records"
        @action-click="onActionClick"
        @grid-action-click="onGridActionClick"
      >
      </AgGridView2>
    </main>

    <ElDialogCustom
      :title="userDialog?.title"
      :name="userDialog?.title"
      :width="'50%'"
      :visible="userDialog?.visible ?? false"
      @on-before-close="onModalClose"
    >
      <ElFormCustom
        ref="formCustomRef"
        :colNum="formRef?.colNum"
        :model="formRef.dto"
        :schemas="formRef.schemas"
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
