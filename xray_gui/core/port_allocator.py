"""
智能端口分配器 - 管理代理节点的端口分配策略
"""
import logging
import socket
import threading
import time
from typing import Dict, List, Set, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from .node import Node


class PortAllocationStrategy(Enum):
    """端口分配策略"""
    IMMEDIATE = "immediate"  # 立即分配
    LAZY = "lazy"  # 延迟分配（启动时才分配）
    RESERVED = "reserved"  # 保留端口范围
    DYNAMIC = "dynamic"  # 动态分配


@dataclass
class PortRange:
    """端口范围"""
    start: int
    end: int
    
    def __post_init__(self):
        if self.start < 1024 or self.end > 65535:
            raise ValueError("Port range must be between 1024 and 65535")
        if self.start >= self.end:
            raise ValueError("Start port must be less than end port")
    
    def contains(self, port: int) -> bool:
        """检查端口是否在范围内"""
        return self.start <= port <= self.end
    
    def size(self) -> int:
        """获取范围大小"""
        return self.end - self.start + 1


@dataclass
class PortAllocation:
    """端口分配信息"""
    node_id: str
    port: int
    allocated_at: float = field(default_factory=time.time)
    is_active: bool = False
    is_protected: bool = False  # 用户保护的端口
    allocation_strategy: PortAllocationStrategy = PortAllocationStrategy.LAZY
    
    def age(self) -> float:
        """获取分配时长（秒）"""
        return time.time() - self.allocated_at


class PortAllocator:
    """智能端口分配器"""
    
    def __init__(self, 
                 port_range: PortRange = None,
                 strategy: PortAllocationStrategy = PortAllocationStrategy.LAZY,
                 max_concurrent_checks: int = 50):
        """
        初始化端口分配器
        
        Args:
            port_range: 端口分配范围，默认为10000-20000
            strategy: 默认分配策略
            max_concurrent_checks: 最大并发端口检查数
        """
        self.port_range = port_range or PortRange(10000, 20000)
        self.default_strategy = strategy
        self.max_concurrent_checks = max_concurrent_checks
        
        # 端口分配状态
        self._allocations: Dict[str, PortAllocation] = {}  # node_id -> allocation
        self._port_to_node: Dict[int, str] = {}  # port -> node_id
        self._protected_ports: Set[int] = set()  # 用户保护的端口
        self._reserved_ranges: List[PortRange] = []  # 保留的端口范围
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 日志
        self.logger = logging.getLogger(__name__)
        
        # 端口可用性缓存
        self._port_availability_cache: Dict[int, Tuple[bool, float]] = {}
        self._cache_ttl = 30.0  # 缓存30秒
    
    def set_protected_ports(self, ports: Set[int]) -> None:
        """
        设置用户保护的端口
        
        Args:
            ports: 保护的端口集合
        """
        with self._lock:
            self._protected_ports = set(ports)
            self.logger.info(f"Protected ports updated: {sorted(ports)}")
    
    def add_reserved_range(self, port_range: PortRange) -> None:
        """
        添加保留端口范围
        
        Args:
            port_range: 保留的端口范围
        """
        with self._lock:
            self._reserved_ranges.append(port_range)
            self.logger.info(f"Added reserved range: {port_range.start}-{port_range.end}")
    
    def is_port_available(self, port: int, use_cache: bool = True) -> bool:
        """
        检查端口是否可用
        
        Args:
            port: 要检查的端口
            use_cache: 是否使用缓存
            
        Returns:
            端口是否可用
        """
        # 检查缓存
        if use_cache and port in self._port_availability_cache:
            is_available, cached_at = self._port_availability_cache[port]
            if time.time() - cached_at < self._cache_ttl:
                return is_available
        
        # 检查端口范围
        if not self.port_range.contains(port):
            return False
        
        # 检查是否已分配
        if port in self._port_to_node:
            return False
        
        # 检查是否在保留范围内
        for reserved_range in self._reserved_ranges:
            if reserved_range.contains(port):
                return False
        
        # 实际检查端口是否被占用
        is_available = self._check_port_binding(port)
        
        # 更新缓存
        if use_cache:
            self._port_availability_cache[port] = (is_available, time.time())
        
        return is_available
    
    def _check_port_binding(self, port: int) -> bool:
        """
        检查端口是否可以绑定
        
        Args:
            port: 要检查的端口
            
        Returns:
            端口是否可以绑定
        """
        try:
            # 尝试绑定TCP端口
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
                sock.listen(1)
            
            # 尝试绑定UDP端口
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('127.0.0.1', port))
            
            return True
        except OSError:
            return False
    
    def find_available_ports(self, count: int, start_port: int = None) -> List[int]:
        """
        查找可用端口
        
        Args:
            count: 需要的端口数量
            start_port: 开始搜索的端口，默认从范围开始
            
        Returns:
            可用端口列表
        """
        if count <= 0:
            return []
        
        start = start_port or self.port_range.start
        available_ports = []
        
        # 使用并发检查提高效率
        with ThreadPoolExecutor(max_workers=self.max_concurrent_checks) as executor:
            # 提交端口检查任务
            port_futures = {}
            ports_to_check = []
            
            for port in range(start, self.port_range.end + 1):
                if len(ports_to_check) >= count * 3:  # 检查更多端口以提高成功率
                    break
                ports_to_check.append(port)
            
            # 批量提交检查任务
            for port in ports_to_check:
                future = executor.submit(self.is_port_available, port, False)
                port_futures[future] = port
            
            # 收集结果
            for future in as_completed(port_futures):
                port = port_futures[future]
                try:
                    if future.result():
                        available_ports.append(port)
                        if len(available_ports) >= count:
                            break
                except Exception as e:
                    self.logger.warning(f"Error checking port {port}: {e}")
        
        return sorted(available_ports[:count])
    
    def allocate_port(self, node: Node, 
                     strategy: PortAllocationStrategy = None,
                     preferred_port: int = None) -> Optional[int]:
        """
        为节点分配端口
        
        Args:
            node: 节点对象
            strategy: 分配策略，默认使用全局策略
            preferred_port: 首选端口
            
        Returns:
            分配的端口，如果分配失败返回None
        """
        strategy = strategy or self.default_strategy
        node_id = self._get_node_id(node)
        
        with self._lock:
            # 检查节点是否已有分配
            if node_id in self._allocations:
                existing = self._allocations[node_id]
                if existing.is_protected:
                    self.logger.info(f"Node {node_id} has protected port {existing.port}")
                    return existing.port
                
                # 如果是延迟分配策略且还未激活，可以重新分配
                if strategy == PortAllocationStrategy.LAZY and not existing.is_active:
                    self._deallocate_port(node_id)
                else:
                    return existing.port
            
            # 尝试分配首选端口
            if preferred_port and self.is_port_available(preferred_port):
                return self._do_allocate_port(node_id, preferred_port, strategy)
            
            # 根据策略分配端口
            if strategy == PortAllocationStrategy.IMMEDIATE:
                return self._allocate_immediate(node_id)
            elif strategy == PortAllocationStrategy.LAZY:
                return self._allocate_lazy(node_id)
            elif strategy == PortAllocationStrategy.RESERVED:
                return self._allocate_reserved(node_id)
            elif strategy == PortAllocationStrategy.DYNAMIC:
                return self._allocate_dynamic(node_id)
            
            return None
    
    def _get_node_id(self, node: Node) -> str:
        """
        获取节点的唯一标识符
        
        Args:
            node: 节点对象
            
        Returns:
            节点唯一标识符
        """
        # 使用节点的关键信息生成唯一ID
        return f"{node.protocol}://{node.uuid}@{node.address}:{node.port}"
    
    def _allocate_immediate(self, node_id: str) -> Optional[int]:
        """立即分配策略"""
        available_ports = self.find_available_ports(1)
        if available_ports:
            return self._do_allocate_port(node_id, available_ports[0], PortAllocationStrategy.IMMEDIATE)
        return None
    
    def _allocate_lazy(self, node_id: str) -> Optional[int]:
        """延迟分配策略 - 只预留，不实际绑定"""
        available_ports = self.find_available_ports(1)
        if available_ports:
            return self._do_allocate_port(node_id, available_ports[0], PortAllocationStrategy.LAZY)
        return None
    
    def _allocate_reserved(self, node_id: str) -> Optional[int]:
        """保留范围分配策略"""
        # 在保留范围内查找可用端口
        for reserved_range in self._reserved_ranges:
            for port in range(reserved_range.start, reserved_range.end + 1):
                if self.is_port_available(port):
                    return self._do_allocate_port(node_id, port, PortAllocationStrategy.RESERVED)
        return None
    
    def _allocate_dynamic(self, node_id: str) -> Optional[int]:
        """动态分配策略"""
        # 动态分配会尝试重用最近释放的端口
        available_ports = self.find_available_ports(1)
        if available_ports:
            return self._do_allocate_port(node_id, available_ports[0], PortAllocationStrategy.DYNAMIC)
        return None
    
    def _do_allocate_port(self, node_id: str, port: int, strategy: PortAllocationStrategy) -> int:
        """执行端口分配"""
        allocation = PortAllocation(
            node_id=node_id,
            port=port,
            allocation_strategy=strategy,
            is_protected=port in self._protected_ports
        )
        
        self._allocations[node_id] = allocation
        self._port_to_node[port] = node_id
        
        self.logger.info(f"Allocated port {port} to node {node_id} with strategy {strategy.value}")
        return port
    
    def activate_port(self, node_id: str) -> bool:
        """
        激活节点的端口分配（实际启动时调用）
        
        Args:
            node_id: 节点ID
            
        Returns:
            激活是否成功
        """
        with self._lock:
            if node_id not in self._allocations:
                return False
            
            allocation = self._allocations[node_id]
            
            # 再次检查端口可用性
            if not self.is_port_available(allocation.port, use_cache=False):
                self.logger.warning(f"Port {allocation.port} no longer available for node {node_id}")
                # 尝试重新分配
                self._deallocate_port(node_id)
                new_port = self.allocate_port_by_id(node_id, allocation.allocation_strategy)
                if new_port:
                    allocation = self._allocations[node_id]
                else:
                    return False
            
            allocation.is_active = True
            self.logger.info(f"Activated port {allocation.port} for node {node_id}")
            return True
    
    def allocate_port_by_id(self, node_id: str, strategy: PortAllocationStrategy = None) -> Optional[int]:
        """
        通过节点ID分配端口（用于重新分配）
        
        Args:
            node_id: 节点ID
            strategy: 分配策略
            
        Returns:
            分配的端口
        """
        strategy = strategy or self.default_strategy
        
        with self._lock:
            # 检查是否已有分配
            if node_id in self._allocations:
                return self._allocations[node_id].port
            
            # 分配新端口
            available_ports = self.find_available_ports(1)
            if available_ports:
                return self._do_allocate_port(node_id, available_ports[0], strategy)
            
            return None
    
    def deallocate_port(self, node_id: str) -> bool:
        """
        释放节点的端口分配
        
        Args:
            node_id: 节点ID
            
        Returns:
            释放是否成功
        """
        with self._lock:
            return self._deallocate_port(node_id)
    
    def _deallocate_port(self, node_id: str) -> bool:
        """内部端口释放方法"""
        if node_id not in self._allocations:
            return False
        
        allocation = self._allocations[node_id]
        port = allocation.port
        
        # 检查是否为保护端口
        if allocation.is_protected:
            self.logger.warning(f"Cannot deallocate protected port {port} for node {node_id}")
            return False
        
        # 释放分配
        del self._allocations[node_id]
        del self._port_to_node[port]
        
        # 清除缓存
        if port in self._port_availability_cache:
            del self._port_availability_cache[port]
        
        self.logger.info(f"Deallocated port {port} from node {node_id}")
        return True
    
    def get_allocation(self, node_id: str) -> Optional[PortAllocation]:
        """
        获取节点的端口分配信息
        
        Args:
            node_id: 节点ID
            
        Returns:
            端口分配信息
        """
        with self._lock:
            return self._allocations.get(node_id)
    
    def get_allocated_ports(self) -> Dict[str, int]:
        """
        获取所有已分配的端口
        
        Returns:
            节点ID到端口的映射
        """
        with self._lock:
            return {node_id: alloc.port for node_id, alloc in self._allocations.items()}
    
    def get_port_statistics(self) -> Dict[str, any]:
        """
        获取端口分配统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_range = self.port_range.size()
            allocated_count = len(self._allocations)
            active_count = sum(1 for alloc in self._allocations.values() if alloc.is_active)
            protected_count = sum(1 for alloc in self._allocations.values() if alloc.is_protected)
            
            strategy_counts = {}
            for alloc in self._allocations.values():
                strategy = alloc.allocation_strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            return {
                "port_range": f"{self.port_range.start}-{self.port_range.end}",
                "total_ports": total_range,
                "allocated_ports": allocated_count,
                "active_ports": active_count,
                "protected_ports": protected_count,
                "available_ports": total_range - allocated_count,
                "utilization_rate": allocated_count / total_range * 100,
                "strategy_distribution": strategy_counts,
                "reserved_ranges": len(self._reserved_ranges)
            }
    
    def reallocate_after_sorting(self, sorted_node_ids: List[str], 
                                preserve_protected: bool = True) -> Dict[str, int]:
        """
        排序后重新分配端口（保持端口稳定性）
        
        Args:
            sorted_node_ids: 排序后的节点ID列表
            preserve_protected: 是否保留保护的端口
            
        Returns:
            新的端口分配映射
        """
        with self._lock:
            old_allocations = self._allocations.copy()
            new_allocations = {}
            
            # 保留保护的端口
            if preserve_protected:
                for node_id, allocation in old_allocations.items():
                    if allocation.is_protected:
                        new_allocations[node_id] = allocation.port
            
            # 为排序后的节点重新分配端口
            available_ports = self.find_available_ports(len(sorted_node_ids))
            port_index = 0
            
            for node_id in sorted_node_ids:
                if node_id in new_allocations:
                    # 已有保护端口，跳过
                    continue
                
                if port_index < len(available_ports):
                    new_port = available_ports[port_index]
                    port_index += 1
                    
                    # 更新分配
                    old_allocation = old_allocations.get(node_id)
                    strategy = old_allocation.allocation_strategy if old_allocation else self.default_strategy
                    
                    self._do_allocate_port(node_id, new_port, strategy)
                    new_allocations[node_id] = new_port
            
            self.logger.info(f"Reallocated ports for {len(new_allocations)} nodes after sorting")
            return new_allocations
    
    def cleanup_inactive_allocations(self, max_age_seconds: float = 3600) -> int:
        """
        清理长时间未激活的端口分配
        
        Args:
            max_age_seconds: 最大未激活时间（秒）
            
        Returns:
            清理的分配数量
        """
        with self._lock:
            current_time = time.time()
            to_cleanup = []
            
            for node_id, allocation in self._allocations.items():
                if (not allocation.is_active and 
                    not allocation.is_protected and
                    current_time - allocation.allocated_at > max_age_seconds):
                    to_cleanup.append(node_id)
            
            cleaned_count = 0
            for node_id in to_cleanup:
                if self._deallocate_port(node_id):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} inactive port allocations")
            
            return cleaned_count


# 全局端口分配器实例
port_allocator = PortAllocator()