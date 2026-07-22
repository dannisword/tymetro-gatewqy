Listed directory tymetro-cms-frotend
Listed directory src
Listed directory router
Listed directory views
Listed directory mtr
Listed directory base
Viewed index.ts:1-170
Viewed home.vue:1-294
Viewed tile-menus.vue:1-67
Viewed parameters.vue:1-145
Viewed period-settings.vue:1-300
Viewed schedule.vue:1-675
Viewed accounts.vue:1-439
Viewed register-management.vue:1-570
Viewed VisualDesigner.vue:1-438
Viewed document-templates.vue:1-173
Viewed car-page.vue:1-490
Viewed equipment-page.vue:1-267
Viewed sensor-records-list.vue:1-256
Viewed sensor-records.vue:1-217
Viewed car-list.vue:1-368
Viewed useMtrStore.ts:1-128
Viewed form-base.vue:1-180
Viewed record-base.vue:1-209
Viewed role-records.vue:1-221
Listed directory docs
Viewed aggrid_component.md:1-132
Viewed doc_dev_core.md:1-458
Viewed doc_dev_record.md:1-91
Viewed user-grecords.vue:1-205
Listed directory layouts
Listed directory Layout
Viewed AppSidebar.vue:1-273
Viewed useAppStore.ts:1-98
Searched for "getMenus"
Viewed service.ts:1-27
Edited frontend_feature_list.md

已為您整理好前端專案的功能清單。我已在 [frontend_feature_list.md](file:///Users/dannis/.gemini/antigravity-ide/brain/19af64c0-6549-4748-b17b-58a9aaf71a3d/frontend_feature_list.md) 建立了完整的結構化說明，主要涵蓋以下四大核心區塊：

1. **監控與即時數據視圖**
   * **車廂狀態監控**：展示冷氣/送風模式、設定/回風溫度、歷史趨勢圖與壓縮機高低壓狀態表。
   * **列車即時監控**：整合 MQTT 訂閱暫存器數據，提供多車廂快覽。
   * **車廂系統圖 (SVG Viewer)**：以車廂 SVG 佈局為基礎，支援感測器標記的**拖拽配置 (Drag-and-Drop)**、坐標調整與批次儲存。
   * **感測器紀錄列表**：Gmail 風格的感測器數據列表，支援篩選與批量操作。
2. **控制與排程設定模組**
   * **參數管理**：PLC 參數讀寫、數據下載與遠端更新。
   * **時段設定**：24x7 小時的季節模式溫度排程設定，支援複製、貼上與清除。
   * **排程設定**：支援 `hourly`, `minutely`, `fixed_time`, `cycle_time` 與 `cron` 五種背景排程任務的管理。
3. **系統維護與權限管理**
   * **帳號資料**：使用者帳號維護與啟用狀態控制。
   * **暫存器設定**：Modbus 暫存器點位、縮放比例、資料型別與監控狀態設定。
   * **權限管理**：利用樹狀選單 (`TreeList`) 分配各角色的選單與操作權限。
   * **樣板維護與 JSON 設計器 (Visual JSON Designer)**：低代碼開發工具，支援視覺化拖曳設計頁面 Schema 並自動生成 JSON 配置。
4. **系統基礎架構特色**
   * 配置驅動 (`BaseHandle` 與 `DocumentHandle`) 的 ERP 低代碼渲染模式。
   * 高度封裝、支援智慧格式化（如貨幣、時間、百分比）與勾選狀態同步的 `AgGridView2`。
   * 可靈活切換的單機版/網路版佈局模式 (`1-column-layout` / `multi-column-layout`)。

您可以直接點擊 [frontend_feature_list.md](file:///Users/dannis/.gemini/antigravity-ide/brain/19af64c0-6549-4748-b17b-58a9aaf71a3d/frontend_feature_list.md) 查看包含檔案關聯路徑的完整詳細清單。