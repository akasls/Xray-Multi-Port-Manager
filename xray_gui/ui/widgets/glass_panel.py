"""
玻璃态面板组件
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect, QWidget
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont


class GlassPanel(QFrame):
    """玻璃态面板组件"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("glass_panel")
        
        self._title = title
        self._setup_ui()
        self._apply_styles()
        self._add_shadow()
    
    def _setup_ui(self):
        """设置 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 20)
        self.main_layout.setSpacing(15)
        
        # 标题
        if self._title:
            self.title_label = QLabel(self._title)
            self.title_label.setObjectName("panel_title")
            title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
            self.title_label.setFont(title_font)
            self.main_layout.addWidget(self.title_label)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #glass_panel {
                background-color: rgba(30, 30, 50, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 16px;
            }
            
            #panel_title {
                color: rgba(255, 255, 255, 0.95);
                padding-bottom: 5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
    
    def _add_shadow(self):
        """添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
    
    def add_widget(self, widget: QWidget):
        """添加子组件"""
        self.content_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """添加布局"""
        self.content_layout.addLayout(layout)
    
    def add_stretch(self):
        """添加弹性空间"""
        self.content_layout.addStretch()


class GlassCard(QFrame):
    """玻璃态卡片组件（更小的面板）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glass_card")
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置 UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 12, 15, 12)
        self.layout.setSpacing(8)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #glass_card {
                background-color: rgba(40, 40, 60, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
            
            #glass_card:hover {
                background-color: rgba(50, 50, 70, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
    
    def add_widget(self, widget: QWidget):
        """添加子组件"""
        self.layout.addWidget(widget)


class GlassButton(QFrame):
    """玻璃态按钮"""
    
    def __init__(self, text: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("glass_button")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._text = text
        self._icon = icon
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)
        
        if self._icon:
            icon_label = QLabel(self._icon)
            icon_label.setObjectName("button_icon")
            layout.addWidget(icon_label)
        
        if self._text:
            text_label = QLabel(self._text)
            text_label.setObjectName("button_text")
            layout.addWidget(text_label)
        
        layout.addStretch()
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #glass_button {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(120, 0, 255, 0.4),
                    stop:1 rgba(0, 212, 255, 0.4)
                );
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }
            
            #glass_button:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(140, 20, 255, 0.6),
                    stop:1 rgba(20, 232, 255, 0.6)
                );
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            #button_icon, #button_text {
                color: rgba(255, 255, 255, 0.95);
            }
        """)
