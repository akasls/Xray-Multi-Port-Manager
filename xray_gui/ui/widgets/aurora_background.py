"""
极光背景动画组件
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, QPointF, Qt
from PyQt6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, 
    QColor, QPainterPath, QBrush
)
import math


class AuroraBackground(QWidget):
    """极光背景动画组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # 动画参数
        self._angle = 0
        self._time = 0
        
        # 颜色配置
        self._colors = [
            QColor(120, 0, 255, 180),    # 紫色
            QColor(0, 212, 255, 180),    # 青色
            QColor(0, 255, 136, 180),    # 绿色
            QColor(255, 0, 128, 180),    # 粉色
            QColor(255, 165, 0, 180),    # 橙色
        ]
        
        # 动画定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(50)  # 20 FPS
    
    def _update_animation(self):
        """更新动画"""
        self._angle = (self._angle + 0.5) % 360
        self._time += 0.02
        self.update()
    
    def paintEvent(self, event):
        """绘制极光背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 绘制深色背景
        painter.fillRect(0, 0, width, height, QColor(15, 15, 30))
        
        # 绘制多层极光效果
        self._draw_aurora_layer(painter, width, height, 0)
        self._draw_aurora_layer(painter, width, height, 1)
        self._draw_aurora_layer(painter, width, height, 2)
        
        # 绘制星星效果
        self._draw_stars(painter, width, height)
        
        # 绘制边框圆角遮罩
        self._draw_border_mask(painter, width, height)
    
    def _draw_aurora_layer(self, painter, width, height, layer):
        """绘制单层极光"""
        # 计算动态位置
        offset = layer * 120
        phase = self._time + layer * 0.5
        
        # 创建渐变路径
        path = QPainterPath()
        
        # 波浪形状
        points = []
        for i in range(0, width + 50, 50):
            x = i
            y = height * 0.3 + math.sin(phase + i * 0.01) * 100 + layer * 50
            points.append(QPointF(x, y))
        
        if points:
            path.moveTo(0, height)
            path.lineTo(points[0])
            
            for i in range(1, len(points)):
                path.lineTo(points[i])
            
            path.lineTo(width, height)
            path.closeSubpath()
        
        # 创建渐变
        gradient = QLinearGradient(0, 0, width, 0)
        
        color_index = int(self._angle / 72) % len(self._colors)
        next_index = (color_index + 1) % len(self._colors)
        
        color1 = self._colors[(color_index + layer) % len(self._colors)]
        color2 = self._colors[(next_index + layer) % len(self._colors)]
        
        # 调整透明度
        color1.setAlpha(80 - layer * 20)
        color2.setAlpha(80 - layer * 20)
        
        gradient.setColorAt(0, color1)
        gradient.setColorAt(0.5, color2)
        gradient.setColorAt(1, color1)
        
        painter.fillPath(path, QBrush(gradient))
    
    def _draw_stars(self, painter, width, height):
        """绘制星星效果"""
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 固定的星星位置（基于时间闪烁）
        stars = [
            (0.1, 0.1), (0.3, 0.05), (0.5, 0.15), (0.7, 0.08), (0.9, 0.12),
            (0.15, 0.25), (0.4, 0.2), (0.6, 0.28), (0.85, 0.22),
            (0.2, 0.4), (0.45, 0.35), (0.75, 0.38),
        ]
        
        for i, (rx, ry) in enumerate(stars):
            x = int(rx * width)
            y = int(ry * height)
            
            # 闪烁效果
            alpha = int(100 + 100 * math.sin(self._time * 2 + i))
            size = 2 + math.sin(self._time * 3 + i) * 1
            
            color = QColor(255, 255, 255, alpha)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), size, size)
    
    def _draw_border_mask(self, painter, width, height):
        """绘制边框圆角"""
        # 创建圆角矩形路径
        radius = 12
        
        # 绘制四个角的遮罩
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 使用深色填充角落（模拟圆角效果）
        corner_color = QColor(15, 15, 30)
        painter.setBrush(QBrush(corner_color))
        
        # 左上角
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(radius, 0)
        path.arcTo(0, 0, radius * 2, radius * 2, 90, 90)
        path.closeSubpath()
        painter.fillPath(path, corner_color)
        
        # 右上角
        path = QPainterPath()
        path.moveTo(width, 0)
        path.lineTo(width - radius, 0)
        path.arcTo(width - radius * 2, 0, radius * 2, radius * 2, 90, -90)
        path.closeSubpath()
        painter.fillPath(path, corner_color)
        
        # 左下角
        path = QPainterPath()
        path.moveTo(0, height)
        path.lineTo(0, height - radius)
        path.arcTo(0, height - radius * 2, radius * 2, radius * 2, 180, 90)
        path.closeSubpath()
        painter.fillPath(path, corner_color)
        
        # 右下角
        path = QPainterPath()
        path.moveTo(width, height)
        path.lineTo(width, height - radius)
        path.arcTo(width - radius * 2, height - radius * 2, radius * 2, radius * 2, 0, -90)
        path.closeSubpath()
        painter.fillPath(path, corner_color)
