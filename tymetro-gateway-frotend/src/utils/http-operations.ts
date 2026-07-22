import request from "./request";
import { isEmptyOrNull } from "./common";
import { useAlert } from "../composables/TLAlter";
import type { AxiosRequestConfig } from "axios";

const { TLWarning } = useAlert();

interface ErrorResponse {
  success: boolean;
  message: string;
}

const handleError = (e: any): ErrorResponse | void => {
  let msg = "未知錯誤";

  if (e.code === "ECONNABORTED" && e.message?.includes("timeout")) {
    msg = "請求超時，請檢查網路或稍後再試";
  } else if (e.status) {
    const statusMap: Record<number | string, string> = {
      400: e.response?.data?.message || "請求錯誤 (400)",
      401: "未經授權 (401)",
      405: "請求方法不允許 (405)",
      500: "系統內部錯誤 (500)",
    };
    msg = statusMap[e.status] || msg;
  } else if (e.message) {
    msg = e.message;
  }

  TLWarning(msg);
  return {
    success: false,
    message: msg,
  };
};

const httpOperations = {
  async get<T = any>(url: string, params: any = undefined, config?: AxiosRequestConfig): Promise<T> {
    const finalUrl = encodeURI(url);
    let finalParams = params;

    if (!isEmptyOrNull(params)) {
      finalParams = Object.fromEntries(
        Object.entries(params).map(([key, value]) => [
          key,
          typeof value === "string" ? encodeURIComponent(value) : value,
        ])
      );
    }

    try {
      const response = await request({
        url: finalUrl,
        method: "GET",
        params: finalParams,
        ...config,
      });
      return response as T;
    } catch (e: any) {
      handleError(e);
      throw e;
    }
  },

  async post<T = any>(url: string, data: any = undefined): Promise<T> {
    try {
      const response = await request({
        url,
        method: "POST",
        data,
      });
      return response as T;
    } catch (e: any) {
      handleError(e);
      throw e;
    }
  },

  async put<T = any>(url: string, data: any = undefined): Promise<T> {
    try {
      const response = await request({
        url,
        method: "PUT",
        data,
      });
      return response as T;
    } catch (e: any) {
      handleError(e);
      throw e;
    }
  },

  async delete<T = any>(url: string, data: any = undefined): Promise<T> {
    try {
      const response = await request({
        url,
        method: "DELETE",
        data,
      });
      return response as T;
    } catch (e: any) {
      handleError(e);
      throw e;
    }
  },
};

export default httpOperations;
