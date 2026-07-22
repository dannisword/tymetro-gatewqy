# 桃園捷運 IoT Gateway 後端 (tymetro-gateway)

這是一個基於 FastAPI 開發的 IoT 閘道器後端應用程式，專門用來處理底層設備通訊 (MQTT / Modbus PLC) 與系統狀態監控。

## 專案結構

```
tymetro-gateway/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health_controller.py # 健康檢查 API
│   │       └── api.py                   # API 路由整合
│   ├── core/
│   │   ├── config.py                    # 系統設定檔 (支援 .env)
│   │   └── logger.py                    # Loguru 日誌設定
│   ├── middleware/
│   │   └── logging_middleware.py        # HTTP 請求日誌紀錄中介軟體
│   ├── schemas/
│   │   └── response_schema.py           # 標準 API 回應結構
│   └── utils/
│       └── response_util.py             # 回應封裝工具
├── logs/                                # 自動產生的日誌檔案存放區
├── .env                                 # 環境變數設定檔
├── .gitignore                           # Git 忽略設定
├── main.py                              # FastAPI 應用程式進入點
└── requirements.txt                     # 專案相依套件清單
```

## 快速啟動

### 1. 建立並啟動虛擬環境 (建議)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 3. 執行伺服器

使用 `uvicorn` 啟動開發伺服器（預設運行於 Port `5400`）：

```bash
uvicorn main:app --reload --port 5400
```

## API 測試 (Health Check)

啟動伺服器後，您可以訪問 Swagger UI 查看並測試 API：
- [http://127.0.0.1:5400/docs](http://127.0.0.1:5400/docs)

或者直接發送 GET 請求獲取系統狀態：
```bash
curl http://127.0.0.1:5400/api/v1/health/status
```

回應範例：
```json
{
  "success": true,
  "message": "Gateway backend is running normally",
  "data": {
    "gateway_id": "GW-TYMETRO-001",
    "gateway_name": "桃園捷運 IoT Gateway",
    "app_mode": "development",
    "status": "online",
    "uptime_seconds": 12,
    "services": {
      "mqtt_broker": {
        "host": "127.0.0.1",
        "port": 1883,
        "status": "connected"
      },
      "modbus_plc": {
        "host": "192.168.1.10",
        "port": 502,
        "slave_id": 1,
        "status": "connected"
      }
    },
    "version": "1.0.0",
    "timestamp": 1715873250
  }
}
```
