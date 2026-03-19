# oMLX for Windows

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/icon-rounded-dark.svg" width="140">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/icon-rounded-light.svg" width="140">
    <img alt="oMLX" src="docs/images/icon-rounded-light.svg" width="140">
  </picture>
</p>

<h1 align="center">oMLX Windows</h1>
<p align="center"><b>LLM 推理，为 Windows 优化</b><br>DirectML 加速，系统托盘管理，Windows 服务集成。</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-black?logo=windows" alt="Windows">
</p>

<p align="center">
  <a href="#installation">安装</a> ·
  <a href="#quick-start">快速开始</a> ·
  <a href="#features">功能</a> ·
  <a href="#models">模型</a> ·
  <a href="#cli-configuration">CLI 配置</a> ·
  <a href="#windows-service">Windows 服务</a>
</p>

---

## 简介

oMLX Windows 版本是一个专为 Windows 系统优化的 LLM 推理服务器，支持：

- **DirectML** - AMD/Intel GPU 加速
- **CUDA** - NVIDIA GPU 加速  
- **OpenVINO** - Intel 硬件加速
- **GGUF** - llama.cpp 后端，兼容广泛模型

## 安装

### 方法 1: pip 安装（推荐）

```bash
# 创建虚拟环境（推荐）
python -m venv omlx-env
omlx-env\Scripts\activate

# 安装 oMLX Windows
pip install omlx-windows
```

### 方法 2: 从源码安装

```bash
git clone https://github.com/jundot/omlx.git
cd omlx

# 安装 Windows 版本
pip install -e . -f pyproject.windows.toml
```

### 依赖说明

安装会自动包含以下核心依赖：

- `onnxruntime-directml` - DirectML 推理引擎
- `llama-cpp-python` - GGUF 模型支持
- `transformers` - Hugging Face 模型支持
- `pywin32` - Windows API 集成
- `pystray` - 系统托盘支持

## 快速开始

### 1. 启动服务器

```bash
# 启动默认服务器（端口 8000）
omlx serve --model-dir C:\models

# 指定端口和主机
omlx serve --model-dir C:\models --port 8080 --host 0.0.0.0

# 使用特定后端
omlx serve --model-dir C:\models --backend directml
```

### 2. 使用系统托盘应用

```bash
# 启动系统托盘应用（推荐）
omlx-tray

# 托盘功能：
# - 启动/停止服务器
# - 查看服务器状态
# - 打开管理面板
# - 查看日志
# - 访问模型目录
```

### 3. 安装为 Windows 服务

```bash
# 安装服务（开机自启动）
omlx service install --model-dir C:\models

# 安装服务（手动启动）
omlx service install --model-dir C:\models --no-auto-start

# 使用 NSSM（备选方案）
omlx service install --model-dir C:\models --nssm

# 管理服务
omlx service start      # 启动服务
omlx service stop       # 停止服务
omlx service status     # 查看状态
omlx service uninstall  # 卸载服务
```

### 4. 访问管理面板

服务器启动后，访问：

- **管理面板**: http://localhost:8000/admin
- **API 端点**: http://localhost:8000/v1
- **健康检查**: http://localhost:8000/health

## 功能

### 🚀 多后端支持

| 后端 | GPU | 说明 |
|------|-----|------|
| **DirectML** | AMD/Intel | Windows 原生 GPU 加速 |
| **CUDA** | NVIDIA | NVIDIA GPU 加速 |
| **OpenVINO** | Intel | Intel CPU/GPU 优化 |
| **GGUF** | CPU/GPU | llama.cpp 量化模型 |

### 💻 系统集成

- **系统托盘应用** - 便捷管理服务器
- **Windows 服务** - 开机自启动，后台运行
- **自动更新** - 版本检测和升级

### 🎯 优化特性

- **连续批处理** - 提高吞吐量
- **分页缓存** - 优化内存使用
- **量化支持** - INT4/INT8 量化
- **多模型管理** - LRU 驱逐策略

### 🛠️ 管理功能

- **Web 管理面板** - 模型管理、监控、基准测试
- **日志系统** - 结构化日志，可配置保留
- **性能监控** - 实时统计和指标

## 模型支持

### 支持的模型格式

1. **ONNX 格式**
   ```
   C:\models\
   └── llama-3-8b-onnx\
       ├── model.onnx
       ├── config.json
       └── tokenizer.json
   ```

2. **GGUF 格式**（推荐）
   ```
   C:\models\
   └── llama-3-8b.Q4_K_M.gguf
   ```

3. **Transformers 格式**
   ```
   C:\models\
   └── meta-llama-3-8b\
       ├── config.json
       ├── pytorch_model.bin
       └── tokenizer.json
   ```

### 推荐模型

| 模型 | 格式 | 大小 | 说明 |
|------|------|------|------|
| Llama 3 8B | GGUF Q4 | 4.9GB | 平衡性能和速度 |
| Llama 3 70B | GGUF Q4 | 40GB | 高质量推理 |
| Qwen2.5 7B | GGUF Q4 | 4.2GB | 中文优化 |
| Phi-3 Mini | GGUF Q4 | 2.3GB | 轻量级 |
| Mistral 7B | GGUF Q4 | 4.1GB | 高性能 |

### 下载模型

使用内置下载器：

```bash
# 通过管理面板下载
# 访问 http://localhost:8000/admin/downloader

# 或手动下载
huggingface-cli download TheBloke/Llama-2-7B-Chat-GGUF llama-2-7b-chat.Q4_K_M.gguf --local-dir C:\models
```

## CLI 配置

### 服务器选项

```bash
omlx serve [选项]

# 模型配置
--model-dir PATH          模型目录（默认：%USERPROFILE%\.omlx\models）
--backend NAME            后端：auto/cuda/directml/openvino/gguf（默认：auto）

# 性能选项
--max-context-length INT  最大上下文长度（默认：4096）
--max-batch-size INT      最大批大小（默认：8）
--num-threads INT         CPU 线程数（0=自动）

# 服务器配置
--host TEXT               绑定主机（默认：127.0.0.1）
--port INT                绑定端口（默认：8000）
--api-key TEXT            API 密钥（可选）

# 缓存选项
--enable-cache            启用 KV 缓存（默认：启用）
--cache-size GB           缓存大小（默认：自动）

# 日志选项
--log-level LEVEL         日志级别：trace/debug/info/warning/error（默认：info）
--log-dir PATH            日志目录（默认：%USERPROFILE%\.omlx\logs）
```

### 示例配置

```bash
# 高性能配置（16GB+ RAM）
omlx serve ^
  --model-dir C:\models ^
  --backend cuda ^
  --max-context-length 8192 ^
  --max-batch-size 16 ^
  --enable-cache ^
  --cache-size 8GB

# 低内存配置（8GB RAM）
omlx serve ^
  --model-dir C:\models ^
  --backend directml ^
  --max-context-length 2048 ^
  --max-batch-size 2 ^
  --num-threads 4
```

## Windows 服务

### 服务管理

```bash
# 安装服务
omlx service install --model-dir C:\models

# 服务配置选项
--model-dir PATH          模型目录
--port INT                服务器端口（默认：8000）
--host TEXT               服务器主机（默认：127.0.0.1）
--no-auto-start          禁用开机自启动
--nssm                   使用 NSSM 而非 pywin32
```

### 服务状态

```bash
# 查看服务状态
omlx service status

# 输出示例：
# Service: oMLX
# Installed: True
# Running: True
# State: Running
```

### 服务日志

服务日志位于：

- **主日志**: `%USERPROFILE%\.omlx\logs\service.log`
- **错误日志**: `%USERPROFILE%\.omlx\logs\service.error.log`

查看日志：

```bash
# 打开日志目录
omlx service logs

# 或手动打开
explorer %USERPROFILE%\.omlx\logs
```

## 系统要求

### 最低要求

- **操作系统**: Windows 10 版本 2004 或更高
- **内存**: 8GB RAM
- **存储**: 10GB 可用空间
- **Python**: 3.10 或更高

### 推荐配置

- **操作系统**: Windows 11
- **内存**: 16GB+ RAM
- **GPU**: NVIDIA GTX 1060 6GB 或更高 / AMD RX 580 或更高
- **存储**: SSD，50GB+ 可用空间

### GPU 要求

| GPU 厂商 | 最低要求 | 推荐 | 后端 |
|---------|---------|------|------|
| **NVIDIA** | GTX 1060 6GB | RTX 3060 12GB+ | CUDA |
| **AMD** | RX 580 8GB | RX 6700 XT 12GB+ | DirectML |
| **Intel** | UHD 630 | Arc A770 16GB | DirectML/OpenVINO |

## 故障排除

### 常见问题

**1. DirectML 不可用**

```bash
# 确保安装了 DirectML 运行时
pip install onnxruntime-directml

# 验证安装
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

**2. CUDA 不可用**

```bash
# 安装 CUDA Toolkit 11.8+
# https://developer.nvidia.com/cuda-toolkit-archive

# 安装 cuDNN
# https://developer.nvidia.com/cudnn

# 验证安装
nvidia-smi
```

**3. 内存不足**

```bash
# 使用量化模型（GGUF Q4/Q5）
# 减小上下文长度
omlx serve --max-context-length 2048

# 减小批大小
omlx serve --max-batch-size 2
```

**4. 服务无法启动**

```bash
# 检查服务状态
omlx service status

# 查看服务日志
type %USERPROFILE%\.omlx\logs\service.log

# 重新安装服务
omlx service uninstall
omlx service install --model-dir C:\models
```

### 性能优化

**1. 使用量化模型**

```bash
# GGUF Q4_K_M 量化（推荐平衡）
model.gguf

# GGUF Q5_K_M 量化（更高质量）
model.gguf
```

**2. 优化缓存**

```bash
# 启用缓存
omlx serve --enable-cache --cache-size 4GB

# 调整缓存大小基于可用内存
```

**3. 选择合适后端**

```bash
# NVIDIA GPU
omlx serve --backend cuda

# AMD/Intel GPU
omlx serve --backend directml

# Intel CPU
omlx serve --backend openvino

# CPU only
omlx serve --backend cpu
```

## API 兼容性

oMLX Windows 提供 OpenAI 兼容的 API：

```bash
# 聊天补全
curl http://localhost:8000/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\": \"llama-3-8b\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}"

# 补全
curl http://localhost:8000/v1/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\": \"llama-3-8b\", \"prompt\": \"Once upon a time\"}"

# 列出模型
curl http://localhost:8000/v1/models
```

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/jundot/omlx.git
cd omlx

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装开发依赖
pip install -e ".[dev]" -f pyproject.windows.toml

# 运行测试
pytest tests/
```

### 构建

```bash
# 构建 wheel
python -m build

# 构建用于发布
python -m twine upload dist/*
```

## 许可证

[Apache 2.0](LICENSE)

## 致谢

- [ONNX Runtime](https://onnxruntime.ai/) - 跨平台推理引擎
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - GGUF 格式支持
- [Hugging Face](https://huggingface.co/) - 模型库
- [PyStray](https://github.com/moses-palmer/pystray) - 系统托盘支持

## 链接

- **GitHub**: https://github.com/jundot/omlx
- **文档**: https://github.com/jundot/omlx#readme
- **问题反馈**: https://github.com/jundot/omlx/issues
