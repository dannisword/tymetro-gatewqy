import axios, { type AxiosRequestConfig } from "axios";
import { useLoadingStore } from "@/store/useLoadingStore";
import { useAppStore } from "@/store/useAppStore";
import { useMtrStore } from "@/store/useMtrStore";
import { useAuthStore } from "@/store/useAuthStore";
declare module "axios" {
  interface AxiosRequestConfig {
    meta?: {
      /** 預設 true；false 可關閉這筆請求的全域 loading */
      loading?: boolean;
      /** true 則不彈錯誤提示 */
      silent?: boolean;
    };
    loadingId?: number; // 內部使用：追蹤這筆請求的 id
  }
}

const service = axios.create({
  baseURL: import.meta.env.VITE_BASE_API,
  timeout: 5000,
  withCredentials: true,
});

let idSeq = 0;
const activeIds = new Set<number>();

function startIfNeeded(cfg?: AxiosRequestConfig) {
  if (cfg?.meta?.loading === false) {
    return;
  }
  const store = useLoadingStore();
  if (activeIds.size === 0) {
    store.start();
  }
}

function stopIfNeeded(cfg?: AxiosRequestConfig) {
  if (cfg?.meta?.loading === false) {
    return;
  }
  const store = useLoadingStore();
  if (activeIds.size === 0) {
    store.stop();
  }
}

/** 註冊請求 id，必要時觸發 start */
function registerLoading(cfg: AxiosRequestConfig) {
  if (cfg.meta?.loading === false) {
    return;
  }
  const id = ++idSeq;
  cfg.loadingId = id;
  startIfNeeded(cfg);
  activeIds.add(id);
}

/** 解除請求 id，必要時觸發 stop */
function unregisterLoading(cfg?: AxiosRequestConfig) {
  if (!cfg || cfg.meta?.loading === false) {
    return;
  }
  if (cfg.loadingId != null) {
    activeIds.delete(cfg.loadingId);
  }
  stopIfNeeded(cfg);
}

service.interceptors.request.use(
  (config) => {
    if (!config.headers["Content-Type"]) {
      config.headers["Content-Type"] = "application/json";
    }
    const token = useAuthStore().accessToken;

    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }

    // 🌟 動態替換 baseURL 為當前選擇車廂的 IP
    const mtrStore = useMtrStore();

    // if (mtrStore.useDefaultIP == false) {
    //   // 排除不需要動態轉向的 CMS 核心系統端點 (這些端點必須連線到中央 CMS 伺服器)
    //   const bypassUrls = [
    //     "/api/v1/users",
    //     "/api/v1/configs",
    //     "/api/v1/settings"
    //   ];
    //   const isBypass = bypassUrls.some((url) => config.url && config.url.startsWith(url));
    //   console.log(mtrStore.currentCarIp);

    //   if (isBypass && import.meta.env.MODE === "production") {
    //     // 在本地開發/轉發模式下，可根據需要加上 port E.g. 5400 或直接使用 http://${ip}:5400
    //     config.baseURL = `http://${mtrStore.currentCarIp}:5400`;
    //   }
    // }

    registerLoading(config);
    return config;
  },
  (error) => {
    unregisterLoading(error.config);
    return Promise.reject(error);
  },
);

// response interceptor
service.interceptors.response.use(
  (response) => {
    unregisterLoading(response.config);
    return Promise.resolve(response.data);
  },
  (error) => {
    unregisterLoading(error.config);
    if (error.response && error.response.status === 401) {
      const store = useAppStore();
      store.logout();
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export default service;
