#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
条件编译机制示例文件
演示如何在项目中使用类似C语言#ifdef的条件编译功能
"""

from config import (
    # 功能标志
    FEATURE_SIMULATION, FEATURE_MODBUS, FEATURE_REPORT, FEATURE_EXPORT,
    # 调试模式标志
    DEBUG_MODE, VERBOSE_LOGGING,
    # 辅助函数和装饰器
    is_feature_enabled, conditional_compile, import_if_enabled
)

# 示例1：使用条件判断直接检查功能标志

def example_feature_check():
    """\示例：直接检查功能标志"""
    print("=== 示例1：直接检查功能标志 ===")
    
    if FEATURE_SIMULATION:
        print("✅ 仿真功能已启用")
        # 仿真相关代码...
    else:
        print("❌ 仿真功能已禁用")
    
    if FEATURE_MODBUS:
        print("✅ Modbus通信功能已启用")
        # Modbus相关代码...
    else:
        print("❌ Modbus通信功能已禁用")
    
    # 使用辅助函数检查功能
    if is_feature_enabled(FEATURE_REPORT):
        print("✅ 报告生成功能已启用")
        # 报告生成相关代码...
    else:
        print("❌ 报告生成功能已禁用")

# 示例2：使用条件编译装饰器

def example_conditional_decorator():
    """\示例：使用条件编译装饰器"""
    print("\n=== 示例2：使用条件编译装饰器 ===")
    
    # 定义一个只有在仿真功能启用时才会执行的函数
    @conditional_compile(FEATURE_SIMULATION)
    def run_simulation():
        """运行电力系统仿真"""
        print("执行电力系统仿真...")
        # 仿真代码...
        return "仿真结果数据"
    
    # 定义一个只有在调试模式启用时才会执行的函数
    @conditional_compile(DEBUG_MODE)
    def debug_log(message):
        """输出调试日志"""
        print(f"[DEBUG] {message}")
    
    # 调用这些函数
    result = run_simulation()
    if result:
        print(f"仿真运行成功，结果: {result}")
    else:
        print("仿真功能已禁用，跳过执行")
    
    debug_log("这是一条调试信息")

# 示例3：条件导入模块

def example_conditional_import():
    """\示例：条件导入模块"""
    print("\n=== 示例3：条件导入模块 ===")
    
    # 条件导入可能不存在或不需要的模块
    # 例如，只有在仿真功能启用时才导入pandapower
    pp = import_if_enabled('pandapower', FEATURE_SIMULATION)
    
    if pp:
        print("✅ 成功导入pandapower模块")
        # 可以在这里使用pandapower模块
        try:
            # 创建一个简单的网络示例
            net = pp.create_empty_network()
            print("成功创建空的电力网络")
        except Exception as e:
            print(f"创建网络时出错: {e}")
    else:
        print("❌ 未导入pandapower模块（仿真功能已禁用或模块不存在）")

# 示例4：在类中使用条件编译

def example_class_conditional():
    """\示例：在类中使用条件编译"""
    print("\n=== 示例4：在类中使用条件编译 ===")
    
    class PowerSystemTool:
        def __init__(self):
            self.name = "电力系统工具"
            # 根据功能标志初始化不同的组件
            self.components = []
            
            if FEATURE_SIMULATION:
                self.components.append("仿真引擎")
                print("已加载仿真引擎")
            
            if FEATURE_MODBUS:
                self.components.append("Modbus通信模块")
                print("已加载Modbus通信模块")
            
            if FEATURE_REPORT:
                self.components.append("报告生成器")
                print("已加载报告生成器")
        
        @conditional_compile(FEATURE_EXPORT)
        def export_data(self, data, filename):
            """导出数据到文件"""
            print(f"导出数据到文件: {filename}")
            # 导出数据的代码...
            return True
    
    # 创建工具实例
    tool = PowerSystemTool()
    print(f"已加载的组件: {tool.components}")
    
    # 尝试调用条件导出功能
    export_result = tool.export_data({"key": "value"}, "export.csv")
    if export_result:
        print("数据导出成功")
    else:
        print("数据导出功能已禁用")

# 示例5：在主程序中集成条件编译

def example_main_integration():
    """\示例：在主程序中集成条件编译"""
    print("\n=== 示例5：在主程序中集成条件编译 ===")
    
    # 初始化日志
    if DEBUG_MODE:
        print("启动调试模式")
        
        if VERBOSE_LOGGING:
            print("启用详细日志记录")
    else:
        print("启动生产模式")
    
    # 加载必要的功能模块
    enabled_features = []
    if FEATURE_SIMULATION: enabled_features.append("仿真")
    if FEATURE_MODBUS: enabled_features.append("Modbus")
    if FEATURE_REPORT: enabled_features.append("报告")
    if FEATURE_EXPORT: enabled_features.append("导出")
    
    print(f"已启用的功能: {', '.join(enabled_features)}")
    
    # 运行主程序逻辑
    print("主程序逻辑执行中...")
    # 这里是主程序的核心代码
    print("主程序逻辑执行完成")

# 运行所有示例
if __name__ == "__main__":
    print("开始演示条件编译机制...\n")
    
    example_feature_check()
    example_conditional_decorator()
    example_conditional_import()
    example_class_conditional()
    example_main_integration()
    
    print("\n条件编译机制演示完成！")
    print("\n提示：您可以在config.py文件中修改各种功能标志的值，")
    print("来体验不同条件下代码的执行情况。")