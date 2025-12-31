"""
增强的服务状态管理器 - 管理服务状态持久化和同步
"""
import json
import os
import time
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from .xray_service import XrayService, ServiceStatus


class ServiceStateStatus(Enum):
    """服务状态枚举"""
    STOPPED = "stopped"
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ServiceState:
    """服务状态数据模型"""
    is_running: bool
    start_time: Optional[datetime]
    config_path: str
    active_nodes: List[str]  # 节点标识符列表
    allocated_ports: Dict[str, int]  # 节点到端口的映射
    last_update: datetime
    status: ServiceStateStatus = ServiceStateStatus.STOPPED
    error_message: str = ""
    process_id: Optional[int] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        data = asdict(self)
        # 处理datetime序列化
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        else:
            data['start_time'] = None
        data['last_update'] = self.last_update.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ServiceState':
        """从字典创建实例"""
        # 处理datetime反序列化
        start_time = None
        if data.get('start_time'):
            start_time = datetime.fromisoformat(data['start_time'])
        
        last_update = datetime.now()
        if data.get('last_update'):
            try:
                last_update = datetime.fromisoformat(data['last_update'])
            except:
                pass
        
        status = ServiceStateStatus.STOPPED
        if data.get('status'):
            try:
                status = ServiceStateStatus(data['status'])
            except:
                pass
        
        return cls(
            is_running=data.get('is_running', False),
            start_time=start_time,
            config_path=data.get('config_path', ''),
            active_nodes=data.get('active_nodes', []),
            allocated_ports=data.get('allocated_ports', {}),
            last_update=last_update,
            status=status,
            error_message=data.get('error_message', ''),
            process_id=data.get('process_id')
        )


class EnhancedServiceManager:
    """增强的服务状态管理器"""
    
    def __init__(self, state_file: str = "config/service_state.json", 
                 backup_file: str = "config/service_state.backup.json"):
        """
        初始化服务状态管理器
        
        Args:
            state_file: 状态文件路径
            backup_file: 备份文件路径
        """
        self.state_file = Path(state_file)
        self.backup_file = Path(backup_file)
        self.logger = logging.getLogger(__name__)
        
        # 当前状态
        self._current_state: Optional[ServiceState] = None
        self._xray_service: Optional[XrayService] = None
        
        # 监控相关
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        self._monitor_interval = 2.0  # 监控间隔（秒）
        
        # 状态变化回调
        self._status_callbacks: List[Callable[[ServiceState], None]] = []
        
        # 确保目录存在
        self._ensure_directories()
        
        # 加载初始状态
        self._load_state()
    
    def _ensure_directories(self) -> None:
        """确保配置目录存在"""
        for file_path in [self.state_file, self.backup_file]:
            directory = file_path.parent
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
    
    def set_xray_service(self, xray_service: XrayService) -> None:
        """
        设置Xray服务实例
        
        Args:
            xray_service: Xray服务实例
        """
        self._xray_service = xray_service
    
    def add_status_callback(self, callback: Callable[[ServiceState], None]) -> None:
        """
        添加状态变化回调
        
        Args:
            callback: 状态变化时调用的回调函数
        """
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[ServiceState], None]) -> None:
        """
        移除状态变化回调
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status_change(self, state: ServiceState) -> None:
        """
        通知状态变化
        
        Args:
            state: 新的状态
        """
        for callback in self._status_callbacks:
            try:
                callback(state)
            except Exception as e:
                self.logger.error(f"Status callback error: {e}")
    
    def save_service_state(self, state: ServiceState) -> bool:
        """
        保存服务状态
        
        Args:
            state: 要保存的状态
            
        Returns:
            是否保存成功
        """
        try:
            # 更新最后修改时间
            state.last_update = datetime.now()
            
            # 创建备份
            if self.state_file.exists():
                try:
                    self.state_file.replace(self.backup_file)
                except Exception as e:
                    self.logger.warning(f"Failed to create backup: {e}")
            
            # 保存状态
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._current_state = state
            self.logger.info(f"Service state saved: {state.status.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save service state: {e}")
            return False
    
    def restore_service_state(self) -> Optional[ServiceState]:
        """
        恢复服务状态
        
        Returns:
            恢复的状态，如果失败返回None
        """
        return self._load_state()
    
    def _load_state(self) -> Optional[ServiceState]:
        """
        加载状态文件
        
        Returns:
            加载的状态，如果失败返回None
        """
        # 尝试加载主状态文件
        state = self._load_state_from_file(self.state_file)
        
        if state is None:
            # 尝试从备份文件加载
            self.logger.warning("Main state file failed, trying backup")
            state = self._load_state_from_file(self.backup_file)
            
            if state is not None:
                # 从备份恢复成功，保存为主文件
                self.save_service_state(state)
        
        if state is not None:
            self._current_state = state
            self.logger.info(f"Service state loaded: {state.status.value}")
        else:
            # 创建默认状态
            self._current_state = ServiceState(
                is_running=False,
                start_time=None,
                config_path="",
                active_nodes=[],
                allocated_ports={},
                last_update=datetime.now(),
                status=ServiceStateStatus.STOPPED
            )
            self.logger.info("Created default service state")
        
        return self._current_state
    
    def _load_state_from_file(self, file_path: Path) -> Optional[ServiceState]:
        """
        从指定文件加载状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的状态，如果失败返回None
        """
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ServiceState.from_dict(data)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load state from {file_path}: {e}")
            return None
    
    def get_current_state(self) -> ServiceState:
        """
        获取当前状态
        
        Returns:
            当前状态
        """
        if self._current_state is None:
            self._load_state()
        return self._current_state
    
    def start_with_state_sync(self, config_path: str, active_nodes: List[str], 
                             allocated_ports: Dict[str, int]) -> bool:
        """
        启动服务并同步状态
        
        Args:
            config_path: 配置文件路径
            active_nodes: 活跃节点列表
            allocated_ports: 分配的端口映射
            
        Returns:
            是否启动成功
        """
        if self._xray_service is None:
            self.logger.error("Xray service not set")
            return False
        
        try:
            # 更新状态为启动中
            starting_state = ServiceState(
                is_running=False,
                start_time=None,
                config_path=config_path,
                active_nodes=active_nodes,
                allocated_ports=allocated_ports,
                last_update=datetime.now(),
                status=ServiceStateStatus.STARTING
            )
            self.save_service_state(starting_state)
            self._notify_status_change(starting_state)
            
            # 启动Xray服务
            success = self._xray_service.start(config_path)
            
            if success:
                # 启动成功，更新状态
                running_state = ServiceState(
                    is_running=True,
                    start_time=datetime.now(),
                    config_path=config_path,
                    active_nodes=active_nodes,
                    allocated_ports=allocated_ports,
                    last_update=datetime.now(),
                    status=ServiceStateStatus.RUNNING,
                    process_id=self._get_process_id()
                )
                self.save_service_state(running_state)
                self._notify_status_change(running_state)
                
                # 启动监控
                self.start_monitoring()
                
                self.logger.info("Service started successfully with state sync")
                return True
            else:
                # 启动失败，更新状态
                error_state = ServiceState(
                    is_running=False,
                    start_time=None,
                    config_path=config_path,
                    active_nodes=active_nodes,
                    allocated_ports=allocated_ports,
                    last_update=datetime.now(),
                    status=ServiceStateStatus.ERROR,
                    error_message=self._xray_service.error_message
                )
                self.save_service_state(error_state)
                self._notify_status_change(error_state)
                
                self.logger.error(f"Service start failed: {self._xray_service.error_message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start service with state sync: {e}")
            return False
    
    def stop_with_state_sync(self) -> bool:
        """
        停止服务并同步状态
        
        Returns:
            是否停止成功
        """
        if self._xray_service is None:
            self.logger.error("Xray service not set")
            return False
        
        try:
            # 停止监控
            self.stop_monitoring()
            
            # 更新状态为停止中
            current = self.get_current_state()
            stopping_state = ServiceState(
                is_running=current.is_running,
                start_time=current.start_time,
                config_path=current.config_path,
                active_nodes=current.active_nodes,
                allocated_ports=current.allocated_ports,
                last_update=datetime.now(),
                status=ServiceStateStatus.STOPPING
            )
            self.save_service_state(stopping_state)
            self._notify_status_change(stopping_state)
            
            # 停止Xray服务
            success = self._xray_service.stop()
            
            # 更新状态为已停止
            stopped_state = ServiceState(
                is_running=False,
                start_time=None,
                config_path=current.config_path,
                active_nodes=[],
                allocated_ports={},
                last_update=datetime.now(),
                status=ServiceStateStatus.STOPPED
            )
            self.save_service_state(stopped_state)
            self._notify_status_change(stopped_state)
            
            self.logger.info("Service stopped successfully with state sync")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to stop service with state sync: {e}")
            return False
    
    def start_monitoring(self) -> None:
        """启动进程状态监控"""
        if self._monitor_running:
            return
        
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Process monitoring started")
    
    def stop_monitoring(self) -> None:
        """停止进程状态监控"""
        if not self._monitor_running:
            return
        
        self._monitor_running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        self.logger.info("Process monitoring stopped")
    
    def _monitor_process(self) -> None:
        """监控进程状态的线程函数"""
        while self._monitor_running:
            try:
                self._check_and_sync_status()
                time.sleep(self._monitor_interval)
            except Exception as e:
                self.logger.error(f"Monitor process error: {e}")
                time.sleep(self._monitor_interval)
    
    def _check_and_sync_status(self) -> None:
        """检查并同步状态"""
        if self._xray_service is None:
            return
        
        current_state = self.get_current_state()
        actual_status = self._xray_service.status
        
        # 检查状态是否不一致
        needs_sync = False
        new_status = current_state.status
        new_is_running = current_state.is_running
        new_error_message = current_state.error_message
        
        if actual_status == ServiceStatus.RUNNING:
            if not current_state.is_running or current_state.status != ServiceStateStatus.RUNNING:
                needs_sync = True
                new_status = ServiceStateStatus.RUNNING
                new_is_running = True
                new_error_message = ""
        elif actual_status == ServiceStatus.STOPPED:
            if current_state.is_running or current_state.status not in [ServiceStateStatus.STOPPED, ServiceStateStatus.STOPPING]:
                needs_sync = True
                new_status = ServiceStateStatus.STOPPED
                new_is_running = False
                new_error_message = ""
        elif actual_status == ServiceStatus.ERROR:
            if current_state.status != ServiceStateStatus.ERROR:
                needs_sync = True
                new_status = ServiceStateStatus.ERROR
                new_is_running = False
                new_error_message = self._xray_service.error_message
        
        # 如果需要同步，更新状态
        if needs_sync:
            synced_state = ServiceState(
                is_running=new_is_running,
                start_time=current_state.start_time if new_is_running else None,
                config_path=current_state.config_path,
                active_nodes=current_state.active_nodes if new_is_running else [],
                allocated_ports=current_state.allocated_ports if new_is_running else {},
                last_update=datetime.now(),
                status=new_status,
                error_message=new_error_message,
                process_id=self._get_process_id() if new_is_running else None
            )
            
            self.save_service_state(synced_state)
            self._notify_status_change(synced_state)
            
            self.logger.info(f"Status synced: {current_state.status.value} -> {new_status.value}")
    
    def _get_process_id(self) -> Optional[int]:
        """
        获取Xray进程ID
        
        Returns:
            进程ID，如果获取失败返回None
        """
        if self._xray_service and hasattr(self._xray_service, '_process') and self._xray_service._process:
            return self._xray_service._process.pid
        return None
    
    def sync_ui_status(self) -> bool:
        """
        同步UI状态显示
        
        Returns:
            是否同步成功
        """
        try:
            self._check_and_sync_status()
            return True
        except Exception as e:
            self.logger.error(f"Failed to sync UI status: {e}")
            return False
    
    def monitor_process_status(self) -> ServiceStateStatus:
        """
        监控Xray进程的实际状态
        
        Returns:
            当前进程状态
        """
        if self._xray_service is None:
            return ServiceStateStatus.UNKNOWN
        
        actual_status = self._xray_service.status
        
        if actual_status == ServiceStatus.RUNNING:
            return ServiceStateStatus.RUNNING
        elif actual_status == ServiceStatus.STOPPED:
            return ServiceStateStatus.STOPPED
        elif actual_status == ServiceStatus.STARTING:
            return ServiceStateStatus.STARTING
        elif actual_status == ServiceStatus.ERROR:
            return ServiceStateStatus.ERROR
        else:
            return ServiceStateStatus.UNKNOWN
    
    def is_state_consistent(self) -> bool:
        """
        检查状态是否一致
        
        Returns:
            状态是否一致
        """
        if self._xray_service is None:
            return False
        
        current_state = self.get_current_state()
        actual_status = self.monitor_process_status()
        
        # 简化的一致性检查
        if current_state.status == ServiceStateStatus.RUNNING and actual_status == ServiceStateStatus.RUNNING:
            return True
        elif current_state.status == ServiceStateStatus.STOPPED and actual_status == ServiceStateStatus.STOPPED:
            return True
        elif current_state.status == ServiceStateStatus.ERROR and actual_status == ServiceStateStatus.ERROR:
            return True
        else:
            return False
    
    def force_sync(self) -> None:
        """强制同步状态"""
        self._check_and_sync_status()
    
    def cleanup(self) -> None:
        """清理资源"""
        self.stop_monitoring()
        
        # 如果服务正在运行，保存当前状态
        if self._current_state and self._current_state.is_running:
            self.save_service_state(self._current_state)


# 全局服务状态管理器实例
service_state_manager = EnhancedServiceManager()