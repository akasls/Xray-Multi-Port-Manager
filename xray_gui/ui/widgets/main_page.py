"""
主页面组件 - 合并订阅、节点列表和控制面板（增强版）
Feature: xray-protocol-enhancement, Requirements 1.1-1.8, 2.1-2.5, 4.1-4.6, 5.1-5.5
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu, QAbstractItemView,
    QGraphicsDropShadowEffect, QProgressBar, QSplitter,
    QCheckBox, QComboBox, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QAction

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from xray_gui.core.node import Node

from .enhanced_node_list import EnhancedNodeList
from ...core.ui_integration_manager import UIIntegrationManager, UIUpdateType, UIUpdateData
from ...core.concurrent_latency_tester import ConcurrentTestConfig, TestStrategy
from ...core.system_adaptability_manager import SystemAdaptabilityManager


class MainPage(QFrame):
    """主页面 - 合并所有功能（增强版）"""
    
    # 信号
    refresh_requested = pyqtSignal(str)
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    test_selected = pyqtSignal(list)
    test_all = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("main_page")
        
        self._nodes: List = []
        self._is_running = False
        
        # 初始化UI集成管理器
        self.ui_manager = UIIntegrationManager()
        self.adaptability_manager = SystemAdaptabilityManager()
        
        # 延迟测试配置
        self._latency_config = ConcurrentTestConfig(
            max_concurrent=10,
            timeout=5.0,
            strategy=TestStrategy.ASYNCIO,
            bypass_tun=True
        )
        
        self._setup_ui()
        self._apply_styles()
        self._setup_ui_callbacks()
        
        # 启动系统监控
        self.adaptability_manager.start_monitoring()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 顶部控制栏
        self._create_control_bar(layout)
        
        # 延迟测试配置面板
        self._create_latency_config_panel(layout)
        
        # 使用增强的节点列表
        self._create_enhanced_node_list(layout)
    
    def _create_control_bar(self, layout):
        """创建控制栏"""
        control_bar = QFrame()
        control_bar.setObjectName("control_bar")
        control_bar.setFixedHeight(70)
        
        bar_layout = QHBoxLayout(control_bar)
        bar_layout.setContentsMargins(20, 12, 20, 12)
        bar_layout.setSpacing(15)
        
        # 订阅 URL 输入
        url_widget = QWidget()
        url_layout = QVBoxLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(4)
        
        url_label = QLabel("订阅地址")
        url_label.setObjectName("field_label")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText("请输入订阅地址...")
        url_layout.addWidget(self.url_input)
        
        bar_layout.addWidget(url_widget, 1)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("↻ 刷新")
        self.refresh_btn.setObjectName("action_btn")
        self.refresh_btn.setFixedSize(90, 38)
        self.refresh_btn.clicked.connect(self._on_refresh)
        bar_layout.addWidget(self.refresh_btn)
        
        # 测速按钮（增强版）
        self.test_btn = QPushButton("⚡ 智能测速")
        self.test_btn.setObjectName("action_btn")
        self.test_btn.setFixedSize(110, 38)
        self.test_btn.clicked.connect(self._on_enhanced_test)
        bar_layout.addWidget(self.test_btn)
        
        # 取消测试按钮
        self.cancel_test_btn = QPushButton("⏹ 取消")
        self.cancel_test_btn.setObjectName("cancel_btn")
        self.cancel_test_btn.setFixedSize(70, 38)
        self.cancel_test_btn.setVisible(False)
        self.cancel_test_btn.clicked.connect(self._on_cancel_test)
        bar_layout.addWidget(self.cancel_test_btn)
        
        # 分隔线
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedWidth(1)
        sep.setFixedHeight(40)
        bar_layout.addWidget(sep)
        
        # 启动/停止按钮
        self.start_btn = QPushButton("▶ 启动")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setFixedSize(100, 38)
        self.start_btn.clicked.connect(self._on_start)
        bar_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedSize(100, 38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        bar_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_bar)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setObjectName("progress_bar")
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
    
    def _create_latency_config_panel(self, layout):
        """创建延迟测试配置面板"""
        config_group = QGroupBox("延迟测试配置")
        config_group.setObjectName("config_group")
        config_group.setCheckable(True)
        config_group.setChecked(False)  # 默认折叠
        config_group.setFixedHeight(120)
        
        config_layout = QHBoxLayout(config_group)
        config_layout.setContentsMargins(15, 25, 15, 10)
        config_layout.setSpacing(20)
        
        # 并发数设置
        concurrent_widget = QWidget()
        concurrent_layout = QVBoxLayout(concurrent_widget)
        concurrent_layout.setContentsMargins(0, 0, 0, 0)
        concurrent_layout.setSpacing(4)
        
        concurrent_label = QLabel("并发数")
        concurrent_label.setObjectName("config_label")
        concurrent_layout.addWidget(concurrent_label)
        
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setObjectName("config_spin")
        self.concurrent_spin.setRange(1, 50)
        self.concurrent_spin.setValue(10)
        self.concurrent_spin.valueChanged.connect(self._update_latency_config)
        concurrent_layout.addWidget(self.concurrent_spin)
        
        config_layout.addWidget(concurrent_widget)
        
        # 超时设置
        timeout_widget = QWidget()
        timeout_layout = QVBoxLayout(timeout_widget)
        timeout_layout.setContentsMargins(0, 0, 0, 0)
        timeout_layout.setSpacing(4)
        
        timeout_label = QLabel("超时(秒)")
        timeout_label.setObjectName("config_label")
        timeout_layout.addWidget(timeout_label)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setObjectName("config_spin")
        self.timeout_spin.setRange(1, 30)
        self.timeout_spin.setValue(5)
        self.timeout_spin.valueChanged.connect(self._update_latency_config)
        timeout_layout.addWidget(self.timeout_spin)
        
        config_layout.addWidget(timeout_widget)
        
        # 测试策略
        strategy_widget = QWidget()
        strategy_layout = QVBoxLayout(strategy_widget)
        strategy_layout.setContentsMargins(0, 0, 0, 0)
        strategy_layout.setSpacing(4)
        
        strategy_label = QLabel("测试策略")
        strategy_label.setObjectName("config_label")
        strategy_layout.addWidget(strategy_label)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.setObjectName("config_combo")
        self.strategy_combo.addItems(["异步并发", "线程池", "混合模式"])
        self.strategy_combo.currentTextChanged.connect(self._update_latency_config)
        strategy_layout.addWidget(self.strategy_combo)
        
        config_layout.addWidget(strategy_widget)
        
        # TUN模式绕过
        bypass_widget = QWidget()
        bypass_layout = QVBoxLayout(bypass_widget)
        bypass_layout.setContentsMargins(0, 0, 0, 0)
        bypass_layout.setSpacing(4)
        
        bypass_label = QLabel("TUN绕过")
        bypass_label.setObjectName("config_label")
        bypass_layout.addWidget(bypass_label)
        
        self.bypass_check = QCheckBox("启用直连测试")
        self.bypass_check.setObjectName("config_check")
        self.bypass_check.setChecked(True)
        self.bypass_check.toggled.connect(self._update_latency_config)
        bypass_layout.addWidget(self.bypass_check)
        
        config_layout.addWidget(bypass_widget)
        
        config_layout.addStretch()
        
        # 系统状态指示器
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(4)
        
        status_label = QLabel("系统状态")
        status_label.setObjectName("config_label")
        status_layout.addWidget(status_label)
        
        self.system_status_label = QLabel("正常")
        self.system_status_label.setObjectName("system_status")
        status_layout.addWidget(self.system_status_label)
        
        config_layout.addWidget(status_widget)
        
        layout.addWidget(config_group)
    
    def _create_enhanced_node_list(self, layout):
        """创建增强的节点列表"""
        self.enhanced_node_list = EnhancedNodeList()
        
        # 连接信号
        self.enhanced_node_list.node_selected.connect(self._on_node_selected)
        self.enhanced_node_list.nodes_test_requested.connect(self._on_nodes_test_requested)
        self.enhanced_node_list.single_node_test_requested.connect(self._on_single_node_test_requested)
        
        layout.addWidget(self.enhanced_node_list, 1)
    
    def _setup_ui_callbacks(self):
        """设置UI回调"""
        # 注册UI更新回调
        self.ui_manager.register_ui_callback(UIUpdateType.LATENCY_TEST_PROGRESS, self._on_latency_progress)
        self.ui_manager.register_ui_callback(UIUpdateType.LATENCY_TEST_COMPLETE, self._on_latency_complete)
        self.ui_manager.register_ui_callback(UIUpdateType.TUN_MODE_STATUS, self._on_tun_status_update)
        self.ui_manager.register_ui_callback(UIUpdateType.SYSTEM_ADAPTATION, self._on_system_adaptation)
        self.ui_manager.register_ui_callback(UIUpdateType.ERROR_NOTIFICATION, self._on_error_notification)
    
    def _update_latency_config(self):
        """更新延迟测试配置"""
        strategy_map = {
            "异步并发": TestStrategy.ASYNCIO,
            "线程池": TestStrategy.THREADING,
            "混合模式": TestStrategy.HYBRID
        }
        
        self._latency_config = ConcurrentTestConfig(
            max_concurrent=self.concurrent_spin.value(),
            timeout=float(self.timeout_spin.value()),
            strategy=strategy_map.get(self.strategy_combo.currentText(), TestStrategy.ASYNCIO),
            bypass_tun=self.bypass_check.isChecked()
        )
    
    def _create_control_bar(self, layout):
        """创建控制栏"""
        control_bar = QFrame()
        control_bar.setObjectName("control_bar")
        control_bar.setFixedHeight(70)
        
        bar_layout = QHBoxLayout(control_bar)
        bar_layout.setContentsMargins(20, 12, 20, 12)
        bar_layout.setSpacing(15)
        
        # 订阅 URL 输入
        url_widget = QWidget()
        url_layout = QVBoxLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(4)
        
        url_label = QLabel("订阅地址")
        url_label.setObjectName("field_label")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText("请输入订阅地址...")
        url_layout.addWidget(self.url_input)
        
        bar_layout.addWidget(url_widget, 1)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("↻ 刷新")
        self.refresh_btn.setObjectName("action_btn")
        self.refresh_btn.setFixedSize(90, 38)
        self.refresh_btn.clicked.connect(self._on_refresh)
        bar_layout.addWidget(self.refresh_btn)
        
        # 测速按钮
        self.test_btn = QPushButton("⚡ 测速")
        self.test_btn.setObjectName("action_btn")
        self.test_btn.setFixedSize(90, 38)
        self.test_btn.clicked.connect(self._on_test)
        bar_layout.addWidget(self.test_btn)
        
        # 分隔线
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedWidth(1)
        sep.setFixedHeight(40)
        bar_layout.addWidget(sep)
        
        # 启动/停止按钮
        self.start_btn = QPushButton("▶ 启动")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setFixedSize(100, 38)
        self.start_btn.clicked.connect(self._on_start)
        bar_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedSize(100, 38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        bar_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_bar)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setObjectName("progress_bar")
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #main_page {
                background: transparent;
            }
            
            #control_bar {
                background: rgba(20, 15, 40, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 14px;
            }
            
            #field_label {
                color: rgba(180, 150, 220, 0.9);
                font-size: 11px;
            }
            
            #url_input {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 12px;
            }
            
            #url_input:focus {
                border: 1px solid rgba(120, 0, 255, 0.6);
            }
            
            #action_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 0, 200, 0.7),
                    stop:1 rgba(0, 150, 200, 0.7)
                );
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            
            #action_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(120, 20, 220, 0.9),
                    stop:1 rgba(20, 170, 220, 0.9)
                );
            }
            
            #action_btn:disabled {
                background: rgba(60, 50, 80, 0.5);
            }
            
            #cancel_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(200, 80, 80, 0.7),
                    stop:1 rgba(180, 50, 100, 0.7)
                );
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            
            #cancel_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(220, 100, 100, 0.9),
                    stop:1 rgba(200, 70, 120, 0.9)
                );
            }
            
            #separator {
                background: rgba(120, 0, 255, 0.3);
            }
            
            #start_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 180, 100, 0.8),
                    stop:1 rgba(0, 130, 180, 0.8)
                );
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            
            #start_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(20, 200, 120, 0.9),
                    stop:1 rgba(20, 150, 200, 0.9)
                );
            }
            
            #start_btn:disabled {
                background: rgba(60, 50, 80, 0.5);
            }
            
            #stop_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(200, 80, 80, 0.8),
                    stop:1 rgba(180, 50, 100, 0.8)
                );
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            
            #stop_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(220, 100, 100, 0.9),
                    stop:1 rgba(200, 70, 120, 0.9)
                );
            }
            
            #stop_btn:disabled {
                background: rgba(60, 50, 80, 0.5);
            }
            
            #progress_bar {
                background: rgba(40, 30, 60, 0.5);
                border: none;
                border-radius: 1px;
            }
            
            #progress_bar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7800ff,
                    stop:1 #00d4ff
                );
            }
            
            #config_group {
                background: rgba(20, 15, 40, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 12px;
                color: rgba(180, 150, 220, 0.9);
                font-size: 12px;
                font-weight: bold;
            }
            
            #config_group::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
            
            #config_label {
                color: rgba(180, 150, 220, 0.9);
                font-size: 10px;
            }
            
            #config_spin {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 6px;
                padding: 4px 8px;
                color: white;
                font-size: 11px;
            }
            
            #config_spin:focus {
                border: 1px solid rgba(120, 0, 255, 0.6);
            }
            
            #config_combo {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 6px;
                padding: 4px 8px;
                color: white;
                font-size: 11px;
            }
            
            #config_combo:focus {
                border: 1px solid rgba(120, 0, 255, 0.6);
            }
            
            #config_combo::drop-down {
                border: none;
            }
            
            #config_combo::down-arrow {
                image: none;
                border: none;
            }
            
            #config_check {
                color: rgba(180, 150, 220, 0.9);
                font-size: 10px;
            }
            
            #config_check::indicator {
                width: 16px;
                height: 16px;
            }
            
            #config_check::indicator:unchecked {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 3px;
            }
            
            #config_check::indicator:checked {
                background: rgba(120, 0, 255, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.6);
                border-radius: 3px;
            }
            
            #system_status {
                color: #4CAF50;
                font-size: 10px;
                font-weight: bold;
            }
        """)
    
    def _on_refresh(self):
        """刷新按钮点击"""
        url = self.url_input.text().strip()
        if url:
            self.refresh_requested.emit(url)
    
    def _on_enhanced_test(self):
        """增强测试按钮点击"""
        if self.ui_manager.is_latency_test_running():
            return
        
        # 使用增强的延迟测试
        success = self.ui_manager.start_latency_test(
            nodes=self._nodes,
            config=self._latency_config
        )
        
        if success:
            self.test_btn.setVisible(False)
            self.cancel_test_btn.setVisible(True)
    
    def _on_cancel_test(self):
        """取消测试按钮点击"""
        self.ui_manager.cancel_latency_test()
        self.test_btn.setVisible(True)
        self.cancel_test_btn.setVisible(False)
    
    def _on_start(self):
        """启动按钮点击"""
        self.start_requested.emit()
    
    def _on_stop(self):
        """停止按钮点击"""
        self.stop_requested.emit()
    
    def _on_node_selected(self, node):
        """节点选中事件"""
        # 可以在这里添加节点选中后的处理逻辑
        pass
    
    def _on_nodes_test_requested(self, nodes):
        """批量节点测试请求"""
        if not self.ui_manager.is_latency_test_running():
            self.ui_manager.start_latency_test(nodes=nodes, config=self._latency_config)
    
    def _on_single_node_test_requested(self, node):
        """单个节点测试请求"""
        if not self.ui_manager.is_latency_test_running():
            self.ui_manager.start_latency_test(nodes=[node], config=self._latency_config)
    
    def _on_latency_progress(self, update_data: UIUpdateData):
        """延迟测试进度回调"""
        data = update_data.data
        completed = data.get('completed', 0)
        total = data.get('total', 0)
        percentage = data.get('percentage', 0)
        
        # 显示进度条
        self.progress.setVisible(True)
        self.progress.setMaximum(total)
        self.progress.setValue(completed)
        
        # 更新按钮状态
        self.test_btn.setEnabled(False)
        self.test_btn.setText(f"测试中... {percentage:.1f}%")
    
    def _on_latency_complete(self, update_data: UIUpdateData):
        """延迟测试完成回调"""
        data = update_data.data
        
        # 隐藏进度条
        self.progress.setVisible(False)
        
        # 恢复按钮状态
        self.test_btn.setEnabled(True)
        self.test_btn.setText("⚡ 智能测速")
        self.test_btn.setVisible(True)
        self.cancel_test_btn.setVisible(False)
        
        # 更新节点列表
        if 'updated_nodes' in data:
            self._nodes = data['updated_nodes']
            self.enhanced_node_list.update_nodes(self._nodes)
    
    def _on_tun_status_update(self, update_data: UIUpdateData):
        """TUN模式状态更新回调"""
        data = update_data.data
        active = data.get('active', False)
        
        if active:
            self.system_status_label.setText("TUN模式激活")
            self.system_status_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        else:
            self.system_status_label.setText("正常")
            self.system_status_label.setStyleSheet("color: #4CAF50;")
    
    def _on_system_adaptation(self, update_data: UIUpdateData):
        """系统适应性回调"""
        data = update_data.data
        is_healthy = data.get('is_healthy', True)
        
        if is_healthy:
            self.system_status_label.setText("正常")
            self.system_status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.system_status_label.setText("异常")
            self.system_status_label.setStyleSheet("color: #F44336; font-weight: bold;")
    
    def _on_error_notification(self, update_data: UIUpdateData):
        """错误通知回调"""
        data = update_data.data
        message = data.get('message', '')
        
        # 可以在这里显示错误通知
        # 例如使用状态栏或弹出通知
        print(f"Error: {message}")  # 临时处理
    
    def set_url(self, url: str):
        """设置订阅 URL"""
        self.url_input.setText(url)
    
    def get_url(self) -> str:
        """获取订阅 URL"""
        return self.url_input.text().strip()
    
    def set_loading(self, loading: bool):
        """设置加载状态"""
        self.progress.setVisible(loading)
        self.refresh_btn.setEnabled(not loading)
    
    def set_running(self, running: bool):
        """设置运行状态"""
        self._is_running = running
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
    
    def set_nodes(self, nodes: List):
        """设置节点列表"""
        self._nodes = nodes
        
        # 更新增强节点列表
        self.enhanced_node_list.update_nodes(nodes)
        
        # 通知UI管理器
        self.ui_manager.update_node_list(nodes)
    
    def get_selected_nodes(self) -> List:
        """获取选中的节点（兼容性方法）"""
        # 这个方法保留用于向后兼容
        return []
    
    def cleanup(self):
        """清理资源"""
        self.adaptability_manager.stop_monitoring()
        self.ui_manager.cleanup()
