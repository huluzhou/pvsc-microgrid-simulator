#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主窗口组件
"""

import threading
from PySide6.QtWidgets import QMainWindow, QDockWidget, QMessageBox, QProgressDialog
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QAction

from components.canvas import NetworkCanvas
from components.component_palette import ComponentPalette
from components.properties_panel import PropertiesPanel
from components.topology_utils import TopologyManager
from config import (
    # 功能标志
    FEATURE_SIMULATION, DEBUG_MODE, conditional_compile
)
from utils.logger import logger
# import pandapower as pp
if FEATURE_SIMULATION:
    import pandapower as pp
    from models.network_model import NetworkModel
# 从globals.py导入全局变量

class DiagnosticThread(QObject):
    """网络诊断线程类，使用Python原生threading模块实现"""
    progress_updated = Signal(int)  # 进度更新信号
    diagnostic_completed = Signal(bool, str, dict)  # 诊断完成信号
    error_occurred = Signal(str)  # 错误发生信号
    
    def __init__(self, network_model):
        super().__init__()
        self.net = network_model.net
        self.running = True
        self._thread = None
    
    def run(self):
        """线程运行函数，只执行网络诊断操作"""
        try:
            # 初始化进度
            self.progress_updated.emit(30)
            
            # 使用pandapower内置诊断函数
            diagnostic_results = {}
            
            if not DEBUG_MODE:
                try:
                    # 运行诊断检查
                    diag_report = pp.diagnostic(self.net)
                    
                    # 解析诊断报告
                    if diag_report:
                        diagnostic_results.update(diag_report)
                        
                except Exception as e:
                    # 如果pandapower诊断模块不可用或发生错误，添加错误信息
                    diagnostic_results['error'] = f"警告：诊断过程中发生错误：{str(e)}"
            
            self.progress_updated.emit(80)
            
            self.progress_updated.emit(90)
            
            self.progress_updated.emit(95)
            
            # 诊断完成
            if self.running:
                self.progress_updated.emit(100)
                self.diagnostic_completed.emit(True, None, diagnostic_results)
                
        except Exception as e:
            if self.running:
                self.error_occurred.emit(str(e))
    
    def start(self):
        """启动线程"""
        self.running = True
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True  # 设置为守护线程，主线程结束时自动终止
        self._thread.start()
        
    def stop(self):
        """停止诊断线程"""
        self.running = False
        if self._thread and self._thread.is_alive():
            # 等待线程结束，但不阻塞主线程太长时间
            self._thread.join(timeout=1.0)  # 最多等待1秒
    
    def is_alive(self):
        """检查线程是否存活"""
        return self._thread and self._thread.is_alive()
    
class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.network_is_valid = False  # 网络状态标志位 
        self.network_items = {
            "bus": {},
            "line": {},
            "transformer": {},
            "load": {},
            "storage": {},
            "charger": {},
            "external_grid": {},
            "static_generator": {},
            "switch": {},
            "meter": {},
        }
        if FEATURE_SIMULATION:
            self.network_model = NetworkModel(self.network_items)
        self.topology_manager = TopologyManager(self.network_items)
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
                
            logger.info(f"属性更新: {component_type}.{prop_name} = {new_value}")
            self.network_is_valid = False
            logger.info("网络状态已标记为无效")
            
        except Exception as e:
            logger.error(f"处理属性变化时出错: {e}")
    
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
        """启动网络诊断线程"""
        # 显示进度对话框
        self.progress_dialog = QProgressDialog("正在进行网络诊断...", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("网络诊断")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        # 彻底禁用取消按钮
        self.progress_dialog.setCancelButton(None)
        
        # 确保之前的线程已经结束
        if hasattr(self, 'diagnostic_thread') and self.diagnostic_thread is not None:
            self.diagnostic_thread.stop()
            # 断开所有之前的信号连接
            try:
                self.diagnostic_thread.progress_updated.disconnect()
                self.diagnostic_thread.diagnostic_completed.disconnect()
                self.diagnostic_thread.error_occurred.disconnect()
            except TypeError:
                pass  # 忽略已断开连接的异常
            
            # 将线程引用设置为None，允许垃圾回收
            self.diagnostic_thread = None
        
        try:
            # 在主线程中创建网络模型
            self.progress_dialog.setValue(5)
            
            self.progress_dialog.setValue(10)
            
            # 显式清理旧的网络模型资源（如果有）
            if hasattr(self.network_model, 'net'):
                # 将net设置为None，帮助垃圾回收
                self.network_model.net = None
            
            # 重新实例化NetworkModel类以完全清空现有结构
            self.network_model = NetworkModel(self.network_items)
            
            # 从网络项创建模型
            if not self.network_model.create_from_network_items(self.canvas):
                self.progress_dialog.close()
                QMessageBox.warning(self, "网络诊断", "创建网络模型失败，请检查电网组件。")
                return
            self.progress_dialog.setValue(20)
            
            # 验证IP和端口唯一性
            is_valid, error_msg = self.topology_manager.validate_ip_port_uniqueness(self.canvas.scene, None)
            if not is_valid:
                self.progress_dialog.close()
                QMessageBox.warning(self, "网络诊断", f"IP和端口不唯一：{error_msg}")
                return
            self.progress_dialog.setValue(30)
            
            # 创建诊断线程，并传入已创建好的网络模型
            self.diagnostic_thread = DiagnosticThread(self.network_model)
            
            # 连接信号和槽
            self.diagnostic_thread.progress_updated.connect(self.progress_dialog.setValue)
            self.diagnostic_thread.diagnostic_completed.connect(self.on_diagnostic_completed)
            self.diagnostic_thread.error_occurred.connect(self.on_diagnostic_error)
            # 启动线程
            self.diagnostic_thread.start()
            
            # 显示进度对话框
            self.progress_dialog.exec_()
        except Exception as e:
            self.progress_dialog.close()
            QMessageBox.critical(self, "错误", f"准备诊断时发生错误：{str(e)}")
    
    def on_diagnostic_completed(self, success, error_message, diagnostic_results=None):
        """处理诊断完成事件"""
        self.progress_dialog.close()
        
        if not success:
            QMessageBox.warning(self, "网络诊断", error_message)
            return
        
        # 显示诊断结果
        if diagnostic_results and 'error' not in diagnostic_results:
            result_text = "\n".join(f"• [{key}]: {value}" for key, value in diagnostic_results.items())
            QMessageBox.warning(self, "网络诊断", 
                f"网络诊断发现以下问题：\n\n{result_text}\n\n建议修复后再进入仿真模式。")
            self.network_is_valid = False
        else:
            self.network_is_valid = True
            QMessageBox.information(self, "网络诊断", "网络诊断通过！")
        
        # 停止诊断线程并清理资源
        if hasattr(self, 'diagnostic_thread'):
            self.diagnostic_thread.stop()
            # 断开所有信号连接，避免内存泄漏
            try:
                self.diagnostic_thread.progress_updated.disconnect()
                self.diagnostic_thread.diagnostic_completed.disconnect()
                self.diagnostic_thread.error_occurred.disconnect()
            except TypeError:
                pass  # 忽略已断开连接的异常
            
            # 将线程引用设置为None，允许垃圾回收
            self.diagnostic_thread = None
    
    def on_diagnostic_error(self, error_message):
        """处理诊断错误事件"""
        self.progress_dialog.close()
        QMessageBox.critical(self, "错误", f"网络诊断时发生错误：{error_message}")
        
        # 停止诊断线程并清理资源
        if hasattr(self, 'diagnostic_thread'):
            self.diagnostic_thread.stop()
            # 断开所有信号连接，避免内存泄漏
            try:
                self.diagnostic_thread.progress_updated.disconnect()
                self.diagnostic_thread.diagnostic_completed.disconnect()
                self.diagnostic_thread.error_occurred.disconnect()
            except TypeError:
                pass  # 忽略已断开连接的异常
            
            # 将线程引用设置为None，允许垃圾回收
            self.diagnostic_thread = None
        
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 PandaPower 仿真工具",
            "<h3>PandaPower 仿真工具</h3>"
            "<p>基于PySide6和pandapower的电网仿真工具</p>"
            "<p>版本: 1.0.5</p>"
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
            
            self.statusBar().showMessage("已创建新网络", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "新建错误", f"创建新网络时发生错误：\n{str(e)}")
            self.statusBar().showMessage("新建失败", 3000)