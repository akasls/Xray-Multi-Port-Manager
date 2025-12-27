"""
开机自启管理器 - Windows 启动项管理
"""
import os
import sys
import winreg
from typing import Optional


class StartupManager:
    """Windows 开机自启管理器"""
    
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "XrayGUIManager"
    
    def __init__(self, app_name: str = None, app_path: str = None):
        """
        初始化启动管理器
        
        Args:
            app_name: 应用名称（注册表键名）
            app_path: 应用路径
        """
        self.app_name = app_name or self.APP_NAME
        self.app_path = app_path or self._get_default_path()
    
    def _get_default_path(self) -> str:
        """获取默认应用路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            return sys.executable
        else:
            # 开发环境
            return os.path.abspath(sys.argv[0])
    
    def _get_startup_command(self) -> str:
        """获取启动命令"""
        if self.app_path.endswith('.py'):
            # Python 脚本
            return f'"{sys.executable}" "{self.app_path}" --minimized'
        else:
            # 可执行文件
            return f'"{self.app_path}" --minimized'
    
    def enable(self) -> bool:
        """
        启用开机自启
        
        Returns:
            是否成功
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_SET_VALUE
            )
            
            winreg.SetValueEx(
                key,
                self.app_name,
                0,
                winreg.REG_SZ,
                self._get_startup_command()
            )
            
            winreg.CloseKey(key)
            return True
            
        except Exception:
            return False
    
    def disable(self) -> bool:
        """
        禁用开机自启
        
        Returns:
            是否成功
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, self.app_name)
            except FileNotFoundError:
                # 键不存在，视为成功
                pass
            
            winreg.CloseKey(key)
            return True
            
        except Exception:
            return False
    
    def is_enabled(self) -> bool:
        """
        检查是否已启用开机自启
        
        Returns:
            是否已启用
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            )
            
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return bool(value)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
                
        except Exception:
            return False
    
    def get_startup_path(self) -> Optional[str]:
        """
        获取当前注册的启动路径
        
        Returns:
            启动路径，未注册返回 None
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            )
            
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return value
            except FileNotFoundError:
                winreg.CloseKey(key)
                return None
                
        except Exception:
            return None
    
    def set_enabled(self, enabled: bool) -> bool:
        """
        设置开机自启状态
        
        Args:
            enabled: 是否启用
            
        Returns:
            是否成功
        """
        if enabled:
            return self.enable()
        else:
            return self.disable()
