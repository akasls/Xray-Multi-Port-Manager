"""
VMess协议解析器
"""
import base64
import json
import urllib.parse
from typing import Optional, List, Dict, Any
from ..protocol_parser import ProtocolParser
from ..node import Node


class VMessParser(ProtocolParser):
    """VMess协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "vmess"
    
    def get_supported_schemes(self) -> List[str]:
        return ["vmess://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """
        解析VMess链接为Node对象
        
        VMess链接格式: vmess://base64(json_config)
        
        Args:
            link: vmess://格式的链接
            
        Returns:
            Node对象，解析失败返回None
        """
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 去掉vmess://前缀
            base64_part = link[8:]
            
            # Base64解码
            try:
                # 处理可能的padding问题
                missing_padding = len(base64_part) % 4
                if missing_padding:
                    base64_part += '=' * (4 - missing_padding)
                
                decoded_bytes = base64.b64decode(base64_part)
                json_str = decoded_bytes.decode('utf-8')
            except Exception:
                return None
            
            # JSON解析
            try:
                config = json.loads(json_str)
            except json.JSONDecodeError:
                return None
            
            # 验证必要字段
            if not isinstance(config, dict):
                return None
            
            # 提取基本信息
            address = config.get('add', '').strip()
            port = config.get('port')
            uuid = config.get('id', '').strip()
            remark = config.get('ps', 'Untitled').strip()
            
            if not address or not uuid:
                return None
            
            # 端口处理
            if isinstance(port, str):
                try:
                    port = int(port)
                except ValueError:
                    return None
            elif not isinstance(port, int):
                return None
            
            if not (1 <= port <= 65535):
                return None
            
            # 提取协议相关信息
            alter_id = config.get('aid', 0)
            if isinstance(alter_id, str):
                try:
                    alter_id = int(alter_id)
                except ValueError:
                    alter_id = 0
            
            # 网络类型
            network = config.get('net', 'tcp').lower()
            if network not in ['tcp', 'kcp', 'ws', 'h2', 'quic', 'grpc']:
                network = 'tcp'
            
            # 安全类型
            security = config.get('tls', '').lower()
            if security not in ['', 'tls', 'reality']:
                security = ''
            
            # 创建Node对象
            node = Node(
                uuid=uuid,
                address=address,
                port=port,
                remark=remark,
                protocol="vmess",
                alter_id=alter_id,
                network=network,
                security=security,
                sni=config.get('sni', ''),
                host=config.get('host', ''),
                path=config.get('path', ''),
                service_name=config.get('serviceName', ''),
                alpn=config.get('alpn', ''),
                fingerprint=config.get('fp', '')
            )
            
            # 处理网络特定配置
            self._process_network_config(node, config)
            
            return node
            
        except Exception:
            return None
    
    def _process_network_config(self, node: Node, config: Dict[str, Any]) -> None:
        """
        处理网络特定配置
        
        Args:
            node: Node对象
            config: VMess配置字典
        """
        if node.network == 'ws':
            # WebSocket配置
            node.path = config.get('path', '/')
            node.host = config.get('host', '')
            
        elif node.network == 'h2':
            # HTTP/2配置
            node.h2_path = config.get('path', '/')
            node.h2_host = config.get('host', '')
            
        elif node.network == 'grpc':
            # gRPC配置
            node.service_name = config.get('serviceName', '')
            node.grpc_mode = config.get('mode', 'gun')
            
        elif node.network == 'kcp':
            # KCP配置（暂时不处理具体参数）
            pass
            
        elif node.network == 'quic':
            # QUIC配置（暂时不处理具体参数）
            pass


def create_vmess_link(node: Node) -> str:
    """
    从Node对象创建VMess链接
    
    Args:
        node: Node对象
        
    Returns:
        VMess链接字符串
    """
    if node.protocol != "vmess":
        raise ValueError("Node protocol must be vmess")
    
    config = {
        "v": "2",
        "ps": node.remark,
        "add": node.address,
        "port": node.port,
        "id": node.uuid,
        "aid": node.alter_id,
        "net": node.network,
        "type": "none",
        "host": node.host,
        "path": node.path,
        "tls": node.security,
        "sni": node.sni,
        "alpn": node.alpn,
        "fp": node.fingerprint
    }
    
    # 处理网络特定配置
    if node.network == 'h2':
        config["host"] = node.h2_host
        config["path"] = node.h2_path
    elif node.network == 'grpc':
        config["serviceName"] = node.service_name
        config["mode"] = node.grpc_mode
    
    # 移除空值
    config = {k: v for k, v in config.items() if v}
    
    # JSON编码并Base64编码
    json_str = json.dumps(config, separators=(',', ':'))
    base64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    return f"vmess://{base64_str}"