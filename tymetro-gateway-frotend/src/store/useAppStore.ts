import { defineStore } from 'pinia'
import { getMenus, getOptions } from '@/utils'
import { useGlobalStore } from '@/store/useGlobalStore'
import { useTagsStore } from '@/store/useTagsStore'
import { usePermissionStore } from '@/store/usePermissionStore'
import httpOperations from '@/utils/http-operations'
import { useAuthStore } from '@/store/useAuthStore'

export const useAppStore = defineStore('useAppStore', {
  state: () => ({
    lang: 'zh-tw',
    menus: [] as any[],
    user: {} as any,
    options: {} as any,
    sysInfo: {} as any,
    isAuthenticated: false,
    activeCarId: 1,
  }),
  getters: {
    currentLang: (state) => state.lang,
    isAuthenticated: () => useAuthStore().isAuthenticated,
  },
  actions: {
    setActiveCarId(id: number) {
      this.activeCarId = id;
    },
    /**
     * 登入處理
     */
    async login(data: any) {
      if (!data) {
        return
      }
      this.user = data
      this.user.accessToken = "";
      useAuthStore().setToken(data.accessToken)

    },

    setSysInfo(sysInfo: any) {
      this.sysInfo = sysInfo
    },

    /**
     * 登出
     */
    logout() {
      httpOperations.post('/api/v1/users/logout').catch(() => { })
      useTagsStore().closeAll()
      this.clearLocalData()
      useAuthStore().clearToken()
      this.user = {}
      this.menus = []
    },

    /**
     * 清除本地資料
     */
    clearLocalData() {
      localStorage.clear()
    },

    setDataCenter(dc: any) {
      // reserved for future use
    },
  },
  persist: {
    key: 'useAppStore',
    storage: localStorage,
    paths: ['lang', 'menus', 'user', 'options', 'sysInfo', 'activeCarId'],
  },
})
