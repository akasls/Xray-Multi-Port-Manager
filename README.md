# Xray Multi-Port Manager

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/PyQt6-6.5+-green.svg" alt="PyQt6">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
  <b>高性能、美观的 Xray 多端口代理管理工具</b>
</p>

<p align="center">
  一键管理多个代理端口，支持订阅自动更新、节点测速、智能筛选排序
</p>

---

## 功能特性

- **订阅管理** - 支持主流机场订阅格式（Base64、明文）
- **多端口分配** - 自动为节点分配本地端口
- **节点测速** - 批量或单个测试节点延迟
- **智能筛选** - 按关键词排除无效节点
- **地区排序** - 自定义地区优先级
- **日/夜模式** - 支持深色和浅色主题切换
- **系统托盘** - 最小化到托盘后台运行
- **状态持久化** - 自动保存所有设置和运行状态

---

## 快速开始

### 方式一：从源码运行

```bash
# 克隆项目
git clone https://github.com/yourusername/xray-multi-port-manager.git
cd xray-multi-port-manager

# 安装依赖
pip install -r requirements.txt

# 运行程序
python xray_manager.py
```

### 方式二：使用启动脚本

直接双击 `启动GUI.bat` 即可运行。

### 运行前准备

将 [Xray-core](https://github.com/XTLS/Xray-core/releases) 的 `xray.exe` 放到程序目录。

---

## 打包成 EXE

```bash
# 安装打包工具
pip install pyinstaller

# 执行打包
build.bat
```

构建完成后，可执行文件位于 `dist/` 目录。

---

## 项目结构

```
xray-multi-port-manager/
├── xray_manager.py         # 主程序入口
├── xray_gui/               # GUI 核心模块
│   ├── core/               # 核心业务逻辑
│   │   ├── node.py             # 节点数据模型
│   │   ├── subscription.py     # 订阅管理器
│   │   ├── filter_engine.py    # 节点过滤引擎
│   │   ├── sort_engine.py      # 节点排序引擎
│   │   ├── speed_tester.py     # 节点测速器
│   │   ├── config_generator.py # Xray 配置生成
│   │   └── xray_service.py     # Xray 进程管理
│   └── ...
├── requirements.txt        # Python 依赖
├── build.bat               # 打包脚本
├── tb.png                  # 托盘图标
└── 启动GUI.bat             # 快速启动脚本
```

---

## 使用说明

### 代理配置

启动服务后，使用 SOCKS5 代理：`127.0.0.1:端口号`

端口号对应表格中的"本地端口"列。

### 快捷操作

| 操作 | 说明 |
|------|------|
| 双击节点 | 测试该节点延迟 |
| 右键菜单 | 测试选中/所有节点 |
| 编辑节点名 | 双击"节点名称"列 |
| 编辑端口 | 双击"本地端口"列 |
| 回车刷新 | 在输入框按 Enter |

---

## 许可证

[MIT License](LICENSE)

---

## 致谢

- [XTLS/Xray-core](https://github.com/XTLS/Xray-core)
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [qtawesome](https://github.com/spyder-ide/qtawesome)
