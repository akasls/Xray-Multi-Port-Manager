#!/usr/bin/env python3
"""
简化的配置管理器单元测试
"""
import tempfile
import shutil
import os
import json
from xray_gui.core.enhanced_config_manager import EnhancedConfigManager, ConfigStatus
from xray_gui.core.node import Node

def test_config_manager_unit_tests():
    """运行配置管理器的单元测试"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        config_manager = EnhancedConfigManager(
            config_dir=temp_dir,
            config_file="test_config.json",
            backup_file="test_config.backup.json"
        )
        
        # 创建测试节点
        test_nodes = [
            Node(
                uuid="test-uuid-1",
                remark="test_node_1",
                protocol="vless",
                address="127.0.0.1",
                port=443,
                security="tls",
                sni="example.com"
            ),
            Node(
                uuid="test-uuid-2",
                remark="test_node_2",
                protocol="vmess",
                address="192.168.1.1",
                port=80,
                alter_id=0,
                method="aes-128-gcm"
            )
        ]
        
        test_user_settings = {
            'theme': 'dark',
            'auto_start': True,
            'log_level': 'info'
        }
        
        print("1. 测试配置保存和加载...")
        
        # 保存配置
        success, status = config_manager.save_config(test_nodes, test_user_settings)
        assert success, "配置保存应该成功"
        assert status == ConfigStatus.VALID, "保存后状态应该是有效的"
        
        # 验证配置文件存在
        assert config_manager.config_file.exists(), "配置文件应该存在"
        
        # 加载配置
        loaded_config, load_status = config_manager.load_config()
        assert loaded_config is not None, "应该能够加载配置"
        assert load_status == ConfigStatus.VALID, "加载状态应该是有效的"
        
        # 验证数据一致性
        assert len(loaded_config.node_data) == len(test_nodes), "节点数量应该一致"
        assert loaded_config.user_settings == test_user_settings, "用户设置应该一致"
        assert loaded_config.metadata.node_count == len(test_nodes), "元数据节点计数应该正确"
        
        print("✅ 配置保存和加载测试通过")
        
        print("2. 测试备份创建和恢复...")
        
        # 创建备份
        backup_success = config_manager.create_backup()
        assert backup_success, "应该能够创建备份"
        assert config_manager.backup_file.exists(), "备份文件应该存在"
        
        # 修改配置
        new_node = Node(
            uuid="test-uuid-3",
            remark="new_test_node",
            protocol="shadowsocks",
            address="10.0.0.1",
            port=8388,
            method="aes-256-gcm",
            password="test-password"
        )
        modified_nodes = test_nodes + [new_node]
        
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
        assert len(restored_config.node_data) == len(test_nodes), "恢复后节点数量应该与原始一致"
        
        print("✅ 备份创建和恢复测试通过")
        
        print("3. 测试配置验证...")
        
        # 验证有效配置
        is_valid, message = config_manager.validate_config()
        assert is_valid, f"有效配置应该通过验证: {message}"
        assert "valid" in message.lower(), "验证消息应该包含'valid'"
        
        # 创建无效配置文件
        invalid_config_path = os.path.join(temp_dir, "invalid_config.json")
        with open(invalid_config_path, 'w') as f:
            json.dump({"invalid": "structure"}, f)
        
        # 验证无效配置
        is_valid, message = config_manager.validate_config(invalid_config_path)
        assert not is_valid, "无效配置应该验证失败"
        assert "Missing required field" in message, "应该报告缺少必要字段"
        
        print("✅ 配置验证测试通过")
        
        print("4. 测试损坏配置处理...")
        
        # 删除备份文件以确保不会从备份恢复
        if config_manager.backup_file.exists():
            os.remove(config_manager.backup_file)
        
        # 创建损坏的配置文件
        with open(config_manager.config_file, 'w') as f:
            f.write("invalid json content {")
        
        # 清除缓存以强制重新加载
        config_manager._current_config = None
        
        # 尝试加载损坏的配置
        loaded_config, status = config_manager.load_config()
        
        # 应该返回默认配置
        assert loaded_config is not None, "即使配置损坏也应该返回有效配置"
        assert status == ConfigStatus.DEFAULT_CREATED, f"状态应该是默认创建，实际是: {status}"
        assert len(loaded_config.node_data) == 0, "默认配置应该没有节点"
        assert isinstance(loaded_config.xray_config, dict), "应该有有效的Xray配置"
        
        print("✅ 损坏配置处理测试通过")
        
        print("5. 测试配置导出和导入...")
        
        # 重新保存有效配置
        success, _ = config_manager.save_config(test_nodes, test_user_settings)
        assert success, "配置应该保存成功"
        
        # 导出配置
        export_path = os.path.join(temp_dir, "exported_config.json")
        export_success = config_manager.export_config(export_path)
        assert export_success, "应该能够导出配置"
        assert os.path.exists(export_path), "导出文件应该存在"
        
        # 验证导出文件内容
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        assert 'metadata' in exported_data, "导出数据应该包含元数据"
        assert 'xray_config' in exported_data, "导出数据应该包含Xray配置"
        assert 'node_data' in exported_data, "导出数据应该包含节点数据"
        assert 'user_settings' in exported_data, "导出数据应该包含用户设置"
        
        # 清空当前配置
        os.remove(config_manager.config_file)
        
        # 导入配置
        import_success, message = config_manager.import_config(export_path)
        assert import_success, f"应该能够导入配置: {message}"
        assert "successfully" in message, "导入消息应该包含成功信息"
        
        # 验证导入的配置
        imported_config, _ = config_manager.load_config()
        assert len(imported_config.node_data) == len(test_nodes), "导入后节点数量应该正确"
        assert imported_config.user_settings == test_user_settings, "导入后用户设置应该正确"
        
        print("✅ 配置导出和导入测试通过")
        
        print("6. 测试配置状态跟踪...")
        
        # 获取当前状态
        current_status = config_manager.get_config_status()
        assert current_status == ConfigStatus.VALID, "当前状态应该是有效的"
        
        # 获取当前配置
        current_config = config_manager.get_current_config()
        assert current_config is not None, "应该能够获取当前配置"
        assert len(current_config.node_data) == len(test_nodes), "当前配置节点数量应该正确"
        
        print("✅ 配置状态跟踪测试通过")
        
        print("\n🎉 所有配置管理器单元测试都通过了！")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_config_manager_unit_tests()