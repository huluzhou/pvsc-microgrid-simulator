// 内核工厂（计算内核和AI内核）
// Rust 端主要负责内核选择和配置管理
// 具体的内核实现在 Python 中

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum KernelType {
    Pandapower,
    PyPSA,
    GridCal,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AIKernelType {
    PyTorch,
    TensorFlow,
    OpenAIGym,
}

pub struct KernelFactory;

impl KernelFactory {
    pub fn create_power_kernel(kernel_type: KernelType) -> Result<String, String> {
        match kernel_type {
            KernelType::Pandapower => Ok("pandapower".to_string()),
            KernelType::PyPSA => Ok("pypsa".to_string()),
            KernelType::GridCal => Ok("gridcal".to_string()),
        }
    }

    pub fn create_ai_kernel(kernel_type: AIKernelType) -> Result<String, String> {
        match kernel_type {
            AIKernelType::PyTorch => Ok("pytorch".to_string()),
            AIKernelType::TensorFlow => Ok("tensorflow".to_string()),
            AIKernelType::OpenAIGym => Ok("gym".to_string()),
        }
    }
}
