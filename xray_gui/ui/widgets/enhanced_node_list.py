"""
增强的节点列表组件 - 支持多协议显示和新功能
Feature: xray-protocol-enhancement, Requirements 1.1-1.8, 2.1-2.5
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QToolTip, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPalette, QAction, QPixmap, QPainter
from typing import List, Dict, Optional, Any
from datetime import datetime

from ...core.node import Node
from ...core.ui_integration_manager import UIIntegrationManager, UIUpdateType, UIUpdateData, ProtocolDisplayInfo


class ProtocolBadge(QLabel):
    """协议标识组件"""
    
    def __init__(self, protocol_info: ProtocolDisplayInfo, parent=None):
        super().__init__(parent)
        self.protocol_info = protocol_info
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self.setText(self.protocol_info.display_name)
        self.setFixedSize(60, 20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 设置样式
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self.protocol_info.color};
                color: white;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
            }}
        """)
        
        # 设置工具提示
        tooltip_text = f"""
        <b>{self.protocol_info.display_name}</b><br>
        {self.protocol_info.description}<br><br>
        <b>支持特性:</b><br>
        {'<br>'.join(['• ' + feature for feature in self.protocol_info.supported_features])}
        """
        self.setToolTip(tooltip_text)


class LatencyIndicator(QLabel):
    """延迟指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.latency = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self.setFixedSize(60, 20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_latency(None)
    
    def update_latency(self, latency: Optional[int]):
        """更新延迟显示"""
        self.latency = latency
        
        if latency is None:
            self.setText("未测试")
            color = "#9E9E9E"
            text_color = "white"
        elif latency == -1:
            self.setText("超时")
            color = "#F44336"
            text_color = "white"
        elif latency < 100:
            self.setText(f"{latency}ms")
            color = "#4CAF50"
            text_color = "white"
        elif latency < 300:
            self.setText(f"{latency}ms")
            color = "#FF9800"
            text_color = "white"
        else:
            self.setText(f"{latency}ms")
            color = "#F44336"
            text_color = "white"
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: {text_color};
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
            }}
        """)


class NodeItem(QFrame):
    """节点项组件"""
    
    node_selected = pyqtSignal(Node)
    test_requested = pyqtSignal(Node)
    
    def __init__(self, node: Node, protocol_info: ProtocolDisplayInfo, parent=None):
        super().__init__(parent)
        self.node = node
        self.protocol_info = protocol_info
        self.selected = False
        self._setup_ui()
        self._setup_context_menu()
    
    def _setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                background-color: white;
                margin: 2px;
            }
            QFrame:hover {
                border-color: #2196F3;
                background-color: #F5F5F5;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # 左侧：协议标识和节点信息
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)
        
        # 节点名称和协议标识
        name_protocol_layout = QHBoxLayout()
        name_protocol_layout.setSpacing(8)
        
        # 节点名称
        self.name_label = QLabel(self.node.remark or "未命名节点")
        self.name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        name_protocol_layout.addWidget(self.name_label)
        
        # 协议标识
        self.protocol_badge = ProtocolBadge(self.protocol_info)
        name_protocol_layout.addWidget(self.protocol_badge)
        
        name_protocol_layout.addStretch()
        left_layout.addLayout(name_protocol_layout)
        
        # 节点地址和端口
        address_text = f"{self.node.address}:{self.node.port}"
        self.address_label = QLabel(address_text)
        self.address_label.setFont(QFont("Consolas", 9))
        self.address_label.setStyleSheet("color: #666666;")
        left_layout.addWidget(self.address_label)
        
        layout.addLayout(left_layout)
        
        # 中间：延迟信息
        middle_layout = QVBoxLayout()
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        latency_label = QLabel("延迟")
        latency_label.setFont(QFont("Arial", 9))
        latency_label.setStyleSheet("color: #666666;")
        latency_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle_layout.addWidget(latency_label)
        
        self.latency_indicator = LatencyIndicator()
        middle_layout.addWidget(self.latency_indicator)
        
        layout.addLayout(middle_layout)
        
        # 右侧：端口信息和操作按钮
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 本地端口
        if hasattr(self.node, 'local_port') and self.node.local_port:
            port_text = f"本地端口: {self.node.local_port}"
        else:
            port_text = "未分配端口"
        
        self.port_label = QLabel(port_text)
        self.port_label.setFont(QFont("Arial", 9))
        self.port_label.setStyleSheet("color: #666666;")
        self.port_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.port_label)
        
        # 测试按钮
        self.test_button = QPushButton("测试")
        self.test_button.setFixedSize(50, 25)
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.test_button.clicked.connect(lambda: self.test_requested.emit(self.node))
        right_layout.addWidget(self.test_button)
        
        layout.addLayout(right_layout)
        
        # 更新延迟显示
        self.update_latency()
    
    def _setup_context_menu(self):
        """设置右键菜单"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 复制节点信息
        copy_action = QAction("复制节点信息", self)
        copy_action.triggered.connect(self._copy_node_info)
        menu.addAction(copy_action)
        
        # 复制地址
        copy_address_action = QAction("复制地址", self)
        copy_address_action.triggered.connect(self._copy_address)
        menu.addAction(copy_address_action)
        
        menu.addSeparator()
        
        # 测试延迟
        test_action = QAction("测试延迟", self)
        test_action.triggered.connect(lambda: self.test_requested.emit(self.node))
        menu.addAction(test_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def _copy_node_info(self):
        """复制节点信息"""
        from PyQt6.QtWidgets import QApplication
        
        info_text = f"""节点名称: {self.node.remark}
协议: {self.node.protocol}
地址: {self.node.address}
端口: {self.node.port}
本地端口: {getattr(self.node, 'local_port', '未分配')}
延迟: {self.node.latency if self.node.latency else '未测试'}ms"""
        
        QApplication.clipboard().setText(info_text)
    
    def _copy_address(self):
        """复制地址"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(f"{self.node.address}:{self.node.port}")
    
    def update_latency(self):
        """更新延迟显示"""
        latency = getattr(self.node, 'latency', None)
        self.latency_indicator.update_latency(latency)
    
    def update_port(self):
        """更新端口显示"""
        if hasattr(self.node, 'local_port') and self.node.local_port:
            port_text = f"本地端口: {self.node.local_port}"
        else:
            port_text = "未分配端口"
        self.port_label.setText(port_text)
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.selected = selected
        if selected:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #2196F3;
                    border-radius: 8px;
                    background-color: #E3F2FD;
                    margin: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    background-color: white;
                    margin: 2px;
                }
                QFrame:hover {
                    border-color: #2196F3;
                    background-color: #F5F5F5;
                }
            """)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.node_selected.emit(self.node)
        super().mousePressEvent(event)


class EnhancedNodeList(QWidget):
    """增强的节点列表组件"""
    
    node_selected = pyqtSignal(Node)
    nodes_test_requested = pyqtSignal(list)
    single_node_test_requested = pyqtSignal(Node)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui_manager = UIIntegrationManager()
        self.nodes: List[Node] = []
        self.node_items: List[NodeItem] = []
        self.selected_nodes: List[Node] = []
        self._setup_ui()
        self._setup_ui_callbacks()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 顶部工具栏
        self._create_toolbar(layout)
        
        # 节点列表区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(4)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area)
        
        # 底部状态栏
        self._create_status_bar(layout)
    
    def _create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar_frame = QFrame()
        toolbar_frame.setFixedHeight(40)
        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(12, 6, 12, 6)
        toolbar_layout.setSpacing(8)
        
        # 节点统计
        self.stats_label = QLabel("节点: 0 | 协议: 0")
        self.stats_label.setFont(QFont("Arial", 10))
        self.stats_label.setStyleSheet("color: #666666;")
        toolbar_layout.addWidget(self.stats_label)
        
        toolbar_layout.addStretch()
        
        # TUN模式指示器
        self.tun_indicator = QLabel("TUN模式: 未检测")
        self.tun_indicator.setFont(QFont("Arial", 9))
        self.tun_indicator.setStyleSheet("color: #666666;")
        toolbar_layout.addWidget(self.tun_indicator)
        
        # 测试所有按钮
        self.test_all_button = QPushButton("测试所有")
        self.test_all_button.setFixedSize(80, 28)
        self.test_all_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:pressed {
                background-color: #3D8B40;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        self.test_all_button.clicked.connect(self._test_all_nodes)
        toolbar_layout.addWidget(self.test_all_button)
        
        parent_layout.addWidget(toolbar_frame)
    
    def _create_status_bar(self, parent_layout):
        """创建状态栏"""
        self.status_frame = QFrame()
        self.status_frame.setFixedHeight(30)
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }
        """)
        
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 4, 12, 4)
        status_layout.setSpacing(8)
        
        # 状态文本
        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setStyleSheet("color: #666666;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 进度条（默认隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(200, 16)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                text-align: center;
                font-size: 9px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 7px;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        parent_layout.addWidget(self.status_frame)
    
    def _setup_ui_callbacks(self):
        """设置UI回调"""
        # 注册UI更新回调
        self.ui_manager.register_ui_callback(UIUpdateType.NODE_LIST_REFRESH, self._on_node_list_update)
        self.ui_manager.register_ui_callback(UIUpdateType.LATENCY_TEST_PROGRESS, self._on_latency_progress)
        self.ui_manager.register_ui_callback(UIUpdateType.LATENCY_TEST_COMPLETE, self._on_latency_complete)
        self.ui_manager.register_ui_callback(UIUpdateType.TUN_MODE_STATUS, self._on_tun_status_update)
        self.ui_manager.register_ui_callback(UIUpdateType.PORT_ALLOCATION_UPDATE, self._on_port_allocation_update)
    
    def update_nodes(self, nodes: List[Node]):
        """更新节点列表"""
        self.nodes = nodes.copy()
        self._refresh_node_items()
        
        # 通知UI管理器
        self.ui_manager.update_node_list(nodes)
    
    def _refresh_node_items(self):
        """刷新节点项"""
        # 清除现有项
        for item in self.node_items:
            item.setParent(None)
        self.node_items.clear()
        
        # 创建新项
        for node in self.nodes:
            protocol_info = self.ui_manager.get_protocol_display_info(node.protocol)
            if protocol_info:
                item = NodeItem(node, protocol_info)
                item.node_selected.connect(self._on_node_selected)
                item.test_requested.connect(self.single_node_test_requested.emit)
                
                # 插入到布局中（在stretch之前）
                self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, item)
                self.node_items.append(item)
    
    def _test_all_nodes(self):
        """测试所有节点"""
        if self.nodes:
            self.nodes_test_requested.emit(self.nodes)
    
    def _on_node_selected(self, node: Node):
        """节点选中事件"""
        # 更新选中状态
        for item in self.node_items:
            item.set_selected(item.node.uuid == node.uuid)
        
        self.node_selected.emit(node)
    
    def _on_node_list_update(self, update_data: UIUpdateData):
        """节点列表更新回调"""
        data = update_data.data
        total_count = data.get('total_count', 0)
        protocol_stats = data.get('protocol_stats', {})
        
        # 更新统计信息
        protocol_count = len(protocol_stats)
        self.stats_label.setText(f"节点: {total_count} | 协议: {protocol_count}")
        
        # 更新状态
        if total_count > 0:
            protocol_list = ', '.join(protocol_stats.keys())
            self.status_label.setText(f"已加载 {total_count} 个节点 ({protocol_list})")
        else:
            self.status_label.setText("无节点")
    
    def _on_latency_progress(self, update_data: UIUpdateData):
        """延迟测试进度回调"""
        data = update_data.data
        completed = data.get('completed', 0)
        total = data.get('total', 0)
        percentage = data.get('percentage', 0)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(completed)
        
        # 更新状态文本
        self.status_label.setText(f"延迟测试进行中... {completed}/{total} ({percentage:.1f}%)")
        
        # 禁用测试按钮
        self.test_all_button.setEnabled(False)
        self.test_all_button.setText("测试中...")
    
    def _on_latency_complete(self, update_data: UIUpdateData):
        """延迟测试完成回调"""
        data = update_data.data
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 启用测试按钮
        self.test_all_button.setEnabled(True)
        self.test_all_button.setText("测试所有")
        
        if data.get('cancelled'):
            self.status_label.setText("延迟测试已取消")
        else:
            result = data.get('result')
            if result:
                success_rate = data.get('success_rate', 0)
                duration = data.get('test_duration', 0)
                self.status_label.setText(f"延迟测试完成 - 成功率: {success_rate:.1f}% | 用时: {duration:.1f}s")
            else:
                self.status_label.setText("延迟测试完成")
        
        # 更新所有节点项的延迟显示
        for item in self.node_items:
            item.update_latency()
    
    def _on_tun_status_update(self, update_data: UIUpdateData):
        """TUN模式状态更新回调"""
        data = update_data.data
        active = data.get('active', False)
        interfaces = data.get('interfaces', [])
        
        if active:
            interface_text = f" ({', '.join(interfaces)})" if interfaces else ""
            self.tun_indicator.setText(f"TUN模式: 激活{interface_text}")
            self.tun_indicator.setStyleSheet("color: #FF9800; font-weight: bold;")
        else:
            self.tun_indicator.setText("TUN模式: 未激活")
            self.tun_indicator.setStyleSheet("color: #666666;")
    
    def _on_port_allocation_update(self, update_data: UIUpdateData):
        """端口分配更新回调"""
        # 更新所有节点项的端口显示
        for item in self.node_items:
            item.update_port()
    
    def start_latency_test(self):
        """启动延迟测试"""
        if self.nodes:
            self.ui_manager.start_latency_test(self.nodes)
    
    def cancel_latency_test(self):
        """取消延迟测试"""
        self.ui_manager.cancel_latency_test()