"""
增强的延迟测试功能 - 支持TUN模式检测和直连测试
"""
import socket
import time
import threading
import subprocess
import platform
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from .network_manager import network_manager, NetworkInterface
from .node import Node


@dataclass
class LatencyTestResult:
    """延迟测试结果"""
    node_uuid: str
    latency: Optional[int]  # ms，None表示未测试，-1表示超时
    error: Optional[str] = None
    test_method: str = "direct"  # "direct", "proxy", "bypass"
    interface_used: Optional[str] = None


class LatencyTester:
    """增强的延迟测试器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.default_timeout = 5.0  # 默认超时时间（秒）
        self.test_target = "8.8.8.8"  # 默认测试目标
        self.test_port = 53  # 默认测试端口
        
    def test_node_latency(
        self, 
        node: Node, 
        timeout: float = None,
        bypass_tun: bool = True,
        callback: Optional[Callable[[LatencyTestResult], None]] = None
    ) -> LatencyTestResult:
        """
        测试单个节点延迟
        
        Args:
            node: 要测试的节点
            timeout: 超时时间（秒）
            bypass_tun: 是否绕过TUN模式
            callback: 结果回调函数
            
        Returns:
            延迟测试结果
        """
        if timeout is None:
            timeout = self.default_timeout
        
        result = LatencyTestResult(
            node_uuid=node.uuid,
            latency=None,
            test_method="direct"
        )
        
        try:
            # 检测TUN模式
            tun_active = network_manager.is_tun_mode_active(refresh=True)
            
            if tun_active and bypass_tun:
                # TUN模式下使用直连测试
                result = self._test_direct_connection(node, timeout)
                result.test_method = "bypass"
            else:
                # 普通连接测试
                result = self._test_normal_connection(node, timeout)
                result.test_method = "direct"
            
            if callback:
                callback(result)
                
        except Exception as e:
            result.error = str(e)
            result.latency = -1
            
            if callback:
                callback(result)
        
        return result
    
    def test_multiple_nodes(
        self,
        nodes: List[Node],
        timeout: float = None,
        bypass_tun: bool = True,
        max_concurrent: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        result_callback: Optional[Callable[[LatencyTestResult], None]] = None
    ) -> List[LatencyTestResult]:
        """
        并发测试多个节点延迟
        
        Args:
            nodes: 要测试的节点列表
            timeout: 超时时间（秒）
            bypass_tun: 是否绕过TUN模式
            max_concurrent: 最大并发数
            progress_callback: 进度回调函数 (completed, total)
            result_callback: 单个结果回调函数
            
        Returns:
            延迟测试结果列表
        """
        if timeout is None:
            timeout = self.default_timeout
        
        results = []
        completed = 0
        lock = threading.Lock()
        
        def test_worker(node: Node) -> None:
            nonlocal completed
            
            result = self.test_node_latency(node, timeout, bypass_tun)
            
            with lock:
                results.append(result)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, len(nodes))
                
                if result_callback:
                    result_callback(result)
        
        # 创建线程池
        threads = []
        semaphore = threading.Semaphore(max_concurrent)
        
        def thread_wrapper(node: Node) -> None:
            with semaphore:
                test_worker(node)
        
        # 启动所有测试线程
        for node in nodes:
            thread = threading.Thread(target=thread_wrapper, args=(node,))
            thread.start()
            threads.append(thread)
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 按原始顺序排序结果
        node_uuid_to_index = {node.uuid: i for i, node in enumerate(nodes)}
        results.sort(key=lambda r: node_uuid_to_index.get(r.node_uuid, len(nodes)))
        
        return results
    
    def _test_direct_connection(self, node: Node, timeout: float) -> LatencyTestResult:
        """
        直连测试（绕过系统代理）
        
        Args:
            node: 要测试的节点
            timeout: 超时时间
            
        Returns:
            测试结果
        """
        result = LatencyTestResult(
            node_uuid=node.uuid,
            latency=None,
            test_method="bypass"
        )
        
        try:
            # 获取物理网络接口
            physical_interfaces = network_manager.get_physical_interfaces(refresh=False)
            default_interface = network_manager.get_default_interface(refresh=False)
            
            # 选择要使用的接口
            interface_to_use = None
            if default_interface and default_interface.type == 'physical':
                interface_to_use = default_interface
            elif physical_interfaces:
                # 选择第一个活跃的物理接口
                for iface in physical_interfaces:
                    if iface.status == 'up' and iface.ip_addresses:
                        interface_to_use = iface
                        break
            
            if interface_to_use:
                result.interface_used = interface_to_use.name
                
                # 使用指定接口进行连接测试
                latency = self._test_connection_with_interface(
                    node.address, 
                    node.port, 
                    timeout,
                    interface_to_use
                )
                result.latency = latency
            else:
                # 回退到普通连接测试
                result.latency = self._test_tcp_connection(node.address, node.port, timeout)
                
        except Exception as e:
            result.error = str(e)
            result.latency = -1
        
        return result
    
    def _test_normal_connection(self, node: Node, timeout: float) -> LatencyTestResult:
        """
        普通连接测试
        
        Args:
            node: 要测试的节点
            timeout: 超时时间
            
        Returns:
            测试结果
        """
        result = LatencyTestResult(
            node_uuid=node.uuid,
            latency=None,
            test_method="direct"
        )
        
        try:
            result.latency = self._test_tcp_connection(node.address, node.port, timeout)
        except Exception as e:
            result.error = str(e)
            result.latency = -1
        
        return result
    
    def _test_connection_with_interface(
        self, 
        address: str, 
        port: int, 
        timeout: float,
        interface: NetworkInterface
    ) -> Optional[int]:
        """
        使用指定网络接口进行连接测试
        
        Args:
            address: 目标地址
            port: 目标端口
            timeout: 超时时间
            interface: 网络接口
            
        Returns:
            延迟（毫秒），失败返回-1
        """
        try:
            # 在Windows上，我们使用绑定到特定IP的方法
            if self.system == 'windows' and interface.ip_addresses:
                source_ip = interface.ip_addresses[0]
                return self._test_tcp_connection_with_source(address, port, timeout, source_ip)
            else:
                # 在Linux/macOS上，可以使用SO_BINDTODEVICE（需要root权限）
                # 这里简化为普通连接测试
                return self._test_tcp_connection(address, port, timeout)
                
        except Exception:
            return -1
    
    def _test_tcp_connection_with_source(
        self, 
        address: str, 
        port: int, 
        timeout: float,
        source_ip: str
    ) -> Optional[int]:
        """
        使用指定源IP进行TCP连接测试
        
        Args:
            address: 目标地址
            port: 目标端口
            timeout: 超时时间
            source_ip: 源IP地址
            
        Returns:
            延迟（毫秒），失败返回-1
        """
        try:
            start_time = time.time()
            
            # 创建socket并绑定到指定IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                sock.bind((source_ip, 0))
                sock.connect((address, port))
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                return latency_ms
                
            finally:
                sock.close()
                
        except socket.timeout:
            return -1
        except Exception:
            return -1
    
    def _test_tcp_connection(self, address: str, port: int, timeout: float) -> Optional[int]:
        """
        普通TCP连接测试
        
        Args:
            address: 目标地址
            port: 目标端口
            timeout: 超时时间
            
        Returns:
            延迟（毫秒），失败返回-1
        """
        try:
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                sock.connect((address, port))
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                return latency_ms
                
            finally:
                sock.close()
                
        except socket.timeout:
            return -1
        except Exception:
            return -1
    
    def get_tun_mode_status(self) -> Dict[str, any]:
        """
        获取TUN模式状态信息
        
        Returns:
            TUN模式状态字典
        """
        tun_active = network_manager.is_tun_mode_active(refresh=True)
        active_tun_interfaces = network_manager.get_active_tun_interfaces()
        all_virtual_interfaces = network_manager.get_virtual_interfaces()
        
        return {
            'tun_mode_active': tun_active,
            'active_tun_interfaces': [
                {
                    'name': iface.name,
                    'display_name': iface.display_name,
                    'ip_addresses': iface.ip_addresses
                }
                for iface in active_tun_interfaces
            ],
            'all_virtual_interfaces': [
                {
                    'name': iface.name,
                    'display_name': iface.display_name,
                    'type': iface.type,
                    'status': iface.status,
                    'ip_addresses': iface.ip_addresses
                }
                for iface in all_virtual_interfaces
            ]
        }


# 全局延迟测试器实例
latency_tester = LatencyTester()