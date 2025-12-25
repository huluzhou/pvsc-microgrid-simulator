#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志记录模块
用于监控自动计算模块的运行状态，记录启动时间、执行状态、关键操作节点及异常信息
"""

import os
import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler

class LoggerManager:
    """日志管理类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化日志配置"""
        # 创建logger对象
        self.logger = logging.getLogger('power_simulation')
        self.logger.setLevel(logging.DEBUG)
        
        # 确保没有重复添加处理器
        if self.logger.handlers:
            return
        
        # 获取可执行文件同级目录作为日志保存路径
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            log_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            log_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '..', '..')))
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志文件名（按日期命名）
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f'power_simulation_{current_date}.log')
        
        # 创建文件处理器，使用RotatingFileHandler来控制文件大小
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=100,          # 保留100个备份文件
            encoding='utf-8'
        )
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        self.logger.addHandler(file_handler)
        
        # 将pymodbus日志重定向到同一处理器
        try:
            modbus_loggers = [
                # 'pymodbus',
                'pymodbus.client',
                'pymodbus.server',
                'pymodbus.framer',
                # 'pymodbus.datastore',
                'pymodbus.transaction',
                'pymodbus.transport'
            ]
            for name in modbus_loggers:
                l = logging.getLogger(name)
                l.setLevel(logging.DEBUG)
                l.propagate = False
                if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == file_handler.baseFilename for h in l.handlers):
                    l.addHandler(file_handler)
        except Exception:
            pass
        
    def debug(self, message):
        """记录调试日志"""
        self.logger.debug(message)
        
    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)
        
    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)
        
    def error(self, message):
        """记录错误日志"""
        self.logger.error(message)
    
    def critical(self, message):
        """记录严重错误日志"""
        self.logger.critical(message)

# 创建全局日志实例
logger = LoggerManager()
