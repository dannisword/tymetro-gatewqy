<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, reactive, toRefs } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseSwitch from '@/components/BaseSwitch.vue';
import BaseRangeSlider from '@/components/BaseRangeSlider.vue';
import RegisterTrendModal from '@/views/mtr/components/RegisterTrendModal.vue';
import ElDialogCustom from '@/components/ElDialogCustom.vue';
import { useMQTT } from '@/store/useMQTT';
import { useAlert } from "@/composables/TLAlter";
import { ElMessageBox, ElLoading } from 'element-plus';
import { SYSTEM_MODE_MAP, SystemModeKey, CompressorStatus, CompressorHealth, SettingTypeEnum } from '@/utils/enums';
import type { 
  TrainCarStatus, 
  EndpointStatus, 
  ModbusRegisterRow,
  CarOption,
  EndpointOption,
  CarVinConfig,
  SensorData,
  MapSensorMarker,
  MapSensorConfig,
  MqttPayload
} from '@/utils/types';
import CarSensorMap from '@/views/mtr/components/CarSensorMap.vue';
import httpOperations from '@/utils/http-operations';
import { logger, updateCompressorStatus } from '@/utils';
import { useFullscreen } from '@vueuse/core';
import { 
  mdiWeatherWindy, 
  mdiSnowflake, 
  mdiAirConditioner, 
  mdiRefresh,
  mdiClockOutline,
  mdiPower,
  mdiThermometer,
  mdiFlash,
  mdiPause,
  mdiGauge,
  mdiPlus,
  mdiMinus,
  mdiMagnify
} from '@mdi/js';
// ==========================================
// 0. Configuration Parameters
// ==========================================
const HEARTBEAT_TIMEOUT = 5000; // 判定斷線超時時間 (毫秒)
const HEARTBEAT_CHECK_INTERVAL = 1000; // 心跳檢查間隔 (毫秒)

/**
 * 通用延遲鎖定函式 (防連續重複操作)
 * @param lockRef 目標 ref<boolean> 鎖定旗標
 * @param delayMs 延遲時間 (毫秒)，預設 2000ms
 */
const withLockDelay = (lockRef: { value: boolean }, delayMs = 2000) => {
  lockRef.value = true;
  setTimeout(() => {
    lockRef.value = false;
  }, delayMs);
};

/**
 * 畫面通用全螢幕 loading 2 秒
 * @param delayMs 延遲時間 (毫秒)，預設 2000ms
 */
const triggerActionLoading = (delayMs = 2000) => {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '載入中...',
    background: 'rgba(0, 0, 0, 0.8)'
  });
  setTimeout(() => {
    loadingInstance.close();
  }, delayMs);
};
// ==========================================
// 1. Hook & Utilities
// ==========================================
const route = useRoute();
const router = useRouter();
const { TLError, TLWarning, TLInfo, TLSuccess } = useAlert();

// ==========================================
// 2. Core Route State & Derived Computeds
// ==========================================
const state = reactive({
  carNo: Number(route.params.carNo) || 1101,
  endPosId: Number(route.params.endPos) || 1,
  carInfoMap: {} as Record<number, TrainCarStatus>
});
const { carNo, endPosId, carInfoMap } = toRefs(state);

const carInfo = computed(() => carInfoMap.value[carNo.value] || carInfoMap.value[1101] || { id: 1101, name: '', ip: '', endpoints: [] });
const endPos = computed(() => {
  const info = carInfo.value;
  const defaultEp = { name: `端點 ${endPosId.value}`, address: '' };
  if (!info || !info.endpoints) return defaultEp;
  const ep = info.endpoints.find(e => e.id === endPosId.value);
  return ep ? { ...ep, name: ep.name || `端點 ${endPosId.value}` } : defaultEp;
});
const normalizedCarNo = computed(() => carInfo.value ? carInfo.value.id : 1101);
const carType = computed(() => Math.floor(carNo.value / 1000));
const trainNo = computed(() => carType.value * 100 + (carNo.value % 100));
// ==========================================
// 3. MQTT Connection & Heartbeat Tracker State
// ==========================================
const { isConnected: isMqttConnected, connect, subscribe, publish } = useMQTT();
const isDeviceConnected = ref(false);
const isTempSettingLocked = ref(false);
const isDamperSettingLocked = ref(false);
const lastMsgTime = ref<number | null>(null);
let mqttCheckInterval: ReturnType<typeof setInterval> | null = null;
let heartbeatInterval: ReturnType<typeof setInterval> | null = null;

// ==========================================
// 4. UI Layout & Navigation States
// ==========================================
const pageContainerRef = ref<HTMLElement | null>(null);
const { isFullscreen, toggle: toggleFullscreen } = useFullscreen(pageContainerRef);

const activeTab = ref('dashboard');
const breadcrumbItems = computed(() => [
  { label: '首頁', to: '/dashboard' },
  { label: `${carNo.value}車廂-${endPos.value.name} 狀態` }
]);

const rawCarOptions = ref<CarOption[]>([]);
const dynamicCarOptions = ref<CarOption[]>([]);
const carOptions = computed(() => {
  if (rawCarOptions.value.length > 0) {
    return rawCarOptions.value.map((opt) => ({
      ...opt,
      value: carType.value * 1000 + opt.value * 100 + (trainNo.value % 100)
    }));
  }
  return dynamicCarOptions.value;
});
const endpointsOptions = ref<EndpointOption[]>([]);
const configCarVinsList = ref<CarVinConfig[]>([]);

// ==========================================
// 5. HVAC Status, Damper Controls & Operating Modes
// ==========================================
const mode = ref(''); // 停止 / 自動 / 送風 / 測試
const returnTemp = ref<number | null>(null);
const setTemp = ref<number | null>(null);
const compressors = ref([
  { id: 1, status: CompressorStatus.OFF, health: CompressorHealth.Normal, highPress: 0, lowPress: 0, runHours: 0 },
  { id: 2, status: CompressorStatus.OFF, health: CompressorHealth.Normal, highPress: 0, lowPress: 0, runHours: 0 }
]);
// 新鮮空氣擋板開度 (設定觸發: D40212, 顯示完成: D40213): 0=關閉, 25=25%, 50=50%, 75=75%, 100=100%
const freshAirDamperPos = ref<number>(0);
// 緊急供氣擋板 (設定觸發: D40214, 顯示完成: D40215): 1=否, 2=是
const emergAirDamper = ref<number>(1);

const freshAirDamperOptions = ref<{ value: number; label: string }[]>([
  { value: 0, label: '關閉' },
  { value: 25, label: '25%' },
  { value: 50, label: '50%' },
  { value: 75, label: '75%' },
  { value: 100, label: '100%' }
]);
const operationModes = ref<{ value: string; label: string; icon: string; activeClass: string }[]>([]);

// ==========================================
// 6. Modbus Registers Monitoring State & Computeds
// ==========================================
const modbusRegisters = ref<ModbusRegisterRow[]>([]);
const registersSearchQuery = ref('');

const addressRangeText = computed(() => {
  if (modbusRegisters.value.length === 0) return '讀取位址: —';
  const addresses = modbusRegisters.value.map(r => r.address);
  const minAddress = Math.min(...addresses);
  const maxAddress = Math.max(...addresses);
  return `讀取位址: ${40001 + minAddress} - ${40001 + maxAddress} (對應 PLC 暫存器位址 ${minAddress} - ${maxAddress})`;
});

const filteredRegisters = computed(() => {
  const query = registersSearchQuery.value.trim().toLowerCase();
  if (!query) return modbusRegisters.value;
  return modbusRegisters.value.filter(r => 
    (r.sensorCode || '').toLowerCase().includes(query) || 
    (r.sensorName || '').toLowerCase().includes(query) ||
    String(r.address).includes(query)
  );
});

// ==========================================
// 7. Svg Map Configuration & Mapped Sensors
// ==========================================
const planUrl = "/images/layout.svg";
const mapTemplateSensors = ref<MapSensorMarker[]>([]);

// 數值對照 (key: sensorCode)：(暫存器值 & bitMask) === matchValue 時顯示 text
interface ValueLabel { bitMask: number; matchValue: number; text: string }
const valueLabelMap = ref<Record<string, ValueLabel[]>>({});

const fetchValueLabels = async () => {
  try {
    const res = await httpOperations.get('/api/v1/sensor-value-labels');
    if (res.success && Array.isArray(res.data)) {
      const map: Record<string, ValueLabel[]> = {};
      res.data.forEach((v: any) => {
        if (v.text == null || v.matchValue == null) return; // 位元名稱列不參與數值對照
        (map[v.sensorCode] ||= []).push({ bitMask: v.bitMask, matchValue: v.matchValue, text: v.text });
      });
      valueLabelMap.value = map;
    }
  } catch (error) {
    console.error("Fetch value labels failed:", error);
  }
};

const findValueText = (code: string, raw: number, predicate: (mask: number) => boolean): string | undefined =>
  valueLabelMap.value[code]?.find(v => predicate(v.bitMask) && (raw & v.bitMask) === v.matchValue)?.text;

const mappedSensors = computed(() => {
  return mapTemplateSensors.value.map(s => {
    const matched = modbusRegisters.value.find(reg => reg.sensorCode === s.code);
    if (matched) {
      if (matched.dataType === 'bitmap' && s.bitIndex !== null && s.bitIndex !== undefined) {
        const rawStr = String(matched.sensorValue || '');
        let bitVal = 0;
        if (rawStr.length >= 16 && /^[01]+$/.test(rawStr)) {
          bitVal = rawStr.charAt(15 - s.bitIndex) === '1' ? 1 : 0;
        } else {
          const intVal = Number(matched.sensorValue) || 0;
          bitVal = (intVal & (1 << s.bitIndex)) !== 0 ? 1 : 0;
        }
        const bitMask = 1 << s.bitIndex;
        const customText = findValueText(s.code, bitVal ? bitMask : 0, mask => mask === bitMask);
        return { 
          ...s, 
          bitValue: bitVal,
          value: customText || (bitVal === 1 ? 'ON' : 'OFF')
        };
      }
      // 多位元組合判定 (例如主控制模式)：有對照文字時直接顯示文字
      const comboText = findValueText(s.code, Number(matched.sensorValue) || 0, mask => (mask & (mask - 1)) !== 0);
      if (comboText) {
        return { ...s, value: comboText };
      }
      const hasUnit = matched.sensorUnit && matched.sensorUnit.toUpperCase() !== 'N/A';
      const unit = hasUnit ? ` ${matched.sensorUnit}` : '';
      return { ...s, value: `${matched.sensorValue || '0.0'}${unit}` };
    }
    return s;
  });
});

// ==========================================
// 8. Modals State
// ==========================================
const showTrendModal = ref(false);
const selectedRegister = ref<ModbusRegisterRow | null>(null);

// 8 個端點批次控制 Modal (每次只能設定一種: 溫度 / 新鮮空氣擋板開度 / 開啟緊急供氣擋板)
const showBatchTempModal = ref(false);
const batchSettingType = ref<'temperature' | 'freshAir' | 'emergAir'>('temperature');
const batchTemp = ref(24.0);
const batchFreshAirDamperPos = ref<number>(0);
const batchEmergAirDamper = ref<number>(1);
const isBatchSettingLocked = ref(false);

// ==========================================
// 9. Methods & Event Handlers
// ==========================================

// 車廂及端點切換與載入
const handleCarChange = (newCarNo: number) => {
  carNo.value = newCarNo;
  router.replace(`/mtr/single-end-pos/${newCarNo}/${endPosId.value}`);
};

const handleEndpointChange = (newEndPosId: number) => {
  endPosId.value = newEndPosId;
  router.replace(`/mtr/single-end-pos/${carNo.value}/${newEndPosId}`);
};

const updateCarMap = (carVins: CarVinConfig[], hasPredefinedOptions = false) => {
  const map: Record<number, TrainCarStatus> = {};
  const options: CarOption[] = [];

  carVins.forEach((carVin) => {
    const resolvedCarNo = carVin.carNo || carVin.id;    
    const endpoints: EndpointStatus[] = [];
    const equipments = carVin.equipment || [];

    // 端點 1
    const ep1 = equipments.find((e) => e.id === 1);
    endpoints.push({
      id: 1,
      name: ep1 ? `${ep1.name}` : '端點 1',
      address: ep1 ? ep1.address : carVin.ip || '127.0.0.1',
      isConnected: false,
      mode: '停止',
      returnTemp: 24.0,
      setTemp: 24.0,
      status: 'normal',
      statusName: '正常營運',
      compressors: [
        { id: 1, status: CompressorStatus.OFF, health: '正常', highPress: 0, lowPress: 0 },
        { id: 2, status: CompressorStatus.OFF, health: '正常', highPress: 0, lowPress: 0 }
      ]
    });

    // 端點 2
    const ep2 = equipments.find((e) => e.id === 2);
    endpoints.push({
      id: 2,
      name: ep2 ? `${ep2.name}` : '端點 2',
      address: ep2 ? ep2.address : carVin.ip || '127.0.0.1',
      isConnected: false,
      mode: '停止',
      returnTemp: 24.0,
      setTemp: 24.0,
      status: 'normal',
      statusName: '正常營運',
      compressors: [
        { id: 1, status: 'OFF', health: '正常', highPress: 0, lowPress: 0 },
        { id: 2, status: 'OFF', health: '正常', highPress: 0, lowPress: 0 }
      ]
    });

    const shortName = carVin.name.replace(/第|節|車廂/g, '').trim() + '車';
    const fullName = carVin.name.includes('第') ? carVin.name : `第 ${carVin.id} 節車廂`;

    const info: TrainCarStatus = {
      id: resolvedCarNo,
      trainNo: carVin.trainNo || trainNo.value,
      carNo : resolvedCarNo,
      name: fullName,
      endpoints: endpoints
    };

    map[resolvedCarNo] = info;
    map[carVin.id] = info;

    options.push({
      value: resolvedCarNo,
      label: fullName,
      name: shortName
    });
  });

  if (Object.keys(map).length > 0) {
    carInfoMap.value = map;
  }
  if (options.length > 0 && !hasPredefinedOptions) {
    dynamicCarOptions.value = options;
  }
};

const loadCarConfig = async () => {
  try {
    const res = await fetch('/config.json');
    if (res.ok) {
      const config = await res.json();
      if (config) {
        if (config.carOptions && Array.isArray(config.carOptions)) {
          rawCarOptions.value = config.carOptions;
        }
        if (config.endpointsOptions && Array.isArray(config.endpointsOptions)) {
          endpointsOptions.value = config.endpointsOptions;
        }
        const rawCarVins = config.metro_config?.carVins || config.carVins;
        if (rawCarVins && Array.isArray(rawCarVins)) {
          const currentTrainNo = trainNo.value || config.metro_config?.trainNo || 101;
          const type = Math.floor(currentTrainNo / 100);
          const num = currentTrainNo % 100;

          const mappedCarVins = rawCarVins.map((c: any, index: number) => {
            const carIndex = index + 1;
            const resolvedCarNo = type * 1000 + carIndex * 100 + num;
            return {
              id: c.id || carIndex,
              carNo: resolvedCarNo,
              name: c.name || `第 ${carIndex} 節車廂`,
              ip: c.ip || c.equipments?.[0]?.address || '127.0.0.1',
              trainNo: currentTrainNo,
              equipment: (c.equipments || c.equipment || []).map((eq: any) => ({
                id: eq.endPosId || eq.id || 1,
                name: eq.name || `端點 ${eq.endPosId || eq.id || 1}`,
                address: eq.address || '127.0.0.1'
              }))
            };
          });
          configCarVinsList.value = mappedCarVins;
          updateCarMap(mappedCarVins, !!config.carOptions);
        }
        if (config.freshAirDamperOptions && Array.isArray(config.freshAirDamperOptions)) {
          freshAirDamperOptions.value = config.freshAirDamperOptions;
        }
        if (config.operationModes && Array.isArray(config.operationModes)) {
          const iconMap: Record<string, string> = {
            mdiPause,
            mdiFlash,
            mdiSnowflake,
            mdiWeatherWindy
          };
          operationModes.value = config.operationModes.map((mode: any) => ({
            ...mode,
            icon: iconMap[mode.iconName] || mode.iconName || ''
          }));
        }
      }
    }
  } catch (error) {
    logger.error('Failed to load car config from /config.json:', error);
    TLError('讀取車廂設定失敗');
  }
};

const carsList = ref<any[]>([]);
const currentCarVin = computed(() => {
  const matched = carsList.value.find(c => 
    String(c.carVin) === String(carNo.value) || 
    Number(c.carNo) === Math.floor((carNo.value % 1000) / 100)
  );
  return matched ? matched.carVin : '';
});

const fetchCars = async () => {
  try {
    const res = await httpOperations.get('/api/v1/cars', { pageSize: 100 });
    if (res && res.success) {
      carsList.value = res.data?.source || [];
    }
  } catch (err) {
    console.error('Failed to fetch cars:', err);
  }
};

// API 載入數據
const fetchInitialSensors = async () => {
  try {
    const res = await httpOperations.get('/api/v1/sensors/by-group', { registerGroup: 'initial' }, { meta: { loading: false } });
    if (res && res.success) {
      const list = (Array.isArray(res.data) ? res.data : (res.data?.source || [])) as SensorData[];
      const reg: Record<string, number> = {};
      list.forEach((item) => {
        if (item.sensorCode && item.sensorValue !== null && item.sensorValue !== undefined) {
          reg[item.sensorCode] = Number(item.sensorValue);
        }
      });

      const dbTrainNo = reg.D40054 !== undefined ? Number(reg.D40054) : undefined;
      if (dbTrainNo) {
        const type = Math.floor(dbTrainNo / 100);
        const num = dbTrainNo % 100;
        
        const currentCarIndex = Math.floor((carNo.value % 1000) / 100) || 1;
        const newCarNo = type * 1000 + currentCarIndex * 100 + num;
        
        if (configCarVinsList.value.length > 0) {
          configCarVinsList.value.forEach((car, index) => {
            const carIndex = index + 1;
            car.trainNo = dbTrainNo;
            car.carNo = type * 1000 + carIndex * 100 + num;
          });
          updateCarMap(configCarVinsList.value, !!rawCarOptions.value.length);
        }

        if (carNo.value !== newCarNo) {
          carNo.value = newCarNo;
          router.replace(`/mtr/single-end-pos/${newCarNo}/${endPosId.value}`);
        }
      }
    }
  } catch (error) {
    logger.error("Fetch initial sensors error in single-end-pos:", error);
  }
};

const fetchRegisters = async () => {
  try {
    const params: Record<string, any> = {
      sensorType: 'REAL_TIME',
      endPos: String(endPosId.value),
      pageSize: 1000
    };
    if (currentCarVin.value) {
      params.carVin = currentCarVin.value;
    }
    const res = await httpOperations.get('/api/v1/sensors', params, { meta: { loading: false } });
    if (res && res.success) {
      const list = (Array.isArray(res.data) ? res.data : (res.data?.source || [])) as SensorData[];
      list.sort((a, b) => (a.address || 0) - (b.address || 0));
      modbusRegisters.value = list.map((reg) => ({
        id: reg.id,
        address: reg.address,
        sensorCode: reg.sensorCode,
        sensorName: reg.sensorName || reg.sensorCode,
        dataType: reg.dataType || 'int16',
        scale: reg.scale || 1.0,
        sensorUnit: reg.sensorUnit || null,
        sensorValue: String(reg.sensorValue || ''),
        rawValue: reg.sensorValue ? Math.round(Number(reg.sensorValue) / (reg.scale || 1.0)) : 0,
        isChanging: false,
        carNo: reg.carNo || carNo.value
      }));
      // 載入時初始化新鮮空氣擋板開度 (完成狀態 D40213)
      const freshAirReg = list.find((s: any) => s.sensorCode === 'D40213');
      if (freshAirReg && freshAirReg.sensorValue !== undefined && freshAirReg.sensorValue !== null) {
        freshAirDamperPos.value = Number(freshAirReg.sensorValue);
      }
      // 載入時初始化緊急供氣擋板 (完成狀態 D40215)
      const emergAirReg = list.find((s: any) => s.sensorCode === 'D40215');
      if (emergAirReg && emergAirReg.sensorValue !== undefined && emergAirReg.sensorValue !== null) {
        emergAirDamper.value = Number(emergAirReg.sensorValue);
      }
      syncStatusToRegisters();
    }
  } catch (error) {
    console.error("Fetch registers error:", error);
  }
};

const fetchMapConfig = async () => {
  try {
    const mapRes = await httpOperations.get('/api/v1/sensor-maps/template/HVAC_STANDARD');
    if (mapRes.success && mapRes.data) {
      const mapData = (mapRes.data || []) as MapSensorConfig[];
      mapTemplateSensors.value = mapData.map((m) => {
        const isBitmap = m.bitIndex !== null && m.bitIndex !== undefined;
        return {
          id: isBitmap ? `${m.sensorCode}_bit${m.bitIndex}` : m.sensorCode,
          x: m.x,
          y: m.y,
          label: m.label || (isBitmap ? `${m.sensorCode} [B${m.bitIndex}]` : m.sensorCode),
          value: "0.0",
          code: m.sensorCode,
          bitIndex: m.bitIndex,
          color: m.color || (m.markerType === 'circle' ? '#10b981' : '#3b82f6'),
          type: m.markerType || 'rect',
          styleConfig: (m as any).styleConfig || { valuePosition: 'bottom' }
        };
      });
    }
  } catch (error) {
    console.error("Fetch map config failed:", error);
  }
};

// HVAC 與 PLC 控制
const handleTempAdjust = (amount: number) => {
  if (setTemp.value === null || isTempSettingLocked.value) return;
  const newTemp = parseFloat((setTemp.value + amount).toFixed(1));
  if (newTemp >= 16 && newTemp <= 30) {
    setTemp.value = newTemp;
    setTargetTemp();
  }
};

const setTargetTemp = async () => {
  if (setTemp.value === null || isTempSettingLocked.value) return;

  const targetTemperature = setTemp.value;
  isTempSettingLocked.value = true;

  const loadingInstance = ElLoading.service({
    lock: true,
    text: `正在設定溫度 (${targetTemperature}°C) 並等待 PLC 確認...`,
    background: 'rgba(0, 0, 0, 0.7)'
  });

  try {
    const res = await httpOperations.post('/api/v1/equipments/set-temperature', {
      trainCode: String(trainNo.value),
      carNo: Number(carNo.value),
      endPos: Number(endPosId.value),
      targetTemperature: targetTemperature
    }, { meta: { loading: false } });

    const isSuccess = Boolean(res?.success && (res?.data === undefined || res?.data?.success !== false));

    if (isSuccess) {
      TLSuccess(`溫度設定成功！目標溫度：${targetTemperature}°C (PLC 已確認)`);
      syncStatusToRegisters();
    } else {
      TLWarning(res?.message || res?.data?.message || '溫度指令已送出，但 PLC 尚未確認');
    }
  } catch (err: any) {
    console.error('Failed to set temperature via backend API:', err);
    TLError(err?.message || '設定溫度請求失敗');
  } finally {
    loadingInstance.close();
    withLockDelay(isTempSettingLocked, 1500);
  }
};


// 2D 圖標記點擊 (clickAction 為 detail 時開啟詳細視窗，與 tymetro 一致)
const showMarkerModal = ref(false);
const activeMarker = ref<any>(null);

// 標記點位對應的設定指令，key 為 點位代碼:bit (暫時寫死，之後再改由標記資料帶入)；dataType 為 bitmap 的標記以 ON / OFF 切換，寫入 onValue / offValue
interface MarkerCommand {
  command: SettingTypeEnum;
  onValue: number;
  offValue: number;
}
// 皆為觸發型指令：後端一律寫入 1 觸發 (不看 value)，PLC 以完成暫存器回報
const MARKER_COMMANDS: Record<string, MarkerCommand> = {
  'D40015:8': { command: SettingTypeEnum.MANUAL_START_AC, onValue: 1, offValue: 1 },         // D40218 / D40219
  'D40015:9': { command: SettingTypeEnum.FORCE_EMERGENCY_DAMPER, onValue: 1, offValue: 1 },  // D40220 / D40221
  'D40015:10': { command: SettingTypeEnum.FORCE_EXCHANGER, onValue: 1, offValue: 1 }         // D40222 / D40223
};
const markerKey = (m: any) => `${String(m?.code || '').toUpperCase()}:${m?.bitIndex}`;

// 以即時資料取得標記目前值 (視窗開啟期間隨 MQTT 更新)
const liveMarker = computed(() => {
  const m = activeMarker.value;
  return m ? (mappedSensors.value.find((s: any) => s.code === m.code && s.bitIndex === m.bitIndex) ?? m) : null;
});
const currentMarkerOn = computed(() => liveMarker.value?.bitValue === 1);
const activeMarkerCommand = computed(() => {
  const m = liveMarker.value;
  // 僅 bitmap (有 bitValue) 且有對應指令的標記可切換
  if (!m || m.bitValue === undefined || m.bitValue === null) return undefined;
  return MARKER_COMMANDS[markerKey(m)];
});
// 視窗中的 ON / OFF 切換狀態 (開啟時帶入目前值)
const markerToggleOn = ref(false);

const handleMarkerClick = (marker: any) => {
  if (marker?.styleConfig?.clickAction !== 'detail') return;
  activeMarker.value = marker;
  markerToggleOn.value = marker.bitValue === 1;
  showMarkerModal.value = true;
};

const handleMarkerDialogClose = async (res: any) => {
  const needExecute = res?.success && markerToggleOn.value !== currentMarkerOn.value;
  // 先關閉詳細視窗，再跳出確認框與執行指令 (避免確認框疊在視窗上)
  showMarkerModal.value = false;
  if (needExecute) await executeMarkerCommand();
};

const resetCompressorHours = async (id: number) => {
  try {
    await ElMessageBox.confirm(`確定要重置壓縮機 ${id} 的運轉時數嗎？此操作無法復原。`, '確認重置時數', {
      type: 'warning',
      confirmButtonText: '確定重置',
      cancelButtonText: '取消'
    });
  } catch {
    return; // User cancelled
  }
  const command = id === 1 ? SettingTypeEnum.CLEAR_COMP1_HOURS : SettingTypeEnum.CLEAR_COMP2_HOURS;
  if (await executePlcCommand(command)) {
    TLSuccess(`壓縮機 ${id} 運轉時數重置指令已發送！`);
  }
};



const executeMarkerCommand = async () => {
  const cmd = activeMarkerCommand.value;
  if (!cmd) return;
  const stateText = markerToggleOn.value ? 'ON' : 'OFF';
  const name = `${activeMarker.value?.label || activeMarker.value?.code}：${stateText}`;
  try {
    await ElMessageBox.confirm(`確定要將「${activeMarker.value?.label || activeMarker.value?.code}」設為 ${stateText} 嗎？`, '確認設定', {
      type: 'warning',
      confirmButtonText: '確定',
      cancelButtonText: '取消'
    });
  } catch {
    return; // User cancelled
  }
  // 由後端發布 MQTT 並確認 PLC 完成暫存器，最長約 10 秒
  const loadingInstance = ElLoading.service({ lock: true, text: '等待 PLC 回報完成...', background: 'rgba(0, 0, 0, 0.8)' });
  try {
    if (await executePlcCommand(cmd.command, markerToggleOn.value ? cmd.onValue : cmd.offValue)) {
      TLSuccess(`「${name}」已完成`);
      showMarkerModal.value = false;
      fetchRegisters();
    }
  } finally {
    loadingInstance.close();
  }
};

// 呼叫後端執行設定 API (後端負責發布 MQTT、寫入稽核與設定紀錄)
const executePlcCommand = async (command: SettingTypeEnum, value?: number): Promise<boolean> => {
  try {
    const res = await httpOperations.post('/api/v1/plc-control/execute', {
      command,
      trainCode: String(trainNo.value),
      carNo: Number(carNo.value),
      endPos: Number(endPosId.value),
      value
    }, { meta: { loading: false } });
    if (res?.success) {
      // 後端會依 sensors 完成暫存器確認的指令 (confirmed === false 表示 PLC 逾時未回報完成)
      if (res.data?.confirmed === false) {
        TLError(res.data.confirmMessage || 'PLC 未回報完成');
        return false;
      }
      return true;
    }
    TLError(res?.message || '設定指令送出失敗');
  } catch (err: any) {
    console.error('Execute PLC command error:', err);
    TLError(err?.message || '設定指令送出失敗');
  }
  return false;
};

const setFreshAirDamper = async (val: number) => {
  if (isDamperSettingLocked.value) return;
  freshAirDamperPos.value = val;
  if (await executePlcCommand(SettingTypeEnum.FRESH_AIR_DAMPER, val)) {
    TLSuccess(`新鮮空氣擋板指令已發送：${freshAirDamperOptions.value.find(o => o.value === val)?.label || `${val}%`}`);
  }

  // 畫面全螢幕 loading 2 秒
  triggerActionLoading();

  // 執行後，畫面延遲 2 秒避免連續重複點擊
  withLockDelay(isDamperSettingLocked);
};

const setEmergAirDamper = async (val: number) => {
  if (isDamperSettingLocked.value) return;
  emergAirDamper.value = val;
  if (await executePlcCommand(SettingTypeEnum.EMERGENCY_AIR_SUPPLY, val)) {
    TLSuccess(`緊急供氣擋板指令已發送：${val === 2 ? '開啟' : '關閉'}`);
  }

  // 畫面全螢幕 loading 2 秒
  triggerActionLoading();

  // 執行後，畫面延遲 2 秒避免連續重複點擊
  withLockDelay(isDamperSettingLocked);
};

const syncStatusToRegisters = () => {
  modbusRegisters.value.forEach(reg => {
    const prevRaw = reg.rawValue;
    let updated = false;

    if (reg.sensorCode === 'D40001') {
      const modeEntry = mode.value ? Object.entries(SYSTEM_MODE_MAP).find(([_, val]) => val === mode.value) : null;
      const modeVal = modeEntry ? Number(modeEntry[0]) : 2;

      reg.rawValue = modeVal;
      reg.sensorValue = String(modeVal);
      updated = prevRaw !== modeVal;
    }
    else if (reg.sensorCode === 'D40004') {
      const rawTemp = returnTemp.value !== null ? Math.round(returnTemp.value * 10) : 0;
      reg.rawValue = rawTemp;
      reg.sensorValue = returnTemp.value !== null ? returnTemp.value.toFixed(1) : '';
      updated = prevRaw !== rawTemp;
    }
    else if (reg.sensorCode === 'D40005') {
      reg.rawValue = compressors.value[0].lowPress;
      reg.sensorValue = String(compressors.value[0].lowPress);
      updated = prevRaw !== compressors.value[0].lowPress;
    }
    else if (reg.sensorCode === 'D40006') {
      reg.rawValue = compressors.value[0].highPress;
      reg.sensorValue = String(compressors.value[0].highPress);
      updated = prevRaw !== compressors.value[0].highPress;
    }
    else if (reg.sensorCode === 'D40007') {
      reg.rawValue = compressors.value[1].lowPress;
      reg.sensorValue = String(compressors.value[1].lowPress);
      updated = prevRaw !== compressors.value[1].lowPress;
    }
    else if (reg.sensorCode === 'D40008') {
      reg.rawValue = compressors.value[1].highPress;
      reg.sensorValue = String(compressors.value[1].highPress);
      updated = prevRaw !== compressors.value[1].highPress;
    }

    if (updated) {
      reg.isChanging = true;
      setTimeout(() => { reg.isChanging = false; }, 800);
    }
  });
};

const displayRegisterValue = (reg: ModbusRegisterRow) => {
  if (!isDeviceConnected.value) return '--';
  return (reg.sensorValue !== null && reg.sensorValue !== undefined && reg.sensorValue !== '') ? String(reg.sensorValue) : '--';
};

const displayRegisterRawValue = (reg: ModbusRegisterRow) => {
  if (!isDeviceConnected.value) return '--';
  return (reg.rawValue !== null && reg.rawValue !== undefined) ? reg.rawValue : '--';
};

const onReload = () => {
  isDeviceConnected.value = false;
  lastMsgTime.value = null;
  fetchRegisters();
};

const handlePlcReset = () => {
  ElMessageBox.confirm("確定要發送重置復歸指令給此端點的 PLC 嗎？", "重置復歸", {
    type: "warning",
    confirmButtonText: "確定",
    cancelButtonText: "取消"
  }).then(async () => {
    if (await executePlcCommand(SettingTypeEnum.RESET_ALL)) {
      TLSuccess("重置復歸指令已發送！");
    }
  }).catch(() => {
    // User cancelled
  });
};

const handleClearAcHours = () => {
  ElMessageBox.confirm("確定要清除此端點的空調運轉時數嗎？此操作無法復原。", "空調時數重置", {
    type: "warning",
    confirmButtonText: "確定",
    cancelButtonText: "取消"
  }).then(async () => {
    if (await executePlcCommand(SettingTypeEnum.CLEAR_AC_HOURS)) {
      TLSuccess("空調運轉時數重置指令已發送！");
    }
  }).catch(() => {
    // User cancelled
  });
};

const openBatchTempModal = (type: 'temperature' | 'freshAir' | 'emergAir' = 'temperature') => {
  batchSettingType.value = type;
  // 預設填入當前端點的即時/設定數值
  batchTemp.value = setTemp.value !== null ? setTemp.value : 24.0;
  batchFreshAirDamperPos.value = freshAirDamperPos.value || 0;
  batchEmergAirDamper.value = emergAirDamper.value || 1;
  showBatchTempModal.value = true;
};

const handleBatchTempAdjust = (amount: number) => {
  const newTemp = parseFloat((batchTemp.value + amount).toFixed(1));
  if (newTemp >= 16 && newTemp <= 30) {
    batchTemp.value = newTemp;
  }
};

const handleBatchDamperAdjust = () => {
  // 彈窗內調整暫存值，無需在此提前鎖定
};

const handleBatchTempDialogClose = async (res: any) => {
  if (res?.success) {
    await handleBatchTempSubmit();
  }
  showBatchTempModal.value = false;
};

const handleBatchTempSubmit = async () => {
  if (isBatchSettingLocked.value) return;

  const currentTrainNo = trainNo.value;

  // 依據選擇的單一設定類型組裝 Register 與日誌資訊
  if (batchSettingType.value === 'temperature') {
    const targetTemperature = batchTemp.value;
    isBatchSettingLocked.value = true;

    const loadingInstance = ElLoading.service({
      lock: true,
      text: `正在批次設定 8 端點目標溫度 (${targetTemperature}°C) 並等待 PLC 確認...`,
      background: 'rgba(0, 0, 0, 0.7)'
    });

    try {
      // 直接向後端發送 8 端點批次溫度命令 (由後端自動從 DB 載入 8 台設備並執行閉環驗證)
      const res = await httpOperations.post('/api/v1/equipments/batch-set-temperature', {
        trainCode: String(currentTrainNo),
        targetTemperature: targetTemperature
      }, { meta: { loading: false } });

      const resData = res?.data;
      const isBatchSuccess = Boolean(res?.success && resData?.success);

      if (isBatchSuccess) {
        TLSuccess(`8 個端點溫度設定成功！目標溫度：${targetTemperature.toFixed(1)}°C (全數 PLC 已確認)`);
        setTemp.value = targetTemperature;
        syncStatusToRegisters();
      } else {
        TLWarning(res?.message || resData?.message || '部分端點 PLC 尚未確認，請查看審計日誌');
      }
    } catch (err: any) {
      console.error('Failed to batch set temperature via backend API:', err);
      TLError(err?.message || '批次設定溫度請求失敗');
    } finally {
      loadingInstance.close();
      withLockDelay(isBatchSettingLocked, 2000);
    }
    return;
  }

  // 整理 8 個端點供擋板類設定使用 (4 車廂 × 2 端點)
  const targets: { carNo: number; endPos: number }[] = [];
  for (let c = 1; c <= 4; c++) {
    const cNo = carType.value * 1000 + c * 100 + (currentTrainNo % 100);
    targets.push({ carNo: cNo, endPos: 1 });
    targets.push({ carNo: cNo, endPos: 2 });
  }

  let registersPayload: Record<string, number> = {};
  let successMsg = '';
  let logValue = '';
  let settingTypeEnum = SettingTypeEnum.FRESH_AIR_DAMPER;

  if (batchSettingType.value === 'freshAir') {
    const damperVal = batchFreshAirDamperPos.value;
    registersPayload = {
      D40212: damperVal
    };
    const label = freshAirDamperOptions.value.find(o => o.value === damperVal)?.label || `${damperVal}%`;
    successMsg = `8 個端點新鮮空氣擋板開度指令已發送：${label}`;
    logValue = `8端點批次設定新鮮空氣擋板: ${label} (D40212: ${damperVal})`;
    settingTypeEnum = SettingTypeEnum.FRESH_AIR_DAMPER;
    freshAirDamperPos.value = damperVal;
  } else if (batchSettingType.value === 'emergAir') {
    const emergVal = batchEmergAirDamper.value;
    registersPayload = {
      D40214: emergVal
    };
    const stateText = emergVal === 2 ? '開啟' : '關閉';
    successMsg = `8 個端點緊急供氣擋板指令已發送：${stateText}`;
    logValue = `8端點批次設定緊急供氣擋板: ${stateText} (D40214: ${emergVal})`;
    settingTypeEnum = SettingTypeEnum.EMERGENCY_AIR_SUPPLY;
    emergAirDamper.value = emergVal;
  }

  // 逐一發送 MQTT 指令至 8 個端點 (擋板類)
  targets.forEach(({ carNo: cNo, endPos: ep }) => {
    const topic = `TYMC/AIR/SET/${currentTrainNo}/${cNo}/${ep}`;
    const payload = {
      events: 'set_value',
      trainCode: String(currentTrainNo),
      carNo: cNo,
      endPos: ep,
      register: registersPayload
    };
    publish(topic, payload);
  });

  // 更新當前頁面的暫存器
  syncStatusToRegisters();
  TLSuccess(successMsg);

  // 記錄 setting log
  httpOperations.post('/api/v1/setting-logs', {
    settingType: settingTypeEnum,
    train: String(currentTrainNo),
    carNo: Number(carNo.value),
    value: logValue,
    topic: `TYMC/AIR/SET/${currentTrainNo}/+/+`,
    payload: JSON.stringify({
      settingType: batchSettingType.value,
      registers: registersPayload,
      endpointsCount: targets.length,
      targets
    })
  }).catch(err => {
    console.error('Failed to log batch setting:', err);
  });

  // 畫面全螢幕 loading 2 秒
  triggerActionLoading();

  // 送出後鎖定 2 秒延遲，避免連續重複送出
  withLockDelay(isBatchSettingLocked);
};

const openTrend = (reg: ModbusRegisterRow) => {
  selectedRegister.value = reg;
  showTrendModal.value = true;
};

// ==========================================
// 10. Watchers & Lifecycle Hooks
// ==========================================

// 監聽路由參數變更，更新本地狀態並載入資料
watch(
  () => [route.params.carNo, route.params.endPos],
  ([newCar, newEp]) => {
    if (newCar !== undefined && newEp !== undefined) {
      carNo.value = Number(newCar);
      endPosId.value = Number(newEp);
      onReload();
    }
  }
);

// 統計狀態更新
watch([returnTemp, setTemp, mode], () => {
  syncStatusToRegisters();
});

// 監聽新鮮空氣擋板控制完成 (D40213 顯示)
watch(() => modbusRegisters.value.find(s => s.sensorCode === 'D40213')?.sensorValue, (val) => {
  if (val !== undefined && val !== null && val !== '') {
    freshAirDamperPos.value = Number(val);
  }
});

// 監聽緊急通風擋板完成 (D40215 顯示)
watch(() => modbusRegisters.value.find(s => s.sensorCode === 'D40215')?.sensorValue, (val) => {
  if (val !== undefined && val !== null && val !== '') {
    emergAirDamper.value = Number(val);
  }
});

// 當 MQTT 連線成功時，自動發送讀取設備初始狀態請求
watch(isMqttConnected, (connected) => {
  if (connected) {
    onReload();
  }
});



// 當 carVin 解析出來時，重新撈取暫存器設定
watch(currentCarVin, (newVin) => {
  if (newVin) {
    fetchRegisters();
  }
});

onMounted(async () => {
  await loadCarConfig();
  await fetchCars();
  await fetchInitialSensors();
  fetchMapConfig();
  fetchValueLabels();
  fetchRegisters();

  const brokerHost = import.meta.env.VITE_MQTT_BROKER;
  connect(`ws://${brokerHost}:9001`);
  
  if (isMqttConnected.value) {
    onReload();
  }

  // 每 5 秒檢查 MQTT 連線狀態，若中斷則嘗試重新連線
  mqttCheckInterval = setInterval(() => {    
    if (!isMqttConnected.value) {
      console.warn('[MQTT Status Check] MQTT disconnected, attempting to reconnect...');
      connect(`ws://${brokerHost}:9001`);
    }
  }, 5000);

  // 啟動心跳檢測：每 1 秒檢查一次是否超過 5 秒未收到訊息
  heartbeatInterval = setInterval(() => {
    const now = Date.now();
    if (isDeviceConnected.value && lastMsgTime.value && (now - lastMsgTime.value > HEARTBEAT_TIMEOUT)) {
      console.warn(`[Heartbeat Timeout] Single end-pos exceeded ${HEARTBEAT_TIMEOUT / 1000}s without MQTT data. Setting offline.`);
      isDeviceConnected.value = false;
    }
  }, HEARTBEAT_CHECK_INTERVAL);

  const mqttTopicPrefix = import.meta.env.VITE_MQTT_TOPIC_PREFIX || 'TYMC/AIR';
  logger.info("trainNo.value", trainNo.value);
  logger.info("carNo.value", carNo.value);
  logger.info("endPosId.value", endPosId.value);
  logger.info(`${mqttTopicPrefix}/${trainNo.value}/${carNo.value}/#`);
  subscribe(`${mqttTopicPrefix}/${trainNo.value}/${carNo.value}/#`, (topic: string, data: unknown) => {
    const payload = data as MqttPayload;
    //logger.info('single-end-pos', topic, data);
    const payloadCarNo = payload.carNo !== undefined ? Number(payload.carNo) : (payload.carVin !== undefined ? Number(payload.carVin) : undefined);
    
    if (payload && payloadCarNo === carNo.value && Number(payload.endPos) === endPosId.value) {   
      const reg = payload.register || payload || {};
      isDeviceConnected.value = true;
      lastMsgTime.value = Date.now();

      if (reg.D40001 !== undefined) {
        const modeKey = reg.D40001.toString() as SystemModeKey;
        mode.value = SYSTEM_MODE_MAP[modeKey] || '未知';
      }
      
      if (reg.D40004 !== undefined) {
        returnTemp.value = parseFloat((Number(reg.D40004) / 10).toFixed(1));
      }
      if (reg.D40201 !== undefined) {
        setTemp.value = parseFloat((Number(reg.D40201) / 10).toFixed(1));
      }

      updateCompressorStatus({ compressors: compressors.value }, reg);
      // 新鮮空氣檔版位置 (顯示完成: D40213)
      if (reg.D40213 !== undefined && reg.D40213 !== null) freshAirDamperPos.value = Number(reg.D40213);
      // 緊急供氣檔版位置 (顯示完成: D40215)
      if (reg.D40215 !== undefined && reg.D40215 !== null) emergAirDamper.value = Number(reg.D40215);

      modbusRegisters.value.forEach(r => {
        const plcAddress = 40001 + r.address;
        const key = `D${plcAddress}`;
        
        if (reg[key] !== undefined) {
          const rawVal = Number(reg[key]);
          if (r.rawValue !== rawVal) {
            r.rawValue = rawVal;
            r.sensorValue = r.scale ? (rawVal * r.scale).toFixed(r.scale === 1 ? 0 : 1) : String(rawVal);
            r.isChanging = true;
            setTimeout(() => { r.isChanging = false; }, 800);
          }
        }
      });

      syncStatusToRegisters();
    }
  });
});

onUnmounted(() => {
  if (mqttCheckInterval) clearInterval(mqttCheckInterval);
  if (heartbeatInterval) clearInterval(heartbeatInterval);
});
</script>

<template>
  <div 
    ref="pageContainerRef"
    :class="[
      'w-full min-h-screen transition-colors',
      isFullscreen ? 'bg-slate-100 p-4 sm:p-6 overflow-y-auto h-screen' : 'pb-24 sm:pb-8'
    ]"
  >
    <!-- 導航麵包屑 -->
    <div v-if="!isFullscreen" class="w-full mb-6">
      <Breadcrumb :title="`${carInfo.name} - ${endPos.name} 狀態`" :items="breadcrumbItems" />
    </div>

    <div class="w-full px-4 max-w-[1600px] mx-auto space-y-6">
      <!-- 整合的頂部控制與狀態面板 (RWD 整合型) -->
      <div class="bg-white/80 backdrop-blur-md p-4 sm:p-6 rounded-3xl border border-slate-200/60 shadow-sm animate-fade-in">
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <!-- 左側資訊區：標題與狀態資訊 -->
          <div class="flex items-center gap-4 flex-grow">
            <div class="flex flex-col gap-1.5">
              <div class="flex items-center gap-3">
                <h1 class="text-xl sm:text-2xl font-black text-slate-800 tracking-tight whitespace-nowrap m-0">
                  {{ carNo }}車廂-{{ endPos.name }}
                </h1>
                
                <BaseButton 
                  @click="onReload"
                  variant="default"
                  mode="outline"
                  class="rounded-xl px-2.5 py-1 flex items-center justify-center border-slate-200 text-slate-600 hover:bg-slate-50 shrink-0 shadow-sm"
                  title="重新整理"
                >
                  <BaseIcon :path="mdiRefresh" :w="'w-6'" :h="'h-6'" size="18" />
                  <span class="hidden xs:inline ml-1 text-xs font-bold">重新整理</span>
                </BaseButton>

                <BaseButton 
                  @click="handlePlcReset"
                  :disabled="!isDeviceConnected"
                  variant="default"
                  mode="outline"
                  class="rounded-xl px-2.5 py-1 flex items-center justify-center border-rose-200 text-rose-600 hover:bg-rose-50 shrink-0 shadow-sm disabled:opacity-50"
                  title="PLC 復歸重置"
                >
                  <BaseIcon :path="mdiPower" :w="'w-6'" :h="'h-6'" size="18" />
                  <span class="hidden xs:inline ml-1 text-xs font-bold">重置復歸</span>
                </BaseButton>

                <BaseButton
                  @click="handleClearAcHours"
                  :disabled="!isDeviceConnected"
                  variant="default"
                  mode="outline"
                  class="rounded-xl px-2.5 py-1 flex items-center justify-center border-rose-200 text-rose-600 hover:bg-rose-50 shrink-0 shadow-sm disabled:opacity-50"
                  title="清除空調運轉時數 (D40228)"
                >
                  <BaseIcon :path="mdiClockOutline" :w="'w-6'" :h="'h-6'" size="18" />
                  <span class="hidden xs:inline ml-1 text-xs font-bold">空調時數重置</span>
                </BaseButton>
              </div>
              
              <div class="flex flex-wrap items-center gap-3">
                <!-- MQTT 連線狀態 -->
                <div class="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-full border border-slate-200 shrink-0 shadow-sm">
                  <div :class="['w-3.5 h-3.5 rounded-full', isMqttConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-600']"></div>
                  <span class="text-xs font-black text-emerald-600 uppercase tracking-wider">MQTT Broker</span>
                </div>
                <!-- 端點連線狀態 -->
                <div class="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 rounded-full border border-slate-200 shrink-0 shadow-sm">
                  <div :class="['w-3.5 h-3.5 rounded-full', isDeviceConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500']"></div>
                  <span class="text-xs font-black text-slate-600 tracking-wider">端點狀態: {{ isDeviceConnected ? '已連線' : '已離線' }}</span>
                </div>
                <!-- 實體 IP -->
                <div class="text-sm text-slate-400 font-semibold shrink-0">
                  實體 IP: <span class="font-mono text-slate-600 bg-slate-100/50 px-1.5 py-0.5 rounded border border-slate-200/50">{{ endPos.address }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 右側控制與狀態區：切換按鈕組與營運狀態 Badge -->
          <div class="flex flex-col gap-3 lg:items-start shrink-0 w-full lg:w-auto">
            <!-- 顯示模式切換 (分段按鈕組) -->
            <div class="flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200 shadow-inner w-full sm:w-auto shrink-0">
              <BaseButton 
                @click="activeTab = 'dashboard'"
                :colorClass="activeTab === 'dashboard' 
                  ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-sm font-bold scale-102 rounded-lg px-3.5 py-1.5 text-md whitespace-nowrap' 
                  : 'text-slate-500 hover:text-slate-800 bg-transparent rounded-lg px-3.5 py-1.5 text-md whitespace-nowrap'"
                :icon="'mdiMonitorDashboard'"
              >
                儀表板
              </BaseButton>
              <BaseButton 
                @click="activeTab = 'map'"
                :colorClass="activeTab === 'map' 
                  ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-sm font-bold scale-102 rounded-lg px-3.5 py-1.5 text-md whitespace-nowrap' 
                  : 'text-slate-500 hover:text-slate-800 bg-transparent rounded-lg px-3.5 py-1.5 text-md whitespace-nowrap'"
                :icon="'mdiMap'"
              >
                感測器圖面
              </BaseButton>
            </div>

            <!-- 車廂與端點切換列 -->
            <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
              <!-- 切換車廂 (整合按鈕組) -->
              <div class="flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200 shadow-inner w-full sm:w-auto overflow-x-auto scrollbar-none">
                <BaseButton 
                  v-for="opt in carOptions" 
                  :key="opt.value"
                  @click="handleCarChange(opt.value)"
                  :colorClass="normalizedCarNo === opt.value 
                    ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-sm font-bold scale-102 rounded-lg px-3.5 py-1.5 text-md whitespace-nowrap' 
                    : 'text-slate-500 hover:text-slate-800 bg-transparent rounded-lg px-3.5 py-1.5 text-md whitespace-nowrap'"
                  :icon="'mdiTrain'"
                >
                  {{ opt.name }}
                </BaseButton>
              </div>

              <!-- 切換端點 (整合按鈕組) -->
              <div class="flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200 shadow-inner w-full sm:w-auto shrink-0">
                <BaseButton 
                  v-for="opt in endpointsOptions" 
                  :key="opt.value"
                  @click="handleEndpointChange(opt.value)"
                  :colorClass="endPosId === opt.value 
                    ? 'bg-blue-700 hover:bg-blue-800 text-white shadow-sm font-bold scale-102 rounded-lg px-5 py-1.5 text-md whitespace-nowrap' 
                    : 'text-slate-500 hover:text-slate-800 bg-transparent rounded-lg px-5 py-1.5 text-md whitespace-nowrap'"
                  :icon="'mdiGauge'"
                >
                  {{ opt.value }}端
                </BaseButton>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 核心狀態監控網格 -->
      <div v-if="activeTab === 'dashboard'" class="grid grid-cols-1 lg:grid-cols-12 gap-3">
        <!-- 溫度與模式控制面版 (左側佔 7 欄) -->
        <div class="lg:col-span-7 bg-white rounded-2xl p-4 border border-slate-200/60 shadow-sm flex flex-col justify-between space-y-4">
          <div class="flex justify-between items-center pb-2 border-b border-slate-100">
            <h2 class="text-lg font-black text-slate-800 flex items-center gap-2">
              <BaseIcon :path="mdiGauge" class="text-primary-600" w="w-8" h="h-8" size="28" />
              溫度與運行模式調整
            </h2>
            <div class="flex items-center gap-2">
              <BaseButton 
                @click="openBatchTempModal"
                variant="default"
                mode="outline"
                class="rounded-lg px-2.5 py-1 flex items-center justify-center border-blue-200 text-blue-600 hover:bg-blue-50 text-xs font-bold shadow-sm"
                title="同時設定 8 個端點目標溫度"
              >
                <BaseIcon :path="mdiThermometer" :w="'w-4'" :h="'h-4'" size="16" />
                <span class="ml-1">8端點同步設定</span>
              </BaseButton>
              <span class="hidden sm:inline text-xs text-slate-400 font-bold uppercase tracking-wider">PLC Control</span>
            </div>
          </div>
        <!-- 切換控制模式 (OPERATION MODE) -->
        <div class="space-y-2">
          <span class="text-xs font-black text-slate-400 uppercase tracking-widest block">控制模式 (OPERATION MODE)</span>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 border border-slate-200/50 rounded-xl p-3">
            <div  
              v-for="opt in operationModes"
              :key="opt.value"
              :class="[
                'py-2.5 px-3 rounded-xl font-black text-sm flex flex-row items-center justify-center gap-2 border transition-all duration-300',
                (isDeviceConnected && mode === opt.value) 
                  ? opt.activeClass 
                  : 'bg-white text-slate-500 border-slate-200 opacity-60'
              ]"
            >
              <BaseIcon :path="opt.icon" w="w-7" h="w-7" size="24" />
              {{ opt.label }}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <!-- 圓形回風溫度儀表板 -->
            <div class="flex flex-col items-center justify-center p-4 bg-slate-50/50 rounded-xl border border-slate-100">
              <span class="text-xs font-black text-slate-400 uppercase tracking-widest mb-2">目前回風溫度 (RETURN AIR)</span>
              <div class="relative w-32 h-32 flex items-center justify-center">
                <!-- SVG 溫度圓環形儀表板 -->
                <svg class="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                  <defs>
                    <linearGradient id="tempGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="#3b82f6" />
                      <stop offset="60%" stop-color="#10b981" />
                      <stop offset="100%" stop-color="#f59e0b" />
                    </linearGradient>
                  </defs>
                  <circle cx="80" cy="80" r="68" stroke="#e2e8f0" stroke-width="12" fill="transparent" />
                  <circle 
                    cx="80" 
                    cy="80" 
                    r="68" 
                    stroke="url(#tempGradient)" 
                    stroke-width="12" 
                    fill="transparent" 
                    :stroke-dasharray="2 * Math.PI * 68" 
                    :stroke-dashoffset="(isDeviceConnected && returnTemp !== null) ? (2 * Math.PI * 68 * (1 - Math.min(Math.max(returnTemp, 10), 40) / 40)) : (2 * Math.PI * 68)" 
                    stroke-linecap="round"
                    class="transition-all duration-500 ease-out"
                  />
                </svg>
                <div class="absolute flex flex-col items-center">
                  <span class="text-3xl font-black text-slate-800 font-mono tracking-tighter">{{ (isDeviceConnected && returnTemp !== null) ? returnTemp.toFixed(1) : '--' }}</span>
                  <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">°C</span>
                </div>
              </div>
              
              <!-- 狀態反饋說明 -->
              <div class="mt-2 flex items-center gap-1.5 px-3 py-1 bg-white rounded-full border border-slate-100 shadow-sm text-xs font-bold text-slate-500">
                <BaseIcon :path="'mdiThermometer'" size="14" class="text-blue-500" />
                溫度回差 (±0.5°C)
              </div>
            </div>

            <!-- 設定溫度控制與調整 -->
            <div class="flex flex-col justify-center space-y-3 p-4 bg-slate-50/50 rounded-xl border border-slate-100">
              <span class="text-xs font-black text-slate-400 uppercase tracking-widest block">目標設定溫度 (TARGET TEMP)</span>
              
              <div class="flex items-center justify-between">
                <BaseButton
                  @click="handleTempAdjust(-0.5)"
                  :disabled="!isDeviceConnected || isTempSettingLocked"
                  variant="default"
                  mode="outline"
                  class="w-12 h-12 rounded-xl border-slate-200 shadow-sm flex items-center justify-center"
                  title="減少 0.5°C"
                >
                  <BaseIcon :path="mdiMinus" size="20" />
                </BaseButton>
 
                <div class="text-center">
                  <span class="text-4xl font-black font-mono text-primary-700 tracking-tighter">{{ (isDeviceConnected && setTemp !== null) ? setTemp.toFixed(1) : '--' }}</span>
                  <span class="text-sm font-bold text-slate-400 ml-1">°C</span>
                </div>

                <BaseButton
                  @click="handleTempAdjust(0.5)"
                  :disabled="!isDeviceConnected || isTempSettingLocked"
                  variant="default"
                  mode="outline"
                  class="w-12 h-12 rounded-xl border-slate-200 shadow-sm flex items-center justify-center"
                  title="增加 0.5°C"
                >
                  <BaseIcon :path="mdiPlus" size="20" />
                </BaseButton>
              </div>

              <!-- 拖拉滑桿 -->
              <BaseRangeSlider
                v-model="setTemp"
                @change="setTargetTemp"
                :min="16"
                :max="30"
                :step="0.5"
                :disabled="!isDeviceConnected || isTempSettingLocked"
                minLabel="16.0°C"
                midLabel="舒適值 (24°C)"
                maxLabel="30.0°C"
              />
            </div>
        </div>
        </div>

        <!-- 壓縮機狀態面版 (右側佔 5 欄) -->
        <div class="lg:col-span-5 bg-white rounded-2xl p-4 border border-slate-200/60 shadow-sm flex flex-col space-y-4">
          <div class="flex justify-between items-center pb-2 border-b border-slate-100">
            <h2 class="text-lg font-black text-slate-800 flex items-center gap-2">
              <BaseIcon :path="mdiAirConditioner" class="text-primary-600" w="w-8" h="h-8" size="24"/>
              擋板位置與壓縮機狀態
            </h2>
            <div class="flex items-center gap-2">
              <BaseButton 
                @click="openBatchTempModal('freshAir')"
                variant="default"
                mode="outline"
                class="rounded-lg px-2 py-1 flex items-center justify-center border-emerald-200 text-emerald-600 hover:bg-emerald-50 text-xs font-bold shadow-sm"
                title="同時設定 8 個端點新鮮空氣或緊急供氣擋板"
              >
                <BaseIcon :path="mdiWeatherWindy" :w="'w-4'" :h="'h-4'" size="16" />
                <span class="ml-1">8端點同步設定</span>
              </BaseButton>
              <span class="hidden sm:inline text-xs text-slate-400 font-bold uppercase tracking-wider">Stats</span>
            </div>
          </div>
          <!-- 擋板控制區 -->
          <div class="space-y-3 pt-3">
            <span class="text-xs font-black text-slate-400 uppercase tracking-widest block">擋板控制 (DAMPER CONTROL)</span>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

              <!-- 新鮮空氣擋板開度 -->
              <div class="p-3.5 bg-slate-50/50 rounded-xl border border-slate-100 space-y-2">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-black text-slate-500 uppercase tracking-wide">新鮮空氣擋板開度</span>
                  <!-- <span class="ml-auto text-[10px] font-bold text-slate-400" title="設定觸發: D40212 / 顯示完成: D40213">觸發 D40212 / 完成 D40213</span> -->
                </div>
                <BaseRangeSlider
                  v-model="freshAirDamperPos"
                  @change="setFreshAirDamper"
                  :min="0"
                  :max="100"
                  :step="25"
                  :disabled="!isDeviceConnected || isDamperSettingLocked"
                  :labels="['0', '25', '50', '75', '100']"
                />
              </div>

              <!-- 緊急供氣擋板 -->
              <div class="p-3.5 bg-slate-50/50 rounded-xl border border-slate-100 flex flex-col justify-between gap-3 h-full">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-black text-slate-500 uppercase tracking-wide">開啟緊急供氣擋板</span>
                  <!-- <span class="ml-auto text-[10px] font-bold text-slate-400" title="設定觸發: D40214 / 顯示完成: D40215">觸發 D40214 / 完成 D40215</span> -->
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm font-black" :class="emergAirDamper === 2 ? 'text-rose-600' : 'text-slate-400'">
                    {{ emergAirDamper === 2 ? '開啟' : '關閉' }}
                  </span>
                  <BaseSwitch
                    :modelValue="emergAirDamper === 2"
                    @update:modelValue="setEmergAirDamper($event ? 2 : 1)"
                    :disabled="!isDeviceConnected || isDamperSettingLocked"
                    activeColor="bg-rose-500"
                    inactiveColor="bg-slate-300"
                  />
                </div>
              </div>

            </div>
          </div>
          <!-- 兩組壓縮機 -->
          <div class="space-y-3 flex-1 flex flex-col justify-center">
            <div 
              v-for="comp in compressors" 
              :key="comp.id"
              class="p-3.5 bg-slate-50/50 rounded-xl border border-slate-200/50 space-y-3"
            >
              <div class="flex justify-between items-center">
                <div class="flex items-center gap-2">
                  <span class="w-8 h-8 rounded-lg bg-primary-100 text-primary-700 flex items-center justify-center font-black text-sm font-mono">#{{ comp.id }}</span>
                  <span class="font-black text-slate-700 text-sm">壓縮機 {{ comp.id }}</span>
                </div>
                <div class="flex gap-2">
                  <span 
                    class="px-2.5 py-0.5 rounded-lg text-sm font-black tracking-wider"
                    :class="isDeviceConnected && comp.status === CompressorStatus.ON ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-500'"
                  >
                    {{ isDeviceConnected ? comp.status : '--' }}
                  </span>
                  <span 
                    class="px-2.5 py-0.5 rounded-lg text-sm font-black tracking-wider"
                    :class="isDeviceConnected ? (comp.health === CompressorHealth.Normal ? 'bg-blue-500 text-white' : 'bg-rose-500 text-white') : 'bg-slate-200 text-slate-500'"
                  >
                    {{ isDeviceConnected ? comp.health : '--' }}
                  </span>
                </div>
              </div>

              <!-- 壓力數據指示器 -->
              <div class="grid grid-cols-2 gap-4">
                <!-- 高壓 -->
                <div class="space-y-1">
                  <div class="flex justify-between items-baseline">
                    <span class="text-xs font-black text-slate-400 uppercase">排氣高壓</span>
                    <span class="text-sm font-black font-mono text-rose-600">
                      {{ (isDeviceConnected && comp.highPress !== 0) ? comp.highPress : '--' }}<small class="text-[9px] font-sans text-slate-400 ml-0.5" v-if="isDeviceConnected && comp.highPress !== 0">kPa</small>
                    </span>
                  </div>
                  <!-- 高壓進度條 -->
                  <div class="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      class="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 rounded-full transition-all duration-500 ease-out" 
                      :style="{ width: (isDeviceConnected && comp.highPress !== 0) ? `${Math.min((comp.highPress / 2500) * 100, 100)}%` : '0%' }"
                    ></div>
                  </div>
                </div>

                <!-- 低壓 -->
                <div class="space-y-1">
                  <div class="flex justify-between items-baseline">
                    <span class="text-xs font-black text-slate-400 uppercase">吸氣低壓</span>
                    <span class="text-sm font-black font-mono text-blue-600">{{ isDeviceConnected ? comp.lowPress : '--' }}<small class="text-[9px] font-sans text-slate-400 ml-0.5" v-if="isDeviceConnected">kPa</small></span>
                  </div>
                  <!-- 低壓進度條 -->
                  <div class="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      class="h-full bg-gradient-to-r from-blue-300 to-blue-600 rounded-full transition-all duration-500 ease-out" 
                      :style="{ width: isDeviceConnected ? `${Math.min((comp.lowPress / 600) * 100, 100)}%` : '0%' }"
                    ></div>
                  </div>
                </div>
              </div>

              <!-- 運轉時數 -->
              <div class="flex justify-between items-center pt-2 border-t border-slate-200/70">
                <div class="flex items-baseline gap-2">
                  <span class="text-xs font-black text-slate-400 uppercase">累計運轉時數</span>
                  <span class="text-sm font-black font-mono text-slate-700">
                    {{ isDeviceConnected ? (comp.runHours ?? 0) : '--' }}<small class="text-[9px] font-sans text-slate-400 ml-0.5" v-if="isDeviceConnected">hr</small>
                  </span>
                </div>
                <el-button
                  size="small"
                  plain
                  type="danger"
                  :disabled="!isDeviceConnected"
                  @click="resetCompressorHours(comp.id)"
                >
                  <BaseIcon :path="mdiClockOutline" :w="'w-4'" :h="'h-4'" size="14" class="mr-1" />重置時數
                </el-button>
              </div>
            </div>
          </div>


        </div>
      </div>

      <!-- SvgViewer 畫布 (圖面配置) -->
      <CarSensorMap
        v-else-if="activeTab === 'map'"
        :planUrl="planUrl"
        :markers="mappedSensors"
        @click-marker="handleMarkerClick"
        :heightClass="isFullscreen ? 'h-[calc(100vh-280px)]' : 'h-[500px]'"
      />

      <!-- Modbus 暫存器監測表格 -->
      <div class="bg-white rounded-3xl p-6 border border-slate-200/60 shadow-sm space-y-4">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-100">
          <div>
            <h2 class="text-lg font-black text-slate-800 flex items-center gap-2">
              <BaseIcon :path="mdiFlash" class="text-primary-600" size="20" />
              暫存器即時監測 (Modbus Registers)
            </h2>
            <p class="text-sm text-slate-400 font-bold mt-1 uppercase tracking-wide">
              {{ addressRangeText }}
            </p>
          </div>

          <div class="flex items-center gap-3 w-full sm:w-auto">
            <!-- 搜尋框 -->
            <div class="relative flex-1 sm:flex-initial">
              <input 
                type="text" 
                v-model="registersSearchQuery"
                placeholder="搜尋點位名稱或描述..."
                class="w-full sm:w-64 pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 focus:bg-white transition-all"
              />
              <span class="absolute left-3 top-2.5 text-slate-400">
                <BaseIcon :path="mdiMagnify" size="16" />
              </span>
            </div>
          </div>
        </div>

        <!-- 暫存器表格 (桌機版: lg 以上顯示) -->
        <div class="hidden lg:block overflow-x-auto rounded-2xl border border-slate-100 shadow-inner">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-100 text-slate-500 text-sm font-black uppercase tracking-wider">
                <th class="py-3 px-4 w-20">PLC 位址</th>
                <th class="py-3 px-4">功能說明</th>
                <th class="py-3 px-4 w-28 text-right">換算值</th>
                <th class="py-3 px-4 w-20">單位</th>
                <th class="py-3 px-4 w-28 text-right bg-slate-100/50">原始碼值 (Raw)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm">
              <tr 
                v-for="reg in filteredRegisters" 
                :key="reg.address"
                :class="[
                  'hover:bg-slate-50/80 transition-colors',
                  reg.isChanging ? 'bg-amber-50/50 font-bold transition-all duration-300' : ''
                ]"
              >
                <!-- PLC 位址 (可點擊 → 趨勢圖) -->
                <td
                  class="py-3 px-4 font-mono font-bold text-blue-500 cursor-pointer hover:text-blue-700 hover:underline underline-offset-2 transition-colors select-none"
                  @click="openTrend(reg)"
                  title="點擊查看趨勢圖"
                >
                  {{ 40001 + reg.address }}
                </td>
                
                <!-- 功能說明 -->
                <td class="py-3 px-4 text-slate-500 font-medium">
                  {{ reg.sensorName }}
                </td>
                
                <!-- 換算值 -->
                <td class="py-3 px-4 font-mono font-bold text-slate-800 text-right">
                  {{ displayRegisterValue(reg) }}
                </td>
                
                <!-- 單位 -->
                <td class="py-3 px-4 text-slate-500 font-bold">
                  {{ reg.sensorUnit || '-' }}
                </td>
                
                <!-- 原始碼值 -->
                <td class="py-3 px-4 font-mono text-right bg-slate-50/30 font-bold text-primary-700">
                  {{ displayRegisterRawValue(reg) }}
                </td>
              </tr>

              <tr v-if="filteredRegisters.length === 0">
                <td colspan="5" class="text-center py-8 text-slate-400 font-bold">
                  找不到符合搜尋條件的暫存器資料。
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 暫存器卡片列表 (行動版: lg 以下顯示) -->
        <div class="lg:hidden space-y-4">
          <div 
            v-for="reg in filteredRegisters" 
            :key="reg.address"
            :class="[
              'p-4 bg-slate-50/50 border border-slate-200/60 rounded-2xl flex flex-col gap-3 transition-all duration-300',
              reg.isChanging ? 'bg-amber-50/50 border-amber-200 font-bold' : ''
            ]"
          >
            <!-- 卡片頂部：位址 (可點擊 → 趨勢圖) -->
            <div class="flex justify-between items-center">
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-bold text-slate-400">位址:</span>
                <span
                  class="font-mono text-sm font-black text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 cursor-pointer hover:bg-blue-100 transition-colors select-none"
                  @click="openTrend(reg)"
                  title="點擊查看趨勢圖"
                >
                  {{ 40001 + reg.address }}
                </span>
                <span class="text-[10px] font-mono text-slate-400">({{ reg.address }})</span>
                <!-- 趨勢圖圖示提示 -->
                <svg class="w-3.5 h-3.5 text-blue-400 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                </svg>
              </div>
            </div>

            <!-- 卡片中部：原始值 -->
            <div class="flex justify-end items-center">
              <div class="flex items-baseline gap-1 bg-slate-100/50 px-2.5 py-1 rounded-xl border border-slate-200/50">
                <span class="text-xs text-slate-400 font-bold">Raw:</span>
                <span class="font-mono text-sm font-black text-primary-700">{{ displayRegisterRawValue(reg) }}</span>
              </div>
            </div>

            <!-- 卡片說明：功能描述 -->
            <div class="text-xs text-slate-500 font-medium bg-white/60 p-2.5 rounded-xl border border-slate-100">
              {{ reg.sensorName }}
            </div>

            <!-- 卡片底部：換算值 -->
            <div class="flex justify-between items-center text-xs pt-1 border-t border-slate-100">
              <div class="flex items-center gap-1.5">
                <span class="text-slate-400 font-medium">換算值:</span>
                <span class="font-mono font-black text-slate-800 text-sm">
                  {{ displayRegisterValue(reg) }}
                </span>
                <span class="text-slate-500 font-bold" v-if="isDeviceConnected && reg.sensorUnit">{{ reg.sensorUnit }}</span>
              </div>
            </div>
          </div>

          <!-- 無資料提示 -->
          <div v-if="filteredRegisters.length === 0" class="text-center py-12 bg-slate-50/50 border border-dashed border-slate-200 rounded-2xl text-slate-400 font-bold text-sm">
            找不到符合搜尋條件的暫存器資料。
          </div>
        </div>
      </div>
    </div>

    <!-- ── 趨勢圖 Modal ──────────────────────────────────────────────────────── -->
    <RegisterTrendModal
      v-model:visible="showTrendModal"
      :register="selectedRegister"
      :car-no="carNo"
      :end-pos="endPosId"
    />

    <!-- ── 8 個端點同步設定 Dialog ─────────────────────────────────────────── -->
    <ElDialogCustom
      v-model:visible="showBatchTempModal"
      title="8 個端點同時設定"
      width="560px"
      minHeight="320px"
      action="確認"
      cancel="取消"
      @on-before-close="handleBatchTempDialogClose"
    >
      <div class="py-2 px-1 flex flex-col space-y-4">
        <!-- 說明提示卡 -->
        <div class="bg-blue-50/80 border border-blue-200/70 rounded-xl p-3 flex items-start gap-2.5">
          <BaseIcon :path="mdiThermometer" class="text-blue-600 shrink-0 mt-0.5" :w="'w-5'" :h="'h-5'" size="20" />
          <div class="text-xs text-blue-900 leading-relaxed font-medium">
            此操作將同時針對車組 <span class="font-bold text-blue-700 font-mono">#{{ trainNo }}</span> 的 <span class="font-bold text-blue-700">4 節車廂共 8 個端點 PLC</span> 發送控制指令。
          </div>
        </div>

        <!-- 選擇設定項目 (單選: 每次只能設定一種) -->
        <div class="space-y-1.5">
          <span class="text-xs font-black text-slate-500 uppercase tracking-widest block">選擇設定項目 (每次限選一種)</span>
          <div class="grid grid-cols-3 gap-2">
            <button
              type="button"
              @click="batchSettingType = 'temperature'"
              :class="[
                'p-2.5 rounded-xl border text-xs font-bold flex flex-col items-center justify-center gap-1 transition-all',
                batchSettingType === 'temperature'
                  ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-sm ring-1 ring-blue-400 font-black'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              ]"
            >
              <BaseIcon :path="mdiThermometer" size="20" :class="batchSettingType === 'temperature' ? 'text-blue-600' : 'text-slate-400'" />
              <span>目標溫度</span>
            </button>

            <button
              type="button"
              @click="batchSettingType = 'freshAir'"
              :class="[
                'p-2.5 rounded-xl border text-xs font-bold flex flex-col items-center justify-center gap-1 transition-all',
                batchSettingType === 'freshAir'
                  ? 'bg-emerald-50 border-emerald-500 text-emerald-700 shadow-sm ring-1 ring-emerald-400 font-black'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              ]"
            >
              <BaseIcon :path="mdiWeatherWindy" size="20" :class="batchSettingType === 'freshAir' ? 'text-emerald-600' : 'text-slate-400'" />
              <span>新鮮空氣開度</span>
            </button>

            <button
              type="button"
              @click="batchSettingType = 'emergAir'"
              :class="[
                'p-2.5 rounded-xl border text-xs font-bold flex flex-col items-center justify-center gap-1 transition-all',
                batchSettingType === 'emergAir'
                  ? 'bg-rose-50 border-rose-500 text-rose-700 shadow-sm ring-1 ring-rose-400 font-black'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              ]"
            >
              <BaseIcon :path="mdiAirConditioner" size="20" :class="batchSettingType === 'emergAir' ? 'text-rose-600' : 'text-slate-400'" />
              <span>緊急供氣擋板</span>
            </button>
          </div>
        </div>

        <!-- 1. 目標溫度調整控制區 -->
        <div v-if="batchSettingType === 'temperature'" class="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-4 flex flex-col items-center space-y-4 animate-fade-in">
          <span class="text-xs font-black text-slate-500 uppercase tracking-widest">目標設定溫度 (TARGET TEMPERATURE)</span>

          <!-- 加減按鈕與數值顯示 -->
          <div class="flex items-center justify-center gap-6 w-full">
            <BaseButton
              @click="handleBatchTempAdjust(-0.5)"
              :disabled="isBatchSettingLocked"
              variant="default"
              mode="outline"
              class="w-12 h-12 rounded-xl border-slate-200 shadow-sm flex items-center justify-center hover:bg-white active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              title="減少 0.5°C"
            >
              <BaseIcon :path="mdiMinus" size="22" />
            </BaseButton>

            <div class="text-center min-w-[130px]">
              <span class="text-5xl font-black font-mono text-primary-700 tracking-tighter">{{ batchTemp.toFixed(1) }}</span>
              <span class="text-base font-bold text-slate-400 ml-1">°C</span>
            </div>

            <BaseButton
              @click="handleBatchTempAdjust(0.5)"
              :disabled="isBatchSettingLocked"
              variant="default"
              mode="outline"
              class="w-12 h-12 rounded-xl border-slate-200 shadow-sm flex items-center justify-center hover:bg-white active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              title="增加 0.5°C"
            >
              <BaseIcon :path="mdiPlus" size="22" />
            </BaseButton>
          </div>

          <!-- 拖拉滑桿 -->
          <div class="w-full px-2">
            <BaseRangeSlider
              v-model="batchTemp"
              :disabled="isBatchSettingLocked"
              :min="16"
              :max="30"
              :step="0.5"
              minLabel="16.0°C"
              midLabel="舒適值 (24°C)"
              maxLabel="30.0°C"
            />
          </div>
        </div>

        <!-- 2. 新鮮空氣擋板開度控制區 -->
        <div v-else-if="batchSettingType === 'freshAir'" class="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-4 flex flex-col items-center space-y-4 animate-fade-in">
          <span class="text-xs font-black text-slate-500 uppercase tracking-widest">新鮮空氣擋板開度 (FRESH AIR DAMPER)</span>

          <div class="text-center">
            <span class="text-4xl font-black font-mono text-emerald-600 tracking-tight">
              {{ freshAirDamperOptions.find(o => o.value === batchFreshAirDamperPos)?.label || `${batchFreshAirDamperPos}%` }}
            </span>
          </div>

          <!-- 擋板開度滑桿 -->
          <div class="w-full px-2">
            <BaseRangeSlider
              v-model="batchFreshAirDamperPos"
              @change="handleBatchDamperAdjust"
              :disabled="isBatchSettingLocked"
              :min="0"
              :max="100"
              :step="25"
              :labels="['0', '25', '50', '75', '100']"
            />
          </div>
        </div>

        <!-- 3. 開啟緊急供氣擋板控制區 -->
        <div v-else-if="batchSettingType === 'emergAir'" class="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-4 flex flex-col items-center space-y-4 animate-fade-in">
          <span class="text-xs font-black text-slate-500 uppercase tracking-widest">緊急供氣擋板 (EMERGENCY AIR SUPPLY)</span>

          <div class="flex items-center justify-between w-full max-w-xs px-4 py-3 bg-white rounded-xl border border-slate-200 shadow-sm">
            <span class="text-base font-black" :class="batchEmergAirDamper === 2 ? 'text-rose-600' : 'text-slate-400'">
              {{ batchEmergAirDamper === 2 ? '開啟' : '關閉' }}
            </span>
            <BaseSwitch
              :modelValue="batchEmergAirDamper === 2"
              @update:modelValue="(val) => { batchEmergAirDamper = val ? 2 : 1; handleBatchDamperAdjust(); }"
              :disabled="isBatchSettingLocked"
              activeColor="bg-rose-500"
              inactiveColor="bg-slate-300"
            />
          </div>
        </div>
      </div>
    </ElDialogCustom>

    <!-- 標記詳細資訊 Modal -->
    <ElDialogCustom
      v-model:visible="showMarkerModal"
      :title="activeMarker?.label"
      width="448px"
      minHeight="0px"
      action="確認"
      cancel="關閉"
      :show-action="!!activeMarkerCommand"
      @on-before-close="handleMarkerDialogClose"
    >
      <div v-if="activeMarker" class="space-y-3 text-sm">
        <div class="flex justify-between">
          <span class="font-black text-slate-400">點位代碼</span>
          <span class="font-mono text-slate-700">{{ activeMarker.code }}<template v-if="activeMarker.bitIndex !== null && activeMarker.bitIndex !== undefined"> (Bit {{ activeMarker.bitIndex }})</template></span>
        </div>
        <div class="flex justify-between">
          <span class="font-black text-slate-400">目前數值</span>
          <span class="font-mono font-black text-slate-800">{{ liveMarker?.value }}<template v-if="activeMarker.unit"> {{ activeMarker.unit }}</template></span>
        </div>
        <label v-if="activeMarkerCommand" class="flex items-center justify-between cursor-pointer pt-2 border-t border-slate-100">
          <span class="font-black text-slate-400">設定狀態</span>
          <span class="flex items-center gap-2">
            <span class="font-mono font-black" :class="markerToggleOn ? 'text-emerald-600' : 'text-slate-500'">{{ markerToggleOn ? 'ON' : 'OFF' }}</span>
            <input type="checkbox" v-model="markerToggleOn" class="w-5 h-5 accent-emerald-600 cursor-pointer" />
          </span>
        </label>
      </div>
    </ElDialogCustom>

  </div>
</template>

<style scoped>
@keyframes pulseGlow {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 0.6; }
}

.bg-amber-50\/50 {
  animation: pulseGlow 0.8s ease-in-out infinite alternate;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}

.w-full {
  animation: fadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* 自定義拖拉條 Accent 色與樣式 */
input[type="range"]::-webkit-slider-runnable-track {
  background: #cbd5e1;
  height: 8px;
  border-radius: 9999px;
}
input[type="range"]::-webkit-slider-thumb {
  margin-top: -4px;
}
</style>
