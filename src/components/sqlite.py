
import sqlite3  

conn = sqlite3.connect("filtered.db") 

    # conn.execute(f"ATTACH DATABASE '{DB_PATH}' AS source")

    # 创建与原结构相同的表（无聚合逻辑）
conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meter_data(
        device_sn TEXT NOT NULL,       -- 设备序列号
        timestamp INTEGER NOT NULL,    -- UNIX时间戳
        activePower REAL,              -- 有功功率
        ACfrequency REAL,             -- 交流频率（注意拼写修正）
        activeEnergy REAL,             -- 有功电能
        reverseActiveEnergy REAL,      -- 反向有功电能
        reactivePower REAL,            -- 无功功率
        apparentPower REAL,            -- 视在功率
        powerFactor REAL,               -- 功率因数
        local_timestamp INTEGER NOT NULL
        );"""
    )
conn.execute(
        """
        CREATE TABLE IF NOT EXISTS storage_data(
        device_sn TEXT NOT NULL,       -- 设备序列号
        timestamp INTEGER NOT NULL,    -- UNIX时间戳
        ACfrequency REAL,             -- 交流频率
        activePower REAL,             -- 有功功率
        reactivePower REAL,           -- 无功功率
        max_charge_power REAL,        -- 最大充电功率
        max_discharge_power REAL,      -- 最大放电功率
        internalT REAL,               -- PCS内部温度平均值
        radiatorT REAL,               -- 散热器温度平均值
        soc REAL,                     -- 平均荷电状态
        soh REAL,                     -- 平均健康状态
        total_charge_energy REAL,      -- 累计充电量
        total_discharge_energy REAL,   -- 累计放电量
        today_charge_energy REAL,      -- 当日充电量
        today_discharge_energy REAL,  -- 当日放电量
        sumCapacity REAL,    
        local_timestamp INTEGER NOT NULL
        );"""
    )
conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pv_data(
        device_sn TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        activePower REAL,
        activePowerLimit REAL,
        internalTemp REAL,
        ratedPower REAL,
        dayActiveEnergy REAL,
        reverseActiveEnergy REAL,
        tTotal REAL,
        reactivePower REAL,
        powerFactor REAL,
        ACfrequency REAL,
        local_timestamp INTEGER NOT NULL
        );
        """
    )
conn.execute(
        """
        CREATE TABLE IF NOT EXISTS charger_data(
            device_sn TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            need_power REAL,
            activePower REAL,
            chargeEnergy REAL,
            meterNow REAL,
            local_timestamp INTEGER NOT NULL
            OutVoltage REAL
            OutCurrent REAL
            NeedVoltage REAL
            NeedCurrent REAL
            Soc REAL
        );"""
    )
conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cmd_data(
            timestamp INTEGER NOT NULL,
            device_sn TEXT NOT NULL,
            name TEXT,
            value REAL,
            local_timestamp INTEGER NOT NULL
        );
        """
    )