// utils/parse-document.ts
import dayjs from "dayjs";
import type {
  DocumentConfig,
  ParsedDocument,
  TableActionButton,
  TableColumn,
  ApiUrl,
  Schemas,
} from "../types/document-config";

/**
 * 建立「項次」欄
 * @returns 
 */
function buildIndexCol(): any {
  return {
    headerName: "項次",
    maxWidth: 60,
    valueGetter: (params: any) => (params.node ? params.node.rowIndex + 1 : ""),
    sortable: false,
    filter: false,
    pinned: "left",
  };
}

/**
 * 日期欄位預設格式化
 * @param col 
 * @returns 
 */
function withDateFormatter(col: TableColumn): any {
  const isDateLike = !!col.field && /(date|time|at)$/i.test(col.field); // e.g. updatedAt / createdAt / time / date
  if (!isDateLike) return col;

  return {
    ...col,
    valueFormatter: (p: any) => {
      const v = p.value;
      if (!v) return "";
      const d = dayjs(v);
      return d.isValid() ? d.format("YYYY-MM-DD HH:mm:ss") : v;
    },
  };
}

/**
 * 將 JSON 列定義轉為 ag-grid columnDef
 * @param columns 
 * @param actionsOnRight 
 * @returns 
 */
function buildColumnDefs(columns: TableColumn[], actionsOnRight = true): any[] {
  const defs: any[] = [];

  // 1) 項次欄固定放最左
  defs.push(buildIndexCol());

  // 2) 其他欄
  for (const col of columns) {
    // 操作欄留到最後處理
    if (col.cellRenderer === "AGActionButtonRenderer") continue;

    const def = withDateFormatter({
      ...col,
      // ag-grid key 對應：headerName/field/minWidth/maxWidth/sortable/filter/pinned...
    });

    defs.push(def);
  }

  // 3) 操作欄，如果有
  const actionCol = columns.find(
    (c) => c.cellRenderer === "AGActionButtonRenderer"
  );
  if (actionCol) {
    defs.push({
      headerName: actionCol.headerName ?? "操作",
      field: actionCol.field ?? "action",
      pinned: "right",
      editable: false,
      maxWidth: actionCol.maxWidth ?? 200,
      cellRenderer: (params: any) => {
        // 這裡交給外部自訂元件；此處只保留欄位定義
        // 你在元件中用 frameworkComponents 或 cellRendererSelector 指向 Vue renderer
        return "";
      },
      cellRendererParams: {
        actionButtons: actionCol.actionButtons ?? [],
      },
    });
  }

  // 4) 如果需要把項次放左側固定，已經在最前面
  return defs;
}

/**
 * 主轉換：將 DocumentConfig 解析成可直接塞進元件的資料
 * @param cfg 
 * @returns 
 */
export function parseDocumentConfig(cfg: DocumentConfig): ParsedDocument {
  const docName = cfg.templateName;

  // 找出三個區段
  const paramsSec = cfg.sections.find(
    (s: any) => s.sectionType === "Params"
  ) as { sectionType: "Params"; apiUrl: ApiUrl } | undefined;

  const searchSec = cfg.sections.find(
    (s: any) => s.sectionType === "Search"
  ) as
    | { sectionType: "Search"; params: Record<string, any>; schemas: Schemas[] }
    | undefined;

  const tableSec = cfg.sections.find((s: any) => s.sectionType === "Table") as
    | {
        sectionType: "Table";
        options?: Record<string, any>;
        actions?: TableActionButton[];
        columns: TableColumn[];
      }
    | undefined;

  if (!paramsSec?.apiUrl)
    throw new Error("Invalid config: missing Params.apiUrl");
  if (!searchSec) throw new Error("Invalid config: missing Search section");
  if (!tableSec?.columns?.length)
    throw new Error("Invalid config: missing Table.columns");

  // 組 columnDefs
  const columnDefs = buildColumnDefs(tableSec.columns, true);

  return {
    docName,
    apiUrl: paramsSec.apiUrl,
    search: {
      params: { ...searchSec.params },
      schemas: searchSec.schemas ?? [],
    },
    table: {
      options: { ...(tableSec.options ?? {}) },
      actions: tableSec.actions ?? [],
      columnDefs,
    },
    form: {
      dto: { ...searchSec.params },
      schemas: searchSec.schemas ?? [],
    },
  };
}
