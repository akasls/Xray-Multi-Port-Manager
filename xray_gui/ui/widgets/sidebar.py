"""
侧边栏导航组件
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont


class SidebarItem(QFrame):
    """侧边栏导航项"""
    
    clicked = pyqtSignal()
    
    def __init__(self, text: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar_item")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        
        self._text = text
        self._icon = icon
        self._selected = False
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(12)
        
        # 图标
        if self._icon:
            self.icon_label = QLabel(self._icon)
            self.icon_label.setObjectName("item_icon")
            self.icon_label.setFixedWidth(24)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_font = QFont("Segoe UI Emoji", 14)
            self.icon_label.setFont(icon_font)
            layout.addWidget(self.icon_label)
        
        # 文本
        self.text_label = QLabel(self._text)
        self.text_label.setObjectName("item_text")
        text_font = QFont("Segoe UI", 11)
        self.text_label.setFont(text_font)
        layout.addWidget(self.text_label)
        
        layout.addStretch()
        
        # 选中指示器
        self.indicator = QFrame()
        self.indicator.setObjectName("indicator")
        self.indicator.setFixedSize(4, 24)
        self.indicator.setVisible(False)
        layout.addWidget(self.indicator)
    
    def _apply_styles(self):
        """应用样式"""
        self._update_style()
    
    def _update_style(self):
        """更新样式"""
        if self._selected:
            self.setStyleSheet("""
                #sidebar_item {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(120, 0, 255, 0.4),
                        stop:1 rgba(0, 212, 255, 0.2)
                    );
                    border: none;
                    border-radius: 12px;
                }
                #item_icon, #item_text {
                    color: rgba(255, 255, 255, 0.95);
                }
                #indicator {
                    background: qlineargradient(
                        x1:0, y1:0, x2:0, y2:1,
                        stop:0 #7800ff,
                        stop:1 #00d4ff
                    );
                    border-radius: 2px;
                }
            """)
            self.indicator.setVisible(True)
        else:
            self.setStyleSheet("""
                #sidebar_item {
                    background: transparent;
                    border: none;
                    border-radius: 12px;
                }
                #sidebar_item:hover {
                    background: rgba(255, 255, 255, 0.08);
                }
                #item_icon, #item_text {
                    color: rgba(255, 255, 255, 0.7);
                }
            """)
            self.indicator.setVisible(False)
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self._selected = selected
        self._update_style()
    
    def is_selected(self) -> bool:
        """获取选中状态"""
        return self._selected
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        if not self._selected:
            # 悬停动画效果
            pass
        super().enterEvent(event)


class Sidebar(QFrame):
    """侧边栏导航"""
    
    page_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        
        self._items: list[SidebarItem] = []
        self._current_index = 0
        
        self._setup_ui()
        self._apply_styles()
        self._add_shadow()
    
    def _setup_ui(self):
        """设置 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 15, 10, 15)
        self.main_layout.setSpacing(5)
        
        # Logo 区域
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(10, 5, 10, 15)
        
        logo_label = QLabel("☆")
        logo_label.setObjectName("logo")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_font = QFont("Segoe UI Emoji", 28)
        logo_label.setFont(logo_font)
        logo_layout.addWidget(logo_label)
        
        app_name = QLabel("Xray GUI")
        app_name.setObjectName("app_name")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        app_name.setFont(name_font)
        logo_layout.addWidget(app_name)
        
        self.main_layout.addWidget(logo_widget)
        
        # 分隔线
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        self.main_layout.addWidget(separator)
        
        # 导航项容器
        self.items_widget = QWidget()
        self.items_layout = QVBoxLayout(self.items_widget)
        self.items_layout.setContentsMargins(0, 10, 0, 0)
        self.items_layout.setSpacing(5)
        self.main_layout.addWidget(self.items_widget)
        
        self.main_layout.addStretch()
        
        # 底部状态
        self.status_widget = QWidget()
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setContentsMargins(10, 10, 10, 5)
        
        self.status_label = QLabel("● 已停止")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont("Segoe UI", 10)
        self.status_label.setFont(status_font)
        status_layout.addWidget(self.status_label)
        
        self.main_layout.addWidget(self.status_widget)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #sidebar {
                background-color: rgba(20, 20, 40, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            
            #logo {
                color: white;
            }
            
            #app_name {
                color: rgba(255, 255, 255, 0.9);
            }
            
            #separator {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent,
                    stop:0.5 rgba(255, 255, 255, 0.2),
                    stop:1 transparent
                );
            }
            
            #status_label {
                color: rgba(255, 100, 100, 0.8);
            }
        """)
    
    def _add_shadow(self):
        """添加阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)
    
    def add_item(self, text: str, icon: str = ""):
        """添加导航项"""
        item = SidebarItem(text, icon)
        item.clicked.connect(lambda: self._on_item_clicked(item))
        
        self.items_layout.addWidget(item)
        self._items.append(item)
        
        # 第一个项默认选中
        if len(self._items) == 1:
            item.set_selected(True)
    
    def _on_item_clicked(self, item: SidebarItem):
        """导航项点击处理"""
        index = self._items.index(item)
        if index != self._current_index:
            # 取消之前的选中
            if 0 <= self._current_index < len(self._items):
                self._items[self._current_index].set_selected(False)
            
            # 选中新项
            item.set_selected(True)
            self._current_index = index
            self.page_changed.emit(index)
    
    def set_current_index(self, index: int):
        """设置当前选中项"""
        if 0 <= index < len(self._items):
            self._on_item_clicked(self._items[index])
    
    def set_status(self, running: bool):
        """设置运行状态"""
        if running:
            self.status_label.setText("● 运行中")
            self.status_label.setStyleSheet("color: rgba(100, 255, 150, 0.9);")
        else:
            self.status_label.setText("● 已停止")
            self.status_label.setStyleSheet("color: rgba(255, 100, 100, 0.8);")
