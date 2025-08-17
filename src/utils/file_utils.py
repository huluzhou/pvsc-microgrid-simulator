#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件工具类，用于处理文件保存和加载
"""

import os
import json
import pickle
from PyQt5.QtWidgets import QFileDialog, QMessageBox


def save_network(parent, network_model, scene_data):
    """保存网络到文件
    
    Args:
        parent: 父窗口
        network_model: 网络模型
        scene_data: 场景数据
    
    Returns:
        bool: 保存是否成功
    """
    # 打开文件对话框
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "保存网络",
        "",
        "PandaPower网络文件 (*.ppn);;所有文件 (*)"
    )
    
    if not file_path:
        return False
    
    # 确保文件扩展名
    if not file_path.endswith(".ppn"):
        file_path += ".ppn"
    
    try:
        # 创建保存数据
        save_data = {
            "network": network_model.net,
            "component_map": network_model.component_map,
            "scene_data": scene_data
        }
        
        # 保存到文件
        with open(file_path, "wb") as f:
            pickle.dump(save_data, f)
        
        return True
    except Exception as e:
        QMessageBox.critical(parent, "保存错误", f"保存网络时出错：{str(e)}")
        return False


def load_network(parent):
    """从文件加载网络
    
    Args:
        parent: 父窗口
    
    Returns:
        tuple: (network_data, scene_data) 如果加载成功，否则 (None, None)
    """
    # 打开文件对话框
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "加载网络",
        "",
        "PandaPower网络文件 (*.ppn);;所有文件 (*)"
    )
    
    if not file_path:
        return None, None
    
    try:
        # 从文件加载
        with open(file_path, "rb") as f:
            save_data = pickle.load(f)
        
        # 提取数据
        network_data = {
            "network": save_data.get("network"),
            "component_map": save_data.get("component_map")
        }
        scene_data = save_data.get("scene_data")
        
        return network_data, scene_data
    except Exception as e:
        QMessageBox.critical(parent, "加载错误", f"加载网络时出错：{str(e)}")
        return None, None


def export_results(parent, results):
    """导出计算结果
    
    Args:
        parent: 父窗口
        results: 计算结果
    
    Returns:
        bool: 导出是否成功
    """
    # 打开文件对话框
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "导出结果",
        "",
        "CSV文件 (*.csv);;JSON文件 (*.json);;所有文件 (*)"
    )
    
    if not file_path:
        return False
    
    try:
        # 根据文件扩展名选择导出格式
        if file_path.endswith(".csv"):
            # 导出为CSV
            for key, df in results.items():
                if df is not None:
                    df.to_csv(f"{os.path.splitext(file_path)[0]}_{key}.csv")
        elif file_path.endswith(".json"):
            # 导出为JSON
            result_dict = {}
            for key, df in results.items():
                if df is not None:
                    result_dict[key] = df.to_dict(orient="records")
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2)
        else:
            # 默认导出为JSON
            result_dict = {}
            for key, df in results.items():
                if df is not None:
                    result_dict[key] = df.to_dict(orient="records")
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2)
        
        return True
    except Exception as e:
        QMessageBox.critical(parent, "导出错误", f"导出结果时出错：{str(e)}")
        return False