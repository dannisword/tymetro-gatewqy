import { CompressorStatus, SYSTEM_MODE_MAP, SystemModeKey } from './enums';
import { EndpointStatus } from './types';

/**
 * 轉換壓縮機運行指標與狀態
 */
export const updateCompressorStatus = (
  targetEp: {
    compressors: Array<{
      id: number;
      status: any;
      health: any;
      highPress: number;
      lowPress: number;
    }>;
  },
  reg: Record<string, any>
) => {
  const D40002 = (reg.D40002 !== undefined && reg.D40002 !== null) ? Number(reg.D40002) : undefined;
  const D40003 = (reg.D40003 !== undefined && reg.D40003 !== null) ? Number(reg.D40003) : undefined;

  const isD40002Valid = D40002 !== undefined && !isNaN(D40002);
  const isD40003Valid = D40003 !== undefined && !isNaN(D40003);

  // 轉換健康/異常狀態 (DI 7 & DI 8)
  // 條件：1 是正常，0 是斷路/異常
  if (isD40002Valid) {
    if (targetEp.compressors[0]) {
      targetEp.compressors[0].health = ((D40002 >> 4) & 1) === 1 ? '正常' : '異常';
    }
    if (targetEp.compressors[1]) {
      targetEp.compressors[1].health = ((D40002 >> 5) & 1) === 1 ? '正常' : '異常';
    }
  }

  // 轉換運行狀態 (ON / OFF)
  // 條件：DO 需要啟動 (1) 且 DI 需要正常 (1)
  if (isD40002Valid && isD40003Valid) {
    if (targetEp.compressors[0]) {
      const isDoOn = ((D40003 >> 5) & 1) === 1;
      const isDiNormal = ((D40002 >> 4) & 1) === 1;
      targetEp.compressors[0].status = (isDoOn && isDiNormal) ? CompressorStatus.ON : CompressorStatus.OFF;
    }
    if (targetEp.compressors[1]) {
      const isDoOn = ((D40003 >> 6) & 1) === 1;
      const isDiNormal = ((D40002 >> 5) & 1) === 1;
      targetEp.compressors[1].status = (isDoOn && isDiNormal) ? CompressorStatus.ON : CompressorStatus.OFF;
    }
  } else if (isD40003Valid) {
    // 預防萬一：如果只有 D40003 有值，先以 DO 當作 ON/OFF 判斷
    if (targetEp.compressors[0]) {
      targetEp.compressors[0].status = ((D40003 >> 5) & 1) === 1 ? CompressorStatus.ON : CompressorStatus.OFF;
    }
    if (targetEp.compressors[1]) {
      targetEp.compressors[1].status = ((D40003 >> 6) & 1) === 1 ? CompressorStatus.ON : CompressorStatus.OFF;
    }
  }
  // 轉換壓縮機 1 高低壓
  const highP1 = (reg.D40006 !== undefined && reg.D40006 !== null) ? Number(reg.D40006) : undefined;
  const lowP1 = (reg.D40005 !== undefined && reg.D40005 !== null) ? Number(reg.D40005) : undefined;
  if (targetEp.compressors[0]) {
    if (highP1 !== undefined && !isNaN(highP1)) targetEp.compressors[0].highPress = Math.round(highP1);
    if (lowP1 !== undefined && !isNaN(lowP1)) targetEp.compressors[0].lowPress = Math.round(lowP1);
  }

  // 轉換壓縮機 2 高低壓
  const highP2 = (reg.D40008 !== undefined && reg.D40008 !== null) ? Number(reg.D40008) : undefined;
  const lowP2 = (reg.D40007 !== undefined && reg.D40007 !== null) ? Number(reg.D40007) : undefined;
  if (targetEp.compressors[1]) {
    if (highP2 !== undefined && !isNaN(highP2)) targetEp.compressors[1].highPress = Math.round(highP2);
    if (lowP2 !== undefined && !isNaN(lowP2)) targetEp.compressors[1].lowPress = Math.round(lowP2);
  }
};

/**
 * 統一更新端點數值邏輯
 */
export const updateEndpointData = (targetEp: EndpointStatus, reg: Record<string, any>) => {
  // 轉換模式
  if (reg.D40001 !== undefined) {
    const modeKey = reg.D40001.toString() as SystemModeKey;
    targetEp.mode = SYSTEM_MODE_MAP[modeKey] || '未知';
  }
  // 轉換回風溫度 (可能為字串，需轉型為 Number)
  if (reg.D40004 !== undefined) {
    targetEp.returnTemp = parseFloat((Number(reg.D40004) / 10).toFixed(1));
  }
  // 轉換設定溫度 (可能為字串，需轉型為 Number)
  if (reg.D40201 !== undefined) {
    targetEp.setTemp = parseFloat((Number(reg.D40201) / 10).toFixed(1));
  }
  // 轉換壓縮機運行指標與狀態
  updateCompressorStatus(targetEp, reg);
};

