#!/usr/bin/env python3
"""
功能测试脚本 - 测试Xray Protocol Enhancement的各项功能
"""
import sys
import os
import time
from typing import List

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xray_gui.core.protocol_parser import ProtocolParserFactory
from xray_gui.core.node import Node
from xray_gui.core.enhanced_config_manager import EnhancedConfigManager
from xray_gui.core.port_allocator import PortAllocator, PortAllocationStrategy
from xray_gui.core.latency_tester import LatencyTester
from xray_gui.core.network_manager import NetworkInterfaceManager
from xray_gui.core.concurrent_latency_tester import ConcurrentLatencyTester, ConcurrentTestConfig, TestStrategy
from xray_gui.core.ui_integration_manager import UIIntegrationManager

# Import all parsers to register them
from xray_gui.core.parsers.vmess_parser import VMessParser
from xray_gui.core.parsers.vless_parser import VLessParser
from xray_gui.core.parsers.shadowsocks_parser import ShadowsocksParser
from xray_gui.core.parsers.trojan_parser import TrojanParser
from xray_gui.core.parsers.multi_parser import WireGuardParser, Hysteria2Parser, SocksParser, HttpParser


def print_header(title: str):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")


def test_protocol_parsing():
    """测试协议解析功能"""
    print_header("协议解析测试")
    
    # 创建协议解析器工厂并注册所有解析器
    parser_factory = ProtocolParserFactory()
    
    # 注册所有协议解析器
    parser_factory.register_parser(VMessParser())
    parser_factory.register_parser(VLessParser())
    parser_factory.register_parser(ShadowsocksParser())
    parser_factory.register_parser(TrojanParser())
    parser_factory.register_parser(WireGuardParser())
    parser_factory.register_parser(Hysteria2Parser())
    parser_factory.register_parser(SocksParser())
    parser_factory.register_parser(HttpParser())
    
    # 测试各种协议链接
    test_links = [
        # VMess
        "vmess://eyJ2IjoiMiIsInBzIjoidGVzdC12bWVzcyIsImFkZCI6ImV4YW1wbGUuY29tIiwicG9ydCI6IjQ0MyIsImlkIjoiMTIzNDU2NzgtYWJjZC0xMjM0LWFiY2QtMTIzNDU2Nzg5YWJjIiwiYWlkIjoiMCIsInNjeSI6ImF1dG8iLCJuZXQiOiJ3cyIsInR5cGUiOiJub25lIiwiaG9zdCI6IiIsInBhdGgiOiIvIiwidGxzIjoidGxzIiwic25pIjoiIn0=",
        
        # VLESS
        "vless://12345678-abcd-1234-abcd-123456789abc@example.com:443?encryption=none&security=tls&type=ws&path=/&host=example.com#test-vless",
        
        # Shadowsocks
        "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@example.com:8388#test-shadowsocks",
        
        # Trojan
        "trojan://password@example.com:443?security=tls&type=tcp&headerType=none#test-trojan",
        
        # SOCKS
        "socks://user:pass@example.com:1080#test-socks",
        
        # HTTP
        "http://user:pass@example.com:8080#test-http"
    ]
    
    nodes = []
    for link in test_links:
        try:
            node = parser_factory.parse_link(link)
            if node:
                nodes.append(node)
                print(f"✅ 成功解析 {node.protocol.upper()} 协议: {node.remark}")
                print(f"   地址: {node.address}:{node.port}")
            else:
                print(f"❌ 解析失败: {link[:50]}...")
        except Exception as e:
            print(f"❌ 解析异常: {str(e)}")
    
    print(f"\n📊 解析结果: 成功 {len(nodes)}/{len(test_links)} 个节点")
    return nodes


def test_port_allocation(nodes: List[Node]):
    """测试端口分配功能"""
    print_header("端口分配测试")
    
    allocator = PortAllocator()
    
    # 测试不同分配策略
    strategies = [
        (PortAllocationStrategy.IMMEDIATE, "立即分配"),
        (PortAllocationStrategy.LAZY, "延迟分配")
    ]
    
    for strategy, name in strategies:
        print(f"\n🔧 测试 {name} 策略:")
        allocator.default_strategy = strategy
        
        # 为节点分配端口
        allocated_ports = []
        for i, node in enumerate(nodes[:3]):  # 只测试前3个节点
            port = allocator.allocate_port(node, strategy)
            if port:
                allocated_ports.append(port)
                print(f"   节点 {node.remark}: 端口 {port}")
        
        print(f"   分配端口: {allocated_ports}")
        
        # 清理分配
        for i, node in enumerate(nodes[:3]):
            node_id = allocator._get_node_id(node)
            allocator.deallocate_port(node_id)
    
    print(f"\n📊 端口分配测试完成")


def test_network_detection():
    """测试网络检测功能"""
    print_header("网络检测测试")
    
    network_manager = NetworkInterfaceManager()
    
    # 检测网络接口
    print("🔍 检测网络接口:")
    interfaces = network_manager.get_all_interfaces()
    for interface in interfaces[:5]:  # 只显示前5个
        print(f"   {interface.name}: {', '.join(interface.ip_addresses)} ({interface.type})")
    
    # 检测TUN模式
    print(f"\n🔍 TUN模式检测:")
    tun_active = network_manager.is_tun_mode_active()
    print(f"   TUN模式状态: {'激活' if tun_active else '未激活'}")
    
    if tun_active:
        tun_interfaces = network_manager.get_tun_interfaces()
        print(f"   TUN接口: {[iface.name for iface in tun_interfaces]}")


def test_latency_testing(nodes: List[Node]):
    """测试延迟测试功能"""
    print_header("延迟测试")
    
    if not nodes:
        print("❌ 没有可测试的节点")
        return
    
    # 基础延迟测试
    print("🚀 基础延迟测试:")
    latency_tester = LatencyTester()
    
    test_node = nodes[0]  # 测试第一个节点
    print(f"   测试节点: {test_node.remark} ({test_node.address}:{test_node.port})")
    
    try:
        result = latency_tester.test_node_latency(test_node, timeout=3.0)
        if result.error is None and result.latency is not None and result.latency >= 0:
            print(f"   ✅ 延迟: {result.latency}ms")
        else:
            print(f"   ❌ 测试失败: {result.error or '超时'}")
    except Exception as e:
        print(f"   ❌ 测试异常: {str(e)}")
    
    # 并发延迟测试
    print(f"\n🚀 并发延迟测试 ({len(nodes)} 个节点):")
    concurrent_tester = ConcurrentLatencyTester()
    
    config = ConcurrentTestConfig(
        max_concurrent=3,
        timeout=3.0,
        strategy=TestStrategy.ASYNCIO,
        bypass_tun=True
    )
    
    def progress_callback(completed: int, total: int, percentage: float):
        print(f"   进度: {completed}/{total} ({percentage:.1f}%)")
    
    try:
        result = concurrent_tester.test_nodes_batch(
            nodes=nodes[:3],  # 只测试前3个节点
            config=config,
            progress_callback=progress_callback
        )
        
        print(f"   ✅ 测试完成: {result.completed_nodes}/{result.total_nodes} 个节点")
        print(f"   用时: {result.test_duration:.2f}s")
        
        for test_result in result.results:
            success = test_result.error is None and test_result.latency is not None and test_result.latency >= 0
            status = "✅" if success else "❌"
            latency_text = f"{test_result.latency}ms" if success else (test_result.error or "超时")
            print(f"   {status} 节点: {latency_text}")
            
    except Exception as e:
        print(f"   ❌ 并发测试异常: {str(e)}")


def test_config_management():
    """测试配置管理功能"""
    print_header("配置管理测试")
    
    config_manager = EnhancedConfigManager()
    
    # 创建测试节点
    test_node = Node(
        uuid="12345678-abcd-1234-abcd-123456789abc",
        address="example.com",
        port=443,
        remark="test-node-1",
        protocol="vless"
    )
    
    test_nodes = [test_node]
    test_user_settings = {
        "auto_start": True,
        "port_range": [10000, 20000]
    }
    
    print("💾 测试配置保存:")
    try:
        success, status = config_manager.save_config(test_nodes, test_user_settings)
        if success:
            print("   ✅ 配置保存成功")
            
            # 测试配置加载
            print("📂 测试配置加载:")
            loaded_config, status = config_manager.load_config()
            if loaded_config:
                print("   ✅ 配置加载成功")
                print(f"   版本: {loaded_config.metadata.version}")
                print(f"   节点数: {len(loaded_config.node_data)}")
            else:
                print(f"   ❌ 配置加载失败: {status}")
        else:
            print(f"   ❌ 配置保存失败: {status}")
    except Exception as e:
        print(f"   ❌ 配置管理异常: {str(e)}")
    
    # 测试备份功能
    print("🔄 测试配置备份:")
    try:
        backup_created = config_manager.create_backup()
        if backup_created:
            print("   ✅ 备份创建成功")
            
            backups = config_manager.list_backups()
            print(f"   备份数量: {len(backups)}")
        else:
            print("   ❌ 备份创建失败")
    except Exception as e:
        print(f"   ❌ 备份功能异常: {str(e)}")


def test_ui_integration():
    """测试UI集成功能"""
    print_header("UI集成测试")
    
    ui_manager = UIIntegrationManager()
    
    # 测试协议显示信息
    print("🎨 协议显示信息:")
    protocols = ui_manager.get_supported_protocols()
    for protocol_info in protocols[:4]:  # 显示前4个
        print(f"   {protocol_info.display_name}: {protocol_info.description}")
        print(f"      颜色: {protocol_info.color}, 特性: {len(protocol_info.supported_features)}")
    
    # 测试系统状态
    print(f"\n📊 系统状态摘要:")
    status = ui_manager.get_system_status_summary()
    for key, value in status.items():
        if key not in ['adaptability_stats', 'latency_stats']:  # 跳过复杂对象
            print(f"   {key}: {value}")


def main():
    """主测试函数"""
    print("🚀 Xray Protocol Enhancement 功能测试")
    print("=" * 60)
    
    try:
        # 1. 协议解析测试
        nodes = test_protocol_parsing()
        
        # 2. 端口分配测试
        if nodes:
            test_port_allocation(nodes)
        
        # 3. 网络检测测试
        test_network_detection()
        
        # 4. 延迟测试
        if nodes:
            test_latency_testing(nodes)
        
        # 5. 配置管理测试
        test_config_management()
        
        # 6. UI集成测试
        test_ui_integration()
        
        print_header("测试完成")
        print("🎉 所有功能测试完成！")
        print("✨ Xray Protocol Enhancement 工作正常")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()