# oMLX Windows 快速入门指南

## 🚀 5 分钟快速开始

### 步骤 1: 安装

运行自动安装脚本：

```batch
setup-windows.bat
```

这将：
- ✅ 创建虚拟环境
- ✅ 安装所有依赖
- ✅ 创建默认目录

### 步骤 2: 下载模型

**方法 1: 使用管理面板（推荐）**

1. 启动服务器：
   ```batch
   omlx-windows.bat serve
   ```

2. 访问管理面板：
   ```
   http://localhost:8000/admin/downloader
   ```

3. 搜索并下载模型

**方法 2: 手动下载**

推荐模型（适合 8-16GB RAM）：

```batch
# Llama 3 8B (4.9GB) - 通用对话
curl -L https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf ^
  -o "%USERPROFILE%\.omlx\models\llama-2-7b-chat.gguf"

# Qwen2.5 7B (4.2GB) - 中文优化
curl -L https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf ^
  -o "%USERPROFILE%\.omlx\models\qwen2.5-7b.gguf"
```

### 步骤 3: 启动服务

**选项 A: 系统托盘应用（推荐）**

```batch
omlx-windows.bat tray
```

系统托盘图标会出现在右下角，可以：
- 启动/停止服务器
- 查看状态
- 打开管理面板

**选项 B: 命令行**

```batch
omlx-windows.bat serve
```

**选项 C: Windows 服务（开机自启动）**

```batch
omlx-windows.bat service install
omlx-windows.bat service start
```

### 步骤 4: 使用 API

```bash
# 测试连接
curl http://localhost:8000/health

# 列出模型
curl http://localhost:8000/v1/models

# 聊天
curl http://localhost:8000/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\": \"llama-2-7b-chat\", \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}]}"
```

---

## 📋 常用命令

### 服务器管理

```batch
# 启动服务器
omlx-windows.bat serve

# 指定端口
omlx-windows.bat serve --port 8080

# 使用特定后端
omlx-windows.bat serve --backend cuda
omlx-windows.bat serve --backend directml

# 查看帮助
omlx-windows.bat help
```

### 系统托盘

```batch
# 启动托盘应用
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

---

## 🔧 故障排除

### 问题 1: 无法启动服务器

**症状**: 报错 "Address already in use"

**解决**:
```batch
# 更改端口
omlx-windows.bat serve --port 8080
```

### 问题 2: 内存不足

**症状**: 生成过程中崩溃

**解决**:
```batch
# 使用更小的上下文
omlx-windows.bat serve --max-context-length 2048

# 使用量化模型（推荐）
# 下载 Q4 或 Q5 量化版本的 GGUF 模型
```

### 问题 3: DirectML 不可用

**症状**: "DirectMLExecutionProvider not available"

**解决**:
```batch
# 重新安装 DirectML
pip uninstall onnxruntime-directml
pip install onnxruntime-directml --force-reinstall
```

### 问题 4: CUDA 不可用（NVIDIA GPU）

**症状**: "CUDAExecutionProvider not available"

**解决**:
1. 安装 CUDA Toolkit 11.8+: https://developer.nvidia.com/cuda-toolkit
2. 安装 cuDNN: https://developer.nvidia.com/cudnn
3. 验证安装: `nvidia-smi`

---

## 📊 性能优化建议

### 根据内存配置

**8GB RAM**:
```batch
omlx-windows.bat serve ^
  --max-context-length 2048 ^
  --max-batch-size 2 ^
  --backend gguf
```

**16GB RAM**:
```batch
omlx-windows.bat serve ^
  --max-context-length 4096 ^
  --max-batch-size 4 ^
  --backend directml
```

**32GB+ RAM**:
```batch
omlx-windows.bat serve ^
  --max-context-length 8192 ^
  --max-batch-size 8 ^
  --enable-cache ^
  --cache-size 8GB
```

### 根据 GPU

**NVIDIA GPU**:
```batch
omlx-windows.bat serve --backend cuda
```

**AMD GPU**:
```batch
omlx-windows.bat serve --backend directml
```

**Intel GPU/CPU**:
```batch
omlx-windows.bat serve --backend openvino
```

---

## 📁 目录结构

```
%USERPROFILE%\.omlx\
├── models\           # 模型文件
├── logs\             # 日志文件
└── settings.json     # 配置文件
```

---

## 🔗 有用链接

- **管理面板**: http://localhost:8000/admin
- **API 文档**: http://localhost:8000/docs
- **模型下载**: https://huggingface.co/TheBloke
- **GGUF 模型**: https://huggingface.co/models?library=gguf

---

## 💡 提示

1. **首次启动**会较慢，因为需要加载模型
2. **系统托盘应用**是最方便的管理方式
3. **GGUF 量化模型**可以显著减少内存使用
4. **Windows 服务**适合长期运行的场景

---

## 🆘 获取帮助

如果遇到问题：

1. 查看日志：
   ```batch
   explorer %USERPROFILE%\.omlx\logs
   ```

2. 查看 GitHub Issues:
   https://github.com/jundot/omlx/issues

3. 提供以下信息：
   - Windows 版本
   - Python 版本
   - GPU 型号
   - 错误日志

祝使用愉快！🎉
