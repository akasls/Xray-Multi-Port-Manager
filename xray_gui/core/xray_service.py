"""
Xray 服务管理器 - 管理 Xray 进程
"""
import os
import subprocess
import time
import logging
from typing import Optional
from enum import Enum

try:
    from .process_monitor import process_monitor, ProcessInfo
except ImportError:
    process_monitor = None
    ProcessInfo = None


class ServiceStatus(Enum):
    """服务状态枚举"""
    STOPPED = "stopped"
    RUNNING = "running"
    STARTING = "starting"
    ERROR = "error"


class XrayService:
    """Xray 进程管理器"""
    
    def __init__(self, xray_path: str = "xray.exe", config_path: str = "config.json"):
        """
        初始化服务管理器
        
        Args:
            xray_path: xray 可执行文件路径
            config_path: 配置文件路径
        """
        self.xray_path = xray_path
        self.config_path = config_path
        self._process: Optional[subprocess.Popen] = None
        self._status = ServiceStatus.STOPPED
        self._error_message = ""
        self.logger = logging.getLogger(__name__)
    
    @property
    def status(self) -> ServiceStatus:
        """获取服务状态"""
        self._update_status()
        return self._status
    
    @property
    def error_message(self) -> str:
        """获取错误信息"""
        return self._error_message
    
    def _update_status(self) -> None:
        """更新服务状态"""
        # 如果状态是 ERROR，保持不变
        if self._status == ServiceStatus.ERROR:
            return
        
        if self._process is None:
            self._status = ServiceStatus.STOPPED
        elif self._process.poll() is None:
            # 进程仍在运行，但需要验证是否真的在运行
            if process_monitor and hasattr(self._process, 'pid'):
                if process_monitor.is_process_running(self._process.pid):
                    self._status = ServiceStatus.RUNNING
                else:
                    self._status = ServiceStatus.STOPPED
                    self._process = None
            else:
                self._status = ServiceStatus.RUNNING
        else:
            self._status = ServiceStatus.STOPPED
            self._process = None
    
    def is_running(self) -> bool:
        """检查服务是否运行中"""
        return self.status == ServiceStatus.RUNNING
    
    def get_status_text(self) -> str:
        """获取状态文本"""
        status = self.status
        if status == ServiceStatus.RUNNING:
            return "运行中"
        elif status == ServiceStatus.STOPPED:
            return "已停止"
        elif status == ServiceStatus.STARTING:
            return "启动中"
        elif status == ServiceStatus.ERROR:
            return f"错误: {self._error_message}"
        return "未知"
    
    def check_executable(self) -> bool:
        """检查可执行文件是否存在"""
        return os.path.exists(self.xray_path)
    
    def check_config(self) -> bool:
        """检查配置文件是否存在"""
        return os.path.exists(self.config_path)
    
    def start(self, config_path: str = None) -> bool:
        """
        启动 Xray 服务
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            是否启动成功
        """
        # 重置错误状态
        if self._status == ServiceStatus.ERROR:
            self._status = ServiceStatus.STOPPED
            self._error_message = ""
        
        if self.is_running():
            return True
        
        if config_path:
            self.config_path = config_path
        
        # 检查可执行文件
        if not self.check_executable():
            self._error_message = f"找不到 {self.xray_path}"
            self._status = ServiceStatus.ERROR
            return False
        
        # 检查配置文件
        if not self.check_config():
            self._error_message = f"找不到配置文件 {self.config_path}"
            self._status = ServiceStatus.ERROR
            return False
        
        try:
            # 先杀掉所有旧的 xray 进程
            self.kill_all_xray()
            time.sleep(0.3)
            
            self._status = ServiceStatus.STARTING
            
            # 启动进程（隐藏窗口）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self._process = subprocess.Popen(
                [self.xray_path, "-c", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 等待一小段时间检查是否启动成功
            time.sleep(0.5)
            
            if self._process.poll() is not None:
                # 进程已退出，启动失败
                stderr = self._process.stderr.read().decode('utf-8', errors='ignore')
                self._error_message = stderr or "启动失败"
                self._status = ServiceStatus.ERROR
                self._process = None
                return False
            
            self._status = ServiceStatus.RUNNING
            self._error_message = ""
            return True
            
        except Exception as e:
            self._error_message = str(e)
            self._status = ServiceStatus.ERROR
            self._process = None
            return False
    
    def stop(self) -> bool:
        """
        停止 Xray 服务
        
        Returns:
            是否停止成功
        """
        if not self.is_running():
            return True
        
        try:
            if self._process:
                self._process.terminate()
                self._process.wait(timeout=5)
                self._process = None
            
            self._status = ServiceStatus.STOPPED
            return True
            
        except subprocess.TimeoutExpired:
            # 强制杀死
            if self._process:
                self._process.kill()
                self._process = None
            self._status = ServiceStatus.STOPPED
            return True
            
        except Exception as e:
            self._error_message = str(e)
            return False
    
    def restart(self, config_path: str = None) -> bool:
        """
        重启 Xray 服务
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            是否重启成功
        """
        self.stop()
        time.sleep(0.5)
        return self.start(config_path)
    
    def kill_all_xray(self) -> None:
        """杀死所有 xray 进程"""
        try:
            if process_monitor:
                # 使用进程监控器更精确地终止进程
                killed_count = process_monitor.kill_processes_by_name("xray", exact_match=False)
                if killed_count > 0:
                    self.logger.info(f"Killed {killed_count} xray processes")
            else:
                # 回退到系统命令
                os.system(f'taskkill /f /im {os.path.basename(self.xray_path)} >nul 2>&1')
        except Exception as e:
            self.logger.error(f"Error killing xray processes: {e}")
    
    def get_process_info(self) -> Optional[ProcessInfo]:
        """
        获取当前Xray进程信息
        
        Returns:
            进程信息，如果进程不存在返回None
        """
        if not self._process or not process_monitor:
            return None
        
        return process_monitor.get_process_info(self._process.pid)
    
    def get_all_xray_processes(self) -> list:
        """
        获取所有Xray进程信息
        
        Returns:
            Xray进程信息列表
        """
        if not process_monitor:
            return []
        
        return process_monitor.find_processes_by_name("xray", exact_match=False)
