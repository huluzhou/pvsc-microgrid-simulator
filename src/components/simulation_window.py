#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
仿真界面窗口
"""


from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QTreeWidgetItem, QMessageBox, QDockWidget, QFileDialog, QStatusBar
  )
import threading
import time
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
import pandapower as pp
from datetime import datetime

from .data_generators import DataGeneratorManager

# Modbus管理器导入
from .modbus_manager import ModbusManager
# UI组件管理器导入
from .ui_components import UIComponentManager
# 功率监控模块导入
from .power_monitor import PowerMonitor
from .sqlite import init_database
from utils.logger import logger


class SimulationWindow(QMainWindow):
    """仿真界面窗口"""
    # 定义信号，参数为设备索引和新的功率值
    storage_power_changed = Signal(int, float)
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        # 先进行内存清理，确保之前仿真不会遗留内存
        self._cleanup_previous_simulation()
        
        # 数据记录相关属性
        self.is_recording = False
        self.recording_thread = None
        self.recording_lock = threading.Lock()
        self.db_path = None  # 数据库文件路径
        
        # 回测相关属性
        self.is_backtesting = False
        self.backtest_data = None
        self.backtest_data_index = None
        self.backtest_current_step = 0
        self.backtest_start_time = None
        self.backtest_timer = None
        
        self.canvas = canvas
        self.parent_window = parent
        self.network_model = self.parent_window.network_model
        self.network_items = self.parent_window.network_items
        # 从canvas获取scene引用
        self.scene = canvas.scene if hasattr(canvas, 'scene') else None
        
        # 自动潮流计算相关属性
        self.auto_calc_timer = QTimer()
        self.auto_calc_timer.timeout.connect(self.auto_power_flow_calculation)
        self.is_auto_calculating = False
        self.selected_device_id = None
        self.selected_device_type = None
        self.generated_devices = set()
        
        # 数据生成器管理
        self.data_generator_manager = DataGeneratorManager()
        self.current_load_index = 0
        
        # 当前显示的组件信息（用于自动更新组件参数表格）
        self.current_component_type = None
        self.current_component_idx = None
        
        # 光伏能量统计相关属性
        self.last_pv_update_time = None
        self.last_reset_date = datetime.now().date()
        
        # 储能能量统计相关属性
        self.last_storage_update_time = None
        
        # 初始化功率监控管理器
        self.power_monitor = PowerMonitor(self)

        # Modbus服务器管理器
        self.modbus_manager = ModbusManager(self.network_model, self.network_items, self.power_monitor, self.scene)
        
        # 初始化数据控制管理器，传入已创建的数据生成器管理器实例
        from .data_control import DataControlManager
        self.data_control_manager = DataControlManager(self, self.data_generator_manager)

        # 初始化UI组件管理器
        self.ui_manager = UIComponentManager(self)
        
        self.init_ui()
        self.load_network_data()
        # 默认不启动自动计算，需要用户手动启动
        self.is_auto_calculating = False
        # 初始化新的计算控制UI状态
        if hasattr(self, 'start_calc_btn'):
            self.start_calc_btn.setChecked(False)
            self.start_calc_btn.setText("开始仿真")
        if hasattr(self, 'calc_status_label'):
            self.calc_status_label.setText("仿真状态: 已停止")
    
    def _cleanup_previous_simulation(self):
        """清理之前仿真可能遗留的内存"""
        try:
            import gc
            
            # 强制垃圾回收
            gc.collect()
            
        except Exception as e:
            logger.error(f"定期清理失败: {e}")

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("仿真模式 - PandaPower 仿真工具")
        self.setMinimumSize(1500, 800)
        
        # 创建主窗口部件和布局
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 初始化菜单栏
        self.init_menu_bar()
        
        # 添加状态显示面板 - 这里使用不同的方式来确保小部件不会被销毁
        self.init_status_indicators()
        
        # 将状态指示器面板添加到主布局
        self.main_layout.addWidget(self.status_indicators_bar)
        
        # 创建中央功率曲线区域
        self.central_chart_widget = QWidget()
        layout = QHBoxLayout(self.central_chart_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        # 设置中央区域大小策略
        self.central_chart_widget.setMinimumSize(600, 400)
        self.ui_manager.create_central_image_area(layout)
        
        # 将中央图表部件添加到主布局
        self.main_layout.addWidget(self.central_chart_widget)
        
        # 设置主窗口的中央部件
        self.setCentralWidget(self.central_widget)
        
        
        # 创建左侧设备树dockwidget
        self.device_tree_dock = QDockWidget("网络设备", self)
        self.device_tree_dock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.device_tree_dock.setMinimumWidth(250)
        self.device_tree_dock.setMaximumWidth(400)
        self.ui_manager.create_device_tree_panel(self.device_tree_dock)
        # 添加dock widget到主窗口
        self.addDockWidget(Qt.LeftDockWidgetArea, self.device_tree_dock)
        
        
        # 创建四个设备类型的dockwidget
        # 创建光伏设备dockwidget
        self.sgen_dock = QDockWidget("光伏设备数据", self)
        self.sgen_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.sgen_dock.setMinimumWidth(300)
        self.sgen_dock.setMaximumWidth(500)
        self.ui_manager.create_sgen_data_panel(self.sgen_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.sgen_dock)
        self.sgen_dock.hide()  # 初始隐藏
        
        # 负载设备dockwidget
        self.load_dock = QDockWidget("负载设备数据", self)
        self.load_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.load_dock.setMinimumWidth(300)
        self.load_dock.setMaximumWidth(500)
        self.ui_manager.create_load_data_panel(self.load_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.load_dock)
        self.load_dock.hide()  # 初始隐藏
        
        # 储能设备dockwidget
        self.storage_dock = QDockWidget("储能设备数据", self)
        self.storage_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.storage_dock.setMinimumWidth(300)
        self.storage_dock.setMaximumWidth(500)
        self.ui_manager.create_storage_data_panel(self.storage_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.storage_dock)
        self.storage_dock.hide()  # 初始隐藏
        
        # 充电桩设备dockwidget
        self.charger_dock = QDockWidget("充电桩设备数据", self)
        self.charger_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.charger_dock.setMinimumWidth(300)
        self.charger_dock.setMaximumWidth(500)
        self.ui_manager.create_charger_data_panel(self.charger_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.charger_dock)
        self.charger_dock.hide()  # 初始隐藏
        
        # 开关设备dockwidget
        self.switch_dock = QDockWidget("开关设备数据", self)
        self.switch_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.switch_dock.setMinimumWidth(300)
        self.switch_dock.setMaximumWidth(500)
        self.ui_manager.create_switch_data_panel(self.switch_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.switch_dock)
        self.switch_dock.hide()  # 初始隐藏
        
        # 创建并显示状态栏
        self.statusBar().showMessage("仿真模式已就绪")
        
        # 初始化功率监控的UI组件引用
        self.power_monitor.initialize_ui_components()
        
        
    def init_status_indicators(self):
        """初始化状态指示器面板"""
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QStatusBar
        from PySide6.QtCore import Qt
        
        # 创建一个独立的状态条小部件，而不是使用菜单栏的corner widget
        self.status_indicators_bar = QWidget()
        self.status_indicators_bar.setMinimumHeight(25)
        self.status_indicators_layout = QHBoxLayout(self.status_indicators_bar)
        self.status_indicators_layout.setContentsMargins(10, 2, 10, 2)
        self.status_indicators_layout.setSpacing(20)
        
        # 创建回测状态指示器
        self.backtest_status_indicator = QFrame()
        self.backtest_status_indicator.setFixedSize(12, 12)
        self.backtest_status_indicator.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.backtest_status_indicator.setStyleSheet("background-color: #9E9E9E;")  # 灰色表示未运行
        
        self.backtest_status_label = QLabel("回测: 未运行")
        
        # 创建记录数据状态指示器
        self.record_status_indicator = QFrame()
        self.record_status_indicator.setFixedSize(12, 12)
        self.record_status_indicator.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.record_status_indicator.setStyleSheet("background-color: #9E9E9E;")  # 灰色表示未运行
        
        self.record_status_label = QLabel("记录: 未运行")
        
        # 将指示器添加到布局中
        self.status_indicators_layout.addWidget(QLabel("运行状态:"))
        self.status_indicators_layout.addWidget(self.backtest_status_indicator)
        self.status_indicators_layout.addWidget(self.backtest_status_label)
        self.status_indicators_layout.addWidget(self.record_status_indicator)
        self.status_indicators_layout.addWidget(self.record_status_label)
        
        # 将状态指示器条添加到主布局中，放在菜单栏下方
        # 注意：我们不在此处添加到主布局，而是在创建中央部件后添加
    
    def update_backtest_status(self, is_running):
        """更新回测状态显示"""
        # 检查对象是否存在且有效
        if hasattr(self, 'backtest_status_label') and hasattr(self, 'backtest_status_indicator'):
            try:
                if is_running:
                    self.backtest_status_label.setText("回测: 运行中")
                    self.backtest_status_indicator.setStyleSheet("background-color: #2196F3;")  # 蓝色表示运行中
                else:
                    self.backtest_status_label.setText("回测: 未运行")
                    self.backtest_status_indicator.setStyleSheet("background-color: #9E9E9E;")  # 灰色表示未运行
            except RuntimeError:
                # 忽略对象已被销毁的错误
                pass
    
    def update_record_status(self, is_recording):
        """更新记录数据状态显示"""
        # 检查对象是否存在且有效
        if hasattr(self, 'record_status_label') and hasattr(self, 'record_status_indicator'):
            try:
                if is_recording:
                    self.record_status_label.setText("记录: 运行中")
                    self.record_status_indicator.setStyleSheet("background-color: #FF9800;")  # 橙色表示运行中
                else:
                    self.record_status_label.setText("记录: 未运行")
                    self.record_status_indicator.setStyleSheet("background-color: #9E9E9E;")  # 灰色表示未运行
            except RuntimeError:
                # 忽略对象已被销毁的错误
                pass
    
    def init_menu_bar(self):
        """初始化菜单栏"""
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 创建数据菜单
        data_menu = menubar.addMenu("数据")
        record_data_menu = data_menu.addMenu("记录数据")
        backtest_menu = data_menu.addMenu("回测功能")
        
        # 添加导入回测数据菜单项
        import_backtest_action = backtest_menu.addAction("导入回测数据")
        import_backtest_action.triggered.connect(self.import_backtest_data)
        
        # 添加开始回测菜单项
        start_backtest_action = backtest_menu.addAction("开始回测")
        start_backtest_action.triggered.connect(self.start_backtest)
        
        # 添加停止回测菜单项
        stop_backtest_action = backtest_menu.addAction("停止回测")
        # 连接信号时使用lambda确保传递正确的参数类型
        stop_backtest_action.triggered.connect(lambda: self.stop_backtest())
        
        # 添加记录仿真数据菜单项
        record_simulation_action = record_data_menu.addAction("记录仿真数据")
        record_simulation_action.triggered.connect(self.record_simulation_data)

        stop_record_action = record_data_menu.addAction("停止记录")
        stop_record_action.triggered.connect(self.stop_record_data)
        
    def import_backtest_data(self):
        """导入回测数据"""
        try:
            # 打开文件选择对话框，只支持SQLite数据库文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "选择回测数据文件", 
                "", 
                "SQLite数据库 (*.db);;所有文件 (*.*)"
            )
            
            if not file_path:
                # 用户取消选择
                return
            
            # 验证文件扩展名是否为.db
            if not file_path.endswith('.db'):
                QMessageBox.warning(self, "格式错误", "请选择SQLite数据库文件 (*.db)")
                return
            
            # 从SQLite数据库读取数据
            df = self._read_backtest_data_from_db(file_path)
            
            # 检查数据格式是否正确
            required_columns = ['timestamp', 'device_type', 'device_id', 'p_mw']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                QMessageBox.warning(self, "格式错误", 
                                   f"文件缺少必要的列: {', '.join(missing_columns)}")
                return
            
            # 显示数据预览对话框
            preview_text = "成功导入回测数据文件\n"
            preview_text += f"数据总行数: {len(df)}\n"
            
            # 统计设备类型
            device_types = df['device_type'].unique()
            preview_text += f"包含设备类型: {', '.join(device_types)}\n"
            
            # 统计设备数量（使用device_type和device_id组合唯一标识设备）
            device_count = len(df.groupby(['device_type', 'device_id']).size())
            preview_text += f"设备总数: {device_count} 个\n"
            
            # 存储回测数据到实例变量
            self.backtest_data = df
            # 注意：is_backtesting标志将在开始回测时设置，而不是导入时
            
            # 准备回测数据的索引结构，优化查询性能
            self._prepare_backtest_data_index()
            
            # 提示用户开始回测
            reply = QMessageBox.question(self, "导入成功", 
                                        f"{preview_text}\n是否立即开始回测？",
                                        QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # 如果用户选择立即开始回测，可以在这里添加启动回测的代码
                self.start_backtest()
                
        except Exception as e:
            logger.error(f"导入回测数据失败: {str(e)}")
            QMessageBox.critical(self, "导入失败", 
                               f"导入回测数据时发生错误: {str(e)}")
            
    def _read_backtest_data_from_db(self, db_path):
        """从SQLite数据库读取回测数据"""
        try:
            import pandas as pd
            import sqlite3
            
            # 连接到数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取数据库中的所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [table[0] for table in cursor.fetchall()]
            
            if not tables:
                raise Exception("数据库中没有表")
            
            # 存储所有设备数据的列表
            all_data = []
            
            # 读取每个表中的数据
            for table in tables:
                # 跳过命令数据表
                if table == 'cmd_data':
                    continue
                
                # 如果是meter_data表，需要特殊处理
                if table == 'meter_data':
                    # 查询meter_data表中的数据
                    df_meter = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                    if not df_meter.empty:
                        for _, row in df_meter.iterrows():
                            device_sn = row['device_sn']
                            # 从表名获取设备类型信息，优化查找效率
                            table_device_type = table.replace('_data', '')
                            # 使用_find_device_type_and_id_by_sn方法获取设备类型和ID，传入表名对应的设备类型
                            device_type, device_id = self._find_device_type_and_id_by_sn(device_sn, table_device_type)
                            
                            # 如果没有找到设备类型，根据设备序列号判断设备类型
                            if not device_type:
                                logger.warning(f"未找到设备类型，根据SN判断: {device_sn}")
                                continue
                            
                            data_row = {
                                'timestamp': row['timestamp'],
                                'device_type': device_type,
                                'device_id': device_id,
                                'p_mw': row['activePower'] / 1000 if 'load' in device_sn else 0.0,  # 转换为MW
                                'q_mvar': row.get('reactivePower', 0.0) / 1000 if 'load' in device_sn else 0.0  # 转换为MVAr
                            }
                            all_data.append(data_row)
                elif table == 'load_data':
                    # 查询load_data表中的数据
                    df_load = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                    if not df_load.empty:
                        for _, row in df_load.iterrows():
                            device_id = row['device_id']
                            data_row = {
                                'timestamp': row['timestamp'],
                                'device_type': 'load',
                                'device_id': device_id,
                                'p_mw': row['activePower'] / 1000,  # 转换为MW
                                'q_mvar': row.get('reactivePower', 0.0) / 1000  # 转换为MVAr
                            }
                            all_data.append(data_row)
                else:
                    # 查询其他表的数据
                    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                    if not df.empty:
                        # 从device_sn字段提取设备信息
                        for _, row in df.iterrows():
                            device_sn = row['device_sn']
                            
                            table_device_type = table.replace('_data', '')
                            # 使用_find_device_type_and_id_by_sn方法获取设备类型和ID
                            device_type, device_id = self._find_device_type_and_id_by_sn(device_sn, table_device_type)
                            
                            # 如果没有找到设备类型和ID，使用表名和从SN提取的ID作为默认值
                            if not device_type:
                                logger.warning(f"未找到设备类型，根据SN判断: {device_sn}")
                                continue
                            
                            # 根据设备类型选择功率字段
                            if device_type == 'static_generator':
                                p_mw = row.get('activePower', 0.0) / 1000  # 转换为MW
                                q_mvar = row.get('reactivePower', 0.0) / 1000  # 转换为MVAr
                            elif device_type == 'storage':
                                p_mw = row.get('activePower', 0.0) / 1000  # 转换为MW
                                q_mvar = row.get('reactivePower', 0.0) / 1000  # 转换为MVAr
                            elif device_type == 'charger':
                                p_mw = row.get('activePower', 0.0) / 1000  # 转换为MW
                                q_mvar = row.get('reactivePower', 0.0) / 1000  # 转换为MVAr
                            else:
                                p_mw = 0.0
                                q_mvar = 0.0
                            
                            data_row = {
                                'timestamp': row['timestamp'],
                                'device_type': device_type,
                                'device_id': device_id,
                                'p_mw': p_mw,
                                'q_mvar': q_mvar
                            }
                            all_data.append(data_row)
            
            # 关闭数据库连接
            conn.close()
            
            if not all_data:
                raise Exception("数据库中没有可用于回测的设备数据")
            
            # 将所有数据转换为DataFrame
            result_df = pd.DataFrame(all_data)
            
            if result_df.empty:
                raise Exception("没有找到有效的设备数据")
            
            # 将timestamp列转换为datetime类型
            try:
                result_df['timestamp'] = pd.to_datetime(result_df['timestamp'], unit='s')
            except Exception:
                # 如果转换失败，尝试其他格式
                try:
                    result_df['timestamp'] = pd.to_datetime(result_df['timestamp'])
                except Exception as e:
                    # 如果都失败，保持原始格式但记录警告
                    logger.warning(f"无法将timestamp转换为datetime格式: {str(e)}")
                    # 按时间戳排序
                    result_df.sort_values(by='timestamp', inplace=True)
                    return result_df
            
            # 设置timestamp为索引
            result_df.set_index('timestamp', inplace=True)
            
            # 创建空的结果DataFrame用于存储重采样后的数据
            resampled_data = []
            
            # 按设备类型和设备ID分组进行重采样
            for (device_type, device_id), group in result_df.groupby(['device_type', 'device_id']):
                # 对每个设备的数据进行1秒重采样
                # 使用前向填充和线性插值相结合的方式
                try:
                    # 首先进行1秒重采样，保留原始值
                    resampled = group.resample('1s').asfreq()
                    
                    # 对缺失的值进行前向填充（保留最近的有效值）
                    resampled = resampled.ffill()
                    
                    # 先推断数据类型
                    resampled = resampled.infer_objects(copy=False)
                    
                    # 重新添加设备类型和设备ID信息，确保与DataFrame行数匹配
                    resampled['device_type'] = [device_type] * len(resampled)
                    resampled['device_id'] = [device_id] * len(resampled)
                    
                    # 只对数值型列进行线性插值，避免object类型警告
                    numeric_cols = resampled.select_dtypes(include=['float64', 'int64']).columns
                    if not numeric_cols.empty:
                        resampled[numeric_cols] = resampled[numeric_cols].interpolate(method='linear')
                    
                    # 转换回秒级时间戳
                    resampled.reset_index(inplace=True)
                    resampled['timestamp'] = resampled['timestamp'].astype(int) / 10**9  # 转换为秒
                    
                    # 添加到结果列表
                    resampled_data.append(resampled)
                except Exception as e:
                    logger.error(f"重采样设备数据失败 (设备类型: {device_type}, ID: {device_id}): {str(e)}")
                    # 如果重采样失败，使用原始数据
                    group.reset_index(inplace=True)
                    group['timestamp'] = group['timestamp'].astype(int) / 10**9  # 转换为秒
                    resampled_data.append(group)
            
            # 合并所有重采样后的数据
            if resampled_data:
                result_df = pd.concat(resampled_data)
            else:
                # 如果重采样失败，重置索引并转换时间戳
                result_df.reset_index(inplace=True)
                result_df['timestamp'] = result_df['timestamp'].astype(int) / 10**9  # 转换为秒
            
            # 按时间戳排序
            result_df.sort_values(by='timestamp', inplace=True)
            
            logger.info(f"回测数据重采样完成，总记录数: {len(result_df)}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"从数据库读取回测数据失败: {str(e)}")
            raise Exception(f"读取数据库时出错: {str(e)}")
    
    def _prepare_backtest_data_index(self):
        """准备回测数据的索引结构，优化查询性能"""
        if not hasattr(self, 'backtest_data'):
            return
        
        # 初始化索引结构: backtest_data_index[device_type][device_id][second_key]
        self.backtest_data_index = {}
        self.backtest_max_timestamp = 0  # 存储最大时间戳（秒）
        
        # 遍历所有数据行
        for _, row in self.backtest_data.iterrows():
            # 优先使用数据行中预先提取的device_type和device_id
            device_type = row.get('device_type')
            device_id = row.get('device_id')
            
            # 如果数据行中没有设备类型和ID，记录警告并跳过
            if not device_type or device_id is None:
                logger.warning("无法找到设备对应的类型和ID，跳过此数据点")
                continue
            
            # 初始化嵌套字典结构
            if device_type not in self.backtest_data_index:
                self.backtest_data_index[device_type] = {}
            if device_id not in self.backtest_data_index[device_type]:
                self.backtest_data_index[device_type][device_id] = {}
            
            # 将timestamp转换为整数秒作为索引键
            try:
                second_key = int(float(row['timestamp']))
                self.backtest_data_index[device_type][device_id][second_key] = {
                    'timestamp': row['timestamp'],
                    'p_mw': row['p_mw'],
                    'q_mvar': row.get('q_mvar', 0.0)
                }
                # 更新最大时间戳
                if second_key > self.backtest_max_timestamp:
                    self.backtest_max_timestamp = second_key
            except (ValueError, TypeError):
                logger.warning(f"无法将时间戳 {row['timestamp']} 转换为秒数，跳过此数据点")
        
        # 记录统计信息
        total_devices = sum(len(devices) for devices in self.backtest_data_index.values())
        total_data_points = sum(sum(len(data_points) for data_points in devices.values()) 
                               for devices in self.backtest_data_index.values())
        logger.info(f"回测数据索引准备完成: 设备总数={total_devices}, 数据点总数={total_data_points}, 最大时间戳={self.backtest_max_timestamp}秒")
    
    def _find_device_type_and_id_by_sn(self, device_sn, table_device_type=None):
        """通过device_sn在network_items中查找对应的设备类型和ID
        
        Args:
            device_sn: 设备序列号
            table_device_type: 从表名推断的设备类型（可选），用于优化查找效率
        
        Returns:
            设备类型和设备ID的元组
        """
        if not hasattr(self, 'network_items') or not self.network_items:
            return None, None
            
        try:
            # 如果提供了表名对应的设备类型，直接在该类型中查找
            type_map = {
                'pv': 'static_generator',
                'storage': 'storage',
                'charger': 'charger',
                'meter': 'meter',
                'load': 'load',
            }
            dev_type = type_map.get(table_device_type, table_device_type)
            if dev_type and dev_type in self.network_items:
                item_dict = self.network_items[dev_type]
                # 处理字典类型的item_dict
                if isinstance(item_dict, dict):
                    for item in item_dict.values():
                        # 检查设备是否有properties字典并且包含device_sn属性
                        if hasattr(item, 'properties'):
                            if 'sn' in item.properties and item.properties['sn'] == device_sn:
                                return item.component_type, item.component_index
            
            # 如果没有找到匹配的设备，返回None
            return None, None
            
        except Exception as e:
            logger.error(f"查找设备类型和ID失败: {device_sn}, 错误: {str(e)}")
            return None, None
    
    def start_backtest(self):
        """开始回测过程"""
        # 检查是否有回测数据而不是检查is_backtesting标志
        if not hasattr(self, 'backtest_data') or self.backtest_data is None:
            QMessageBox.warning(self, "警告", "没有可用的回测数据，请先导入回测数据")
            return
        
        # 设置回测标志
        self.is_backtesting = True
        
        # 更新回测状态显示
        self.update_backtest_status(True)
        
        # 初始化回测状态
        self.backtest_current_step = 0
        self.backtest_start_time = time.time()
        
        # 存储回测数据中的最小时间戳作为基准时间
        if hasattr(self, 'backtest_data_index'):
            # 获取所有时间戳并找到最小值
            all_timestamps = []
            for devices in self.backtest_data_index.values():
                for data_points in devices.values():
                    all_timestamps.extend(data_points.keys())
            if all_timestamps:
                self.backtest_base_timestamp = min(all_timestamps)
                logger.info(f"回测基准时间戳: {self.backtest_base_timestamp}秒")
            else:
                self.backtest_base_timestamp = 0
        else:
            self.backtest_base_timestamp = 0
        
        # 不再使用回测定时器，回测步骤将在自动潮流计算中运行
        # 直接更新状态和显示消息
        self.statusBar().showMessage("回测已开始")
        QMessageBox.information(self, "成功", "回测已开始")
    
    def run_backtest_step(self):
        """执行回测的每一步"""
        try:
            # 获取当前时间步的数据
            current_time = time.time() - self.backtest_start_time
            current_second = int(current_time)
            
            # 计算实际的数据时间戳
            if hasattr(self, 'backtest_base_timestamp') and hasattr(self, 'backtest_max_timestamp'):
                data_timestamp = self.backtest_base_timestamp + current_second
                
                # 检查当前时间是否已超过回测数据的最大时间戳
                if data_timestamp > self.backtest_max_timestamp:
                    logger.info(f"回测数据已用尽: 当前秒数={current_second}, 数据时间戳={data_timestamp}, 最大时间戳={self.backtest_max_timestamp}")
            else:
                # 兼容旧版本逻辑，直接使用current_second
                data_timestamp = current_second
                if hasattr(self, 'backtest_max_timestamp') and current_second > self.backtest_max_timestamp:
                    logger.info(f"回测数据已用尽: 当前秒数={current_second}, 最大秒数={self.backtest_max_timestamp}")
                
                # 重置所有设备功率为零
                self._reset_all_devices_power()
                
                # 停止回测
                self.stop_backtest("回测数据已用尽")
                return
            
            # 更新设备数据，传递实际的回测时间（从开始到现在的秒数）
            self._update_devices_with_backtest_data(current_time)
            
            # 增加回测步数
            self.backtest_current_step += 1
            
        except Exception as e:
            logger.error(f"回测步骤执行失败: {str(e)}")
            self.stop_backtest()
    
    def _update_devices_with_backtest_data(self, current_time):
        """使用回测数据更新设备状态"""
        if not hasattr(self, 'backtest_data_index'):
            return
            
        # 将current_time转换为整数秒（从回测开始的秒数，从零开始）
        current_second = int(current_time)
        
        # 将回测秒数转换为数据索引中的时间戳
        if hasattr(self, 'backtest_base_timestamp'):
            data_timestamp = self.backtest_base_timestamp + current_second
        else:
            data_timestamp = current_second
            
        logger.debug(f"回测当前秒数: {current_second}秒，数据时间戳: {data_timestamp}秒")
            
        # 遍历所有设备类型和ID
        for device_type, devices in self.backtest_data_index.items():
            for device_id, data_points in devices.items():
                if data_points:
                    # 直接通过秒数索引获取数据点（使用字典键）
                    if data_timestamp in data_points:
                        data_point = data_points[data_timestamp]
                        logger.debug(f"回测数据点: 设备类型={device_type}, ID={device_id}, 秒数={current_second}, 数据时间戳={data_timestamp}")
                        
                        # 更新设备数据
                        self._apply_device_backtest_data(
                            device_type, 
                            device_id, 
                            data_point['p_mw'], 
                            data_point['q_mvar']
                        )
                    else:
                        logger.debug(f"回测数据点不存在: 设备类型={device_type}, ID={device_id}, 秒数={current_second}, 数据时间戳={data_timestamp}")
    

    
    def _apply_device_backtest_data(self, device_type, device_id, p_mw, q_mvar):
        """直接使用设备类型和ID更新回测数据"""
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        net = self.network_model.net
        
        # 如果提供了设备类型和ID，直接更新其数据
        if device_type and device_id is not None:
            try:
                # 根据设备类型更新相应的设备数据
                if device_type == 'load' and hasattr(net, 'load') and device_id in net.load.index:
                    net.load.at[device_id, 'p_mw'] = p_mw
                    net.load.at[device_id, 'q_mvar'] = q_mvar
                elif device_type == 'static_generator' and hasattr(net, 'sgen') and device_id in net.sgen.index:
                    net.sgen.at[device_id, 'p_mw'] = p_mw
                    net.sgen.at[device_id, 'q_mvar'] = q_mvar
                elif device_type == 'charger' and hasattr(net, 'load') and device_id in net.load.index:
                    net.load.at[device_id, 'p_mw'] = p_mw
                    net.load.at[device_id, 'q_mvar'] = q_mvar

            except Exception as e:
                logger.error(f"更新设备 {device_type}_{device_id} 数据失败: {str(e)}")
        else:
            logger.warning("未提供有效的设备类型和ID")
    
    def stop_backtest(self, message="回测已停止"):
        """停止回测过程"""
        # 不再需要停止回测定时器，因为已经移除了定时器
        self.is_backtesting = False
        
        # 更新回测状态显示
        self.update_backtest_status(False)
        
        self.statusBar().showMessage(message)
        QMessageBox.information(self, "提示", message)
        
    def _reset_all_devices_power(self):
        """重置所有设备的功率为零"""
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        net = self.network_model.net
        
        # 重置各类设备的功率
        try:
            # 重置负载
            if hasattr(net, 'load') and not net.load.empty:
                net.load['p_mw'] = 0.0
                net.load['q_mvar'] = 0.0
                logger.info("已重置所有负载功率为零")
            
            # 重置光伏
            if hasattr(net, 'sgen') and not net.sgen.empty:
                net.sgen['p_mw'] = 0.0
                net.sgen['q_mvar'] = 0.0
                logger.info("已重置所有光伏功率为零")
            
            # 重置储能
            if hasattr(net, 'storage') and not net.storage.empty:
                net.storage['p_mw'] = 0.0
                net.storage['q_mvar'] = 0.0
                logger.info("已重置所有储能功率为零")
                
        except Exception as e:
            logger.error(f"重置设备功率时发生错误: {str(e)}")

    
    def record_simulation_data(self):
        """记录仿真数据"""
        with self.recording_lock:
            if self.is_recording:
                QMessageBox.information(self, "提示", "数据记录已经在进行中")
                return
                
            # 弹出文件选择对话框，让用户选择数据库保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "选择数据库保存位置", 
                "filtered.db", 
                "SQLite Database Files (*.db);;All Files (*)"
            )
            
            if not file_path:
                # 用户取消选择
                return
            # 初始化数据库 - 使用用户选择的路径
            init_database(file_path)
            
            # 设置数据库路径
            self.db_path = file_path
            
            # 创建并启动记录线程
            self.is_recording = True
            
            # 更新记录状态显示
            self.update_record_status(True)
            
            self.recording_thread = threading.Thread(target=self._record_data_loop)
            self.recording_thread.daemon = True  # 设置为守护线程，主程序退出时自动终止
            self.recording_thread.start()
            
            self.statusBar().showMessage(f"数据记录已启动，保存至: {self.db_path}")
            QMessageBox.information(self, "成功", f"仿真数据记录已开始，每秒保存一次数据到数据库\n{self.db_path}")
      
    def stop_record_data(self):
        """停止记录数据"""
        with self.recording_lock:
            if not self.is_recording or not self.recording_thread:
                QMessageBox.information(self, "提示", "当前没有正在进行的数据记录")
                return
                
            # 停止记录线程
            self.is_recording = False
            
            # 更新记录状态显示
            self.update_record_status(False)
            if self.recording_thread and self.recording_thread.is_alive():
                # 等待线程自然结束
                self.recording_thread.join(timeout=2.0)  # 设置超时，避免死锁
                self.recording_thread = None
                
            self.statusBar().showMessage("数据记录已停止")
            QMessageBox.information(self, "成功", "仿真数据记录已停止")
            
    def _record_data_loop(self):
        """数据记录循环"""
        try:
            while self.is_recording:
                try:
                    # 保存数据到数据库
                    self.save_data_to_db()
                    
                    # 等待1秒
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"数据记录出错: {str(e)}")
                    # 出错后等待一小段时间再继续
                    time.sleep(0.5)
        finally:
            # 线程结束时确保状态正确
            with self.recording_lock:
                self.is_recording = False
                self.recording_thread = None
            
    def save_data_to_db(self):
        """将当前仿真数据保存到数据库"""
        try:
            import sqlite3
            import time
            
            # 确保网络模型可用
            if not self.network_model or not hasattr(self.network_model, 'net'):
                logger.error("网络模型不可用，无法保存数据到数据库")
                return
                
            net = self.network_model.net
            timestamp = int(time.time())  # UNIX时间戳
            local_timestamp = timestamp
            # 连接到SQLite数据库
            db_file = self.db_path if self.db_path else "simulation.db"
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # 记录电表数据到meter_data表
            if hasattr(self, 'power_monitor') and "meter" in self.network_items:
                # 遍历所有电表，尝试获取对应的电表数据
                # 添加安全检查，确保正确遍历字典项
                meter_items = self.network_items["meter"]
                if isinstance(meter_items, dict):
                    # 使用items()方法安全遍历字典的键值对
                    for _, item in meter_items.items():
                        idx = item.properties['index']
                        # 尝试获取电表数据，使用母线ID作为电表ID
                        activePower = self.power_monitor.get_meter_measurement(idx, 'active_power') * 1000 # 转换为kW
                        reactivePower = self.power_monitor.get_meter_measurement(idx, 'reactive_power') * 1000  # 转换为kVar
                        device_sn = item.properties.get('sn', f"meter_{idx}")
                            
                        apparentPower = (activePower**2 + reactivePower**2)**0.5 if activePower or reactivePower else 0.0
                        powerFactor = activePower / apparentPower if apparentPower else 0.0
                        
                        cursor.execute(
                            "INSERT INTO meter_data (device_sn, timestamp, activePower, reactivePower, apparentPower, powerFactor, local_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (device_sn, timestamp, activePower, reactivePower, apparentPower, powerFactor, local_timestamp)
                        )
            
            # 记录光伏数据到pv_data表
            if hasattr(net, 'sgen') and hasattr(net, 'res_sgen') and not net.res_sgen.empty:
                for idx, sgen_data in net.res_sgen.iterrows():
                    if idx in net.sgen.index:
                        pv_item = self.network_items.get("static_generator", {}).get(idx, {})
                        device_sn = pv_item.properties.get('sn', f"pv_{idx}")
                        activePower = sgen_data.get('p_mw', 0.0) * 1000  # 转换为kW
                        reactivePower = sgen_data.get('q_mvar', 0.0) * 1000  # 转换为kVar
                        powerFactor = activePower / ((activePower**2 + reactivePower**2)**0.5) if activePower or reactivePower else 0.0
                        
                        # 从network_items中获取光伏设备的电量数据 - O(1)查找
                        dayActiveEnergy = 0.0
                        reverseActiveEnergy = 0.0
                        
                        # 直接通过索引映射查找对应的光伏设备 - 使用get方法保证安全性
                        dayActiveEnergy = pv_item.today_discharge_energy
                        reverseActiveEnergy = pv_item.total_discharge_energy
                        
                        cursor.execute(
                            "INSERT INTO pv_data (device_sn, timestamp, activePower, reactivePower, powerFactor, dayActiveEnergy, reverseActiveEnergy, local_timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (device_sn, timestamp, activePower, reactivePower, powerFactor, dayActiveEnergy, reverseActiveEnergy, local_timestamp)
                        )
            
            # 记录储能数据到storage_data表
            if hasattr(net, 'storage') and hasattr(net, 'res_storage') and not net.res_storage.empty:
                for idx, storage_data in net.res_storage.iterrows():
                    if idx in net.storage.index:
                        storage_item = self.network_items.get("storage", {}).get(idx, {})
                        device_sn = storage_item.properties.get('sn', f"storage_{idx}")
                        activePower = storage_data.get('p_mw', 0.0) * 1000  # 转换为kW
                        reactivePower = storage_data.get('q_mvar', 0.0) * 1000  # 转换为kVar
                        soc = storage_item.soc_percent
                        
                        cursor.execute(
                            "INSERT INTO storage_data (device_sn, timestamp, activePower, reactivePower, soc, local_timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                            (device_sn, timestamp, activePower, reactivePower, soc, local_timestamp)
                        )
            
            # 记录负载数据到meter_data表（作为特殊的电表）
            if hasattr(net, 'res_load') and not net.res_load.empty:
                for idx, load_data in net.res_load.iterrows():
                    # 区分普通负载和充电桩
                    if idx >= 1000:
                        charger_item = self.network_items.get("charger", {}).get(idx, {})
                        device_sn = charger_item.properties.get('sn', f"charger_{idx}")
                        # 记录到charger_data表
                        activePower = load_data.get('p_mw', 0.0) * 1000  # 转换为kW
                        cursor.execute(
                            "INSERT INTO charger_data (device_sn, timestamp, activePower, local_timestamp) VALUES (?, ?, ?, ?)",
                            (device_sn, timestamp, activePower, local_timestamp)
                        )
                    else:
                        # 记录到meter_data表
                        activePower = load_data.get('p_mw', 0.0) * 1000  # 转换为kW
                        reactivePower = load_data.get('q_mvar', 0.0) * 1000  # 转换为kVar
                        cursor.execute(
                            "INSERT INTO load_data (device_id, timestamp, activePower, reactivePower, local_timestamp) VALUES (?, ?, ?, ?, ?)",
                            (idx, timestamp, activePower, reactivePower, local_timestamp)
                        )
            
            # 提交事务并关闭连接
            conn.commit()
            conn.close()
            
            logger.info(f"成功保存仿真数据到数据库，时间戳: {timestamp}")
            
        except Exception as e:
            logger.error(f"保存数据到数据库时出错: {str(e)}")


# 移除QThread相关代码，使用标准threading模块
    
    def load_network_data(self):
        """加载网络数据到设备树"""
        if not self.network_model:
            return
            
        self.device_tree.clear()
        
        # 缓存网络模型引用，减少重复访问
        net = self.network_model.net
        
        # 提前检查结果属性是否存在且非空，避免重复检查
        result_available = {
            'bus': hasattr(net, 'res_bus') and not net.res_bus.empty,
            'line': hasattr(net, 'res_line') and not net.res_line.empty,
            'trafo': hasattr(net, 'res_trafo') and not net.res_trafo.empty,
            'load': hasattr(net, 'res_load') and not net.res_load.empty,
            'gen': hasattr(net, 'res_gen') and not net.res_gen.empty,
            'sgen': hasattr(net, 'res_sgen') and not net.res_sgen.empty,
            'ext_grid': hasattr(net, 'res_ext_grid') and not net.res_ext_grid.empty,
            'storage': hasattr(net, 'res_storage') and not net.res_storage.empty,
            'switch': hasattr(net, 'res_switch') and not net.res_switch.empty
        }
        
        # 添加组件的通用函数，减少重复代码
        def add_components(component_type, display_name, icon_type=None):
            if not hasattr(net, component_type) or getattr(net, component_type).empty:
                return
                
            root = QTreeWidgetItem(self.device_tree, [display_name, "分类", "-"])
            component_data = getattr(net, component_type)
            
            for idx, item_data in component_data.iterrows():
                item_name = item_data.get('name', f'{display_name}_{idx}')
                
                # 处理特殊情况：负载包含充电桩
                if component_type == 'load' and idx >= 1000:
                    current_type = 'charger'
                    current_name = f'Charger {idx}: {item_data.get("name", f"Charger_{idx}")}'
                    current_icon = "充电桩"
                else:
                    current_type = component_type
                    current_name = f'{display_name[:2]} {idx}: {item_name}'
                    current_icon = icon_type or display_name
                
                # 确定状态
                status = "正常" if result_available.get(current_type) and idx in getattr(net, f'res_{current_type}').index else "未计算"
                
                tree_item = QTreeWidgetItem(root, [current_name, current_icon, status])
                tree_item.setData(0, Qt.UserRole, (current_type, idx))
        
        # 批量添加各类组件
        add_components('bus', '母线')
        add_components('line', '线路')
        add_components('trafo', '变压器')
        add_components('load', '负载')  # 包含充电桩
        add_components('gen', '发电机')
        add_components('sgen', '光伏')
        add_components('ext_grid', '外部电网')
        add_components('storage', '储能')
        add_components('switch', '开关')
        
        # 添加电表
        if hasattr(net, 'measurement') and not net.measurement.empty:
            meter_root = QTreeWidgetItem(self.device_tree, ["电表", "分类", "-"])
            for idx, meter in net.measurement.iterrows():
                meter_name = meter.get('name', f'Meter_{idx}')
                element_type = meter.get('element_type', '未知')
                element_idx = meter.get('element', idx)
                status = "正常" if meter.get('in_service', True) else "离线"
                meter_item = QTreeWidgetItem(meter_root, [f"Meter {idx}: {meter_name} ({element_type}_{element_idx})", "电表", status])
                meter_item.setData(0, Qt.UserRole, ('meter', idx))
        
        # 展开所有节点
        self.device_tree.expandAll()
        
        # 更新设备统计
        self.update_device_stats()
        
    def on_device_selected(self, item, column):
        """设备树中选择设备时的处理"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        component_type, component_idx = data
        self.selected_device_id = str(component_idx)
        self.selected_device_type = self.get_component_type_chinese(component_type)
        
        # 更新当前设备监控复选框状态
        device_key = f"{self.selected_device_type}_{self.selected_device_id}"
        self.current_device_monitor.setChecked(device_key in self.power_monitor.monitored_devices)
        
        # 隐藏所有设备类型的dockwidget
        self.sgen_dock.hide()
        self.load_dock.hide()
        self.storage_dock.hide()
        self.charger_dock.hide()
        self.switch_dock.hide()
        
        # 根据设备类型显示对应的dockwidget
        if component_type == 'sgen':
            # 显示光伏数据生成面板dockwidget
            self.sgen_dock.show()
        elif component_type == 'load':  # 普通负载
            self.load_dock.show()
        elif component_type == 'charger':  # 充电桩
            self.charger_dock.show()
        elif component_type == 'storage':
            self.storage_dock.show()
        elif component_type == 'switch':  # 开关
            self.switch_dock.show()
        
        # 显示组件详情
        self.show_component_details(component_type, component_idx)
        
        # 更新功率监控
        # self.power_monitor.update_monitored_devices_list()
        
    def show_component_details(self, component_type, component_idx):
        """显示组件详细信息"""
        if not self.network_model:
            return
            
        # 记录当前显示的组件信息，用于自动更新
        self.current_component_type = component_type
        self.current_component_idx = component_idx
        
        
        # 根据设备类型更新设备信息
        if component_type == 'sgen':
            self.data_control_manager.update_sgen_control_panel_info(component_type, component_idx)
        elif component_type == 'load':
            self.data_control_manager.update_load_control_panel_info(component_type, component_idx)
        elif component_type == 'charger':
            # 根据额定功率设置spinbox的范围
            self.data_control_manager.update_charger_control_panel_info(component_type, component_idx)
        elif component_type == 'storage':
            self.data_control_manager.update_storage_control_panel_info(component_type, component_idx)
        elif component_type == 'switch':
            self.data_control_manager.update_switch_control_panel_info(component_type, component_idx)
            
    # def show_meter_measurement_details(self, meter_idx):
    #     """显示电表设备的测量结果详情"""
    #     try:
    #         # 获取电表图形项
    #         meter_item = self.get_meter_item_by_type_and_id('meter', meter_idx)
    #         if not meter_item:
    #             return {"error": f"未找到电表设备: {meter_idx}"}
            
    #         # 获取电表属性
    #         properties = meter_item.properties
            
    #         # 获取测量参数
    #         element_type = properties.get('element_type', 'bus')
    #         element_idx = properties.get('element', 0)
    #         side = properties.get('side', None)
            
    #         # 构建返回字典
    #         result = {}
            
    #         # 快速检查网络模型是否可用
    #         if not self.network_model or not hasattr(self.network_model, 'net'):
    #             return {"error": "网络模型不可用"}
            
    #         net = self.network_model.net
            
    #         # 获取实时测量值 - 使用映射表避免重复的条件判断
    #         measurement_mapping = {
    #             'load': {'res_attr': 'res_load', 'param': 'p_mw'},
    #             'sgen': {'res_attr': 'res_sgen', 'param': 'p_mw'},
    #             'storage': {'res_attr': 'res_storage', 'param': 'p_mw', 'factor': -1},
    #             'bus': {'res_attr': 'res_bus', 'param': 'p_mw'},
    #             'line': {
    #                 'res_attr': 'res_line',
    #                 'params': {'from': 'p_from_mw', 'to': 'p_to_mw'},
    #                 'side': side
    #             },
    #             'trafo': {
    #                 'res_attr': 'res_trafo',
    #                 'params': {'hv': 'p_hv_mw', 'lv': 'p_lv_mw'},
    #                 'side': side
    #             },
    #             'ext_grid': {'res_attr': 'res_ext_grid', 'param': 'p_mw'}
    #         }
            
    #         if element_type in measurement_mapping:
    #             mapping = measurement_mapping[element_type]
    #             res_attr = mapping.get('res_attr')
                
    #             # 检查结果属性是否存在
    #             if hasattr(net, res_attr) and not getattr(net, res_attr).empty and element_idx in getattr(net, res_attr).index:
    #                 result_set = False
    #                 res_data = getattr(net, res_attr)
                    
    #                 # 处理带方向的组件（线路和变压器）
    #                 if 'params' in mapping and 'side' in mapping:
    #                     side_param = mapping.get('params', {}).get(mapping.get('side'))
    #                     if side_param:
    #                         measurement_value = res_data.at[element_idx, side_param]
    #                         result[side_param] = measurement_value
    #                         result_set = True
    #                 # 处理普通组件
    #                 elif 'param' in mapping:
    #                     param = mapping.get('param')
    #                     measurement_value = res_data.at[element_idx, param]
    #                     # 应用可选的转换因子
    #                     if 'factor' in mapping:
    #                         measurement_value *= mapping.get('factor')
    #                     result[param] = measurement_value
    #                     result_set = True
                    
    #                 # 如果成功获取测量值，添加其他有用信息
    #                 if result_set:
    #                     result['element_type'] = element_type
    #                     result['element_idx'] = element_idx
    #                     result['side'] = side
            
    #         return result if result else {"error": "无法获取测量值"}
    #     except Exception as e:
    #         return {"error": f"获取电表详情时出错: {str(e)}"}
                        
    def on_switch_close(self):
        """开关合闸操作"""
        if self.current_component_type == 'switch' and hasattr(self, 'current_component_idx'):
            try:
                # 更新network_items中的开关状态
                if 'switch' in self.network_items and self.current_component_idx in self.network_items['switch']:
                    switch_item = self.network_items['switch'][self.current_component_idx]
                    switch_item.properties['closed'] = True
                    
                    # 更新UI显示
                    if hasattr(self, 'switch_status_value'):
                        self.switch_status_value.setText("合闸")
                        self.switch_status_value.setStyleSheet("font-weight: bold; color: #4CAF50;")
                    
                    # 更新network_model中的开关状态会在自动计算前进行
                    logger.info(f"开关 {self.current_component_idx} 已合闸")
            except Exception as e:
                logger.error(f"开关合闸操作失败: {e}")
                
    def on_switch_open(self):
        """开关分闸操作"""
        if self.current_component_type == 'switch' and hasattr(self, 'current_component_idx'):
            try:
                # 更新network_items中的开关状态
                if 'switch' in self.network_items and self.current_component_idx in self.network_items['switch']:
                    switch_item = self.network_items['switch'][self.current_component_idx]
                    switch_item.properties['closed'] = False
                    
                    # 更新UI显示
                    if hasattr(self, 'switch_status_value'):
                        self.switch_status_value.setText("分闸")
                        self.switch_status_value.setStyleSheet("font-weight: bold; color: #F44336;")
                    
                    # 更新network_model中的开关状态会在自动计算前进行
                    logger.info(f"开关 {self.current_component_idx} 已分闸")
            except Exception as e:
                logger.error(f"开关分闸操作失败: {e}")
            
    def get_component_type_chinese(self, component_type):
        """获取组件类型的中文名称"""
        type_map = {
            'bus': '母线',
            'line': '线路', 
            'trafo': '变压器',
            'load': '负载',
            'charger': '充电桩',
            'gen': '发电机',
            'sgen': '光伏',
            'ext_grid': '外部电网',
            'storage': '储能',
            'meter': '电表'
        }
        return type_map.get(component_type, component_type)
            
    def filter_device_tree(self, text):
        """根据搜索文本过滤设备树"""
        def hide_items(item, text):
            """递归隐藏/显示项目"""
            match = text.lower() in item.text(0).lower()
            
            # 检查子项目
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                if hide_items(child, text):
                    child_match = True
            
            # 如果有匹配的子项目或自身匹配，则显示
            should_show = match or child_match or text == ""
            item.setHidden(not should_show)
            
            return should_show
        
        # 对根项目应用过滤
        for i in range(self.device_tree.topLevelItemCount()):
            root_item = self.device_tree.topLevelItem(i)
            hide_items(root_item, text)
    
    def clear_search(self):
        """清除搜索"""
        self.search_input.clear()
    
    def filter_by_category(self, category):
        """根据分类过滤设备"""
        category_map = {
            "全部设备": [],
            "母线": ["母线"],
            "线路": ["线路"],
            "变压器": ["变压器"],
            "发电设备": ["发电机", "光伏", "外部电网"],
            "负载设备": ["负载"],
            "储能设备": ["储能"],
            "测量设备": ["电表"]
        }
        
        show_categories = category_map.get(category, [])
        
        for i in range(self.device_tree.topLevelItemCount()):
            root_item = self.device_tree.topLevelItem(i)
            category_name = root_item.text(0)
            
            if category == "全部设备":
                root_item.setHidden(False)
            else:
                root_item.setHidden(category_name not in show_categories)
    
    def refresh_device_tree(self):
        """刷新设备树"""
        # 网络模型可能已变化，但不需要清除Modbus设备缓存，因为现在直接使用network_items
            
        self.load_network_data()
        self.search_input.clear()
        self.category_combo.setCurrentText("全部设备")
    
    def update_device_stats(self):
        """更新设备统计信息"""
        if not self.network_model:
            self.device_stats_label.setText("设备统计: 无网络模型")
            return
        
        stats = {
            "母线": len(self.network_model.net.bus),
            "线路": len(self.network_model.net.line),
            "变压器": len(self.network_model.net.trafo),
            "负载": len(self.network_model.net.load),
            "发电机": len(self.network_model.net.gen),
            "光伏": len(self.network_model.net.sgen),
            "外部电网": len(self.network_model.net.ext_grid),
            "储能": len(self.network_model.net.storage),
            "电表":len(self.network_model.net.measurement)
        }
        
        total = sum(stats.values())
        stats_text = f"设备统计: 总计 {total} 个设备 | "
        stats_text += " | ".join([f"{k}: {v}" for k, v in stats.items() if v > 0])
        
        self.device_stats_label.setText(stats_text)
    
    
    def closeEvent(self, event):
        """窗口关闭事件 - 增强内存清理"""
        try:
            # 停止数据记录线程
            if hasattr(self, 'is_recording') and self.is_recording:
                self.stop_record_data()
                
            # 停止回测
            if hasattr(self, 'is_backtesting') and self.is_backtesting:
                self.stop_backtest()
                
            # 下电所有设备
            self.power_off_all_devices()
            
            # 停止所有定时器
            self.auto_calc_timer.stop()
            # 回测定时器已移除，不再需要停止
            
            # 关闭所有Modbus服务器（额外保障）
            if hasattr(self, 'modbus_manager'):
                self.modbus_manager.stop_all_modbus_servers()
            
            # 将所有开关设置为合闸状态
            if 'switch' in self.network_items:
                for switch_idx, switch_item in self.network_items['switch'].items():
                    try:
                        switch_item.properties['closed'] = True
                        logger.info(f"开关 {switch_idx} 已设置为合闸状态")
                    except Exception as e:
                        logger.error(f"设置开关 {switch_idx} 状态失败: {e}")
            
            # 清理功率监控
            if hasattr(self, 'power_monitor'):
                self.power_monitor.cleanup()
            
            # 清理缓存
            self._clear_all_caches()
            
            # 断开信号连接
            self._disconnect_all_signals()
            
            self.parent_window.statusBar().showMessage("已退出仿真模式")
            # 强制垃圾回收
            import gc
            gc.collect()
            
        except Exception as e:
            logger.error(f"关闭仿真窗口时发生错误: {e}")
        finally:
            event.accept()
    def clear_all_members(self):
        """清空类中所有成员变量"""
        # 保留基本属性，清空其他所有
        keep_attrs = ['__class__', '__dict__', '__weakref__']
        
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attrs:
                delattr(self, attr)
    def _clear_all_caches(self):
        """清理所有缓存"""
        # 清理可能存在的缓存
        cache_attrs = [
            '_storage_cache', 'generated_devices',
            'current_component_type', 'current_component_idx'
        ]
        
        for attr in cache_attrs:
            if hasattr(self, attr):
                cache = getattr(self, attr)
                if isinstance(cache, dict):
                    cache.clear()
                elif isinstance(cache, set):
                    cache.clear()
                elif isinstance(cache, list):
                    cache.clear()
                else:
                    setattr(self, attr, None)
    
    def _disconnect_all_signals(self):
        """断开所有信号连接"""
        try:
            # 断开定时器信号
            self.auto_calc_timer.timeout.disconnect()
        except Exception as e:
            logger.error(f"断开自动潮流计算定时器信号时发生错误: {e}")
            pass
    
    def update_auto_calc_timer(self):
        """更新自动潮流计算定时器间隔"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            return
        
        if self.is_auto_calculating:
            # 重新启动定时器以应用新的间隔
            self.auto_calc_timer.stop()
            interval = self.calc_interval_spinbox.value() * 1000  # 转换为毫秒
            self.auto_calc_timer.start(interval)
            self.statusBar().showMessage(f"自动潮流计算间隔已更新为 {self.calc_interval_spinbox.value()} 秒")

    def toggle_calculation(self):
        """切换计算状态"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            self.start_calc_btn.setChecked(True)  # 恢复按钮状态
            return
            
        if self.start_calc_btn.isChecked():
            # 开始计算
            interval = self.calc_interval_spinbox.value() * 1000  # 转换为毫秒
            self.auto_calc_timer.start(interval)
            self.is_auto_calculating = True
            self.start_calc_btn.setText("停止仿真")
            self.calc_status_label.setText("仿真状态: 运行中")
            self.statusBar().showMessage("仿真已启动")
            # 记录日志：自动计算任务启动
            logger.info(f"自动计算任务启动，计算间隔: {self.calc_interval_spinbox.value()}秒")
        else:
            # 停止计算
            self.auto_calc_timer.stop()
            self.is_auto_calculating = False
            self.start_calc_btn.setText("开始仿真")
            self.calc_status_label.setText("仿真状态: 已停止")
            self.statusBar().showMessage("仿真已停止")
            # 记录日志：自动计算任务停止
            logger.info("自动计算任务停止")

    def power_on_all_devices(self):
        """开启所有设备的通信 - 启动所有Modbus服务器"""
        try:
            if not self.network_model:
                QMessageBox.warning(self, "警告", "没有可用的网络模型")
                return
            
            # # 首先验证IP和端口的唯一性 诊断时已经验证
            # is_valid, error_msg = self.parent_window.topology_manager.validate_ip_port_uniqueness(self.scene, self)
            # if not is_valid:
            #     return
                
            # 启动所有Modbus服务器
            self.modbus_manager.start_all_modbus_servers()
            
            # 获取运行状态
            device_count = self.modbus_manager.get_device_count()
            running_services = self.modbus_manager.get_service_count()
            
            QMessageBox.information(
                self, 
                "通信开启成功", 
                f"已成功启动 {running_services} 个设备的Modbus服务器\n"
                f"总设备数: {device_count['total']}"
            )
            
            self.statusBar().showMessage(f"已开启 {running_services} 个设备的通信")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"通信开启失败: {str(e)}")
            self.statusBar().showMessage("通信开启操作失败")
    
    def power_off_all_devices(self):
        """关闭所有设备的通信 - 停止所有Modbus服务器"""
        try:
            if not self.network_model:
                QMessageBox.warning(self, "警告", "没有可用的网络模型")
                return
                
            # 获取当前运行状态
            device_count = self.modbus_manager.get_device_count()
            running_count = device_count['running_services']
            
            # 停止所有Modbus服务器
            self.modbus_manager.stop_all_modbus_servers()
            
            QMessageBox.information(
                self, 
                "通信关闭成功", 
                f"已成功停止 {running_count} 个设备的Modbus服务器"
            )
            
            self.statusBar().showMessage(f"已关闭 {running_count} 个设备的通信")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"通信关闭失败: {str(e)}")
            self.statusBar().showMessage("通信关闭操作失败")
    
    def check_and_reset_daily_data(self):
        """检查并执行每日数据重置"""
        try:
            from datetime import datetime
            current_date = datetime.now().date()
            
            # 检查是否需要每日重置
            if hasattr(self, 'last_reset_date') and current_date != self.last_reset_date:
                self.reset_daily_pv_energy()
                self.reset_daily_storage_energy()
                self.last_reset_date = current_date
                logger.info(f"已重置所有设备的每日数据 - {current_date}")
            elif not hasattr(self, 'last_reset_date'):
                self.last_reset_date = current_date
        except Exception as e:
            logger.error(f"每日数据重置检查失败: {str(e)}")


    def _update_energy_stats_batch(self):
        """批量更新能量统计信息 - 优化版本"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # 计算时间间隔（使用定时器中的实际值）
            timer_interval_ms = self.auto_calc_timer.interval()
            time_interval_hours = timer_interval_ms / (1000.0 * 3600.0)  # 毫秒转小时
            
            # 批量更新光伏能量统计
            if self.network_items['static_generator'] and hasattr(self.network_model, 'net'):
                valid_pv_indices = [idx for idx in self.network_items['static_generator'].keys() 
                                  if idx in self.network_model.net.sgen.index]
                
                for device_idx in valid_pv_indices:
                    try:
                        pv_item = self.network_items['static_generator'][device_idx]
                        current_power_mw = abs(self.network_model.net.sgen.at[device_idx, 'p_mw'])
                        
                        # 计算本次产生的能量（kWh）
                        energy_generated_kwh = current_power_mw * time_interval_hours * 1000
                        
                        # 更新今日发电量和总发电量
                        pv_item.today_discharge_energy += energy_generated_kwh
                        pv_item.total_discharge_energy += energy_generated_kwh
                        
                    except Exception as e:
                        logger.error(f"批量更新光伏设备 {device_idx} 能量统计时出错: {e}")
            
            # 批量更新储能能量统计
            if self.network_items['storage'] and hasattr(self.network_model, 'net'):
                valid_storage_indices = [idx for idx in self.network_items['storage'].keys() 
                                       if idx in self.network_model.net.storage.index]
                
                for device_idx in valid_storage_indices:
                    try:
                        storage_item = self.network_items['storage'][device_idx]
                        current_power_mw = -self.network_model.net.storage.at[device_idx, 'p_mw']
                        
                        # 调用StorageItem的实时数据更新方法
                        storage_item.update_storage_energy_and_state(current_power_mw, time_interval_hours)
                        
                    except Exception as e:
                        logger.error(f"批量更新储能设备 {device_idx} 能量统计时出错: {e}")
                        
        except Exception as e:
            logger.error(f"批量更新能量统计失败: {str(e)}")
            
    def reset_daily_storage_energy(self):
        """重置储能设备的每日能量统计"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # 获取当前场景中的所有储能设备
            storage_items = []
            for item in self.canvas.scene.items():
                if hasattr(item, 'component_type') and item.component_type == 'storage':
                    storage_items.append(item)
            
            # 遍历所有储能设备，重置每日数据
            for storage_item in storage_items:
                storage_item.reset_daily_energy()
                
        except Exception as e:
            logger.error(f"重置储能设备每日能量统计失败: {str(e)}")



    def _update_para_from_modbus_batch(self):
        """
        从Modbus寄存器读取数据并更新设备参数
        
        支持储能、充电桩和光伏系统的完整Modbus数据更新：
        - 储能设备：开关机状态、功率设定值、SOC控制
        - 充电桩：功率设定值、充电状态
        - 光伏系统：功率设定值、启停控制
        """
        try:
            if not hasattr(self, 'modbus_manager') or not self.modbus_manager:
                return
                
            if not self.network_model or not hasattr(self.network_model, 'net'):
                return
                
            # 获取所有正在运行的Modbus设备
            running_devices = list(self.modbus_manager.running_services)
            if not running_devices:
                return
            
            # 批量收集各类型设备更新数据
            storage_updates = []
            charger_updates = []
            sgen_updates = []
            
            for device_key in running_devices:
                device_type, device_idx_str = device_key.rsplit('_', 1)
                device_idx = int(device_idx_str)
                
                # 获取设备的Modbus上下文
                slave_context = self.modbus_manager.modbus_contexts.get(device_key)
                if not slave_context:
                    continue
                
                try:
                    if device_type == 'storage':
                        # 储能设备数据收集
                        update_data = self.modbus_manager.collect_storage_modbus_data(device_idx, slave_context)
                        logger.info(f"储能设备 {device_idx} 数据更新: {update_data}")
                        if update_data:
                            storage_updates.append((device_idx, update_data))
                    
                    elif device_type == 'charger':
                        # 充电桩设备数据收集（负荷类型中的充电桩）
                        update_data = self.modbus_manager.collect_charger_modbus_data(device_idx, slave_context)
                        if update_data:
                            charger_updates.append((device_idx, update_data))
                    
                    elif device_type == 'static_generator':
                        # 光伏系统数据收集
                        update_data = self.modbus_manager.collect_sgen_modbus_data(device_idx, slave_context)
                        if update_data:
                            sgen_updates.append((device_idx, update_data))
                            
                except Exception as e:
                    logger.error(f"收集设备 {device_key} 参数失败: {e}")
            
            # 批量应用各类型设备更新
            if storage_updates:
                self._apply_storage_updates_batch(storage_updates)
            
            if charger_updates:
                self._apply_charger_updates_batch(charger_updates)
                
            if sgen_updates:
                self._apply_sgen_updates_batch(sgen_updates)
                    
        except Exception as e:
            logger.error(f"Modbus参数批量更新失败: {str(e)}")



    def _apply_storage_updates_batch(self, storage_updates):
        """批量应用储能设备更新"""
        try:
            # 批量应用更新
            for device_idx, update_data in storage_updates:
                storage_item = self.network_items['storage'].get(device_idx)
                if not storage_item:
                    continue
                    
                power_on = update_data['power_on'] 
                power_setpoint = update_data['power_setpoint']
                # 初始化final_power变量，确保在所有代码路径中都有定义
                final_power = 0.0
                
                # 更新开关机状态，根据实际功率判断充放电状态
                if power_on is not None:
                    if power_on:
                        storage_item.is_power_on = True
                        final_power = power_setpoint if power_setpoint is not None else 0.0
                        
                        # 检查SOC限制，SOC大于等于100%时，禁止充电（如果final_power为正）
                        if hasattr(storage_item, 'soc_percent'):
                            # SOC大于等于100%时，禁止充电（如果final_power为正）
                            if storage_item.soc_percent >= 1.0 and final_power > 0:
                                final_power = 0.0
                            # SOC小于等于0%时，禁止放电（如果final_power为负）
                            elif storage_item.soc_percent <= 0.0 and final_power < 0:
                                final_power = 0.0
                    else:
                        storage_item.is_power_on = False
                        final_power = 0.0
                    
                # 更新功率设定值到网络模型
                try:
                    # 只有在非手动模式下才执行更新操作
                    if hasattr(storage_item, 'is_manual_control') and not storage_item.is_manual_control:
                        # 检查功率值是否发生变化
                        current_power = -self.network_model.net.storage.at[device_idx, 'p_mw']
                        if final_power != current_power:
                            self.network_model.net.storage.at[device_idx, 'p_mw'] = -final_power
                            # 发射信号通知功率变化
                            self.storage_power_changed.emit(device_idx, final_power)
                
                except (KeyError, IndexError):
                    pass
                # 更新并网离网状态
                grid_connected = update_data['grid_connected']
                if grid_connected == 0:
                    storage_item.grid_connected = True
                elif grid_connected == 1:
                    storage_item.grid_connected = False
                        
        except Exception as e:
            logger.error(f"批量应用储能更新失败: {e}")
            
    def _apply_charger_updates_batch(self, charger_updates):
        """批量应用充电桩设备功率限制更新"""
        try:
            # 批量应用更新
            for device_idx, update_data in charger_updates:
                charger_item = self.network_items['charger'].get(device_idx)
                if not charger_item:
                    continue
                
                power_limit = update_data['power_limit']

                # 更新充电桩功率限制
                if power_limit is not None:
                    try:
                        charger_item.power_limit = power_limit
                        # 检查并更新功率限制标签
                        if hasattr(self, "charger_power_limit_label"):
                            try:
                                # 确保标签已经被添加到UI中
                                if self.charger_power_limit_label.parentWidget():
                                    self.charger_power_limit_label.setText(
                                        f"{charger_item.power_limit * 1000:.1f} kW"
                                    )
                            except Exception as label_error:
                                logger.error(f"更新功率限制标签时出错: {label_error}")

                    except Exception as e:
                        logger.error(f"更新充电桩{charger_item.component_index}功率限制时出错: {e}")
                        
        except Exception as e:
            logger.error(f"批量应用充电桩功率限制更新失败: {e}")
            
    def _apply_sgen_updates_batch(self, sgen_updates):
        """批量应用光伏系统更新"""
        try:
            # 批量应用更新
            for device_idx, update_data in sgen_updates:
                sgen_item = self.network_items['static_generator'].get(device_idx)
                if not sgen_item:
                    continue
                
                power_on = update_data['power_on']
                power_limit_mw = update_data['power_limit_mw']
                power_percent_limit = update_data['power_percent_limit']
                rated_power = sgen_item.properties.get('sn_mva', 0.0)  # 从属性中获取额定功率，默认0.0
                # 获取光伏设备的实际功率
                try:
                    active_power_mw = self.network_model.net.sgen.at[device_idx, 'p_mw']
                except (KeyError, IndexError):
                    active_power_mw = 0.0
                
                # 计算最终功率值
                final_power = 0.0
                
                if power_on:
                    # 根据功率限制模式计算最终功率
                    if power_limit_mw is not None and power_percent_limit is not None:
                        # 同时存在绝对功率限制和百分比功率限制，取较小值
                        final_power = min(active_power_mw,power_limit_mw)
                        percent_limit_mw = rated_power * (power_percent_limit / 100.0)
                        final_power = min(final_power, percent_limit_mw)
                    else:
                        # 无限制，使用实际功率
                        final_power = active_power_mw
                
                # 更新光伏功率到网络模型
                try:
                    self.network_model.net.sgen.at[device_idx, 'p_mw'] = final_power
                except (KeyError, IndexError):
                    pass
                    
        except Exception as e:
            logger.error(f"批量应用光伏系统更新失败: {e}")

    def _update_generated_data_batch(self, generated_devices, network_model, data_generator_manager):
        """
        批量更新生成的设备数据 - 优化版本
        
        Args:
            generated_devices (list): 生成的设备列表，格式为['type_idx', ...]
            network_model: 网络模型对象
            data_generator_manager: 数据生成器管理器
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            if not network_model or not hasattr(network_model, 'net'):
                return False
                
            # 批量收集需要更新的设备
            load_updates = {}
            sgen_updates = {}
            
            for device in generated_devices:
                device_type, device_idx_str = device.split('_', 1)
                device_idx = int(device_idx_str)
                
                if device_type == 'load' and device_idx in network_model.net.load.index:
                    load_data = data_generator_manager.generate_device_data('load', device_idx, network_model)
                    if device_idx in load_data:
                        load_updates[device_idx] = load_data[device_idx]
                        
                elif device_type == 'sgen' and device_idx in network_model.net.sgen.index:
                    sgen_data = data_generator_manager.generate_device_data('sgen', device_idx, network_model)
                    if device_idx in sgen_data:
                        sgen_updates[device_idx] = sgen_data[device_idx]
            
            # 批量更新负载数据
            if load_updates:
                for device_idx, values in load_updates.items():
                    network_model.net.load.at[device_idx, 'p_mw'] = values['p_mw']
                    network_model.net.load.at[device_idx, 'q_mvar'] = values['q_mvar']
            
            # 批量更新光伏数据
            if sgen_updates:
                for device_idx, values in sgen_updates.items():
                    network_model.net.sgen.at[device_idx, 'p_mw'] = values['p_mw']
                    network_model.net.sgen.at[device_idx, 'q_mvar'] = values['q_mvar']
            
            return True
            
        except Exception as e:
            logger.error(f"批量更新设备数据失败: {str(e)}")
            return False

    def get_meter_item_by_type_and_id(self, device_type, device_id):
        """根据设备类型和ID获取对应的电表项
        
        Args:
            device_type (str): 设备类型，如 'meter'
            device_id (int): 设备ID
            
        Returns:
            object: 对应的电表图形项对象，如果未找到返回None
        """
        try:
            if device_type != 'meter':
                return None
                
            return self.network_items['meter'].get(device_id)
            
        except Exception as e:
            logger.error(f"获取电表项失败: {str(e)}")
            return None
    
    def update_device_tree_status(self):
        """更新设备树状态"""
        try:
            if not hasattr(self.network_model.net, 'res_bus') or self.network_model.net.res_bus.empty:
                return
                
            # 预加载所有结果索引，避免重复访问
            if not hasattr(self, '_device_status_cache'):
                self._device_status_cache = {}
            
            # 批量获取所有结果索引
            net = self.network_model.net
            result_indices = {
                'bus': set(net.res_bus.index) if net.res_bus is not None else set(),
                'line': set(net.res_line.index) if net.res_line is not None else set(),
                'trafo': set(net.res_trafo.index) if net.res_trafo is not None else set(),
                'load': set(net.res_load.index) if net.res_load is not None else set(),
                'charger': set(net.res_load.index) if net.res_load is not None else set(),
                'gen': set(net.res_gen.index) if net.res_gen is not None else set(),
                'sgen': set(net.res_sgen.index) if net.res_sgen is not None else set(),
                'ext_grid': set(net.res_ext_grid.index) if net.res_ext_grid is not None else set(),
                'storage': set(net.res_storage.index) if net.res_storage is not None else set(),
                'switch': set(net.res_switch.index) if net.res_switch is not None else set()
            }
            
            # 批量更新所有项目
            root = self.device_tree.invisibleRootItem()
            
            def update_item_status_optimized(item):
                """优化后的状态更新函数"""
                if not item:
                    return
                    
                data = item.data(0, Qt.UserRole)
                if data:
                    device_type, device_id = data
                    
                    # 处理电表类型
                    if device_type == 'meter':
                        meter_item = self.get_meter_item_by_type_and_id(device_type, device_id)
                        device_type = meter_item.properties['element_type']
                        device_id = meter_item.properties['element']

                    # 快速检查其他设备状态
                    if device_type in result_indices and device_id in result_indices[device_type]:
                        item.setText(2, "正常")
                        item.setForeground(2, QColor("green"))
                    else:
                        item.setText(2, "异常")
                        item.setForeground(2, QColor("red"))
                
                # 批量递归更新子项
                child_count = item.childCount()
                for i in range(child_count):
                    update_item_status_optimized(item.child(i))
            
            # 批量更新所有根项
            root_count = root.childCount()
            for i in range(root_count):
                update_item_status_optimized(root.child(i))
                
        except Exception as e:
            logger.error(f"更新设备树状态失败: {str(e)}")

    def reset_daily_pv_energy(self):
        """重置所有光伏设备的日发电量"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # 获取当前场景中的所有光伏设备
            pv_items = []
            for item in self.canvas.scene.items():
                if hasattr(item, 'component_type') and item.component_type == 'static_generator':
                    pv_items.append(item)
            
            # 重置每个光伏设备的今日发电量
            for pv_item in pv_items:
                pv_item.today_discharge_energy = 0.0
                
            logger.info("已重置所有光伏设备的日发电量")
            
        except Exception as e:
            logger.error(f"重置光伏日发电量失败: {str(e)}")

    def _sync_switch_states(self, network_items, net):
        """
        将network_items中的开关状态同步到network_model中
        
        参数:
            network_items: 包含所有网络项的字典
            net: pandapower网络模型
        """
        if 'switch' in network_items and hasattr(net, 'switch'):
            for switch_idx, switch_item in network_items['switch'].items():
                if switch_idx in net.switch.index:
                    try:
                        # 获取switch_item中的closed状态并更新到network_model中
                        closed_state = switch_item.properties.get('closed', True)
                        net.switch.at[switch_idx, 'closed'] = closed_state
                        logger.debug(f"更新开关 {switch_idx} 状态为: {'闭合' if closed_state else '断开'}")
                    except Exception as e:
                        logger.error(f"更新开关 {switch_idx} 状态失败: {e}")

    def auto_power_flow_calculation(self):
        """自动潮流计算主方法"""
        try:
            # 快速检查网络模型可用性
            if not self.network_model or not hasattr(self.network_model, 'net'):
                return
                
            # 性能监控：跳过计算如果上次计算未完成
            if hasattr(self, '_is_calculating') and self._is_calculating:
                return
            self._is_calculating = True
            # 缓存网络模型引用，减少重复访问
            network_model = self.network_model
            net = network_model.net
                
            # 记录日志：计算周期开始
            logger.info("开始新一轮潮流计算")
                
            # 检查每日重置
            self.check_and_reset_daily_data()
                
            # 使用批处理更新生成的数据，但在回测期间禁止数据自动生成
            if self.generated_devices and not hasattr(self, 'is_backtesting') or not self.is_backtesting:
                logger.info(f"更新生成数据，设备数量: {len(self.generated_devices)}")
                self._update_generated_data_batch(self.generated_devices, network_model, self.data_generator_manager)
            elif hasattr(self, 'is_backtesting') and self.is_backtesting:
                logger.info("回测期间，禁止数据自动生成")
                
            # 在回测期间，先执行回测步骤以确保时序一致性
            if hasattr(self, 'is_backtesting') and self.is_backtesting:
                logger.info("执行回测步骤")
                self.run_backtest_step()
                
            # 批量更新Modbus参数
            logger.info("批量更新Modbus参数")
            self._update_para_from_modbus_batch()
            
            # 更新开关状态：将network_items中的开关状态同步到network_model中
            logger.info("更新开关状态")
            self._sync_switch_states(self.network_items, net)
            
            # 运行潮流计算
            try:
                pp.runpp(net)
                self.statusBar().showMessage("潮流计算成功")
                logger.info("潮流计算成功完成")
                
                # 批量更新能量统计
                self._update_energy_stats_batch()
                logger.info("能量统计更新完成")
                
                # 智能更新策略：仅在数据变化时更新UI
                if not hasattr(self, '_ui_update_counter'):
                    self._ui_update_counter = 0
                self._ui_update_counter += 1
                
                # 每3次计算更新一次设备树（约6秒一次）
                if self._ui_update_counter % 3 == 0:
                    self.update_device_tree_status()
                    logger.info("设备树状态更新完成")
                
                # 每2次计算更新一次功率曲线（约4秒一次）
                if self._ui_update_counter % 1 == 0:
                    self.power_monitor.update_power_curve()
                    logger.info("功率曲线更新完成")
                
                self.data_control_manager.show_realtime_info()
                logger.info("实时数据更新完成")
                
                # 批量更新Modbus数据
                self.modbus_manager.update_all_modbus_data()
                logger.info("Modbus数据更新完成")
                    
            except Exception as e:
                self.statusBar().showMessage(f"潮流计算失败: {str(e)}")
                logger.error(f"潮流计算失败: {str(e)}")
                return  # 潮流计算失败，跳过后续数据更新操作
                
        except Exception as e:
            error_msg = f"自动潮流计算错误: {str(e)}"
            logger.error(error_msg)
            self.statusBar().showMessage("自动潮流计算发生错误")
            logger.critical(error_msg)
        finally:
            # 重置计算状态标志
            if hasattr(self, '_is_calculating'):
                self._is_calculating = False
                logger.info("计算周期结束")
    
