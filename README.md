# oMLX - 项目索引

欢迎使用 oMLX！这是一个跨平台的本地 LLM 推理服务器。

## 📚 文档导航

### 🪟 Windows 用户

**开始使用：**
1. 📘 [完整文档](README.windows.md) - 详细安装、配置、故障排除
2. 🚀 [快速入门](QUICKSTART.windows.md) - 5 分钟上手指南
3. 📝 [重构总结](REFACTOR_SUMMARY.windows.md) - 技术架构说明

**快速命令：**
```batch
REM 安装
setup-windows.bat

REM 启动
omlx-windows.bat serve

REM 托盘应用
omlx-windows.bat tray

REM Windows 服务
omlx-windows.bat service install
```

### 🍎 macOS 用户

**开始使用：**
- 📘 [macOS 文档](README.md) - Apple Silicon 优化版本

**快速命令：**
```bash
# 安装
pip install -e .

# 启动
omlx serve --model-dir ~/models

# 菜单栏应用
open /Applications/oMLX.app
```

---

## 🎯 选择适合你的版本

### Windows 版本特点

✅ **多后端支持**
- DirectML (AMD/Intel GPU)
- CUDA (NVIDIA GPU)
- OpenVINO (Intel CPU/GPU)
- GGUF (llama.cpp CPU)

✅ **系统深度集成**
- Windows 系统托盘应用
- Windows 服务（开机自启）
- 原生性能优化

✅ **广泛的模型支持**
- GGUF 格式（量化模型）
- ONNX 格式（优化推理）
- Transformers 格式（HuggingFace）

### macOS 版本特点

✅ **Apple Silicon 优化**
- MLX 框架原生支持
- Metal GPU 加速
- 统一内存架构优化

✅ **分层缓存系统**
- 热缓存 (RAM)
- 冷缓存 (SSD)
- 前缀缓存复用

✅ **菜单栏集成**
- 原生 PyObjC 菜单栏
- 实时监控统计
- 自动更新

---

## 🚀 快速对比

| 特性 | Windows | macOS |
|------|---------|-------|
| **推理后端** | DirectML/CUDA/OpenVINO/GGUF | MLX/Metal |
| **模型格式** | GGUF/ONNX/Transformers | .safetensors (MLX) |
| **系统集成** | 托盘应用 + Windows 服务 | 菜单栏应用 |
| **内存管理** | 虚拟内存分页 | 统一内存 |
| **缓存系统** | 分页缓存 | 分层缓存 (热 + 冷) |
| **批处理** | 连续批处理 | 连续批处理 |
| **API 兼容** | OpenAI/Anthropic | OpenAI/Anthropic |

---

## 📦 核心文件说明

### Windows 特定文件

```
LLMomlx/
├── pyproject.windows.toml          # Windows 项目配置
├── README.windows.md                # Windows 完整文档
├── QUICKSTART.windows.md            # Windows 快速入门
├── REFACTOR_SUMMARY.windows.md      # 重构技术总结
├── omlx-windows.bat                 # Windows 启动脚本
├── setup-windows.bat                # Windows 安装脚本
├── omlx/
│   ├── platform/
│   │   └── __init__.py              # 平台抽象层
│   ├── utils/
│   │   └── hardware_windows.py      # Windows 硬件检测
│   ├── engine/
│   │   └── directml_engine.py       # DirectML 推理引擎
│   ├── tray_app.py                  # 系统托盘应用
│   └── integrations/
│       └── windows_service.py       # Windows 服务管理
```

### macOS 特定文件（原有）

```
LLMomlx/
├── pyproject.toml                   # macOS 项目配置
├── README.md                        # macOS 文档
├── packaging/                       # macOS 应用打包
├── Formula/                         # Homebrew 配方
└── omlx/
    ├── engine/
    │   ├── llm.py                   # MLX LLM 引擎
    │   └── vlm.py                   # MLX VLM 引擎
    └── utils/
        └── hardware.py              # macOS 硬件检测
```

---

## 🎓 学习路径

### 新手路径

1. **阅读快速入门** → [QUICKSTART.windows.md](QUICKSTART.windows.md)
2. **运行安装脚本** → `setup-windows.bat`
3. **启动托盘应用** → `omlx-windows.bat tray`
4. **下载模型** → 使用管理面板的下载器
5. **开始聊天** → 访问 http://localhost:8000/admin/chat

### 进阶路径

1. **理解架构** → [REFACTOR_SUMMARY.windows.md](REFACTOR_SUMMARY.windows.md)
2. **配置优化** → 阅读配置章节
3. **性能调优** → 查看性能优化建议
4. **API 集成** → 阅读 API 文档
5. **贡献代码** → 查看开发指南

---

## 🔧 常用命令参考

### 服务器管理

```batch
# 启动服务器
omlx-windows.bat serve

# 指定端口和后端
omlx-windows.bat serve --port 8080 --backend cuda

# 查看帮助
omlx-windows.bat help
```

### 系统托盘

```batch
# 启动托盘
omlx-windows.bat tray
```

### Windows 服务

```batch
# 安装服务
omlx-windows.bat service install

# 启动服务
omlx-windows.bat service start

# 停止服务
omlx-windows.bat service stop

# 查看状态
omlx-windows.bat service status

# 卸载服务
omlx-windows.bat service uninstall
```

### 维护命令

```batch
# 更新 oMLX
omlx-windows.bat update

# 清理临时文件
omlx-windows.bat clean

# 重新安装依赖
omlx-windows.bat install
```

---

## 📊 性能建议

### 根据内存配置

| 系统内存 | 推荐模型 | 上下文长度 | 批大小 |
|---------|---------|-----------|--------|
| **8GB** | Phi-3 Mini, Qwen2.5 7B Q4 | 2048 | 2 |
| **16GB** | Llama 3 8B Q4, Mistral 7B | 4096 | 4 |
| **32GB** | Llama 3 70B Q4, Mixtral 8x7B | 8192 | 8 |
| **64GB+** | 大型模型，多模型并发 | 16384+ | 16+ |

### 根据 GPU 配置

| GPU | 推荐后端 | 预期性能 |
|-----|---------|---------|
| **NVIDIA RTX 3060+** | CUDA | 40-60 t/s (8B 模型) |
| **AMD RX 6700 XT+** | DirectML | 25-35 t/s (8B 模型) |
| **Intel Arc A770** | DirectML/OpenVINO | 20-30 t/s (8B 模型) |
| **集成显卡** | GGUF CPU | 5-15 t/s (小模型) |

---

## 🆘 获取帮助

### 遇到问题？

1. **查看快速入门** → [QUICKSTART.windows.md](QUICKSTART.windows.md)
2. **查看故障排除** → [README.windows.md#故障排除](README.windows.md#故障排除)
3. **查看日志** → `explorer %USERPROFILE%\.omlx\logs`
4. **GitHub Issues** → https://github.com/jundot/omlx/issues

### 提供以下信息

- Windows 版本
- Python 版本 (`python --version`)
- GPU 型号
- 错误日志内容

---

## 🎉 开始使用

选择你的平台：

- 🪟 **Windows 用户** → [查看 Windows 文档](README.windows.md)
- 🍎 **macOS 用户** → [查看 macOS 文档](README.md)

祝你使用愉快！🚀

---

<p align="center">
  <b>oMLX - 让本地 LLM 推理更简单</b><br>
  跨平台 | 高性能 | 易用
</p>
