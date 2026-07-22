import { defineStore } from "pinia";

export const useGlobalStore = defineStore("useGlobalStore", {
  state: () => {
    return {
      //  下拉選單
      options: Array<any>(),
    };
  },
  getters: {
    // 💡 修正點：直接使用 state 參數，不要混合使用 this
    getOptions: (state) => state.options,

    // 如果需要處理邏輯的範例
    optionCount: (state) => state.options.length,
  },
  actions: {
    setOptions(options: any) {
      if (options) {
        this.options = options;
      }
    },
  },
  persist: {
    key: "useGlobalStore", // 自訂儲存 key（可選）
    storage: localStorage, // 默認 localStorage
  },
});
