import { useGlobalStore } from "@/store/useGlobalStore";
import dayjs from 'dayjs';
/**
 * 判斷是否空值
 * @param val
 * @returns
 */
export const isEmptyOrNull = (val: any) => {
  if (val == undefined) {
    return true;
  }
  // 集合
  if (val.constructor === Array) {
    return val.length <= 0;
  }
  // 物件
  if (typeof val == "object") {
    return Object.keys(val).length === 0;
  }
  // 數值
  if (typeof val == "number") {
    return false;
  }
  // 其他
  return val == undefined || val == null || val == "" ? true : false;
};

/**
 *
 * @param val
 * @returns
 */
export function validEmpty(val: any) {
  if (typeof val == "number") {
    return false;
  }
  return val == undefined || val == null || val == "" ? true : false;
}

/**
 * Adds a specific number of days to the current date and formats it.
 * @param amount - The number of days to add (number)
 * @param format - The desired output format (string)
 */
export function addDay(amount: number | string, format: string = "YYYY-MM-DD"): string {
  return dayjs().add(Number(amount), "day").format(format);
}

/**
 * 將日期格式化 (原 format 改名為 formatDateTime)
 * @param inp - 傳入的日期來源 (支援 Date 物件, 字串, 或毫秒)
 * @param format - 輸出的格式，預設為 "YYYY-MM-DD"
 * @returns 格式化後的字串，若輸入為空則回傳空字串
 */
export function formatDateTime(inp: any, format: string = "YYYY-MM-DD"): string {
  if (inp) {
    return dayjs(inp).format(format);
  }
  return "";
}
/**
 * 處理時間函式
 * @param search 
 */
export function handleSearchData(search: any) {
  // 處理時間
  const dateRange = search.schemas.filter((x: any) => x.type == "date");
  for (const d of dateRange) {
    if (d && d.value != null) {
      search.params[d.start.prop] = formatDateTime(d.value[0]);
      search.params[d.end.prop] = formatDateTime(d.value[1]);
    } else {
      search.params[d.start.prop] = "";
      search.params[d.end.prop] = "";
    }
  }
}
/**
 * 將陣列轉換物件
 * @param {*} object
 * @param {*} pairs
 */
export function arrayToObject(object: any, pairs: any) {
  for (let [key, value] of Object.entries(pairs)) {
    let name: string;
    Object.entries(value as any).forEach(([k, v]) => {
      if (k == "prop") {
        name = v as string;
      }

      if (k == "value") {
        object[name] = v;
      }
    });
  }
}
/**
 * 將物件轉換陣列
 * @param object
 * @param pairs
 */
export function objectToArray(object: any, pairs: any[]) {
  for (let [key, value] of Object.entries(object)) {
    let pair = pairs.find((x: any) => x.prop == key);

    if (pair) {
      pair.value = value;
    }
  }
}

export function getCacheOptions(code: any) {
  const store = useGlobalStore(); // 放在函數裡面，呼叫時才執行
  const data = store.getOptions;
  const value = data.find((x: any) => x.code == code);
  if (value) {
    return value.options;
  }
  return null;
}
/**
 * 查詢條件轉換成 Url 參數
 * @param {*} params
 * @param {*} num
 * @returns
 */
export function URLSearchParams(params: any, num: boolean = true) {
  let query = "";

  for (let [key, value] of Object.entries(params)) {
    // 忽略特定欄位
    if (
      key === "dateRange" ||
      key === "prodGoodDateRange" ||
      key === "prodMadeDateRange"
    ) {
      continue;
    }

    // 忽略 undefined/null
    if (value === undefined || value === null) {
      continue;
    }

    // 忽略空字串
    if (typeof value === "string" && value === "") {
      continue;
    }

    // 忽略數值為 0（根據 num 判斷）
    // if (typeof value === "number" && value === 0 && num === true) {
    //   continue;
    // }

    // 處理陣列
    if (Array.isArray(value)) {
      for (let item of value) {
        query += query === "" ? `${key}=${item}` : `&${key}=${item}`;
      }
    } else {
      query += query === "" ? `${key}=${value}` : `&${key}=${value}`;
    }
  }

  return query;
}

export function handleParams(params: any) {
  const p = { ...params };
  Object.keys(p).forEach(key => {
    // 處理 Boolean
    if (typeof p[key] === 'boolean') {
      p[key] = p[key] ? 'true' : 'false'; // 或轉成 1 / 0
    }
    // 處理 Array (例如轉成逗號分隔字串)
    if (Array.isArray(p[key])) {
      p[key] = p[key].join(','); 
    }
  });
  return p;
};