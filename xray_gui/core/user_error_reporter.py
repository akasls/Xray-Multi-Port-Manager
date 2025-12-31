"""
用户友好的错误报告器
Feature: xray-protocol-enhancement, Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""
import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Optional, Dict, Any
from datetime import datetime

from .error_handler import ErrorInfo, ErrorSeverity, ErrorCategory, global_error_handler


class UserErrorReporter:
    """用户错误报告器"""
    
    def __init__(self, parent_window: Optional[tk.Tk] = None):
        """
        初始化用户错误报告器
        
        Args:
            parent_window: 父窗口
        """
        self.parent_window = parent_window
        self._error_dialog = None
        
        # 注册错误回调
        for category in ErrorCategory:
            global_error_handler.register_error_callback(category, self._on_error_occurred)
    
    def show_error(self, error_info: ErrorInfo, show_details: bool = False):
        """
        显示错误信息
        
        Args:
            error_info: 错误信息
            show_details: 是否显示详细信息
        """
        if error_info.severity == ErrorSeverity.INFO:
            self._show_info_message(error_info)
        elif error_info.severity == ErrorSeverity.WARNING:
            self._show_warning_message(error_info, show_details)
        elif error_info.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            self._show_error_message(error_info, show_details)
    
    def show_error_dialog(self, error_info: ErrorInfo):
        """
        显示详细的错误对话框
        
        Args:
            error_info: 错误信息
        """
        if self._error_dialog and self._error_dialog.winfo_exists():
            self._error_dialog.destroy()
        
        self._error_dialog = tk.Toplevel(self.parent_window)
        self._error_dialog.title("错误详情")
        self._error_dialog.geometry("600x500")
        self._error_dialog.resizable(True, True)
        
        # 设置图标和样式
        try:
            if self.parent_window:
                self._error_dialog.iconbitmap(self.parent_window.iconbitmap())
        except:
            pass
        
        # 创建主框架
        main_frame = tk.Frame(self._error_dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 错误标题
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        severity_color = {
            ErrorSeverity.INFO: "#2196F3",
            ErrorSeverity.WARNING: "#FF9800",
            ErrorSeverity.ERROR: "#F44336",
            ErrorSeverity.CRITICAL: "#D32F2F"
        }.get(error_info.severity, "#F44336")
        
        title_label = tk.Label(
            title_frame,
            text=f"[{error_info.severity.value.upper()}] {error_info.message}",
            font=("Arial", 12, "bold"),
            fg=severity_color,
            wraplength=550,
            justify=tk.LEFT
        )
        title_label.pack(anchor=tk.W)
        
        # 基本信息
        info_frame = tk.LabelFrame(main_frame, text="基本信息", padx=10, pady=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = f"""错误代码: {error_info.code}
错误类别: {self._get_category_display_name(error_info.category)}
发生时间: {error_info.timestamp.strftime('%Y-%m-%d %H:%M:%S') if error_info.timestamp else 'N/A'}"""
        
        info_label = tk.Label(info_frame, text=info_text, justify=tk.LEFT, anchor=tk.W)
        info_label.pack(fill=tk.X)
        
        # 详细信息
        if error_info.details:
            details_frame = tk.LabelFrame(main_frame, text="详细信息", padx=10, pady=10)
            details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            details_text = scrolledtext.ScrolledText(
                details_frame,
                height=8,
                wrap=tk.WORD,
                font=("Consolas", 9)
            )
            details_text.pack(fill=tk.BOTH, expand=True)
            details_text.insert(tk.END, error_info.details)
            details_text.config(state=tk.DISABLED)
        
        # 建议解决方案
        if error_info.suggestions:
            suggestions_frame = tk.LabelFrame(main_frame, text="建议解决方案", padx=10, pady=10)
            suggestions_frame.pack(fill=tk.X, pady=(0, 10))
            
            for i, suggestion in enumerate(error_info.suggestions, 1):
                suggestion_label = tk.Label(
                    suggestions_frame,
                    text=f"{i}. {suggestion}",
                    justify=tk.LEFT,
                    anchor=tk.W,
                    wraplength=550
                )
                suggestion_label.pack(fill=tk.X, pady=2)
        
        # 上下文信息
        if error_info.context:
            context_frame = tk.LabelFrame(main_frame, text="上下文信息", padx=10, pady=10)
            context_frame.pack(fill=tk.X, pady=(0, 10))
            
            context_text = scrolledtext.ScrolledText(
                context_frame,
                height=4,
                wrap=tk.WORD,
                font=("Consolas", 9)
            )
            context_text.pack(fill=tk.BOTH, expand=True)
            
            context_str = "\n".join([f"{k}: {v}" for k, v in error_info.context.items()])
            context_text.insert(tk.END, context_str)
            context_text.config(state=tk.DISABLED)
        
        # 按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 复制错误信息按钮
        copy_button = tk.Button(
            button_frame,
            text="复制错误信息",
            command=lambda: self._copy_error_info(error_info)
        )
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 查看错误历史按钮
        history_button = tk.Button(
            button_frame,
            text="查看错误历史",
            command=self._show_error_history
        )
        history_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 关闭按钮
        close_button = tk.Button(
            button_frame,
            text="关闭",
            command=self._error_dialog.destroy
        )
        close_button.pack(side=tk.RIGHT)
        
        # 居中显示
        self._center_window(self._error_dialog)
        
        # 设置焦点
        self._error_dialog.focus_set()
        self._error_dialog.grab_set()
    
    def show_error_history(self):
        """显示错误历史记录"""
        self._show_error_history()
    
    def _on_error_occurred(self, error_info: ErrorInfo):
        """错误发生时的回调函数"""
        # 只对严重错误显示弹窗
        if error_info.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            # 在主线程中显示错误
            if self.parent_window:
                self.parent_window.after(0, lambda: self.show_error(error_info, show_details=True))
    
    def _show_info_message(self, error_info: ErrorInfo):
        """显示信息消息"""
        messagebox.showinfo(
            "信息",
            error_info.to_user_message(),
            parent=self.parent_window
        )
    
    def _show_warning_message(self, error_info: ErrorInfo, show_details: bool = False):
        """显示警告消息"""
        if show_details:
            self.show_error_dialog(error_info)
        else:
            result = messagebox.showwarning(
                "警告",
                f"{error_info.message}\n\n点击'确定'查看详细信息",
                parent=self.parent_window
            )
            if result == 'ok':
                self.show_error_dialog(error_info)
    
    def _show_error_message(self, error_info: ErrorInfo, show_details: bool = False):
        """显示错误消息"""
        if show_details:
            self.show_error_dialog(error_info)
        else:
            result = messagebox.showerror(
                "错误",
                f"{error_info.message}\n\n点击'确定'查看详细信息和解决建议",
                parent=self.parent_window
            )
            if result == 'ok':
                self.show_error_dialog(error_info)
    
    def _show_error_history(self):
        """显示错误历史记录窗口"""
        history_window = tk.Toplevel(self.parent_window)
        history_window.title("错误历史记录")
        history_window.geometry("800x600")
        history_window.resizable(True, True)
        
        # 创建主框架
        main_frame = tk.Frame(history_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            main_frame,
            text="错误历史记录",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 统计信息
        stats = global_error_handler.get_error_statistics()
        stats_text = f"总错误数: {stats['total_errors']} | 最近1小时: {stats['recent_errors']}"
        stats_label = tk.Label(main_frame, text=stats_text, font=("Arial", 10))
        stats_label.pack(pady=(0, 10))
        
        # 错误列表框架
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview显示错误列表
        import tkinter.ttk as ttk
        
        columns = ("时间", "类别", "严重程度", "代码", "消息")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        # 设置消息列更宽
        tree.column("消息", width=300)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充错误数据
        errors = global_error_handler.get_error_history(limit=100)
        for error in reversed(errors):  # 最新的在前面
            tree.insert("", tk.END, values=(
                error.timestamp.strftime('%H:%M:%S') if error.timestamp else 'N/A',
                self._get_category_display_name(error.category),
                error.severity.value.upper(),
                error.code,
                error.message[:50] + "..." if len(error.message) > 50 else error.message
            ), tags=(error.severity.value,))
        
        # 设置行颜色
        tree.tag_configure("info", background="#E3F2FD")
        tree.tag_configure("warning", background="#FFF3E0")
        tree.tag_configure("error", background="#FFEBEE")
        tree.tag_configure("critical", background="#FFCDD2")
        
        # 双击查看详情
        def on_item_double_click(event):
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                error_code = item['values'][3]
                # 查找对应的错误信息
                for error in errors:
                    if error.code == error_code:
                        self.show_error_dialog(error)
                        break
        
        tree.bind("<Double-1>", on_item_double_click)
        
        # 按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 清空历史按钮
        clear_button = tk.Button(
            button_frame,
            text="清空历史",
            command=lambda: self._clear_error_history(history_window)
        )
        clear_button.pack(side=tk.LEFT)
        
        # 导出按钮
        export_button = tk.Button(
            button_frame,
            text="导出日志",
            command=self._export_error_log
        )
        export_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # 关闭按钮
        close_button = tk.Button(
            button_frame,
            text="关闭",
            command=history_window.destroy
        )
        close_button.pack(side=tk.RIGHT)
        
        # 居中显示
        self._center_window(history_window)
    
    def _copy_error_info(self, error_info: ErrorInfo):
        """复制错误信息到剪贴板"""
        try:
            import pyperclip
            error_text = f"""错误信息:
代码: {error_info.code}
类别: {self._get_category_display_name(error_info.category)}
严重程度: {error_info.severity.value.upper()}
消息: {error_info.message}
时间: {error_info.timestamp.strftime('%Y-%m-%d %H:%M:%S') if error_info.timestamp else 'N/A'}

详细信息:
{error_info.details or 'N/A'}

建议解决方案:
{chr(10).join([f"{i}. {s}" for i, s in enumerate(error_info.suggestions or [], 1)]) or 'N/A'}

上下文信息:
{chr(10).join([f"{k}: {v}" for k, v in (error_info.context or {}).items()]) or 'N/A'}"""
            
            pyperclip.copy(error_text)
            messagebox.showinfo("成功", "错误信息已复制到剪贴板", parent=self._error_dialog)
        except ImportError:
            # 如果没有pyperclip，使用tkinter的剪贴板
            self._error_dialog.clipboard_clear()
            self._error_dialog.clipboard_append(error_info.to_user_message())
            messagebox.showinfo("成功", "错误信息已复制到剪贴板", parent=self._error_dialog)
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {e}", parent=self._error_dialog)
    
    def _clear_error_history(self, parent_window):
        """清空错误历史"""
        result = messagebox.askyesno(
            "确认",
            "确定要清空所有错误历史记录吗？",
            parent=parent_window
        )
        if result:
            global_error_handler.clear_error_history()
            messagebox.showinfo("成功", "错误历史记录已清空", parent=parent_window)
            parent_window.destroy()
    
    def _export_error_log(self):
        """导出错误日志"""
        try:
            from tkinter import filedialog
            import json
            
            filename = filedialog.asksaveasfilename(
                title="导出错误日志",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
                parent=self.parent_window
            )
            
            if filename:
                errors = global_error_handler.get_error_history()
                
                if filename.endswith('.json'):
                    # 导出为JSON格式
                    export_data = {
                        'export_time': datetime.now().isoformat(),
                        'total_errors': len(errors),
                        'errors': [error.to_dict() for error in errors]
                    }
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    # 导出为文本格式
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"错误日志导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"总错误数: {len(errors)}\n")
                        f.write("=" * 80 + "\n\n")
                        
                        for error in errors:
                            f.write(f"[{error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ")
                            f.write(f"[{error.severity.value.upper()}] ")
                            f.write(f"[{self._get_category_display_name(error.category)}] ")
                            f.write(f"{error.code}: {error.message}\n")
                            
                            if error.details:
                                f.write(f"详细信息: {error.details}\n")
                            
                            if error.suggestions:
                                f.write("建议解决方案:\n")
                                for i, suggestion in enumerate(error.suggestions, 1):
                                    f.write(f"  {i}. {suggestion}\n")
                            
                            f.write("-" * 80 + "\n\n")
                
                messagebox.showinfo("成功", f"错误日志已导出到: {filename}", parent=self.parent_window)
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}", parent=self.parent_window)
    
    def _get_category_display_name(self, category: ErrorCategory) -> str:
        """获取错误类别的显示名称"""
        display_names = {
            ErrorCategory.PROTOCOL_PARSING: "协议解析",
            ErrorCategory.XRAY_SERVICE: "Xray服务",
            ErrorCategory.LATENCY_TEST: "延迟测试",
            ErrorCategory.STARTUP_MANAGEMENT: "自启动管理",
            ErrorCategory.PORT_ALLOCATION: "端口分配",
            ErrorCategory.CONFIG_PERSISTENCE: "配置持久化",
            ErrorCategory.NETWORK_CONNECTION: "网络连接",
            ErrorCategory.SYSTEM_PERMISSION: "系统权限",
            ErrorCategory.FILE_OPERATION: "文件操作",
            ErrorCategory.UNKNOWN: "未知"
        }
        return display_names.get(category, category.value)
    
    def _center_window(self, window):
        """居中显示窗口"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")


# 全局用户错误报告器实例
global_user_error_reporter = None


def initialize_user_error_reporter(parent_window: Optional[tk.Tk] = None):
    """初始化全局用户错误报告器"""
    global global_user_error_reporter
    global_user_error_reporter = UserErrorReporter(parent_window)
    return global_user_error_reporter


def show_user_error(error_info: ErrorInfo, show_details: bool = False):
    """显示用户错误"""
    if global_user_error_reporter:
        global_user_error_reporter.show_error(error_info, show_details)


def show_user_error_dialog(error_info: ErrorInfo):
    """显示用户错误对话框"""
    if global_user_error_reporter:
        global_user_error_reporter.show_error_dialog(error_info)