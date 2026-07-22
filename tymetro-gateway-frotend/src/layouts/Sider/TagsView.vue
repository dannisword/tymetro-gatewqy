<script setup lang="ts">
import { reactive, ref, computed, watch, nextTick } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";

// import { ElScrollbar } from "element-plus";
import { useBasicStore } from "../../store/useBasicStore";
import { routeHandle } from "../../hooks/route-handle";
const route = useRoute();
const router = useRouter();
const { navigation } = routeHandle();
const basicStore = useBasicStore();
const {
  visitedViews
} = storeToRefs(basicStore);
const {
  getVisitedViews,
  delVisitedView,
  delAllVisitedViews,
  delOthersVisitedViews,
} = basicStore;

const state = reactive({
  visible: false,
  top: 0,
  left: 0,
  x: 0,
  y: 0,
  selectedTag: {},
  scrollValue: 0,
});

const containerRef = ref<HTMLDivElement | null>(null);


const scrollLeftNumber = ref(0);


watch(
  () => route.name,
  (val) => {
    state.visible = false;
    if (visitedViews.value && visitedViews.value.length > 0) {
      const lastView = visitedViews.value[visitedViews.value.length - 1];
      if (lastView && lastView.name == val) {
        toCurrentView();
      }
    }
  }
);

const isActive = (param: any) => {
  return route.path === param.path;
};

const isAffix = (tag: any) => {
  return tag.meta.affix;
};

const closeSelectedTag = (view: any) => {
  const views = getVisitedViews;
  const index = views.findIndex((v: any) => v.path === view.path);
  
  delVisitedView(view).then((newViews: any) => {
    if (route.path !== view.path) return;
    
    // 優先選取左側標籤 (index - 1)，若無則選取新的同位置標籤 (現在的 index)，若再無則選取最後一個
    const nextView = newViews[index - 1] || newViews[index] || newViews.at(-1);
    
    if (nextView) {
      router.push({ path: nextView.path, query: nextView.query });
    } else {
      router.push("/");
    }
  });
};

// const toCurrentView = () => {
//   const to =
//     scrollbarRef.value?.wrapRef!.scrollWidth == undefined
//       ? 0
//       : scrollbarRef.value?.wrapRef!.scrollWidth;

//   scrollbarRef.value?.setScrollLeft(to);
// };

const toCurrentView = () => {
    const el = containerRef.value;
    if (!el) return;
    el.scrollLeft = el.scrollWidth; // 捲到最右
};

const toLastView = (view: any) => {
  const views = getVisitedViews;
  // 如果關閉的不是當前頁面，則不需要跳轉
  if (route.path !== view.path) {
    return;
  }

  // 尋找關閉標籤在原列表中的位置（此時 views 已經是刪除後的列表）
  // 我們傾向於跳到最後一個，但如果列表不為空，跳到最後一個其實就是「上一個」或「鄰近的一個」
  const latestView = views.slice(-1)[0];
  
  if (latestView) {
    router.push({ path: latestView.path, query: latestView.query });
  } else {
    // 如果標籤全關了，回首頁
    if (view.name === "Dashboard") {
      router.replace({ path: `/redirect${view.fullPath}` });
    } else {
      router.push("/");
    }
  }
};

const click = (event: any) => {
  state.visible = false;
  if (event == "CANAEL") {
    return;
  }

  if (event == "CLOSE_ALL") {
    delAllVisitedViews();
    navigation("/dashboard");
  }
  if (event == "CLOSE") {
    closeSelectedTag(state.selectedTag);
  }
  if (event == "CLOSE_OTHER") {
    delOthersVisitedViews(state.selectedTag);
    //closeSelectedTag(state.selectedTag);
  }
};

const openMenu = (event: any, tag: any) => {
  state.top = 28;
  state.left = event.x - 160;
  state.x = event.clientX;
  state.y = event.clientY;
  state.visible = true;
  state.selectedTag = tag;
};

const scroll = ({ scrollLeft }: { scrollLeft: any }) => {
  scrollLeftNumber.value = scrollLeft as number;
};
</script>
<template>
    <!-- 頂部水平可捲動 tabs（Tailwind 純手刻） -->
    <div class="relative">
        <div ref="containerRef"
            class="flex w-screen overflow-x-auto no-scrollbar border-b border-b-gray-200 bg-muted pt-3">
            <template v-for="tag in visitedViews" :key="tag.path">
                <button class="group inline-flex items-center px-4 py-1.5 text-sm border-b-2 transition
                 whitespace-nowrap" :class="isActive(tag)
    ? ' bg-primary-500 border-teal-500 text-white rounded-sm'
    : 'text-fg border-transparent hover:bg-gray-200 hover:border-teal-500 hover:text-gray-500'"
                    @click="$router.push({ path: tag.path, query: tag.query })"
                    @contextmenu.prevent="openMenu($event, tag)">
                    <!-- 左側 *（僅 active 顯示） -->
                    <span v-if="isActive(tag)" class="-ml-1 text-white">*</span>
                    <span>{{ tag.meta.title }}</span>

                    <!-- 關閉鈕（只有 affix=true 才顯示；原本邏輯） -->
                    <span v-if="isAffix(tag)" class="material-symbols-outlined text-[18px] opacity-80 hover:opacity-100"
                        @click.stop.prevent="closeSelectedTag(tag)">close</span>
                </button>
            </template>
        </div>
    </div>

    <!-- 右鍵選單 -->
    <ul v-show="state.visible" :style="{ left: state.left + 'px', top: state.top + 'px' }"
        class="absolute z-50 min-w-[140px] rounded-md bg-card text-fg shadow border border-border py-1">
        <li class="px-4 py-2 cursor-pointer hover:bg-muted" @click="click('CANAEL')">取消</li>
        <li class="px-4 py-2 cursor-pointer hover:bg-muted" @click="click('CLOSE_OTHER')">關閉其他</li>
        <li class="px-4 py-2 cursor-pointer hover:bg-muted" @click="click('CLOSE_ALL')">關閉全部</li>
    </ul>
</template>



<style lang="scss" scoped>

/* 隱藏 scrollbar，保留滾動功能 */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;  /* IE & Edge */
  scrollbar-width: none;     /* Firefox */
}

.tags-view-container {
  --tags-view-item-active-background: #4db6ac;
  --tags-view-item-active-border-color: #4db6ac;
  --tags-view-item-active-color: #fff;
  --tags-view-contextmenu-background: #e0e0e0;
  --tags-view-contextmenu-hover-background: #e0e0e0;
  margin-top: -1px;
  height: var(--tag-view-height);
  width: 100%;
  position: relative;
  z-index: 10;
  background: var(--tags-view-background);
  border-bottom: 1px solid var(--tags-view-border-bottom);
  box-shadow: var(--tags-view-box-shadow);
  font-size: 16px;
  .tags-view-wrapper {
    .tags-view-item {
      display: inline-block;
      position: relative;
      cursor: pointer;
      height: 30px;
      line-height: 30px;
      border: 1px solid var(--tags-view-item-border-color);
      color: var(--tags-view-item-color);
      background: var(--tags-view-item-background);
      padding: 0 8px;
      border-radius: 0px;
      
      font-size: 16px;
      &:first-of-type {
        margin-left: 10px;
      }
      &:last-of-type {
        margin-right: 15px;
      }
      &.active {
        background-color: var(--tags-view-item-active-background);
        color: var(--tags-view-item-active-color);
        border-color: var(--tags-view-item-active-border-color);
        &::before {
          content: "*";
          background: var(--tags-view-background);
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          position: relative;
          margin-right: 2px;
        }
      }
    }
  }
  .contextmenu {
    margin: 0;
    background: var(--tags-view-contextmenu-background);
    z-index: 3000;
    position: absolute;
    list-style-type: none;
    padding: 5px 0;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 400;
    color: var(--tags-view-contextmenu-color);
    box-shadow: var(--tags-view-contextmenu-box-shadow);

    li {
      margin: 0;
      padding: 7px 16px;
      cursor: pointer;
      &:hover {
        background: var(--tags-view-contextmenu-hover-background);
      }
    }
  }
}
.scroll-container {
  white-space: nowrap;
  position: relative;
  overflow: hidden;
  width: 100%;
  ::v-deep {
    .el-scrollbar__bar {
      bottom: 0px;
    }
    .el-scrollbar__wrap {
      height: 49px !important;
    }
  }
}

//reset element css of el-icon-close
.tags-view-wrapper {
  .tags-view-item {
    border-radius: 3px;
    .el-icon-close {
      border-radius: 6px;
      width: 12px;
      height: 12px;
      font-size: small;
      transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
      transform-origin: 100% 50%;
      vertical-align: -2px;

      &:hover {
        background-color: var(--tags-view-close-icon-hover-background);
        color: var(--tags-view-close-icon-hover-color);
      }
    }
  }
}
</style>
