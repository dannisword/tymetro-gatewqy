<script setup lang="ts">
import { AgGridVue } from "ag-grid-vue3";
import { AG_GRID_LOCALE_TW } from "../assets/languages/ag-tw";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import customParseFormat from "dayjs/plugin/customParseFormat";
import AGTagCell from "../components/AGTagCell.vue";
import AGActionButtonRenderer from "../components/AGActionButtonRenderer.vue";
import {
  ColDef,
  GridApi,
  GridOptions,
  CellValueChangedEvent,
  RowSelectionOptions,
  ValueFormatterParams,
} from "ag-grid-community";
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(customParseFormat);
type FormatFn = (value: any, p: ValueFormatterParams) => string;
const { t, locale } = useI18n();
const gridApi = shallowRef<GridApi | null>(null);
const getRowId = (p: any) => String(p.data.id);

const props = defineProps({
  defaultColumns: { type: Object as PropType<any[]>, default: () => [] },
  options: { type: Object as PropType<GridOptions> },
  columns: { type: Array as PropType<any[]>, default: () => [] },
  records: { type: Array as PropType<any[]>, default: () => [] },
  actions: { type: Array as PropType<any[]>, default: () => [] },
  //custom: { type: Object as PropType<any> }, // 自設
  // singleRow: { type: Boolean, default: false },
  //actionsButtons: { type: Array as PropType<any[]>, default: () => [] },
  pagination: { type: Object, default: null },
});

const emit = defineEmits<{
  (e: "selection-changed", data: any[]): void;
  (e: "grid-action-click", payload: { action: any; data: any }): void;
  (e: "action-click", data: any): void;
  (e: "update:records", records: any[]): void;
  (e: "pagination-change", payload: { page: number; pageSize: number }): void;
  (e: "columns-reset", columns: any[]): void;
}>();

const baseGridOptions = computed<GridOptions>(() => ({
  defaultColDef: {
    resizable: true,
    sortable: true,
    filter: true,
    suppressMovable: false,
  },
  suppressMovableColumns: false,
  rowSelection: "single",
  animateRows: false,
  pagination: false,
}));

const rowSelection = ref<RowSelectionOptions>({
  mode: "singleRow",
});

const defaultColDef = ref<ColDef>({
  sortable: true,
  filter: true,
  resizable: true,
  suppressMovable: false,

  flex: 1,
  minWidth: 100,
  floatingFilter: false,
  editable: false,
});

watch(
  () => props.records,
  async (records) => {
    if (records) {
      syncSelectionFromData(records);
    }
  },
);
watch(
  () => props.options,
  (value) => {
    if (value) {
      // rowSelection.value.mode =
      //   value.singleRow == true ? "singleRow" : "multiRow";
    }
  },
);

async function syncSelectionFromData(records: any) {
  if (!gridApi.value) return;
  await nextTick();

  gridApi.value.forEachNode((node: any) => {
    const row = records.find((x: any) => x.id == node.data.id);
    if (row) {
      node.setSelected(row.isSelected);
    }
  });
}

//語系
const localeText = ref<{ [key: string]: string }>(AG_GRID_LOCALE_TW);

/**
 *  checkBox 勾選
 * @param event
 */
const onSelectionChanged = (event: any) => {
  // 處理勾選資料
  const nodes = gridApi.value?.getSelectedNodes();

  const selectedIds = nodes?.map((n: any) => n.data.id);
  const selectedIdSet = new Set(selectedIds?.map(String));

  const newRecords = props.records.map((r: any) => ({
    ...r,
    isSelected: selectedIdSet.has(String(r.id)),
  }));
  emit("update:records", newRecords);

  if (nodes) {
    const selectedNodes = nodes.map((n: any) => n.data);
    emit("selection-changed", selectedNodes);
  }
};

const onFilterChanged = (params: any) => {
  console.log(params);
};
const onCellValueChanged = (event: CellValueChangedEvent) => {
  console.log(event);
};
const onGridReady = (params: any) => {
  gridApi.value = params.api;
  params.api.sizeColumnsToFit();
};
function parseToDayjs(
  raw: any,
  opts: { input?: "utc" | "local"; useTz?: boolean; tz?: string },
) {
  const { input = "local", useTz = false, tz } = opts || {};
  if (raw == null || raw === "") {
    return null;
  }
  // 1) 先依 input 來源解析
  let d = input === "utc" ? dayjs.utc(raw) : dayjs(raw);

  // 2) 若指定時區，轉換到該時區觀看
  if (useTz) {
    const zone = tz || "UTC";
    // 注意：如果 input 是 UTC，先 utc() 再 tz()
    d = (input === "utc" ? dayjs.utc(raw) : dayjs(raw)).tz(zone);
  }
  return d;
}
function buildValueFormatter(
  column: any,
): ColDef["valueFormatter"] | undefined {
  const fmt = column?.format;
  const locale = column?.locale ?? "zh-TW";
  const timeZone = column?.timeZone; // 若不指定，就用瀏覽器時區
  // 1.若是自訂函式：直接用
  if (typeof fmt === "function") {
    const fn = fmt as FormatFn;
    return (p) => fn(p.value, p);
  }

  if (typeof fmt === "string") {
    const [kind, arg] = fmt.split(":"); // e.g. "date:short", "currency:TWD"

    // --- 統一使用 dayjs 處理日期相關格式 ---
    const dateTypes: Record<string, string> = {
      date: "YYYY-MM-DD",
      datetime: "YYYY-MM-DD HH:mm:ss",
      time: "HH:mm:ss",
    };

    if (kind.startsWith("dayjs") || dateTypes[kind]) {
      const isTz = kind.includes(".tz");
      // 優先使用 arg (e.g. date:YYYY/MM) 或 映射表格式，最後預設 YYYY-MM-DD
      const pattern = arg || dateTypes[kind] || "YYYY-MM-DD";
      const tz = timeZone;
      const input = (column?.input ?? "local") as "utc" | "local";

      return (p) => {
        const d = parseToDayjs(p.value, { input, useTz: isTz || !!tz, tz });
        return d ? d.locale(locale).format(pattern) : "";
      };
    }

    // --- 數字 ---
    if (kind === "number") {
      const maximumFractionDigits = Number(arg ?? 2);
      const nf = new Intl.NumberFormat(locale, {
        maximumFractionDigits: isNaN(maximumFractionDigits)
          ? 2
          : maximumFractionDigits,
      });
      return (p) => {
        const n = Number(p.value);
        if (isNaN(n)) {
          return "";
        }
        return nf.format(n);
      };
    }

    // --- 貨幣 ---
    if (kind === "currency") {
      const currency = arg ?? "TWD";
      const nf = new Intl.NumberFormat(locale, {
        style: "currency",
        currency,
        maximumFractionDigits: 2,
      });
      return (p) => {
        const n = Number(p.value);
        if (isNaN(n)) {
          return "";
        }
        return nf.format(n);
      };
    }

    // --- 百分比 ---
    if (kind === "percent") {
      const digits = Number(arg ?? 0);
      const nf = new Intl.NumberFormat(locale, {
        style: "percent",
        maximumFractionDigits: isNaN(digits) ? 0 : digits,
      });
      return (p) => {
        const n = Number(p.value);
        if (isNaN(n)) {
          return "";
        }
        return nf.format(n);
      };
    }
  }

  // 沒有 format 就不處理
  return undefined;
}
// 自動加上操作欄與佈局修正
const computedColumnDefs = computed(() => {
  // 1. 將欄位分為「一般欄位」與「操作欄位」
  const normalCols = props.columns.filter(
    (c: any) => c.field !== "actions" && c.cellRenderer !== "AGActionButtonRenderer"
  );
  const actionCols = props.columns.filter(
    (c: any) => c.field === "actions" || c.cellRenderer === "AGActionButtonRenderer"
  );

  // 2. 重新組合，確保操作欄始終在最後面
  const sortedCols = [...normalCols, ...actionCols];

  return sortedCols.map((column: any) => {
    const base: ColDef = { ...column };
    
    // 檢查是否為操作欄位
    const isAction = column.field === "actions" || column.cellRenderer === "AGActionButtonRenderer";

    // 多國翻譯
    base.headerName = t(base.headerName ?? "");

    if (isAction) {
      base.pinned = "right"; // 固定在最右側
      base.lockPosition = "right"; // 禁止拖拉改變位置
      base.sortable = false; // 操作欄通常不需要排序
      base.filter = false;   // 操作欄不需要過濾
      base.suppressMovable = true;
      base.maxWidth = base.maxWidth || 200; // 避免操作欄被拉得太寬
    }

    if (column.filter == true && !isAction) {
      base.filterParams = (params: any) => {
        console.log(params.colDef);
      };
    }
    // --- 類型專屬渲染/編輯器處理 ---
    switch (column.type) {
      case "checkbox":      
        base.cellRenderer = "agCheckboxCellRenderer";
        base.cellRendererParams = {
          disabled: column.readOnly === true || column.editable !== true
        };
        
        if (column.editable === true) {
          base.editable = true;
          base.cellEditor = "agCheckboxCellEditor";
        }
      break;

      case "select":
        // 無論是否可編輯，原本存 value 的地方都要顯示成 label (valueFormatter)
        base.valueFormatter = (params) => {
          const opt = column.options?.find((o: any) => o.value === params.value);
          return opt ? opt.label : params.value;
        };

        if (column.editable === true) {
          base.editable = true;
          base.cellEditor = "agSelectCellEditor";
          base.cellEditorParams = {
            values: column.options ? column.options.map((o: any) => o.value) : [],
            // 編輯時選單也要顯示的是 Label 而非 Value
            valueListRenderer: (params: any) => {
              const opt = column.options?.find((o: any) => o.value === params.value);
              return opt ? opt.label : params.value;
            }
          };
        }
        break;

      case "autocomplete":
      case "input":
        if (column.editable === true) {
          base.editable = true;
          base.cellEditor = "agTextCellEditor";
        }
        break;
    }

    // 當非編輯模式的 checkbox 渲染已移至 switch
    
    // cellRenderer (自定義元件)
    if (column.cellRenderer === "AGTagCell") {
      base.cellRenderer = AGTagCell as any;
    }
    if (column.cellRenderer === "AGActionButtonRenderer") {
      base.cellRenderer = AGActionButtonRenderer as any;
      base.cellRendererParams = {
        actions: column.actionButtons,
        onAction: (action: any, data: any) => {
          // 修正資料不一致問題
          gridApi.value?.stopEditing();
          const fresh = gridApi.value?.getRowNode(data.id);
          if (fresh) {
            data = fresh.data;
          }
          emit("grid-action-click", { action, data });
        },
      };
    }
    const vf = buildValueFormatter(column);
    if (vf) {
      base.valueFormatter = vf;

      // 若判斷為日期類型，自動套用日期過濾器
      const isDateLike =
        typeof column.format === "string" &&
        /^(date|datetime|time)\b/i.test(column.format);
      if (isDateLike && !base.filter) {
        base.filter = "agDateColumnFilter";
      }
    }
    return base;
  });
});

const mergedGridOptions = computed<GridOptions>(() => ({
  ...baseGridOptions.value,
  ...(props.options || {}),
  async onDragStopped(event) {
    // TODO 表頭拖拉
    const currentColumnDefs = event.api.getColumnDefs() || [];
    const columns = currentColumnDefs.map((x: any) => {
      // json table 樣板增減屬性要跟這調整
      return {
        field: x.field,
        headerName: x.headerName,
        minWidth: x.minWidth,
        maxWidth: x.maxWidth,
        editable: x.editable,
        sortable: x.sortable,
        filter: x.filter,
        suppressMovable: x.suppressMovable,
        lockPosition: x.lockPosition,
        pinned: x.pinned,
        valueGetter: x.valueGetter,
      };
    });
    emit("columns-reset", columns);
  },
  onColumnMoved(event) {},
}));

const onActionClick = (event: any) => {
  emit("action-click", event);
};

const onFirstDataRendered = (params: any) => {
  // 全部資料都選
  //params.api.forEachNode(node => node.setSelected(true));
  params.api.forEachNode((node: any) => {
    node.setSelected(node.data.isSelected);
  });
};

async function loadServerPage(page: number, pageSize: number) {
  emit("pagination-change", { page, pageSize });
}
const onPaginationChange = ({
  page,
  pageSize,
}: {
  page: number;
  pageSize: number;
}) => {
  loadServerPage(page, pageSize);
};

const onRefresh = () => {
  loadServerPage(props.pagination.page, props.pagination.pageSize);
};
</script>

<template>
  <!-- dynamic button -->
  <div class="h-full flex flex-col min-h-0">
    <div class="action-button-group">
      <BaseButtonGroup
        v-if="actions != null && actions?.length > 0"
        aria-label="Actions"
        class="m-1"
      >
        <BaseButton
          v-for="action in actions"
          :variant="action.type"
          :size="'md'"
          :icon="action.icon"
          @click="() => onActionClick(action)"
        >
          {{ t(action.label) }}
        </BaseButton>
      </BaseButtonGroup>
    </div>

    <div class="flex-1 min-h-0 ag-theme-alpine">
      <AgGridVue
        class="w-full h-full"
        :grid-options="mergedGridOptions"
        :columnDefs="computedColumnDefs"
        :rowData="props.records"
        :getRowId="getRowId"
        :localeText="localeText"
        :defaultColDef="defaultColDef"
        :pagination="false"
        :undoRedoCellEditing="true"
        :undoRedoCellEditingLimit="5"
        @selectionChanged="onSelectionChanged"
        @onFilterChanged="onFilterChanged"
        @cell-value-changed="onCellValueChanged"
        @grid-ready="onGridReady"
        @first-data-rendered="onFirstDataRendered"
      >
      </AgGridVue>
    </div>

    <!-- 外部分頁器 -->
    <AgPagination
      v-if="pagination"
      :page="pagination.number"
      :pageSize="pagination.size"
      :pageSizes="[10, 20, 50, 100]"
      :totalRows="pagination.totalElements"
      :totalPages="pagination.totalPages"
      @change="onPaginationChange"
      @refresh="onRefresh"
    />
  </div>
</template>

<style>
.ag-theme-alpine {
  width: 100%;
  height: 100%;
  border-radius: 0cm;
  --ag-header-background-color: #bdbdbd; /* 表頭背景 */
  --ag-header-foreground-color: #ffffff; /* 表頭文字 */
  --ag-odd-row-background-color: #f3f4f6; /* 奇數列背景 */
}
.action-button-group {
  display: flex;
  justify-content: end;
}
.grid-view {
  width: 100%;
  height: 100%;
}
</style>

<!--  dayjs
 {
  "headerName": "更新日期",
  "field": "updatedAt",
  "format": "datetime"
}
// 或是指定特定格式
{
  "headerName": "月份",
  "field": "date",
  "format": "date:YYYY-MM"
}
  -->
