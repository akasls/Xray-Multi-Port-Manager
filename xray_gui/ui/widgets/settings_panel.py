"""
设置面板组件 - 弹出式设置对话框
"""
from PyQt6.QtWidgets import (
    QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QWidget, QSpinBox,
    QCheckBox, QGraphicsDropShadowEffect, QScrollArea,
    QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class SettingsSection(QFrame):
    """设置分组"""
    
    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("settings_section")
        
        self._title = title
        self._icon = icon
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        
        # 标题
        title_text = f"{self._icon} {self._title}" if self._icon else self._title
        title_label = QLabel(title_text)
        title_label.setObjectName("section_title")
        title_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        title_label.setFont(title_font)
        self.main_layout.addWidget(title_label)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 5, 0, 0)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #settings_section {
                background: rgba(30, 20, 50, 0.6);
                border: 1px solid rgba(120, 0, 255, 0.2);
                border-radius: 12px;
            }
            
            #section_title {
                color: rgba(200, 150, 255, 0.95);
            }
        """)
    
    def add_widget(self, widget: QWidget):
        """添加组件"""
        self.content_layout.addWidget(widget)
    
    def add_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        """添加一行设置"""
        row = QHBoxLayout()
        row.setSpacing(15)
        
        label_widget = QLabel(label)
        label_widget.setObjectName("field_label")
        label_widget.setFixedWidth(100)
        row.addWidget(label_widget)
        
        row.addWidget(widget, 1)
        
        self.content_layout.addLayout(row)
        return row


class SettingsDialog(QDialog):
    """设置对话框"""
    
    # 信号
    settings_saved = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(500, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._drag_pos = None
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """设置 UI"""
        # 主容器
        main_widget = QFrame(self)
        main_widget.setObjectName("settings_dialog")
        main_widget.setGeometry(0, 0, 500, 600)
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题栏
        title_bar = QFrame()
        title_bar.setObjectName("dialog_title_bar")
        title_bar.setFixedHeight(45)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 10, 0)
        
        title = QLabel("⚙ 设置")
        title.setObjectName("dialog_title")
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        title.setFont(title_font)
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setObjectName("dialog_close_btn")
        close_btn.setFixedSize(35, 28)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setObjectName("settings_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(15, 10, 15, 15)
        self.scroll_layout.setSpacing(12)
        
        # 端口设置
        self._create_port_section()
        
        # 过滤设置
        self._create_filter_section()
        
        # 排序设置
        self._create_sort_section()
        
        # 定时刷新设置
        self._create_refresh_section()
        
        # 其他设置
        self._create_other_section()
        
        self.scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # 底部按钮
        btn_widget = QFrame()
        btn_widget.setObjectName("btn_bar")
        btn_widget.setFixedHeight(55)
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(15, 10, 15, 10)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedSize(80, 35)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("✓ 保存")
        save_btn.setObjectName("save_btn")
        save_btn.setFixedSize(100, 35)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        layout.addWidget(btn_widget)
        
        # 添加阴影
        shadow = QGraphicsDropShadowEffect(main_widget)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        main_widget.setGraphicsEffect(shadow)
    
    def _create_port_section(self):
        """创建端口设置"""
        section = SettingsSection("端口配置", "⚙")
        
        # 起始端口
        self.start_port_spin = QSpinBox()
        self.start_port_spin.setObjectName("spin_box")
        self.start_port_spin.setRange(1024, 65535)
        self.start_port_spin.setValue(40000)
        section.add_row("起始端口", self.start_port_spin)
        
        # 端口数量
        self.port_count_spin = QSpinBox()
        self.port_count_spin.setObjectName("spin_box")
        self.port_count_spin.setRange(1, 100)
        self.port_count_spin.setValue(20)
        section.add_row("端口数量", self.port_count_spin)
        
        self.scroll_layout.addWidget(section)
    
    def _create_filter_section(self):
        """创建过滤设置"""
        section = SettingsSection("节点过滤", "▦")
        
        # 排除关键词
        self.exclude_keywords = QTextEdit()
        self.exclude_keywords.setObjectName("text_edit")
        self.exclude_keywords.setPlaceholderText("每行一个关键词")
        self.exclude_keywords.setFixedHeight(60)
        section.add_widget(QLabel("排除关键词"))
        section.add_widget(self.exclude_keywords)
        
        self.scroll_layout.addWidget(section)
    
    def _create_sort_section(self):
        """创建排序设置"""
        section = SettingsSection("节点排序", "↕")
        
        # 地区优先级
        self.region_priority = QTextEdit()
        self.region_priority.setObjectName("text_edit")
        self.region_priority.setPlaceholderText("每行一个地区")
        self.region_priority.setFixedHeight(60)
        section.add_widget(QLabel("地区优先级"))
        section.add_widget(self.region_priority)
        
        # 按速度排序
        self.sort_by_speed = QCheckBox("按延迟排序")
        self.sort_by_speed.setObjectName("check_box")
        section.add_widget(self.sort_by_speed)
        
        self.scroll_layout.addWidget(section)
    
    def _create_refresh_section(self):
        """创建定时刷新设置"""
        section = SettingsSection("定时刷新", "⏰")
        
        # 启用定时刷新
        self.auto_refresh = QCheckBox("启用定时刷新")
        self.auto_refresh.setObjectName("check_box")
        section.add_widget(self.auto_refresh)
        
        # 刷新间隔
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setObjectName("spin_box")
        self.refresh_interval.setRange(1, 1440)
        self.refresh_interval.setValue(30)
        self.refresh_interval.setSuffix(" 分钟")
        section.add_row("刷新间隔", self.refresh_interval)
        
        self.scroll_layout.addWidget(section)
    
    def _create_other_section(self):
        """创建其他设置"""
        section = SettingsSection("其他设置", "☰")
        
        # 开机自启
        self.auto_start = QCheckBox("开机自动启动")
        self.auto_start.setObjectName("check_box")
        section.add_widget(self.auto_start)
        
        # 最小化到托盘
        self.minimize_to_tray = QCheckBox("关闭时最小化到托盘")
        self.minimize_to_tray.setObjectName("check_box")
        self.minimize_to_tray.setChecked(True)
        section.add_widget(self.minimize_to_tray)
        
        self.scroll_layout.addWidget(section)
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #settings_dialog {
                background: rgba(20, 15, 40, 0.98);
                border: 1px solid rgba(120, 0, 255, 0.4);
                border-radius: 16px;
            }
            
            #dialog_title_bar {
                background: rgba(30, 20, 50, 0.9);
                border-bottom: 1px solid rgba(120, 0, 255, 0.3);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
            
            #dialog_title {
                color: rgba(255, 255, 255, 0.95);
            }
            
            #dialog_close_btn {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                font-size: 18px;
                border-radius: 4px;
            }
            
            #dialog_close_btn:hover {
                background: rgba(255, 80, 80, 0.8);
                color: white;
            }
            
            #settings_scroll {
                background: transparent;
                border: none;
            }
            
            #scroll_content {
                background: transparent;
            }
            
            #field_label {
                color: rgba(255, 255, 255, 0.7);
            }
            
            #spin_box {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                min-width: 120px;
            }
            
            #spin_box:focus {
                border: 1px solid rgba(120, 0, 255, 0.6);
            }
            
            #text_edit {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 8px;
                padding: 8px;
                color: white;
            }
            
            #text_edit:focus {
                border: 1px solid rgba(120, 0, 255, 0.6);
            }
            
            #check_box {
                color: rgba(255, 255, 255, 0.85);
                spacing: 8px;
            }
            
            #check_box::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 1px solid rgba(120, 0, 255, 0.4);
                background: rgba(40, 30, 60, 0.8);
            }
            
            #check_box::indicator:checked {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7800ff,
                    stop:1 #00d4ff
                );
                border: none;
            }
            
            #btn_bar {
                background: rgba(30, 20, 50, 0.9);
                border-top: 1px solid rgba(120, 0, 255, 0.3);
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }
            
            #cancel_btn {
                background: rgba(60, 50, 80, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
            }
            
            #cancel_btn:hover {
                background: rgba(80, 70, 100, 0.9);
            }
            
            #save_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(120, 0, 255, 0.8),
                    stop:1 rgba(0, 180, 255, 0.8)
                );
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            
            #save_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(140, 20, 255, 0.9),
                    stop:1 rgba(20, 200, 255, 0.9)
                );
            }
        """)
    
    def _on_save(self):
        """保存设置"""
        self.settings_saved.emit(self.get_settings())
        self.close()
    
    def get_settings(self) -> dict:
        """获取设置"""
        return {
            'start_port': self.start_port_spin.value(),
            'port_count': self.port_count_spin.value(),
            'exclude_keywords': [k.strip() for k in self.exclude_keywords.toPlainText().split('\n') if k.strip()],
            'region_priority': [r.strip() for r in self.region_priority.toPlainText().split('\n') if r.strip()],
            'sort_by_speed': self.sort_by_speed.isChecked(),
            'auto_refresh': self.auto_refresh.isChecked(),
            'refresh_interval': self.refresh_interval.value(),
            'auto_start': self.auto_start.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked()
        }
    
    def set_settings(self, settings: dict):
        """设置配置"""
        if 'start_port' in settings:
            self.start_port_spin.setValue(settings['start_port'])
        if 'port_count' in settings:
            self.port_count_spin.setValue(settings['port_count'])
        if 'exclude_keywords' in settings:
            self.exclude_keywords.setPlainText('\n'.join(settings['exclude_keywords']))
        if 'region_priority' in settings:
            self.region_priority.setPlainText('\n'.join(settings['region_priority']))
        if 'sort_by_speed' in settings:
            self.sort_by_speed.setChecked(settings['sort_by_speed'])
        if 'auto_refresh' in settings:
            self.auto_refresh.setChecked(settings['auto_refresh'])
        if 'refresh_interval' in settings:
            self.refresh_interval.setValue(settings['refresh_interval'])
        if 'auto_start' in settings:
            self.auto_start.setChecked(settings['auto_start'])
        if 'minimize_to_tray' in settings:
            self.minimize_to_tray.setChecked(settings['minimize_to_tray'])
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 45:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# 保持向后兼容
class SettingsPanel(SettingsDialog):
    """设置面板（兼容旧接口）"""
    apply_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_saved.connect(lambda _: self.apply_clicked.emit())
