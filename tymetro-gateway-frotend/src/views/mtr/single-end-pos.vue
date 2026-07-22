<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Breadcrumb from '@/components/Breadcrumb.vue';
import BaseIcon from '@/components/BaseIcon.vue';
import BaseButton from '@/components/BaseButton.vue';
import BaseSwitch from '@/components/BaseSwitch.vue';
import BaseRangeSlider from '@/components/BaseRangeSlider.vue';
import RegisterTrendModal from '@/views/mtr/components/RegisterTrendModal.vue';
import { useMQTT } from '@/store/useMQTT';
import { useAlert } from "@/composables/TLAlter";
import { SYSTEM_MODE_MAP, SystemModeKey, CompressorStatus, CompressorHealth } from '@/utils/enums';
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
import SvgViewer from '@/components/SvgViewer.vue';
import httpOperations from '@/utils/http-operations';
import { logger } from '@/utils';
import { 
  mdiWeatherWindy, 
  mdiSnowflake, 
  mdiAirConditioner, 
  mdiRefresh,
  mdiFlash,
  mdiPause,
  mdiGauge,
  mdiPlus,
  mdiMinus,
  mdiMagnify
} from '@mdi/js';

// ==========================================
// 1. Hook & Utilities
// ==========================================
const route = useRoute();
const router = useRouter();
const { TLError, TLWarning, TLInfo, TLSuccess } = useAlert();

// ==========================================
// 2. Core Route State & Derived Computeds
// ==========================================
const carVin = ref(Number(route.params.carVin) || 1101);
const endPosId = ref(Number(route.params.endPos) || 1);
const carInfoMap = ref<Record<number, TrainCarStatus>>({});

const carInfo = computed(() => carInfoMap.value[carVin.value] || carInfoMap.value[1101] || { id: 1101, name: '', ip: '', endpoints: [] });
const epName = computed(() => `端點 ${endPosId.value}`);
const endPos = computed(() => {
  const info = carInfo.value;
  if (!info || !info.endpoints) return { name: '', address: '' };
  return info.endpoints.find(e => e.id === endPosId.value) || { name: '', address: '' };
});
const normalizedCarNo = computed(() => carInfo.value ? carInfo.value.id : 1101);
const trainNo = computed(() => {
  const type = Math.floor(carVin.value / 1000);
  const num = carVin.value % 100;
  return type * 100 + num;
});
const carType = computed(() => Math.floor(carVin.value / 1000));

// ==========================================
// 0. Configuration Parameters
// ==========================================
const TEMP_LOCK_DELAY = 3000; // 設定溫度鎖定延遲時間 (毫秒)
const HEARTBEAT_TIMEOUT = 5000; // 判定斷線超時時間 (毫秒)
const HEARTBEAT_CHECK_INTERVAL = 1000; // 心跳檢查間隔 (毫秒)

// ==========================================
// 3. MQTT Connection & Heartbeat Tracker State
// ==========================================
const { isConnected: isMqttConnected, connect, subscribe, publish } = useMQTT();
const isDeviceConnected = ref(false);
const isTempSettingLocked = ref(false);
const lastMsgTime = ref<number | null>(null);
let mqttCheckInterval: ReturnType<typeof setInterval> | null = null;
let heartbeatInterval: ReturnType<typeof setInterval> | null = null;

// ==========================================
// 4. UI Layout & Navigation States
// ==========================================
const activeTab = ref('dashboard');
const breadcrumbItems = computed(() => [
  { label: '首頁', to: '/dashboard' },
  { label: `${carInfo.value.name} - ${epName.value} 狀態` }
]);

const rawCarOptions = ref<CarOption[]>([]);
const carOptions = ref<CarOption[]>([]);
const endpointsOptions = ref<EndpointOption[]>([]);
const configCarVinsList = ref<CarVinConfig[]>([]);

// ==========================================
// 5. HVAC Status, Damper Controls & Operating Modes
// ==========================================
const mode = ref(''); // 停止 / 自動 / 送風 / 測試
const returnTemp = ref<number | null>(null);
const setTemp = ref<number | null>(null);
const compressors = ref([
  { id: 1, status: CompressorStatus.OFF, health: CompressorHealth.Normal, highPress: 0, lowPress: 0 },
  { id: 2, status: CompressorStatus.OFF, health: CompressorHealth.Normal, highPress: 0, lowPress: 0 }
]);
const freshAirDamperPos = ref<number>(0);
const emergAirDamper = ref<number>(0);

const freshAirDamperOptions = ref<{ value: number; label: string }[]>([]);
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

const mappedSensors = computed(() => {
  return mapTemplateSensors.value.map(s => {
    const matched = modbusRegisters.value.find(reg => reg.sensorCode === s.code);
    if (matched) {
      if (matched.dataType === 'bitmap' && s.bitIndex !== null && s.bitIndex !== undefined) {
        const bitVal = String(matched.sensorValue || '').charAt(15 - s.bitIndex);
        return { ...s, value: bitVal === '1' ? 'ON' : 'OFF' };
      }
      return { ...s, value: String(matched.sensorValue || '0.0') };
    }
    return s;
  });
});

// ==========================================
// 8. Register Trend Modal State
// ==========================================
const showTrendModal = ref(false);
const selectedRegister = ref<ModbusRegisterRow | null>(null);

// ==========================================
// 9. Methods & Event Handlers
// ==========================================

// 車廂及端點切換與載入
const handleCarChange = (newCarNo: number) => {
  carVin.value = newCarNo;
  router.replace(`/mtr/single-end-pos/${newCarNo}/${endPosId.value}`);
};

const handleEndpointChange = (newEndPosId: number) => {
  endPosId.value = newEndPosId;
  router.replace(`/mtr/single-end-pos/${carVin.value}/${newEndPosId}`);
};

const updateCarMap = (carVins: CarVinConfig[], hasPredefinedOptions = false) => {
  const map: Record<number, TrainCarStatus> = {};
  const options: CarOption[] = [];

  carVins.forEach((carVin) => {
    const resolvedCarNo = carVin.carVin || carVin.carNo || carVin.id;    
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
      carVin : resolvedCarNo,
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
    carOptions.value = options;
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
        if (config.carVins && Array.isArray(config.carVins)) {
          configCarVinsList.value = config.carVins;
          updateCarMap(config.carVins, !!config.carOptions);
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

// API 載入數據
const fetchInitialSensors = async () => {
  try {
    const res = await httpOperations.get('/api/v1/sensors/by-group', { registerGroup: 'initial' }, { meta: { loading: false } });
    if (res && res.success) {
      const list = (res.data || []) as SensorData[];
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
        
        if (configCarVinsList.value.length > 0) {
          configCarVinsList.value.forEach((car, index) => {
            const carIndex = index + 1;
            car.trainNo = dbTrainNo;
            car.carVin = type * 1000 + carIndex * 100 + num;
          });
          updateCarMap(configCarVinsList.value, !!rawCarOptions.value.length);
        }
      }
    }
  } catch (error) {
    logger.error("Fetch initial sensors error in single-end-pos:", error);
  }
};

const fetchRegisters = async () => {
  try {
    const params = {
      registerGroup: 'realtime'
    };
    const res = await httpOperations.get('/api/v1/sensors/by-group', params, { meta: { loading: false } });
    if (res && res.success) {
      const list = (res.data || []) as SensorData[];
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
        isChanging: false
      }));
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
          type: m.markerType || 'rect'
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

const setTargetTemp = () => {
  if (setTemp.value === null || isTempSettingLocked.value) return;

  const register = {
     D40200: Math.round(setTemp.value * 10),
     D40202: 1
  };
  const statusPayload = {
    events: "set_value",
    carNo: carVin.value,
    endPos: endPosId.value,
    register: register
  };

  publish(`TYMC/AIR/SET/${trainNo.value}/${carVin.value}/${endPosId.value}`, statusPayload);
  TLSuccess(`控制指令已發送！設定溫度：${setTemp.value}°C，模式：${mode.value}`);
  syncStatusToRegisters();

  // 鎖定設定溫度按鈕與滑桿以避免連續點擊
  isTempSettingLocked.value = true;
  setTimeout(() => {
    isTempSettingLocked.value = false;
  }, TEMP_LOCK_DELAY);
};

const setFreshAirDamper = (val: number) => {
  freshAirDamperPos.value = val;
  const payload = {
    events: 'set_value',
    carNo: carVin.value,
    endPos: endPosId.value,
    register: { D40212: val }
  };
  publish(`TYMC/AIR/SET/${trainNo.value}/${carVin.value}/${endPosId.value}`, payload);
  TLSuccess(`新鮮空氣擋板指令已發送：${freshAirDamperOptions.value.find(o => o.value === val)?.label}`);
};

const setEmergAirDamper = (val: number) => {
  emergAirDamper.value = val;
  const payload = {
    events: 'set_value',
    carNo: carVin.value,
    endPos: endPosId.value,
    register: { D40213: val }
  };
  publish(`TYMC/AIR/SET/${trainNo.value}/${carVin.value}/${endPosId.value}`, payload);
  TLSuccess(`緊急供氣擋板指令已發送：${val === 1 ? '開啟' : '關閉'}`);
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
      carVin.value = Number(newCar);
      endPosId.value = Number(newEp);
      onReload();
    }
  }
);

// 統計狀態更新
watch([returnTemp, setTemp, mode], () => {
  syncStatusToRegisters();
});

// 當 MQTT 連線成功時，自動發送讀取設備初始狀態請求
watch(isMqttConnected, (connected) => {
  if (connected) {
    onReload();
  }
});

// 監聽車廂選單來源變動，同步對應正確車型 vin
watch([rawCarOptions, trainNo, carType], () => {
  if (rawCarOptions.value.length > 0) {
    carOptions.value = rawCarOptions.value.map((opt) => ({
      ...opt,
      value: carType.value * 1000 + opt.value * 100 + (trainNo.value % 100)
    }));
  }
}, { immediate: true });

onMounted(async () => {
  await loadCarConfig();
  await fetchInitialSensors();
  fetchMapConfig();
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

  // 訂閱單點設備狀態主題
  logger.info("trainNo.value", trainNo.value);
  logger.info("carVin.value", carVin.value);
  logger.info("endPosId.value", endPosId.value);
  logger.info(`TYMC/AIR/${trainNo.value}/${carVin.value}/#`);
  subscribe(`TYMC/AIR/${trainNo.value}/${carVin.value}/#`, (topic: string, data: unknown) => {
    const payload = data as MqttPayload;
    logger.info('single-end-pos', topic, data);
    const payloadCarVin = payload.carVin !== undefined ? Number(payload.carVin) : (payload.carNo !== undefined ? Number(payload.carNo) : undefined);
    
    if (payload && payloadCarVin === carVin.value && Number(payload.endPos) === endPosId.value) {   
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

      const D40002 = reg.D40002 !== undefined ? Number(reg.D40002) : undefined;
      if (D40002 !== undefined) {
        if (compressors.value[0]) {
          compressors.value[0].status = ((D40002 >> 4) & 1) === 1 ? CompressorStatus.ON : CompressorStatus.OFF;
        }
        if (compressors.value[1]) {
          compressors.value[1].status = ((D40002 >> 5) & 1) === 1 ? CompressorStatus.ON : CompressorStatus.OFF;
        }
      }

      // 壓縮機 1
      const highP1 = reg.D40006 !== undefined ? reg.D40006 : undefined;
      const lowP1 = reg.D40005 !== undefined ? reg.D40005 : undefined;
      if (compressors.value[0]) {
        if (highP1 !== undefined) {
          compressors.value[0].highPress = Math.round(Number(highP1));
        }
        if (lowP1 !== undefined) {
          compressors.value[0].lowPress = Math.round(Number(lowP1));
        }
      }

      // 壓縮機 2
      const highP2 = reg.D40008 !== undefined ? reg.D40008 : undefined;
      const lowP2 = reg.D40007 !== undefined ? reg.D40007 : undefined;
      if (compressors.value[1]) {
        if (highP2 !== undefined) {
          compressors.value[1].highPress = Math.round(Number(highP2));
        }
        if (lowP2 !== undefined) {
          compressors.value[1].lowPress = Math.round(Number(lowP2));
        }
      }
      if (reg.D40212 !== undefined) freshAirDamperPos.value = Number(reg.D40212);
      if (reg.D40213 !== undefined) emergAirDamper.value = Number(reg.D40213);

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
  <div class="w-full pb-24 sm:pb-8 min-h-screen">
    <!-- 導航麵包屑 -->
    <div class="w-full mb-6">
      <Breadcrumb :title="`${carInfo.name} - ${epName} 狀態`" :items="breadcrumbItems" />
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
                  {{ carInfo.name }} - {{ epName }}
                </h1>
                
                <BaseButton 
                  @click="onReload"
                  variant="default"
                  mode="outline"
                  class="rounded-xl px-2.5 py-1 flex items-center justify-center border-slate-200 text-slate-600 hover:bg-slate-50 shrink-0 shadow-sm"
                >
                  <BaseIcon :path="mdiRefresh" :w="'w-6'" :h="'h-6'" size="18" />
                  <span class="hidden xs:inline ml-1 text-xs font-bold">重新整理</span>
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
            <span class="text-sm text-slate-400 font-bold uppercase tracking-wider">PLC Control Panel</span>
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
            <span class="text-sm text-slate-400 font-bold uppercase tracking-wider">Compressor Stats</span>
          </div>
          <!-- 擋板控制區 -->
          <div class="space-y-3 pt-3">
            <span class="text-xs font-black text-slate-400 uppercase tracking-widest block">擋板控制 (DAMPER CONTROL)</span>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

              <!-- 新鮮空氣擋板開度 -->
              <div class="p-3.5 bg-slate-50/50 rounded-xl border border-slate-100 space-y-2">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-black text-slate-500 uppercase tracking-wide">新鮮空氣擋板開度</span>
                  <span class="ml-auto text-[10px] font-bold text-slate-400">D40212</span>
                </div>
                <BaseRangeSlider
                  v-model="freshAirDamperPos"
                  @change="setFreshAirDamper"
                  :min="0"
                  :max="2"
                  :step="1"
                  :disabled="!isDeviceConnected"
                  minLabel="關閉"
                  midLabel="50%"
                  maxLabel="100%"
                />
              </div>

              <!-- 緊急供氣擋板 -->
              <div class="p-3.5 bg-slate-50/50 rounded-xl border border-slate-100 flex flex-col justify-between gap-3 h-full">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-black text-slate-500 uppercase tracking-wide">開啟緊急供氣擋板</span>
                  <span class="ml-auto text-[10px] font-bold text-slate-400">D40213</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm font-black" :class="emergAirDamper ? 'text-rose-600' : 'text-slate-400'">
                    {{ emergAirDamper ? '開啟' : '關閉' }}
                  </span>
                  <BaseSwitch
                    :modelValue="Boolean(emergAirDamper)"
                    @update:modelValue="setEmergAirDamper($event ? 1 : 0)"
                    :disabled="!isDeviceConnected"
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
            </div>
          </div>


        </div>
      </div>

      <!-- SvgViewer 畫布 (圖面配置) -->
      <div v-else-if="activeTab === 'map'" class="bg-white border border-slate-200 shadow-sm rounded-2xl p-4 mb-4">
        <div class="flex items-center justify-between mb-4">
          <div class="font-extrabold text-slate-800 text-lg tracking-wide flex items-center gap-2">
            <div class="w-1 h-4 bg-[#2a7eb5] rounded-full"></div>
            車廂感測配置圖面
          </div>
          <span class="text-xs font-semibold text-slate-400">
            唯讀模式
          </span>
        </div>
        <div class="h-[500px] border border-slate-200/60 rounded-2xl overflow-hidden relative bg-white">
          <SvgViewer
            :src="planUrl"
            :markers="mappedSensors"
            :editable="false"
            :zoomable="true"
            :initialScale="0.7"
            :minScale="0.5"
            :maxScale="1.2"
          />
        </div>
      </div>

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
      :car-no="carVin"
      :end-pos="endPosId"
    />

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
