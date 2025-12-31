"""
启动项故障排除器 - 提供详细的错误诊断和解决方案
"""
import os
import sys
import subprocess
import ctypes
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from .startup_manager import startup_manager, StartupStatus, StartupValidationResult
    from .registry_manager import registry_manager, RegistryHive
except ImportError:
    startup_manager = None
    registry_manager = None
    StartupStatus = None
    StartupValidationResult = None
    RegistryHive = None


class TroubleshootingLevel(Enum):
    """故障排除级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TroubleshootingStep:
    """故障排除步骤"""
    title: str
    description: str
    level: TroubleshootingLevel
    action_required: bool = False
    auto_fixable: bool = False
    fix_command: Optional[str] = None


@dataclass
class DiagnosticResult:
    """诊断结果"""
    issue_found: bool
    issue_description: str
    severity: TroubleshootingLevel
    steps: List[TroubleshootingStep]
    can_auto_fix: bool = False


class StartupTroubleshooter:
    """启动项故障排除器"""
    
    def __init__(self):
        self.is_windows = os.name == 'nt'
        self.is_admin = self._check_admin_privileges() if self.is_windows else False
    
    def _check_admin_privileges(self) -> bool:
        """检查管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def run_full_diagnosis(self) -> List[DiagnosticResult]:
        """
        运行完整的启动项诊断
        
        Returns:
            诊断结果列表
        """
        results = []
        
        if not self.is_windows:
            results.append(DiagnosticResult(
                issue_found=True,
                issue_description="Platform not supported",
                severity=TroubleshootingLevel.CRITICAL,
                steps=[
                    TroubleshootingStep(
                        title="Unsupported Platform",
                        description="Startup management is only supported on Windows",
                        level=TroubleshootingLevel.CRITICAL
                    )
                ]
            ))
            return results
        
        # 检查基本系统要求
        results.extend(self._diagnose_system_requirements())
        
        # 检查权限问题
        results.extend(self._diagnose_permissions())
        
        # 检查启动项状态
        results.extend(self._diagnose_startup_status())
        
        # 检查注册表完整性
        results.extend(self._diagnose_registry_integrity())
        
        # 检查文件系统问题
        results.extend(self._diagnose_filesystem_issues())
        
        return results
    
    def _diagnose_system_requirements(self) -> List[DiagnosticResult]:
        """诊断系统要求"""
        results = []
        
        # 检查Windows版本
        try:
            import platform
            windows_version = platform.win32_ver()[0]
            
            if not windows_version:
                results.append(DiagnosticResult(
                    issue_found=True,
                    issue_description="Cannot determine Windows version",
                    severity=TroubleshootingLevel.WARNING,
                    steps=[
                        TroubleshootingStep(
                            title="Unknown Windows Version",
                            description="Unable to determine Windows version. Some features may not work correctly.",
                            level=TroubleshootingLevel.WARNING
                        )
                    ]
                ))
        except Exception as e:
            results.append(DiagnosticResult(
                issue_found=True,
                issue_description=f"System detection failed: {e}",
                severity=TroubleshootingLevel.ERROR,
                steps=[
                    TroubleshootingStep(
                        title="System Detection Error",
                        description="Failed to detect system information. This may indicate system corruption.",
                        level=TroubleshootingLevel.ERROR
                    )
                ]
            ))
        
        return results
    
    def _diagnose_permissions(self) -> List[DiagnosticResult]:
        """诊断权限问题"""
        results = []
        
        if not registry_manager:
            return results
        
        # 检查当前用户注册表权限
        can_access_user, user_error = registry_manager.test_registry_access(RegistryHive.HKEY_CURRENT_USER)
        
        if not can_access_user:
            steps = [
                TroubleshootingStep(
                    title="User Registry Access Denied",
                    description=f"Cannot access user registry: {user_error}",
                    level=TroubleshootingLevel.ERROR,
                    action_required=True
                ),
                TroubleshootingStep(
                    title="Restart Application",
                    description="Try restarting the application",
                    level=TroubleshootingLevel.INFO,
                    action_required=True
                ),
                TroubleshootingStep(
                    title="Check User Account",
                    description="Ensure your user account is not corrupted",
                    level=TroubleshootingLevel.WARNING,
                    action_required=True
                )
            ]
            
            results.append(DiagnosticResult(
                issue_found=True,
                issue_description="User registry access denied",
                severity=TroubleshootingLevel.ERROR,
                steps=steps
            ))
        
        # 检查系统注册表权限
        can_access_system, system_error = registry_manager.test_registry_access(RegistryHive.HKEY_LOCAL_MACHINE)
        
        if not can_access_system and not self.is_admin:
            steps = [
                TroubleshootingStep(
                    title="System Registry Access Requires Admin",
                    description="System-wide startup requires administrator privileges",
                    level=TroubleshootingLevel.INFO
                ),
                TroubleshootingStep(
                    title="Run as Administrator",
                    description="Right-click the application and select 'Run as administrator'",
                    level=TroubleshootingLevel.INFO,
                    action_required=True,
                    auto_fixable=True,
                    fix_command="runas"
                ),
                TroubleshootingStep(
                    title="Use User-Level Startup",
                    description="Alternatively, use user-level startup which doesn't require admin privileges",
                    level=TroubleshootingLevel.INFO
                )
            ]
            
            results.append(DiagnosticResult(
                issue_found=False,  # 这不是问题，只是信息
                issue_description="System registry access requires administrator privileges",
                severity=TroubleshootingLevel.INFO,
                steps=steps
            ))
        
        return results
    
    def _diagnose_startup_status(self) -> List[DiagnosticResult]:
        """诊断启动项状态"""
        results = []
        
        if not startup_manager:
            return results
        
        try:
            status_result = startup_manager.is_startup_enabled()
            
            if status_result.status == StartupStatus.ERROR:
                steps = [
                    TroubleshootingStep(
                        title="Startup Status Error",
                        description=status_result.error_message or "Unknown error occurred",
                        level=TroubleshootingLevel.ERROR,
                        action_required=True
                    )
                ]
                
                # 添加建议的解决步骤
                for suggestion in status_result.suggestions:
                    steps.append(TroubleshootingStep(
                        title="Suggested Solution",
                        description=suggestion,
                        level=TroubleshootingLevel.INFO,
                        action_required=True
                    ))
                
                results.append(DiagnosticResult(
                    issue_found=True,
                    issue_description="Startup status check failed",
                    severity=TroubleshootingLevel.ERROR,
                    steps=steps
                ))
            
            elif status_result.status == StartupStatus.ENABLED and not status_result.is_valid:
                steps = [
                    TroubleshootingStep(
                        title="Invalid Startup Entry",
                        description="Startup entry exists but is invalid",
                        level=TroubleshootingLevel.WARNING,
                        action_required=True
                    ),
                    TroubleshootingStep(
                        title="Repair Startup Entry",
                        description="Remove and recreate the startup entry",
                        level=TroubleshootingLevel.INFO,
                        action_required=True,
                        auto_fixable=True,
                        fix_command="repair_startup"
                    )
                ]
                
                results.append(DiagnosticResult(
                    issue_found=True,
                    issue_description="Invalid startup entry detected",
                    severity=TroubleshootingLevel.WARNING,
                    steps=steps,
                    can_auto_fix=True
                ))
        
        except Exception as e:
            results.append(DiagnosticResult(
                issue_found=True,
                issue_description=f"Startup diagnosis failed: {e}",
                severity=TroubleshootingLevel.ERROR,
                steps=[
                    TroubleshootingStep(
                        title="Diagnosis Error",
                        description="Failed to check startup status",
                        level=TroubleshootingLevel.ERROR
                    )
                ]
            ))
        
        return results
    
    def _diagnose_registry_integrity(self) -> List[DiagnosticResult]:
        """诊断注册表完整性"""
        results = []
        
        if not registry_manager:
            return results
        
        try:
            # 检查启动项注册表路径是否存在
            for hive in [RegistryHive.HKEY_CURRENT_USER, RegistryHive.HKEY_LOCAL_MACHINE]:
                try:
                    entries = registry_manager.list_startup_entries(hive)
                    # 如果能成功列出条目，说明注册表路径正常
                except Exception as e:
                    hive_name = "User" if hive == RegistryHive.HKEY_CURRENT_USER else "System"
                    
                    steps = [
                        TroubleshootingStep(
                            title=f"{hive_name} Registry Path Corrupted",
                            description=f"Cannot access {hive_name.lower()} startup registry path: {e}",
                            level=TroubleshootingLevel.ERROR,
                            action_required=True
                        ),
                        TroubleshootingStep(
                            title="Run Registry Repair",
                            description="Run Windows Registry repair tools",
                            level=TroubleshootingLevel.WARNING,
                            action_required=True
                        ),
                        TroubleshootingStep(
                            title="System File Check",
                            description="Run 'sfc /scannow' in Command Prompt as Administrator",
                            level=TroubleshootingLevel.INFO,
                            action_required=True
                        )
                    ]
                    
                    results.append(DiagnosticResult(
                        issue_found=True,
                        issue_description=f"{hive_name} registry corruption detected",
                        severity=TroubleshootingLevel.ERROR,
                        steps=steps
                    ))
        
        except Exception as e:
            results.append(DiagnosticResult(
                issue_found=True,
                issue_description=f"Registry integrity check failed: {e}",
                severity=TroubleshootingLevel.ERROR,
                steps=[
                    TroubleshootingStep(
                        title="Registry Check Failed",
                        description="Unable to verify registry integrity",
                        level=TroubleshootingLevel.ERROR
                    )
                ]
            ))
        
        return results
    
    def _diagnose_filesystem_issues(self) -> List[DiagnosticResult]:
        """诊断文件系统问题"""
        results = []
        
        if not registry_manager:
            return results
        
        try:
            current_executable = registry_manager.get_current_executable_path()
            
            # 检查当前可执行文件
            if not os.path.exists(current_executable):
                steps = [
                    TroubleshootingStep(
                        title="Executable Not Found",
                        description=f"Current executable not found: {current_executable}",
                        level=TroubleshootingLevel.CRITICAL,
                        action_required=True
                    ),
                    TroubleshootingStep(
                        title="Reinstall Application",
                        description="The application may need to be reinstalled",
                        level=TroubleshootingLevel.ERROR,
                        action_required=True
                    )
                ]
                
                results.append(DiagnosticResult(
                    issue_found=True,
                    issue_description="Application executable missing",
                    severity=TroubleshootingLevel.CRITICAL,
                    steps=steps
                ))
            
            # 检查可执行文件权限
            elif not os.access(current_executable, os.R_OK):
                steps = [
                    TroubleshootingStep(
                        title="Executable Access Denied",
                        description=f"Cannot read executable: {current_executable}",
                        level=TroubleshootingLevel.ERROR,
                        action_required=True
                    ),
                    TroubleshootingStep(
                        title="Check File Permissions",
                        description="Verify file permissions and antivirus settings",
                        level=TroubleshootingLevel.WARNING,
                        action_required=True
                    )
                ]
                
                results.append(DiagnosticResult(
                    issue_found=True,
                    issue_description="Executable access denied",
                    severity=TroubleshootingLevel.ERROR,
                    steps=steps
                ))
            
            # 检查路径中的特殊字符
            elif any(char in current_executable for char in ['<', '>', '|', '*', '?']):
                steps = [
                    TroubleshootingStep(
                        title="Invalid Path Characters",
                        description="Executable path contains invalid characters",
                        level=TroubleshootingLevel.WARNING,
                        action_required=True
                    ),
                    TroubleshootingStep(
                        title="Move Application",
                        description="Move the application to a path without special characters",
                        level=TroubleshootingLevel.INFO,
                        action_required=True
                    )
                ]
                
                results.append(DiagnosticResult(
                    issue_found=True,
                    issue_description="Invalid characters in executable path",
                    severity=TroubleshootingLevel.WARNING,
                    steps=steps
                ))
        
        except Exception as e:
            results.append(DiagnosticResult(
                issue_found=True,
                issue_description=f"Filesystem check failed: {e}",
                severity=TroubleshootingLevel.ERROR,
                steps=[
                    TroubleshootingStep(
                        title="Filesystem Check Failed",
                        description="Unable to verify filesystem integrity",
                        level=TroubleshootingLevel.ERROR
                    )
                ]
            ))
        
        return results
    
    def auto_fix_issues(self, diagnostic_results: List[DiagnosticResult]) -> Dict[str, bool]:
        """
        自动修复可修复的问题
        
        Args:
            diagnostic_results: 诊断结果列表
            
        Returns:
            修复结果字典 {issue_description: success}
        """
        fix_results = {}
        
        for result in diagnostic_results:
            if result.can_auto_fix:
                try:
                    if "Invalid startup entry" in result.issue_description:
                        # 修复无效的启动项
                        repair_result = startup_manager.repair_startup()
                        fix_results[result.issue_description] = repair_result.is_valid
                    else:
                        fix_results[result.issue_description] = False
                except Exception:
                    fix_results[result.issue_description] = False
        
        return fix_results
    
    def generate_troubleshooting_report(self) -> str:
        """
        生成故障排除报告
        
        Returns:
            格式化的报告文本
        """
        results = self.run_full_diagnosis()
        
        report_lines = [
            "=== Xray Multi-Port Manager Startup Troubleshooting Report ===",
            f"Platform: {sys.platform}",
            f"Administrator: {'Yes' if self.is_admin else 'No'}",
            f"Diagnosis Time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=== Issues Found ==="
        ]
        
        issues_found = False
        for result in results:
            if result.issue_found:
                issues_found = True
                report_lines.append(f"\n[{result.severity.value.upper()}] {result.issue_description}")
                
                for step in result.steps:
                    action_marker = " (ACTION REQUIRED)" if step.action_required else ""
                    report_lines.append(f"  - {step.title}: {step.description}{action_marker}")
        
        if not issues_found:
            report_lines.append("No issues detected.")
        
        # 添加系统信息
        if startup_manager:
            report_lines.extend([
                "",
                "=== System Information ===",
            ])
            
            try:
                info = startup_manager.get_startup_info()
                for key, value in info.items():
                    if key != "entries":
                        report_lines.append(f"{key}: {value}")
                
                if info.get("entries"):
                    report_lines.append("\nStartup Entries:")
                    for entry in info["entries"]:
                        report_lines.append(f"  - {entry}")
            except Exception as e:
                report_lines.append(f"Failed to get system information: {e}")
        
        return "\n".join(report_lines)


# 全局故障排除器实例
startup_troubleshooter = StartupTroubleshooter()