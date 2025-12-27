"""
订阅管理器 - 获取和解析订阅内容
"""
import base64
import asyncio
from typing import List, Optional, Callable
import aiohttp

from .node import Node
from .node_parser import parse_links


class SubscriptionError(Exception):
    """订阅相关错误"""
    pass


class SubscriptionManager:
    """订阅管理器"""
    
    def __init__(self, timeout: float = 15.0):
        """
        初始化订阅管理器
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
        self._nodes: List[Node] = []
        self._raw_links: List[str] = []
    
    @property
    def nodes(self) -> List[Node]:
        """获取当前节点列表"""
        return self._nodes.copy()
    
    @property
    def node_count(self) -> int:
        """获取节点数量"""
        return len(self._nodes)
    
    async def fetch_subscription(self, url: str) -> str:
        """
        异步获取订阅内容
        
        Args:
            url: 订阅链接
            
        Returns:
            原始订阅内容字符串
            
        Raises:
            SubscriptionError: 获取失败时抛出
        """
        if not url or not url.startswith(('http://', 'https://')):
            raise SubscriptionError("无效的订阅链接格式")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise SubscriptionError(f"HTTP 错误: {response.status}")
                    return await response.text()
        except asyncio.TimeoutError:
            raise SubscriptionError("连接超时，请检查网络")
        except aiohttp.ClientError as e:
            raise SubscriptionError(f"网络错误: {str(e)}")
        except Exception as e:
            raise SubscriptionError(f"获取订阅失败: {str(e)}")
    
    def decode_content(self, content: str) -> List[str]:
        """
        解码订阅内容（支持 Base64）
        
        Args:
            content: 原始内容
            
        Returns:
            节点链接列表
        """
        content = content.strip()
        
        # 尝试 Base64 解码
        try:
            # 处理可能的 Padding 问题
            missing_padding = len(content) % 4
            if missing_padding:
                content += '=' * (4 - missing_padding)
            
            decoded = base64.b64decode(content).decode('utf-8')
            links = decoded.strip().splitlines()
            
            # 验证解码结果是否包含有效链接
            if any(link.startswith(('vless://', 'vmess://', 'ss://')) for link in links):
                self._raw_links = links
                return links
        except Exception:
            pass
        
        # 如果 Base64 解码失败，尝试直接按行读取
        links = content.strip().splitlines()
        self._raw_links = links
        return links
    
    def parse_nodes(self, links: List[str]) -> List[Node]:
        """
        解析节点链接为 Node 对象
        
        Args:
            links: 节点链接列表
            
        Returns:
            Node 对象列表
        """
        self._nodes = parse_links(links)
        return self._nodes
    
    async def refresh(self, url: str, 
                      progress_callback: Optional[Callable[[str], None]] = None) -> List[Node]:
        """
        刷新订阅（获取 + 解码 + 解析）
        
        Args:
            url: 订阅链接
            progress_callback: 进度回调函数
            
        Returns:
            解析后的节点列表
            
        Raises:
            SubscriptionError: 刷新失败时抛出
        """
        if progress_callback:
            progress_callback("正在获取订阅...")
        
        content = await self.fetch_subscription(url)
        
        if progress_callback:
            progress_callback("正在解码内容...")
        
        links = self.decode_content(content)
        
        if progress_callback:
            progress_callback("正在解析节点...")
        
        nodes = self.parse_nodes(links)
        
        if not nodes:
            raise SubscriptionError("未找到有效节点，请检查订阅内容")
        
        if progress_callback:
            progress_callback(f"完成！共 {len(nodes)} 个节点")
        
        return nodes
    
    def refresh_sync(self, url: str) -> List[Node]:
        """
        同步刷新订阅（用于非异步环境）
        
        Args:
            url: 订阅链接
            
        Returns:
            解析后的节点列表
        """
        return asyncio.run(self.refresh(url))


def encode_to_base64(links: List[str]) -> str:
    """
    将链接列表编码为 Base64
    
    Args:
        links: 链接列表
        
    Returns:
        Base64 编码的字符串
    """
    content = '\n'.join(links)
    return base64.b64encode(content.encode('utf-8')).decode('utf-8')


def decode_from_base64(content: str) -> List[str]:
    """
    从 Base64 解码链接列表
    
    Args:
        content: Base64 编码的内容
        
    Returns:
        链接列表
    """
    content = content.strip()
    missing_padding = len(content) % 4
    if missing_padding:
        content += '=' * (4 - missing_padding)
    
    decoded = base64.b64decode(content).decode('utf-8')
    return decoded.strip().splitlines()
