# AgGridView 元件技術說明文件
這份文件說明了 `AgGridView.vue` 的架構設計與功能。這是一個高度封裝的 **AG Grid Vue 3** 元件，旨在簡化表格的配置，並提供統一的格式化、操作按鈕與資料同步邏輯。
## 1. 概要 (Overview)
`AgGridView` 是基於 `ag-grid-vue3` 的封裝元件。它並非單純透傳屬性，而是加入了一層**中間處理層 (Middle Layer)**，負責處理：

* **格式化 (Formatting)**：透過字串配置自動轉換日期、數字、貨幣格式。
* **渲染器 (Renderers)**：根據欄位設定自動掛載 Tag 或 Action Button 元件。
* **狀態同步 (State Sync)**：實現外部資料 (`records`) 與表格勾選狀態 (`selection`) 的雙向綁定。
* **在地化 (Localization)**：內建繁體中文語系。

---

## 2. 介面定義 (API Interface)
### 2.1 Props (輸入屬性)
| 屬性名稱 | 類型 | 預設值 | 說明 |
| --- | --- | --- | --- |
| **options** | `GridOptions` | `{}` | 覆蓋預設的 AG Grid 設定 (如 rowSelection, context 等)。 |
| **columns** | `Array` | `[]` | **核心配置**。定義欄位結構、渲染器與格式化規則。 |
| **records** | `Array` | `[]` | 表格資料來源 (Row Data)。支援雙向綁定 (v-model)。 |
| **actions** | `Array` | `[]` | 定義**表格上方**的全域操作按鈕 (Global Actions)。 |
| **pagination** | `Object` | `null` | 分頁設定 (目前主要依賴內部 `baseGridOptions`)。 |

### 2.2 Emits (輸出事件)
| 事件名稱 | 參數 | 說明 |
| --- | --- | --- |
| **update:records** | `newRecords[]` | 當勾選狀態改變時觸發，用於更新外部資料的 `isSelected` 屬性。 |
| **selectionChanged** | `selectedNodes[]` | 標準 AG Grid 事件，回傳被選中的原始資料列。 |
| **action-click** | `action` | 點擊**表格上方**按鈕時觸發。 |
| **grid-action-click** | `{ action, data }` | 點擊**表格行內 (Row)** 操作按鈕時觸發。`data` 為該行資料。 |

---

## 3. 核心功能詳解
### 3.1 智慧格式化 (Smart Formatting)
元件內建 `buildValueFormatter` 函式，允許在 `columns` 定義中使用 `format` 字串來處理資料顯示，無需撰寫重複的 formatter 函式。

**`columns` 定義範例：**

```javascript
{ 
  headerName: "金額", 
  field: "amount", 
  format: "currency:TWD" // 自動格式化為新台幣
}

```

**支援的格式化語法：**

| 類型 (Kind) | 參數 (Arg) | 語法範例 (`format`) | 說明 |
| --- | --- | --- | --- |
| **dayjs** | `Pattern | Timezone` | `dayjs:YYYY-MM-DD` |
| **date** | `short`/`medium`/`long` | `date:short` | 使用 `Intl.DateTimeFormat` (僅日期)。 |
| **datetime** | 同上 | `datetime:medium` | 日期 + 時間。 |
| **time** | 同上 | `time:short` | 僅時間。 |
| **number** | 小數位數 | `number:2` | 數值格式化，預設兩位小數。 |
| **currency** | 幣別代碼 | `currency:USD` | 貨幣格式化。 |
| **percent** | 小數位數 | `percent:1` | 百分比格式化 (0.5 -> 50.0%)。 |

### 3.2 特殊渲染器 (Custom Renderers)
透過在 `columns` 中指定 `cellRenderer` 字串，元件會自動掛載對應的 Vue 子元件。

1. **Tag 標籤 (`AGTagCell`)**
* 設定：`cellRenderer: "AGTagCell"`
* 用途：顯示帶顏色的標籤 (Badge/Tag)。


2. **操作按鈕組 (`AGActionButtonRenderer`)**
* 設定：`cellRenderer: "AGActionButtonRenderer"`
* 搭配屬性：`actionButtons` (定義按鈕列表)
* 行為：點擊後觸發 `grid-action-click` 事件。



### 3.3 選擇狀態同步 (Selection Synchronization)
此元件實現了較為罕見的**雙向綁定邏輯**：

1. **資料驅動視圖 (`watch(records)`)**：
* 當外部 `records` 變更時，執行 `syncSelectionFromData`。
* 檢查資料中的 `isSelected` 屬性，並透過 `gridApi.node.setSelected()` 強制更新表格的勾選狀態。


2. **視圖驅動資料 (`onSelectionChanged`)**：
* 當使用者在表格勾選時，計算出所有被選中的 ID。
* 重新映射 `props.records`，更新每筆資料的 `isSelected` 屬性。
* 發送 `emit("update:records", ...)` 通知父層更新。



---

## 4. 依賴與插件 (Dependencies)
* **Ag-Grid Community / Vue3**: 核心表格庫。
* **Day.js**: 處理時間日期，包含 `utc`, `timezone`, `customParseFormat` 插件。
* **BaseButton / BaseButtonGroup**: (全域組件) 用於渲染上方的操作按鈕區。

## 5. 使用範例 (Usage Example)
```html
<template>
  <AgGridView
    v-model:records="tableData"
    :columns="columns"
    :actions="globalActions"
    @grid-action-click="handleRowAction"
  />
</template>

<script setup>
const columns = [
  { headerName: "ID", field: "id" },
  { 
    headerName: "建立時間", 
    field: "createTime", 
    format: "dayjs:YYYY-MM-DD HH:mm" // 自動格式化
  },
  {
    headerName: "操作",
    cellRenderer: "AGActionButtonRenderer",
    actionButtons: [{ label: "編輯", event: "EDIT" }]
  }
];

const tableData = ref([
  { id: 1, createTime: "2023-01-01T12:00:00Z", isSelected: false }
]);
</script>

```

## 6. 注意事項
1. **ID 依賴**：程式碼中多次使用 `data.id` (`getRowId`, `syncSelectionFromData`)，因此傳入的 `records` **必須包含唯一的 `id` 欄位**，否則選取功能會失效。
2. **時區處理**：`buildValueFormatter` 預設使用瀏覽器時區，若需固定時區請在 `column` 定義中加入 `timeZone` 或使用 `dayjs.tz` 語法。