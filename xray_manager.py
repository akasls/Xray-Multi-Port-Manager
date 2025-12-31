"""
Xray Multi-Port Manager - 现代化 UI 版本
高性能、美观的 Xray 多端口代理管理工具
"""
import sys
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QDialog, QSpinBox,
    QCheckBox, QTextEdit, QMenu, QProgressBar, QToolButton, 
    QGraphicsDropShadowEffect, QScrollArea, QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QAction, QFont, QPainter, QPalette, QBrush, QIcon

# FontAwesome 图标支持
try:
    import qtawesome as qta
    FA_AVAILABLE = True
except ImportError:
    FA_AVAILABLE = False
    print("Warning: qtawesome not installed. Using fallback icons.")

from xray_gui.core.subscription import SubscriptionManager
from xray_gui.core.node import Node
from xray_gui.core.port_allocator import PortAllocator
from xray_gui.core.config_generator import ConfigGenerator
from xray_gui.core.filter_engine import FilterEngine
from xray_gui.core.sort_engine import SortEngine
from xray_gui.core.speed_tester import SpeedTester
from xray_gui.core.xray_service import XrayService

# ============== 配置 ==============
DEFAULT_EXCLUDE = ["官网", "流量", "套餐", "到期", "剩余", "订阅", "群", "频道", "公告", "网址", "TG", "Telegram"]
CONFIG_FILE = Path("app_state.json")
APP_NAME = "Xray Multi-Port Manager"
APP_VERSION = "2.0.0"

# ============== 主题管理 ==============
class ThemeManager:
    """主题管理器 - 支持日间/夜间模式"""
    
    _instance = None
    _is_dark = True
    _callbacks = []
    
    # 暗色主题
    DARK = {
        'PRIMARY': "#667eea",
        'PRIMARY_LIGHT': "#764ba2",
        'PRIMARY_DARK': "#5a67d8",
        'SUCCESS': "#48bb78",
        'SUCCESS_LIGHT': "#68d391",
        'WARNING': "#ed8936",
        'DANGER': "#fc8181",
        'DANGER_DARK': "#f56565",
        'INFO': "#4299e1",
        'BG_DARK': "#0f0f23",
        'BG_CARD': "#1a1a2e",
        'BG_CARD_HOVER': "#252542",
        'BG_INPUT': "#16213e",
        'TEXT_PRIMARY': "#e2e8f0",
        'TEXT_SECONDARY': "#a0aec0",
        'TEXT_MUTED': "#718096",
        'TEXT_PLACEHOLDER': "#4a5568",
        'BORDER': "#2d3748",
        'BORDER_LIGHT': "#4a5568",
    }
    
    # 亮色主题
    LIGHT = {
        'PRIMARY': "#5a67d8",
        'PRIMARY_LIGHT': "#667eea",
        'PRIMARY_DARK': "#4c51bf",
        'SUCCESS': "#38a169",
        'SUCCESS_LIGHT': "#48bb78",
        'WARNING': "#dd6b20",
        'DANGER': "#e53e3e",
        'DANGER_DARK': "#c53030",
        'INFO': "#3182ce",
        'BG_DARK': "#f7fafc",
        'BG_CARD': "#ffffff",
        'BG_CARD_HOVER': "#edf2f7",
        'BG_INPUT': "#edf2f7",
        'TEXT_PRIMARY': "#1a202c",
        'TEXT_SECONDARY': "#4a5568",
        'TEXT_MUTED': "#718096",
        'TEXT_PLACEHOLDER': "#a0aec0",
        'BORDER': "#e2e8f0",
        'BORDER_LIGHT': "#cbd5e0",
    }
    
    @classmethod
    def get(cls, key):
        theme = cls.DARK if cls._is_dark else cls.LIGHT
        return theme.get(key, "#000000")
    
    @classmethod
    def is_dark(cls):
        return cls._is_dark
    
    @classmethod
    def toggle(cls):
        cls._is_dark = not cls._is_dark
        for callback in cls._callbacks:
            callback()
    
    @classmethod
    def add_callback(cls, callback):
        cls._callbacks.append(callback)
    
    @classmethod
    def gradient_style(cls):
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {cls.get('PRIMARY')}, stop:1 {cls.get('PRIMARY_LIGHT')})"


# 简化访问
def T(key):
    return ThemeManager.get(key)


# ============== FontAwesome 图标常量 ==============
class FA:
    """FontAwesome 图标映射"""
    # 窗口控制
    CLOSE = ('fa5s.times', '✕')
    MINIMIZE = ('fa5s.minus', '─')
    SETTINGS = ('fa5s.cog', '⚙')
    THEME_LIGHT = ('fa5s.sun', '☀')
    THEME_DARK = ('fa5s.moon', '☾')
    
    # 操作按钮
    REFRESH = ('fa5s.sync-alt', '↻')
    SPEED_TEST = ('fa5s.bolt', '⚡')
    PLAY = ('fa5s.play', '▶')
    STOP = ('fa5s.stop', '■')
    
    # 设置章节图标
    PORT = ('fa5s.plug', '⚡')
    FILTER = ('fa5s.filter', '⊙')
    SORT = ('fa5s.sort-amount-down', '⊕')
    OPTIONS = ('fa5s.sliders-h', '⊛')
    
    @classmethod
    def icon(cls, fa_tuple, color=None, size=16):
        """获取 FontAwesome 图标"""
        if FA_AVAILABLE:
            fa_name, _ = fa_tuple
            icon_color = color or T('TEXT_SECONDARY')
            return qta.icon(fa_name, color=icon_color)
        return None
    
    @classmethod
    def text(cls, fa_tuple):
        """获取回退文本"""
        _, fallback = fa_tuple
        return fallback
    
    @classmethod
    def btn_text(cls, fa_tuple, label):
        """获取按钮文本（图标 + 文字）"""
        return f"{cls.text(fa_tuple)} {label}"

# ============== 异步工作线程 ==============
class AsyncWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self._coro_func = coro_func
        self._args = args
        self._kwargs = kwargs
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._coro_func(*self._args, **self._kwargs))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()


# ============== 自定义组件 ==============
class GlassCard(QFrame):
    """玻璃态卡片"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            #glassCard {{
                background: {T('BG_CARD')};
                border: 1px solid {T('BORDER')};
                border-radius: 10px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def refresh_style(self):
        self._apply_style()


class IconButton(QToolButton):
    """图标按钮 - 支持 FontAwesome 图标"""
    def __init__(self, fa_icon_tuple, tooltip="", parent=None):
        super().__init__(parent)
        self._fa_tuple = fa_icon_tuple
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self._update_icon()
        self._apply_style()
    
    def _update_icon(self):
        """更新图标"""
        icon = FA.icon(self._fa_tuple)
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))
            self.setText("")
        else:
            self.setText(FA.text(self._fa_tuple))
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                color: {T('TEXT_SECONDARY')};
            }}
            QToolButton:hover {{
                background: {T('BG_CARD_HOVER')};
                color: {T('PRIMARY')};
            }}
        """)
    
    def refresh_style(self):
        self._update_icon()
        self._apply_style()


class GradientButton(QPushButton):
    """渐变按钮"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {ThemeManager.gradient_style()};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {T('PRIMARY_DARK')}, stop:1 {T('PRIMARY')});
            }}
            QPushButton:disabled {{
                background: {T('BORDER')};
                color: {T('TEXT_MUTED')};
            }}
        """)
    
    def refresh_style(self):
        self._apply_style()


class ModernLineEdit(QLineEdit):
    """现代化输入框"""
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {T('BG_INPUT')};
                border: 2px solid {T('BORDER')};
                border-radius: 10px;
                padding: 10px 14px;
                color: {T('TEXT_PRIMARY')};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {T('PRIMARY')};
                background: {T('BG_CARD')};
            }}
        """)
    
    def refresh_style(self):
        self._apply_style()


class StatusIndicator(QWidget):
    """状态指示器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self.setFixedSize(10, 10)
    
    def set_running(self, running: bool):
        self._running = running
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(T('SUCCESS')) if self._running else QColor(T('DANGER'))
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 8, 8)


# ============== 设置对话框 ==============
class SettingsDialog(QDialog):
    saved = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 560)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None
        self._setup_ui()
    
    def _setup_ui(self):
        container = QFrame(self)
        container.setObjectName("settingsContainer")
        container.setGeometry(0, 0, 500, 560)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题栏
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(50)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 12, 0)
        
        title = QLabel(FA.text(FA.SETTINGS) + " 设置")
        title.setObjectName("dialogTitle")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        close_btn = IconButton(FA.CLOSE, "关闭")
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
        
        # 内容
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 20)
        content_layout.setSpacing(16)
        
        # 端口配置
        self._add_section(content_layout, "端口配置", FA.PORT)
        port_row = QHBoxLayout()
        
        start_lbl = QLabel("起始端口:")
        start_lbl.setStyleSheet(f"color: {T('TEXT_SECONDARY')};")
        port_row.addWidget(start_lbl)
        self.start_port = QSpinBox()
        self.start_port.setRange(1024, 65535)
        self.start_port.setValue(40000)
        self._style_spinbox(self.start_port)
        port_row.addWidget(self.start_port)
        
        port_row.addSpacing(20)
        
        count_lbl = QLabel("数量:")
        count_lbl.setStyleSheet(f"color: {T('TEXT_SECONDARY')};")
        port_row.addWidget(count_lbl)
        self.port_count = QSpinBox()
        self.port_count.setRange(1, 100)
        self.port_count.setValue(20)
        self._style_spinbox(self.port_count)
        port_row.addWidget(self.port_count)
        port_row.addStretch()
        
        content_layout.addLayout(port_row)
        
        # 排除关键词
        self._add_section(content_layout, "排除关键词", FA.FILTER)
        self.exclude_edit = QTextEdit()
        self.exclude_edit.setPlaceholderText("每行一个关键词")
        self.exclude_edit.setFixedHeight(80)
        self._style_textedit(self.exclude_edit)
        content_layout.addWidget(self.exclude_edit)
        
        # 地区优先级
        self._add_section(content_layout, "地区优先级", FA.SORT)
        self.priority_edit = QTextEdit()
        self.priority_edit.setPlaceholderText("每行一个地区，从上到下优先级递减")
        self.priority_edit.setFixedHeight(80)
        self._style_textedit(self.priority_edit)
        content_layout.addWidget(self.priority_edit)
        
        # 其他选项
        self._add_section(content_layout, "其他选项", FA.OPTIONS)
        self.sort_speed = QCheckBox("测速后自动按延迟排序")
        self._style_checkbox(self.sort_speed)
        content_layout.addWidget(self.sort_speed)
        
        refresh_row = QHBoxLayout()
        self.auto_refresh = QCheckBox("定时刷新订阅")
        self._style_checkbox(self.auto_refresh)
        refresh_row.addWidget(self.auto_refresh)
        self.refresh_min = QSpinBox()
        self.refresh_min.setRange(5, 1440)
        self.refresh_min.setValue(30)
        self.refresh_min.setSuffix(" 分钟")
        self._style_spinbox(self.refresh_min)
        refresh_row.addWidget(self.refresh_min)
        refresh_row.addStretch()
        content_layout.addLayout(refresh_row)
        
        # 开机自启
        self.auto_start = QCheckBox("开机自动启动")
        self._style_checkbox(self.auto_start)
        content_layout.addWidget(self.auto_start)
        
        # 最小化到托盘
        self.minimize_to_tray = QCheckBox("关闭时最小化到托盘")
        self._style_checkbox(self.minimize_to_tray)
        self.minimize_to_tray.setChecked(True)
        content_layout.addWidget(self.minimize_to_tray)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 按钮
        btn_bar = QFrame()
        btn_bar.setObjectName("btnBar")
        btn_bar.setFixedHeight(60)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(20, 10, 20, 10)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(90, 36)
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addSpacing(10)
        
        save_btn = GradientButton("保存")
        save_btn.setFixedSize(90, 36)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addWidget(btn_bar)
        self._apply_style()
    
    def _add_section(self, layout, title, fa_icon=None):
        section_widget = QWidget()
        section_layout = QHBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 8, 0, 0)
        section_layout.setSpacing(8)
        
        # 添加图标（如果有）
        if fa_icon:
            if FA_AVAILABLE:
                icon_label = QLabel()
                icon_label.setPixmap(FA.icon(fa_icon, color=T('PRIMARY')).pixmap(QSize(14, 14)))
                section_layout.addWidget(icon_label)
            else:
                # 回退到文字图标
                icon_label = QLabel(FA.text(fa_icon))
                icon_label.setStyleSheet(f"color: {T('PRIMARY')};")
                section_layout.addWidget(icon_label)
        
        label = QLabel(title)
        label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {T('TEXT_PRIMARY')};")
        section_layout.addWidget(label)
        section_layout.addStretch()
        
        layout.addWidget(section_widget)
    
    def _style_spinbox(self, spinbox):
        spinbox.setStyleSheet(f"""
            QSpinBox {{
                background: {T('BG_INPUT')};
                border: 1px solid {T('BORDER')};
                border-radius: 6px;
                padding: 6px 10px;
                color: {T('TEXT_PRIMARY')};
                min-width: 80px;
            }}
            QSpinBox:focus {{ border-color: {T('PRIMARY')}; }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {T('BG_CARD_HOVER')};
                border: none;
                border-radius: 3px;
                width: 16px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {T('PRIMARY')};
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid {T('TEXT_PRIMARY')};
                width: 0;
                height: 0;
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {T('TEXT_PRIMARY')};
                width: 0;
                height: 0;
            }}
        """)
    
    def _style_textedit(self, textedit):
        textedit.setStyleSheet(f"""
            QTextEdit {{
                background: {T('BG_INPUT')};
                border: 1px solid {T('BORDER')};
                border-radius: 8px;
                padding: 8px;
                color: {T('TEXT_PRIMARY')};
            }}
            QTextEdit:focus {{ border-color: {T('PRIMARY')}; }}
        """)
    
    def _style_checkbox(self, checkbox):
        checkbox.setStyleSheet(f"""
            QCheckBox {{ color: {T('TEXT_PRIMARY')}; spacing: 8px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border-radius: 4px;
                border: 2px solid {T('BORDER_LIGHT')};
                background: {T('BG_INPUT')};
            }}
            QCheckBox::indicator:hover {{
                border-color: {T('PRIMARY')};
            }}
            QCheckBox::indicator:checked {{
                background: {T('PRIMARY')};
                border: 2px solid {T('PRIMARY')};
            }}
        """)
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            #settingsContainer {{
                background: {T('BG_CARD')};
                border: 1px solid {T('BORDER')};
                border-radius: 10px;
            }}
            #titleBar {{
                background: {T('BG_INPUT')};
                border-bottom: 1px solid {T('BORDER')};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            #dialogTitle {{ font-size: 14px; font-weight: 600; color: {T('TEXT_PRIMARY')}; }}
            #settingsScroll {{ 
                background: transparent; 
                border: none; 
            }}
            #settingsScroll QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            #settingsScroll QScrollBar::handle:vertical {{
                background: {T('BORDER_LIGHT')};
                border-radius: 3px;
            }}
            #settingsScroll QScrollBar::add-line:vertical, 
            #settingsScroll QScrollBar::sub-line:vertical {{ height: 0; }}
            #btnBar {{
                background: {T('BG_INPUT')};
                border-top: 1px solid {T('BORDER')};
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }}
            #cancelBtn {{
                background: transparent;
                border: 1px solid {T('BORDER')};
                border-radius: 8px;
                color: {T('TEXT_SECONDARY')};
            }}
            #cancelBtn:hover {{ border-color: {T('PRIMARY')}; color: {T('PRIMARY')}; }}
            QWidget {{
                background: transparent;
            }}
            QLabel {{
                background: transparent;
                color: {T('TEXT_PRIMARY')};
            }}
        """)
        
        # 刷新子组件样式
        if hasattr(self, 'start_port'):
            self._style_spinbox(self.start_port)
            self._style_spinbox(self.port_count)
            self._style_spinbox(self.refresh_min)
            self._style_textedit(self.exclude_edit)
            self._style_textedit(self.priority_edit)
            self._style_checkbox(self.sort_speed)
            self._style_checkbox(self.auto_refresh)
            self._style_checkbox(self.auto_start)
            self._style_checkbox(self.minimize_to_tray)
    
    def _save(self):
        self.saved.emit(self.get_data())
        self.accept()
    
    def get_data(self):
        return {
            'start_port': self.start_port.value(),
            'port_count': self.port_count.value(),
            'exclude': [k.strip() for k in self.exclude_edit.toPlainText().split('\n') if k.strip()],
            'priority': [r.strip() for r in self.priority_edit.toPlainText().split('\n') if r.strip()],
            'sort_speed': self.sort_speed.isChecked(),
            'auto_refresh': self.auto_refresh.isChecked(),
            'refresh_min': self.refresh_min.value(),
            'auto_start': self.auto_start.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked()
        }
    
    def set_data(self, d):
        self.start_port.setValue(d.get('start_port', 40000))
        self.port_count.setValue(d.get('port_count', 20))
        self.exclude_edit.setPlainText('\n'.join(d.get('exclude', DEFAULT_EXCLUDE)))
        self.priority_edit.setPlainText('\n'.join(d.get('priority', [])))
        self.sort_speed.setChecked(d.get('sort_speed', False))
        self.auto_refresh.setChecked(d.get('auto_refresh', False))
        self.refresh_min.setValue(d.get('refresh_min', 30))
        self.auto_start.setChecked(d.get('auto_start', False))
        self.minimize_to_tray.setChecked(d.get('minimize_to_tray', True))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 50:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ============== 主窗口 ==============
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1050, 680)
        self.resize(1150, 720)
        
        # 无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 设置窗口圆角裁剪
        from PyQt6.QtGui import QRegion, QPainterPath
        from PyQt6.QtCore import QRectF
        
        self._drag_pos = None
        self._running = False
        self._nodes: List[Node] = []
        self._filtered: List[Node] = []
        self._workers: List[QThread] = []
        self._node_edits: Dict = {}
        self._table_updating = False
        
        # 延迟初始化组件
        self._subscription = None
        self._port_allocator = None
        self._config_gen = None
        self._filter_engine = None
        self._sort_engine = None
        self._speed_tester = None
        self._xray = None
        
        self.settings: Dict = {}
        self.settings_dlg = SettingsDialog(self)
        self.settings_dlg.saved.connect(self._on_settings_saved)
        
        # 主题切换回调
        ThemeManager.add_callback(self._on_theme_changed)
        
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        
        # 系统托盘
        self._setup_tray()
        
        self._setup_ui()
        self._apply_style()
        self._load_state()
    
    def _setup_tray(self):
        """设置系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 使用 tb.png 作为图标
        from PyQt6.QtGui import QPixmap
        import sys
        
        # 支持 PyInstaller 打包后的路径
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            base_path = Path(sys._MEIPASS)
        else:
            # 开发环境路径
            base_path = Path(__file__).parent
        
        icon_path = base_path / "tb.png"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # 回退到简单图标
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(T('PRIMARY')))
            self.tray_icon.setIcon(QIcon(pixmap))
        
        self.tray_icon.setToolTip(APP_NAME)
        
        # 托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def _show_from_tray(self):
        """从托盘显示窗口"""
        self.showNormal()
        self.activateWindow()
    
    def _on_tray_activated(self, reason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()
    
    def _quit_app(self):
        """真正退出应用"""
        self._save_state()
        if self._running:
            self.xray.stop()
        for w in self._workers:
            if w.isRunning():
                w.quit()
                w.wait(1000)
        QApplication.quit()
    
    # 延迟初始化
    @property
    def subscription(self):
        if not self._subscription:
            self._subscription = SubscriptionManager()
        return self._subscription
    
    @property
    def port_allocator(self):
        if not self._port_allocator:
            self._port_allocator = PortAllocator()
        return self._port_allocator
    
    @property
    def config_gen(self):
        if not self._config_gen:
            self._config_gen = ConfigGenerator()
        return self._config_gen
    
    @property
    def filter_engine(self):
        if not self._filter_engine:
            self._filter_engine = FilterEngine()
        return self._filter_engine
    
    @property
    def sort_engine(self):
        if not self._sort_engine:
            self._sort_engine = SortEngine()
        return self._sort_engine
    
    @property
    def speed_tester(self):
        if not self._speed_tester:
            self._speed_tester = SpeedTester()
        return self._speed_tester
    
    @property
    def xray(self):
        if not self._xray:
            self._xray = XrayService()
        return self._xray
    
    def _setup_ui(self):
        # 主容器
        main_container = QFrame()
        main_container.setObjectName("mainContainer")
        self.setCentralWidget(main_container)
        
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== 自定义标题栏 ==========
        title_bar = QFrame()
        title_bar.setObjectName("customTitleBar")
        title_bar.setFixedHeight(48)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 0, 8, 0)
        title_layout.setSpacing(12)
        
        # 应用名称
        app_title = QLabel(APP_NAME)
        app_title.setObjectName("appTitle")
        title_layout.addWidget(app_title)
        
        title_layout.addStretch()
        
        # 状态指示
        self.status_indicator = StatusIndicator()
        title_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        title_layout.addWidget(self.status_label)
        
        title_layout.addSpacing(16)
        
        # 日/夜模式切换
        self.theme_btn = IconButton(FA.THEME_LIGHT if ThemeManager.is_dark() else FA.THEME_DARK, "切换主题")
        self.theme_btn.clicked.connect(self._toggle_theme)
        title_layout.addWidget(self.theme_btn)
        
        # 设置按钮
        self.settings_btn = IconButton(FA.SETTINGS, "设置")
        self.settings_btn.clicked.connect(lambda: self.settings_dlg.exec())
        title_layout.addWidget(self.settings_btn)
        
        title_layout.addSpacing(8)
        
        # 窗口控制按钮
        self.min_btn = IconButton(FA.MINIMIZE, "最小化")
        self.min_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.min_btn)
        
        self.close_btn = IconButton(FA.CLOSE, "关闭")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.close_btn)
        
        main_layout.addWidget(title_bar)
        
        # ========== 内容区域 ==========
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(14)
        
        # 工具栏卡片
        toolbar_card = GlassCard()
        self.toolbar_card = toolbar_card
        toolbar_layout = QHBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(18, 14, 18, 14)
        toolbar_layout.setSpacing(14)
        
        # 订阅链接
        url_group = QVBoxLayout()
        url_group.setSpacing(5)
        url_label = QLabel("订阅链接")
        url_label.setObjectName("fieldLabel")
        url_group.addWidget(url_label)
        
        self.url_input = ModernLineEdit("请输入订阅地址...")
        self.url_input.returnPressed.connect(self._refresh)
        url_group.addWidget(self.url_input)
        toolbar_layout.addLayout(url_group, 1)
        
        # 分隔
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setObjectName("separator")
        toolbar_layout.addWidget(sep)
        
        # 按钮组
        btn_group = QVBoxLayout()
        btn_group.setSpacing(5)
        btn_label = QLabel("操作")
        btn_label.setObjectName("fieldLabel")
        btn_group.addWidget(btn_label)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.refresh_btn = GradientButton(FA.btn_text(FA.REFRESH, "刷新"))
        self.refresh_btn.setFixedHeight(38)
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_btn)
        
        self.test_btn = QPushButton(FA.btn_text(FA.SPEED_TEST, "测速"))
        self.test_btn.setObjectName("outlineBtn")
        self.test_btn.setFixedHeight(38)
        self.test_btn.clicked.connect(self._test_all)
        btn_row.addWidget(self.test_btn)
        
        self.toggle_btn = QPushButton(FA.btn_text(FA.PLAY, "启动"))
        self.toggle_btn.setObjectName("successBtn")
        self.toggle_btn.setFixedHeight(38)
        self.toggle_btn.clicked.connect(self._toggle)
        btn_row.addWidget(self.toggle_btn)
        
        btn_group.addLayout(btn_row)
        toolbar_layout.addLayout(btn_group)
        
        content_layout.addWidget(toolbar_card)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setObjectName("progressBar")
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        content_layout.addWidget(self.progress)
        
        # 表格卡片
        table_card = GlassCard()
        self.table_card = table_card
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        
        # 表格头部
        table_header = QFrame()
        table_header.setObjectName("tableHeader")
        table_header.setFixedHeight(46)
        header_layout = QHBoxLayout(table_header)
        header_layout.setContentsMargins(18, 0, 18, 0)
        
        list_title = QLabel("节点列表")
        list_title.setObjectName("listTitle")
        header_layout.addWidget(list_title)
        header_layout.addStretch()
        
        self.stats_label = QLabel("共 0 个节点")
        self.stats_label.setObjectName("statsLabel")
        header_layout.addWidget(self.stats_label)
        
        table_layout.addWidget(table_header)
        
        # 表格
        self.table = QTableWidget()
        self.table.setObjectName("nodeTable")
        self._setup_table()
        table_layout.addWidget(self.table)
        
        content_layout.addWidget(table_card, 1)
        main_layout.addWidget(content)
    
    def _setup_table(self):
        # 节点名称、地址、协议、延迟、本地端口
        cols = ["#", "节点名称", "地址", "协议", "延迟", "本地端口"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for i in [3, 4, 5]:
            h.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(0, 45)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 90)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        
        # 固定表头，防止滚动时表头移动
        h.setFixedHeight(40)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_menu)
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            #mainContainer {{
                background: {T('BG_DARK')};
                border-radius: 8px;
            }}
            #customTitleBar {{
                background: {T('BG_CARD')};
                border-bottom: 1px solid {T('BORDER')};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            #appTitle {{
                font-size: 14px;
                font-weight: 700;
                color: {T('TEXT_PRIMARY')};
            }}
            #statusLabel {{
                font-size: 12px;
                color: {T('TEXT_SECONDARY')};
            }}
            #closeBtn:hover {{
                background: {T('DANGER')};
                color: white;
            }}
            #contentArea {{
                background: {T('BG_DARK')};
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            #fieldLabel {{
                font-size: 11px;
                font-weight: 500;
                color: {T('TEXT_SECONDARY')};
            }}
            #separator {{
                background: {T('BORDER')};
            }}
            #outlineBtn {{
                background: transparent;
                border: 2px solid {T('BORDER')};
                border-radius: 10px;
                padding: 0 18px;
                color: {T('TEXT_PRIMARY')};
                font-size: 13px;
                font-weight: 500;
            }}
            #outlineBtn:hover {{
                border-color: {T('WARNING')};
                color: {T('WARNING')};
            }}
            #successBtn {{
                background: {T('SUCCESS')};
                border: none;
                border-radius: 10px;
                padding: 0 22px;
                color: white;
                font-size: 13px;
                font-weight: 600;
            }}
            #successBtn:hover {{
                background: {T('SUCCESS_LIGHT')};
            }}
            #progressBar {{
                background: {T('BORDER')};
                border: none;
                border-radius: 2px;
            }}
            #progressBar::chunk {{
                background: {ThemeManager.gradient_style()};
                border-radius: 2px;
            }}
            #tableHeader {{
                background: {T('BG_INPUT')};
                border-bottom: 1px solid {T('BORDER')};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            #listTitle {{
                font-size: 13px;
                font-weight: 600;
                color: {T('TEXT_PRIMARY')};
            }}
            #statsLabel {{
                font-size: 11px;
                color: {T('TEXT_MUTED')};
            }}
            #nodeTable {{
                background: {T('BG_CARD')};
                border: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                gridline-color: transparent;
            }}
            #nodeTable::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {T('BG_INPUT')};
                color: {T('TEXT_PRIMARY')};
            }}
            #nodeTable::item:selected {{
                background: rgba(102, 126, 234, 0.15);
            }}
            #nodeTable::item:alternate {{
                background: {T('BG_INPUT')};
            }}
            QHeaderView::section {{
                background: {T('BG_INPUT')};
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid {T('BORDER')};
                font-weight: 600;
                font-size: 11px;
                color: {T('TEXT_SECONDARY')};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: transparent;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        
        # 刷新组件样式
        if hasattr(self, 'toolbar_card'):
            self.toolbar_card.refresh_style()
            self.table_card.refresh_style()
            self.url_input.refresh_style()
            self.refresh_btn.refresh_style()
            self.theme_btn.refresh_style()
            self.settings_btn.refresh_style()
            self.min_btn.refresh_style()
            self.close_btn.refresh_style()
    
    def _toggle_theme(self):
        ThemeManager.toggle()
        # 暗色模式显示太阳(切换到亮色)，亮色模式显示月亮(切换到暗色)
        self.theme_btn._fa_tuple = FA.THEME_LIGHT if ThemeManager.is_dark() else FA.THEME_DARK
        self.theme_btn.refresh_style()
    
    def _on_theme_changed(self):
        self._apply_style()
        self.settings_dlg._apply_style()
    
    # ========== 窗口拖拽 ==========
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 48:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
    
    def resizeEvent(self, event):
        """重写 resizeEvent 以设置窗口圆角遮罩"""
        from PyQt6.QtGui import QPainterPath, QRegion
        from PyQt6.QtCore import QRectF
        
        path = QPainterPath()
        # 使用 8px 圆角
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
        super().resizeEvent(event)
    
    # ========== 业务逻辑 ==========
    def _load_state(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                self.settings = state.get('settings', {})
                if not self.settings.get('exclude'):
                    self.settings['exclude'] = DEFAULT_EXCLUDE
                
                # 恢复日夜模式
                saved_dark = state.get('dark_mode', True)
                if ThemeManager.is_dark() != saved_dark:
                    ThemeManager.toggle()
                    self.theme_btn._fa_tuple = FA.THEME_LIGHT if ThemeManager.is_dark() else FA.THEME_DARK
                    self.theme_btn.refresh_style()
                
                self.url_input.setText(state.get('url', ''))
                self._node_edits = state.get('node_edits', {})
                
                nodes_data = state.get('nodes', [])
                if nodes_data:
                    self._nodes = []
                    for nd in nodes_data:
                        node = Node(
                            protocol=nd.get('protocol', 'vless'),
                            address=nd.get('address', ''),
                            port=nd.get('port', 443),
                            uuid=nd.get('uuid', ''),
                            remark=nd.get('remark', ''),
                            # 网络和安全设置
                            network=nd.get('network', 'tcp'),
                            security=nd.get('security', ''),
                            sni=nd.get('sni', ''),
                            fingerprint=nd.get('fingerprint', ''),
                            alpn=nd.get('alpn', ''),
                            # WebSocket 设置
                            path=nd.get('path', ''),
                            host=nd.get('host', ''),
                            # gRPC 设置
                            service_name=nd.get('service_name', ''),
                            # Reality 设置
                            public_key=nd.get('public_key', ''),
                            short_id=nd.get('short_id', ''),
                            # VLESS flow
                            flow=nd.get('flow', ''),
                            # VMess 设置
                            alter_id=nd.get('alter_id', 0),
                            method=nd.get('method', ''),
                            # Shadowsocks/Trojan 密码
                            password=nd.get('password', '')
                        )
                        node.local_port = nd.get('local_port')
                        node.latency = nd.get('latency')
                        self._nodes.append(node)
                    self._apply_filter()
                
                if state.get('running') and self._filtered:
                    self._start_service()
                
                self._setup_auto_refresh()
            except Exception as e:
                print(f"Load state failed: {e}")
                self.settings = {'exclude': DEFAULT_EXCLUDE}
        else:
            self.settings = {'exclude': DEFAULT_EXCLUDE}
        
        self.settings_dlg.set_data(self.settings)
    
    def _save_state(self):
        nodes_data = [{
            'protocol': n.protocol, 'address': n.address, 'port': n.port,
            'uuid': n.uuid, 'remark': n.remark, 'local_port': n.local_port,
            'latency': n.latency,
            # 网络和安全设置
            'network': n.network, 'security': n.security, 'sni': n.sni,
            'fingerprint': n.fingerprint, 'alpn': n.alpn,
            # WebSocket 设置
            'path': n.path, 'host': n.host,
            # gRPC 设置
            'service_name': n.service_name,
            # Reality 设置
            'public_key': n.public_key, 'short_id': n.short_id,
            # VLESS flow
            'flow': n.flow,
            # VMess 设置
            'alter_id': n.alter_id, 'method': n.method,
            # Shadowsocks/Trojan 密码
            'password': n.password
        } for n in self._nodes]
        
        state = {
            'url': self.url_input.text().strip(),
            'settings': self.settings,
            'nodes': nodes_data,
            'node_edits': self._node_edits,
            'running': self._running,
            'dark_mode': ThemeManager.is_dark()  # 保存日夜模式
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Save state failed: {e}")
    
    def _setup_auto_refresh(self):
        if self.settings.get('auto_refresh'):
            interval = self.settings.get('refresh_min', 30) * 60 * 1000
            self._refresh_timer.start(interval)
        else:
            self._refresh_timer.stop()
    
    def _auto_refresh(self):
        if self.url_input.text().strip():
            self._refresh()
    
    def _on_settings_saved(self, data):
        self.settings = data
        self._save_state()
        self._setup_auto_refresh()
        if self._nodes:
            self._apply_filter()
    
    def _set_status(self, text: str, color: str = None):
        self.status_label.setText(text)
        c = color or T('TEXT_SECONDARY')
        self.status_label.setStyleSheet(f"font-size: 12px; color: {c};")
    
    def _refresh(self):
        url = self.url_input.text().strip()
        if not url:
            self._set_status("请输入订阅地址", T('WARNING'))
            return
        
        self.progress.setVisible(True)
        self.refresh_btn.setEnabled(False)
        self._set_status("正在获取...", T('INFO'))
        
        async def fetch():
            return await self.subscription.refresh(url)
        
        w = AsyncWorker(fetch)
        w.finished.connect(self._on_fetched)
        w.error.connect(self._on_fetch_error)
        self._workers.append(w)
        w.start()
    
    def _on_fetched(self, nodes):
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        if nodes:
            self._nodes = nodes
            self._apply_filter()
            self._set_status(f"获取到 {len(nodes)} 个节点", T('SUCCESS'))
            self._save_state()
    
    def _on_fetch_error(self, err):
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self._set_status(f"获取失败: {err[:15]}", T('DANGER'))
    
    def _apply_filter(self):
        keywords = self.settings.get('exclude', DEFAULT_EXCLUDE)
        self.filter_engine.set_keywords_list(keywords)
        self._filtered, _ = self.filter_engine.filter_nodes(self._nodes)
        
        priority = self.settings.get('priority', [])
        if priority:
            self.sort_engine.set_priority_list(priority)
            self._filtered = self.sort_engine.sort_by_region(self._filtered)
        
        start = self.settings.get('start_port', 40000)
        count = self.settings.get('port_count', 20)
        
        for node in self._filtered:
            key = f"{node.address}:{node.port}"
            if key in self._node_edits and 'local_port' in self._node_edits[key]:
                node.local_port = self._node_edits[key]['local_port']
            else:
                node.local_port = None
        
        port = start
        for node in self._filtered[:count]:
            if node.local_port is None:
                node.local_port = port
                port += 1
        
        self._refresh_table()
    
    def _refresh_table(self):
        if self._table_updating:
            return
        
        self._table_updating = True
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        
        try:
            self.table.setRowCount(len(self._filtered))
            
            for row, node in enumerate(self._filtered):
                key = f"{node.address}:{node.port}"
                name = self._node_edits.get(key, {}).get('name', node.remark)
                
                # 列顺序: #, 节点名称, 地址, 协议, 延迟, 本地端口
                self._set_item(row, 0, str(row + 1), True, False)
                self._set_item(row, 1, name, False, True)
                self._set_item(row, 2, node.address, False, False)
                self._set_item(row, 3, node.protocol.upper(), True, False)
                lat_item = self._set_item(row, 4, node.latency_display, True, False)
                self._color_latency(lat_item, node.latency)
                self._set_item(row, 5, str(node.local_port) if node.local_port else "-", True, True)
            
            allocated = len([n for n in self._filtered if n.local_port])
            self.stats_label.setText(f"共 {len(self._filtered)} 个节点 | 已分配 {allocated} 个端口")
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)
            self._table_updating = False
    
    def _set_item(self, row, col, text, center=False, editable=True):
        item = QTableWidgetItem(text)
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, col, item)
        return item
    
    def _color_latency(self, item, latency):
        if latency is None:
            item.setForeground(QColor(T('TEXT_MUTED')))
        elif latency == -1:
            item.setForeground(QColor(T('DANGER')))
        elif latency < 100:
            item.setForeground(QColor(T('SUCCESS')))
        elif latency < 300:
            item.setForeground(QColor(T('WARNING')))
        else:
            item.setForeground(QColor(T('DANGER')))
    
    def _on_item_changed(self, item):
        if self._table_updating:
            return
        row, col = item.row(), item.column()
        if row >= len(self._filtered):
            return
        
        node = self._filtered[row]
        key = f"{node.address}:{node.port}"
        
        if col == 1:  # 节点名称
            name = item.text().strip()
            if name:
                self._node_edits.setdefault(key, {})['name'] = name
                self._save_state()
        elif col == 5:  # 本地端口（新索引）
            try:
                port = int(item.text().strip())
                if 1024 <= port <= 65535:
                    node.local_port = port
                    self._node_edits.setdefault(key, {})['local_port'] = port
                    self._save_state()
            except:
                pass
    
    def _on_double_click(self, index):
        row, col = index.row(), index.column()
        if row >= len(self._filtered) or col in [1, 4]:
            return
        self._test_single(self._filtered[row])
    
    def _test_single(self, node):
        self._set_status(f"测试: {node.remark[:15]}...", T('INFO'))
        
        async def test():
            return await self.speed_tester.test_node(node)
        
        w = AsyncWorker(test)
        w.finished.connect(lambda lat: self._on_single_tested(node, lat))
        w.error.connect(lambda: self._set_status("测试失败", T('DANGER')))
        self._workers.append(w)
        w.start()
    
    def _on_single_tested(self, node, latency):
        node.latency = latency
        self._refresh_table()
        self._save_state()
        if latency == -1:
            self._set_status(f"{node.remark[:12]}... 超时", T('DANGER'))
        else:
            self._set_status(f"{node.remark[:12]}... {latency}ms", T('SUCCESS'))
    
    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {T('BG_CARD')}; border: 1px solid {T('BORDER')}; border-radius: 8px; padding: 6px; }}
            QMenu::item {{ padding: 8px 20px; border-radius: 4px; color: {T('TEXT_PRIMARY')}; }}
            QMenu::item:selected {{ background: {T('BG_INPUT')}; }}
        """)
        
        test_sel = QAction("测试选中节点", self)
        test_sel.triggered.connect(self._test_selected)
        menu.addAction(test_sel)
        
        test_all = QAction("测试所有节点", self)
        test_all.triggered.connect(self._test_all)
        menu.addAction(test_all)
        
        menu.exec(self.table.mapToGlobal(pos))
    
    def _test_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        nodes = [self._filtered[r] for r in rows if r < len(self._filtered)]
        if nodes:
            self._test_nodes(nodes)
    
    def _test_all(self):
        self._test_nodes(self._filtered)
    
    def _test_nodes(self, nodes):
        if not nodes:
            return
        
        self._set_status(f"测速中... 0/{len(nodes)}", T('INFO'))
        self.test_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        async def test():
            results = {}
            for node in nodes:
                lat = await self.speed_tester.test_node(node)
                results[f"{node.address}:{node.port}"] = lat
            return results
        
        w = AsyncWorker(test)
        w.finished.connect(self._on_tested)
        w.error.connect(lambda: self._on_test_error())
        self._workers.append(w)
        w.start()
    
    def _on_test_error(self):
        self.test_btn.setEnabled(True)
        self.progress.setVisible(False)
        self._set_status("测速失败", T('DANGER'))
    
    def _on_tested(self, results):
        self.test_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        for node in self._filtered:
            key = f"{node.address}:{node.port}"
            if key in results:
                node.latency = results[key]
        
        if self.settings.get('sort_speed'):
            self._filtered = self.sort_engine.sort_by_region_then_speed(self._filtered)
        
        self._refresh_table()
        self._save_state()
        self._set_status("测速完成", T('SUCCESS'))
    
    def _toggle(self):
        if self._running:
            self._stop_service()
        else:
            self._start_service()
    
    def _start_service(self):
        active = [n for n in self._filtered if n.local_port]
        if not active:
            self._set_status("没有可用节点", T('WARNING'))
            return
        
        config = self.config_gen.generate(active)
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        if self.xray.start("config.json"):
            self._running = True
            self.status_indicator.set_running(True)
            self.toggle_btn.setText(FA.btn_text(FA.STOP, "停止"))
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {T('DANGER')};
                    border: none; border-radius: 10px;
                    padding: 0 22px; color: white;
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton:hover {{ background: {T('DANGER_DARK')}; }}
            """)
            self._set_status(f"运行中 | {len(active)} 个节点", T('SUCCESS'))
            self._save_state()
        else:
            # 显示详细错误信息
            error_msg = self.xray.error_message if self.xray.error_message else "未知错误"
            self._set_status(f"启动失败: {error_msg}", T('DANGER'))
            print(f"启动失败: {error_msg}")
    
    def _stop_service(self):
        self.xray.stop()
        self._running = False
        self.status_indicator.set_running(False)
        self.toggle_btn.setText(FA.btn_text(FA.PLAY, "启动"))
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {T('SUCCESS')};
                border: none; border-radius: 10px;
                padding: 0 22px; color: white;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {T('SUCCESS_LIGHT')}; }}
        """)
        self._set_status("已停止", T('TEXT_SECONDARY'))
        self._save_state()
    
    def closeEvent(self, event):
        # 检查是否最小化到托盘
        if self.settings.get('minimize_to_tray', True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                APP_NAME, 
                "程序已最小化到系统托盘，双击图标可恢复窗口",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            # 真正关闭
            self._quit_app()
            event.accept()


# ============== 主入口 ==============
def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    win = MainWindow()
    win.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
