"""
协议解析器基础接口和工厂类
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type, List
from .node import Node


class ProtocolParser(ABC):
    """协议解析器基础接口"""
    
    @abstractmethod
    def parse_link(self, link: str) -> Optional[Node]:
        """
        解析协议链接为Node对象
        
        Args:
            link: 协议链接字符串
            
        Returns:
            Node对象，解析失败返回None
        """
        pass
    
    @abstractmethod
    def get_protocol_name(self) -> str:
        """
        获取协议名称
        
        Returns:
            协议名称字符串
        """
        pass
    
    @abstractmethod
    def get_supported_schemes(self) -> List[str]:
        """
        获取支持的URL scheme列表
        
        Returns:
            支持的scheme列表，如['vmess://', 'vmess+ws://']
        """
        pass
    
    def validate_link(self, link: str) -> bool:
        """
        验证链接格式是否正确
        
        Args:
            link: 协议链接字符串
            
        Returns:
            是否为有效链接
        """
        link = link.strip()
        return any(link.startswith(scheme) for scheme in self.get_supported_schemes())


class ProtocolParserFactory:
    """协议解析器工厂类"""
    
    def __init__(self):
        self._parsers: Dict[str, ProtocolParser] = {}
        self._scheme_to_parser: Dict[str, ProtocolParser] = {}
    
    def register_parser(self, parser: ProtocolParser) -> None:
        """
        注册协议解析器
        
        Args:
            parser: 协议解析器实例
        """
        protocol_name = parser.get_protocol_name()
        self._parsers[protocol_name] = parser
        
        # 为每个支持的scheme注册解析器
        for scheme in parser.get_supported_schemes():
            self._scheme_to_parser[scheme] = parser
    
    def get_parser(self, protocol_name: str) -> Optional[ProtocolParser]:
        """
        根据协议名称获取解析器
        
        Args:
            protocol_name: 协议名称
            
        Returns:
            协议解析器，不存在返回None
        """
        return self._parsers.get(protocol_name)
    
    def get_parser_by_link(self, link: str) -> Optional[ProtocolParser]:
        """
        根据链接自动识别并获取对应的解析器
        
        Args:
            link: 协议链接字符串
            
        Returns:
            协议解析器，无法识别返回None
        """
        link = link.strip()
        for scheme, parser in self._scheme_to_parser.items():
            if link.startswith(scheme):
                return parser
        return None
    
    def parse_link(self, link: str) -> Optional[Node]:
        """
        自动识别协议并解析链接
        
        Args:
            link: 协议链接字符串
            
        Returns:
            Node对象，解析失败返回None
        """
        parser = self.get_parser_by_link(link)
        if parser:
            return parser.parse_link(link)
        return None
    
    def get_supported_protocols(self) -> List[str]:
        """
        获取所有支持的协议名称列表
        
        Returns:
            协议名称列表
        """
        return list(self._parsers.keys())
    
    def get_supported_schemes(self) -> List[str]:
        """
        获取所有支持的URL scheme列表
        
        Returns:
            scheme列表
        """
        return list(self._scheme_to_parser.keys())


# 全局协议解析器工厂实例
protocol_factory = ProtocolParserFactory()


def parse_links(links: List[str]) -> List[Node]:
    """
    批量解析协议链接
    
    Args:
        links: 链接列表
        
    Returns:
        成功解析的Node列表
    """
    nodes = []
    for link in links:
        node = protocol_factory.parse_link(link)
        if node:
            nodes.append(node)
    return nodes


def get_supported_protocols() -> List[str]:
    """
    获取所有支持的协议名称
    
    Returns:
        协议名称列表
    """
    return protocol_factory.get_supported_protocols()