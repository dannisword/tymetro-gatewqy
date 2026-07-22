<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseButton from '@/components/BaseButton.vue';
import { useAppStore } from '@/store/useAppStore';
import { useAlert } from '@/composables/TLAlter';
import httpOperations from '@/utils/http-operations';
import {
  mdiAccount,
  mdiLockOutline,
  mdiCardAccountDetailsOutline,
  mdiCheckCircleOutline
} from '@mdi/js';
import BaseIcon from '@/components/BaseIcon.vue';

const appStore = useAppStore();
const { TLSuccess, TLError } = useAlert();

const breadcrumbItems = [
  { label: '首頁', to: '/dashboard' },
  { label: '個人資料' }
];

const account = ref('');
const userName = ref('');
const password = ref('');
const confirmPassword = ref('');

onMounted(() => {
  if (appStore.user) {
    account.value = appStore.user.account || '';
    userName.value = appStore.user.userName || '';
  }
});

const isSubmitting = ref(false);

const handleSave = async () => {
  if (!userName.value.trim()) {
    TLError('使用者姓名不能為空');
    return;
  }

  if (password.value || confirmPassword.value) {
    if (password.value !== confirmPassword.value) {
      TLError('兩次輸入的新密碼不一致');
      return;
    }
    if (password.value.length < 4) {
      TLError('密碼長度至少需要 4 個字元');
      return;
    }
  }

  isSubmitting.value = true;
  try {
    const userId = appStore.user.userId || appStore.user.id;
    if (!userId) {
      TLError('找不到當前使用者識別碼');
      return;
    }

    const payload: Record<string, any> = {
      userName: userName.value
    };

    if (password.value) {
      payload.password = password.value;
    }

    const res = await httpOperations.put(`/api/v1/users/${userId}`, payload);
    
    if (res.success !== false) {
      // 更新 Pinia 中的使用者資料
      appStore.user.userName = userName.value;
      
      // 清空密碼欄位
      password.value = '';
      confirmPassword.value = '';
      
      TLSuccess('個人資料修改成功！');
    } else {
      TLError(res.message || '更新失敗');
    }
  } catch (error: any) {
    console.error('Update profile error:', error);
    TLError(error.response?.data?.message || '伺服器連線錯誤');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="w-full pb-24 sm:pb-8">
    
    <!-- Breadcrumb -->
    <div class="w-full mb-6">
      <Breadcrumb :items="breadcrumbItems" />
    </div>

    <!-- Content Area -->
    <div class="w-full px-4 max-w-2xl mx-auto">
      
      <!-- Card Container -->
      <div class="bg-white rounded-3xl shadow-sm p-8 sm:p-10 relative overflow-hidden">
        
        <!-- Header -->
        <div class="flex items-center gap-3 border-b border-slate-100 pb-5 mb-8">
          <div class="w-10 h-10 rounded-full bg-[#f0f7ff] border border-[#e1f0ff] flex items-center justify-center text-[#2a7eb5]">
            <BaseIcon :path="mdiAccount" w="24" h="24" size="24" />
          </div>
          <div>
            <h2 class="text-xl font-bold text-slate-800">帳號資料與密碼變更</h2>
            <p class="text-xs font-semibold text-slate-400 mt-0.5">您可以在此更新您的顯示姓名與系統登入密碼</p>
          </div>
        </div>

        <!-- Form Fields -->
        <div class="space-y-6">
          
          <!-- 帳號 (唯讀) -->
          <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
            <label class="text-sm font-bold text-slate-600 flex items-center gap-1.5 sm:w-32 shrink-0">
              <BaseIcon :path="mdiAccount" w="16" h="16" size="16" class="text-slate-400" />
              登入帳號
            </label>
            <input 
              v-model="account" 
              type="text" 
              disabled 
              class="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-400 font-medium select-none cursor-not-allowed outline-none"
            />
          </div>

          <!-- 使用者名稱 -->
          <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
            <label class="text-sm font-bold text-slate-600 flex items-center gap-1.5 sm:w-32 shrink-0">
              <BaseIcon :path="mdiCardAccountDetailsOutline" w="16" h="16" size="16" class="text-slate-400" />
              使用者姓名
            </label>
            <input 
              v-model="userName" 
              type="text" 
              placeholder="請輸入使用者姓名" 
              class="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
            />
          </div>

          <div class="border-t border-slate-100 my-8 pt-6 space-y-6">
            <h3 class="text-sm font-bold text-[#2a7eb5] tracking-wide mb-4">修改登入密碼</h3>

            <!-- 新密碼 -->
            <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
              <label class="text-sm font-bold text-slate-600 flex items-center gap-1.5 sm:w-32 shrink-0">
                <BaseIcon :path="mdiLockOutline" w="16" h="16" size="16" class="text-slate-400" />
                新密碼
              </label>
              <input 
                v-model="password" 
                type="password" 
                placeholder="若不修改密碼請留空" 
                class="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
              />
            </div>

            <!-- 確認新密碼 -->
            <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
              <label class="text-sm font-bold text-slate-600 flex items-center gap-1.5 sm:w-32 shrink-0">
                <BaseIcon :path="mdiLockOutline" w="16" h="16" size="16" class="text-slate-400" />
                確認新密碼
              </label>
              <input 
                v-model="confirmPassword" 
                type="password" 
                placeholder="請再次輸入新密碼" 
                class="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium focus:border-[#2a7eb5] focus:ring-2 focus:ring-[#2a7eb5]/10 outline-none transition-all"
              />
            </div>
          </div>

        </div>

        <!-- Submit Button -->
        <div class="flex justify-end gap-3 mt-10 border-t border-slate-100 pt-6">
          <BaseButton 
            @click="handleSave"
            :loading="isSubmitting"
            colorClass="bg-[#2a7eb5] text-white hover:bg-[#206796] shadow-sm font-bold px-6 py-2.5 rounded-xl transition-all active:scale-[0.98]"
            icon="mdiCheck"
          >
            儲存修改
          </BaseButton>
        </div>

      </div>

    </div>
  </div>
</template>
