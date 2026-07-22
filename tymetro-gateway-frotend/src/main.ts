import { createApp } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";

import * as ElementPlus from "element-plus";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";

import "gridjs/dist/theme/mermaid.css";
import "element-plus/dist/index.css";
import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";

import "@/style.css";
import App from "@/App.vue";
import router from "@/router/index";
import { injectGuard } from "@/router/Inject-guard";
import { setupLoadingGuard } from "@/router/setup-loading-guard";

import i18n from '@/plugins/i18n'

ModuleRegistry.registerModules([AllCommunityModule]);

const app = createApp(App);
// element plus
app.use(ElementPlus);
// 多國語言
app.use(i18n)
// icon
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}
// store pinia
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);
app.use(pinia);
app.use(router);

setupLoadingGuard(router); // 重載
injectGuard(router); // 路由初始化

import { useMtrStore } from "@/store/useMtrStore";
const mtrStore = useMtrStore(pinia);
mtrStore.loadConfig().finally(() => {
  app.mount("#app");
});
