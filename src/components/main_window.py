#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主窗口组件
"""

from PySide6.QtWidgets import QMainWindow, QDockWidget, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from components.canvas import NetworkCanvas
from components.component_palette import ComponentPalette
from components.properties_panel import PropertiesPanel
from utils.topology_utils import TopologyManager
from config import (
    # 功能标志
    FEATURE_SIMULATION, FEATURE_MODBUS, FEATURE_REPORT, FEATURE_EXPORT,
    # 调试模式标志
    DEBUG_MODE, VERBOSE_LOGGING,
    # 辅助函数和装饰器
    is_feature_enabled, conditional_compile, import_if_enabled
)
# import pandapower as pp
if FEATURE_SIMULATION:
    import pandapower as pp
    from models.network_model import NetworkModel
    from components.globals import network_model 
# 从globals.py导入全局变量

class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.network_is_valid = False  # 网络状态标志位 
        self.topology_manager = TopologyManager()
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("PandaPower 仿真工具")
        self.setMinimumSize(1000, 800)

        # 创建中央画布
        self.canvas = NetworkCanvas(self)
        self.setCentralWidget(self.canvas)
        # 确保画布始终接收键盘事件
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setFocus()  # 设置初始焦点到画布

        # 创建组件面板
        self.create_component_palette()
        
        # 创建属性面板
        self.create_properties_panel()

        # 移除工具栏，功能由菜单栏完全覆盖

        # 创建菜单栏
        self.create_menu()

        # 状态栏
        self.statusBar().showMessage("就绪")

    def create_component_palette(self):
        """创建组件面板"""
        # 创建组件面板
        self.component_dock = QDockWidget("电网组件", self)
        self.component_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 组件面板内容
        self.component_palette = ComponentPalette(self)
        self.component_dock.setWidget(self.component_palette)
        
        # 添加到主窗口
        self.addDockWidget(Qt.LeftDockWidgetArea, self.component_dock)
        
    def create_properties_panel(self):
        """创建属性面板"""
        # 创建属性面板停靠窗口
        self.properties_dock = QDockWidget("组件属性", self)
        self.properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 设置停靠窗口的最小宽度
        self.properties_dock.setMinimumWidth(300)
        
        # 属性面板内容
        self.properties_panel = PropertiesPanel(self)
        self.properties_dock.setWidget(self.properties_panel)
        
        # 添加到主窗口右侧
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)
        
        # 连接画布选择事件到属性面板更新
        self.canvas.selection_changed.connect(self.properties_panel.update_properties)
        
        # 连接属性面板的属性变化信号
        self.properties_panel.property_changed.connect(self.on_property_changed)


    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_topology)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_topology)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_topology)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = self.menuBar().addMenu("编辑")
        edit_menu.addAction("撤销")
        edit_menu.addAction("重做")
        edit_menu.addSeparator()
        
        # 断开连接动作
        disconnect_action = QAction("断开连接", self)
        disconnect_action.setShortcut("Ctrl+D")
        disconnect_action.triggered.connect(self.disconnect_selected)
        edit_menu.addAction(disconnect_action)
        
        # 删除动作 - 让画布直接处理DEL键事件
        delete_action = QAction("删除所选", self)
        # 不设置快捷键，让画布直接处理DEL键
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        edit_menu.addAction("全选")
        
        # 视图菜单
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.component_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())
        view_menu.addSeparator()
        
        # 缩放操作
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        fit_view_action = QAction("适应视图", self)
        fit_view_action.setShortcut("Ctrl+0")
        fit_view_action.triggered.connect(self.fit_view)
        view_menu.addAction(fit_view_action)
        
        view_menu.addSeparator()
        if FEATURE_SIMULATION:
            # 仿真菜单
            sim_menu = self.menuBar().addMenu("仿真")
            
            # 仿真模式菜单项
            diagnostic_action = QAction("诊断", self)
            diagnostic_action.setShortcut("F6")
            diagnostic_action.triggered.connect(self.diagnostic_network)
            sim_menu.addAction(diagnostic_action)

            simulation_mode_action = QAction("仿真模式", self)
            simulation_mode_action.setShortcut("F5")
            simulation_mode_action.triggered.connect(self.enter_simulation_mode)
            sim_menu.addAction(simulation_mode_action)
            
            sim_menu.addSeparator()
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def disconnect_selected(self):
        """断开选中设备的连接"""
        self.canvas.disconnect_all_from_selected()
        self.statusBar().showMessage("已断开选中设备的连接")
    
    def delete_selected(self):
        """删除选中的项目"""
        self.canvas.delete_selected_items()
        self.statusBar().showMessage("已删除选中项目")
    
    def zoom_in(self):
        """放大视图"""
        self.canvas.scale(1.15, 1.15)
        self.statusBar().showMessage("视图已放大")
    
    def zoom_out(self):
        """缩小视图"""
        self.canvas.scale(1.0 / 1.15, 1.0 / 1.15)
        self.statusBar().showMessage("视图已缩小")
    
    def fit_view(self):
        """适应视图"""
        self.canvas.fit_in_view()
        self.statusBar().showMessage("视图已适应画布内容")
    
    def on_property_changed(self, component_type, prop_name, new_value):
        """处理组件属性变化事件"""
        try:
            # 获取当前选中的组件
            current_item = self.properties_panel.current_item
            if not current_item:
                return
            
            # 如果是名称属性变化，需要更新网络模型中的名称
            if prop_name == 'name':
                # 强制刷新画布显示
                self.canvas.scene.update()
                
            print(f"属性更新: {component_type}.{prop_name} = {new_value}")
            self.network_is_valid = False
            print("网络状态已标记为无效")
            
        except Exception as e:
            print(f"处理属性变化时出错: {e}")
    
    # 删除快速潮流计算方法（潮流计算功能已移除）
    @conditional_compile(FEATURE_SIMULATION)
    def enter_simulation_mode(self):
        """进入仿真模式"""
        try:
            
            # 首先验证IP和端口的唯一性
            is_valid, error_msg = self.topology_manager.validate_ip_port_uniqueness(self.canvas.scene, self)
            if not is_valid:
                return
            
            # 然后进行网络诊断
            if not self.network_is_valid:
                QMessageBox.warning(self, "网络诊断", "网络诊断未通过，请先进行诊断。")
                return
            
            # 如果诊断通过，创建并显示仿真界面
            from components.simulation_window import SimulationWindow
            self.simulation_window = SimulationWindow(self.canvas, self)
            self.simulation_window.show()
            
            self.statusBar().showMessage("已进入仿真模式")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"进入仿真模式时发生错误：{str(e)}")
    
    @conditional_compile(FEATURE_SIMULATION)
    def diagnostic_network(self):
        try:
            global network_model
            network_model = NetworkModel()
            if not network_model.create_from_network_items(self.canvas):
                QMessageBox.warning(self, "网络诊断", "创建网络模型失败，请检查电网组件。")
                return
            is_valid, error_msg = self.topology_manager.validate_ip_port_uniqueness(self.canvas.scene, self)
            if not is_valid:
                QMessageBox.warning(self, "网络诊断", f"IP和端口不唯一：{error_msg}")
                return
            validation_results = self.validate_network()
            if not validation_results:
                return
        except Exception as e:
            print(f"网络诊断时发生错误：{e}")
            QMessageBox.critical(self, "错误", f"网络诊断时发生错误：{str(e)}")
        
    @conditional_compile(FEATURE_SIMULATION)    
    def validate_network(self):
        """使用pandapower内置函数验证网络拓扑和参数"""
        try:
            # 检查是否有网络模型
            if not network_model:
                QMessageBox.warning(self, "网络诊断", "当前没有创建网络模型，请先添加电网组件。")
                return False
            
            # network_model已作为全局变量导入
            
            # 检查是否有足够的组件
            if network_model.net.bus.empty:
                QMessageBox.warning(self, "网络诊断", "网络中没有母线组件，无法进行仿真。")
                return False
            
            # 检查是否有电源
            has_power_source = (
                not network_model.net.ext_grid.empty or 
                not network_model.net.gen.empty or 
                not network_model.net.sgen.empty
            )
            
            if not has_power_source:
                QMessageBox.warning(self, "网络诊断", "网络中没有电源（外部电网、发电机或光伏）。")
                return False
            
            # 使用pandapower内置诊断函数
            diagnostic_results = []
            
            try:
                # 运行诊断检查
                diag_report = pp.diagnostic(network_model.net)
                
                # 解析诊断报告
                if diag_report:
                    diagnostic_results.extend(diag_report)
                    
            except ImportError:
                # 如果pandapower诊断模块不可用，使用自定义诊断
                diagnostic_results.append("警告：pandapower诊断模块不可用，使用基础诊断")
                
                # 检查孤立母线
                connected_buses = set()
                if not network_model.net.line.empty:
                    connected_buses.update(network_model.net.line['from_bus'])
                    connected_buses.update(network_model.net.line['to_bus'])
                if not network_model.net.trafo.empty:
                    connected_buses.update(network_model.net.trafo['hv_bus'])
                    connected_buses.update(network_model.net.trafo['lv_bus'])
                
                isolated_buses = set(network_model.net.bus.index) - connected_buses
                if isolated_buses and len(isolated_buses) > 1:
                    diagnostic_results.append(f"发现 {len(isolated_buses)} 个孤立母线: {list(isolated_buses)}")
                
                # 检查负载和发电机是否连接到有效母线
                invalid_connections = []
                for component_type in ['load', 'gen', 'sgen', 'ext_grid', 'storage']:
                    if hasattr(network_model.net, component_type):
                        component_table = getattr(network_model.net, component_type)
                        if not component_table.empty:
                            invalid_buses = set(component_table['bus']) - set(network_model.net.bus.index)
                            if invalid_buses:
                                invalid_connections.append(f"{component_type}: {list(invalid_buses)}")
                
                if invalid_connections:
                    diagnostic_results.append(f"发现无效的母线连接: {', '.join(invalid_connections)}")
            
            # 检查电网连通性
            try:
                import pandapower.topology as topology
                
                # 检查网络是否连通
                unsupplied_buses = topology.unsupplied_buses(network_model.net)
                if unsupplied_buses:
                    diagnostic_results.append(f"发现未供电母线: {list(unsupplied_buses)}")
                
                # 检查是否存在环网
                if not network_model.net.bus.empty and not network_model.net.line.empty:
                    try:
                        cycles = topology.cycles(network_model.net)
                        if cycles:
                            diagnostic_results.append("检测到环网结构，可能影响潮流计算收敛性")
                    except Exception:
                        pass  # 忽略环网检查错误
                        
            except ImportError:
                pass  # 如果拓扑模块不可用，跳过连通性检查
            
            # 检查电压等级一致性
            if not network_model.net.bus.empty:
                voltage_levels = network_model.net.bus['vn_kv'].unique()
                if len(voltage_levels) > 3:  # 超过3个电压等级
                    diagnostic_results.append(
                        f"检测到多个电压等级: {sorted(voltage_levels)} kV，注意变压器配置"
                    )
            
            # 显示诊断结果
            if diagnostic_results:
                result_text = "\n".join(f"• {result}" for result in diagnostic_results)
                QMessageBox.warning(self, "网络诊断", 
                    f"网络诊断发现以下问题：\n\n{result_text}\n\n建议修复后再进入仿真模式。")
                return False
            else:
                self.network_is_valid = True
                QMessageBox.information(self, "网络诊断", "网络诊断通过！")
                return True
            
        except Exception as e:
            QMessageBox.critical(self, "网络诊断错误", f"网络诊断过程中发生错误：{str(e)}")
            return False
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 PandaPower 仿真工具",
            "<h3>PandaPower 仿真工具</h3>"
            "<p>基于PySide6和pandapower的电网仿真工具</p>"
            "<p>版本: 0.1.0</p>"
        )

    def open_topology(self):
        """从文件打开网络拓扑"""
        try:
            # 使用TopologyManager导入拓扑
            success = self.topology_manager.import_topology(
                self.canvas.scene, 
                self
            )
            
            if success:
                self.statusBar().showMessage("拓扑结构已加载", 3000)
                # 刷新画布视图
                self.canvas.fit_in_view()
            else:
                self.statusBar().showMessage("加载取消或失败", 3000)
                
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载拓扑结构时发生错误：\n{str(e)}")
            self.statusBar().showMessage("加载失败", 3000)

    def save_topology(self):
        """保存当前网络拓扑到文件"""
        try:
            # 使用TopologyManager保存拓扑
            success = self.topology_manager.export_topology(
                self.canvas.scene, 
                self
            )
            
            if success:
                self.statusBar().showMessage("拓扑结构已保存", 3000)
                return True
            else:
                self.statusBar().showMessage("保存取消或无网络组件", 3000)
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存拓扑结构时发生错误：\n{str(e)}")
            self.statusBar().showMessage("保存失败", 3000)

    def new_topology(self):
        """创建新的网络拓扑（清空当前场景）"""
        try:
            # 检查当前是否有组件，询问是否保存
            has_items = False
            for item in self.canvas.scene.items():
                if hasattr(item, 'component_type'):
                    has_items = True
                    break
            
            if has_items:
                reply = QMessageBox.question(
                    self, 
                    "新建网络", 
                    "当前网络中有组件，是否保存当前网络？",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )
                
                if reply == QMessageBox.Save:
                    # 先保存当前网络
                    if not self.save_topology():
                        return  # 如果保存取消，不新建
                elif reply == QMessageBox.Cancel:
                    return  # 取消新建操作
            
            # 清空当前场景（使用画布的专用清空方法）
            self.canvas.clear_canvas()
            
            # 重置组件计数器
            from components.network_items import BaseNetworkItem
            BaseNetworkItem.reset_component_counters()
            
            self.statusBar().showMessage("已创建新网络", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "新建错误", f"创建新网络时发生错误：\n{str(e)}")
            self.statusBar().showMessage("新建失败", 3000)