<script setup lang="ts">
import { ref, reactive, computed, watch } from "vue";
import { mdiPlus, mdiDelete, mdiChevronUp, mdiChevronDown, mdiContentCopy, mdiCodeJson } from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";
import BaseButton from "@/components/BaseButton.vue";
import { useAlert } from "@/composables/TLAlter";
import JsonEditorVue from "vue3-ts-jsoneditor";

const { TLSuccess, TLWarning } = useAlert();

// --- Types ---
interface ApiUrl {
  read: string;
  create: string;
  update: string;
  delete: string;
}

interface Section {
  sectionType: "Params" | "Form" | "Search" | "Table";
  apiUrl?: ApiUrl;
  colNum?: number;
  dto?: Record<string, any>;
  schemas?: any[];
  params?: Record<string, any>;
  singleRow?: boolean;
  options?: Record<string, any>;
  actions?: any[];
  columns?: any[];
}

// --- Initial Data ---
const initialJson = {
  sections: [
    {
      sectionType: "Params",
      apiUrl: {
        read: "/api/v1/users",
        create: "/api/v1/users",
        update: "/api/v1/users",
        delete: "/api/v1/users"
      }
    }
  ]
};

const config = reactive({
  sections: [] as Section[]
});

// Load initial structure
try {
  Object.assign(config, JSON.parse(JSON.stringify(initialJson)));
} catch (e) {}

const activeTab = ref("editor"); // editor | preview
const activeSections = ref<number[]>([0]);

// --- Methods ---
const addSection = (type: Section["sectionType"]) => {
  const newSection: Section = { sectionType: type };
  
  if (type === "Params") {
    newSection.apiUrl = { read: "", create: "", update: "", delete: "" };
  } else if (type === "Form") {
    newSection.colNum = 12;
    newSection.dto = { id: 0 };
    newSection.schemas = [];
  } else if (type === "Search") {
    newSection.params = { order: "ASC", pageIndex: 0, propertyName: "OrderSeq", pageSize: 50 };
    newSection.schemas = [];
  } else if (type === "Table") {
    newSection.singleRow = true;
    newSection.options = {};
    newSection.actions = [];
    newSection.columns = [];
  }
  
  config.sections.push(newSection);
  activeSections.value = [config.sections.length - 1];
};

const removeSection = (index: number) => {
  config.sections.splice(index, 1);
};

const moveSection = (index: number, direction: number) => {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= config.sections.length) return;
  const temp = config.sections[index];
  config.sections[index] = config.sections[newIndex];
  config.sections[newIndex] = temp;
};

// --- Field Helpers ---
const addField = (section: Section, target: 'schemas' | 'columns' | 'actions' | 'actionButtons', parent?: any) => {
  if (target === 'schemas') {
    section.schemas = section.schemas || [];
    section.schemas.push({ prop: "", type: "input", label: "", value: "", rules: [] });
  } else if (target === 'columns') {
    section.columns = section.columns || [];
    section.columns.push({ headerName: "", field: "", minWidth: 180, editable: false, sortable: true, filter: false, suppressMovable: false, lockPosition: false});
  } else if (target === 'actions') {
    section.actions = section.actions || [];
    section.actions.push({ label: "", type: "primary", field: "", action: "", icon: "mdiPlus" });
  } else if (target === 'actionButtons') {
    parent.actionButtons = parent.actionButtons || [];
    parent.actionButtons.push({ label: "編輯", type: "primary", icon: "mdiPencil", event: "Edit" });
  }
};

const removeField = (list: any[], index: number) => {
  list.splice(index, 1);
};

// --- JSON Output ---
const generatedJson = computed(() => {
  return JSON.stringify(config, null, 2);
});

const copyJson = async () => {
  try {
    await navigator.clipboard.writeText(generatedJson.value);
    TLSuccess("已複製到剪貼簿");
  } catch (err) {
    TLWarning("複製失敗");
  }
};

const onJsonUpdate = (val: any) => {
  if (val && val.sections) {
    config.sections = val.sections;
  }
};
</script>

<template>
  <div class="designer-container flex flex-col h-screen bg-slate-50 overflow-hidden">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3">
        <div class="bg-blue-600 p-2 rounded-lg text-white">
          <BaseIcon :path="mdiCodeJson" size="24" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-800">Visual JSON Designer</h1>
          <p class="text-xs text-slate-500 uppercase tracking-wider">Drag & Build Document Templates</p>
        </div>
      </div>
      
      <div class="flex items-center gap-4">
        <el-radio-group v-model="activeTab" size="large">
          <el-radio-button label="editor">設計器</el-radio-button>
          <el-radio-button label="preview">源碼預覽</el-radio-button>
        </el-radio-group>
        <BaseButton variant="primary" @click="copyJson">
          <BaseIcon :path="mdiContentCopy" /> 複製代碼
        </BaseButton>
      </div>
    </header>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden flex">
      <!-- Editor Mode -->
      <div v-if="activeTab === 'editor'" class="flex-1 flex overflow-hidden">
        <!-- Sidebar: Toolbox -->
        <aside class="w-64 border-r border-slate-200 bg-white p-4 overflow-y-auto shrink-0 shadow-sm">
          <h3 class="text-xs font-bold text-slate-400 mb-4 uppercase tracking-widest">可用區塊類型</h3>
          <div class="flex flex-col gap-2">
            <button @click="addSection('Params')" class="toolbox-item group">
              <span class="bg-blue-100 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">P</span> Params (API 路徑)
            </button>
            <button @click="addSection('Form')" class="toolbox-item group">
              <span class="bg-green-100 text-green-600 group-hover:bg-green-600 group-hover:text-white transition-colors">F</span> Form (表單欄位)
            </button>
            <button @click="addSection('Search')" class="toolbox-item group">
              <span class="bg-blue-100 text-blue-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">S</span> Search (搜尋條件)
            </button>
            <button @click="addSection('Table')" class="toolbox-item group">
              <span class="bg-orange-100 text-orange-600 group-hover:bg-orange-600 group-hover:text-white transition-colors">T</span> Table (資料表格)
            </button>
          </div>

          <div class="mt-8 p-4 bg-slate-50 rounded-xl border border-slate-100">
             <p class="text-[10px] text-slate-400 leading-relaxed italic">
               說明：點擊上方按鈕可新增對應格式的 JSON 區塊。
             </p>
          </div>
        </aside>

        <!-- Canvas -->
        <main class="flex-1 bg-slate-100 p-8 overflow-y-auto">
          <div class="max-w-4xl mx-auto flex flex-col gap-4">
            <div v-if="config.sections.length === 0" class="text-center py-32 border-2 border-dashed border-slate-300 rounded-3xl text-slate-400 bg-white">
               <BaseIcon :path="mdiPlus" size="64" class="mx-auto mb-4 opacity-10" />
               <p class="text-lg font-medium">尚未加入任何區塊</p>
               <p class="text-sm">從左側選擇一個類型開始設計你的頁面 JSON</p>
            </div>

            <el-collapse v-model="activeSections" accordion>
              <el-collapse-item v-for="(section, idx) in config.sections" :key="idx" :name="idx" 
                class="section-card border !border-slate-200 rounded-xl overflow-hidden mb-4 shadow-sm bg-white">
                <template #title>
                  <div class="flex items-center justify-between w-full px-6">
                    <div class="flex items-center gap-4">
                      <span :class="['type-badge', section.sectionType]">{{ section.sectionType }}</span>
                      <span class="text-slate-700 font-bold">區塊 #{{ idx + 1 }}</span>
                    </div>
                    <div class="flex items-center gap-1 mr-4" @click.stop>
                      <button @click="moveSection(idx, -1)" class="icon-btn" :disabled="idx === 0" title="上移">
                        <BaseIcon :path="mdiChevronUp" size="18" />
                      </button>
                      <button @click="moveSection(idx, 1)" class="icon-btn" :disabled="idx === config.sections.length - 1" title="下移">
                        <BaseIcon :path="mdiChevronDown" size="18" />
                      </button>
                      <button @click="removeSection(idx)" class="icon-btn danger" title="刪除">
                        <BaseIcon :path="mdiDelete" size="18" />
                      </button>
                    </div>
                  </div>
                </template>

                <div class="p-6 bg-white border-t border-slate-100 space-y-6">
                  <!-- API URL (Params Type) -->
                  <div v-if="section.sectionType === 'Params'" class="space-y-4">
                     <div class="grid grid-cols-2 gap-4">
                        <div class="space-y-1">
                          <label class="text-xs font-bold text-slate-500">Read API</label>
                          <el-input v-model="section.apiUrl!.read" placeholder="/api/v1/..." />
                        </div>
                        <div class="space-y-1">
                          <label class="text-xs font-bold text-slate-500">Create API</label>
                          <el-input v-model="section.apiUrl!.create" placeholder="/api/v1/..." />
                        </div>
                        <div class="space-y-1">
                          <label class="text-xs font-bold text-slate-500">Update API</label>
                          <el-input v-model="section.apiUrl!.update" placeholder="/api/v1/..." />
                        </div>
                        <div class="space-y-1">
                          <label class="text-xs font-bold text-slate-500">Delete API</label>
                          <el-input v-model="section.apiUrl!.delete" placeholder="/api/v1/..." />
                        </div>
                     </div>
                  </div>

                  <!-- Form / Search Fields -->
                  <div v-if="section.sectionType === 'Form' || section.sectionType === 'Search'" class="space-y-4">
                    <div class="flex items-center justify-between bg-slate-50 p-3 rounded-lg border border-slate-200">
                      <h4 class="font-bold text-slate-700 text-sm">欄位配置 (Schemas)</h4>
                      <BaseButton size="sm" variant="primary" @click="addField(section, 'schemas')">
                        <BaseIcon :path="mdiPlus" /> 新增欄位
                      </BaseButton>
                    </div>
                    
                    <div class="space-y-3">
                      <div v-for="(schema, sIdx) in section.schemas" :key="sIdx" 
                        class="grid grid-cols-12 gap-3 p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-400 transition-colors shadow-sm relative group items-end">
                        
                        <div class="col-span-2 space-y-1">
                          <label class="text-[10px] uppercase font-bold text-slate-400">Prop (ID)</label>
                          <el-input v-model="schema.prop" placeholder="欄位代碼" />
                        </div>
                        
                        <div class="col-span-2 space-y-1">
                          <label class="text-[10px] uppercase font-bold text-slate-400">Type</label>
                          <el-select v-model="schema.type" placeholder="類型" class="w-full">
                            <el-option label="Input (文字)" value="input" />
                            <el-option label="Textarea (長文字)" value="textarea" />
                            <el-option label="Select (下拉)" value="select" />
                            <el-option label="Multiple Select (複選)" value="multiple-select" />
                            <el-option label="Autocomplete (自動完成)" value="autocomplete" />
                            <el-option label="Number (數字)" value="number" />
                            <el-option label="Date (日期)" value="date" />
                          </el-select>
                        </div>
                        
                        <div class="col-span-3 space-y-1">
                          <label class="text-[10px] uppercase font-bold text-slate-400">Label (顯示名稱)</label>
                          <el-input v-model="schema.label" placeholder="顯示名稱" />
                        </div>

                        <div class="col-span-1 flex flex-col items-center justify-center pb-2">
                          <label class="text-[10px] uppercase font-bold text-slate-400 mb-2">必填</label>
                          <el-checkbox v-model="schema.required" @change="(val: any) => {
                            if (val) {
                              schema.rules = [{ required: true, message: '', trigger: 'blur' }, { message: '請輸入' + schema.label }];
                            } else {
                              schema.rules = [];
                            }
                          }" />
                        </div>

                        <div class="col-span-3 space-y-1">
                          <template v-if="schema.type === 'select'">
                            <label class="text-[10px] uppercase font-bold text-slate-400">Option Type</label>
                            <el-input v-model="schema.optionType" placeholder="選項類型碼" />
                          </template>
                          <template v-else>
                             <label class="text-[10px] uppercase font-bold text-slate-400 opacity-0">Placeholder</label>
                             <el-input v-model="schema.placeholder" placeholder="提示文字" />
                          </template>
                        </div>

                        <div class="col-span-1 flex items-end justify-center pb-1">
                          <button @click="removeField(section.schemas!, sIdx)" class="icon-btn danger text-rose-500 opacity-0 group-hover:opacity-100 transition-opacity">
                            <BaseIcon :path="mdiDelete" size="18" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Table Columns -->
                  <div v-if="section.sectionType === 'Table'" class="space-y-4">
                    <div class="flex items-center justify-between bg-slate-50 p-3 rounded-lg border border-slate-200">
                      <h4 class="font-bold text-slate-700 text-sm">表格欄位 (Columns)</h4>
                      <BaseButton size="sm" variant="primary" @click="addField(section, 'columns')">
                        <BaseIcon :path="mdiPlus" /> 新增列
                      </BaseButton>
                    </div>
                    
                    <div class="space-y-3">
                      <div v-for="(col, cIdx) in section.columns" :key="cIdx" 
                        class="p-4 bg-white rounded-xl border border-slate-200 hover:border-orange-400 transition-colors shadow-sm group">
                        
                        <div class="grid grid-cols-12 gap-3 items-end">
                           <div class="col-span-4 space-y-1">
                             <label class="text-[10px] uppercase font-bold text-slate-400">Header Name</label>
                             <el-input v-model="col.headerName" />
                           </div>
                           <div class="col-span-4 space-y-1">
                             <label class="text-[10px] uppercase font-bold text-slate-400">Field (Prop)</label>
                             <el-input v-model="col.field" />
                           </div>
                           <div class="col-span-3 space-y-1">
                             <label class="text-[10px] uppercase font-bold text-slate-400">Width</label>
                             <el-input-number v-model="col.minWidth" class="!w-full" controls-position="right" />
                           </div>
                           <div class="col-span-1 flex justify-center">
                             <button @click="removeField(section.columns!, cIdx)" class="icon-btn danger text-rose-500 opacity-0 group-hover:opacity-100 transition-opacity">
                               <BaseIcon :path="mdiDelete" size="18" />
                             </button>
                           </div>
                        </div>

                        <!-- Special: Action Buttons if Action Renderer -->
                        <div class="mt-4 pt-4 border-t border-slate-100 flex items-center gap-4">
                           <el-checkbox v-model="col.cellRenderer" true-label="AGActionButtonRenderer" false-label="">
                             設為操作按鈕列
                           </el-checkbox>
                           
                           <div v-if="col.cellRenderer === 'AGActionButtonRenderer'" class="flex-1 flex gap-2">
                              <el-tag v-for="(btn, bIdx) in col.actionButtons" :key="bIdx" closable @close="col.actionButtons.splice(bIdx,1)" effect="dark">
                                {{ btn.label }}
                              </el-tag>
                              <button @click="addField(section, 'actionButtons', col)" class="text-xs text-blue-600 font-bold hover:underline">
                                + 新增按鈕
                              </button>
                           </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </main>
      </div>

      <!-- Preview Mode -->
      <div v-else class="flex-1 p-8 bg-slate-900 overflow-hidden flex flex-col">
          <div class="mb-4 flex items-center justify-between text-white/60">
             <span class="text-xs uppercase tracking-widest font-bold">Template Source Code</span>
             <span class="text-[10px]">Real-time JSON synchronization</span>
          </div>
          <div class="flex-1 bg-slate-950/50 rounded-2xl shadow-2xl border border-white/5 overflow-hidden">
             <JsonEditorVue 
               class="h-full"
               :model-value="config" 
               @update:model-value="onJsonUpdate"
               mode="text" 
             />
          </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbox-item {
  @apply flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-100 hover:border-blue-300 hover:bg-slate-50 transition-all text-sm font-bold text-slate-600 text-left mb-1;
}
.toolbox-item span {
  @apply w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shadow-sm;
}

.type-badge {
  @apply px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest shadow-sm;
}
.type-badge.Params { @apply bg-blue-100 text-blue-600; }
.type-badge.Form { @apply bg-green-100 text-green-600; }
.type-badge.Search { @apply bg-blue-100 text-blue-600; }
.type-badge.Table { @apply bg-orange-100 text-orange-600; }

.icon-btn {
  @apply p-2 rounded-xl text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition-all disabled:opacity-20;
}
.icon-btn.danger:hover {
  @apply bg-rose-50 text-rose-600;
}

:deep(.el-collapse-item__header) {
  @apply h-16 border-none select-none !important;
}
:deep(.el-collapse-item__content) {
  @apply p-0 !important;
}
:deep(.el-collapse-item__wrap) {
  @apply border-none !important;
}

.designer-container {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  @apply bg-transparent;
}
::-webkit-scrollbar-thumb {
  @apply bg-slate-200 rounded-full hover:bg-slate-300 transition-colors;
}
</style>
