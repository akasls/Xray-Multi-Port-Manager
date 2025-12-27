"""
主页面组件 - 合并订阅、节点列表和控制面板
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu, QAbstractItemView,
    QGraphicsDropShadowEffect, QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QAction

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from xray_gui.core.node import Node


class MainPage(QFrame):
    """主页面 - 合并所有功能"""
    
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
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 顶部控制栏
        self._create_control_bar(layout)
        
        # 节点列表
        self._create_node_list(layout)
    
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
    
    def _create_node_list(self, layout):
        """创建节点列表"""
        list_frame = QFrame()
        list_frame.setObjectName("node_list_frame")
        
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        
        # 工具栏
        toolbar = QWidget()
        toolbar.setObjectName("list_toolbar")
        toolbar.setFixedHeight(45)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 8, 15, 8)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_input")
        self.search_input.setPlaceholderText("搜索节点...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(self.search_input)
        
        toolbar_layout.addStretch()
        
        # 统计信息
        self.stats_label = QLabel("共 0 个节点 | 已分配 0 个端口")
        self.stats_label.setObjectName("stats_label")
        toolbar_layout.addWidget(self.stats_label)
        
        list_layout.addWidget(toolbar)
        
        # 表格
        self.table = QTableWidget()
        self.table.setObjectName("node_table")
        self._setup_table()
        list_layout.addWidget(self.table)
        
        # 添加阴影
        shadow = QGraphicsDropShadowEffect(list_frame)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        list_frame.setGraphicsEffect(shadow)
        
        layout.addWidget(list_frame, 1)
    
    def _setup_table(self):
        """设置表格"""
        columns = ["#", "节点名称", "地址", "端口", "本地端口", "延迟", "协议"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(3, 65)
        self.table.setColumnWidth(4, 75)
        self.table.setColumnWidth(5, 75)
        self.table.setColumnWidth(6, 65)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
    
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
            
            #node_list_frame {
                background: rgba(20, 15, 40, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 14px;
            }
            
            #list_toolbar {
                background: rgba(30, 20, 50, 0.6);
                border-bottom: 1px solid rgba(120, 0, 255, 0.2);
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }
            
            #search_input {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 8px;
                padding: 6px 12px;
                color: white;
                font-size: 12px;
            }
            
            #search_input:focus {
                border: 1px solid rgba(120, 0, 255, 0.6);
            }
            
            #stats_label {
                color: rgba(180, 150, 220, 0.8);
                font-size: 12px;
            }
            
            #node_table {
                background: transparent;
                border: none;
                gridline-color: transparent;
            }
            
            #node_table::item {
                padding: 8px;
                color: rgba(255, 255, 255, 0.9);
                border-bottom: 1px solid rgba(120, 0, 255, 0.1);
            }
            
            #node_table::item:selected {
                background: rgba(120, 0, 255, 0.3);
            }
            
            #node_table::item:alternate {
                background: rgba(40, 30, 60, 0.3);
            }
            
            QHeaderView::section {
                background: rgba(30, 20, 50, 0.9);
                color: rgba(200, 150, 255, 0.9);
                padding: 10px;
                border: none;
                border-bottom: 1px solid rgba(120, 0, 255, 0.3);
                font-weight: bold;
                font-size: 11px;
            }
        """)
    
    def _on_refresh(self):
        """刷新按钮点击"""
        url = self.url_input.text().strip()
        if url:
            self.refresh_requested.emit(url)
    
    def _on_test(self):
        """测速按钮点击"""
        selected = self.get_selected_nodes()
        if selected:
            self.test_selected.emit(selected)
        else:
            self.test_all.emit()
    
    def _on_start(self):
        """启动按钮点击"""
        self.start_requested.emit()
    
    def _on_stop(self):
        """停止按钮点击"""
        self.stop_requested.emit()
    
    def _on_search(self, text: str):
        """搜索处理"""
        self._refresh_table(text)
    
    def _show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(25, 20, 45, 0.98);
                border: 1px solid rgba(120, 0, 255, 0.4);
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: rgba(255, 255, 255, 0.9);
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(120, 0, 255, 0.4);
            }
        """)
        
        test_action = QAction("⚡ 测试选中节点", self)
        test_action.triggered.connect(lambda: self.test_selected.emit(self.get_selected_nodes()))
        menu.addAction(test_action)
        
        test_all_action = QAction("↻ 测试所有节点", self)
        test_all_action.triggered.connect(self.test_all.emit)
        menu.addAction(test_all_action)
        
        menu.exec(self.table.mapToGlobal(pos))
    
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
        self._refresh_table()
    
    def _refresh_table(self, filter_text: str = ""):
        """刷新表格"""
        self.table.setRowCount(0)
        
        filtered_nodes = self._nodes
        if filter_text:
            filter_text = filter_text.lower()
            filtered_nodes = [n for n in self._nodes if filter_text in n.remark.lower()]
        
        for node in filtered_nodes:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 序号
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, index_item)
            
            # 节点名称
            name_item = QTableWidgetItem(node.remark)
            self.table.setItem(row, 1, name_item)
            
            # 地址
            addr_item = QTableWidgetItem(node.address)
            self.table.setItem(row, 2, addr_item)
            
            # 端口
            port_item = QTableWidgetItem(str(node.port))
            port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, port_item)
            
            # 本地端口
            local_port = str(node.local_port) if node.local_port else "-"
            local_item = QTableWidgetItem(local_port)
            local_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, local_item)
            
            # 延迟
            latency_item = QTableWidgetItem(node.latency_display)
            latency_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_latency_color(latency_item, node.latency)
            self.table.setItem(row, 5, latency_item)
            
            # 协议
            protocol_item = QTableWidgetItem(node.protocol.upper())
            protocol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, protocol_item)
        
        # 更新统计
        allocated = len([n for n in self._nodes if n.local_port])
        self.stats_label.setText(f"共 {len(filtered_nodes)} 个节点 | 已分配 {allocated} 个端口")
    
    def _set_latency_color(self, item: QTableWidgetItem, latency: Optional[int]):
        """设置延迟颜色"""
        if latency is None:
            item.setForeground(QColor(150, 150, 150))
        elif latency == -1:
            item.setForeground(QColor(255, 100, 100))
        elif latency < 100:
            item.setForeground(QColor(100, 255, 150))
        elif latency < 300:
            item.setForeground(QColor(255, 220, 100))
        else:
            item.setForeground(QColor(255, 150, 100))
    
    def get_selected_nodes(self) -> List:
        """获取选中的节点"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        filter_text = self.search_input.text().lower()
        if filter_text:
            filtered_nodes = [n for n in self._nodes if filter_text in n.remark.lower()]
        else:
            filtered_nodes = self._nodes
        
        return [filtered_nodes[row] for row in sorted(selected_rows) if row < len(filtered_nodes)]
