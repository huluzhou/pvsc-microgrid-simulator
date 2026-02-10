/**
 * 设备控制状态管理
 */
import { create } from 'zustand';
import { 
  DeviceControlConfig, 
  DataSourceType, 
  ManualSetpoint,
  RandomConfig,
  HistoricalConfig,
  DeviceSimParams,
} from '../types/dataSource';

interface DeviceControlState {
  // 设备控制配置
  deviceConfigs: Record<string, DeviceControlConfig>;
  
  // 设备级仿真参数
  deviceSimParams: Record<string, DeviceSimParams>;
  
  // 选中的设备
  selectedDeviceIds: string[];
  
  // 操作方法
  setDeviceConfig: (deviceId: string, config: Partial<DeviceControlConfig>) => void;
  setDataSourceType: (deviceId: string, type: DataSourceType) => void;
  setManualSetpoint: (deviceId: string, setpoint: ManualSetpoint) => void;
  setRandomConfig: (deviceId: string, config: RandomConfig) => void;
  setHistoricalConfig: (deviceId: string, config: HistoricalConfig) => void;
  setDeviceSimParams: (deviceId: string, params: DeviceSimParams) => void;
  
  // 批量操作
  setSelectedDevices: (ids: string[]) => void;
  batchSetDataSource: (type: DataSourceType) => void;
  batchSetManualSetpoint: (setpoint: ManualSetpoint) => void;
  
  // 清理
  removeDeviceConfig: (deviceId: string) => void;
  clearAllConfigs: () => void;
}

// 默认随机配置
const defaultRandomConfig: RandomConfig = {
  minPower: 0,
  maxPower: 100,
  updateInterval: 1,
  volatility: 0.1,
};

// 默认手动设定值
const defaultManualSetpoint: ManualSetpoint = {
  activePower: 0,
  reactivePower: 0,
};

export const useDeviceControlStore = create<DeviceControlState>((set, get) => ({
  deviceConfigs: {},
  deviceSimParams: {},
  selectedDeviceIds: [],

  setDeviceConfig: (deviceId, config) => {
    set((state) => ({
      deviceConfigs: {
        ...state.deviceConfigs,
        [deviceId]: {
          ...state.deviceConfigs[deviceId],
          deviceId,
          ...config,
        },
      },
    }));
  },

  setDataSourceType: (deviceId, type) => {
    set((state) => {
      const existing = state.deviceConfigs[deviceId] || { deviceId };
      return {
        deviceConfigs: {
          ...state.deviceConfigs,
          [deviceId]: {
            ...existing,
            dataSourceType: type,
            // 设置默认配置
            ...(type === 'random' && !existing.randomConfig && { randomConfig: defaultRandomConfig }),
            ...(type === 'manual' && !existing.manualSetpoint && { manualSetpoint: defaultManualSetpoint }),
          },
        },
      };
    });
  },

  setManualSetpoint: (deviceId, setpoint) => {
    set((state) => ({
      deviceConfigs: {
        ...state.deviceConfigs,
        [deviceId]: {
          ...state.deviceConfigs[deviceId],
          deviceId,
          dataSourceType: 'manual',
          manualSetpoint: setpoint,
        },
      },
    }));
  },

  setRandomConfig: (deviceId, config) => {
    set((state) => ({
      deviceConfigs: {
        ...state.deviceConfigs,
        [deviceId]: {
          ...state.deviceConfigs[deviceId],
          deviceId,
          dataSourceType: 'random',
          randomConfig: config,
        },
      },
    }));
  },

  setHistoricalConfig: (deviceId, config) => {
    set((state) => ({
      deviceConfigs: {
        ...state.deviceConfigs,
        [deviceId]: {
          ...state.deviceConfigs[deviceId],
          deviceId,
          dataSourceType: 'historical',
          historicalConfig: config,
        },
      },
    }));
  },

  setDeviceSimParams: (deviceId, params) => {
    set((state) => ({
      deviceSimParams: {
        ...state.deviceSimParams,
        [deviceId]: params,
      },
    }));
  },

  setSelectedDevices: (ids) => {
    set({ selectedDeviceIds: ids });
  },

  batchSetDataSource: (type) => {
    const { selectedDeviceIds, setDataSourceType } = get();
    selectedDeviceIds.forEach((id) => setDataSourceType(id, type));
  },

  batchSetManualSetpoint: (setpoint) => {
    const { selectedDeviceIds, setManualSetpoint } = get();
    selectedDeviceIds.forEach((id) => setManualSetpoint(id, setpoint));
  },

  removeDeviceConfig: (deviceId) => {
    set((state) => {
      const { [deviceId]: _, ...rest } = state.deviceConfigs;
      return { deviceConfigs: rest };
    });
  },

  clearAllConfigs: () => {
    set({ deviceConfigs: {}, deviceSimParams: {}, selectedDeviceIds: [] });
  },
}));
