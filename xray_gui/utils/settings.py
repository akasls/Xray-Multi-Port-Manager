"""
设置管理器 - 用户配置持久化
"""
import json
import os
from typing import Any, Dict


class SettingsManager:
    """用户设置管理器"""
    
    DEFAULT_SETTINGS = {
        "subscription_url": "",
        "start_port": 40000,
        "port_count": 20,
        "exclude_keywords": "",
        "region_priority": "美国,日本,香港",
        "auto_refresh_enabled": False,
        "auto_refresh_interval": 30,
        "startup_enabled": False,
        "minimize_on_close": True,
        "window_geometry": {
            "x": 100,
            "y": 100,
            "width": 1200,
            "height": 800
        }
    }
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初始化设置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._settings: Dict[str, Any] = {}
        self._loaded = False
    
    def _ensure_directory(self) -> None:
        """确保配置目录存在"""
        directory = os.path.dirname(self.config_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """
        加载设置
        
        Returns:
            设置字典
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并默认设置和加载的设置
                    self._settings = {**self.DEFAULT_SETTINGS, **loaded}
            else:
                self._settings = self.DEFAULT_SETTINGS.copy()
            
            self._loaded = True
            return self._settings.copy()
            
        except json.JSONDecodeError:
            # 配置文件损坏，使用默认值
            self._settings = self.DEFAULT_SETTINGS.copy()
            self._loaded = True
            return self._settings.copy()
        except Exception:
            self._settings = self.DEFAULT_SETTINGS.copy()
            self._loaded = True
            return self._settings.copy()
    
    def save(self) -> bool:
        """
        保存设置
        
        Returns:
            是否保存成功
        """
        try:
            self._ensure_directory()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取设置项
        
        Args:
            key: 设置键
            default: 默认值
            
        Returns:
            设置值
        """
        if not self._loaded:
            self.load()
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """
        设置配置项
        
        Args:
            key: 设置键
            value: 设置值
            auto_save: 是否自动保存
        """
        if not self._loaded:
            self.load()
        self._settings[key] = value
        if auto_save:
            self.save()
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有设置
        
        Returns:
            设置字典副本
        """
        if not self._loaded:
            self.load()
        return self._settings.copy()
    
    def reset_to_defaults(self) -> None:
        """重置为默认设置"""
        self._settings = self.DEFAULT_SETTINGS.copy()
        self.save()
    
    def update(self, settings: Dict[str, Any], auto_save: bool = True) -> None:
        """
        批量更新设置
        
        Args:
            settings: 设置字典
            auto_save: 是否自动保存
        """
        if not self._loaded:
            self.load()
        self._settings.update(settings)
        if auto_save:
            self.save()
    
    # 便捷属性访问
    @property
    def subscription_url(self) -> str:
        return self.get("subscription_url", "")
    
    @subscription_url.setter
    def subscription_url(self, value: str):
        self.set("subscription_url", value)
    
    @property
    def start_port(self) -> int:
        return self.get("start_port", 40000)
    
    @start_port.setter
    def start_port(self, value: int):
        self.set("start_port", value)
    
    @property
    def port_count(self) -> int:
        return self.get("port_count", 20)
    
    @port_count.setter
    def port_count(self, value: int):
        self.set("port_count", value)
    
    @property
    def exclude_keywords(self) -> str:
        return self.get("exclude_keywords", "")
    
    @exclude_keywords.setter
    def exclude_keywords(self, value: str):
        self.set("exclude_keywords", value)
    
    @property
    def region_priority(self) -> str:
        return self.get("region_priority", "美国,日本,香港")
    
    @region_priority.setter
    def region_priority(self, value: str):
        self.set("region_priority", value)
    
    @property
    def auto_refresh_enabled(self) -> bool:
        return self.get("auto_refresh_enabled", False)
    
    @auto_refresh_enabled.setter
    def auto_refresh_enabled(self, value: bool):
        self.set("auto_refresh_enabled", value)
    
    @property
    def auto_refresh_interval(self) -> int:
        return self.get("auto_refresh_interval", 30)
    
    @auto_refresh_interval.setter
    def auto_refresh_interval(self, value: int):
        self.set("auto_refresh_interval", value)
    
    @property
    def startup_enabled(self) -> bool:
        return self.get("startup_enabled", False)
    
    @startup_enabled.setter
    def startup_enabled(self, value: bool):
        self.set("startup_enabled", value)
    
    @property
    def minimize_on_close(self) -> bool:
        return self.get("minimize_on_close", True)
    
    @minimize_on_close.setter
    def minimize_on_close(self, value: bool):
        self.set("minimize_on_close", value)
