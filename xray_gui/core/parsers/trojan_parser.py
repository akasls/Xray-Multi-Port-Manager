"""
Trojan协议解析器
"""
import urllib.parse
from typing import Optional, List
from ..protocol_parser import ProtocolParser
from ..node import Node


class TrojanParser(ProtocolParser):
    """Trojan协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "trojan"
    
    def get_supported_schemes(self) -> List[str]:
        return ["trojan://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """
        解析Trojan链接为Node对象
        
        Trojan链接格式: trojan://password@server:port?params#remark
        
        Args:
            link: trojan://格式的链接
            
        Returns:
            Node对象，解析失败返回None
        """
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 去掉trojan://前缀
            content = link[9:]
            
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
            
            password, server_part = auth_server_part.rsplit("@", 1)
            
            # 密码不能为空
            if not password.strip():
                return None
            
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
            
            # 解析查询参数
            params = urllib.parse.parse_qs(query_string)
            get_param = lambda k: params.get(k, [''])[0]
            
            # 网络类型
            network = get_param("type") or "tcp"
            if network not in ["tcp", "ws", "grpc", "h2"]:
                network = "tcp"
            
            # 安全类型（Trojan通常使用TLS）
            security = get_param("security") or "tls"
            
            # 创建Node对象
            node = Node(
                uuid="",  # Trojan不使用UUID
                address=address,
                port=port,
                remark=remark,
                protocol="trojan",
                password=password,
                network=network,
                security=security,
                sni=get_param("sni"),
                host=get_param("host"),
                path=get_param("path"),
                service_name=get_param("serviceName"),
                alpn=get_param("alpn"),
                fingerprint=get_param("fp")
            )
            
            # 处理网络特定配置
            self._process_network_config(node, params)
            
            return node
            
        except (ValueError, IndexError, KeyError):
            return None
    
    def _process_network_config(self, node: Node, params: dict) -> None:
        """
        处理网络特定配置
        
        Args:
            node: Node对象
            params: 查询参数字典
        """
        get_param = lambda k: params.get(k, [''])[0]
        
        if node.network == "ws":
            # WebSocket配置
            node.path = get_param("path") or "/"
            node.host = get_param("host")
            
        elif node.network == "h2":
            # HTTP/2配置
            node.h2_path = get_param("path") or "/"
            node.h2_host = get_param("host")
            
        elif node.network == "grpc":
            # gRPC配置
            node.service_name = get_param("serviceName")
            node.grpc_mode = get_param("mode") or "gun"


def create_trojan_link(node: Node) -> str:
    """
    从Node对象创建Trojan链接
    
    Args:
        node: Node对象
        
    Returns:
        Trojan链接字符串
    """
    if node.protocol != "trojan":
        raise ValueError("Node protocol must be trojan")
    
    if not node.password:
        raise ValueError("Password is required for Trojan")
    
    # 处理IPv6地址
    if ":" in node.address and not node.address.startswith("["):
        server_part = f"[{node.address}]:{node.port}"
    else:
        server_part = f"{node.address}:{node.port}"
    
    # 构建查询参数
    params = []
    
    if node.network and node.network != "tcp":
        params.append(f"type={node.network}")
    
    if node.security and node.security != "tls":
        params.append(f"security={node.security}")
    
    if node.sni:
        params.append(f"sni={urllib.parse.quote(node.sni)}")
    
    if node.host:
        params.append(f"host={urllib.parse.quote(node.host)}")
    
    if node.path:
        params.append(f"path={urllib.parse.quote(node.path)}")
    
    if node.service_name:
        params.append(f"serviceName={urllib.parse.quote(node.service_name)}")
    
    if node.alpn:
        params.append(f"alpn={urllib.parse.quote(node.alpn)}")
    
    if node.fingerprint:
        params.append(f"fp={node.fingerprint}")
    
    # 构建链接
    link = f"trojan://{node.password}@{server_part}"
    
    if params:
        link += "?" + "&".join(params)
    
    if node.remark:
        encoded_remark = urllib.parse.quote(node.remark)
        link += f"#{encoded_remark}"
    
    return link