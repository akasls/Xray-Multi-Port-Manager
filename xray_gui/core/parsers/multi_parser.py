"""
多协议解析器 - 支持WireGuard、Hysteria2、SOCKS、HTTP等协议
"""
import urllib.parse
import json
from typing import Optional, List
from ..protocol_parser import ProtocolParser
from ..node import Node


class WireGuardParser(ProtocolParser):
    """WireGuard协议解析器（简化版）"""
    
    def get_protocol_name(self) -> str:
        return "wireguard"
    
    def get_supported_schemes(self) -> List[str]:
        return ["wireguard://", "wg://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """解析WireGuard链接（基础实现）"""
        # WireGuard配置通常比较复杂，这里提供基础解析
        # 实际使用中可能需要更复杂的配置文件解析
        return None  # 暂时返回None，表示不支持


class Hysteria2Parser(ProtocolParser):
    """Hysteria2协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "hysteria2"
    
    def get_supported_schemes(self) -> List[str]:
        return ["hysteria2://", "hy2://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """解析Hysteria2链接"""
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 去掉协议前缀
            if link.startswith("hysteria2://"):
                content = link[12:]
            elif link.startswith("hy2://"):
                content = link[6:]
            else:
                return None
            
            # 处理备注
            if "#" in content:
                main_part, remark = content.rsplit("#", 1)
                remark = urllib.parse.unquote(remark)
            else:
                main_part = content
                remark = "Untitled"
            
            # 处理参数
            if "?" in main_part:
                auth_server_part, query_string = main_part.split("?", 1)
            else:
                auth_server_part = main_part
                query_string = ""
            
            # 解析认证和服务器部分
            if "@" not in auth_server_part:
                return None
            
            auth, server_part = auth_server_part.rsplit("@", 1)
            
            # 解析服务器和端口
            if ":" not in server_part:
                return None
            
            address, port_str = server_part.rsplit(":", 1)
            port = int(port_str)
            
            if not (1 <= port <= 65535):
                return None
            
            # 解析查询参数
            params = urllib.parse.parse_qs(query_string)
            get_param = lambda k: params.get(k, [''])[0]
            
            return Node(
                uuid="",  # Hysteria2不使用UUID
                address=address,
                port=port,
                remark=remark,
                protocol="hysteria2",
                password=auth,  # 使用password字段存储认证信息
                network="udp",  # Hysteria2使用UDP
                security="tls",  # Hysteria2通常使用TLS
                sni=get_param("sni"),
                alpn=get_param("alpn")
            )
            
        except (ValueError, IndexError, KeyError):
            return None


class SocksParser(ProtocolParser):
    """SOCKS协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "socks"
    
    def get_supported_schemes(self) -> List[str]:
        return ["socks://", "socks5://", "socks4://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """解析SOCKS链接"""
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 确定协议版本
            if link.startswith("socks5://"):
                content = link[9:]
                socks_version = "5"
            elif link.startswith("socks4://"):
                content = link[9:]
                socks_version = "4"
            elif link.startswith("socks://"):
                content = link[8:]
                socks_version = "5"  # 默认SOCKS5
            else:
                return None
            
            # 处理备注
            if "#" in content:
                main_part, remark = content.rsplit("#", 1)
                remark = urllib.parse.unquote(remark)
            else:
                main_part = content
                remark = "Untitled"
            
            # 解析用户名密码和服务器
            if "@" in main_part:
                auth_part, server_part = main_part.rsplit("@", 1)
                if ":" in auth_part:
                    username, password = auth_part.split(":", 1)
                else:
                    username, password = auth_part, ""
            else:
                server_part = main_part
                username, password = "", ""
            
            # 解析服务器和端口
            if ":" not in server_part:
                return None
            
            address, port_str = server_part.rsplit(":", 1)
            port = int(port_str)
            
            if not (1 <= port <= 65535):
                return None
            
            return Node(
                uuid=username,  # 使用uuid字段存储用户名
                address=address,
                port=port,
                remark=remark,
                protocol="socks",
                password=password,
                method=socks_version,  # 使用method字段存储SOCKS版本
                network="tcp"
            )
            
        except (ValueError, IndexError, KeyError):
            return None


class HttpParser(ProtocolParser):
    """HTTP代理协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "http"
    
    def get_supported_schemes(self) -> List[str]:
        return ["http://", "https://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """解析HTTP代理链接"""
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 确定是否使用TLS
            if link.startswith("https://"):
                content = link[8:]
                use_tls = True
            elif link.startswith("http://"):
                content = link[7:]
                use_tls = False
            else:
                return None
            
            # 处理备注（HTTP链接通常不包含#备注，但为了一致性支持）
            if "#" in content:
                main_part, remark = content.rsplit("#", 1)
                remark = urllib.parse.unquote(remark)
            else:
                main_part = content
                remark = "Untitled"
            
            # 解析用户名密码和服务器
            if "@" in main_part:
                auth_part, server_part = main_part.rsplit("@", 1)
                if ":" in auth_part:
                    username, password = auth_part.split(":", 1)
                else:
                    username, password = auth_part, ""
            else:
                server_part = main_part
                username, password = "", ""
            
            # 解析服务器和端口
            if ":" in server_part:
                address, port_str = server_part.rsplit(":", 1)
                port = int(port_str)
            else:
                address = server_part
                port = 443 if use_tls else 80  # 默认端口
            
            if not (1 <= port <= 65535):
                return None
            
            return Node(
                uuid=username,  # 使用uuid字段存储用户名
                address=address,
                port=port,
                remark=remark,
                protocol="http",
                password=password,
                security="tls" if use_tls else "",
                network="tcp"
            )
            
        except (ValueError, IndexError, KeyError):
            return None