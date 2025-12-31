"""
网络接口管理器 - 检测和管理系统网络接口
"""
import subprocess
import platform
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class NetworkInterface:
    """网络接口信息"""
    name: str
    display_name: str
    type: str  # 'physical', 'virtual', 'tun', 'tap', 'loopback'
    status: str  # 'up', 'down', 'unknown'
    ip_addresses: List[str]
    is_default: bool = False


class NetworkInterfaceManager:
    """网络接口管理器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self._interfaces_cache: Optional[List[NetworkInterface]] = None
        self._cache_valid = False
    
    def get_all_interfaces(self, refresh: bool = False) -> List[NetworkInterface]:
        """
        获取所有网络接口
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            网络接口列表
        """
        if refresh or not self._cache_valid:
            self._refresh_interfaces()
        
        return self._interfaces_cache or []
    
    def get_virtual_interfaces(self, refresh: bool = False) -> List[NetworkInterface]:
        """
        获取虚拟网络接口（包括TUN/TAP）
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            虚拟网络接口列表
        """
        all_interfaces = self.get_all_interfaces(refresh)
        return [iface for iface in all_interfaces if iface.type in ['virtual', 'tun', 'tap']]
    
    def get_tun_interfaces(self, refresh: bool = False) -> List[NetworkInterface]:
        """
        获取TUN接口
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            TUN接口列表
        """
        all_interfaces = self.get_all_interfaces(refresh)
        return [iface for iface in all_interfaces if iface.type == 'tun']
    
    def get_physical_interfaces(self, refresh: bool = False) -> List[NetworkInterface]:
        """
        获取物理网络接口
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            物理网络接口列表
        """
        all_interfaces = self.get_all_interfaces(refresh)
        return [iface for iface in all_interfaces if iface.type == 'physical']
    
    def get_default_interface(self, refresh: bool = False) -> Optional[NetworkInterface]:
        """
        获取默认网络接口
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            默认网络接口，如果没有则返回None
        """
        all_interfaces = self.get_all_interfaces(refresh)
        for iface in all_interfaces:
            if iface.is_default:
                return iface
        return None
    
    def is_tun_mode_active(self, refresh: bool = False) -> bool:
        """
        检测系统是否启用TUN模式
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            是否启用TUN模式
        """
        tun_interfaces = self.get_tun_interfaces(refresh)
        return any(iface.status == 'up' for iface in tun_interfaces)
    
    def get_active_tun_interfaces(self, refresh: bool = False) -> List[NetworkInterface]:
        """
        获取活跃的TUN接口
        
        Args:
            refresh: 是否刷新缓存
            
        Returns:
            活跃的TUN接口列表
        """
        tun_interfaces = self.get_tun_interfaces(refresh)
        return [iface for iface in tun_interfaces if iface.status == 'up']
    
    def _refresh_interfaces(self) -> None:
        """刷新网络接口缓存"""
        try:
            if self.system == 'windows':
                self._interfaces_cache = self._get_windows_interfaces()
            elif self.system == 'linux':
                self._interfaces_cache = self._get_linux_interfaces()
            elif self.system == 'darwin':  # macOS
                self._interfaces_cache = self._get_macos_interfaces()
            else:
                self._interfaces_cache = []
            
            self._cache_valid = True
        except Exception:
            self._interfaces_cache = []
            self._cache_valid = False
    
    def _get_windows_interfaces(self) -> List[NetworkInterface]:
        """获取Windows网络接口"""
        interfaces = []
        
        try:
            # 使用netsh命令获取接口信息
            result = subprocess.run(
                ['netsh', 'interface', 'show', 'interface'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',   # Ignore encoding errors
                timeout=10
            )
            
            if result.returncode == 0:
                interfaces.extend(self._parse_windows_netsh_output(result.stdout))
            
            # 获取IP地址信息
            self._add_windows_ip_info(interfaces)
            
        except Exception:
            pass
        
        return interfaces
    
    def _parse_windows_netsh_output(self, output: str) -> List[NetworkInterface]:
        """解析Windows netsh输出"""
        interfaces = []
        lines = output.strip().split('\n')
        
        # 找到分隔线，从分隔线后开始解析
        start_index = 0
        for i, line in enumerate(lines):
            if '---' in line:
                start_index = i + 1
                break
        
        for line in lines[start_index:]:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) >= 4:
                admin_state = parts[0]
                state = parts[1]
                type_name = parts[2]
                interface_name = ' '.join(parts[3:])
                
                # 确定接口类型
                iface_type = self._determine_interface_type(interface_name, type_name)
                
                # 确定状态
                status = 'up' if state.lower() == 'connected' else 'down'
                
                interface = NetworkInterface(
                    name=interface_name,
                    display_name=interface_name,
                    type=iface_type,
                    status=status,
                    ip_addresses=[]
                )
                
                interfaces.append(interface)
        
        return interfaces
    
    def _add_windows_ip_info(self, interfaces: List[NetworkInterface]) -> None:
        """为Windows接口添加IP地址信息"""
        try:
            # 使用ipconfig获取IP信息
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                encoding='utf-8',  # Try UTF-8 first
                errors='ignore',   # Ignore encoding errors
                timeout=10
            )
            
            if result.returncode == 0:
                self._parse_windows_ipconfig(result.stdout, interfaces)
                
        except Exception:
            pass
    
    def _parse_windows_ipconfig(self, output: str, interfaces: List[NetworkInterface]) -> None:
        """解析Windows ipconfig输出"""
        current_adapter = None
        current_ips = []
        
        for line in output.split('\n'):
            line = line.strip()
            
            # 检测适配器名称
            if '适配器' in line or 'adapter' in line.lower():
                # 保存上一个适配器的信息
                if current_adapter and current_ips:
                    for iface in interfaces:
                        if current_adapter in iface.name or iface.name in current_adapter:
                            iface.ip_addresses = current_ips[:]
                            break
                
                current_adapter = line
                current_ips = []
            
            # 检测IP地址
            elif 'IPv4' in line or 'IP Address' in line:
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    current_ips.append(ip_match.group(1))
        
        # 处理最后一个适配器
        if current_adapter and current_ips:
            for iface in interfaces:
                if current_adapter in iface.name or iface.name in current_adapter:
                    iface.ip_addresses = current_ips[:]
                    break
    
    def _get_linux_interfaces(self) -> List[NetworkInterface]:
        """获取Linux网络接口"""
        interfaces = []
        
        try:
            # 使用ip命令获取接口信息
            result = subprocess.run(
                ['ip', 'addr', 'show'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                interfaces = self._parse_linux_ip_output(result.stdout)
                
        except Exception:
            pass
        
        return interfaces
    
    def _parse_linux_ip_output(self, output: str) -> List[NetworkInterface]:
        """解析Linux ip命令输出"""
        interfaces = []
        current_interface = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            # 接口行
            if re.match(r'^\d+:', line):
                if current_interface:
                    interfaces.append(current_interface)
                
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1].rstrip(':')
                    flags = line
                    
                    # 确定状态
                    status = 'up' if 'UP' in flags else 'down'
                    
                    # 确定类型
                    iface_type = self._determine_interface_type(name)
                    
                    current_interface = NetworkInterface(
                        name=name,
                        display_name=name,
                        type=iface_type,
                        status=status,
                        ip_addresses=[]
                    )
            
            # IP地址行
            elif line.startswith('inet ') and current_interface:
                ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    current_interface.ip_addresses.append(ip_match.group(1))
        
        if current_interface:
            interfaces.append(current_interface)
        
        return interfaces
    
    def _get_macos_interfaces(self) -> List[NetworkInterface]:
        """获取macOS网络接口"""
        # macOS使用类似Linux的方法
        return self._get_linux_interfaces()
    
    def _determine_interface_type(self, name: str, type_name: str = "") -> str:
        """
        确定接口类型
        
        Args:
            name: 接口名称
            type_name: 类型名称（Windows）
            
        Returns:
            接口类型
        """
        name_lower = name.lower()
        type_lower = type_name.lower()
        
        # TUN接口
        if ('tun' in name_lower or 'tap' in name_lower or 
            'wintun' in name_lower or 'openvpn' in name_lower or
            'wireguard' in name_lower):
            return 'tun'
        
        # 虚拟接口
        if ('virtual' in name_lower or 'virtual' in type_lower or
            'vmware' in name_lower or 'virtualbox' in name_lower or
            'hyper-v' in name_lower or 'docker' in name_lower):
            return 'virtual'
        
        # 回环接口
        if name_lower in ['lo', 'loopback'] or 'loopback' in type_lower:
            return 'loopback'
        
        # 默认为物理接口
        return 'physical'


# 全局网络接口管理器实例
network_manager = NetworkInterfaceManager()