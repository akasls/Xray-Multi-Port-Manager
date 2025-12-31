"""
控制面板组件 - Xray 服务控制（增强版）
Feature: xray-protocol-enhancement, Requirements 4.1-4.6, 5.1-5.5
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QGraphicsDropShadowEffect,
    QProgressBar, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from ...core.ui_integration_manager import UIIntegrationManager, UIUpdateType, UIUpdateData
from ...core.port_allocator import PortAllocator, AllocationStrategy
from ...core.service_state_manager import ServiceStateManager


class ControlPanel(QFrame):
    """控制面板（增强版）"""
    
    # 信号
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    port_allocation_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("control_panel")
        
        self._is_running = False
        self._nodes_count = 0
        self._allocated_ports = 0
        
        # 初始化管理器
        self.ui_manager = UIIntegrationManager()
        self.port_allocator = PortAllocator()
        self.state_manager = ServiceStateManager()
        
        self._setup_ui()
        self._apply_styles()
        self._add_shadow()
        self._setup_ui_callbacks()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("☰ 服务控制")
        title.setObjectName("panel_title")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 状态显示
        self._create_status_section(layout)
        
        # 控制按钮
        self._create_control_buttons(layout)
        
        # 端口分配设置
        self._create_port_allocation_section(layout)
        
        # 运行信息
        self._create_info_section(layout)
        
        # 错误信息
        self.error_label = QLabel("")
        self.error_label.setObjectName("error_label")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        
        # 运行时间计时器
        self._start_time = None
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
    
    def _create_status_section(self, layout):
        """创建状态显示区域"""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(15)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("status_indicator")
        status_indicator_font = QFont("Segoe UI", 24)
        self.status_indicator.setFont(status_indicator_font)
        status_layout.addWidget(self.status_indicator)
        
        status_text_widget = QWidget()
        status_text_layout = QVBoxLayout(status_text_widget)
        status_text_layout.setContentsMargins(0, 0, 0, 0)
        status_text_layout.setSpacing(2)
        
        self.status_label = QLabel("已停止")
        self.status_label.setObjectName("status_label")
        status_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        self.status_label.setFont(status_font)
        status_text_layout.addWidget(self.status_label)
        
        self.status_detail = QLabel("Xray 服务未运行")
        self.status_detail.setObjectName("status_detail")
        status_text_layout.addWidget(self.status_detail)
        
        status_layout.addWidget(status_text_widget)
        status_layout.addStretch()
        
        layout.addWidget(status_widget)
    
    def _create_control_buttons(self, layout):
        """创建控制按钮"""
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(15)
        
        self.start_btn = QPushButton("▶ 启动")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.setFixedHeight(50)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedHeight(50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addWidget(btn_widget)
    
    def _create_port_allocation_section(self, layout):
        """创建端口分配设置区域"""
        port_group = QGroupBox("端口分配设置")
        port_group.setObjectName("port_group")
        port_group.setCheckable(True)
        port_group.setChecked(False)  # 默认折叠
        port_group.setFixedHeight(100)
        
        port_layout = QVBoxLayout(port_group)
        port_layout.setContentsMargins(15, 25, 15, 10)
        port_layout.setSpacing(8)
        
        # 端口分配策略选择
        strategy_layout = QHBoxLayout()
        strategy_layout.setSpacing(15)
        
        self.sequential_check = QCheckBox("顺序分配")
        self.sequential_check.setObjectName("strategy_check")
        self.sequential_check.setChecked(True)
        self.sequential_check.toggled.connect(self._update_allocation_strategy)
        strategy_layout.addWidget(self.sequential_check)
        
        self.random_check = QCheckBox("随机分配")
        self.random_check.setObjectName("strategy_check")
        self.random_check.toggled.connect(self._update_allocation_strategy)
        strategy_layout.addWidget(self.random_check)
        
        self.preserve_check = QCheckBox("保持现有端口")
        self.preserve_check.setObjectName("strategy_check")
        self.preserve_check.setChecked(True)
        strategy_layout.addWidget(self.preserve_check)
        
        strategy_layout.addStretch()
        
        # 重新分配按钮
        self.reallocate_btn = QPushButton("重新分配端口")
        self.reallocate_btn.setObjectName("reallocate_btn")
        self.reallocate_btn.setFixedHeight(28)
        self.reallocate_btn.clicked.connect(self._on_reallocate_ports)
        strategy_layout.addWidget(self.reallocate_btn)
        
        port_layout.addLayout(strategy_layout)
        
        layout.addWidget(port_group)
    
    def _create_info_section(self, layout):
        """创建信息显示区域"""
        info_widget = QWidget()
        info_widget.setObjectName("info_widget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setSpacing(8)
        
        self.node_count_label = QLabel("活动节点: 0")
        self.node_count_label.setObjectName("info_label")
        info_layout.addWidget(self.node_count_label)
        
        self.port_range_label = QLabel("端口范围: -")
        self.port_range_label.setObjectName("info_label")
        info_layout.addWidget(self.port_range_label)
        
        self.port_allocation_label = QLabel("端口分配: 0/0")
        self.port_allocation_label.setObjectName("info_label")
        info_layout.addWidget(self.port_allocation_label)
        
        self.uptime_label = QLabel("运行时间: -")
        self.uptime_label.setObjectName("info_label")
        info_layout.addWidget(self.uptime_label)
        
        # 服务状态同步进度条
        self.sync_progress = QProgressBar()
        self.sync_progress.setObjectName("sync_progress")
        self.sync_progress.setFixedHeight(4)
        self.sync_progress.setTextVisible(False)
        self.sync_progress.setVisible(False)
        info_layout.addWidget(self.sync_progress)
        
        layout.addWidget(info_widget)
    
    def _setup_ui_callbacks(self):
        """设置UI回调"""
        # 注册UI更新回调
        self.ui_manager.register_ui_callback(UIUpdateType.SERVICE_STATUS_UPDATE, self._on_service_status_update)
        self.ui_manager.register_ui_callback(UIUpdateType.PORT_ALLOCATION_UPDATE, self._on_port_allocation_update)
        self.ui_manager.register_ui_callback(UIUpdateType.NODE_LIST_REFRESH, self._on_node_list_update)
    
    def _update_allocation_strategy(self):
        """更新端口分配策略"""
        if self.sequential_check.isChecked():
            self.random_check.setChecked(False)
            strategy = AllocationStrategy.SEQUENTIAL
        elif self.random_check.isChecked():
            self.sequential_check.setChecked(False)
            strategy = AllocationStrategy.RANDOM
        else:
            self.sequential_check.setChecked(True)
            strategy = AllocationStrategy.SEQUENTIAL
        
        # 更新端口分配器策略
        self.port_allocator.set_strategy(strategy)
    
    def _on_reallocate_ports(self):
        """重新分配端口"""
        self.port_allocation_requested.emit()
    
    def _on_service_status_update(self, update_data: UIUpdateData):
        """服务状态更新回调"""
        data = update_data.data
        running = data.get('running', False)
        details = data.get('details', {})
        
        self.set_running(running)
        
        # 更新详细信息
        if details:
            process_id = details.get('process_id')
            if process_id:
                self.status_detail.setText(f"Xray 服务正在运行 (PID: {process_id})")
    
    def _on_port_allocation_update(self, update_data: UIUpdateData):
        """端口分配更新回调"""
        data = update_data.data
        allocations = data.get('allocations', {})
        total_ports = data.get('total_ports', 0)
        port_range = data.get('port_range', 'N/A')
        
        self._allocated_ports = total_ports
        self.port_allocation_label.setText(f"端口分配: {total_ports}/{self._nodes_count}")
        self.port_range_label.setText(f"端口范围: {port_range}")
    
    def _on_node_list_update(self, update_data: UIUpdateData):
        """节点列表更新回调"""
        data = update_data.data
        total_count = data.get('total_count', 0)
        
        self._nodes_count = total_count
        self.node_count_label.setText(f"活动节点: {total_count}")
        self.port_allocation_label.setText(f"端口分配: {self._allocated_ports}/{total_count}")
    
    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            #control_panel {
                background-color: rgba(30, 30, 50, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            
            #panel_title {
                color: rgba(255, 255, 255, 0.95);
            }
            
            #status_indicator {
                color: rgba(255, 100, 100, 0.9);
            }
            
            #status_label {
                color: rgba(255, 255, 255, 0.95);
            }
            
            #status_detail {
                color: rgba(255, 255, 255, 0.6);
            }
            
            #start_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 200, 100, 0.7),
                    stop:1 rgba(0, 150, 200, 0.7)
                );
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            
            #start_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 220, 120, 0.9),
                    stop:1 rgba(0, 170, 220, 0.9)
                );
            }
            
            #start_btn:disabled {
                background: rgba(100, 100, 100, 0.4);
            }
            
            #stop_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 100, 100, 0.7),
                    stop:1 rgba(200, 50, 100, 0.7)
                );
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            
            #stop_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 120, 120, 0.9),
                    stop:1 rgba(220, 70, 120, 0.9)
                );
            }
            
            #stop_btn:disabled {
                background: rgba(100, 100, 100, 0.4);
            }
            
            #port_group {
                background: rgba(40, 30, 60, 0.6);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 12px;
                color: rgba(180, 150, 220, 0.9);
                font-size: 12px;
                font-weight: bold;
            }
            
            #port_group::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
            
            #strategy_check {
                color: rgba(180, 150, 220, 0.9);
                font-size: 11px;
            }
            
            #strategy_check::indicator {
                width: 14px;
                height: 14px;
            }
            
            #strategy_check::indicator:unchecked {
                background: rgba(40, 30, 60, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.3);
                border-radius: 3px;
            }
            
            #strategy_check::indicator:checked {
                background: rgba(120, 0, 255, 0.8);
                border: 1px solid rgba(120, 0, 255, 0.6);
                border-radius: 3px;
            }
            
            #reallocate_btn {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 0, 200, 0.7),
                    stop:1 rgba(0, 150, 200, 0.7)
                );
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
            
            #reallocate_btn:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(120, 20, 220, 0.9),
                    stop:1 rgba(20, 170, 220, 0.9)
                );
            }
            
            #info_widget {
                background: rgba(40, 40, 60, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            
            #info_label {
                color: rgba(255, 255, 255, 0.7);
            }
            
            #sync_progress {
                background: rgba(40, 30, 60, 0.5);
                border: none;
                border-radius: 2px;
            }
            
            #sync_progress::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7800ff,
                    stop:1 #00d4ff
                );
                border-radius: 2px;
            }
            
            #error_label {
                color: rgba(255, 100, 100, 0.9);
                padding: 10px;
                background: rgba(255, 50, 50, 0.1);
                border-radius: 8px;
            }
        """)
    
    def _add_shadow(self):
        """添加阴影"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
    
    def _on_start(self):
        """启动按钮点击"""
        self.start_requested.emit()
    
    def _on_stop(self):
        """停止按钮点击"""
        self.stop_requested.emit()
    
    def set_running(self, running: bool):
        """设置运行状态"""
        self._is_running = running
        
        if running:
            self.status_indicator.setStyleSheet("color: rgba(100, 255, 150, 0.9);")
            self.status_label.setText("运行中")
            self.status_detail.setText("Xray 服务正在运行")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # 开始计时
            from datetime import datetime
            self._start_time = datetime.now()
            self._uptime_timer.start(1000)
        else:
            self.status_indicator.setStyleSheet("color: rgba(255, 100, 100, 0.9);")
            self.status_label.setText("已停止")
            self.status_detail.setText("Xray 服务未运行")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            # 停止计时
            self._uptime_timer.stop()
            self._start_time = None
            self.uptime_label.setText("运行时间: -")
    
    def _update_uptime(self):
        """更新运行时间"""
        if self._start_time:
            from datetime import datetime
            delta = datetime.now() - self._start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.uptime_label.setText(f"运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def set_node_count(self, count: int):
        """设置活动节点数"""
        self._nodes_count = count
        self.node_count_label.setText(f"活动节点: {count}")
        self.port_allocation_label.setText(f"端口分配: {self._allocated_ports}/{count}")
    
    def set_port_range(self, start: int, end: int):
        """设置端口范围"""
        self.port_range_label.setText(f"端口范围: {start} - {end}")
    
    def set_error(self, message: str):
        """设置错误信息"""
        if message:
            self.error_label.setText(f"❌ {message}")
            self.error_label.setVisible(True)
        else:
            self.error_label.setVisible(False)
    
    def is_running(self) -> bool:
        """获取运行状态"""
        return self._is_running
    
    def show_sync_progress(self, show: bool = True):
        """显示同步进度条"""
        self.sync_progress.setVisible(show)
        if show:
            self.sync_progress.setRange(0, 0)  # 无限进度条
    
    def cleanup(self):
        """清理资源"""
        self.ui_manager.cleanup()
        self._uptime_timer.stop()
