"""
节点列表组件
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMenu, QAbstractItemView, QPushButton, QWidget,
    QGraphicsDropShadowEffect, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QAction

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from xray_gui.core.node import Node


class NodeListWidget(QFrame):
    """节点列表组件"""
    
    # 信号
    test_selected = pyqtSignal(list)  # 测试选中节点
    test_all = pyqtSignal()  # 测试所有节点
    selection_changed = pyqtSignal(list)  # 选中变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("node_list_widget")
        
        self._nodes: List[Node] = []
        self._setup_ui()
        self._apply_styles()
        self._add_shadow()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(50)
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
        
        # 节点统计
        self.count_label = QLabel("共 0 个节点")
        self.count_label.setObjectName("count_label")
        toolbar_layout.addWidget(self.count_label)
        
        # 测试按钮
        self.test_btn = QPushButton("⚡ 测速")
        self.test_btn.setObjectName("action_btn")
        self.test_btn.clicked.connect(self._on_test_clicked)
        toolbar_layout.addWidget(self.test_btn)
        
        layout.addWidget(toolbar)
        
        # 表格
        self.table = QTableWidget()
        self.table.setObjectName("node_table")
        self._setup_table()
        layout.addWidget(self.table)
    
    def _setup_table(self):
        """设置表格"""
        # 列配置
        columns = ["", "节点名称", "地址", "端口", "本地端口", "延迟", "协议"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        # 表头设置
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(6, 70)
        
        # 表格属性
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #node_list_widget {
                background-color: rgba(30, 30, 50, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            
            #toolbar {
                background: rgba(20, 20, 40, 0.5);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
            
            #search_input {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px 12px;
                color: white;
            }
            
            #search_input:focus {
                border: 1px solid rgba(120, 0, 255, 0.5);
            }
            
            #count_label {
                color: rgba(255, 255, 255, 0.7);
                padding: 0 15px;
            }
            
            #action_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(120, 0, 255, 0.6),
                    stop:1 rgba(0, 212, 255, 0.6)
                );
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }
            
            #action_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(140, 20, 255, 0.8),
                    stop:1 rgba(20, 232, 255, 0.8)
                );
            }
            
            #node_table {
                background: transparent;
                border: none;
                gridline-color: transparent;
            }
            
            #node_table::item {
                padding: 8px;
                color: rgba(255, 255, 255, 0.9);
            }
            
            #node_table::item:selected {
                background: rgba(120, 0, 255, 0.3);
            }
            
            #node_table::item:alternate {
                background: rgba(255, 255, 255, 0.03);
            }
            
            QHeaderView::section {
                background: rgba(40, 40, 60, 0.8);
                color: rgba(255, 255, 255, 0.8);
                padding: 10px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                font-weight: bold;
            }
        """)
    
    def _add_shadow(self):
        """添加阴影"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
    
    def set_nodes(self, nodes: List[Node]):
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
        
        self.count_label.setText(f"共 {len(filtered_nodes)} 个节点")
    
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
    
    def _on_search(self, text: str):
        """搜索处理"""
        self._refresh_table(text)
    
    def _on_test_clicked(self):
        """测试按钮点击"""
        selected = self.get_selected_nodes()
        if selected:
            self.test_selected.emit(selected)
        else:
            self.test_all.emit()
    
    def _on_selection_changed(self):
        """选中变化"""
        self.selection_changed.emit(self.get_selected_nodes())
    
    def _show_context_menu(self, pos: QPoint):
        """显示右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(30, 30, 50, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.15);
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
    
    def get_selected_nodes(self) -> List[Node]:
        """获取选中的节点"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        # 根据搜索过滤后的索引获取节点
        filter_text = self.search_input.text().lower()
        if filter_text:
            filtered_nodes = [n for n in self._nodes if filter_text in n.remark.lower()]
        else:
            filtered_nodes = self._nodes
        
        return [filtered_nodes[row] for row in sorted(selected_rows) if row < len(filtered_nodes)]
    
    def update_node_latency(self, node: Node, latency: Optional[int]):
        """更新节点延迟"""
        node.latency = latency
        self._refresh_table(self.search_input.text())
