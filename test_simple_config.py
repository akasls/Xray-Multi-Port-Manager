#!/usr/bin/env python3
"""
简单的配置持久化测试
"""
import tempfile
import shutil
from xray_gui.core.enhanced_config_manager import EnhancedConfigManager, ConfigStatus
from xray_gui.core.node import Node

def test_config_persistence():
    """测试配置持久化功能"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建配置管理器
        config_manager = EnhancedConfigManager(
            config_dir=temp_dir,
            config_file="test_config.json",
            backup_file="test_config.backup.json"
        )
        
        # 创建测试节点
        nodes = [
            Node(
                uuid="test-uuid-1",
                remark="test_node_1",
                protocol="vless",
                address="127.0.0.1",
                port=443
            ),
            Node(
                uuid="test-uuid-2",
                remark="test_node_2",
                protocol="vmess",
                address="192.168.1.1",
                port=80,
                alter_id=0
            )
        ]
        
        # 用户设置
        user_settings = {
            'theme': 'dark',
            'auto_start': True,
            'log_level': 'info'
        }
        
        print("Testing config persistence...")
        
        # 保存配置
        success, status = config_manager.save_config(nodes, user_settings)
        print(f"Save result: success={success}, status={status}")
        assert success, "配置保存应该成功"
        assert status == ConfigStatus.VALID, "保存后状态应该是有效的"
        
        # 重新加载配置
        loaded_config, load_status = config_manager.load_config()
        print(f"Load result: config={loaded_config is not None}, status={load_status}")
        assert loaded_config is not None, "应该能够加载配置"
        assert load_status == ConfigStatus.VALID, "加载状态应该是有效的"
        
        # 验证节点数据一致性
        assert len(loaded_config.node_data) == len(nodes), f"节点数量应该一致: {len(loaded_config.node_data)} vs {len(nodes)}"
        
        # 验证每个节点的关键信息
        for i, original_node in enumerate(nodes):
            loaded_node_data = loaded_config.node_data[i]
            assert loaded_node_data['remark'] == original_node.remark, f"节点名称应该一致: {loaded_node_data['remark']} vs {original_node.remark}"
            assert loaded_node_data['protocol'] == original_node.protocol, f"协议应该一致: {loaded_node_data['protocol']} vs {original_node.protocol}"
            assert loaded_node_data['address'] == original_node.address, f"地址应该一致: {loaded_node_data['address']} vs {original_node.address}"
            assert loaded_node_data['port'] == original_node.port, f"端口应该一致: {loaded_node_data['port']} vs {original_node.port}"
        
        # 验证用户设置一致性
        assert loaded_config.user_settings == user_settings, f"用户设置应该一致: {loaded_config.user_settings} vs {user_settings}"
        
        # 验证端口分配一致性
        expected_ports = {node.remark: getattr(node, 'local_port', None) for node in nodes if hasattr(node, 'local_port') and node.local_port}
        # 由于我们的测试节点没有local_port，这个测试会是空的
        print(f"Port allocations: {loaded_config.port_allocations}")
        print(f"Expected ports: {expected_ports}")
        
        # 验证元数据包含必要信息
        assert loaded_config.metadata.created_at is not None, "创建时间应该存在"
        assert loaded_config.metadata.last_modified is not None, "修改时间应该存在"
        assert loaded_config.metadata.node_count == len(nodes), f"节点计数应该一致: {loaded_config.metadata.node_count} vs {len(nodes)}"
        assert loaded_config.metadata.checksum is not None, "校验和应该存在"
        
        print("✅ 配置持久化往返一致性测试通过！")
        
        # 测试备份功能
        print("\nTesting backup functionality...")
        backup_success = config_manager.create_backup()
        assert backup_success, "应该能够创建备份"
        
        # 修改配置
        new_node = Node(
            uuid="test-uuid-3",
            remark="test_new_node",
            protocol="shadowsocks",
            address="10.0.0.1",
            port=8388,
            method="aes-256-gcm",
            password="test-password"
        )
        modified_nodes = nodes + [new_node]
        
        success, _ = config_manager.save_config(modified_nodes)
        assert success, "修改后的配置应该保存成功"
        
        # 验证修改后的配置
        loaded_config, _ = config_manager.load_config()
        assert len(loaded_config.node_data) == len(modified_nodes), "修改后节点数量应该正确"
        
        # 从备份恢复
        restore_success = config_manager.restore_from_backup()
        assert restore_success, "应该能够从备份恢复"
        
        # 验证恢复后的配置
        restored_config, _ = config_manager.load_config()
        assert len(restored_config.node_data) == len(nodes), "恢复后节点数量应该与原始一致"
        
        print("✅ 配置备份和恢复功能测试通过！")
        
        # 测试配置验证
        print("\nTesting config validation...")
        is_valid, message = config_manager.validate_config()
        assert is_valid, f"有效配置应该通过验证: {message}"
        
        print("✅ 配置验证功能测试通过！")
        
        print("\n🎉 所有配置持久化测试都通过了！")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_config_persistence()