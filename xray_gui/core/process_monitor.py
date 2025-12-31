"""
进程监控器 - 监控系统进程状态
"""
import os
import psutil
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ProcessStatus(Enum):
    """进程状态枚举"""
    RUNNING = "running"
    SLEEPING = "sleeping"
    DISK_SLEEP = "disk-sleep"
    STOPPED = "stopped"
    TRACING_STOP = "tracing-stop"
    ZOMBIE = "zombie"
    DEAD = "dead"
    WAKE_KILL = "wake-kill"
    WAKING = "waking"
    IDLE = "idle"
    LOCKED = "locked"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    exe: str
    cmdline: List[str]
    status: ProcessStatus
    cpu_percent: float
    memory_percent: float
    create_time: float
    parent_pid: Optional[int] = None
    
    def is_alive(self) -> bool:
        """检查进程是否存活"""
        return self.status not in [ProcessStatus.ZOMBIE, ProcessStatus.DEAD]


class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_processes_by_name(self, name: str, exact_match: bool = False) -> List[ProcessInfo]:
        """
        根据进程名查找进程
        
        Args:
            name: 进程名
            exact_match: 是否精确匹配
            
        Returns:
            匹配的进程列表
        """
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'status', 
                                           'cpu_percent', 'memory_percent', 'create_time', 'ppid']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    
                    # 检查名称匹配
                    if exact_match:
                        if proc_name == name.lower():
                            processes.append(self._create_process_info(proc_info))
                    else:
                        if name.lower() in proc_name:
                            processes.append(self._create_process_info(proc_info))
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error finding processes by name '{name}': {e}")
        
        return processes
    
    def find_processes_by_exe(self, exe_path: str) -> List[ProcessInfo]:
        """
        根据可执行文件路径查找进程
        
        Args:
            exe_path: 可执行文件路径
            
        Returns:
            匹配的进程列表
        """
        processes = []
        exe_path = os.path.abspath(exe_path).lower()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'status', 
                                           'cpu_percent', 'memory_percent', 'create_time', 'ppid']):
                try:
                    proc_info = proc.info
                    proc_exe = proc_info.get('exe', '')
                    
                    if proc_exe and os.path.abspath(proc_exe).lower() == exe_path:
                        processes.append(self._create_process_info(proc_info))
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error finding processes by exe '{exe_path}': {e}")
        
        return processes
    
    def find_processes_by_cmdline(self, pattern: str) -> List[ProcessInfo]:
        """
        根据命令行参数查找进程
        
        Args:
            pattern: 命令行模式
            
        Returns:
            匹配的进程列表
        """
        processes = []
        pattern = pattern.lower()
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'status', 
                                           'cpu_percent', 'memory_percent', 'create_time', 'ppid']):
                try:
                    proc_info = proc.info
                    cmdline = proc_info.get('cmdline', [])
                    
                    if cmdline:
                        cmdline_str = ' '.join(cmdline).lower()
                        if pattern in cmdline_str:
                            processes.append(self._create_process_info(proc_info))
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error finding processes by cmdline '{pattern}': {e}")
        
        return processes
    
    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """
        获取指定PID的进程信息
        
        Args:
            pid: 进程ID
            
        Returns:
            进程信息，如果进程不存在返回None
        """
        try:
            proc = psutil.Process(pid)
            proc_info = proc.as_dict(['pid', 'name', 'exe', 'cmdline', 'status', 
                                    'cpu_percent', 'memory_percent', 'create_time', 'ppid'])
            return self._create_process_info(proc_info)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
        except Exception as e:
            self.logger.error(f"Error getting process info for PID {pid}: {e}")
            return None
    
    def is_process_running(self, pid: int) -> bool:
        """
        检查进程是否正在运行
        
        Args:
            pid: 进程ID
            
        Returns:
            进程是否正在运行
        """
        try:
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
        except Exception:
            return False
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """
        终止进程
        
        Args:
            pid: 进程ID
            force: 是否强制终止
            
        Returns:
            是否成功终止
        """
        try:
            proc = psutil.Process(pid)
            
            if force:
                proc.kill()
            else:
                proc.terminate()
            
            # 等待进程终止
            proc.wait(timeout=5)
            return True
            
        except psutil.TimeoutExpired:
            # 超时，尝试强制终止
            try:
                proc.kill()
                proc.wait(timeout=2)
                return True
            except Exception:
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return True  # 进程已经不存在
        except Exception as e:
            self.logger.error(f"Error killing process {pid}: {e}")
            return False
    
    def kill_processes_by_name(self, name: str, exact_match: bool = False, force: bool = False) -> int:
        """
        根据进程名终止进程
        
        Args:
            name: 进程名
            exact_match: 是否精确匹配
            force: 是否强制终止
            
        Returns:
            成功终止的进程数量
        """
        processes = self.find_processes_by_name(name, exact_match)
        killed_count = 0
        
        for proc_info in processes:
            if self.kill_process(proc_info.pid, force):
                killed_count += 1
                self.logger.info(f"Killed process {proc_info.name} (PID: {proc_info.pid})")
        
        return killed_count
    
    def kill_processes_by_exe(self, exe_path: str, force: bool = False) -> int:
        """
        根据可执行文件路径终止进程
        
        Args:
            exe_path: 可执行文件路径
            force: 是否强制终止
            
        Returns:
            成功终止的进程数量
        """
        processes = self.find_processes_by_exe(exe_path)
        killed_count = 0
        
        for proc_info in processes:
            if self.kill_process(proc_info.pid, force):
                killed_count += 1
                self.logger.info(f"Killed process {proc_info.name} (PID: {proc_info.pid})")
        
        return killed_count
    
    def _create_process_info(self, proc_info: Dict[str, Any]) -> ProcessInfo:
        """
        创建ProcessInfo对象
        
        Args:
            proc_info: psutil进程信息字典
            
        Returns:
            ProcessInfo对象
        """
        # 转换状态
        status = ProcessStatus.UNKNOWN
        proc_status = proc_info.get('status')
        if proc_status:
            # 基础状态映射（所有平台都支持）
            status_mapping = {
                psutil.STATUS_RUNNING: ProcessStatus.RUNNING,
                psutil.STATUS_SLEEPING: ProcessStatus.SLEEPING,
                psutil.STATUS_STOPPED: ProcessStatus.STOPPED,
                psutil.STATUS_ZOMBIE: ProcessStatus.ZOMBIE,
            }
            
            # 添加可选的状态常量（某些平台/版本可能不支持）
            optional_statuses = [
                ('STATUS_DISK_SLEEP', ProcessStatus.DISK_SLEEP),
                ('STATUS_TRACING_STOP', ProcessStatus.TRACING_STOP),
                ('STATUS_DEAD', ProcessStatus.DEAD),
                ('STATUS_IDLE', ProcessStatus.IDLE),
                ('STATUS_LOCKED', ProcessStatus.LOCKED),
                ('STATUS_WAITING', ProcessStatus.WAITING),
                ('STATUS_SUSPENDED', ProcessStatus.SUSPENDED),
                ('STATUS_WAKE_KILL', ProcessStatus.WAKE_KILL),
                ('STATUS_WAKING', ProcessStatus.WAKING),
            ]
            
            for attr_name, process_status in optional_statuses:
                if hasattr(psutil, attr_name):
                    status_mapping[getattr(psutil, attr_name)] = process_status
            
            status = status_mapping.get(proc_status, ProcessStatus.UNKNOWN)
        
        return ProcessInfo(
            pid=proc_info.get('pid', 0),
            name=proc_info.get('name', ''),
            exe=proc_info.get('exe', ''),
            cmdline=proc_info.get('cmdline', []),
            status=status,
            cpu_percent=proc_info.get('cpu_percent', 0.0),
            memory_percent=proc_info.get('memory_percent', 0.0),
            create_time=proc_info.get('create_time', 0.0),
            parent_pid=proc_info.get('ppid')
        )
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            系统信息字典
        """
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory()._asdict(),
                'disk': psutil.disk_usage('/')._asdict() if os.name != 'nt' else psutil.disk_usage('C:')._asdict(),
                'boot_time': psutil.boot_time(),
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {}


# 全局进程监控器实例
process_monitor = ProcessMonitor()