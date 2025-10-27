
import sqlite3  

def init_database(db_path="filtered.db"):
    """
    初始化数据库，创建所有必要的表
    
    Args:
        db_path (str): 数据库文件路径，默认为filtered.db
    """
    # 连接到指定路径的数据库
    conn = sqlite3.connect(db_path)
    
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
                local_timestamp INTEGER NOT NULL,
                OutVoltage REAL,
                OutCurrent REAL,
                NeedVoltage REAL,
                NeedCurrent REAL,
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
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()
    print(f"数据库初始化完成，所有表已创建: {db_path}")

# 如果直接运行此文件，则初始化数据库
if __name__ == "__main__":
    init_database()