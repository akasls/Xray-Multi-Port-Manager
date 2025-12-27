"""
主窗口 - 应用程序主界面（无侧边栏版本）
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFrame, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from .widgets.aurora_background import AuroraBackground


class MainWindow(QMainWindow):
    """主窗口类"""
    
    refresh_requested = pyqtSignal()
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xray GUI Manager")
        self.setMinimumSize(1100, 750)
        self.resize(1100, 750)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.aurora_bg = AuroraBackground(self.central_widget)
        self.content_container = QWidget(self.central_widget)
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self._create_title_bar(content_layout)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 10, 15, 15)
        self.content_layout.setSpacing(15)
        content_layout.addWidget(self.content_widget, 1)
        self.content_container.setGeometry(0, 0, self.width(), self.height())

    
    def _create_title_bar(self, layout):
        title_bar = QFrame()
        title_bar.setFixedHeight(50)
        title_bar.setObjectName("title_bar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 10, 0)
        title_label = QLabel("☆ Xray GUI Manager")
        title_label.setObjectName("title_label")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        self.status_indicator = QLabel("● 已停止")
        self.status_indicator.setObjectName("status_stopped")
        title_layout.addWidget(self.status_indicator)
        title_layout.addStretch()
        self.min_btn = QPushButton("─")
        self.min_btn.setObjectName("window_btn")
        self.min_btn.setFixedSize(40, 30)
        self.min_btn.setToolTip("最小化")
        self.min_btn.clicked.connect(self._on_minimize)
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("window_btn")
        self.settings_btn.setFixedSize(40, 30)
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.setFixedSize(40, 30)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.min_btn)
        title_layout.addWidget(self.settings_btn)
        title_layout.addWidget(self.close_btn)
        layout.addWidget(title_bar)
    
    def _on_minimize(self):
        self.minimize_requested.emit()
        self.showMinimized()
    
    def set_status(self, running: bool):
        if running:
            self.status_indicator.setText("● 运行中")
            self.status_indicator.setObjectName("status_running")
        else:
            self.status_indicator.setText("● 已停止")
            self.status_indicator.setObjectName("status_stopped")
        self.status_indicator.setStyleSheet(self.status_indicator.styleSheet())
        self._apply_status_style()
    
    def _apply_status_style(self):
        if "运行中" in self.status_indicator.text():
            self.status_indicator.setStyleSheet("color: rgba(100, 255, 150, 0.9); font-size: 12px; padding: 0 15px;")
        else:
            self.status_indicator.setStyleSheet("color: rgba(255, 100, 100, 0.8); font-size: 12px; padding: 0 15px;")
    
    def set_content(self, widget: QWidget):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.content_layout.addWidget(widget)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: transparent; }
            #title_bar { background: rgba(15, 10, 30, 0.9); border-bottom: 1px solid rgba(120, 0, 255, 0.3); }
            #title_label { color: rgba(255, 255, 255, 0.95); }
            #window_btn { background: transparent; border: none; color: rgba(255, 255, 255, 0.7); font-size: 16px; border-radius: 4px; }
            #window_btn:hover { background: rgba(120, 0, 255, 0.3); color: white; }
            #close_btn { background: transparent; border: none; color: rgba(255, 255, 255, 0.7); font-size: 18px; border-radius: 4px; }
            #close_btn:hover { background: rgba(255, 80, 80, 0.8); color: white; }
        """)
        self._apply_status_style()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'aurora_bg'):
            self.aurora_bg.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, 'content_container'):
            self.content_container.setGeometry(0, 0, self.width(), self.height())
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 50:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
