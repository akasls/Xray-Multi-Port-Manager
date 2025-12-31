"""
UI集成管理器 - 集成所有新功能到用户界面
Feature: xray-protocol-enhancement, Requirements 1.1-1.8, 2.1-2.5, 4.1-4.6, 5.1-5.5
"""
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .node import Node
from .concurrent_latency_tester import ConcurrentLatencyTester, ConcurrentTestConfig, TestStrategy
from .system_adaptability_manager import SystemAdaptabilityManager, SystemEvent
from .enhanced_config_manager import EnhancedConfigManager
from .error_handler import handle_error, ErrorCategory
from .user_error_reporter import UserErrorReporter


class UIUpdateType(Enum):
    """UI更新类型"""
    NODE_LIST_REFRESH = "node_list_refresh"
    PROTOCOL_SUPPORT_UPDATE = "protocol_support_update"
    LATENCY_TEST_PROGRESS = "latency_test_progress"
    LATENCY_TEST_COMPLETE = "latency_test_complete"
    TUN_MODE_STATUS = "tun_mode_status"
    PORT_ALLOCATION_UPDATE = "port_allocation_update"
    SERVICE_STATUS_UPDATE = "service_status_update"
    ERROR_NOTIFICATION = "error_notification"
    SYSTEM_ADAPTATION = "system_adaptation"


@dataclass
class UIUpdateData:
    """UI更新数据"""
    update_type: UIUpdateType
    data: Any
    timestamp: datetime
    source: str = "ui_integration_manager"


@dataclass
class ProtocolDisplayInfo:
    """协议显示信息"""
    protocol: str
    display_name: str
    icon_name: str
    color: str
    description: str
    supported_features: List[str]


class UIIntegrationManager:
    """UI集成管理器"""
    
    def __init__(self):
        """初始化UI集成管理器"""
        self.logger = logging.getLogger(__name__)
        
        # 核心组件
        self.concurrent_tester = ConcurrentLatencyTester()
        self.adaptability_manager = SystemAdaptabilityManager()
        self.config_manager = EnhancedConfigManager()
        self.error_reporter: Optional[UserErrorReporter] = None
        
        # UI回调函数
        self._ui_callbacks: Dict[UIUpdateType, List[Callable[[UIUpdateData], None]]] = {}
        
        # 协议显示信息
        self._protocol_display_info = self._initialize_protocol_display_info()
        
        # 当前状态
        self._current_nodes: List[Node] = []
        self._latency_test_running = False
        self._service_running = False
        self._tun_mode_active = False
        
        # 注册系统适应性事件
        self._register_adaptability_events()
    
    def initialize_ui_components(self, parent_window=None):
        """初始化UI组件"""
        # 初始化错误报告器
        if parent_window:
            from .user_error_reporter import initialize_user_error_reporter
            self.error_reporter = initialize_user_error_reporter(parent_window)
        
        # 启动系统适应性监控
        self.adaptability_manager.start_monitoring()
        
        self.logger.info("UI integration manager initialized")
    
    def register_ui_callback(self, update_type: UIUpdateType, callback: Callable[[UIUpdateData], None]):
        """注册UI回调函数"""
        if update_type not in self._ui_callbacks:
            self._ui_callbacks[update_type] = []
        self._ui_callbacks[update_type].append(callback)
    
    def get_supported_protocols(self) -> List[ProtocolDisplayInfo]:
        """获取支持的协议列表"""
        return list(self._protocol_display_info.values())
    
    def get_protocol_display_info(self, protocol: str) -> Optional[ProtocolDisplayInfo]:
        """获取协议显示信息"""
        return self._protocol_display_info.get(protocol.lower())
    
    def update_node_list(self, nodes: List[Node]):
        """更新节点列表"""
        self._current_nodes = nodes.copy()
        
        # 统计协议类型
        protocol_stats = {}
        for node in nodes:
            protocol = node.protocol.lower()
            protocol_stats[protocol] = protocol_stats.get(protocol, 0) + 1
        
        update_data = UIUpdateData(
            update_type=UIUpdateType.NODE_LIST_REFRESH,
            data={
                'nodes': nodes,
                'total_count': len(nodes),
                'protocol_stats': protocol_stats
            },
            timestamp=datetime.now()
        )
        
        self._notify_ui_callbacks(update_data)
        
        # 更新协议支持状态
        supported_protocols = list(set(node.protocol.lower() for node in nodes))
        protocol_update_data = UIUpdateData(
            update_type=UIUpdateType.PROTOCOL_SUPPORT_UPDATE,
            data={
                'supported_protocols': supported_protocols,
                'protocol_info': [self._protocol_display_info.get(p) for p in supported_protocols]
            },
            timestamp=datetime.now()
        )
        
        self._notify_ui_callbacks(protocol_update_data)
    
    def start_latency_test(self, 
                          nodes: Optional[List[Node]] = None,
                          config: Optional[ConcurrentTestConfig] = None,
                          progress_callback: Optional[Callable[[int, int, float], None]] = None) -> bool:
        """启动延迟测试"""
        if self._latency_test_running:
            self.logger.warning("Latency test is already running")
            return False
        
        test_nodes = nodes or self._current_nodes
        if not test_nodes:
            self.logger.warning("No nodes to test")
            return False
        
        test_config = config or ConcurrentTestConfig(
            max_concurrent=10,
            timeout=5.0,
            strategy=TestStrategy.ASYNCIO,
            bypass_tun=True
        )
        
        self._latency_test_running = True
        
        def ui_progress_callback(completed: int, total: int, percentage: float):
            progress_data = UIUpdateData(
                update_type=UIUpdateType.LATENCY_TEST_PROGRESS,
                data={
                    'completed': completed,
                    'total': total,
                    'percentage': percentage,
                    'tun_mode_active': self._tun_mode_active
                },
                timestamp=datetime.now()
            )
            self._notify_ui_callbacks(progress_data)
            
            if progress_callback:
                progress_callback(completed, total, percentage)
        
        def test_complete_callback(result):
            self._latency_test_running = False
            
            # 更新节点延迟信息
            for test_result in result.results:
                for node in self._current_nodes:
                    if node.uuid == test_result.node_uuid:
                        node.latency = test_result.latency
                        break
            
            complete_data = UIUpdateData(
                update_type=UIUpdateType.LATENCY_TEST_COMPLETE,
                data={
                    'result': result,
                    'updated_nodes': self._current_nodes,
                    'test_duration': result.test_duration,
                    'success_rate': (result.completed_nodes - result.failed_nodes) / result.total_nodes * 100 if result.total_nodes > 0 else 0
                },
                timestamp=datetime.now()
            )
            self._notify_ui_callbacks(complete_data)
        
        # 在后台线程中执行测试
        import threading
        
        def run_test():
            try:
                result = self.concurrent_tester.test_nodes_batch(
                    nodes=test_nodes,
                    config=test_config,
                    progress_callback=ui_progress_callback
                )
                test_complete_callback(result)
                
            except Exception as e:
                self._latency_test_running = False
                handle_error(
                    category=ErrorCategory.LATENCY_TEST,
                    code="latency_test_ui_error",
                    message="UI延迟测试失败",
                    details=str(e),
                    context={'node_count': len(test_nodes)}
                )
        
        test_thread = threading.Thread(target=run_test, daemon=True)
        test_thread.start()
        
        return True
    
    def cancel_latency_test(self):
        """取消延迟测试"""
        if self._latency_test_running:
            self.concurrent_tester.cancel_test()
            self._latency_test_running = False
            
            cancel_data = UIUpdateData(
                update_type=UIUpdateType.LATENCY_TEST_COMPLETE,
                data={
                    'cancelled': True,
                    'message': '延迟测试已取消'
                },
                timestamp=datetime.now()
            )
            self._notify_ui_callbacks(cancel_data)
    
    def is_latency_test_running(self) -> bool:
        """是否正在进行延迟测试"""
        return self._latency_test_running
    
    def update_tun_mode_status(self, active: bool, interfaces: List[str] = None):
        """更新TUN模式状态"""
        self._tun_mode_active = active
        
        status_data = UIUpdateData(
            update_type=UIUpdateType.TUN_MODE_STATUS,
            data={
                'active': active,
                'interfaces': interfaces or [],
                'impact_message': '延迟测试将使用直连模式绕过TUN代理' if active else '延迟测试将使用标准连接模式'
            },
            timestamp=datetime.now()
        )
        
        self._notify_ui_callbacks(status_data)
    
    def update_port_allocation(self, port_allocations: Dict[str, int]):
        """更新端口分配"""
        allocation_data = UIUpdateData(
            update_type=UIUpdateType.PORT_ALLOCATION_UPDATE,
            data={
                'allocations': port_allocations,
                'total_ports': len(port_allocations),
                'port_range': f"{min(port_allocations.values())}-{max(port_allocations.values())}" if port_allocations else "N/A"
            },
            timestamp=datetime.now()
        )
        
        self._notify_ui_callbacks(allocation_data)
    
    def update_service_status(self, running: bool, details: Optional[Dict[str, Any]] = None):
        """更新服务状态"""
        self._service_running = running
        
        status_data = UIUpdateData(
            update_type=UIUpdateType.SERVICE_STATUS_UPDATE,
            data={
                'running': running,
                'details': details or {},
                'status_text': '服务运行中' if running else '服务已停止'
            },
            timestamp=datetime.now()
        )
        
        self._notify_ui_callbacks(status_data)
    
    def show_error_notification(self, error_message: str, error_details: Optional[str] = None):
        """显示错误通知"""
        error_data = UIUpdateData(
            update_type=UIUpdateType.ERROR_NOTIFICATION,
            data={
                'message': error_message,
                'details': error_details,
                'severity': 'error'
            },
            timestamp=datetime.now()
        )
        
        self._notify_ui_callbacks(error_data)
    
    def get_system_status_summary(self) -> Dict[str, Any]:
        """获取系统状态摘要"""
        adaptability_stats = self.adaptability_manager.get_statistics()
        latency_stats = self.concurrent_tester.get_statistics()
        
        return {
            'nodes_loaded': len(self._current_nodes),
            'protocols_supported': len(self._protocol_display_info),
            'latency_test_running': self._latency_test_running,
            'service_running': self._service_running,
            'tun_mode_active': self._tun_mode_active,
            'system_healthy': self.adaptability_manager.get_current_state().is_healthy(),
            'adaptability_stats': adaptability_stats,
            'latency_stats': latency_stats
        }
    
    def cleanup(self):
        """清理资源"""
        self.adaptability_manager.stop_monitoring()
        self.concurrent_tester.cancel_test()
        self.logger.info("UI integration manager cleaned up")
    
    def _initialize_protocol_display_info(self) -> Dict[str, ProtocolDisplayInfo]:
        """初始化协议显示信息"""
        return {
            'vmess': ProtocolDisplayInfo(
                protocol='vmess',
                display_name='VMess',
                icon_name='vmess_icon',
                color='#4CAF50',
                description='V2Ray 原生协议，支持多种传输方式',
                supported_features=['TCP', 'WebSocket', 'HTTP/2', 'gRPC', 'TLS']
            ),
            'vless': ProtocolDisplayInfo(
                protocol='vless',
                display_name='VLESS',
                icon_name='vless_icon',
                color='#2196F3',
                description='轻量级协议，性能优异',
                supported_features=['TCP', 'WebSocket', 'HTTP/2', 'gRPC', 'TLS', 'XTLS']
            ),
            'shadowsocks': ProtocolDisplayInfo(
                protocol='shadowsocks',
                display_name='Shadowsocks',
                icon_name='ss_icon',
                color='#FF9800',
                description='经典代理协议，简单高效',
                supported_features=['AEAD加密', '流加密', '插件支持']
            ),
            'trojan': ProtocolDisplayInfo(
                protocol='trojan',
                display_name='Trojan',
                icon_name='trojan_icon',
                color='#9C27B0',
                description='伪装成HTTPS流量的代理协议',
                supported_features=['TLS', 'WebSocket', '流量伪装']
            ),
            'wireguard': ProtocolDisplayInfo(
                protocol='wireguard',
                display_name='WireGuard',
                icon_name='wg_icon',
                color='#607D8B',
                description='现代VPN协议，速度快延迟低',
                supported_features=['内核级加速', '密钥交换', 'UDP传输']
            ),
            'hysteria2': ProtocolDisplayInfo(
                protocol='hysteria2',
                display_name='Hysteria2',
                icon_name='hy2_icon',
                color='#E91E63',
                description='基于QUIC的高性能代理协议',
                supported_features=['QUIC', '拥塞控制', '带宽控制', '混淆']
            ),
            'socks': ProtocolDisplayInfo(
                protocol='socks',
                display_name='SOCKS',
                icon_name='socks_icon',
                color='#795548',
                description='通用代理协议',
                supported_features=['SOCKS4', 'SOCKS5', '认证支持']
            ),
            'http': ProtocolDisplayInfo(
                protocol='http',
                display_name='HTTP',
                icon_name='http_icon',
                color='#009688',
                description='HTTP代理协议',
                supported_features=['HTTP/1.1', 'CONNECT方法', '认证支持']
            )
        }
    
    def _register_adaptability_events(self):
        """注册系统适应性事件"""
        def on_system_event(state):
            adaptation_data = UIUpdateData(
                update_type=UIUpdateType.SYSTEM_ADAPTATION,
                data={
                    'system_state': state,
                    'is_healthy': state.is_healthy(),
                    'adaptations_triggered': True
                },
                timestamp=datetime.now()
            )
            self._notify_ui_callbacks(adaptation_data)
        
        # 注册关键系统事件
        for event_type in [
            SystemEvent.NETWORK_CONNECTIVITY_LOST,
            SystemEvent.NETWORK_CONNECTIVITY_RESTORED,
            SystemEvent.TUN_MODE_ACTIVATED,
            SystemEvent.TUN_MODE_DEACTIVATED,
            SystemEvent.XRAY_PROCESS_DIED
        ]:
            self.adaptability_manager.register_event_callback(event_type, on_system_event)
    
    def _notify_ui_callbacks(self, update_data: UIUpdateData):
        """通知UI回调函数"""
        callbacks = self._ui_callbacks.get(update_data.update_type, [])
        for callback in callbacks:
            try:
                callback(update_data)
            except Exception as e:
                self.logger.error(f"Error in UI callback for {update_data.update_type.value}: {e}")


# 全局UI集成管理器实例
ui_integration_manager = UIIntegrationManager()