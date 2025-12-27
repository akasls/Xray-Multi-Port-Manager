"""
节点解析器 - 解析各种协议的代理链接
"""
from typing import List, Optional
import urllib.parse
from .node import Node


def parse_vless(link: str) -> Optional[Node]:
    """
    解析 VLESS 链接
    
    Args:
        link: vless:// 格式的链接
        
    Returns:
        Node 对象，解析失败返回 None
    """
    link = link.strip()
    if not link.startswith("vless://"):
        return None
    
    try:
        # 处理备注
        if "#" in link:
            main_part = link.split("#")[0][8:]
            remark = urllib.parse.unquote(link.split("#")[1])
        else:
            main_part = link[8:]
            remark = "Untitled"
        
        # 处理参数
        if "?" in main_part:
            user_info, query_string = main_part.split("?")
        else:
            user_info, query_string = main_part, ""
        
        if "@" not in user_info:
            return None
            
        uuid, addr_port = user_info.split("@")
        
        # 处理 IPv6 地址
        if addr_port.startswith("["):
            # IPv6 格式: [::1]:port
            bracket_end = addr_port.rfind("]")
            addr = addr_port[1:bracket_end]
            port = int(addr_port[bracket_end + 2:])
        else:
            addr, port = addr_port.rsplit(":", 1)
            port = int(port)
        
        params = urllib.parse.parse_qs(query_string)
        get_param = lambda k: params.get(k, [''])[0]

        return Node(
            uuid=uuid,
            address=addr,
            port=port,
            remark=remark,
            protocol="vless",
            flow=get_param("flow"),
            security=get_param("security"),
            sni=get_param("sni"),
            public_key=get_param("pbk"),
            short_id=get_param("sid"),
            fingerprint=get_param("fp"),
            network=get_param("type") or "tcp",
            service_name=get_param("serviceName")
        )
    except Exception:
        return None


def parse_link(link: str) -> Optional[Node]:
    """
    解析代理链接（自动识别协议）
    
    Args:
        link: 代理链接
        
    Returns:
        Node 对象，解析失败返回 None
    """
    link = link.strip()
    
    if link.startswith("vless://"):
        return parse_vless(link)
    # 可以在这里添加其他协议的支持
    # elif link.startswith("vmess://"):
    #     return parse_vmess(link)
    
    return None


def parse_links(links: List[str]) -> List[Node]:
    """
    批量解析代理链接
    
    Args:
        links: 链接列表
        
    Returns:
        成功解析的 Node 列表
    """
    nodes = []
    for link in links:
        node = parse_link(link)
        if node:
            nodes.append(node)
    return nodes
