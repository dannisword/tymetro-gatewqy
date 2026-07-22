// types/document-config.ts
export type SectionType = "Params" | "Form" | "Search" | "Table" | "Dialog";

export type AnySection = { sectionType: string } & Record<string, any>;

export interface ApiUrl {
  read: string;
  create: string;
  update: string;
  delete: string;
}

export interface Schemas {
  prop: string;
  type: "text" | "number" | "select" | "date" | string;
  label?: string;
  value?: any;
  optionType: string;
  options?: Array<{ label: string; value: any }>;
}
/**
 * 表單選項
 */
export interface FormOptions {
  key?: string;
  colNum: number;
}
/**
 * 表單段落
 */
export interface FormSection {
  sectionType: "Form";
  colNum: number;
  options?: FormOptions;
  dto: Record<string, any>;
  schemas: Schemas[];
}
/**
 * 資料表段落
 */
export interface TableSection {
  sectionType: "Table";
  options?: Record<string, any>;
  actions?: TableActionButton[];
  columns: TableColumn[];
  records?: any[];
}

export interface TableColumn {
  headerName: string;
  field?: string;
  minWidth?: number;
  maxWidth?: number;
  sortable?: boolean;
  filter?: boolean;
  pinned?: "left" | "right";
  editable?: boolean;
  cellRenderer?: string; // e.g. "AGActionButtonRenderer"
  actionButtons?: TableActionButton[];
}

export interface TableActionButton {
  label: string;
  type?: "primary" | "success" | "danger" | "warning" | string;
  icon?: string;
  event: string;
}

export interface ParamsSection {
  sectionType: "Params";
  apiUrl: ApiUrl;
}

export interface SearchSection {
  sectionType: "Search";
  params: Record<string, any>;
  schemas: Schemas[];
}

export interface DialogSection {
  sectionType: "Dialog";
  key: string;
  title: string;
  visible: boolean;
  form?: FormSection;
  table?: TableSection;
}

export interface DocumentConfig {
  templateName: string;
  documentType?: string;
  sections: Array<
    | {
        sectionType: "Params";
        apiUrl: ApiUrl;
      }
    | {
        sectionType: "Form";
        dto: Record<string, any>;
        schemas: Schemas[];
      }
    | {
        sectionType: "Search";
        params: Record<string, any>;
        schemas: Schemas[];
      }
    | {
        sectionType: "Table";
        options?: Record<string, any>;
        actions?: TableActionButton[];
        columns: TableColumn[];
      }
    | {
        sectionType: "Dialog";
        columns: TableColumn[];
      }
  >;
}

export interface ParsedDocument {
  docName: string;
  apiUrl: ApiUrl;
  search: {
    params: Record<string, any> | null;
    schemas: Schemas[] | null;
  } | null;
  form: {
    dto: Record<string, any> | null;
    schemas: Schemas[] | null;
  } | null;
  table: {
    options: Record<string, any> | null;
    actions: TableActionButton[] | null;
    columnDefs: any[] | null;
  } | null;
}
