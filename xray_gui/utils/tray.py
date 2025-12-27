"""
系统托盘管理
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import pyqtSignal, QObject, QSize


class TrayIcon(QObject):
    """系统托盘图标"""
    
    # 信号
    show_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._is_running = False
        self._tray = QSystemTrayIcon(parent)
        
        self._setup_icon()
        self._setup_menu()
        self._connect_signals()
    
    def _setup_icon(self):
        """设置图标"""
        self._update_icon()
    
    def _create_icon(self, running: bool) -> QIcon:
        """创建托盘图标"""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景圆
        if running:
            # 运行中 - 绿色渐变
            gradient_color = QColor(100, 255, 150)
        else:
            # 已停止 - 灰色
            gradient_color = QColor(150, 150, 150)
        
        painter.setBrush(QBrush(gradient_color))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 2))
        painter.drawEllipse(4, 4, size - 8, size - 8)
        
        # 中心图标 (X 形状代表 Xray)
        painter.setPen(QPen(QColor(255, 255, 255), 4))
        margin = 18
        painter.drawLine(margin, margin, size - margin, size - margin)
        painter.drawLine(size - margin, margin, margin, size - margin)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _update_icon(self):
        """更新图标"""
        icon = self._create_icon(self._is_running)
        self._tray.setIcon(icon)
        
        # 更新提示文字
        status = "运行中" if self._is_running else "已停止"
        self._tray.setToolTip(f"Xray GUI Manager - {status}")
    
    def _setup_menu(self):
        """设置右键菜单"""
        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background: rgba(30, 30, 50, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                color: rgba(255, 255, 255, 0.9);
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(120, 0, 255, 0.4);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 5px 10px;
            }
        """)
        
        # 显示主窗口
        self._show_action = self._menu.addAction("□ 显示主窗口")
        self._show_action.triggered.connect(self.show_requested.emit)
        
        self._menu.addSeparator()
        
        # 启动/停止
        self._start_action = self._menu.addAction("▶ 启动服务")
        self._start_action.triggered.connect(self.start_requested.emit)
        
        self._stop_action = self._menu.addAction("■ 停止服务")
        self._stop_action.triggered.connect(self.stop_requested.emit)
        self._stop_action.setEnabled(False)
        
        self._menu.addSeparator()
        
        # 退出
        self._quit_action = self._menu.addAction("❌ 退出")
        self._quit_action.triggered.connect(self.quit_requested.emit)
        
        self._tray.setContextMenu(self._menu)
    
    def _connect_signals(self):
        """连接信号"""
        self._tray.activated.connect(self._on_activated)
    
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """托盘图标激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()
    
    def show(self):
        """显示托盘图标"""
        self._tray.show()
    
    def hide(self):
        """隐藏托盘图标"""
        self._tray.hide()
    
    def set_running(self, running: bool):
        """设置运行状态"""
        self._is_running = running
        self._update_icon()
        
        # 更新菜单状态
        self._start_action.setEnabled(not running)
        self._stop_action.setEnabled(running)
    
    def show_message(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information):
        """显示通知消息"""
        self._tray.showMessage(title, message, icon, 3000)
    
    def is_visible(self) -> bool:
        """是否可见"""
        return self._tray.isVisible()
    
    @staticmethod
    def is_available() -> bool:
        """系统托盘是否可用"""
        return QSystemTrayIcon.isSystemTrayAvailable()
