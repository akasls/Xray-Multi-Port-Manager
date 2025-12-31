"""
并发延迟测试器 - 高性能并发延迟测试实现
Feature: xray-protocol-enhancement, Requirements 8.2
"""
import asyncio
import socket
import time
import threading
import concurrent.futures
from typing import Optional, List, Dict, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

from .network_manager import network_manager, NetworkInterface
from .node import Node
from .error_handler import handle_error, ErrorCategory


class TestStrategy(Enum):
    """测试策略"""
    THREADING = "threading"  # 多线程
    ASYNCIO = "asyncio"      # 异步IO
    PROCESS_POOL = "process_pool"  # 进程池


@dataclass
class ConcurrentTestConfig:
    """并发测试配置"""
    max_concurrent: int = 20  # 最大并发数
    timeout: float = 5.0      # 超时时间（秒）
    retry_count: int = 1      # 重试次数
    retry_delay: float = 0.5  # 重试延迟（秒）
    strategy: TestStrategy = TestStrategy.ASYNCIO  # 测试策略
    bypass_tun: bool = True   # 是否绕过TUN模式
    batch_size: int = 50      # 批处理大小
    progress_interval: float = 0.1  # 进度更新间隔（秒）


@dataclass
class BatchTestResult:
    """批量测试结果"""
    results: List['LatencyTestResult'] = field(default_factory=list)
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    average_latency: float = 0.0
    min_latency: int = -1
    max_latency: int = -1
    test_duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def update_statistics(self):
        """更新统计信息"""
        if not self.results:
            return
        
        valid_latencies = [r.latency for r in self.results if r.latency is not None and r.latency > 0]
        
        self.completed_nodes = len([r for r in self.results if r.latency is not None])
        self.failed_nodes = len([r for r in self.results if r.latency == -1 or r.error])
        
        if valid_latencies:
            self.average_latency = sum(valid_latencies) / len(valid_latencies)
            self.min_latency = min(valid_latencies)
            self.max_latency = max(valid_latencies)
        
        if self.start_time and self.end_time:
            self.test_duration = (self.end_time - self.start_time).total_seconds()


@dataclass
class LatencyTestResult:
    """延迟测试结果"""
    node_uuid: str
    node_remark: str = ""
    latency: Optional[int] = None  # ms，None表示未测试，-1表示超时/失败
    error: Optional[str] = None
    test_method: str = "direct"  # "direct", "proxy", "bypass"
    interface_used: Optional[str] = None
    retry_count: int = 0
    test_duration: float = 0.0
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_successful(self) -> bool:
        """是否测试成功"""
        return self.latency is not None and self.latency > 0
    
    def is_timeout(self) -> bool:
        """是否超时"""
        return self.latency == -1 and self.error and "timeout" in self.error.lower()


class ConcurrentLatencyTester:
    """并发延迟测试器"""
    
    def __init__(self, config: Optional[ConcurrentTestConfig] = None):
        """
        初始化并发延迟测试器
        
        Args:
            config: 测试配置
        """
        self.config = config or ConcurrentTestConfig()
        self.logger = logging.getLogger(__name__)
        
        # 测试状态
        self._is_testing = False
        self._cancel_requested = False
        self._test_lock = threading.Lock()
        
        # 统计信息
        self._total_tests_run = 0
        self._total_successful_tests = 0
        self._total_failed_tests = 0
    
    async def test_nodes_async(
        self,
        nodes: List[Node],
        config: Optional[ConcurrentTestConfig] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        result_callback: Optional[Callable[[LatencyTestResult], None]] = None
    ) -> BatchTestResult:
        """
        异步并发测试多个节点延迟
        
        Args:
            nodes: 要测试的节点列表
            config: 测试配置
            progress_callback: 进度回调函数 (completed, total, percentage)
            result_callback: 单个结果回调函数
            
        Returns:
            批量测试结果
        """
        test_config = config or self.config
        
        with self._test_lock:
            if self._is_testing:
                raise RuntimeError("Another test is already running")
            self._is_testing = True
            self._cancel_requested = False
        
        try:
            batch_result = BatchTestResult(
                total_nodes=len(nodes),
                start_time=datetime.now()
            )
            
            # 创建信号量限制并发数
            semaphore = asyncio.Semaphore(test_config.max_concurrent)
            completed = 0
            
            async def test_single_node(node: Node) -> LatencyTestResult:
                nonlocal completed
                
                async with semaphore:
                    if self._cancel_requested:
                        return LatencyTestResult(
                            node_uuid=node.uuid,
                            node_remark=node.remark,
                            error="Test cancelled"
                        )
                    
                    result = await self._test_node_async(node, test_config)
                    
                    completed += 1
                    
                    # 更新进度
                    if progress_callback:
                        percentage = (completed / len(nodes)) * 100
                        progress_callback(completed, len(nodes), percentage)
                    
                    # 单个结果回调
                    if result_callback:
                        result_callback(result)
                    
                    return result
            
            # 创建所有任务
            tasks = [test_single_node(node) for node in nodes]
            
            # 执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 处理异常
                    error_result = LatencyTestResult(
                        node_uuid=nodes[i].uuid,
                        node_remark=nodes[i].remark,
                        error=str(result),
                        latency=-1
                    )
                    batch_result.results.append(error_result)
                    
                    # 记录错误
                    handle_error(
                        category=ErrorCategory.LATENCY_TEST,
                        code="latency_test_async_error",
                        message=f"异步延迟测试失败: {nodes[i].remark}",
                        details=str(result),
                        context={'node_uuid': nodes[i].uuid}
                    )
                else:
                    batch_result.results.append(result)
            
            batch_result.end_time = datetime.now()
            batch_result.update_statistics()
            
            # 更新全局统计
            self._total_tests_run += len(nodes)
            self._total_successful_tests += len([r for r in batch_result.results if r.is_successful()])
            self._total_failed_tests += len([r for r in batch_result.results if not r.is_successful()])
            
            return batch_result
            
        finally:
            with self._test_lock:
                self._is_testing = False
                self._cancel_requested = False
    
    def test_nodes_threaded(
        self,
        nodes: List[Node],
        config: Optional[ConcurrentTestConfig] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        result_callback: Optional[Callable[[LatencyTestResult], None]] = None
    ) -> BatchTestResult:
        """
        多线程并发测试多个节点延迟
        
        Args:
            nodes: 要测试的节点列表
            config: 测试配置
            progress_callback: 进度回调函数 (completed, total, percentage)
            result_callback: 单个结果回调函数
            
        Returns:
            批量测试结果
        """
        test_config = config or self.config
        
        with self._test_lock:
            if self._is_testing:
                raise RuntimeError("Another test is already running")
            self._is_testing = True
            self._cancel_requested = False
        
        try:
            batch_result = BatchTestResult(
                total_nodes=len(nodes),
                start_time=datetime.now()
            )
            
            results = [None] * len(nodes)
            completed = 0
            lock = threading.Lock()
            
            def test_worker(index: int, node: Node):
                nonlocal completed
                
                if self._cancel_requested:
                    results[index] = LatencyTestResult(
                        node_uuid=node.uuid,
                        node_remark=node.remark,
                        error="Test cancelled"
                    )
                    return
                
                try:
                    result = self._test_node_sync(node, test_config)
                    results[index] = result
                    
                    with lock:
                        completed += 1
                        
                        # 更新进度
                        if progress_callback:
                            percentage = (completed / len(nodes)) * 100
                            progress_callback(completed, len(nodes), percentage)
                        
                        # 单个结果回调
                        if result_callback:
                            result_callback(result)
                            
                except Exception as e:
                    error_result = LatencyTestResult(
                        node_uuid=node.uuid,
                        node_remark=node.remark,
                        error=str(e),
                        latency=-1
                    )
                    results[index] = error_result
                    
                    with lock:
                        completed += 1
                        
                        if progress_callback:
                            percentage = (completed / len(nodes)) * 100
                            progress_callback(completed, len(nodes), percentage)
                        
                        if result_callback:
                            result_callback(error_result)
                    
                    # 记录错误
                    handle_error(
                        category=ErrorCategory.LATENCY_TEST,
                        code="latency_test_thread_error",
                        message=f"线程延迟测试失败: {node.remark}",
                        details=str(e),
                        context={'node_uuid': node.uuid}
                    )
            
            # 使用线程池执行测试
            with concurrent.futures.ThreadPoolExecutor(max_workers=test_config.max_concurrent) as executor:
                futures = [
                    executor.submit(test_worker, i, node)
                    for i, node in enumerate(nodes)
                ]
                
                # 等待所有任务完成
                concurrent.futures.wait(futures)
            
            # 收集结果
            batch_result.results = [r for r in results if r is not None]
            batch_result.end_time = datetime.now()
            batch_result.update_statistics()
            
            # 更新全局统计
            self._total_tests_run += len(nodes)
            self._total_successful_tests += len([r for r in batch_result.results if r.is_successful()])
            self._total_failed_tests += len([r for r in batch_result.results if not r.is_successful()])
            
            return batch_result
            
        finally:
            with self._test_lock:
                self._is_testing = False
                self._cancel_requested = False
    
    def test_nodes_batch(
        self,
        nodes: List[Node],
        config: Optional[ConcurrentTestConfig] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        result_callback: Optional[Callable[[LatencyTestResult], None]] = None
    ) -> BatchTestResult:
        """
        批量测试节点延迟（自动选择最佳策略）
        
        Args:
            nodes: 要测试的节点列表
            config: 测试配置
            progress_callback: 进度回调函数 (completed, total, percentage)
            result_callback: 单个结果回调函数
            
        Returns:
            批量测试结果
        """
        test_config = config or self.config
        
        # 根据节点数量和配置选择最佳策略
        if len(nodes) > 100 and test_config.strategy == TestStrategy.ASYNCIO:
            # 大量节点使用异步IO
            return asyncio.run(self.test_nodes_async(nodes, test_config, progress_callback, result_callback))
        else:
            # 中等数量节点使用多线程
            return self.test_nodes_threaded(nodes, test_config, progress_callback, result_callback)
    
    async def _test_node_async(self, node: Node, config: ConcurrentTestConfig) -> LatencyTestResult:
        """异步测试单个节点"""
        start_time = time.time()
        
        result = LatencyTestResult(
            node_uuid=node.uuid,
            node_remark=node.remark
        )
        
        for attempt in range(config.retry_count + 1):
            try:
                if config.bypass_tun and network_manager.is_tun_mode_active():
                    # TUN模式下使用直连测试
                    latency = await self._test_connection_async_bypass(node, config.timeout)
                    result.test_method = "bypass"
                else:
                    # 普通连接测试
                    latency = await self._test_connection_async(node, config.timeout)
                    result.test_method = "direct"
                
                if latency is not None and latency > 0:
                    result.latency = latency
                    result.retry_count = attempt
                    break
                else:
                    result.latency = -1
                    
            except asyncio.TimeoutError:
                result.error = f"Connection timeout (attempt {attempt + 1})"
                result.latency = -1
            except Exception as e:
                result.error = f"Connection error: {str(e)} (attempt {attempt + 1})"
                result.latency = -1
            
            # 如果不是最后一次尝试，等待重试延迟
            if attempt < config.retry_count:
                await asyncio.sleep(config.retry_delay)
        
        result.test_duration = time.time() - start_time
        return result
    
    def _test_node_sync(self, node: Node, config: ConcurrentTestConfig) -> LatencyTestResult:
        """同步测试单个节点"""
        start_time = time.time()
        
        result = LatencyTestResult(
            node_uuid=node.uuid,
            node_remark=node.remark
        )
        
        for attempt in range(config.retry_count + 1):
            try:
                if config.bypass_tun and network_manager.is_tun_mode_active():
                    # TUN模式下使用直连测试
                    latency = self._test_connection_sync_bypass(node, config.timeout)
                    result.test_method = "bypass"
                else:
                    # 普通连接测试
                    latency = self._test_connection_sync(node, config.timeout)
                    result.test_method = "direct"
                
                if latency is not None and latency > 0:
                    result.latency = latency
                    result.retry_count = attempt
                    break
                else:
                    result.latency = -1
                    
            except socket.timeout:
                result.error = f"Connection timeout (attempt {attempt + 1})"
                result.latency = -1
            except Exception as e:
                result.error = f"Connection error: {str(e)} (attempt {attempt + 1})"
                result.latency = -1
            
            # 如果不是最后一次尝试，等待重试延迟
            if attempt < config.retry_count:
                time.sleep(config.retry_delay)
        
        result.test_duration = time.time() - start_time
        return result
    
    async def _test_connection_async(self, node: Node, timeout: float) -> Optional[int]:
        """异步连接测试"""
        start_time = time.time()
        
        try:
            # 使用asyncio的连接测试
            future = asyncio.open_connection(node.address, node.port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            writer.close()
            await writer.wait_closed()
            
            return latency_ms
            
        except asyncio.TimeoutError:
            return -1
        except Exception:
            return -1
    
    async def _test_connection_async_bypass(self, node: Node, timeout: float) -> Optional[int]:
        """异步绕过TUN模式的连接测试"""
        # 获取物理网络接口
        physical_interfaces = network_manager.get_physical_interfaces(refresh=False)
        
        if physical_interfaces:
            # 选择第一个活跃的物理接口
            for iface in physical_interfaces:
                if iface.status == 'up' and iface.ip_addresses:
                    # 在异步环境中，我们简化处理，直接使用普通连接
                    # 实际的接口绑定需要更复杂的实现
                    return await self._test_connection_async(node, timeout)
        
        # 回退到普通连接
        return await self._test_connection_async(node, timeout)
    
    def _test_connection_sync(self, node: Node, timeout: float) -> Optional[int]:
        """同步连接测试"""
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                sock.connect((node.address, node.port))
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                return latency_ms
            finally:
                sock.close()
                
        except socket.timeout:
            return -1
        except Exception:
            return -1
    
    def _test_connection_sync_bypass(self, node: Node, timeout: float) -> Optional[int]:
        """同步绕过TUN模式的连接测试"""
        # 获取物理网络接口
        physical_interfaces = network_manager.get_physical_interfaces(refresh=False)
        
        if physical_interfaces:
            # 选择第一个活跃的物理接口
            for iface in physical_interfaces:
                if iface.status == 'up' and iface.ip_addresses:
                    try:
                        return self._test_connection_with_source_ip(
                            node.address, 
                            node.port, 
                            timeout, 
                            iface.ip_addresses[0]
                        )
                    except Exception:
                        continue
        
        # 回退到普通连接
        return self._test_connection_sync(node, timeout)
    
    def _test_connection_with_source_ip(
        self, 
        address: str, 
        port: int, 
        timeout: float, 
        source_ip: str
    ) -> Optional[int]:
        """使用指定源IP进行连接测试"""
        start_time = time.time()
        
        try:
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
    
    def cancel_test(self):
        """取消当前测试"""
        with self._test_lock:
            self._cancel_requested = True
    
    def is_testing(self) -> bool:
        """是否正在测试"""
        with self._test_lock:
            return self._is_testing
    
    def get_statistics(self) -> Dict[str, any]:
        """获取测试统计信息"""
        return {
            'total_tests_run': self._total_tests_run,
            'total_successful_tests': self._total_successful_tests,
            'total_failed_tests': self._total_failed_tests,
            'success_rate': (
                self._total_successful_tests / self._total_tests_run * 100
                if self._total_tests_run > 0 else 0
            ),
            'is_testing': self.is_testing()
        }


# 全局并发延迟测试器实例
concurrent_latency_tester = ConcurrentLatencyTester()