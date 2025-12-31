"""
节点解析器 - 解析各种协议的代理链接
"""
from typing import List, Optional
from .protocol_parser import protocol_factory, parse_links as factory_parse_links
from .parsers.vless_parser import VLessParser
from .parsers.vmess_parser import VMessParser
from .parsers.shadowsocks_parser import ShadowsocksParser
from .parsers.trojan_parser import TrojanParser
from .parsers.multi_parser import WireGuardParser, Hysteria2Parser, SocksParser, HttpParser
from .node import Node

# 注册解析器
protocol_factory.register_parser(VLessParser())
protocol_factory.register_parser(VMessParser())
protocol_factory.register_parser(ShadowsocksParser())
protocol_factory.register_parser(TrojanParser())
protocol_factory.register_parser(WireGuardParser())
protocol_factory.register_parser(Hysteria2Parser())
protocol_factory.register_parser(SocksParser())
protocol_factory.register_parser(HttpParser())


def parse_vless(link: str) -> Optional[Node]:
    """
    解析 VLESS 链接（保持向后兼容）
    
    Args:
        link: vless:// 格式的链接
        
    Returns:
        Node 对象，解析失败返回 None
    """
    parser = protocol_factory.get_parser("vless")
    if parser:
        return parser.parse_link(link)
    return None


def parse_link(link: str) -> Optional[Node]:
    """
    解析代理链接（自动识别协议）
    
    Args:
        link: 代理链接
        
    Returns:
        Node 对象，解析失败返回 None
    """
    return protocol_factory.parse_link(link)


def parse_links(links: List[str]) -> List[Node]:
    """
    批量解析代理链接
    
    Args:
        links: 链接列表
        
    Returns:
        成功解析的 Node 列表
    """
    return factory_parse_links(links)
