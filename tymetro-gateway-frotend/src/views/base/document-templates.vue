<script setup lang="ts">
import { onBeforeMount, ref, reactive } from 'vue'
import { DocumentHandle } from '../../hooks/document-handle'
import { FormMode } from '../../utils/enums'
import JsonEditorVue from 'vue3-ts-jsoneditor'
import { cloneDeep } from 'lodash'
import { GridOptions } from 'ag-grid-community'

import { useAlert } from '../../composables/TLAlter'
import ElDialogCustom from '../../components/ElDialogCustom.vue'

const { TLSuccess } = useAlert()

const { instance, loadJson, get, read, create, update, cleanSearch } = DocumentHandle()
/**
 * 原始 row data
 */
const rowData = ref<any>({})
const opts: GridOptions = {
  rowSelection: 'multiple',
  pagination: true,
  paginationPageSize: 20,
}
/**
 * 編輯資料
 */
const editData = ref<any>({})
const dialog = reactive({
  title: '樣板維護',
  visible: false,
})

onBeforeMount(async () => {
  await loadJson()
  await read()
})

const onSelectionChanged = (data: any) => {
  //const selectedRows = event.api.getSelectedRows();
  rowData.value = data
}

const handleActionClick = (event: any) => {
  if (event.action === FormMode.Add) {
    editData.value = {
      id: 0,
      templateCode: '',
      templateName: '',
      content: {},
      component: '',
      version: '1.0',
    }
    rowData.value = cloneDeep(editData.value)
    dialog.visible = true
  }
}
const handleGridActionClick = async ({ action, data }: any) => {
  // 編輯樣板
  if (action.event == FormMode.Edit) {
    let dto = await get(data.id)
    if (!dto) return;

    // 備份原始資料
    rowData.value = cloneDeep(dto);
    
    // 初始化編輯器資料
    const editorObj: any = {
      id: dto.id,
      templateCode: dto.templateCode,
      templateName: dto.templateName,
      component: dto.component,
      version: dto.version,
    };

    // 處理 content 的解析，如果是物件就直接用，是字串才 JSON.parse
    if (dto.content) {
      try {
        editorObj.content = typeof dto.content === 'string' ? JSON.parse(dto.content) : dto.content;
      } catch (e) {
        console.error('內容解析失敗', e);
        editorObj.content = {};
      }
    } else {
      editorObj.content = {}
    }

    editData.value = editorObj;
    dialog.visible = true;
  }
}

const modalClose = (dialogRef: any) => {
  if (dialogRef.close == true || dialogRef.success == false) {
    dialog.visible = false
    return
  }
  dialog.visible = false

  // 1. 確保從編輯器拿到的資料是物件
  let finalEditData = editData.value;
  if (typeof finalEditData === 'string') {
    try {
      finalEditData = JSON.parse(finalEditData);
    } catch (e) {
      console.error('JSON 解析失敗', e);
      return;
    }
  }

  // 2. 合併資料並處理內容字串化
  const submitData = {
    ...rowData.value,       // 保留原始資料（包含可能的 orgId 等）
    ...finalEditData,      // 覆蓋編輯後的欄位
  };

  // 確保 content 是 JSON 字串格式交給後端
  if (submitData.content && typeof submitData.content === 'object') {
    submitData.content = JSON.stringify(submitData.content);
  }

  setDocument(submitData);
}

const setDocument = async (data: any) => {
  if (data.id === 0) {
    data.orgId = 0
    data.id = 0
    data.orgCode = 'DEFAULT'
    await create(data)
  } else {
    await update(data)
  }
  await read()
}

const onPaginationChange = (state: any) => {
  read(state)
}
</script>
<template>
  <div class="flex flex-col h-[calc(100vh-250px)]">
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
        @selection-changed="onSelectionChanged"
        @action-click="handleActionClick"
        @grid-action-click="handleGridActionClick"
        @pagination-change="onPaginationChange"
      >
      </AgGridView2>
    </main>

    <ElDialogCustom
      :title="dialog.title"
      :width="'100%'"
      :visible="dialog.visible"
      @on-before-close="modalClose"
    >
      <JsonEditorVue class="flex flex-col h-[calc(100vh-130px)]" mode="text" v-model="editData" />
    </ElDialogCustom>
  </div>
</template>
