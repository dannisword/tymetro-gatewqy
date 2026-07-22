
---

# Vue 3 CRUD 通用頁面組件說明文件
文件說名 **Vue 3 通用 CRUD（增刪改查）管理頁面**。  
它高度依賴封裝好的 Hooks (`DocumentHandle`) 和自定義組件，實現了「低代碼」風格的開發模式，即通過配置（Config/Schema）來驅動頁面的渲染與邏輯。

以下是為程式碼的技術說明文件：
## 1. 概要 (Overview)
此組件是一個標準的後台管理頁面，具備以下功能：

* **列表展示**：使用 `AgGridView` 顯示數據，支援分頁與多選。
* **搜尋過濾**：使用 `ElSearchCustom` 根據配置動態生成搜尋欄位。
* **新增/編輯**：使用 `ElDialogCustom` 彈窗包裹 `ElFormCustom` 動態表單進行資料維護。
* **邏輯封裝**：透過 `DocumentHandle` 統一管理 API 請求、資料結構定義（Schema）與 CRUD 操作。

---

## 2. 核心依賴與 Hook (Core Dependencies)
組件依賴以下關鍵的 Composable (Hooks) 與工具：

| 名稱 | 來源 | 用途 |
| --- | --- | --- |
| **DocumentHandle** | `hooks/document-handle` | **核心邏輯**。提供資料載入 (`loadDocument`)、CRUD 方法 (`read`, `create`, `update`)、狀態管理 (`instance`) 與表單操作 (`setData`, `cleanData`)。 |
| **useAlert** | `composables/TLAlter` | 處理全域提示訊息 (Success, Warning, Error)。 |
| **routeHandle** | `hooks/route-handle` | 獲取當前路由資訊（如 `pageName`），用於區分不同頁面的配置。 |
| **Custom Components** | `components/*` | 包含 `AgGridView` (表格), `ElDialogCustom` (彈窗), `ElFormCustom` (表單), `ElSearchCustom` (搜尋)。 |

---

## 3. 生命週期與邏輯詳解 (Logic & Lifecycle)
### 3.1 初始化 (Setup & Mount)* **變數定義**：
* `opts`: 定義表格設定（分頁、多選）。
* `dialog`: 控制彈窗的顯示狀態與標題。


* **生命週期 `onBeforeMount**`：
1. `await loadDocument()`: 根據當前頁面名稱，載入對應的 JSON 設定檔或 Schema（包含表格欄位、表單欄位定義）。
2. `await read()`: 呼叫 API 獲取列表資料。



### 3.2 互動事件 (Event Handlers)
#### **搜尋 (Search)**
* 觸發 `<ElSearchCustom @confirm="read">`。
* 直接呼叫 `read()` 重新獲取符合搜尋條件的資料。

#### **新增按鈕 (Add Action)**
* 觸發 `onActionClick`。
* 執行 `cleanData()`：清空表單資料，重置為預設值。
* `dialog.visible = true`：開啟彈窗。

#### **表格行內操作 (Row Action - Edit)**
* 觸發 `onGridActionClick`。
* 判斷 `action.event == FormMode.Edit`。
* 執行 `setData(data)`：將選中的行資料填入表單模型 (`instance.form.dto`)。
* 開啟彈窗進入編輯模式。

#### **表單提交/關閉 (Modal Close / Submit)**
* 觸發 `onModalClose`。
* **流程**：
1. **關閉檢查**：如果是由「取消」或「關閉」觸發，則直接隱藏彈窗。
2. **表單驗證**：呼叫 `formRef.value?.validate()`。
3. **資料轉換**：`arrayToObject` 將表單資料格式化。
4. **CRUD 判斷**：
* 若 `id == 0`：執行 `create` (新增)。
* 若 `id != 0`：執行 `update` (更新)。


5. **後續處理**：顯示成功訊息 (`TLSuccess`) 並刷新列表 (`read`)。
6. **錯誤處理**：捕獲異常並顯示警告。



---

## 4. 模板結構 (Template Structure)
採用 Flex 佈局，主要分為兩大區塊：

1. **主內容區 (`<main>`)**：
* **搜尋列**：由 `instance.search.schemas` 驅動渲染。
* **資料表格**：由 `instance.table.columns` 定義欄位，綁定 `instance.table.records` 資料。


2. **彈窗區 (`<ElDialogCustom>`)**：
* 包含通用表單組件 `<ElFormCustom>`。
* 表單結構由 `instance.form.schemas` 驅動。
* 資料雙向綁定至 `instance.form.dto`。

---
