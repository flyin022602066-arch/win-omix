# oMLX - 跨平台 LLM 推理服务器

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/icon-rounded-dark.svg" width="140">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/icon-rounded-light.svg" width="140">
    <img alt="oMLX" src="docs/images/icon-rounded-light.svg" width="140">
  </picture>
</p>

<p align="center">
  <b>本地 LLM 推理，为你的系统优化</b><br>
  连续批处理 | 分层缓存 | 系统托盘管理 | Windows 服务集成
</p>

<p align="center">
  <a href="README.windows.md"><b>Windows 版本</b></a> · 
  <a href="README.md">macOS 版本</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS-black" alt="Platform">
</p>

---

## 🌟 特性

### 跨平台支持

| 平台 | 推理后端 | GPU 支持 | 状态 |
|------|---------|---------|------|
| **Windows** | DirectML/CUDA/OpenVINO/GGUF | NVIDIA/AMD/Intel | ✅ 完整支持 |
| **macOS** | MLX/Metal | Apple Silicon | ✅ 完整支持 |

### 核心功能

- 🚀 **连续批处理** - 提高吞吐量，优化并发请求
- 💾 **分层缓存** - 热缓存 (RAM) + 冷缓存 (SSD)，跨请求复用
- 🎯 **多模型管理** - LRU 驱逐，模型固定，TTL 自动卸载
- 🖥️ **系统集成** - Windows 托盘应用 / macOS 菜单栏
- 🔧 **Windows 服务** - 开机自启，后台运行，自动恢复
- 📊 **管理面板** - 实时监控，模型下载，基准测试
- 🔌 **API 兼容** - OpenAI 和 Anthropic API 直接替代

### Windows 专属特性

- ✅ **多后端支持** - DirectML (AMD/Intel), CUDA (NVIDIA), OpenVINO (Intel)
- ✅ **系统托盘应用** - 便捷管理，状态监控
- ✅ **Windows 服务** - 原生服务集成，支持 NSSM
- ✅ **GGUF 格式** - llama.cpp 支持，量化模型优化
- ✅ **中文文档** - 完整的中文快速入门和故障排除

---

## 🚀 快速开始 (Windows)

### 1. 安装

```batch
REM 一键安装
setup-windows.bat
```

### 2. 启动

```batch
REM 方式 A: 系统托盘应用（推荐）
omlx-windows.bat tray

REM 方式 B: 命令行
omlx-windows.bat serve

REM 方式 C: Windows 服务（开机自启）
omlx-windows.bat service install
omlx-windows.bat service start
```

### 3. 使用

访问管理面板：http://localhost:8000/admin

---

## 📦 模型支持

### 支持的格式

| 格式 | 后端 | 说明 |
|------|------|------|
| **GGUF** | llama.cpp | 量化模型，内存友好 |
| **ONNX** | DirectML/CUDA | 优化格式，性能最佳 |
| **Transformers** | CUDA/CPU | HuggingFace 原生 |

### 推荐模型

```bash
# Llama 3 8B (4.9GB) - 平衡性能和速度
TheBloke/Llama-2-7B-Chat-GGUF

# Qwen2.5 7B (4.2GB) - 中文优化
Qwen/Qwen2.5-7B-Instruct-GGUF

# Phi-3 Mini (2.3GB) - 轻量级
microsoft/Phi-3-mini-4k-instruct-GGUF
```

---

## 🔧 配置示例

### 低内存配置 (8GB RAM)

```batch
omlx-windows.bat serve ^
  --max-context-length 2048 ^
  --max-batch-size 2 ^
  --backend gguf
```

### 高性能配置 (16GB+ RAM)

```batch
omlx-windows.bat serve ^
  --max-context-length 8192 ^
  --max-batch-size 8 ^
  --backend cuda ^
  --enable-cache ^
  --cache-size 8GB
```

### NVIDIA GPU

```batch
omlx-windows.bat serve --backend cuda
```

### AMD/Intel GPU

```batch
omlx-windows.bat serve --backend directml
```

---

## 📖 文档

### Windows 用户

- 📘 [完整文档](README.windows.md) - 详细安装、配置、API 参考
- 🚀 [快速入门](QUICKSTART.windows.md) - 5 分钟上手指南
- 🔍 [故障排除](README.windows.md#故障排除) - 常见问题解决

### macOS 用户

- 📘 [macOS 文档](README.md) - Apple Silicon 优化版本

---

## 💻 系统要求

### Windows

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| **操作系统** | Windows 10 2004 | Windows 11 |
| **内存** | 8GB RAM | 16GB+ RAM |
| **GPU** | GTX 1060 6GB / RX 580 | RTX 3060 12GB+ / RX 6700 XT |
| **存储** | 10GB | SSD, 50GB+ |
| **Python** | 3.10+ | 3.11+ |

### macOS

| 组件 | 要求 |
|------|------|
| **系统** | macOS 13.0+ |
| **芯片** | Apple Silicon (M1/M2/M3/M4) |
| **内存** | 8GB+ |

---

## 🔌 API 使用

### 聊天补全

```bash
curl http://localhost:8000/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\": \"llama-2-7b-chat\", \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}]}"
```

### Python 示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # 本地运行不需要密钥
)

response = client.chat.completions.create(
    model="llama-2-7b-chat",
    messages=[
        {"role": "user", "content": "你好，请介绍一下自己"}
    ]
)

print(response.choices[0].message.content)
```

---

## 🛠️ 开发

### 设置开发环境

```batch
REM 克隆仓库
git clone https://github.com/jundot/omlx.git
cd omlx

REM 创建虚拟环境
python -m venv venv
venv\Scripts\activate

REM 安装开发依赖
pip install -e ".[dev]" -f pyproject.windows.toml

REM 运行测试
pytest tests/
```

### 构建

```batch
REM 构建 wheel
python -m build

REM 发布
python -m twine upload dist/*
```

---

## 📊 性能对比

| 模型 | 后端 | GPU | 速度 (tokens/s) | 内存 |
|------|------|-----|----------------|------|
| Llama 3 8B Q4 | CUDA | RTX 3060 | ~45 t/s | 6GB |
| Llama 3 8B Q4 | DirectML | RX 6700 XT | ~30 t/s | 8GB |
| Llama 3 8B Q4 | GGUF CPU | i7-12700K | ~8 t/s | 10GB |
| Phi-3 Mini Q4 | DirectML | Intel Arc | ~25 t/s | 4GB |

*性能数据仅供参考，实际性能因硬件和配置而异*

---

## 🤝 贡献

欢迎贡献！

- 🐛 Bug 修复
- 📝 文档改进
- 🚀 性能优化
- 💡 新功能建议

详情请参阅 [贡献指南](docs/CONTRIBUTING.md)。

---

## 📄 许可证

[Apache 2.0](LICENSE)

---

## 🙏 致谢

- [MLX](https://github.com/ml-explore/mlx) - Apple 的机器学习框架
- [ONNX Runtime](https://onnxruntime.ai/) - 跨平台推理引擎
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - GGUF 格式和 CPU 推理
- [Hugging Face](https://huggingface.co/) - 模型库
- [PyStray](https://github.com/moses-palmer/pystray) - 系统托盘支持

---

## 🔗 链接

- **GitHub**: https://github.com/jundot/omlx
- **文档**: 
  - [Windows 版本](README.windows.md)
  - [macOS 版本](README.md)
- **问题反馈**: https://github.com/jundot/omlx/issues
- **讨论区**: https://github.com/jundot/omlx/discussions

---

<p align="center">
  <b>oMLX - 让本地 LLM 推理更简单</b>
</p>
