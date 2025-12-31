"""
增强的配置管理器 - 支持备份、恢复和错误处理
Feature: xray-protocol-enhancement, Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""
import json
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .node import Node
from .config_generator import generate_config


class ConfigStatus(Enum):
    """配置状态枚举"""
    VALID = "valid"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    BACKUP_RESTORED = "backup_restored"
    DEFAULT_CREATED = "default_created"


@dataclass
class ConfigMetadata:
    """配置元数据"""
    version: str = "1.0"
    created_at: str = ""
    last_modified: str = ""
    node_count: int = 0
    checksum: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_modified:
            self.last_modified = datetime.now().isoformat()


@dataclass
class PersistentConfig:
    """持久化配置数据结构"""
    metadata: ConfigMetadata
    xray_config: Dict[str, Any]
    node_data: List[Dict[str, Any]]
    user_settings: Dict[str, Any]
    port_allocations: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'metadata': asdict(self.metadata),
            'xray_config': self.xray_config,
            'node_data': self.node_data,
            'user_settings': self.user_settings,
            'port_allocations': self.port_allocations
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersistentConfig':
        """从字典创建"""
        metadata = ConfigMetadata(**data.get('metadata', {}))
        return cls(
            metadata=metadata,
            xray_config=data.get('xray_config', {}),
            node_data=data.get('node_data', []),
            user_settings=data.get('user_settings', {}),
            port_allocations=data.get('port_allocations', {})
        )


class EnhancedConfigManager:
    """增强的配置管理器"""
    
    def __init__(self, 
                 config_dir: str = "config",
                 config_file: str = "xray_config.json",
                 backup_file: str = "xray_config.backup.json",
                 max_backups: int = 5):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录
            config_file: 主配置文件名
            backup_file: 备份文件名
            max_backups: 最大备份数量
        """
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / config_file
        self.backup_file = self.config_dir / backup_file
        self.max_backups = max_backups
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 当前配置缓存
        self._current_config: Optional[PersistentConfig] = None
        self._config_status = ConfigStatus.MISSING
    
    def save_config(self, 
                   nodes: List[Node], 
                   user_settings: Optional[Dict[str, Any]] = None,
                   create_backup: bool = True) -> Tuple[bool, ConfigStatus]:
        """
        保存配置
        
        Args:
            nodes: 节点列表
            user_settings: 用户设置
            create_backup: 是否创建备份
            
        Returns:
            (成功标志, 配置状态)
        """
        try:
            # 如果存在旧配置且需要备份，先创建备份
            if create_backup and self.config_file.exists():
                self._create_backup()
            
            # 生成Xray配置
            xray_config = generate_config(nodes)
            
            # 准备节点数据
            node_data = []
            port_allocations = {}
            
            for node in nodes:
                node_dict = {
                    'uuid': node.uuid,
                    'remark': node.remark,
                    'protocol': node.protocol,
                    'address': node.address,
                    'port': node.port,
                    'security': node.security,
                    'sni': node.sni,
                    'flow': node.flow,
                    'fingerprint': node.fingerprint,
                    'public_key': node.public_key,
                    'short_id': node.short_id,
                    'network': node.network,
                    'service_name': node.service_name,
                    'alter_id': node.alter_id,
                    'method': node.method,
                    'password': node.password,
                    'path': node.path,
                    'host': node.host,
                    'h2_path': node.h2_path,
                    'h2_host': node.h2_host,
                    'grpc_mode': node.grpc_mode,
                    'tls_version': node.tls_version,
                    'alpn': node.alpn,
                    'private_key': node.private_key,
                    'public_key_wg': node.public_key_wg,
                    'endpoint': node.endpoint,
                    'allowed_ips': node.allowed_ips,
                    'local_port': getattr(node, 'local_port', None),
                    'latency': getattr(node, 'latency', None)
                }
                node_data.append(node_dict)
                
                if hasattr(node, 'local_port') and node.local_port:
                    port_allocations[node.remark] = node.local_port
            
            # 创建配置元数据
            metadata = ConfigMetadata(
                last_modified=datetime.now().isoformat(),
                node_count=len(nodes),
                checksum=self._calculate_checksum(xray_config)
            )
            
            # 创建持久化配置
            persistent_config = PersistentConfig(
                metadata=metadata,
                xray_config=xray_config,
                node_data=node_data,
                user_settings=user_settings or {},
                port_allocations=port_allocations
            )
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(persistent_config.to_dict(), f, indent=2, ensure_ascii=False)
            
            # 更新缓存
            self._current_config = persistent_config
            self._config_status = ConfigStatus.VALID
            
            self.logger.info(f"Configuration saved successfully: {len(nodes)} nodes")
            return True, ConfigStatus.VALID
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False, ConfigStatus.CORRUPTED
    
    def load_config(self) -> Tuple[Optional[PersistentConfig], ConfigStatus]:
        """
        加载配置
        
        Returns:
            (配置对象, 配置状态)
        """
        try:
            # 尝试加载主配置文件
            if self.config_file.exists():
                config, status = self._load_config_file(self.config_file)
                if config:
                    self._current_config = config
                    self._config_status = status
                    return config, status
            
            # 主配置文件不存在或损坏，尝试从备份恢复
            if self.backup_file.exists():
                self.logger.warning("Main config file missing/corrupted, trying backup")
                config, _ = self._load_config_file(self.backup_file)
                if config:
                    # 从备份恢复主配置
                    self._restore_from_backup()
                    self._current_config = config
                    self._config_status = ConfigStatus.BACKUP_RESTORED
                    return config, ConfigStatus.BACKUP_RESTORED
            
            # 没有可用配置，创建默认配置
            self.logger.info("No valid configuration found, creating default")
            default_config = self._create_default_config()
            self._current_config = default_config
            self._config_status = ConfigStatus.DEFAULT_CREATED
            return default_config, ConfigStatus.DEFAULT_CREATED
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return None, ConfigStatus.CORRUPTED
    
    def get_current_config(self) -> Optional[PersistentConfig]:
        """获取当前配置"""
        if self._current_config is None:
            config, _ = self.load_config()
            return config
        return self._current_config
    
    def get_config_status(self) -> ConfigStatus:
        """获取配置状态"""
        return self._config_status
    
    def validate_config(self, config_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        验证配置文件
        
        Args:
            config_path: 配置文件路径，None表示验证当前配置
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            if config_path:
                config_file = Path(config_path)
            else:
                config_file = self.config_file
            
            if not config_file.exists():
                return False, "Configuration file does not exist"
            
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证必要字段
            required_fields = ['metadata', 'xray_config', 'node_data']
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            
            # 验证Xray配置结构
            xray_config = data['xray_config']
            if not isinstance(xray_config, dict):
                return False, "Invalid xray_config format"
            
            required_xray_fields = ['inbounds', 'outbounds', 'routing']
            for field in required_xray_fields:
                if field not in xray_config:
                    return False, f"Missing required xray field: {field}"
            
            return True, "Configuration is valid"
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def create_backup(self) -> bool:
        """手动创建备份"""
        return self._create_backup()
    
    def restore_from_backup(self) -> bool:
        """从备份恢复配置"""
        return self._restore_from_backup()
    
    def list_backups(self) -> List[str]:
        """列出所有备份文件"""
        backups = []
        for file in self.config_dir.glob("*.backup*.json"):
            backups.append(str(file))
        return sorted(backups)
    
    def cleanup_old_backups(self) -> int:
        """清理旧备份文件"""
        backups = self.list_backups()
        if len(backups) <= self.max_backups:
            return 0
        
        # 删除最旧的备份
        to_delete = backups[:-self.max_backups]
        deleted_count = 0
        
        for backup_path in to_delete:
            try:
                os.remove(backup_path)
                deleted_count += 1
                self.logger.info(f"Deleted old backup: {backup_path}")
            except Exception as e:
                self.logger.error(f"Failed to delete backup {backup_path}: {e}")
        
        return deleted_count
    
    def export_config(self, export_path: str, include_sensitive: bool = False) -> bool:
        """
        导出配置
        
        Args:
            export_path: 导出路径
            include_sensitive: 是否包含敏感信息
            
        Returns:
            是否成功
        """
        try:
            config = self.get_current_config()
            if not config:
                return False
            
            export_data = config.to_dict()
            
            # 如果不包含敏感信息，移除密码等字段
            if not include_sensitive:
                export_data = self._sanitize_config(export_data)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration exported to: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, import_path: str) -> Tuple[bool, str]:
        """
        导入配置
        
        Args:
            import_path: 导入路径
            
        Returns:
            (是否成功, 错误信息)
        """
        try:
            if not os.path.exists(import_path):
                return False, "Import file does not exist"
            
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证导入的配置
            config = PersistentConfig.from_dict(data)
            
            # 创建备份
            self._create_backup()
            
            # 保存导入的配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._current_config = config
            self._config_status = ConfigStatus.VALID
            
            self.logger.info(f"Configuration imported from: {import_path}")
            return True, "Configuration imported successfully"
            
        except Exception as e:
            error_msg = f"Failed to import configuration: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _load_config_file(self, file_path: Path) -> Tuple[Optional[PersistentConfig], ConfigStatus]:
        """加载指定的配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = PersistentConfig.from_dict(data)
            return config, ConfigStatus.VALID
            
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {file_path}")
            return None, ConfigStatus.CORRUPTED
        except Exception as e:
            self.logger.error(f"Failed to load config file {file_path}: {e}")
            return None, ConfigStatus.CORRUPTED
    
    def _create_backup(self) -> bool:
        """创建配置备份"""
        try:
            if not self.config_file.exists():
                return True  # 没有配置文件，无需备份
            
            # 创建带时间戳的备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped_backup = self.config_dir / f"xray_config.backup.{timestamp}.json"
            
            # 复制主配置到备份
            shutil.copy2(self.config_file, self.backup_file)
            shutil.copy2(self.config_file, timestamped_backup)
            
            # 清理旧备份
            self.cleanup_old_backups()
            
            self.logger.info(f"Configuration backup created: {self.backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False
    
    def _restore_from_backup(self) -> bool:
        """从备份恢复配置"""
        try:
            if not self.backup_file.exists():
                return False
            
            shutil.copy2(self.backup_file, self.config_file)
            self.logger.info("Configuration restored from backup")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def _create_default_config(self) -> PersistentConfig:
        """创建默认配置"""
        metadata = ConfigMetadata(
            created_at=datetime.now().isoformat(),
            last_modified=datetime.now().isoformat(),
            node_count=0
        )
        
        default_xray_config = {
            "log": {"loglevel": "warning"},
            "inbounds": [],
            "outbounds": [],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": []
            }
        }
        
        return PersistentConfig(
            metadata=metadata,
            xray_config=default_xray_config,
            node_data=[],
            user_settings={},
            port_allocations={}
        )
    
    def _calculate_checksum(self, data: Any) -> str:
        """计算数据校验和"""
        import hashlib
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()
    
    def _sanitize_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """清理配置中的敏感信息"""
        sanitized = config_data.copy()
        
        # 清理节点数据中的敏感信息
        if 'node_data' in sanitized:
            for node in sanitized['node_data']:
                if 'config' in node and isinstance(node['config'], dict):
                    # 移除密码、密钥等敏感字段
                    sensitive_fields = ['password', 'id', 'uuid', 'private_key', 'public_key']
                    for field in sensitive_fields:
                        if field in node['config']:
                            node['config'][field] = "***REMOVED***"
        
        return sanitized