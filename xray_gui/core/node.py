"""
Node 数据模型 - 代理节点数据结构
"""
from dataclasses import dataclass, field
from typing import Optional
import urllib.parse


@dataclass
class Node:
    """代理节点数据模型"""
    uuid: str
    address: str
    port: int
    remark: str
    protocol: str = "vless"
    security: str = ""
    sni: str = ""
    flow: str = ""
    fingerprint: str = ""
    public_key: str = ""
    short_id: str = ""
    network: str = "tcp"
    service_name: str = ""
    latency: Optional[int] = None  # 延迟(ms)，None表示未测试，-1表示超时
    local_port: Optional[int] = None  # 分配的本地端口

    def to_outbound_config(self) -> dict:
        """转换为Xray outbound配置"""
        user_settings = {
            "id": self.uuid,
            "encryption": "none"
        }
        if self.flow:
            user_settings["flow"] = self.flow

        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": self.protocol,
            "settings": {
                "vnext": [{
                    "address": self.address,
                    "port": self.port,
                    "users": [user_settings]
                }]
            },
            "streamSettings": {
                "network": self.network,
                "security": self.security
            }
        }

        # Reality 协议设置
        if self.security == "reality":
            outbound["streamSettings"]["realitySettings"] = {
                "show": False,
                "fingerprint": self.fingerprint or "chrome",
                "serverName": self.sni,
                "publicKey": self.public_key,
                "shortId": self.short_id,
                "spiderX": ""
            }
        # TLS 设置
        elif self.security == "tls":
            outbound["streamSettings"]["tlsSettings"] = {
                "serverName": self.sni
            }

        # gRPC 设置
        if self.network == "grpc":
            outbound["streamSettings"]["grpcSettings"] = {
                "serviceName": self.service_name
            }

        return outbound

    def to_inbound_config(self) -> dict:
        """生成对应的 inbound 配置"""
        if not self.local_port:
            raise ValueError("Node must have local_port assigned")
        
        return {
            "port": self.local_port,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            },
            "settings": {
                "auth": "noauth",
                "udp": True
            },
            "tag": f"in-{self.local_port}"
        }

    def to_routing_rule(self) -> dict:
        """生成路由规则"""
        if not self.local_port:
            raise ValueError("Node must have local_port assigned")
        
        return {
            "type": "field",
            "inboundTag": [f"in-{self.local_port}"],
            "outboundTag": f"proxy-{self.local_port}"
        }

    @property
    def latency_display(self) -> str:
        """延迟显示文本"""
        if self.latency is None:
            return "未测试"
        elif self.latency == -1:
            return "超时"
        else:
            return f"{self.latency}ms"

    def matches_keyword(self, keyword: str) -> bool:
        """检查节点名称是否包含关键词（大小写不敏感）"""
        return keyword.lower() in self.remark.lower()


def parse_vless_link(link: str) -> Optional[Node]:
    """
    解析 VLESS 链接为 Node 对象
    
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
        addr, port = addr_port.split(":")
        
        params = urllib.parse.parse_qs(query_string)
        get_param = lambda k: params.get(k, [''])[0]

        return Node(
            uuid=uuid,
            address=addr,
            port=int(port),
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
