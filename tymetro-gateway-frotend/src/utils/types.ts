export type CellStatus = 0 | 1 | 2 | 3 | 4;

export interface MapData {
  id?: number;
  dcId?: number;
  houseId?: number;
  roomId?: number;
  areaId?: number;
  mapType?: number;
  code?: string;
  name?: string;
  rowCount: number;
  colCount: number;
  levelNum?: number;
  isEnable?: boolean;
  mapCells?: MapCell[][][];
}

export interface MapCell {
  id: number | null; // 資料庫主鍵
  mapId: number | null; // 所屬地圖 ID
  levelIndex: number | null;
  shelfId: number | null; // 貨架 ID，允許為 null
  rowIndex: number;
  colIndex: number;
  mapCellStatus: CellStatus;
}

export interface Compressor {
  id: number;
  status: 'ON' | 'OFF';
  health: '正常' | '異常';
  highPress: number;
  lowPress: number;
}

export interface HVACUnit {
  compressors: Compressor[];
  temp: number;
  setTemp: number;
  mode: string;
}

export interface CarStatus {
  id: number;
  label: string;
  status: 'normal' | 'warning' | 'offline';
  unit1: HVACUnit;
  unit2: HVACUnit;
  lastUpdate: string;
}

export interface TrainStatus {
  id: number;
  label: string;
  cars: CarStatus[];
}


// Health status states
export interface ServiceHealth {
  name: string;
  status: string;
  message?: string;
  host?: string;
  port?: number;
  device_id?: number;
  path?: string;
  url?: string;
}

export interface GatewayHealth {
  gateway_id: string;
  gateway_name: string;
  app_mode: string;
  status: string;
  uptime_seconds: number;
  version: string;
  timestamp: number;
  services: Record<string, ServiceHealth>;
}

export interface TrainCarStatus {
  id: number;
  trainNo: number;
  carVin: number;
  name: string;
  endpoints: EndpointStatus[];
}

// 預設暫存器配置 (Fallback & Live)
export interface ModbusRegisterRow extends SensorData {
  rawValue: number;
  isChanging?: boolean;
}
// 定義端點狀態資料結構
export interface EndpointStatus {
  id: number;
  name: string;
  address: string;
  isConnected: boolean;
  mode: string; // 停止 / 自動 / 送風 / 測試
  returnTemp: number;
  setTemp: number;
  status: 'normal' | 'warning' | 'abnormal';
  statusName: string;
  compressors: {
    id: number;
    status: 'ON' | 'OFF';
    health: '正常' | '異常';
    highPress: number;
    lowPress: number;
  }[];
}

export interface CarOption {
  value: number;
  label: string;
  name: string;
}

export interface EndpointOption {
  value: number;
}

export interface EquipmentConfig {
  id: number;
  name: string;
  address: string;
}

export interface CarVinConfig {
  carVin?: number;
  carNo?: number;
  id: number;
  name: string;
  ip?: string;
  trainNo?: number;
  equipment?: EquipmentConfig[];
}

export interface SensorData {
  id?: number;
  sensorCode: string;
  sensorName?: string;
  sensorUnit?: string | null;
  sensorValue?: string | number | null;
  address: number;
  dataType?: string;
  scale?: number;
}

export interface MapSensorMarker {
  id: string;
  x: number;
  y: number;
  label: string;
  value: string;
  code: string;
  color: string;
  type: string;
  bitIndex?: number | null;
}

export interface MapSensorConfig {
  sensorCode: string;
  x: number;
  y: number;
  label: string;
  color?: string;
  markerType?: string;
  bitIndex?: number | null;
}

export interface MqttPayload {
  carVin?: number | string;
  carNo?: number | string;
  endPos?: number | string;
  events?: string;
  register?: Record<string, number | string>;
  [key: string]: any;
}