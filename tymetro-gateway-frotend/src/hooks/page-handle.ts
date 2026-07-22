import { ref } from "vue";
import { useRoute } from "vue-router";
import { cloneDeep } from "lodash";
import {
  getDocument,
  arrayToObject,
  getCacheOptions,
  objectToArray,
} from "../utils";

import {
  ApiUrl,
  FormSection,
  ParamsSection,
  TableSection,
} from "../types/document-config";
import httpOperations from "../utils/http-operations";
import { useAlert } from "../composables/TLAlter";

const { TLSuccess, TLWarning, TLError } = useAlert();
export type AnySection = { sectionType: string } & Record<string, any>;

export function PageHandle() {
  const route = useRoute();
  const sections = ref<AnySection[]>([] as AnySection[]);

  /**
   * 統一錯誤處理
   */
  function handleError(error: any) {
    console.error("[PageHandle] Error:", error);
    const msg = error?.response?.data?.message || "操作異常，請檢查網路或權限";
    TLError(msg);
  }

  function parseSections(content: unknown): AnySection[] {
    try {
      const v = typeof content === "string" ? JSON.parse(content) : content;
      if (Array.isArray(v)) return v as AnySection[];
      if (v && typeof v === "object" && Array.isArray((v as any).sections)) {
        return (v as any).sections as AnySection[];
      }
    } catch (e) {
      console.error("[PageHandle] JSON 解析失敗", e);
    }
    return [];
  }

  /**
   * 處理 Form 中的下拉選項
   */
  async function formChange(form: FormSection) {
    if (!form.schemas) return;
    for (const schema of form.schemas) {
      if (schema.type === "select" || schema.type === "multiple-select") {
        schema.options = getCacheOptions(schema.optionType);
      }
    }
  }

  /**
   * 取得 API URL 配置
   */
  function getApiUrl(): ApiUrl | undefined {
    const params = getSection(sections.value, "Params") as ParamsSection;
    if (!params || !params.apiUrl) {
      TLWarning("樣板中缺少 Params 或 ApiUrl 配置");
      return undefined;
    }
    const { read, create, update, delete: delPath } = params.apiUrl;
    if (!read || !create || !update || !delPath) {
      TLWarning("樣板 ApiUrl 配置不完整");
      return undefined;
    }
    return params.apiUrl;
  }

  /**
   * 取得特定區塊數據
   */
  const getSection = <T extends AnySection = AnySection>(
    targetSections: AnySection[],
    type: string,
    key?: string | undefined
  ): T | undefined => {
    return targetSections.find((x) => 
      x.sectionType === type && (!key || x.key === key)
    ) as T | undefined;
  };

  /**
   * 載入樣板 sections
   */
  const getSections = async (
    component: string | undefined = undefined
  ): Promise<AnySection[]> => {
    try {
      const name = component || route.name?.toString();
      if (!name) return [];
      
      const response = await getDocument(name);
      if (response?.data?.content) {
        sections.value = parseSections(response.data.content);
        return cloneDeep(sections.value);
      }
    } catch (error) {
      console.error(`[PageHandle] 獲取樣板失敗: ${component}`, error);
    }
    return [];
  };

  /**
   * 初始 Form Schema 數據
   */
  const clearSchemas = async (): Promise<FormSection | null> => {
    const section = getSection(sections.value, "Form") as FormSection;
    if (section) {
      const form = cloneDeep(section);
      await formChange(form);
      // 將 dto 的值拆解回 schemas 的 value
      objectToArray(form.dto || {}, form.schemas);
      return form;
    }
    return null;
  };

  /**
   * 將現有資料分配給 Form Schema
   */
  const assignSchemas = async (data: any): Promise<FormSection | null> => {
    const section = getSection(sections.value, "Form") as FormSection;
    if (section) {
      const form = cloneDeep(section);
      form.dto = cloneDeep(data);
      await formChange(form);
      objectToArray(form.dto, form.schemas);
      return form;
    }
    return null;
  };

  /**
   * 從 Schema 取回 DTO (用於儲存)
   */
  const fetchDto = async (form: FormSection): Promise<any> => {
    if (!form.dto) form.dto = {};
    arrayToObject(form.dto, form.schemas);
    return form.dto;
  };

  /**
   * 集合查詢
   */
  const read = async (table: TableSection) => {
    const apiUrl = getApiUrl();
    if (!apiUrl?.read) return;
    try {
      const response = (await httpOperations.get(apiUrl.read)) as any;
      table.records = response?.data || [];
    } catch (error) {
      handleError(error);
    }
  };

  const get = async (id: number): Promise<any> => {
    const apiUrl = getApiUrl();
    if (!apiUrl?.read) return null;
    try {
      const url = `${apiUrl.read}/${id}`;
      const response = (await httpOperations.get(url)) as any;
      return response?.data;
    } catch (error) {
      handleError(error);
      return null;
    }
  };

  const create = async (dto: any) => {
    const apiUrl = getApiUrl();
    if (!apiUrl?.create) return;
    try {
      const response = (await httpOperations.post(apiUrl.create, dto)) as any;
      TLSuccess(response?.message || "新增成功");
      return response;
    } catch (error) {
      handleError(error);
    }
  };

  const update = async (dto: any) => {
    const apiUrl = getApiUrl();
    if (!apiUrl?.update) return;
    try {
      const url = `${apiUrl.update}/${dto.id}`;
      const response = (await httpOperations.put(url, dto)) as any;
      TLSuccess(response?.message || "更新成功");
      return response;
    } catch (error) {
      handleError(error);
    }
  };

  const del = async (dto: any) => {
    const apiUrl = getApiUrl();
    if (!apiUrl?.delete) return;
    try {
      const url = `${apiUrl.delete}/${dto.id}`;
      const response = (await httpOperations.delete(url)) as any;
      TLSuccess(response?.message || "刪除成功");
      return response;
    } catch (error) {
      handleError(error);
    }
  };

  return {
    getSections,
    getSection,
    clearSchemas,
    assignSchemas,
    fetchDto,
    read,
    get,
    create,
    update,
    del,
  };
}
