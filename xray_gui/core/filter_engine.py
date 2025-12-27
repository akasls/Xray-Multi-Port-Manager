"""
过滤引擎 - 根据关键词过滤节点
"""
from typing import List, Tuple
from .node import Node


class FilterEngine:
    """节点过滤引擎"""
    
    def __init__(self, exclude_keywords: List[str] = None):
        """
        初始化过滤引擎
        
        Args:
            exclude_keywords: 排除关键词列表
        """
        self._exclude_keywords: List[str] = exclude_keywords or []
    
    @property
    def exclude_keywords(self) -> List[str]:
        """获取排除关键词列表"""
        return self._exclude_keywords.copy()
    
    def set_keywords(self, keywords: str) -> None:
        """
        设置排除关键词
        
        Args:
            keywords: 逗号分隔的关键词字符串
        """
        if not keywords or not keywords.strip():
            self._exclude_keywords = []
        else:
            self._exclude_keywords = [
                kw.strip() 
                for kw in keywords.split(',') 
                if kw.strip()
            ]
    
    def set_keywords_list(self, keywords: List[str]) -> None:
        """
        设置排除关键词列表
        
        Args:
            keywords: 关键词列表
        """
        self._exclude_keywords = [kw.strip() for kw in keywords if kw.strip()]
    
    def should_exclude(self, node: Node) -> bool:
        """
        检查节点是否应该被排除
        
        Args:
            node: 节点对象
            
        Returns:
            是否应该排除
        """
        if not self._exclude_keywords:
            return False
        
        remark_lower = node.remark.lower()
        for keyword in self._exclude_keywords:
            if keyword.lower() in remark_lower:
                return True
        
        return False
    
    def filter_nodes(self, nodes: List[Node]) -> Tuple[List[Node], int]:
        """
        过滤节点
        
        Args:
            nodes: 原始节点列表
            
        Returns:
            (过滤后的节点列表, 被过滤的数量)
        """
        if not self._exclude_keywords:
            return nodes.copy(), 0
        
        filtered = []
        excluded_count = 0
        
        for node in nodes:
            if self.should_exclude(node):
                excluded_count += 1
            else:
                filtered.append(node)
        
        return filtered, excluded_count
    
    def filter_by_include(self, nodes: List[Node], include_keywords: List[str]) -> List[Node]:
        """
        根据包含关键词过滤（只保留包含关键词的节点）
        
        Args:
            nodes: 原始节点列表
            include_keywords: 包含关键词列表
            
        Returns:
            过滤后的节点列表
        """
        if not include_keywords:
            return nodes.copy()
        
        filtered = []
        for node in nodes:
            remark_lower = node.remark.lower()
            for keyword in include_keywords:
                if keyword.lower() in remark_lower:
                    filtered.append(node)
                    break
        
        return filtered
