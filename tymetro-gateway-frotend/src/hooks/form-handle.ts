import { ref, computed } from "vue";
import { DocumentHandle } from "./document-handle";
import { type AnySection } from "../types/document-config";

/**
 * 專門處理配置驅動表單佈局的 Hook
 * 內部引用 DocumentHandle，整合資料與佈局邏輯
 */
export function FormHandle() {
  // 引用資料處理 Hook
  const docHandle = DocumentHandle();
  const { instance } = docHandle;

  // 記錄當前啟用的頁籤名稱
  const activeTab = ref("");

  /**
   * 所有表單段落 (sectionType === 'Form')
   */
  const formSections = computed(() => {
    return (instance.form.sections || []) as AnySection[];
  });

  /**
   * 頂部或獨立的區塊 (預設或 layoutType === 'collapse')
   */
  const accordionSections = computed(() => {
    return formSections.value.filter(
      (s) => !s.layoutType || s.layoutType === "collapse"
    );
  });

  /**
   * 標籤頁區塊 (layoutType === 'tab')
   */
  const tabSections = computed(() => {
    return formSections.value.filter((s) => s.layoutType === "tab");
  });

  /**
   * 初始化佈局設定
   */
  const initLayout = () => {
    if (tabSections.value.length > 0) {
      activeTab.value = tabSections.value[0].title;
    }
  };

  /**
   * 驗證所有子表單
   */
  const validateAll = async (formRefs: any[]) => {
    let hasError = false;
    for (const fRef of formRefs) {
      if (fRef && typeof fRef.validate === "function") {
        const isInvalid = await fRef.validate(); // ElFormCustom 回傳 true 代表有錯誤
        if (isInvalid) {
          hasError = true;
        }
      }
    }
    return !hasError; // 全部沒錯誤才回傳 true (代表 Valid)
  };

  return {
    ...docHandle, // 整合所有 DocumentHandle 的方法 (setData, update, loadDocument...)
    activeTab,
    formSections,
    accordionSections,
    tabSections,
    initLayout,
    validateAll,
  };
}
