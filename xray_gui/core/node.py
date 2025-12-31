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
    
    # VMess特定字段
    alter_id: int = 0  # VMess的alterId
    method: str = ""   # 加密方法（VMess/Shadowsocks）
    password: str = "" # 密码（Shadowsocks/Trojan）
    
    # WebSocket相关字段
    path: str = ""     # WebSocket路径
    host: str = ""     # WebSocket Host头
    
    # HTTP/2相关字段
    h2_path: str = ""  # HTTP/2路径
    h2_host: str = ""  # HTTP/2 Host
    
    # gRPC相关字段（service_name已存在）
    grpc_mode: str = "gun"  # gRPC模式
    
    # TLS相关字段
    tls_version: str = ""   # TLS版本
    alpn: str = ""          # ALPN
    
    # WireGuard特定字段
    private_key: str = ""      # WireGuard私钥
    public_key_wg: str = ""    # WireGuard公钥（区别于VLESS的public_key）
    endpoint: str = ""         # WireGuard端点
    allowed_ips: str = ""      # WireGuard允许IP
    
    # Hysteria2特定字段
    obfs: str = ""             # Hysteria2混淆
    auth: str = ""             # Hysteria2认证
    up_mbps: int = 0           # Hysteria2上行带宽
    down_mbps: int = 0         # Hysteria2下行带宽
    
    latency: Optional[int] = None  # 延迟(ms)，None表示未测试，-1表示超时
    local_port: Optional[int] = None  # 分配的本地端口

    def to_outbound_config(self) -> dict:
        """转换为Xray outbound配置"""
        if self.protocol == "vmess":
            return self._to_vmess_outbound_config()
        elif self.protocol == "vless":
            return self._to_vless_outbound_config()
        elif self.protocol == "shadowsocks":
            return self._to_shadowsocks_outbound_config()
        elif self.protocol == "trojan":
            return self._to_trojan_outbound_config()
        elif self.protocol == "socks":
            return self._to_socks_outbound_config()
        elif self.protocol == "http":
            return self._to_http_outbound_config()
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol}")
    
    def _to_socks_outbound_config(self) -> dict:
        """转换为SOCKS outbound配置"""
        server_config = {
            "address": self.address,
            "port": self.port
        }
        
        # 添加认证信息
        if self.uuid or self.password:  # uuid字段存储用户名
            server_config["users"] = [{
                "user": self.uuid,
                "pass": self.password
            }]
        
        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": "socks",
            "settings": {
                "servers": [server_config]
            }
        }
        
        return outbound
    
    def _to_http_outbound_config(self) -> dict:
        """转换为HTTP outbound配置"""
        server_config = {
            "address": self.address,
            "port": self.port
        }
        
        # 添加认证信息
        if self.uuid or self.password:  # uuid字段存储用户名
            server_config["users"] = [{
                "user": self.uuid,
                "pass": self.password
            }]
        
        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": "http",
            "settings": {
                "servers": [server_config]
            }
        }
        
        # HTTP代理的TLS设置
        if self.security == "tls":
            outbound["streamSettings"] = {
                "security": "tls",
                "tlsSettings": {}
            }
            if self.sni:
                outbound["streamSettings"]["tlsSettings"]["serverName"] = self.sni
        
        return outbound
    
    def _to_trojan_outbound_config(self) -> dict:
        """转换为Trojan outbound配置"""
        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": "trojan",
            "settings": {
                "servers": [{
                    "address": self.address,
                    "port": self.port,
                    "password": self.password
                }]
            },
            "streamSettings": {
                "network": self.network,
                "security": self.security
            }
        }
        
        # TLS设置（Trojan通常使用TLS）
        if self.security == "tls":
            tls_settings = {}
            if self.sni:
                tls_settings["serverName"] = self.sni
            if self.alpn:
                tls_settings["alpn"] = self.alpn.split(',')
            if self.fingerprint:
                tls_settings["fingerprint"] = self.fingerprint
            
            if tls_settings:
                outbound["streamSettings"]["tlsSettings"] = tls_settings
        
        # 网络传输设置
        if self.network == "ws":
            ws_settings = {}
            if self.path:
                ws_settings["path"] = self.path
            if self.host:
                ws_settings["headers"] = {"Host": self.host}
            
            if ws_settings:
                outbound["streamSettings"]["wsSettings"] = ws_settings
                
        elif self.network == "h2":
            h2_settings = {}
            if self.h2_path:
                h2_settings["path"] = self.h2_path
            if self.h2_host:
                h2_settings["host"] = [self.h2_host]
            
            if h2_settings:
                outbound["streamSettings"]["httpSettings"] = h2_settings
                
        elif self.network == "grpc":
            grpc_settings = {}
            if self.service_name:
                grpc_settings["serviceName"] = self.service_name
            if self.grpc_mode:
                grpc_settings["multiMode"] = (self.grpc_mode == "multi")
            
            if grpc_settings:
                outbound["streamSettings"]["grpcSettings"] = grpc_settings
        
        return outbound
    
    def _to_shadowsocks_outbound_config(self) -> dict:
        """转换为Shadowsocks outbound配置"""
        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": "shadowsocks",
            "settings": {
                "servers": [{
                    "address": self.address,
                    "port": self.port,
                    "method": self.method,
                    "password": self.password
                }]
            }
        }
        
        return outbound
    
    def _to_vmess_outbound_config(self) -> dict:
        """转换为VMess outbound配置"""
        user_settings = {
            "id": self.uuid,
            "alterId": self.alter_id,
            "security": "auto"
        }

        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": "vmess",
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

        # TLS设置
        if self.security == "tls":
            tls_settings = {}
            if self.sni:
                tls_settings["serverName"] = self.sni
            if self.alpn:
                tls_settings["alpn"] = self.alpn.split(',')
            if self.fingerprint:
                tls_settings["fingerprint"] = self.fingerprint
            
            if tls_settings:
                outbound["streamSettings"]["tlsSettings"] = tls_settings

        # 网络传输设置
        if self.network == "ws":
            ws_settings = {}
            if self.path:
                ws_settings["path"] = self.path
            if self.host:
                ws_settings["headers"] = {"Host": self.host}
            
            if ws_settings:
                outbound["streamSettings"]["wsSettings"] = ws_settings
                
        elif self.network == "h2":
            h2_settings = {}
            if self.h2_path:
                h2_settings["path"] = self.h2_path
            if self.h2_host:
                h2_settings["host"] = [self.h2_host]
            
            if h2_settings:
                outbound["streamSettings"]["httpSettings"] = h2_settings
                
        elif self.network == "grpc":
            grpc_settings = {}
            if self.service_name:
                grpc_settings["serviceName"] = self.service_name
            if self.grpc_mode:
                grpc_settings["multiMode"] = (self.grpc_mode == "multi")
            
            if grpc_settings:
                outbound["streamSettings"]["grpcSettings"] = grpc_settings

        return outbound
    
    def _to_vless_outbound_config(self) -> dict:
        """转换为VLESS outbound配置"""
        user_settings = {
            "id": self.uuid,
            "encryption": "none"
        }
        if self.flow:
            user_settings["flow"] = self.flow

        outbound = {
            "tag": f"proxy-{self.local_port}" if self.local_port else f"proxy-{self.port}",
            "protocol": "vless",
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
            tls_settings = {}
            if self.sni:
                tls_settings["serverName"] = self.sni
            if self.alpn:
                tls_settings["alpn"] = self.alpn.split(',')
            if self.fingerprint:
                tls_settings["fingerprint"] = self.fingerprint
            
            if tls_settings:
                outbound["streamSettings"]["tlsSettings"] = tls_settings

        # 网络传输设置
        if self.network == "ws":
            ws_settings = {}
            if self.path:
                ws_settings["path"] = self.path
            if self.host:
                ws_settings["headers"] = {"Host": self.host}
            
            if ws_settings:
                outbound["streamSettings"]["wsSettings"] = ws_settings
                
        elif self.network == "h2":
            h2_settings = {}
            if self.h2_path:
                h2_settings["path"] = self.h2_path
            if self.h2_host:
                h2_settings["host"] = [self.h2_host]
            
            if h2_settings:
                outbound["streamSettings"]["httpSettings"] = h2_settings
                
        elif self.network == "grpc":
            grpc_settings = {}
            if self.service_name:
                grpc_settings["serviceName"] = self.service_name
            if self.grpc_mode:
                grpc_settings["multiMode"] = (self.grpc_mode == "multi")
            
            if grpc_settings:
                outbound["streamSettings"]["grpcSettings"] = grpc_settings

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
            service_name=get_param("serviceName"),
            path=get_param("path"),
            host=get_param("host"),
            alpn=get_param("alpn")
        )
    except Exception:
        return None
