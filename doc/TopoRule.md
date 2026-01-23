# 拓扑结构文件说明

## 拓扑连接规则（基于 pandapower 数据模型）

### 术语

- **连接点**：设备用于形成连接的端口。母线与功率设备各 1 个连接点；线路、变压器、开关各 2 个连接点。
- **节点设备**：母线。
- **连接设备**：线路、变压器、开关。
- **功率设备**：负荷、储能、静态发电、充电等。
- **电表**：可附着在母线或设备端口的测量设备。

### 全局约束

- 已存在的连接不允许重复创建。
- 母线的连接点允许承载多个不同连接。
- 目前外部电网设备全局仅允许 1 个。
- 不允许母线与母线直接连接。
- 不允许同一设备的两个连接点同时连接到对端同一个连接点（端口）。

---

## 设备连接规则

### 母线（节点设备）

- 拥有且仅有 1 个连接点。
- 允许被线路、变压器、开关、功率设备以及电表连接。

### 功率设备

- 每个功率设备拥有且仅有 1 个连接点。
- 仅允许与 1 个母线连接；若未连接则允许创建，已连接则不允许重复。
- 可选连接 1 个电表；每设备最多 1 个。
- 外部电网属于功率设备范畴，但设备总数最多 1 个。

### 线路（连接设备）

- 拥有 2 个连接点：起点与终点。
- 每个连接点仅可与 1 个母线或 1 个开关连接；同时最多允许附着 1 个电表。
- **与母线连接**：未连接时允许创建；创建后更新 `from_bus`/`to_bus`（分别对应起点/终点）。
- **与开关连接**：该端未连接且另一端未连接开关时允许；创建后更新开关的连接元件类型为线路，并记录线路索引；禁止线路两端同时连接开关。
- **与电表连接**：每个连接点至多 1 个电表。

### 变压器（连接设备）

- 拥有 2 个连接点：高压侧与低压侧。
- 每个连接点仅可与 1 个母线或 1 个开关连接；同时最多允许附着 1 个电表。
- **与母线连接**：未连接时允许创建；创建后更新 `hv_bus`/`lv_bus`（分别对应高压侧/低压侧）。
- **与开关连接**：该端未连接且另一端未连接开关时允许；创建后更新开关的连接元件类型为变压器，并记录变压器索引；禁止变压器两端同时连接开关。
- **与电表连接**：每个连接点至多 1 个电表。

### 开关（连接设备）

- 拥有 2 个连接点；每端允许连接的对象类型为母线、线路、变压器或电表。
- **稳态约束**：至少一端必须连接母线。搭建过程中可先连线路/变压器，但形成闭合连接后必须满足母线端约束。

#### 两端均未连接时

- 与母线连接：记录开关该端的母线索引。
- 与线路/变压器连接：记录开关的连接元件类型与索引。
- 与电表连接：该端未连接电表时允许。

#### 一端已连接母线时

- 与母线连接：允许，记录另一端母线索引。
- 与线路起点连接：更新线路 `from_bus` 为开关另一端的母线索引；并记录开关元件类型为线路及线路索引。
- 与线路终点连接：更新线路 `to_bus` 为开关另一端的母线索引；并记录开关元件类型为线路及线路索引。
- 与变压器高压侧连接：更新变压器 `hv_bus` 为开关另一端的母线索引；并记录开关元件类型为变压器及变压器索引。
- 与变压器低压侧连接：更新变压器 `lv_bus` 为开关另一端的母线索引；并记录开关元件类型为变压器及变压器索引。

#### 一端已连接线路起点/终点时

- 另一端仅允许连接母线或 1 个电表；与母线形成闭合后，更新线路相应的 `from_bus`/`to_bus` 为开关另一端的母线索引。

#### 一端已连接变压器高压侧/低压侧时

- 另一端仅允许连接母线或 1 个电表；与母线形成闭合后，更新变压器相应的 `hv_bus`/`lv_bus` 为开关另一端的母线索引。

### 电表

- 可连接至母线、线路端口、变压器端口、开关端口或功率设备连接点。
- 每个目标端口仅允许 1 个电表连接。
- 每个电表自身仅允许 1 条连接。

---

## 规则速查（设备 × 允许连接对象）

| 设备类型 | 允许连接对象 | 约束 |
|---------|-------------|------|
| 母线 | 线路、变压器、开关、功率设备、电表 | - |
| 功率设备 | 母线（1个）、电表（可选1个） | 不与开关/线路/变压器直接连接 |
| 线路端口 | 母线或开关（二选一）、电表（至多1个） | 禁止两端同时接开关 |
| 变压器端口 | 母线或开关（二选一）、电表（至多1个） | 禁止两端同时接开关 |
| 开关端口 | 母线、线路、变压器、电表 | 稳态至少一端接母线 |
| 电表 | 母线、线路端口、变压器端口、开关端口、功率设备连接点 | 每目标端口至多1个；每功率设备至多1个 |

---

## 连接动作的联动更新

| 连接类型 | 联动操作 |
|---------|---------|
| 线路 ↔ 母线 | 根据连接端更新 `from_bus` 或 `to_bus` |
| 开关 ↔ 线路 | 记录开关连接元件类型为线路，并记录线路索引 |
| 变压器 ↔ 母线 | 根据连接端更新 `hv_bus` 或 `lv_bus` |
| 开关 ↔ 变压器 | 记录开关连接元件类型为变压器，并记录变压器索引 |
| 开关两端形成"母线—线路/变压器"闭合 | 同步更新对应设备的 `from_bus`/`to_bus` 或 `hv_bus`/`lv_bus` 为另一端母线索引 |

---

## 能否连接的决策流程

1. **检查是否已存在同一连接**：已存在则拒绝
2. **判断设备类型组合是否允许**：按"规则速查"确定
3. **判断端口占用是否满足**：需满足"单端只允许 1 连接"的约束
4. **针对开关的稳态约束**：最终至少一端为母线
5. **针对电表的数量约束**：每目标端口 ≤ 1；每功率设备 ≤ 1
6. **外部电网唯一性**：新建或变更时确保系统中仅 1 个外部电网设备

---

## 典型搭建示例

### 线路经开关闭合到两母线

- **端 A**：开关 ↔ 母线
- **端 B**：开关 ↔ 线路起点；随后开关另一端 ↔ 母线
- **联动**：更新线路 `from_bus`/`to_bus` 为另一端母线索引；开关记录元素类型与索引

### 变压器经开关闭合到两母线

- **端 A**：开关 ↔ 母线
- **端 B**：开关 ↔ 变压器高/低压侧；随后开关另一端 ↔ 母线
- **联动**：更新变压器 `hv_bus`/`lv_bus` 为另一端母线索引；开关记录元素类型与索引

### 功率设备接入母线并加电表

- 功率设备 ↔ 母线；功率设备连接点 ↔ 电表
- **约束**：功率设备仅 1 母线；电表在该设备上至多 1 个

---

## 字段说明

### 字段标记说明

| 标记 | 含义 |
|------|------|
| `*` | 描述拓扑结构的必要字段 |
| `**` | 描述设备属性 |
| `***` | 其他信息（品牌、SN等） |

### 字段定义表

| 字段名称 | 所属设备类型 | 说明 |
|---------|-------------|------|
| `name`* | 所有设备类型 | 设备的名称（如 bus0、line2、grid0 或任意名称） |
| `index`* | 所有设备类型 | int32，同类设备序号，与设备类型组合成为唯一 ID |
| `vn_kv`** | Bus | 总线的额定电压，单位为千伏（kV） |
| `from_bus`* | Line | 线路的起始总线 index |
| `to_bus`* | Line | 线路的终止总线 index |
| `length_km`** | Line | 线路的长度，单位为千米（km） |
| `r_ohm_per_km`** | Line | 线路每千米的电阻值，单位为欧姆（Ω/km） |
| `x_ohm_per_km`** | Line | 线路每千米的电抗值，单位为欧姆（Ω/km） |
| `c_nf_per_km`** | Line | 线路每千米的电容值，单位为纳法（nF/km） |
| `max_i_ka`** | Line | 最大热电流，单位为千安（kA） |
| `std_type`** | Line、Transformer | 标准类型，与其他设备参数互斥 |
| `bus`* | Load、Static Generator | 设备所连接的总线编号 |
| `brand`*** | Load、Static Generator、Measurement、Storage | 设备的品牌 |
| `sn`*** | Load、Static Generator、Measurement、Storage | 设备的序列号 |
| `hv_bus`* | Transformer | 变压器高压侧所连接的总线 index |
| `lv_bus`* | Transformer | 变压器低压侧所连接的总线 index |
| `sn_mva`** | Transformer | 变压器的额定容量，单位为兆伏安（MVA） |
| `vn_hv_kv`** | Transformer | 变压器高压侧的额定电压，单位为千伏（kV） |
| `vn_lv_kv`** | Transformer | 变压器低压侧的额定电压，单位为千伏（kV） |
| `vkr_percent`** | Transformer | 变压器短路电压的有功分量百分比（%） |
| `vk_percent`** | Transformer | 变压器短路电压（阻抗电压）百分比（%） |
| `pfe_kw`** | Transformer | 变压器的铁损，单位为千瓦（kW） |
| `i0_percent`** | Transformer | 变压器空载损耗占额定电流的百分比（%） |
| `meas_type`** | Measurement | 测量类型，默认为 "p" |
| `element_type`* | Measurement | 被测量的设备类型 |
| `element`* | Measurement | 被测量的具体 index |
| `side`* | Measurement | 测量点位置（仅用于 line 和 trafo） |
| `max_e_mwh`** | Storage | 储能设备的最大容量，单位为兆瓦时（MWh） |
| `ip`*** | Charger、Static Generator、Measurement、Storage | IPv4 地址 |
| `port`*** | Charger、Static Generator、Measurement、Storage | 端口 |
| `baud`*** | Charger、Static Generator、Measurement、Storage | 波特率 |
| `parity`*** | Charger、Static Generator、Measurement、Storage | 校验位（odd/even） |
| `com_mode`*** | Charger、Static Generator、Measurement、Storage | 通信模式（modbus_rtu/modbus_tcp） |

### 测量类型说明（meas_type）

| 值 | 含义 | 单位 |
|----|------|------|
| `v` | 电压（Voltage） | p.u.（标幺值） |
| `p` | 有功功率（Active Power） | MW（兆瓦） |
| `q` | 无功功率（Reactive Power） | MVAr（兆乏） |
| `i` | 电流（Current） | kA（千安） |

### 测量设备 side 字段说明

| 设备类型 | 可选值 |
|---------|-------|
| Line | `from_bus`、`to_bus` |
| Transformer | `hv_bus`、`lv_bus` |

### 被测设备类型（element_type）

`bus`、`line`、`trafo`、`storage`、`load`、`sgen`、`charger`、`ext_grid`

---

## JSON 示例

### 无设备参数示例

```json
{
    "Bus": [
        { "name": "bus0", "index": 0 },
        { "name": "bus1", "index": 1 }
    ],
    "Line": [
        { "from_bus": 0, "to_bus": 1, "name": "line0", "index": 0 }
    ],
    "Load": [
        { "bus": 1, "name": "load0", "brand": "ABB", "sn": "SN001", "index": 0 }
    ],
    "Charger": [
        {
            "bus": 1,
            "name": "charger0",
            "brand": "Tesla",
            "sn": "SN002",
            "index": 0,
            "ip": "192.168.1.100",
            "port": "502",
            "baud": "9600",
            "parity": "even",
            "com_mode": "modbus_tcp",
            "children": [
                { "sn": "SN002-1" },
                { "sn": "SN002-2" }
            ]
        }
    ],
    "Static_Generator": [
        { "bus": 0, "name": "pv0", "brand": "Huawei", "sn": "SN003", "index": 0 }
    ],
    "External_Grid": [
        { "bus": 0, "name": "grid0" }
    ],
    "Transformer": [
        { "hv_bus": 0, "lv_bus": 1, "name": "trafo0", "index": 0 }
    ],
    "Measurement": [
        {
            "meas_type": "p",
            "element_type": "bus",
            "element": 0,
            "side": null,
            "name": "meter0",
            "brand": "Siemens",
            "sn": "SN004",
            "index": 0
        }
    ],
    "Storage": [
        {
            "bus": 1,
            "name": "storage0",
            "brand": "BYD",
            "sn": "SN005",
            "index": 0,
            "children": [
                { "sn": "SN005-1" },
                { "sn": "SN005-2" }
            ]
        }
    ]
}
```

### 带设备参数示例

```json
{
    "Bus": [
        { "vn_kv": 30, "name": "bus0", "index": 0 },
        { "vn_kv": 30, "name": "bus1", "index": 1 }
    ],
    "Line": [
        {
            "from_bus": 0,
            "to_bus": 1,
            "length_km": 1.5,
            "r_ohm_per_km": 0.1,
            "x_ohm_per_km": 0.2,
            "c_nf_per_km": 10,
            "max_i_ka": 0.5,
            "name": "line0",
            "index": 0
        }
    ],
    "Load": [
        { "bus": 1, "name": "load0", "brand": "ABB", "sn": "SN001", "index": 0 }
    ],
    "Charger": [
        { "bus": 1, "name": "charger0", "brand": "Tesla", "sn": "SN002", "index": 0 }
    ],
    "Static_Generator": [
        { "bus": 0, "name": "pv0", "brand": "Huawei", "sn": "SN003", "index": 0 }
    ],
    "External_Grid": [
        { "bus": 0, "name": "grid0" }
    ],
    "Transformer": [
        {
            "hv_bus": 0,
            "lv_bus": 1,
            "sn_mva": 10,
            "vn_hv_kv": 110,
            "vn_lv_kv": 30,
            "vkr_percent": 0.5,
            "vk_percent": 10,
            "pfe_kw": 5,
            "i0_percent": 0.1,
            "name": "trafo0",
            "index": 0
        }
    ],
    "Measurement": [
        {
            "meas_type": "p",
            "element_type": "line",
            "element": 0,
            "side": "from_bus",
            "name": "meter0",
            "brand": "Siemens",
            "sn": "SN004",
            "index": 0
        }
    ],
    "Storage": [
        {
            "bus": 1,
            "max_e_mwh": 5,
            "name": "storage0",
            "brand": "BYD",
            "sn": "SN005",
            "index": 0
        }
    ]
}
```

---

## 内部拓扑格式（新格式）

系统内部使用的拓扑格式与 pandapower 格式不同，主要区别在于：

1. **设备-连接分离**：设备和连接分别存储，而非嵌入式引用
2. **连接点信息**：连接记录了具体的连接点（port），支持多连接点设备

### 连接数据结构

```json
{
  "id": "edge-device-3-device-4-1234567890",
  "from_device_id": "device-3",
  "to_device_id": "device-4",
  "from_port": "bottom",
  "to_port": "top",
  "connection_type": "line",
  "properties": {},
  "is_active": true
}
```

### 连接点定义

| 设备类型 | 连接点 | 说明 |
|---------|--------|------|
| 母线（bus） | `center` | 唯一连接点 |
| 线路（line） | `top`, `bottom` | 起点和终点 |
| 变压器（transformer） | `top`, `bottom` | 高压侧和低压侧 |
| 开关（switch） | `top`, `bottom` | 两个连接端 |
| 功率设备 | `top` | 唯一连接点（光伏、储能、负载、充电桩、外部电网） |
| 电表（meter） | `top` | 唯一连接点 |

### 连接字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 连接唯一标识 |
| `from_device_id` | string | 源设备 ID |
| `to_device_id` | string | 目标设备 ID |
| `from_port` | string? | 源设备连接点（可选，用于多连接点设备） |
| `to_port` | string? | 目标设备连接点（可选，用于多连接点设备） |
| `connection_type` | string | 连接类型（line, transformer, power 等） |
| `properties` | object | 连接属性 |
| `is_active` | boolean | 连接是否激活 |

### 内部格式示例

```json
{
  "id": "default",
  "name": "示例拓扑",
  "description": "",
  "devices": {
    "device-1": {
      "id": "device-1",
      "name": "母线-1",
      "device_type": "Node",
      "properties": {},
      "position": { "x": 100, "y": 100, "z": 0 }
    },
    "device-2": {
      "id": "device-2",
      "name": "开关-2",
      "device_type": "Switch",
      "properties": {},
      "position": { "x": 100, "y": 200, "z": 0 }
    },
    "device-3": {
      "id": "device-3",
      "name": "变压器-3",
      "device_type": "Transformer",
      "properties": {},
      "position": { "x": 100, "y": 300, "z": 0 }
    }
  },
  "connections": {
    "conn-1": {
      "id": "conn-1",
      "from_device_id": "device-1",
      "to_device_id": "device-2",
      "from_port": "center",
      "to_port": "top",
      "connection_type": "line",
      "properties": {},
      "is_active": true
    },
    "conn-2": {
      "id": "conn-2",
      "from_device_id": "device-2",
      "to_device_id": "device-3",
      "from_port": "bottom",
      "to_port": "top",
      "connection_type": "line",
      "properties": {},
      "is_active": true
    }
  }
}
```

---

## 参考文档

- [pandapower Elements Documentation](https://pandapower.readthedocs.io/en/v3.1.1/elements.html)
- [pandapower Standard Types](https://pandapower.readthedocs.io/en/v3.1.1/std_types/basic.html)
