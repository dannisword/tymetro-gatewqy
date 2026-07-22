<script setup lang="ts">
import { onBeforeMount, ref } from "vue";
import { FormHandle } from "../../hooks/form-handle";
import { useAlert } from "../../composables/TLAlter";
import { useRouter, useRoute } from "vue-router";
import { useTagsStore } from "../../store/useTagsStore";

const props = defineProps<{
  id?: string | number;
}>();

const { TLSuccess, TLWarning } = useAlert();
const router = useRouter();
const route = useRoute();
const tagsStore = useTagsStore();

// 佈局與資料處理 hook (FormHandle 現在已經整合了 DocumentHandle)
const { 
  instance,
  loadDocument,
  setData,
  update,
  activeTab, 
  accordionSections, 
  tabSections, 
  initLayout, 
  validateAll 
} = FormHandle();

const formRefs = ref<any[]>([]);

onBeforeMount(async () => {
  // 1. 載入對應頁面的 JSON 配置
  await loadDocument();
  
  // 2. 初始化佈局 (例如頁籤首項)
  initLayout();

  // 3. 取得並設定資料 (若是編輯模式)
  if (props.id) {
    await setData({ id: props.id });
    
    // 動態更新導航標籤標題
    const baseTitle = route.meta.title || "編輯資料";
    tagsStore.updateTitle(route.fullPath, `${baseTitle} - ${props.id}`);
  }
});

const onSave = async () => {
  // 執行跨區塊批次驗證
  const allValid = await validateAll(formRefs.value);
  if (!allValid) {
    TLWarning("請檢查欄位內容是否填寫正確");
    return;
  }

  try {
    await update(instance.form.dto);
    TLSuccess("儲存成功");
    router.back();
  } catch (err) {
    TLWarning("儲存失敗，請檢查網路狀態");
  }
};

const onCancel = () => {
  router.back();
};
</script>

<template>
  <div class="p-4 bg-slate-50 dark:bg-slate-950 min-h-screen">
    <!-- 頂部頭部區 -->
    <div class="flex items-center justify-between mb-4 bg-white dark:bg-slate-900 p-4 rounded-lg shadow-sm border border-border">
      <div class="flex items-center gap-3">
        <div class="w-2 h-8 bg-primary rounded-full"></div>
        <div>
          <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            {{ instance.document.docName || route.meta.title || '頁面編輯' }}
            <span v-if="props.id" class="text-primary opacity-70">#{{ props.id }}</span>
          </h2>
          <p class="text-xs text-slate-500 opacity-60">
            {{ instance.document.componentName }} (UI: form-base)
          </p>
        </div>
      </div>
      <div class="flex gap-2">
        <el-button @click="onCancel" class="!px-6">返回列表</el-button>
        <el-button type="primary" @click="onSave" class="!px-6 shadow-lg shadow-primary/20">
          確認儲存
        </el-button>
      </div>
    </div>

    <!-- 內容區域 -->
    <div class="space-y-4">
      <!-- 展開區塊 (頂部基本資料) -->
      <el-collapse 
        v-if="accordionSections.length > 0"
        :model-value="accordionSections.map(s => s.title)" 
        class="custom-collapse border-none"
      >
        <el-collapse-item v-for="section in accordionSections" :key="section.title" :name="section.title">
          <template #title>
            <div class="flex items-center gap-2 font-bold text-primary pl-4 text-base">
              <span class="w-1.5 h-4 bg-primary rounded-full"></span>
              {{ section.title }}
            </div>
          </template>
          <div class="p-6 bg-white dark:bg-slate-900 rounded-b-lg border-x border-b border-border shadow-sm">
            <ElFormFlex
              ref="formRefs"
              :colNum="section.colNum || 12"
              :model="instance.form.dto"
              :schemas="section.schemas"
            />
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- 頁籤分區 (次要多組資料) -->
      <div v-if="tabSections.length > 0" class="bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-border overflow-hidden">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane v-for="section in tabSections" :key="section.title" :label="section.title" :name="section.title">
            <div class="p-6">
              <ElFormFlex
                ref="formRefs"
                :colNum="section.colNum || 12"
                :model="instance.form.dto"
                :schemas="section.schemas"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 自訂 UI 樣式，模擬 ERP 專業質感 */
:deep(.el-collapse-item__header) {
  height: 54px;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  border-radius: 8px 8px 0 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:deep(.dark .el-collapse-item__header) {
  background-color: #1e293b;
  border-bottom-color: #334155;
}

:deep(.el-collapse-item__header.is-active) {
  border-bottom-color: transparent;
}

:deep(.el-tabs__header) {
  margin: 0;
  background-color: #f8fafc;
  padding: 0 16px;
  border-bottom: 2px solid #f1f5f9;
}

:deep(.dark .el-tabs__header) {
  background-color: #1e293b;
  border-bottom-color: #334155;
}

:deep(.el-tabs__nav-wrap::after) {
  height: 0;
}

:deep(.el-tabs__item) {
  height: 50px;
  font-weight: 500;
}
</style>
