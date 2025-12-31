"""
VLESS协议解析器
"""
import urllib.parse
from typing import Optional, List
from ..protocol_parser import ProtocolParser
from ..node import Node


class VLessParser(ProtocolParser):
    """VLESS协议解析器"""
    
    def get_protocol_name(self) -> str:
        return "vless"
    
    def get_supported_schemes(self) -> List[str]:
        return ["vless://"]
    
    def parse_link(self, link: str) -> Optional[Node]:
        """
        解析VLESS链接为Node对象
        
        Args:
            link: vless://格式的链接
            
        Returns:
            Node对象，解析失败返回None
        """
        link = link.strip()
        if not self.validate_link(link):
            return None
        
        try:
            # 处理备注
            if "#" in link:
                main_part = link.split("#")[0][8:]  # 去掉vless://前缀
                remark = urllib.parse.unquote(link.split("#")[1])
            else:
                main_part = link[8:]  # 去掉vless://前缀
                remark = "Untitled"
            
            # 处理参数
            if "?" in main_part:
                user_info, query_string = main_part.split("?", 1)
            else:
                user_info, query_string = main_part, ""
            
            if "@" not in user_info:
                return None
                
            uuid, addr_port = user_info.split("@", 1)
            
            # UUID不能为空
            if not uuid.strip():
                return None
            
            # 处理IPv6地址
            if addr_port.startswith("["):
                # IPv6格式: [::1]:port
                bracket_end = addr_port.rfind("]")
                if bracket_end == -1:
                    return None
                addr = addr_port[1:bracket_end]
                port_part = addr_port[bracket_end + 1:]
                if not port_part.startswith(":"):
                    return None
                port = int(port_part[1:])
            else:
                # IPv4格式: host:port
                if ":" not in addr_port:
                    return None
                addr, port_str = addr_port.rsplit(":", 1)
                port = int(port_str)
            
            # 解析查询参数
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
                service_name=get_param("serviceName"),
                path=get_param("path"),
                host=get_param("host"),
                alpn=get_param("alpn")
            )
        except (ValueError, IndexError, KeyError) as e:
            # 解析失败，返回None
            return None