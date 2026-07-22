import { useRouter, useRoute } from "vue-router";
import { useTagsStore } from "@/store/useTagsStore";

export function routeHandle() {
  const router = useRouter();
  const route = useRoute();
  const appRoutes = Array<any>();

  const params = () => {
    return route.params;
  };

  const pageName = () => {
    return route.name?.toString();
  };
  /**
   * 重定位
   * @param url
   */
  const redirect = (url: any) => {
    const redirectUrl = route.query && route.query.redirect;
  };
  /**
   * 導覽頁面
   * @param url
   * @param title 可選，導航後設定 TagView 名稱
   */
  const navigation = (url: any, title?: string) => {
    const path = `${url}`;
    router.push({ path: path });
    if (title) {
      const tagsStore = useTagsStore();
      // 延遲一下確保路徑已經被 addByRoute 加入 tags
      setTimeout(() => {
        tagsStore.updateTitle(path, title);
      }, 100);
    }
  };

  /**
   * 改變目前頁面在 TagView (分頁欄) 的名稱
   * @param title 新名稱
   */
  const setTagTitle = (title: string) => {
    const tagsStore = useTagsStore();
    tagsStore.updateTitle(route.fullPath, title);
  };
  /**
   *
   * @returns
   */
  const currentRouteValue = () => {
    //  route 全部
    return router.currentRoute;
  };
  const addViews = () => {
    appRoutes.push(router.currentRoute.value.meta);
  };

  const getAllViews = () => {
    const data = localStorage.getItem("app-view");
    if (data == null) {
      return data;
    }
    return JSON.parse(data);
  };
  return {
    redirect,
    navigation,
    setTagTitle,
    currentRouteValue,
    getAllViews,
    addViews,
    route,
    pageName,
    params,
  };
}
