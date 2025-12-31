"""
Windows注册表管理器 - 管理开机自启动功能
"""
import winreg
import os
import sys
import subprocess
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class RegistryHive(Enum):
    """注册表根键枚举"""
    HKEY_CURRENT_USER = winreg.HKEY_CURRENT_USER
    HKEY_LOCAL_MACHINE = winreg.HKEY_LOCAL_MACHINE


@dataclass
class StartupEntry:
    """启动项条目"""
    name: str
    command: str
    path: str
    hive: RegistryHive
    enabled: bool = True


class RegistryError(Exception):
    """注册表操作异常"""
    pass


class PermissionError(RegistryError):
    """权限不足异常"""
    pass


class RegistryManager:
    """Windows注册表管理器"""
    
    # 常用的启动项注册表路径
    STARTUP_PATHS = {
        RegistryHive.HKEY_CURRENT_USER: r"Software\Microsoft\Windows\CurrentVersion\Run",
        RegistryHive.HKEY_LOCAL_MACHINE: r"Software\Microsoft\Windows\CurrentVersion\Run"
    }
    
    def __init__(self):
        self._check_windows_platform()
    
    def _check_windows_platform(self) -> None:
        """检查是否为Windows平台"""
        if os.name != 'nt':
            raise RegistryError("Registry operations are only supported on Windows")
    
    def check_admin_privileges(self) -> bool:
        """
        检查是否具有管理员权限
        
        Returns:
            是否具有管理员权限
        """
        try:
            # 尝试访问需要管理员权限的注册表项
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               self.STARTUP_PATHS[RegistryHive.HKEY_LOCAL_MACHINE], 
                               0, winreg.KEY_READ):
                return True
        except PermissionError:
            return False
        except Exception:
            return False
    
    def get_startup_entry(self, name: str, hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> Optional[StartupEntry]:
        """
        获取启动项
        
        Args:
            name: 启动项名称
            hive: 注册表根键
            
        Returns:
            启动项条目，不存在返回None
            
        Raises:
            RegistryError: 注册表操作失败
            PermissionError: 权限不足
        """
        try:
            registry_path = self.STARTUP_PATHS[hive]
            
            with winreg.OpenKey(hive.value, registry_path, 0, winreg.KEY_READ) as key:
                try:
                    command, reg_type = winreg.QueryValueEx(key, name)
                    
                    return StartupEntry(
                        name=name,
                        command=command,
                        path=registry_path,
                        hive=hive,
                        enabled=True
                    )
                except FileNotFoundError:
                    return None
                    
        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing registry: {e}")
        except Exception as e:
            raise RegistryError(f"Failed to get startup entry '{name}': {e}")
    
    def set_startup_entry(self, name: str, command: str, hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> bool:
        """
        设置启动项
        
        Args:
            name: 启动项名称
            command: 启动命令
            hive: 注册表根键
            
        Returns:
            是否设置成功
            
        Raises:
            RegistryError: 注册表操作失败
            PermissionError: 权限不足
        """
        try:
            # 验证命令路径
            if not self.validate_startup_command(command):
                raise RegistryError(f"Invalid startup command: {command}")
            
            registry_path = self.STARTUP_PATHS[hive]
            
            with winreg.OpenKey(hive.value, registry_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
                return True
                
        except PermissionError as e:
            raise PermissionError(f"Permission denied writing to registry: {e}")
        except Exception as e:
            raise RegistryError(f"Failed to set startup entry '{name}': {e}")
    
    def remove_startup_entry(self, name: str, hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> bool:
        """
        删除启动项
        
        Args:
            name: 启动项名称
            hive: 注册表根键
            
        Returns:
            是否删除成功
            
        Raises:
            RegistryError: 注册表操作失败
            PermissionError: 权限不足
        """
        try:
            registry_path = self.STARTUP_PATHS[hive]
            
            with winreg.OpenKey(hive.value, registry_path, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, name)
                    return True
                except FileNotFoundError:
                    # 启动项不存在，认为删除成功
                    return True
                    
        except PermissionError as e:
            raise PermissionError(f"Permission denied deleting from registry: {e}")
        except Exception as e:
            raise RegistryError(f"Failed to remove startup entry '{name}': {e}")
    
    def list_startup_entries(self, hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> List[StartupEntry]:
        """
        列出所有启动项
        
        Args:
            hive: 注册表根键
            
        Returns:
            启动项列表
            
        Raises:
            RegistryError: 注册表操作失败
            PermissionError: 权限不足
        """
        try:
            entries = []
            registry_path = self.STARTUP_PATHS[hive]
            
            with winreg.OpenKey(hive.value, registry_path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, command, reg_type = winreg.EnumValue(key, i)
                        
                        entry = StartupEntry(
                            name=name,
                            command=command,
                            path=registry_path,
                            hive=hive,
                            enabled=True
                        )
                        entries.append(entry)
                        i += 1
                        
                    except OSError:
                        # 没有更多值了
                        break
            
            return entries
            
        except PermissionError as e:
            raise PermissionError(f"Permission denied reading registry: {e}")
        except Exception as e:
            raise RegistryError(f"Failed to list startup entries: {e}")
    
    def validate_startup_command(self, command: str) -> bool:
        """
        验证启动命令的有效性
        
        Args:
            command: 启动命令
            
        Returns:
            是否为有效命令
        """
        if not command or not command.strip():
            return False
        
        # 提取可执行文件路径
        executable_path = self._extract_executable_path(command)
        
        if not executable_path:
            return False
        
        # 检查文件是否存在
        if not os.path.exists(executable_path):
            return False
        
        # 检查是否为可执行文件
        if not executable_path.lower().endswith(('.exe', '.bat', '.cmd', '.com')):
            return False
        
        return True
    
    def _extract_executable_path(self, command: str) -> Optional[str]:
        """
        从命令中提取可执行文件路径
        
        Args:
            command: 完整命令
            
        Returns:
            可执行文件路径
        """
        command = command.strip()
        
        # 处理带引号的路径
        if command.startswith('"'):
            end_quote = command.find('"', 1)
            if end_quote != -1:
                return command[1:end_quote]
        
        # 处理不带引号的路径
        parts = command.split()
        if parts:
            return parts[0]
        
        return None
    
    def get_current_executable_path(self) -> str:
        """
        获取当前可执行文件的路径
        
        Returns:
            当前可执行文件路径
        """
        if getattr(sys, 'frozen', False):
            # 如果是打包的可执行文件
            return sys.executable
        else:
            # 如果是Python脚本
            return os.path.abspath(sys.argv[0])
    
    def create_startup_command(self, executable_path: Optional[str] = None, arguments: Optional[List[str]] = None) -> str:
        """
        创建启动命令
        
        Args:
            executable_path: 可执行文件路径，None使用当前程序
            arguments: 命令行参数
            
        Returns:
            完整的启动命令
        """
        if executable_path is None:
            executable_path = self.get_current_executable_path()
        
        # 如果路径包含空格，添加引号
        if ' ' in executable_path:
            command = f'"{executable_path}"'
        else:
            command = executable_path
        
        # 添加参数
        if arguments:
            command += ' ' + ' '.join(arguments)
        
        return command
    
    def test_registry_access(self, hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> Tuple[bool, Optional[str]]:
        """
        测试注册表访问权限
        
        Args:
            hive: 注册表根键
            
        Returns:
            (是否可访问, 错误信息)
        """
        try:
            registry_path = self.STARTUP_PATHS[hive]
            
            # 测试读取权限
            with winreg.OpenKey(hive.value, registry_path, 0, winreg.KEY_READ):
                pass
            
            # 测试写入权限
            test_name = "__test_access__"
            test_command = "test"
            
            try:
                with winreg.OpenKey(hive.value, registry_path, 0, winreg.KEY_WRITE) as key:
                    winreg.SetValueEx(key, test_name, 0, winreg.REG_SZ, test_command)
                    winreg.DeleteValue(key, test_name)
                
                return True, None
                
            except PermissionError:
                return False, "Write permission denied"
                
        except PermissionError:
            return False, "Read permission denied"
        except Exception as e:
            return False, str(e)
    
    def backup_startup_entries(self, hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> Dict[str, str]:
        """
        备份启动项
        
        Args:
            hive: 注册表根键
            
        Returns:
            启动项备份字典 {name: command}
            
        Raises:
            RegistryError: 备份失败
        """
        try:
            backup = {}
            entries = self.list_startup_entries(hive)
            
            for entry in entries:
                backup[entry.name] = entry.command
            
            return backup
            
        except Exception as e:
            raise RegistryError(f"Failed to backup startup entries: {e}")
    
    def restore_startup_entries(self, backup: Dict[str, str], hive: RegistryHive = RegistryHive.HKEY_CURRENT_USER) -> bool:
        """
        恢复启动项
        
        Args:
            backup: 启动项备份字典
            hive: 注册表根键
            
        Returns:
            是否恢复成功
            
        Raises:
            RegistryError: 恢复失败
        """
        try:
            for name, command in backup.items():
                self.set_startup_entry(name, command, hive)
            
            return True
            
        except Exception as e:
            raise RegistryError(f"Failed to restore startup entries: {e}")


# 全局注册表管理器实例
try:
    registry_manager = RegistryManager()
except RegistryError:
    # 非Windows平台，设置为None
    registry_manager = None