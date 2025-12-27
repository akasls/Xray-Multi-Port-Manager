"""
排序引擎 - 节点排序功能
"""
from typing import List
from .node import Node


class SortEngine:
    """节点排序引擎"""
    
    def __init__(self, region_priority: List[str] = None):
        """
        初始化排序引擎
        
        Args:
            region_priority: 地区优先级列表
        """
        self._region_priority: List[str] = region_priority or []
    
    @property
    def region_priority(self) -> List[str]:
        """获取地区优先级列表"""
        return self._region_priority.copy()
    
    def set_priority(self, priority: str) -> None:
        """
        设置地区优先级
        
        Args:
            priority: 逗号分隔的地区字符串
        """
        if not priority or not priority.strip():
            self._region_priority = []
        else:
            self._region_priority = [
                p.strip() 
                for p in priority.split(',') 
                if p.strip()
            ]
    
    def set_priority_list(self, priority: List[str]) -> None:
        """
        设置地区优先级列表
        
        Args:
            priority: 地区列表
        """
        self._region_priority = [p.strip() for p in priority if p.strip()]
    
    def _get_region_priority_index(self, node: Node) -> int:
        """
        获取节点的地区优先级索引
        
        Args:
            node: 节点对象
            
        Returns:
            优先级索引，未匹配返回最大值
        """
        remark_lower = node.remark.lower()
        
        for i, region in enumerate(self._region_priority):
            if region.lower() in remark_lower:
                return i
        
        # 未匹配的节点放在最后
        return len(self._region_priority)
    
    def sort_by_region(self, nodes: List[Node]) -> List[Node]:
        """
        按地区优先级排序
        
        Args:
            nodes: 节点列表
            
        Returns:
            排序后的节点列表
        """
        if not self._region_priority:
            return nodes.copy()
        
        return sorted(nodes, key=self._get_region_priority_index)
    
    def sort_by_speed(self, nodes: List[Node]) -> List[Node]:
        """
        按速度排序（延迟升序，超时节点放最后）
        
        Args:
            nodes: 节点列表
            
        Returns:
            排序后的节点列表
        """
        def speed_key(node: Node) -> tuple:
            if node.latency is None:
                # 未测试的放在中间
                return (1, 0)
            elif node.latency == -1:
                # 超时的放在最后
                return (2, 0)
            else:
                # 正常延迟按升序
                return (0, node.latency)
        
        return sorted(nodes, key=speed_key)
    
    def sort_by_region_then_speed(self, nodes: List[Node]) -> List[Node]:
        """
        先按地区优先级排序，然后在同一地区内按延迟排序
        确保地区优先级不被延迟排序打乱
        
        Args:
            nodes: 节点列表
            
        Returns:
            排序后的节点列表
        """
        def combined_key(node: Node) -> tuple:
            region_idx = self._get_region_priority_index(node)
            
            # 延迟排序键
            if node.latency is None:
                speed_priority = (1, 0)  # 未测试的放在中间
            elif node.latency == -1:
                speed_priority = (2, 0)  # 超时的放在最后
            else:
                speed_priority = (0, node.latency)  # 正常延迟按升序
            
            return (region_idx, speed_priority)
        
        return sorted(nodes, key=combined_key)
    
    def sort_by_name(self, nodes: List[Node], reverse: bool = False) -> List[Node]:
        """
        按名称排序
        
        Args:
            nodes: 节点列表
            reverse: 是否降序
            
        Returns:
            排序后的节点列表
        """
        return sorted(nodes, key=lambda n: n.remark.lower(), reverse=reverse)
