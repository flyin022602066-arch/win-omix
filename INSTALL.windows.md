# oMLX Windows 安装指南

## ✅ 问题已修复

之前安装失败是因为使用了错误的依赖配置方式。现在已修复：

### 修复内容

1. **创建了 `requirements-windows.txt`** - 标准的 pip 依赖文件
2. **更新了安装脚本** - `setup-windows.bat` 和 `omlx-windows.bat` 现在使用正确的依赖文件

## 📦 安装方法

### 方法 1: 自动安装（推荐）

```batch
REM 运行安装脚本
setup-windows.bat
```

### 方法 2: 手动安装

```batch
REM 创建虚拟环境
python -m venv venv
venv\Scripts\activate

REM 安装所有依赖
pip install -r requirements-windows.txt

REM 安装 oMLX 本身
pip install -e .
```

## 📋 依赖说明

### 核心依赖

- **onnxruntime-directml** - DirectML 推理引擎 (25MB)
- **llama-cpp-python** - GGUF 模型支持 (50MB，需要编译)
- **transformers** - Hugging Face 模型支持
- **optimum** + **optimum-intel** - 模型优化
- **accelerate** - PyTorch 加速

### Windows 特定依赖

- **pywin32** - Windows API 集成
- **pystray** - 系统托盘支持
- **pynvml** - NVIDIA GPU 监控
- **opencv-python** - 图像处理 (40MB)

### 其他依赖

- **bitsandbytes** - 量化支持 (55MB)
- **openai-harmony** - Harmony 格式解析
- **fastapi** + **uvicorn** - Web 服务器
- **jsonschema** - JSON Schema 验证

## ⏱️ 安装时间

- **快速网络**: 3-5 分钟
- **普通网络**: 5-10 分钟
- **llama-cpp-python 编译**: 额外 2-5 分钟

## 🔍 验证安装

安装完成后，验证是否成功：

```batch
REM 检查 Python 包
pip list | findstr omlx
pip list | findstr onnxruntime
pip list | findstr llama

REM 测试导入
python -c "from omlx.platform import get_platform; print(get_platform())"
```

## 🐛 常见问题

### 1. llama-cpp-python 编译失败

**症状**: `error: Microsoft Visual C++ 14.0 or greater is required`

**解决**:
```batch
REM 安装 Microsoft C++ Build Tools
REM 下载地址：https://visualstudio.microsoft.com/visual-cpp-build-tools/
REM 安装 "Desktop development with C++" 工作负载
```

### 2. onnxruntime-directml 安装失败

**症状**: `No matching distribution found`

**解决**:
```batch
REM 确保使用 Python 3.10+
python --version

REM 升级 pip
python -m pip install --upgrade pip

REM 手动安装
pip install onnxruntime-directml
```

### 3. 依赖冲突

**症状**: `ERROR: Cannot install ... and ... because these packages depend on each other`

**解决**:
```batch
REM 使用 --no-deps 安装冲突包，然后单独安装依赖
pip install package-name --no-deps
pip install dependency-name
```

## 📊 磁盘空间需求

- **基础依赖**: ~2GB
- **可选依赖** (OpenVINO 等): +5GB
- **模型文件**: 根据模型大小 (通常 4-50GB)

建议至少预留 **10GB** 可用空间。

## 🚀 安装后步骤

1. **验证安装**
   ```batch
   python -c "import omlx; print('oMLX installed successfully!')"
   ```

2. **下载模型**
   - 访问管理面板：http://localhost:8000/admin/downloader
   - 或手动下载 GGUF 模型

3. **启动服务器**
   ```batch
   omlx-windows.bat serve
   ```

4. **或使用托盘应用**
   ```batch
   omlx-windows.bat tray
   ```

## 📝 完整安装日志

安装过程中会显示：
- ✅ 已安装的包（Requirement already satisfied）
- ⬇️ 正在下载的包（Collecting/Downloading）
- 🔨 正在编译的包（Building wheel）

安装完成标志：
```
Successfully installed ...
```

## 💡 提示

1. **使用国内镜像加速**（可选）:
   ```batch
   pip install -r requirements-windows.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **如果安装时间过长**，可以查看进度：
   - 打开任务管理器
   - 查看 "详细信息" 标签
   - 找到 python.exe 进程

3. **安装失败时**，尝试分步安装：
   ```batch
   pip install onnxruntime-directml
   pip install llama-cpp-python
   pip install transformers accelerate optimum
   pip install pywin32 pystray
   pip install -e .
   ```

## 🔗 相关文档

- [快速入门](QUICKSTART.windows.md)
- [完整文档](README.windows.md)
- [性能优化](IMPROVEMENTS.windows.md)

---

**最后更新**: 2026-03-19  
**版本**: 1.0.0-windows
