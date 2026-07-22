import { createI18n, type I18n } from "vue-i18n";
import { getActivePinia } from "pinia";
import { useLocaleStore } from "@/store/useLocaleStore";
let getStore: (() => ReturnType<typeof useLocaleStore>) | null = null;
export function bindLocaleStore(fn: () => ReturnType<typeof useLocaleStore>) {
  getStore = fn;
}

// 兩種缺字顯示策略（二選一）
const DEV_PLACEHOLDER = (key: string) => `${key}`; // 開發環境辨識用

import zhTw from "../assets/languages/zh-tw.json";
import en from "../assets/languages/zh-en.json";

import element_zh_tw from "element-plus/es/locale/lang/zh-tw";
import element_en from "element-plus/es/locale/lang/en";

import { LangType } from "@/utils/enums/lang-type";
const messages = {
  en_US: {
    ...en,
    ...element_en,
  },
  zh_TW: {
    ...zhTw,
    ...element_zh_tw,
  },
};
type MessageSchema = typeof zhTw;

const i18nInstance = createI18n({
  legacy: false,
  locale: LangType.ZH,
  fallbackLocale: LangType.ZH,
  globalInjection: true,
  messages: messages,
  silentTranslationWarn: true,
  missing(locale, key) {
    const store = getStore?.();
    const dict = store?.dict(String(locale)) ?? {};
    // 1) 先嘗試用 store.langs 補值（不發 API）
    if (key in dict) return dict[key as keyof typeof dict] as string;

    // 2) 找不到就記錄缺字（純記錄）
    store?.addMissing(String(locale), String(key));

    return DEV_PLACEHOLDER(String(key));
  },
}) as I18n;

export default i18nInstance;
//export const i18nGlobal = i18nInstance.global; // Export the global instance

export function appendPackFlat(locale: string, pack: Record<string, string>) {
  const curr =
    (i18nInstance.global.getLocaleMessage(locale) as Record<string, string>) ??
    {};
  i18nInstance.global.setLocaleMessage(locale, { ...curr, ...pack }); // 新值覆蓋舊值
}
export function appendPackNested(locale: string, pack: Record<string, any>) {
  i18nInstance.global.mergeLocaleMessage(locale, pack); // 深合併，新值覆蓋舊值
}
