"""
配置生成器 - 生成 Xray JSON 配置文件
"""
import json
from typing import List
from .node import Node


class ConfigGenerator:
    """配置生成器类"""
    
    def __init__(self, log_level: str = "warning"):
        self.log_level = log_level
    
    def generate(self, nodes: List[Node]) -> dict:
        """生成配置"""
        return generate_config(nodes, self.log_level)
    
    def save(self, config: dict, filepath: str = "multi_port_config.json"):
        """保存配置"""
        save_config(config, filepath)
    
    def generate_and_save(self, nodes: List[Node], filepath: str = "multi_port_config.json") -> dict:
        """生成并保存配置"""
        return generate_and_save(nodes, filepath, self.log_level)


def generate_config(nodes: List[Node], log_level: str = "warning") -> dict:
    """
    生成完整的 Xray 配置
    
    Args:
        nodes: 已分配端口的节点列表
        log_level: 日志级别
        
    Returns:
        Xray 配置字典
    """
    inbounds = []
    outbounds = []
    rules = []
    
    for node in nodes:
        if node.local_port is None:
            continue
        
        # 添加 inbound
        inbounds.append(node.to_inbound_config())
        
        # 添加 outbound
        outbounds.append(node.to_outbound_config())
        
        # 添加路由规则
        rules.append(node.to_routing_rule())
    
    config = {
        "log": {
            "loglevel": log_level
        },
        "inbounds": inbounds,
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "AsIs",
            "rules": rules
        }
    }
    
    return config


def save_config(config: dict, filepath: str = "multi_port_config.json") -> None:
    """
    保存配置到文件
    
    Args:
        config: 配置字典
        filepath: 文件路径
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_config(filepath: str = "multi_port_config.json") -> dict:
    """
    从文件加载配置
    
    Args:
        filepath: 文件路径
        
    Returns:
        配置字典
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_and_save(nodes: List[Node], 
                      filepath: str = "multi_port_config.json",
                      log_level: str = "warning") -> dict:
    """
    生成并保存配置
    
    Args:
        nodes: 已分配端口的节点列表
        filepath: 文件路径
        log_level: 日志级别
        
    Returns:
        生成的配置字典
    """
    config = generate_config(nodes, log_level)
    save_config(config, filepath)
    return config
