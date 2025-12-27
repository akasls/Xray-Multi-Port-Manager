"""
订阅管理面板
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QTextEdit,
    QGraphicsDropShadowEffect, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class SubscriptionPanel(QFrame):
    """订阅管理面板"""
    
    # 信号
    refresh_requested = pyqtSignal(str)  # 刷新订阅
    url_changed = pyqtSignal(str)  # URL 变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("subscription_panel")
        
        self._setup_ui()
        self._apply_styles()
        self._add_shadow()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("↓ 订阅管理")
        title.setObjectName("panel_title")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 订阅 URL 输入区域
        url_widget = QWidget()
        url_layout = QVBoxLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(8)
        
        url_label = QLabel("订阅地址")
        url_label.setObjectName("field_label")
        url_layout.addWidget(url_label)
        
        # URL 输入框和按钮
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText("请输入订阅地址 (支持 Base64 编码)")
        self.url_input.textChanged.connect(lambda t: self.url_changed.emit(t))
        input_row.addWidget(self.url_input)
        
        self.refresh_btn = QPushButton("↻ 刷新")
        self.refresh_btn.setObjectName("refresh_btn")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self._on_refresh)
        input_row.addWidget(self.refresh_btn)
        
        url_layout.addLayout(input_row)
        layout.addWidget(url_widget)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setObjectName("progress_bar")
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)  # 不确定进度
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # 状态信息
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        layout.addWidget(self.status_label)
        
        # 统计信息
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 10, 0, 0)
        stats_layout.setSpacing(20)
        
        # 节点数量
        self.node_count_card = self._create_stat_card("节点数量", "0")
        stats_layout.addWidget(self.node_count_card)
        
        # 有效节点
        self.valid_count_card = self._create_stat_card("有效节点", "0")
        stats_layout.addWidget(self.valid_count_card)
        
        # 上次更新
        self.last_update_card = self._create_stat_card("上次更新", "-")
        stats_layout.addWidget(self.last_update_card)
        
        stats_layout.addStretch()
        layout.addWidget(stats_widget)
        
        layout.addStretch()
    
    def _create_stat_card(self, label: str, value: str) -> QFrame:
        """创建统计卡片"""
        card = QFrame()
        card.setObjectName("stat_card")
        card.setFixedSize(120, 70)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(5)
        
        value_label = QLabel(value)
        value_label.setObjectName("stat_value")
        value_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(value_label)
        
        label_widget = QLabel(label)
        label_widget.setObjectName("stat_label")
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(label_widget)
        
        # 保存引用以便更新
        card.value_label = value_label
        
        return card
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #subscription_panel {
                background-color: rgba(30, 30, 50, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            
            #panel_title {
                color: rgba(255, 255, 255, 0.95);
                padding-bottom: 10px;
            }
            
            #field_label {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
            }
            
            #url_input {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                padding: 12px 15px;
                color: white;
                font-size: 13px;
            }
            
            #url_input:focus {
                border: 1px solid rgba(120, 0, 255, 0.5);
                background: rgba(255, 255, 255, 0.12);
            }
            
            #refresh_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(120, 0, 255, 0.7),
                    stop:1 rgba(0, 212, 255, 0.7)
                );
                border: none;
                border-radius: 10px;
                padding: 12px;
                color: white;
                font-weight: bold;
                font-size: 13px;
            }
            
            #refresh_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(140, 20, 255, 0.9),
                    stop:1 rgba(20, 232, 255, 0.9)
                );
            }
            
            #refresh_btn:disabled {
                background: rgba(100, 100, 100, 0.5);
            }
            
            #progress_bar {
                background: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            
            #progress_bar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7800ff,
                    stop:1 #00d4ff
                );
                border-radius: 2px;
            }
            
            #status_label {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
            }
            
            #stat_card {
                background: rgba(40, 40, 60, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
            
            #stat_value {
                color: rgba(255, 255, 255, 0.95);
            }
            
            #stat_label {
                color: rgba(255, 255, 255, 0.6);
                font-size: 11px;
            }
        """)
    
    def _add_shadow(self):
        """添加阴影"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
    
    def _on_refresh(self):
        """刷新按钮点击"""
        url = self.url_input.text().strip()
        if url:
            self.refresh_requested.emit(url)
    
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
        if loading:
            self.status_label.setText("正在获取订阅...")
        else:
            self.status_label.setText("")
    
    def set_status(self, message: str, is_error: bool = False):
        """设置状态信息"""
        self.status_label.setText(message)
        if is_error:
            self.status_label.setStyleSheet("color: rgba(255, 100, 100, 0.9);")
        else:
            self.status_label.setStyleSheet("color: rgba(100, 255, 150, 0.9);")
    
    def update_stats(self, total: int, valid: int, last_update: str):
        """更新统计信息"""
        self.node_count_card.value_label.setText(str(total))
        self.valid_count_card.value_label.setText(str(valid))
        self.last_update_card.value_label.setText(last_update)
