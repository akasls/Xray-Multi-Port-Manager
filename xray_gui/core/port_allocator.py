"""
端口分配器 - 管理本地端口分配
"""
import socket
from typing import List, Tuple
from .node import Node


class PortAllocator:
    """端口分配器"""
    
    MIN_PORT = 1024
    MAX_PORT = 65535
    
    def __init__(self, start_port: int = 40000, count: int = 20):
        """
        初始化端口分配器
        
        Args:
            start_port: 起始端口
            count: 端口数量
        """
        self._start_port = start_port
        self._count = count
    
    @property
    def start_port(self) -> int:
        """获取起始端口"""
        return self._start_port
    
    @start_port.setter
    def start_port(self, value: int):
        """设置起始端口"""
        self._start_port = value
    
    @property
    def count(self) -> int:
        """获取端口数量"""
        return self._count
    
    @count.setter
    def count(self, value: int):
        """设置端口数量"""
        self._count = value
    
    @property
    def end_port(self) -> int:
        """获取结束端口"""
        return self._start_port + self._count - 1
    
    @property
    def port_range(self) -> List[int]:
        """获取端口范围列表"""
        return list(range(self._start_port, self._start_port + self._count))
    
    def allocate(self, nodes: List[Node]) -> List[Node]:
        """
        为节点分配端口
        
        Args:
            nodes: 节点列表
            
        Returns:
            分配了端口的节点列表（最多分配 count 个）
        """
        allocated_nodes = []
        current_port = self._start_port
        
        for node in nodes:
            if len(allocated_nodes) >= self._count:
                break
            
            node.local_port = current_port
            allocated_nodes.append(node)
            current_port += 1
        
        return allocated_nodes
    
    def validate_ports(self) -> Tuple[bool, str]:
        """
        验证端口配置
        
        Returns:
            (是否有效, 错误信息)
        """
        # 检查起始端口
        if self._start_port < self.MIN_PORT:
            return False, f"起始端口不能小于 {self.MIN_PORT}"
        
        if self._start_port > self.MAX_PORT:
            return False, f"起始端口不能大于 {self.MAX_PORT}"
        
        # 检查端口数量
        if self._count <= 0:
            return False, "端口数量必须大于 0"
        
        # 检查结束端口
        if self.end_port > self.MAX_PORT:
            return False, f"端口范围超出上限 {self.MAX_PORT}，请减少端口数量或降低起始端口"
        
        return True, ""
    
    def check_conflicts(self) -> List[int]:
        """
        检查端口冲突
        
        Returns:
            冲突的端口列表
        """
        conflicts = []
        
        for port in self.port_range:
            if self._is_port_in_use(port):
                conflicts.append(port)
        
        return conflicts
    
    def _is_port_in_use(self, port: int) -> bool:
        """
        检查端口是否被占用
        
        Args:
            port: 端口号
            
        Returns:
            是否被占用
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                result = s.connect_ex(('127.0.0.1', port))
                return result == 0
        except Exception:
            return False
    
    def find_available_ports(self, count: int, start_from: int = None) -> List[int]:
        """
        查找可用端口
        
        Args:
            count: 需要的端口数量
            start_from: 起始搜索端口
            
        Returns:
            可用端口列表
        """
        if start_from is None:
            start_from = self._start_port
        
        available = []
        port = start_from
        
        while len(available) < count and port <= self.MAX_PORT:
            if not self._is_port_in_use(port):
                available.append(port)
            port += 1
        
        return available
