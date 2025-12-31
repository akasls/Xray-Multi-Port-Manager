"""
Shadowsocks协议解析器
"""
import base64
import urllib.parse
from typing import Optional, List
from ..protocol_parser import ProtocolParser
from ..node import Node


class ShadowsocksParser(ProtocolParser):
    """Shadowsocks协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "shadowsocks"
    
    def get_supported_schemes(self) -> List[str]:
        return ["ss://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """
        解析Shadowsocks链接为Node对象
        
        支持的格式:
        1. SIP002: ss://method:password@server:port#tag
        2. Legacy: ss://base64(method:password)@server:port#tag
        
        Args:
            link: ss://格式的链接
            
        Returns:
            Node对象，解析失败返回None
        """
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 去掉ss://前缀
            content = link[5:]
            
            # 处理备注
            if "#" in content:
                main_part, remark = content.rsplit("#", 1)
                remark = urllib.parse.unquote(remark)
            else:
                main_part = content
                remark = "Untitled"
            
            # 解析主要部分
            if "@" not in main_part:
                return None
            
            auth_part, server_part = main_part.rsplit("@", 1)
            
            # 解析服务器和端口
            if ":" not in server_part:
                return None
            
            # 处理IPv6地址
            if server_part.startswith("["):
                bracket_end = server_part.rfind("]")
                if bracket_end == -1:
                    return None
                address = server_part[1:bracket_end]
                port_part = server_part[bracket_end + 1:]
                if not port_part.startswith(":"):
                    return None
                port = int(port_part[1:])
            else:
                address, port_str = server_part.rsplit(":", 1)
                port = int(port_str)
            
            if not (1 <= port <= 65535):
                return None
            
            # 解析认证信息
            method, password = self._parse_auth_part(auth_part)
            if not method or not password:
                return None
            
            return Node(
                uuid="",  # Shadowsocks不使用UUID
                address=address,
                port=port,
                remark=remark,
                protocol="shadowsocks",
                method=method,
                password=password,
                network="tcp"  # Shadowsocks默认使用TCP
            )
            
        except (ValueError, IndexError, KeyError):
            return None
    
    def _parse_auth_part(self, auth_part: str) -> tuple[str, str]:
        """
        解析认证部分
        
        Args:
            auth_part: 认证部分字符串
            
        Returns:
            (method, password) 元组
        """
        # 尝试SIP002格式: method:password
        if ":" in auth_part:
            parts = auth_part.split(":", 1)
            if len(parts) == 2:
                method, password = parts
                if method and password:
                    return method, password
        
        # 尝试Legacy格式: base64(method:password)
        try:
            # 处理可能的padding问题
            missing_padding = len(auth_part) % 4
            if missing_padding:
                auth_part += '=' * (4 - missing_padding)
            
            decoded = base64.b64decode(auth_part).decode('utf-8')
            if ":" in decoded:
                method, password = decoded.split(":", 1)
                if method and password:
                    return method, password
        except Exception:
            pass
        
        return "", ""
    
    def _validate_method(self, method: str) -> bool:
        """
        验证加密方法是否支持
        
        Args:
            method: 加密方法
            
        Returns:
            是否支持
        """
        supported_methods = {
            # AEAD 2022
            "2022-blake3-aes-128-gcm",
            "2022-blake3-aes-256-gcm", 
            "2022-blake3-chacha20-poly1305",
            # AEAD
            "aes-128-gcm",
            "aes-256-gcm",
            "chacha20-poly1305",
            "chacha20-ietf-poly1305",
            # Stream (deprecated but still supported)
            "aes-128-cfb",
            "aes-192-cfb", 
            "aes-256-cfb",
            "aes-128-ctr",
            "aes-192-ctr",
            "aes-256-ctr",
            "chacha20",
            "chacha20-ietf",
            "rc4-md5"
        }
        return method.lower() in supported_methods


def create_shadowsocks_link(node: Node) -> str:
    """
    从Node对象创建Shadowsocks链接
    
    Args:
        node: Node对象
        
    Returns:
        Shadowsocks链接字符串
    """
    if node.protocol != "shadowsocks":
        raise ValueError("Node protocol must be shadowsocks")
    
    if not node.method or not node.password:
        raise ValueError("Method and password are required for Shadowsocks")
    
    # 使用SIP002格式
    auth_part = f"{node.method}:{node.password}"
    
    # 处理IPv6地址
    if ":" in node.address and not node.address.startswith("["):
        server_part = f"[{node.address}]:{node.port}"
    else:
        server_part = f"{node.address}:{node.port}"
    
    # 编码备注
    encoded_remark = urllib.parse.quote(node.remark) if node.remark else ""
    
    link = f"ss://{auth_part}@{server_part}"
    if encoded_remark:
        link += f"#{encoded_remark}"
    
    return link