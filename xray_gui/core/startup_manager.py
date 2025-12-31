"""
启动项管理器 - 管理应用程序的开机自启动功能
"""
import os
import sys
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from .registry_manager import registry_manager, RegistryHive, StartupEntry, RegistryError, PermissionError
except ImportError:
    # 非Windows平台
    registry_manager = None
    RegistryHive = None
    StartupEntry = None
    RegistryError = Exception
    PermissionError = Exception


class StartupStatus(Enum):
    """启动状态枚举"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    NOT_SET = "not_set"
    ERROR = "error"


@dataclass
class StartupValidationResult:
    """启动项验证结果"""
    is_valid: bool
    status: StartupStatus
    error_message: Optional[str] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class StartupManager:
    """启动项管理器"""
    
    def __init__(self, app_name: str = "XrayMultiPortManager"):
        self.app_name = app_name
        self.logger = logging.getLogger(__name__)
        
        # 检查平台支持
        if not self._is_windows():
            self.logger.warning("Startup management is only supported on Windows")
    
    def _is_windows(self) -> bool:
        """检查是否为Windows平台"""
        return os.name == 'nt' and registry_manager is not None
    
    def is_startup_enabled(self) -> StartupValidationResult:
        """
        检查启动项是否已启用
        
        Returns:
            启动项验证结果
        """
        if not self._is_windows():
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message="Startup management is not supported on this platform",
                suggestions=["This feature is only available on Windows"]
            )
        
        try:
            # 首先检查HKEY_CURRENT_USER
            entry = registry_manager.get_startup_entry(self.app_name, RegistryHive.HKEY_CURRENT_USER)
            
            if entry:
                validation_result = self.validate_startup_entry(entry)
                if validation_result.is_valid:
                    validation_result.status = StartupStatus.ENABLED
                    return validation_result
            
            # 检查HKEY_LOCAL_MACHINE
            entry = registry_manager.get_startup_entry(self.app_name, RegistryHive.HKEY_LOCAL_MACHINE)
            
            if entry:
                validation_result = self.validate_startup_entry(entry)
                if validation_result.is_valid:
                    validation_result.status = StartupStatus.ENABLED
                    return validation_result
            
            # 没有找到启动项
            return StartupValidationResult(
                is_valid=True,
                status=StartupStatus.NOT_SET,
                suggestions=["You can enable startup to automatically launch the application when Windows starts"]
            )
            
        except Exception as e:
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message=str(e),
                suggestions=["Check if you have sufficient permissions to access the registry"]
            )
    
    def enable_startup(self, use_admin_privileges: bool = False) -> StartupValidationResult:
        """
        启用开机自启动
        
        Args:
            use_admin_privileges: 是否使用管理员权限（写入HKEY_LOCAL_MACHINE）
            
        Returns:
            操作结果
        """
        if not self._is_windows():
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message="Startup management is not supported on this platform"
            )
        
        try:
            # 选择注册表根键
            hive = RegistryHive.HKEY_LOCAL_MACHINE if use_admin_privileges else RegistryHive.HKEY_CURRENT_USER
            
            # 创建启动命令
            command = registry_manager.create_startup_command()
            
            # 验证命令
            if not registry_manager.validate_startup_command(command):
                return StartupValidationResult(
                    is_valid=False,
                    status=StartupStatus.ERROR,
                    error_message="Invalid startup command generated",
                    suggestions=[
                        "Ensure the application executable exists",
                        "Check if the application path contains invalid characters"
                    ]
                )
            
            # 测试注册表访问权限
            can_access, access_error = registry_manager.test_registry_access(hive)
            if not can_access:
                suggestions = []
                if use_admin_privileges:
                    suggestions.append("Run the application as Administrator")
                else:
                    suggestions.append("Try enabling startup without admin privileges")
                    suggestions.append("Or run the application as Administrator")
                
                return StartupValidationResult(
                    is_valid=False,
                    status=StartupStatus.ERROR,
                    error_message=f"Registry access denied: {access_error}",
                    suggestions=suggestions
                )
            
            # 设置启动项
            success = registry_manager.set_startup_entry(self.app_name, command, hive)
            
            if success:
                # 验证设置是否成功
                verification_result = self.is_startup_enabled()
                if verification_result.status == StartupStatus.ENABLED:
                    return StartupValidationResult(
                        is_valid=True,
                        status=StartupStatus.ENABLED,
                        suggestions=["Startup has been successfully enabled"]
                    )
                else:
                    return StartupValidationResult(
                        is_valid=False,
                        status=StartupStatus.ERROR,
                        error_message="Startup was set but verification failed",
                        suggestions=["Try disabling and re-enabling startup"]
                    )
            else:
                return StartupValidationResult(
                    is_valid=False,
                    status=StartupStatus.ERROR,
                    error_message="Failed to set startup entry",
                    suggestions=["Check registry permissions and try again"]
                )
                
        except PermissionError as e:
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message=f"Permission denied: {e}",
                suggestions=[
                    "Run the application as Administrator",
                    "Or try enabling startup for current user only"
                ]
            )
        except Exception as e:
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message=str(e),
                suggestions=["Check system logs for more details"]
            )
    
    def disable_startup(self) -> StartupValidationResult:
        """
        禁用开机自启动
        
        Returns:
            操作结果
        """
        if not self._is_windows():
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message="Startup management is not supported on this platform"
            )
        
        try:
            removed_any = False
            errors = []
            
            # 尝试从HKEY_CURRENT_USER删除
            try:
                if registry_manager.remove_startup_entry(self.app_name, RegistryHive.HKEY_CURRENT_USER):
                    removed_any = True
            except Exception as e:
                errors.append(f"HKEY_CURRENT_USER: {e}")
            
            # 尝试从HKEY_LOCAL_MACHINE删除
            try:
                if registry_manager.remove_startup_entry(self.app_name, RegistryHive.HKEY_LOCAL_MACHINE):
                    removed_any = True
            except PermissionError:
                # 权限不足是正常的，不记录为错误
                pass
            except Exception as e:
                errors.append(f"HKEY_LOCAL_MACHINE: {e}")
            
            # 验证删除是否成功
            verification_result = self.is_startup_enabled()
            if verification_result.status == StartupStatus.NOT_SET:
                return StartupValidationResult(
                    is_valid=True,
                    status=StartupStatus.DISABLED,
                    suggestions=["Startup has been successfully disabled"]
                )
            elif verification_result.status == StartupStatus.ENABLED:
                return StartupValidationResult(
                    is_valid=False,
                    status=StartupStatus.ERROR,
                    error_message="Startup entry still exists after removal attempt",
                    suggestions=[
                        "Try running as Administrator to remove system-wide startup",
                        "Manually remove the startup entry from Windows Settings"
                    ]
                )
            else:
                return verification_result
                
        except Exception as e:
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message=str(e),
                suggestions=["Check system logs for more details"]
            )
    
    def validate_startup_entry(self, entry: StartupEntry) -> StartupValidationResult:
        """
        验证启动项的有效性
        
        Args:
            entry: 启动项条目
            
        Returns:
            验证结果
        """
        suggestions = []
        
        # 验证命令有效性
        if not registry_manager.validate_startup_command(entry.command):
            executable_path = registry_manager._extract_executable_path(entry.command)
            
            if not executable_path:
                return StartupValidationResult(
                    is_valid=False,
                    status=StartupStatus.ERROR,
                    error_message="Cannot extract executable path from startup command",
                    suggestions=[
                        "The startup command format is invalid",
                        "Remove and re-add the startup entry"
                    ]
                )
            
            if not os.path.exists(executable_path):
                return StartupValidationResult(
                    is_valid=False,
                    status=StartupStatus.ERROR,
                    error_message=f"Startup executable not found: {executable_path}",
                    suggestions=[
                        "The application may have been moved or uninstalled",
                        "Update the startup entry with the correct path",
                        "Or disable startup if the application is no longer needed"
                    ]
                )
        
        # 检查是否指向当前程序
        current_executable = registry_manager.get_current_executable_path()
        entry_executable = registry_manager._extract_executable_path(entry.command)
        
        if entry_executable and os.path.abspath(entry_executable) != os.path.abspath(current_executable):
            suggestions.append("Startup entry points to a different executable than the current one")
            suggestions.append("Consider updating the startup entry")
        
        return StartupValidationResult(
            is_valid=True,
            status=StartupStatus.ENABLED,
            suggestions=suggestions
        )
    
    def get_startup_info(self) -> Dict[str, any]:
        """
        获取启动项详细信息
        
        Returns:
            启动项信息字典
        """
        if not self._is_windows():
            return {
                "supported": False,
                "platform": sys.platform,
                "error": "Startup management is only supported on Windows"
            }
        
        info = {
            "supported": True,
            "platform": "windows",
            "app_name": self.app_name,
            "current_executable": registry_manager.get_current_executable_path(),
            "admin_privileges": registry_manager.check_admin_privileges(),
            "entries": []
        }
        
        # 检查两个注册表位置
        for hive in [RegistryHive.HKEY_CURRENT_USER, RegistryHive.HKEY_LOCAL_MACHINE]:
            try:
                entry = registry_manager.get_startup_entry(self.app_name, hive)
                if entry:
                    validation_result = self.validate_startup_entry(entry)
                    
                    info["entries"].append({
                        "hive": hive.name,
                        "name": entry.name,
                        "command": entry.command,
                        "is_valid": validation_result.is_valid,
                        "error": validation_result.error_message,
                        "suggestions": validation_result.suggestions
                    })
            except Exception as e:
                info["entries"].append({
                    "hive": hive.name,
                    "error": str(e)
                })
        
        return info
    
    def repair_startup(self) -> StartupValidationResult:
        """
        修复启动项
        
        Returns:
            修复结果
        """
        if not self._is_windows():
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message="Startup management is not supported on this platform"
            )
        
        try:
            # 首先检查当前状态
            current_status = self.is_startup_enabled()
            
            if current_status.status == StartupStatus.ENABLED and current_status.is_valid:
                return StartupValidationResult(
                    is_valid=True,
                    status=StartupStatus.ENABLED,
                    suggestions=["Startup is already working correctly"]
                )
            
            # 如果启动项存在但无效，先删除
            if current_status.status == StartupStatus.ENABLED and not current_status.is_valid:
                self.disable_startup()
            
            # 重新启用启动项
            return self.enable_startup(use_admin_privileges=False)
            
        except Exception as e:
            return StartupValidationResult(
                is_valid=False,
                status=StartupStatus.ERROR,
                error_message=f"Failed to repair startup: {e}",
                suggestions=["Try manually removing and re-adding the startup entry"]
            )


# 全局启动管理器实例
startup_manager = StartupManager()