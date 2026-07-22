import { defineStore } from "pinia";

/** 支援巢狀 start()/stop()，避免多來源競爭 */
export const useLoadingStore = defineStore("useLoadingStore", {
  state: () => ({
    counter: 0, // >0 表示正在載入
    minShowMs: 200, // 最短顯示時間，避免閃爍
    openedAt: 0,
    timer: 0 as any,
  }),
  getters: {
    // active: (s) => s.counter > 0,
    active: (s) => s.counter > 0 || !!s.timer,
  },
  actions: {
    start() {
      if (this.counter === 0) {
        this.openedAt = Date.now();
      }
      this.counter++;
      // 若有關閉延遲計時器，先清掉
      if (this.timer) {
        clearTimeout(this.timer);
        this.timer = 0;
      }
    },
    stop() {
      if (this.counter === 0) {
        return;
      }
      this.counter--;
      if (this.counter === 0) {
        const elapsed = Date.now() - this.openedAt;
        const remain = Math.max(0, this.minShowMs - elapsed);
        this.timer = setTimeout(() => {
          this.timer = 0;
          // 觸發更新（active 會變 false）
        }, remain);
      }
    },
    /** 直接設定 */
    set(val: boolean) {
      if (val) {
        this.start();
      } else {
        this.counter = 0;
      }
    },
  },
});
