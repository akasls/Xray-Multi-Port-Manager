"""
UI状态同步器 - 自动同步UI显示状态
"""
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from enum import Enum

from .service_state_manager import EnhancedServiceManager, ServiceState, ServiceStateStatus
from .process_monitor import process_monitor, ProcessInfo


class UIUpdateType(Enum):
    """UI更新类型"""
    STATUS_CHANGE = "status_change"
    PROCESS_INFO = "process_info"
    ERROR_MESSAGE = "error_message"
    SERVICE_METRICS = "service_metrics"


class UIStatusSynchronizer:
    """UI状态同步器"""
    
    def __init__(self, service_manager: EnhancedServiceManager):
        """
        初始化UI状态同步器
        
        Args:
            service_manager: 服务状态管理器
        """
        self.service_manager = service_manager
        self.logger = logging.getLogger(__name__)
        
        # UI更新回调
        self._ui_callbacks: Dict[UIUpdateType, list] = {
            UIUpdateType.STATUS_CHANGE: [],
            UIUpdateType.PROCESS_INFO: [],
            UIUpdateType.ERROR_MESSAGE: [],
            UIUpdateType.SERVICE_METRICS: []
        }
        
        # 监控相关
        self._sync_thread: Optional[threading.Thread] = None
        self._sync_running = False
        self._sync_interval = 1.0  # UI同步间隔（秒）
        
        # 上次状态，用于检测变化
        self._last_state: Optional[ServiceState] = None
        self._last_process_info: Optional[ProcessInfo] = None
        
        # 注册服务状态变化回调
        self.service_manager.add_status_callback(self._on_service_state_change)
    
    def add_ui_callback(self, update_type: UIUpdateType, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        添加UI更新回调
        
        Args:
            update_type: 更新类型
            callback: 回调函数，接收更新数据字典
        """
        if callback not in self._ui_callbacks[update_type]:
            self._ui_callbacks[update_type].append(callback)
            self.logger.debug(f"Added UI callback for {update_type.value}")
    
    def remove_ui_callback(self, update_type: UIUpdateType, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        移除UI更新回调
        
        Args:
            update_type: 更新类型
            callback: 要移除的回调函数
        """
        if callback in self._ui_callbacks[update_type]:
            self._ui_callbacks[update_type].remove(callback)
            self.logger.debug(f"Removed UI callback for {update_type.value}")
    
    def _notify_ui_update(self, update_type: UIUpdateType, data: Dict[str, Any]) -> None:
        """
        通知UI更新
        
        Args:
            update_type: 更新类型
            data: 更新数据
        """
        callbacks = self._ui_callbacks.get(update_type, [])
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"UI callback error for {update_type.value}: {e}")
    
    def _on_service_state_change(self, state: ServiceState) -> None:
        """
        服务状态变化回调
        
        Args:
            state: 新的服务状态
        """
        # 检查状态是否真的发生了变化
        if self._last_state is None or self._has_state_changed(self._last_state, state):
            self._notify_ui_update(UIUpdateType.STATUS_CHANGE, {
                'status': state.status.value,
                'is_running': state.is_running,
                'start_time': state.start_time.isoformat() if state.start_time else None,
                'active_nodes_count': len(state.active_nodes),
                'allocated_ports_count': len(state.allocated_ports),
                'error_message': state.error_message,
                'last_update': state.last_update.isoformat()
            })
            
            self._last_state = state
            self.logger.info(f"UI notified of status change: {state.status.value}")
    
    def _has_state_changed(self, old_state: ServiceState, new_state: ServiceState) -> bool:
        """
        检查状态是否发生变化
        
        Args:
            old_state: 旧状态
            new_state: 新状态
            
        Returns:
            是否发生变化
        """
        return (
            old_state.status != new_state.status or
            old_state.is_running != new_state.is_running or
            old_state.error_message != new_state.error_message or
            len(old_state.active_nodes) != len(new_state.active_nodes) or
            len(old_state.allocated_ports) != len(new_state.allocated_ports)
        )
    
    def start_ui_sync(self) -> None:
        """启动UI同步"""
        if self._sync_running:
            return
        
        self._sync_running = True
        self._sync_thread = threading.Thread(target=self._ui_sync_loop, daemon=True)
        self._sync_thread.start()
        self.logger.info("UI synchronization started")
    
    def stop_ui_sync(self) -> None:
        """停止UI同步"""
        if not self._sync_running:
            return
        
        self._sync_running = False
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=3)
        self.logger.info("UI synchronization stopped")
    
    def _ui_sync_loop(self) -> None:
        """UI同步循环"""
        while self._sync_running:
            try:
                self._sync_process_info()
                self._sync_service_metrics()
                time.sleep(self._sync_interval)
            except Exception as e:
                self.logger.error(f"UI sync loop error: {e}")
                time.sleep(self._sync_interval)
    
    def _sync_process_info(self) -> None:
        """同步进程信息"""
        if not process_monitor:
            return
        
        current_state = self.service_manager.get_current_state()
        
        # 获取当前进程信息
        process_info = None
        if current_state.process_id:
            process_info = process_monitor.get_process_info(current_state.process_id)
        
        # 检查进程信息是否发生变化
        if self._has_process_info_changed(self._last_process_info, process_info):
            if process_info:
                self._notify_ui_update(UIUpdateType.PROCESS_INFO, {
                    'pid': process_info.pid,
                    'name': process_info.name,
                    'status': process_info.status.value,
                    'cpu_percent': process_info.cpu_percent,
                    'memory_percent': process_info.memory_percent,
                    'is_alive': process_info.is_alive(),
                    'create_time': process_info.create_time
                })
            else:
                # 进程不存在或process_id为None
                self._notify_ui_update(UIUpdateType.PROCESS_INFO, {
                    'pid': None,
                    'name': None,
                    'status': 'not_found',
                    'cpu_percent': 0.0,
                    'memory_percent': 0.0,
                    'is_alive': False,
                    'create_time': None
                })
            
            self._last_process_info = process_info
    
    def _has_process_info_changed(self, old_info: Optional[ProcessInfo], new_info: Optional[ProcessInfo]) -> bool:
        """
        检查进程信息是否发生变化
        
        Args:
            old_info: 旧进程信息
            new_info: 新进程信息
            
        Returns:
            是否发生变化
        """
        if old_info is None and new_info is None:
            return False
        
        if old_info is None or new_info is None:
            return True
        
        return (
            old_info.pid != new_info.pid or
            old_info.status != new_info.status or
            abs(old_info.cpu_percent - new_info.cpu_percent) > 1.0 or  # CPU变化超过1%
            abs(old_info.memory_percent - new_info.memory_percent) > 0.1  # 内存变化超过0.1%
        )
    
    def _sync_service_metrics(self) -> None:
        """同步服务指标"""
        if not process_monitor:
            return
        
        try:
            # 获取所有Xray进程
            xray_processes = process_monitor.find_processes_by_name("xray", exact_match=False)
            
            total_cpu = sum(proc.cpu_percent for proc in xray_processes)
            total_memory = sum(proc.memory_percent for proc in xray_processes)
            
            # 获取系统信息
            system_info = process_monitor.get_system_info()
            
            self._notify_ui_update(UIUpdateType.SERVICE_METRICS, {
                'xray_process_count': len(xray_processes),
                'total_cpu_percent': total_cpu,
                'total_memory_percent': total_memory,
                'system_cpu_percent': system_info.get('cpu_percent', 0),
                'system_memory_percent': system_info.get('memory', {}).get('percent', 0),
                'timestamp': time.time()
            })
            
        except Exception as e:
            self.logger.error(f"Error syncing service metrics: {e}")
    
    def force_ui_sync(self) -> None:
        """强制UI同步"""
        try:
            # 强制同步服务状态
            current_state = self.service_manager.get_current_state()
            self._on_service_state_change(current_state)
            
            # 强制同步进程信息
            self._sync_process_info()
            
            # 强制同步服务指标
            self._sync_service_metrics()
            
            self.logger.info("Forced UI synchronization completed")
            
        except Exception as e:
            self.logger.error(f"Error during forced UI sync: {e}")
    
    def get_current_ui_state(self) -> Dict[str, Any]:
        """
        获取当前UI状态
        
        Returns:
            当前UI状态字典
        """
        current_state = self.service_manager.get_current_state()
        
        ui_state = {
            'service_status': current_state.status.value,
            'is_running': current_state.is_running,
            'start_time': current_state.start_time.isoformat() if current_state.start_time else None,
            'config_path': current_state.config_path,
            'active_nodes': current_state.active_nodes.copy(),
            'allocated_ports': current_state.allocated_ports.copy(),
            'error_message': current_state.error_message,
            'last_update': current_state.last_update.isoformat(),
            'process_id': current_state.process_id
        }
        
        # 添加进程信息
        if current_state.process_id and process_monitor:
            process_info = process_monitor.get_process_info(current_state.process_id)
            if process_info:
                ui_state['process_info'] = {
                    'pid': process_info.pid,
                    'name': process_info.name,
                    'status': process_info.status.value,
                    'cpu_percent': process_info.cpu_percent,
                    'memory_percent': process_info.memory_percent,
                    'is_alive': process_info.is_alive()
                }
        
        return ui_state
    
    def cleanup(self) -> None:
        """清理资源"""
        self.stop_ui_sync()
        
        # 移除服务状态回调
        self.service_manager.remove_status_callback(self._on_service_state_change)
        
        # 清空所有回调
        for callback_list in self._ui_callbacks.values():
            callback_list.clear()


# 创建全局UI状态同步器的工厂函数
def create_ui_synchronizer(service_manager: EnhancedServiceManager) -> UIStatusSynchronizer:
    """
    创建UI状态同步器
    
    Args:
        service_manager: 服务状态管理器
        
    Returns:
        UI状态同步器实例
    """
    return UIStatusSynchronizer(service_manager)