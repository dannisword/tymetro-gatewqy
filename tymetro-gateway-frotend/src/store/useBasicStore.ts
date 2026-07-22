import { defineStore } from "pinia";

export const useBasicStore = defineStore("useBasicStore", {
  state: () => {
    return {
      // 標籤資料
      visitedViews: Array<any>(),
      // keep alive cachedViews
      cachedViews: new Array<string>(),
    };
  },
  getters: {
    getVisitedViews(state) {
      return state.visitedViews;
    },
    getCachedViews(): string[] {
      return Array.from(this.cachedViews);
    },
  },
  actions: {
    /**
     *
     * @param route
     */
    addVisitedView(route: any) {
      this.$patch((state) => {
        const fullPath = route.fullPath;
        // Add to visited views if not already present
        if (!state.visitedViews.some((v: any) => v.path === fullPath)) {
          if (route.params.docNo !== undefined) {
            route.meta.title = route.params.docNo;
          }
          const tagViwe = {
            name: route.name,
            path: fullPath,
            query: route.query,
            meta: route.meta,
          };
          state.visitedViews.push(tagViwe);
        }

        // Add to cached views if not already present (Independent check)
        if (!state.cachedViews.includes(fullPath)) {
          state.cachedViews.push(fullPath);
        }
      });
    },
    delVisitedView(view: any) {
      return new Promise((resolve) => {
        this.$patch((state: any) => {
          const key = view.fullPath || view.path;
          //匹配 key 元素将其删除
          for (const [i, v] of state.visitedViews.entries()) {
            if (v.path === key) {
              state.visitedViews.splice(i, 1);
              break;
            }
          }
          const index = state.cachedViews.indexOf(key);
          if (index > -1) {
            state.cachedViews.splice(index, 1);
          }
          resolve([...state.visitedViews]);
        });
      });
    },
    delOthersVisitedViews(view: any) {
      this.$patch((state: any) => {
        const key = view.fullPath || view.path;
        state.visitedViews = state.visitedViews.filter((x: any) => {
          return x.meta.affix == false || x.path === key;
        });
        state.cachedViews = state.cachedViews.filter(
          (x: any) => x == key,
        );
      });
    },
    delAllVisitedViews() {
      const view = this.visitedViews.find((x) => x.name == "Dashboard");
      const path = view ? view.path : '/dashboard';
      this.visitedViews = this.visitedViews.filter((x) => x.path == path);
      this.cachedViews = this.cachedViews.filter((x) => x == path);
    },
  },
  persist: {
    key: "useBasicStore",
    storage: localStorage,
  },
});
