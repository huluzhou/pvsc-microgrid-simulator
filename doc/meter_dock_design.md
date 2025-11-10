# 电表设备DockWidget功能设计文档

## 1. 功能概述

为PandaPower仿真工具开发电表设备DockWidget功能模块，用于实时显示电表测量数据，包括当前测量参数类型、对应测量数值及单位、设备通信连接状态等核心信息，提供直观的电网测量数据监控界面。电表的测量类型由network_items中电表设备的设置决定。

## 2. 详细需求说明

### 2.1 核心功能需求

- **实时数据展示**：显示电表设备的测量参数，测量类型由电表设备自身的`meas_type`属性决定

- **通信状态监控**：显示电表设备的通信连接状态（已连接/未连接）

- **数据一致性**：确保显示的测量数据与电表设备在network_items中配置的测量类型一致

### 2.2 非功能需求

- **界面美观**：遵循现有应用的UI风格，保持一致性
- **响应及时**：数据更新不影响主UI的响应性
- **易于使用**：操作流程简单直观，符合用户习惯

## 3. 界面原型描述

### 3.1 整体布局

电表设备DockWidget将采用与现有设备面板一致的布局结构：

- **标题区域**：显示面板标题"电表设备数据"
- **当前设备区域**：显示当前选中的电表设备信息及通信状态
- **测量结果展示区域**：显示基于电表设备`meas_type`属性的测量参数及其数值

### 3.2 详细组件布局

```
+------------------------电表设备数据------------------------+
|
| +--------------------当前设备--------------------------+  |
| | 设备名称: 未选择电表设备                              |  |
| | 通信状态: 未连接                                      |  |
| | 开启通信 | 关闭通信                                   |  |
| +-----------------------------------------------------+  |
|
| +------------------电表测量结果------------------------+  |
| | 当前测量类型: 有功功率（基于设备配置）               |  |
| | 测量值:      -- kW                                  |  |
| | 设备配置信息:                                        |  |
| |  - 测量元件类型: bus                                 |  |
| |  - 测量元件索引: 0                                   |  |
| |  - 测量位置: 高压侧                                  |  |
| +-----------------------------------------------------+  |
|
+--------------------------------------------------------+
```

## 4. 数据接口定义

### 4.1 数据模型接口

直接使用项目中已定义的电表数据模型（位于`network_items.py`中的`MeterItem`类）：

```python
# 引用路径: /d:/pp_tool/src/components/network_items.py
class MeterItem(BaseNetworkItem):
    """电表组件"""
    
    # 关键属性（包含在properties字典中）：
    # - "meas_type": 测量类型，默认为"p"（有功功率）
    # - "element_type": 测量元件类型
    # - "element": 元件索引
    # - "value": 测量值
    # - "name": 设备名称
    # - "sn": 序列号
    # - "ip": IP地址
    # - "port": 端口号
    # - "in_service": 运行状态
```

### 4.2 UI组件接口

UI组件管理器需实现以下方法：

```python
class UIComponentManager:
    def create_meter_data_panel(self, parent):
        """创建电表设备数据面板"""
        # 实现代码
```

### 4.3 数据控制接口

数据控制管理器将复用`power_monitor.py`中已有的方法：

```python
# 引用路径: /d:/pp_tool/src/components/power_monitor.py
class PowerMonitor:
    def get_meter_measurement(self, meter_id, measurement_type='active_power'):
        """
        获取指定电表的不同类型测量值
        
        参数:
            meter_id (int): 电表设备的唯一标识符
            measurement_type (str): 测量类型，支持以下值：
                - 'active_power': 有功功率（单位：MW）
                - 'reactive_power': 无功功率（单位：MVar）
                - 'voltage': 电压（单位：kV）
                - 'current': 电流（单位：kA）
                默认为'active_power'
                
        返回:
            float: 测量值，如果获取失败则返回0.0
        """
        # 实现代码
```

数据控制管理器需额外实现以下方法：

```python
class DataControlManager:
    def get_meter_measurement_by_type(self, meter_id):
        """
        基于电表设备自身的meas_type属性获取测量值，内部调用PowerMonitor的get_meter_measurement方法
        
        参数:
            meter_id (int): 电表设备的唯一标识符
            
        返回:
            float: 测量值，如果获取失败则返回0.0
        """
        # 实现代码
        
    def update_meter_control_panel_info(self, component_type, component_idx):
        """
        更新电表控制面板信息
        
        参数:
            component_type (str): 组件类型
            component_idx (int): 组件索引
        
        功能:
            1. 更新电表设备名称显示
            2. 基于电表设备的meas_type属性更新测量类型和测量值显示
            3. 更新测量元件类型和索引信息
            4. 基于element_type和side属性更新测量位置信息:
               - 对于变压器(trafo): 显示"高压侧"/"低压侧"/"中压侧"
               - 对于线路(line): 显示"起始端(from)"/"末端(to)"
               - 对于其他类型: 直接显示side值
            5. 包含完整的异常处理机制
        """
        # 实现代码
    
    def on_device_power_on(self, device_type, component_idx):
        """
        开启设备通信功能，支持电表设备
        
        此方法用于开启设备的通信功能，启动Modbus服务器连接设备，更新设备通信状态，并通过UI进行反馈。
        该方法已扩展支持电表设备。
        
        参数:
            device_type (str): 设备类型，包括"meter"（电表）、"sgen"（静态发电机）、"storage"（储能）、"load"（负载）、"charger"（充电桩）
            component_idx (int): 组件索引，用于定位特定设备实例
            
        返回:
            bool: 通信开启成功返回True，失败返回False
        
        实现细节:
            1. 检查设备类型映射表，确定实际的设备类型键名
            2. 获取设备实例并验证IP地址设置是否有效
            3. 尝试启动Modbus服务器进行通信连接
            4. 根据连接结果更新设备的comm_status属性
            5. 调用_update_comm_status_indicator方法更新UI显示
            6. 返回通信开启结果
        
        注意事项:
            - 方法已扩展支持电表设备，在component_type_map和device_type_name中添加了meter相关映射
            - 电表设备的通信状态通过comm_status属性管理
            - 通信失败时会记录详细错误信息并提供用户反馈
        """
        # 实现代码，已扩展支持电表设备
        
    def on_device_power_off(self, device_type, component_idx):
        """
        关闭设备通信功能，支持电表设备
        
        此方法用于关闭设备的通信功能，停止Modbus服务器连接，更新设备通信状态，并通过UI进行反馈。
        该方法已扩展支持电表设备。
        
        参数:
            device_type (str): 设备类型，包括"meter"（电表）、"sgen"（静态发电机）、"storage"（储能）、"load"（负载）、"charger"（充电桩）
            component_idx (int): 组件索引，用于定位特定设备实例
            
        返回:
            bool: 通信关闭成功返回True，失败返回False
        
        实现细节:
            1. 检查设备类型映射表，确定实际的设备类型键名
            2. 获取设备实例并将其comm_status属性设置为False
            3. 停止Modbus服务器通信连接
            4. 调用_update_comm_status_indicator方法更新UI显示
            5. 返回通信关闭结果
        
        注意事项:
            - 方法已扩展支持电表设备，在component_type_map和device_type_name中添加了meter相关映射
            - 电表设备的通信状态通过comm_status属性管理
            - 关闭通信时会优雅地终止连接，避免资源泄漏
        """
        # 实现代码，已扩展支持电表设备
        
    def _update_comm_status_indicator(self, device_type, device_idx=None):
        """
        更新设备通信状态指示器，支持电表设备
        
        此方法用于更新UI界面上设备的通信状态指示器，根据设备的comm_status属性值，
        设置指示器的文本和样式，直观地向用户展示设备的连接状态。该方法已扩展支持电表设备。
        
        参数:
            device_type (str): 设备类型，包括"meter"（电表）、"sgen"（静态发电机）、"storage"（储能）、"load"（负载）、"charger"（充电桩）
            device_idx (int, optional): 设备索引，用于在设备列表中定位特定实例
        
        实现细节:
            1. 构建状态指示器标签名映射，包含电表设备的映射：{"meter": "meter_comm_status_label"}
            2. 确定实际的设备类型键名映射，包含电表设备的映射：{"meter": "meter"}
            3. 从设备的comm_status属性获取当前连接状态
            4. 根据连接状态更新指示器文本和样式：
               - 已连接: 绿色文本显示"通信状态: 已连接"
               - 未连接: 红色文本显示"通信状态: 未连接"
            5. 捕获并记录可能的异常，确保UI更新不会中断应用程序
        
        注意事项:
            - 方法已扩展支持电表设备，在indicator_map和type_map中添加了meter相关映射
            - 电表设备的状态指示器名称为"meter_comm_status_label"
            - 如果UI组件中找不到对应的状态指示器，方法会静默失败并记录日志
        """
        # 实现代码，已扩展支持电表设备

```

## 5. 开发计划

### 5.1 阶段一：基础框架开发（1天）

- 在 `simulation_window.py` 中创建电表DockWidget实例
- 在 `ui_components.py` 中实现 `create_meter_data_panel` 方法
- 确保UI组件正确布局和显示

### 5.2 阶段二：数据交互开发（1天）

- 在 `data_control.py` 中实现电表相关的数据控制方法
- 实现基于MeterItem属性的测量数据获取机制
- 确保通信状态正确显示和更新

### 5.3 阶段三：功能完善和测试（1天）

- 进行功能测试和bug修复
- 确保与现有系统的兼容性

## 6. 验收标准

### 6.1 功能验收

- 电表DockWidget能够正常显示和隐藏
- 能够正确显示当前选中的电表设备信息
- 能够根据电表设备的meas_type属性正确获取并显示测量数据
- 通信状态指示器能够正确反映设备连接状态
- 显示的测量类型与设备配置一致

### 6.2 性能验收

- UI响应流畅，无明显卡顿
- 内存占用在合理范围内

### 6.3 兼容性验收

- 与现有系统功能无冲突
- 能够与其他设备DockWidget同时正常工作
- 支持不同屏幕分辨率和窗口大小调整

## 7. 技术实现要点

1. **DockWidget创建**：遵循现有模式，在 `simulation_window.py` 中添加电表DockWidget
2. **UI布局**：使用PySide6的布局管理器（VBoxLayout, FormLayout等）实现界面布局
3. **数据绑定**：使用信号槽机制实现UI组件与数据模型的绑定
4. **线程安全**：确保数据更新在主线程中执行，避免UI阻塞
5. **状态管理**：正确管理设备通信状态
6. **数据一致性**：确保显示的测量类型和数值与MeterItem中的配置保持一致
7. **模型复用**：直接使用现有的MeterItem类作为数据模型，无需创建新的数据模型类