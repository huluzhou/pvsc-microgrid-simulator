// 设备元数据仓库
use crate::domain::topology::{Device, Topology};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

pub struct DeviceMetadataStore {
    devices: Arc<RwLock<HashMap<String, Device>>>,
    topology: Arc<RwLock<Option<Topology>>>,
}

impl DeviceMetadataStore {
    pub fn new() -> Self {
        Self {
            devices: Arc::new(RwLock::new(HashMap::new())),
            topology: Arc::new(RwLock::new(None)),
        }
    }

    pub fn set_topology(&self, topology: Topology) {
        // 从拓扑中提取设备元数据
        let devices: HashMap<String, Device> = topology.devices.clone();
        *self.devices.write().unwrap() = devices;
        *self.topology.write().unwrap() = Some(topology);
    }

    pub fn get_device(&self, device_id: &str) -> Option<Device> {
        self.devices.read().unwrap().get(device_id).cloned()
    }

    pub fn get_all_devices(&self) -> Vec<Device> {
        self.devices.read().unwrap().values().cloned().collect()
    }

    pub fn get_topology(&self) -> Option<Topology> {
        self.topology.read().unwrap().clone()
    }

    pub fn update_device(&self, device: Device) -> Result<(), String> {
        if !self.devices.read().unwrap().contains_key(&device.id) {
            return Err(format!("Device {} not found", device.id));
        }
        let device_clone = device.clone();
        self.devices.write().unwrap().insert(device.id.clone(), device_clone.clone());
        // 同步更新 topology 中的设备，保证 get_topology() 与 get_all_devices() 一致
        let mut topo_guard = self.topology.write().unwrap();
        if let Some(topo) = topo_guard.as_mut() {
            topo.devices.insert(device.id.clone(), device_clone);
        }
        Ok(())
    }
}

impl Default for DeviceMetadataStore {
    fn default() -> Self {
        Self::new()
    }
}
