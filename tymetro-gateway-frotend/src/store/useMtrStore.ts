import { defineStore } from "pinia";

export interface EquipmentConfig {
  id: number;
  name: string;
  address: string;
}

export interface CarConfig {
  id: number;
  name: string;
  ip: string;
  equipment: EquipmentConfig[];
}

export interface DropdownItem {
  label?: string;
  icon?: string;
  to?: string;
  action?: string;
  divider?: boolean;
}

export interface ToolItem {
  id: number;
  title: string;
  icon: string;
  step?: string;
  route: string;
}

export interface ScheduleTypeItem {
  value: string;
  label: string;
}

export const useMtrStore = defineStore("useMtrStore", {
  state: () => {
    return {
      // 網路版：VITE_LAYOUT_MODE=multi-column-layout 預設Ip true
      // 單機版：VITE_LAYOUT_MODE=1-column-layout 預設Ip false
      useDefaultIP: import.meta.env.VITE_LAYOUT_MODE === 'multi-column-layout',
      localIp: '127.0.0.1',
      activeCarId: 1,
      carConfigs: [] as CarConfig[],
      userDropdown: [] as DropdownItem[],
      tools: [] as ToolItem[],
      scheduleTypes: [] as ScheduleTypeItem[],
      registerGroups: [] as { value: string; label: string }[],
    };
  },
  getters: {
    currentCar: (state: any) => {
      return state.carConfigs.find((c: any) => c.id === state.activeCarId) || state.carConfigs[0];
    },
    currentCarIp: (state): string => {
      if (state.useDefaultIP) {
        return '127.0.0.1'; // 預設 Gateway / 伺服器 IP
      }
      const car = state.carConfigs.find((c) => c.id === state.activeCarId);
      return car ? car.ip : '127.0.0.1';
    },
  },
  actions: {
    setUseDefaultIP(val: boolean) {
      this.useDefaultIP = val;
    },
    setActiveCarId(id: number) {
      this.activeCarId = id;
    },
    setCarIp(id: number, ip: string) {
      const car = this.carConfigs.find((c) => c.id === id);
      if (car) {
        car.ip = ip;
      }
    },
    async loadConfig() {
      try {
        const res = await fetch(`/config.json?t=${Date.now()}`);
        if (res.ok) {
          const config = await res.json();
          if (config && Array.isArray(config.carVins)) {
            this.carConfigs = config.carVins;
          }
          if (config && Array.isArray(config.userDropdown)) {
            this.userDropdown = config.userDropdown;
          }
          if (config && Array.isArray(config.tools)) {
            this.tools = config.tools;
          }
          if (config && Array.isArray(config.scheduleTypes)) {
            this.scheduleTypes = config.scheduleTypes;
          }
          if (config && Array.isArray(config.registerGroups)) {
            this.registerGroups = config.registerGroups;
          }
        }
      } catch (err) {
        console.error("Failed to load /config.json in MtrStore:", err);
      }
    },
    async fetchSystemIp() {
      try {
        const { getHealthStatus } = await import("@/utils/api");
        const res = await getHealthStatus();
        if (res && res.data && res.data.local_ip) {
          this.localIp = res.data.local_ip;
        }
      } catch (err) {
        console.error("Failed to fetch system IP in store:", err);
      }
    }
  },
  persist: {
    key: "useMtrStore",
    storage: localStorage,
  },
});
