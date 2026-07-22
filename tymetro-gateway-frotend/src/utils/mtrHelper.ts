/**
 * 車組與車廂雙向解析工具
 */

/**
 * 從 4 位數車號，反推車組編號（如 1302 反推 T102 且為 3 車）
 */
export function parseCarNo(carNo: number) {
  const type = Math.floor(carNo / 1000);        // 取得千位數 (1 代表普通車，2 代表直達車)
  const carIndex = Math.floor((carNo % 1000) / 100); // 取得百位數 (1 ~ 4 車)
  const num = carNo % 100;                      // 取得末兩位 (1 ~ 20)

  // 格式化為兩位數列車號碼 (例如 2 ➜ "02")
  const formattedNum = num.toString().padStart(2, '0');

  return {
    trainCode: `T${type}${formattedNum}`, // 產出 T102 或 T211
    carIndex,                             // 1 ~ 4 車
    typeName: type === 1 ? '普通車' : '直達車',
    trainNo: num
  };
}

/**
 * 從當前的列車（如 T102）以及選單車廂（如 3），動態算出車號
 */
export function getCarNo(trainCode: string, carIndex: number): number {
  // 解析 T102 ➜ type = 1, num = 2
  const match = trainCode.match(/^T([12])(\d{2})$/);
  if (!match) return 1101; // 預設安全值

  const type = parseInt(match[1]);
  const num = parseInt(match[2]);

  return type * 1000 + carIndex * 100 + num;
}

export function getBitLabel(sensorCode: string, bitIndex: number): string {
  return `B${bitIndex}`;
}
