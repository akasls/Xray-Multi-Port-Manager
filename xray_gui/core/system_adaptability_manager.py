"""
系统适应性管理器 - 处理网络环境变化和异常情况的自动适应
Feature: xray-protocol-enhancement, Requirements 8.4, 8.5
"""
import threading
import time
import logging
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import psutil
import socket

from .network_manager import network_manager, NetworkInterface
from .error_handler import handle_error, ErrorCategory, ErrorSeverity
from .node import Node


class SystemEvent(Enum):
    """系统事件类型"""
    NETWORK_INTERFACE_CHANGED = "network_interface_changed"
    NETWORK_CONNECTIVITY_LOST = "network_connectivity_lost"
    NETWORK_CONNECTIVITY_RESTORED = "network_connectivity_restored"
    TUN_MODE_ACTIVATED = "tun_mode_activated"
    TUN_MODE_DEACTIVATED = "tun_mode_deactivated"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    PROXY_CONNECTION_FAILED = "proxy_connection_failed"
    HIGH_LATENCY_DETECTED = "high_latency_detected"
    SYSTEM_RESOURCE_LOW = "system_resource_low"
    XRAY_PROCESS_DIED = "xray_process_died"


@dataclass
class SystemState:
    """系统状态"""
    network_interfaces: List[NetworkInterface] = field(default_factory=list)
    active_tun_interfaces: List[NetworkInterface] = field(default_factory=list)
    default_interface: Optional[NetworkInterface] = None
    internet_connectivity: bool = True
    dns_working: bool = True
    proxy_working: bool = True
    average_latency: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    xray_process_running: bool = False
    last_updated: datetime = field(default_factory=datetime.now)
    
    def is_healthy(self) -> bool:
        """系统是否健康"""
        return (
            self.internet_connectivity and
            self.dns_working and
            self.cpu_usage < 90.0 and
            self.memory_usage < 90.0
        )


@dataclass
class AdaptationRule:
    """适应规则"""
    event_type: SystemEvent
    condition: Callable[['SystemState'], bool]
    action: Callable[['SystemState'], None]
    cooldown_seconds: int = 30  # 冷却时间，防止频繁触发
    priority: int = 1  # 优先级，数字越小优先级越高
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    
    def can_trigger(self) -> bool:
        """是否可以触发"""
        if not self.enabled:
            return False
        
        if self.last_triggered is None:
            return True
        
        return (datetime.now() - self.last_triggered).total_seconds() >= self.cooldown_seconds
    
    def trigger(self, state: SystemState):
        """触发规则"""
        if self.can_trigger() and self.condition(state):
            try:
                self.action(state)
                self.last_triggered = datetime.now()
            except Exception as e:
                handle_error(
                    category=ErrorCategory.SYSTEM_PERMISSION,
                    code="adaptation_rule_error",
                    message=f"适应规则执行失败: {self.event_type.value}",
                    details=str(e)
                )


class SystemAdaptabilityManager:
    """系统适应性管理器"""
    
    def __init__(self):
        """初始化系统适应性管理器"""
        self.logger = logging.getLogger(__name__)
        
        # 系统状态
        self.current_state = SystemState()
        self.previous_state = SystemState()
        
        # 监控线程
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._monitoring_interval = 5.0  # 监控间隔（秒）
        
        # 事件回调
        self._event_callbacks: Dict[SystemEvent, List[Callable[[SystemState], None]]] = {}
        
        # 适应规则
        self._adaptation_rules: List[AdaptationRule] = []
        
        # 状态锁
        self._state_lock = threading.Lock()
        
        # 初始化默认适应规则
        self._initialize_default_rules()
        
        # 统计信息
        self._events_triggered = 0
        self._rules_executed = 0
        self._adaptations_successful = 0
        self._adaptations_failed = 0
    
    def start_monitoring(self):
        """开始系统监控"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self.logger.warning("System monitoring is already running")
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        self.logger.info("System adaptability monitoring started")
    
    def stop_monitoring(self):
        """停止系统监控"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=10)
            
            if self._monitoring_thread.is_alive():
                self.logger.warning("Failed to stop monitoring thread gracefully")
        
        self.logger.info("System adaptability monitoring stopped")
    
    def register_event_callback(self, event_type: SystemEvent, callback: Callable[[SystemState], None]):
        """注册事件回调"""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)
    
    def add_adaptation_rule(self, rule: AdaptationRule):
        """添加适应规则"""
        self._adaptation_rules.append(rule)
        # 按优先级排序
        self._adaptation_rules.sort(key=lambda r: r.priority)
    
    def remove_adaptation_rule(self, event_type: SystemEvent):
        """移除适应规则"""
        self._adaptation_rules = [r for r in self._adaptation_rules if r.event_type != event_type]
    
    def get_current_state(self) -> SystemState:
        """获取当前系统状态"""
        with self._state_lock:
            return self.current_state
    
    def force_state_update(self):
        """强制更新系统状态"""
        self._update_system_state()
    
    def get_statistics(self) -> Dict[str, any]:
        """获取统计信息"""
        return {
            'events_triggered': self._events_triggered,
            'rules_executed': self._rules_executed,
            'adaptations_successful': self._adaptations_successful,
            'adaptations_failed': self._adaptations_failed,
            'success_rate': (
                self._adaptations_successful / max(self._rules_executed, 1) * 100
            ),
            'monitoring_active': self._monitoring_thread and self._monitoring_thread.is_alive(),
            'system_healthy': self.current_state.is_healthy(),
            'active_rules': len([r for r in self._adaptation_rules if r.enabled])
        }
    
    def _monitoring_loop(self):
        """监控循环"""
        while not self._stop_monitoring.wait(self._monitoring_interval):
            try:
                self._update_system_state()
                self._detect_changes()
                self._apply_adaptation_rules()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                handle_error(
                    category=ErrorCategory.SYSTEM_PERMISSION,
                    code="monitoring_loop_error",
                    message="系统监控循环出错",
                    details=str(e)
                )
    
    def _update_system_state(self):
        """更新系统状态"""
        with self._state_lock:
            # 保存之前的状态
            self.previous_state = SystemState(
                network_interfaces=self.current_state.network_interfaces.copy(),
                active_tun_interfaces=self.current_state.active_tun_interfaces.copy(),
                default_interface=self.current_state.default_interface,
                internet_connectivity=self.current_state.internet_connectivity,
                dns_working=self.current_state.dns_working,
                proxy_working=self.current_state.proxy_working,
                average_latency=self.current_state.average_latency,
                cpu_usage=self.current_state.cpu_usage,
                memory_usage=self.current_state.memory_usage,
                xray_process_running=self.current_state.xray_process_running,
                last_updated=self.current_state.last_updated
            )
            
            # 更新当前状态
            try:
                # 网络接口信息
                self.current_state.network_interfaces = network_manager.get_all_interfaces(refresh=True)
                self.current_state.active_tun_interfaces = network_manager.get_active_tun_interfaces()
                self.current_state.default_interface = network_manager.get_default_interface()
                
                # 网络连通性
                self.current_state.internet_connectivity = self._check_internet_connectivity()
                self.current_state.dns_working = self._check_dns_resolution()
                
                # 系统资源
                self.current_state.cpu_usage = psutil.cpu_percent(interval=1)
                self.current_state.memory_usage = psutil.virtual_memory().percent
                
                # Xray进程状态
                self.current_state.xray_process_running = self._check_xray_process()
                
                self.current_state.last_updated = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Failed to update system state: {e}")
    
    def _detect_changes(self):
        """检测系统变化"""
        try:
            # 检测网络接口变化
            if self._interfaces_changed():
                self._trigger_event(SystemEvent.NETWORK_INTERFACE_CHANGED)
            
            # 检测网络连通性变化
            if self.previous_state.internet_connectivity and not self.current_state.internet_connectivity:
                self._trigger_event(SystemEvent.NETWORK_CONNECTIVITY_LOST)
            elif not self.previous_state.internet_connectivity and self.current_state.internet_connectivity:
                self._trigger_event(SystemEvent.NETWORK_CONNECTIVITY_RESTORED)
            
            # 检测TUN模式变化
            prev_tun_active = len(self.previous_state.active_tun_interfaces) > 0
            curr_tun_active = len(self.current_state.active_tun_interfaces) > 0
            
            if not prev_tun_active and curr_tun_active:
                self._trigger_event(SystemEvent.TUN_MODE_ACTIVATED)
            elif prev_tun_active and not curr_tun_active:
                self._trigger_event(SystemEvent.TUN_MODE_DEACTIVATED)
            
            # 检测DNS问题
            if self.previous_state.dns_working and not self.current_state.dns_working:
                self._trigger_event(SystemEvent.DNS_RESOLUTION_FAILED)
            
            # 检测系统资源问题
            if (self.current_state.cpu_usage > 90 or self.current_state.memory_usage > 90):
                self._trigger_event(SystemEvent.SYSTEM_RESOURCE_LOW)
            
            # 检测Xray进程状态
            if self.previous_state.xray_process_running and not self.current_state.xray_process_running:
                self._trigger_event(SystemEvent.XRAY_PROCESS_DIED)
                
        except Exception as e:
            self.logger.error(f"Error detecting changes: {e}")
    
    def _apply_adaptation_rules(self):
        """应用适应规则"""
        for rule in self._adaptation_rules:
            try:
                if rule.can_trigger() and rule.condition(self.current_state):
                    rule.trigger(self.current_state)
                    self._rules_executed += 1
                    self._adaptations_successful += 1
                    
            except Exception as e:
                self._adaptations_failed += 1
                self.logger.error(f"Failed to apply adaptation rule {rule.event_type.value}: {e}")
    
    def _trigger_event(self, event_type: SystemEvent):
        """触发系统事件"""
        self._events_triggered += 1
        
        self.logger.info(f"System event triggered: {event_type.value}")
        
        # 调用事件回调
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(self.current_state)
            except Exception as e:
                self.logger.error(f"Error in event callback for {event_type.value}: {e}")
    
    def _interfaces_changed(self) -> bool:
        """检测网络接口是否发生变化"""
        prev_names = {iface.name for iface in self.previous_state.network_interfaces}
        curr_names = {iface.name for iface in self.current_state.network_interfaces}
        
        return prev_names != curr_names
    
    def _check_internet_connectivity(self) -> bool:
        """检查互联网连通性"""
        try:
            # 尝试连接到多个知名DNS服务器
            test_hosts = [
                ("8.8.8.8", 53),      # Google DNS
                ("1.1.1.1", 53),      # Cloudflare DNS
                ("208.67.222.222", 53) # OpenDNS
            ]
            
            for host, port in test_hosts:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    
                    if result == 0:
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _check_dns_resolution(self) -> bool:
        """检查DNS解析"""
        try:
            # 尝试解析几个知名域名
            test_domains = ["google.com", "cloudflare.com", "github.com"]
            
            for domain in test_domains:
                try:
                    socket.gethostbyname(domain)
                    return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _check_xray_process(self) -> bool:
        """检查Xray进程是否运行"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'xray' in proc.info['name'].lower():
                        return True
                    
                    if proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline']).lower()
                        if 'xray' in cmdline:
                            return True
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _initialize_default_rules(self):
        """初始化默认适应规则"""
        
        # 网络连接丢失时的适应规则
        def handle_connectivity_lost(state: SystemState):
            self.logger.warning("Internet connectivity lost, attempting recovery...")
            # 可以在这里添加重连逻辑
            handle_error(
                category=ErrorCategory.NETWORK_CONNECTION,
                code="network_connection_no_internet",
                message="网络连接丢失",
                details="系统检测到互联网连接中断"
            )
        
        self.add_adaptation_rule(AdaptationRule(
            event_type=SystemEvent.NETWORK_CONNECTIVITY_LOST,
            condition=lambda state: not state.internet_connectivity,
            action=handle_connectivity_lost,
            cooldown_seconds=60,
            priority=1
        ))
        
        # TUN模式激活时的适应规则
        def handle_tun_activated(state: SystemState):
            self.logger.info("TUN mode activated, adjusting latency test strategy...")
            # 通知延迟测试器使用绕过模式
            
        self.add_adaptation_rule(AdaptationRule(
            event_type=SystemEvent.TUN_MODE_ACTIVATED,
            condition=lambda state: len(state.active_tun_interfaces) > 0,
            action=handle_tun_activated,
            cooldown_seconds=30,
            priority=2
        ))
        
        # DNS解析失败时的适应规则
        def handle_dns_failed(state: SystemState):
            self.logger.warning("DNS resolution failed, suggesting DNS server change...")
            handle_error(
                category=ErrorCategory.NETWORK_CONNECTION,
                code="network_connection_dns_failed",
                message="DNS解析失败",
                details="系统检测到DNS解析问题，建议更换DNS服务器"
            )
        
        self.add_adaptation_rule(AdaptationRule(
            event_type=SystemEvent.DNS_RESOLUTION_FAILED,
            condition=lambda state: not state.dns_working,
            action=handle_dns_failed,
            cooldown_seconds=120,
            priority=2
        ))
        
        # 系统资源不足时的适应规则
        def handle_low_resources(state: SystemState):
            self.logger.warning(f"System resources low - CPU: {state.cpu_usage}%, Memory: {state.memory_usage}%")
            handle_error(
                category=ErrorCategory.SYSTEM_PERMISSION,
                code="system_resource_low",
                message="系统资源不足",
                details=f"CPU使用率: {state.cpu_usage}%, 内存使用率: {state.memory_usage}%"
            )
        
        self.add_adaptation_rule(AdaptationRule(
            event_type=SystemEvent.SYSTEM_RESOURCE_LOW,
            condition=lambda state: state.cpu_usage > 90 or state.memory_usage > 90,
            action=handle_low_resources,
            cooldown_seconds=300,  # 5分钟冷却
            priority=3
        ))
        
        # Xray进程死亡时的适应规则
        def handle_xray_died(state: SystemState):
            self.logger.error("Xray process died unexpectedly")
            handle_error(
                category=ErrorCategory.XRAY_SERVICE,
                code="xray_service_process_died",
                message="Xray进程意外终止",
                details="系统检测到Xray进程已停止运行"
            )
        
        self.add_adaptation_rule(AdaptationRule(
            event_type=SystemEvent.XRAY_PROCESS_DIED,
            condition=lambda state: not state.xray_process_running,
            action=handle_xray_died,
            cooldown_seconds=60,
            priority=1
        ))


# 全局系统适应性管理器实例
system_adaptability_manager = SystemAdaptabilityManager()