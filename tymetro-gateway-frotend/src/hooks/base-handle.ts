import { reactive, ref } from "vue";
import { isEmptyOrNull } from "../utils";
import { cloneDeep } from "lodash";

export default class BaseHandle {
  apiUrl = ref({} as any);
  sections = reactive<any[]>([]);
  table = reactive({
    options: {} as any,
    records: [] as any[],
    columns: [] as any[],
    actions: [] as any[],
  });

  page = reactive({
    name: "",
    code: "",
    // json parts
    parts: {} as any,
    dc: {} as any,
    id: 0 as any,
    sysOrderNo: {} as any,
    docNo: "" as any,
  });
  pagination = reactive({
    number: 0,
    size: 10,
    totalElements: 0,
    totalPages: 0,
  });
  document = reactive({
    orgId: "",
    docName: "",
    componentName: "",
    version: "",
    content: {} as any,
  });
  path = reactive({} as any);
  search = reactive({
    params: {} as any,
    schemas: [] as any[],
    advanced: [] as any[],
  });
  form = reactive({
    dto: {} as any,
    schemas: [] as any[],
    menus: [] as any[],
    filters: [] as any[],
    width: {} as any,
    layout: {} as any,
    isReadonly: false,
    colNum: 12,
    sections: [] as any[], // 新增：用於存放多個表單段落
  });

  map(data: any) {
    this.sections = cloneDeep(data.sections);
    this.form.sections = []; // 初始化清空

    for (const section of data.sections) {
      switch (section.sectionType) {
        case "Params":
          this.mapParams(section);
          break;
        case "Form":
          this.mapForm(section);
          break;
        case "Search":
          this.mapSearch(section);
          break;
        case "Table":
          this.mapTable(section);
          break;
        default:
          break;
      }
    }
  }
  mapParams(section: any) {
    if (isEmptyOrNull(section.apiUrl)) {
      return;
    }
    if (section.apiUrl) {
      this.apiUrl.value = section.apiUrl;
    }
  }
  mapForm(section: any) {
    // 支援多個 Form 段落
    this.form.sections.push(section);

    if (section.colNum) {
      this.form.colNum = section.colNum;
    }
    if (section.dto) {
      // 這裡採取合併策略，或者保留最後一個 (通常 dto 是共用的)
      this.form.dto = { ...this.form.dto, ...section.dto };
    }
    if (section.schemas) {
      // 這裡為了相容舊版，依然保留單一 schemas 引用，通常是第一個
      if (this.form.schemas.length === 0) {
        this.form.schemas = section.schemas;
      }
    }
  }
  mapSearch(section: any) {
    if (section.params) {
      this.search.params = section.params;
    }
    if (section.schemas) {
      this.search.schemas = section.schemas;
    }
  }
  mapTable(section: any) {
    // this.table.singleRow =
    //   section.singleRow == null ? false : section.singleRow;

    if (section.options) {
      this.table.options = section.options;
    }
    if (section.columns) {
      this.table.columns = section.columns;
    }
    if (section.actions) {
      this.table.actions = section.actions;
    }
  }
  renderForm(f: any) {
    this.form.dto = isEmptyOrNull(f.dto) == true ? null : f.dto;
    this.form.schemas = isEmptyOrNull(f.schemas) == true ? [] : f.schemas;
    this.form.menus = isEmptyOrNull(f.menus) == true ? [] : f.menus;
    this.form.filters = isEmptyOrNull(f.filters) == true ? [] : f.filters;
    this.form.width = isEmptyOrNull(f.width) == true ? [] : f.width;
  }

  /**
   * 動態設定表格欄位的下拉選單選項
   * @param field 欄位名稱
   * @param options 選項清單 [{ label: string, value: any }]
   */
  setColumnOptions(field: string, options: any[]) {
    const column = this.table.columns.find((c: any) => c.field === field);
    if (column) {
      column.type = "select";
      column.options = options;
      column.editable = true;
    }
  }
}
