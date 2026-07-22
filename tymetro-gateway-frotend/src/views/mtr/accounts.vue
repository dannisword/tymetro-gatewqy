<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import { useAlert } from '@/composables/TLAlter';
import httpOperations from '@/utils/http-operations';
import {
  mdiAccountOutline,
  mdiAccountPlus,
  mdiPencil,
  mdiMagnify,
  mdiClose,
  mdiRefresh
} from '@mdi/js';

import AgGridView2 from '@/components/AgGridView2.vue';
import { GridOptions } from 'ag-grid-community';

const { TLSuccess, TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '功能選單', to: '/mtr/tile-menus' },
  { label: '帳號資料' }
];

const gridOptions: GridOptions = {
  rowSelection: 'single',
};

const pagination = ref({
  number: 0,
  size: 15,
  totalElements: 0,
  totalPages: 0,
});

const gridColumns = ref([
  { headerName: 'ID', field: 'id', flex: 0.5 },
  { headerName: '帳號', field: 'account' },
  { headerName: '使用者姓名', field: 'userName' },
  {
    headerName: '啟用狀態',
    field: 'isActive',
    cellRenderer: (p: any) => {
      const active = p.value;
      return active 
        ? `<span class="px-2.5 py-1 rounded-full text-xs font-bold shadow-xs inline-block bg-emerald-50 text-emerald-700 border border-emerald-200/50">已啟用</span>`
        : `<span class="px-2.5 py-1 rounded-full text-xs font-bold shadow-xs inline-block bg-slate-100 text-slate-500 border border-slate-200/50">停用中</span>`;
    }
  },
  { headerName: '最後異動時間', field: 'createTime', format: 'datetime' },
  {
    headerName: '操作',
    field: 'actions',
    cellRenderer: 'AGActionButtonRenderer',
    actionButtons: [
      { label: '編輯', event: 'edit', icon: 'mdiPencil', iconOnly: true },
    ]
  }
]);

const onGridActionClick = ({ action, data }: any) => {
  if (action.event === 'edit') {
    openEditModal(data);
  } else if (action.event === 'delete') {
    deleteUser(data);
  }
};

interface UserItem {
  id: number;
  account: string;
  userName: string;
  isActive: boolean;
  createTime?: string;
  orgId: number;
}

const users = ref<UserItem[]>([]);
const total = ref(0);
const loading = ref(false);

// 搜尋關鍵字
const searchKeyword = ref('');

const fetchUsers = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      pageIndex: pagination.value.number,
      pageSize: pagination.value.size,
      propertyName: 'id',
      order: 'DESC'
    };
    if (searchKeyword.value.trim()) {
      params.keyword = searchKeyword.value.trim();
    }

    const res = await httpOperations.get<any>('/api/v1/users', params);
    if (res && res.data) {
      users.value = res.data.source || [];
      const totalCount = res.data.total || 0;
      total.value = totalCount;
      pagination.value.totalElements = totalCount;
      pagination.value.totalPages = Math.ceil(totalCount / pagination.value.size);
    }
  } catch (error) {
    console.error('Fetch users error:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchUsers();
});

const handleSearch = () => {
  pagination.value.number = 0;
  fetchUsers();
};

const handleReset = () => {
  searchKeyword.value = '';
  pagination.value.number = 0;
  fetchUsers();
};

const handlePaginationChange = ({ page, pageSize }: { page: number; pageSize: number }) => {
  pagination.value.number = page;
  pagination.value.size = pageSize;
  fetchUsers();
};

// 新增/修改 Modal 狀態
const showModal = ref(false);
const isEdit = ref(false);
const modalTitle = ref('');

// 表單資料
const formId = ref<number | null>(null);
const formAccount = ref('');
const formUserName = ref('');
const formPassword = ref('');
const formConfirmPassword = ref('');
const formIsActive = ref(true);

const openCreateModal = () => {
  isEdit.value = false;
  modalTitle.value = '新增使用者帳號';
  formId.value = null;
  formAccount.value = '';
  formUserName.value = '';
  formPassword.value = '';
  formConfirmPassword.value = '';
  formIsActive.value = true;
  showModal.value = true;
};

const openEditModal = (user: UserItem) => {
  isEdit.value = true;
  modalTitle.value = '編輯使用者帳號';
  formId.value = user.id;
  formAccount.value = user.account;
  formUserName.value = user.userName;
  formPassword.value = '';
  formConfirmPassword.value = '';
  formIsActive.value = user.isActive;
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const saveUser = async () => {
  if (!formAccount.value.trim()) {
    TLError('登入帳號不能為空');
    return;
  }
  if (!formUserName.value.trim()) {
    TLError('使用者姓名不能為空');
    return;
  }

  if (!isEdit.value && !formPassword.value) {
    TLError('密碼不能為空');
    return;
  }

  if (formPassword.value || formConfirmPassword.value) {
    if (formPassword.value !== formConfirmPassword.value) {
      TLError('兩次輸入的密碼不一致');
      return;
    }
    if (formPassword.value.length < 4) {
      TLError('密碼長度至少需要 4 個字元');
      return;
    }
  }

  try {
    if (isEdit.value && formId.value !== null) {
      const payload: Record<string, any> = {
        userName: formUserName.value,
        isActive: formIsActive.value
      };
      if (formPassword.value) {
        payload.password = formPassword.value;
      }
      await httpOperations.put(`/api/v1/users/${formId.value}`, payload);
      TLSuccess('更新使用者成功');
    } else {
      const payload = {
        account: formAccount.value.trim(),
        userName: formUserName.value.trim(),
        password: formPassword.value,
        isActive: formIsActive.value,
        orgId: 1 // 預設帶入第一組織項目
      };
      await httpOperations.post('/api/v1/users/register', payload);
      TLSuccess('新增使用者成功');
    }
    closeModal();
    fetchUsers();
  } catch (error: any) {
    console.error('Save user error:', error);
    TLError(error.response?.data?.message || '操作失敗，請重試');
  }
};

const deleteUser = async (user: UserItem) => {
  if (confirm(`確定要刪除帳號 [${user.account}] 嗎？`)) {
    try {
      await httpOperations.delete(`/api/v1/users/${user.id}`);
      TLSuccess('刪除使用者成功');
      fetchUsers();
    } catch (error: any) {
      console.error('Delete user error:', error);
      TLError(error.response?.data?.message || '刪除失敗');
    }
  }
};
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    
    <!-- Breadcrumb -->
    <div class="w-full mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <!-- 內容區 -->
    <div class="w-full max-w-[1600px] mx-auto space-y-6">

      <!-- 搜尋過濾條件 -->
      <div class="bg-white rounded-2xl shadow-xs flex flex-col md:flex-row gap-3 items-end">
        <div class="w-full">
          <div class="flex flex-col gap-1">
            <div class="relative">
              <input 
                v-model="searchKeyword"
                type="text" 
                placeholder="請輸入帳號或姓名關鍵字..." 
                class="w-full pl-9 pr-8 py-1.5 rounded-lg border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
                @keyup.enter="handleSearch"
              />
              <BaseIcon :path="mdiMagnify" w="16" h="16" size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <button
                v-if="searchKeyword"
                @click="handleReset"
                type="button"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                title="清除"
              >
                <BaseIcon :path="mdiClose" w="16" h="16" size="16" />
              </button>
            </div>
          </div>
        </div>
        <div class="flex gap-2 w-full md:w-auto shrink-0 justify-end">
          <BaseButton 
            @click="handleReset"
            colorClass="bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 shadow-xs p-1.5 rounded-lg"
            :icon="mdiRefresh"
            :iconOnly="true"
            title="重置"
          />
        </div>
      </div>

      <!-- 資料表與操作 -->
      <div class="bg-white rounded-3xl shadow-sm">
        
        <!-- 表格頂端操作 -->
        <div class="flex justify-between items-center">
          <h3 class="text-slate-800 font-extrabold text-lg flex items-center gap-2">
            <BaseIcon :path="mdiAccountOutline" w="20" h="20" size="20" class="text-[#2a7eb5]" />
            帳號列表 (共 {{ total }} 筆)
          </h3>
        </div>

        <!-- 數據表格 -->
        <div class="h-[500px] border border-slate-100 rounded-2xl overflow-hidden">
          <AgGridView2
            :options="gridOptions"
            :columns="gridColumns"
            :records="users"
            :pagination="pagination"
            @grid-action-click="onGridActionClick"
            @pagination-change="handlePaginationChange"
          />
        </div>
      </div>

    </div>

    <!-- 新增 / 修改彈窗 -->
    <div 
      v-if="showModal" 
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4"
    >
      <div 
        class="bg-white rounded-3xl border border-slate-200/60 shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-150"
      >
        <!-- Modal Header -->
        <div class="flex justify-between items-center bg-[#2a7eb5] text-white px-6 py-4.5">
          <h3 class="font-extrabold text-base tracking-wide flex items-center gap-2">
            <BaseIcon :path="isEdit ? mdiPencil : mdiAccountPlus" w="20" h="20" size="20" />
            {{ modalTitle }}
          </h3>
          <button @click="closeModal" class="text-white/80 hover:text-white transition-colors">
            <BaseIcon :path="mdiClose" w="20" h="20" size="20" />
          </button>
        </div>

        <!-- Modal Body -->
        <div class="p-6 space-y-5">
          
          <!-- 帳號 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              登入帳號 <span v-if="!isEdit" class="text-red-500">*</span>
            </label>
            <input 
              v-model="formAccount" 
              type="text" 
              :disabled="isEdit"
              placeholder="請輸入英文或數字帳號" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed"
            />
          </div>

          <!-- 使用者姓名 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              使用者姓名 <span class="text-red-500">*</span>
            </label>
            <input 
              v-model="formUserName" 
              type="text" 
              placeholder="請輸入真實姓名或顯示稱呼" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 密碼 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              登入密碼 <span v-if="!isEdit" class="text-red-500">*</span>
            </label>
            <input 
              v-model="formPassword" 
              type="password" 
              :placeholder="isEdit ? '若不修改密碼請留空' : '請輸入密碼'" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 確認密碼 -->
          <div class="flex flex-col gap-1.5">
            <label class="text-sm font-bold text-slate-600">
              確認密碼 <span v-if="!isEdit" class="text-red-500">*</span>
            </label>
            <input 
              v-model="formConfirmPassword" 
              type="password" 
              placeholder="請再次輸入密碼以確認" 
              class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <!-- 是否啟用 -->
          <div class="flex items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100">
            <input 
              id="formIsActive"
              v-model="formIsActive" 
              type="checkbox"
              class="w-4 h-4 rounded text-[#2a7eb5] border-slate-300 focus:ring-[#2a7eb5] cursor-pointer"
            />
            <label for="formIsActive" class="text-sm font-bold text-slate-600 cursor-pointer select-none">
              啟用此帳號 (若不啟用，該帳號將無法登入系統)
            </label>
          </div>

        </div>

        <!-- Modal Footer -->
        <div class="flex justify-end gap-2 px-6 py-4 border-t border-slate-100 bg-slate-50">
          <BaseButton 
            @click="closeModal"
            colorClass="bg-white border border-slate-300 text-slate-600 hover:bg-slate-50 px-4 py-2 rounded-xl"
          >
            取消
          </BaseButton>
          <BaseButton 
            @click="saveUser"
            colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm px-5 py-2 rounded-xl"
          >
            確定儲存
          </BaseButton>
        </div>

      </div>
    </div>

  </div>
</template>


