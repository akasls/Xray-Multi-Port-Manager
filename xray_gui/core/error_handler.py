"""
错误处理和报告机制
Feature: xray-protocol-enhancement, Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""
import logging
import traceback
import sys
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    PROTOCOL_PARSING = "protocol_parsing"
    XRAY_SERVICE = "xray_service"
    LATENCY_TEST = "latency_test"
    STARTUP_MANAGEMENT = "startup_management"
    PORT_ALLOCATION = "port_allocation"
    CONFIG_PERSISTENCE = "config_persistence"
    NETWORK_CONNECTION = "network_connection"
    SYSTEM_PERMISSION = "system_permission"
    FILE_OPERATION = "file_operation"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """错误信息数据结构"""
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    details: Optional[str] = None
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'code': self.code,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'context': self.context,
            'suggestions': self.suggestions
        }
    
    def to_user_message(self) -> str:
        """生成用户友好的错误消息"""
        message = f"[{self.severity.value.upper()}] {self.message}"
        
        if self.details:
            message += f"\n详细信息: {self.details}"
        
        if self.suggestions:
            message += "\n建议解决方案:"
            for i, suggestion in enumerate(self.suggestions, 1):
                message += f"\n{i}. {suggestion}"
        
        return message


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.logger = logging.getLogger(__name__)
        self._error_callbacks: Dict[ErrorCategory, List[Callable[[ErrorInfo], None]]] = {}
        self._error_history: List[ErrorInfo] = []
        self._max_history = 1000
        
        # 预定义的错误信息
        self._error_definitions = self._initialize_error_definitions()
    
    def register_error_callback(self, category: ErrorCategory, callback: Callable[[ErrorInfo], None]):
        """注册错误回调函数"""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)
    
    def handle_error(self, 
                    category: ErrorCategory,
                    code: str,
                    message: Optional[str] = None,
                    details: Optional[str] = None,
                    context: Optional[Dict[str, Any]] = None,
                    exception: Optional[Exception] = None) -> ErrorInfo:
        """
        处理错误
        
        Args:
            category: 错误类别
            code: 错误代码
            message: 自定义错误消息
            details: 错误详细信息
            context: 错误上下文
            exception: 异常对象
            
        Returns:
            错误信息对象
        """
        # 获取预定义的错误信息
        error_def = self._error_definitions.get(code)
        if error_def:
            severity = error_def['severity']
            default_message = error_def['message']
            suggestions = error_def.get('suggestions', [])
        else:
            severity = ErrorSeverity.ERROR
            default_message = "未知错误"
            suggestions = []
        
        # 使用自定义消息或默认消息
        final_message = message or default_message
        
        # 如果有异常，添加异常信息到详细信息中
        if exception:
            exception_details = f"{type(exception).__name__}: {str(exception)}"
            if details:
                details = f"{details}\n异常信息: {exception_details}"
            else:
                details = f"异常信息: {exception_details}"
            
            # 在调试模式下添加堆栈跟踪
            if self.logger.isEnabledFor(logging.DEBUG):
                details += f"\n堆栈跟踪:\n{traceback.format_exc()}"
        
        # 创建错误信息对象
        error_info = ErrorInfo(
            category=category,
            severity=severity,
            code=code,
            message=final_message,
            details=details,
            context=context,
            suggestions=suggestions
        )
        
        # 记录错误
        self._log_error(error_info)
        
        # 添加到历史记录
        self._add_to_history(error_info)
        
        # 调用回调函数
        self._notify_callbacks(error_info)
        
        return error_info
    
    def handle_exception(self, 
                        category: ErrorCategory,
                        exception: Exception,
                        context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        处理异常
        
        Args:
            category: 错误类别
            exception: 异常对象
            context: 错误上下文
            
        Returns:
            错误信息对象
        """
        # 根据异常类型确定错误代码
        exception_type = type(exception).__name__
        code = f"{category.value}_{exception_type.lower()}"
        
        return self.handle_error(
            category=category,
            code=code,
            message=f"{exception_type}: {str(exception)}",
            context=context,
            exception=exception
        )
    
    def get_error_history(self, 
                         category: Optional[ErrorCategory] = None,
                         severity: Optional[ErrorSeverity] = None,
                         limit: Optional[int] = None) -> List[ErrorInfo]:
        """
        获取错误历史记录
        
        Args:
            category: 过滤错误类别
            severity: 过滤错误严重程度
            limit: 限制返回数量
            
        Returns:
            错误信息列表
        """
        filtered_errors = self._error_history
        
        if category:
            filtered_errors = [e for e in filtered_errors if e.category == category]
        
        if severity:
            filtered_errors = [e for e in filtered_errors if e.severity == severity]
        
        if limit:
            filtered_errors = filtered_errors[-limit:]
        
        return filtered_errors
    
    def clear_error_history(self):
        """清空错误历史记录"""
        self._error_history.clear()
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        stats = {
            'total_errors': len(self._error_history),
            'by_category': {},
            'by_severity': {},
            'recent_errors': len([e for e in self._error_history 
                                if (datetime.now() - e.timestamp).total_seconds() < 3600])
        }
        
        for error in self._error_history:
            # 按类别统计
            category_key = error.category.value
            stats['by_category'][category_key] = stats['by_category'].get(category_key, 0) + 1
            
            # 按严重程度统计
            severity_key = error.severity.value
            stats['by_severity'][severity_key] = stats['by_severity'].get(severity_key, 0) + 1
        
        return stats
    
    def _initialize_error_definitions(self) -> Dict[str, Dict[str, Any]]:
        """初始化错误定义"""
        return {
            # 协议解析错误
            'protocol_parsing_invalid_link': {
                'severity': ErrorSeverity.ERROR,
                'message': '无效的协议链接格式',
                'suggestions': [
                    '检查链接格式是否正确',
                    '确认协议类型是否支持',
                    '验证链接是否完整'
                ]
            },
            'protocol_parsing_missing_params': {
                'severity': ErrorSeverity.WARNING,
                'message': '协议链接缺少必要参数',
                'suggestions': [
                    '检查链接是否包含所有必要参数',
                    '联系服务提供商获取完整链接'
                ]
            },
            'protocol_parsing_decode_error': {
                'severity': ErrorSeverity.ERROR,
                'message': '协议链接解码失败',
                'suggestions': [
                    '检查链接编码格式',
                    '尝试重新获取链接',
                    '确认链接未被截断'
                ]
            },
            
            # Xray服务错误
            'xray_service_start_failed': {
                'severity': ErrorSeverity.CRITICAL,
                'message': 'Xray服务启动失败',
                'suggestions': [
                    '检查Xray可执行文件是否存在',
                    '验证配置文件格式是否正确',
                    '确认端口未被占用',
                    '检查系统权限'
                ]
            },
            'xray_service_config_invalid': {
                'severity': ErrorSeverity.ERROR,
                'message': 'Xray配置文件无效',
                'suggestions': [
                    '检查JSON格式是否正确',
                    '验证配置参数是否有效',
                    '重新生成配置文件'
                ]
            },
            'xray_service_process_died': {
                'severity': ErrorSeverity.CRITICAL,
                'message': 'Xray进程意外终止',
                'suggestions': [
                    '检查系统日志',
                    '验证配置文件',
                    '重启服务'
                ]
            },
            
            # 延迟测试错误
            'latency_test_timeout': {
                'severity': ErrorSeverity.WARNING,
                'message': '延迟测试超时',
                'suggestions': [
                    '检查网络连接',
                    '确认节点地址是否可达',
                    '增加超时时间'
                ]
            },
            'latency_test_connection_failed': {
                'severity': ErrorSeverity.WARNING,
                'message': '延迟测试连接失败',
                'suggestions': [
                    '检查节点配置是否正确',
                    '验证网络连接',
                    '确认防火墙设置'
                ]
            },
            'latency_test_tun_mode_conflict': {
                'severity': ErrorSeverity.WARNING,
                'message': 'TUN模式影响延迟测试准确性',
                'suggestions': [
                    '暂时关闭TUN模式进行测试',
                    '使用直连模式测试',
                    '检查网络接口配置'
                ]
            },
            
            # 自启动管理错误
            'startup_management_registry_access_denied': {
                'severity': ErrorSeverity.ERROR,
                'message': '注册表访问被拒绝',
                'suggestions': [
                    '以管理员身份运行程序',
                    '检查用户权限',
                    '确认UAC设置'
                ]
            },
            'startup_management_registry_key_not_found': {
                'severity': ErrorSeverity.WARNING,
                'message': '注册表启动项不存在',
                'suggestions': [
                    '重新设置自启动',
                    '检查注册表路径',
                    '验证程序路径'
                ]
            },
            'startup_management_invalid_command': {
                'severity': ErrorSeverity.ERROR,
                'message': '启动命令无效',
                'suggestions': [
                    '检查程序路径是否正确',
                    '验证命令行参数',
                    '确认文件权限'
                ]
            },
            
            # 端口分配错误
            'port_allocation_port_in_use': {
                'severity': ErrorSeverity.WARNING,
                'message': '端口已被占用',
                'suggestions': [
                    '使用其他端口',
                    '关闭占用端口的程序',
                    '检查端口使用情况'
                ]
            },
            'port_allocation_range_exhausted': {
                'severity': ErrorSeverity.ERROR,
                'message': '可用端口范围已耗尽',
                'suggestions': [
                    '扩大端口分配范围',
                    '清理未使用的端口',
                    '减少节点数量'
                ]
            },
            'port_allocation_invalid_range': {
                'severity': ErrorSeverity.ERROR,
                'message': '端口范围配置无效',
                'suggestions': [
                    '检查端口范围设置',
                    '确认起始和结束端口',
                    '使用有效的端口范围'
                ]
            },
            
            # 配置持久化错误
            'config_persistence_file_not_found': {
                'severity': ErrorSeverity.WARNING,
                'message': '配置文件不存在',
                'suggestions': [
                    '创建新的配置文件',
                    '从备份恢复',
                    '检查文件路径'
                ]
            },
            'config_persistence_file_corrupted': {
                'severity': ErrorSeverity.ERROR,
                'message': '配置文件已损坏',
                'suggestions': [
                    '从备份恢复配置',
                    '重新创建配置文件',
                    '检查磁盘空间'
                ]
            },
            'config_persistence_permission_denied': {
                'severity': ErrorSeverity.ERROR,
                'message': '配置文件访问权限不足',
                'suggestions': [
                    '检查文件权限',
                    '以管理员身份运行',
                    '更改文件位置'
                ]
            },
            
            # 网络连接错误
            'network_connection_no_internet': {
                'severity': ErrorSeverity.WARNING,
                'message': '无网络连接',
                'suggestions': [
                    '检查网络连接',
                    '确认DNS设置',
                    '重启网络适配器'
                ]
            },
            'network_connection_dns_failed': {
                'severity': ErrorSeverity.WARNING,
                'message': 'DNS解析失败',
                'suggestions': [
                    '检查DNS服务器设置',
                    '使用其他DNS服务器',
                    '清除DNS缓存'
                ]
            },
            'network_connection_proxy_error': {
                'severity': ErrorSeverity.WARNING,
                'message': '代理连接错误',
                'suggestions': [
                    '检查代理设置',
                    '验证代理服务器状态',
                    '尝试直连'
                ]
            }
        }
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误到日志"""
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        log_message = f"[{error_info.category.value}] {error_info.code}: {error_info.message}"
        if error_info.details:
            log_message += f" | Details: {error_info.details}"
        
        self.logger.log(log_level, log_message)
    
    def _add_to_history(self, error_info: ErrorInfo):
        """添加错误到历史记录"""
        self._error_history.append(error_info)
        
        # 限制历史记录数量
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]
    
    def _notify_callbacks(self, error_info: ErrorInfo):
        """通知错误回调函数"""
        callbacks = self._error_callbacks.get(error_info.category, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")


# 全局错误处理器实例
global_error_handler = ErrorHandler()


def handle_error(category: ErrorCategory, 
                code: str,
                message: Optional[str] = None,
                details: Optional[str] = None,
                context: Optional[Dict[str, Any]] = None,
                exception: Optional[Exception] = None) -> ErrorInfo:
    """全局错误处理函数"""
    return global_error_handler.handle_error(
        category=category,
        code=code,
        message=message,
        details=details,
        context=context,
        exception=exception
    )


def handle_exception(category: ErrorCategory,
                    exception: Exception,
                    context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """全局异常处理函数"""
    return global_error_handler.handle_exception(
        category=category,
        exception=exception,
        context=context
    )


def error_handler_decorator(category: ErrorCategory):
    """错误处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = handle_exception(category, e, {
                    'function': func.__name__,
                    'args': str(args)[:200],  # 限制长度
                    'kwargs': str(kwargs)[:200]
                })
                # 重新抛出异常，让调用者决定如何处理
                raise e
        return wrapper
    return decorator