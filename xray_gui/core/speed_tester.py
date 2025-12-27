"""
速度测试器 - 测试节点连接速度
"""
import asyncio
import socket
import time
from typing import List, Callable, Optional
from .node import Node


class SpeedTester:
    """节点速度测试器"""
    
    def __init__(self, timeout: float = 5.0, concurrent: int = 10):
        """
        初始化速度测试器
        
        Args:
            timeout: 超时时间（秒）
            concurrent: 并发测试数量
        """
        self.timeout = timeout
        self.concurrent = concurrent
    
    async def test_node(self, node: Node) -> int:
        """
        测试单个节点延迟
        
        Args:
            node: 节点对象
            
        Returns:
            延迟(ms)，超时返回 -1
        """
        try:
            start_time = time.time()
            
            # 使用 asyncio 进行 TCP 连接测试
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(node.address, node.port),
                timeout=self.timeout
            )
            
            # 计算延迟
            latency = int((time.time() - start_time) * 1000)
            
            # 关闭连接
            writer.close()
            await writer.wait_closed()
            
            node.latency = latency
            return latency
            
        except asyncio.TimeoutError:
            node.latency = -1
            return -1
        except Exception:
            node.latency = -1
            return -1
    
    async def test_nodes(self, nodes: List[Node],
                         progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Node]:
        """
        批量测试节点
        
        Args:
            nodes: 节点列表
            progress_callback: 进度回调(当前, 总数)
            
        Returns:
            更新了延迟的节点列表
        """
        total = len(nodes)
        completed = 0
        
        # 使用信号量限制并发
        semaphore = asyncio.Semaphore(self.concurrent)
        
        async def test_with_semaphore(node: Node) -> Node:
            nonlocal completed
            async with semaphore:
                await self.test_node(node)
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                return node
        
        # 并发测试所有节点
        tasks = [test_with_semaphore(node) for node in nodes]
        await asyncio.gather(*tasks)
        
        return nodes
    
    def test_node_sync(self, node: Node) -> int:
        """
        同步测试单个节点（用于非异步环境）
        
        Args:
            node: 节点对象
            
        Returns:
            延迟(ms)，超时返回 -1
        """
        try:
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            result = sock.connect_ex((node.address, node.port))
            
            if result == 0:
                latency = int((time.time() - start_time) * 1000)
                node.latency = latency
            else:
                node.latency = -1
                latency = -1
            
            sock.close()
            return latency
            
        except Exception:
            node.latency = -1
            return -1
    
    def test_nodes_sync(self, nodes: List[Node],
                        progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Node]:
        """
        同步批量测试节点
        
        Args:
            nodes: 节点列表
            progress_callback: 进度回调(当前, 总数)
            
        Returns:
            更新了延迟的节点列表
        """
        total = len(nodes)
        
        for i, node in enumerate(nodes):
            self.test_node_sync(node)
            if progress_callback:
                progress_callback(i + 1, total)
        
        return nodes
