# SPDX-License-Identifier: Apache-2.0
"""
Platform abstraction layer for oMLX.

Provides unified interfaces for:
- Hardware detection
- Inference engines
- System integration (tray, services)
- Platform-specific utilities
"""

import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """Supported platforms."""
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """Platform information."""
    
    platform: PlatformType
    platform_name: str
    platform_version: str
    python_version: str
    architecture: str
    is_native: bool  # True if running on native hardware (not emulation)


class InferenceBackend(Enum):
    """Available inference backends."""
    MLX = "mlx"  # Apple Silicon
    DIRECTML = "directml"  # Windows DirectML
    CUDA = "cuda"  # NVIDIA CUDA
    OPENVINO = "openvino"  # Intel OpenVINO
    CPU = "cpu"  # CPU fallback
    GGUF = "gguf"  # llama.cpp GGUF format


@dataclass
class HardwareCapabilities:
    """Hardware capabilities."""
    
    backend: InferenceBackend
    gpu_name: str
    gpu_vendor: str
    total_ram_gb: float
    available_ram_gb: float
    vram_gb: float
    max_context_length: int
    max_batch_size: int
    supports_fp16: bool
    supports_int8: bool


def get_platform() -> PlatformType:
    """Detect current platform."""
    if sys.platform == "darwin":
        return PlatformType.MACOS
    elif sys.platform == "win32":
        return PlatformType.WINDOWS
    elif sys.platform.startswith("linux"):
        return PlatformType.LINUX
    else:
        return PlatformType.UNKNOWN


def get_platform_info() -> PlatformInfo:
    """Get detailed platform information."""
    import platform
    
    current_platform = get_platform()
    
    # Get platform name and version
    if current_platform == PlatformType.MACOS:
        platform_name = "macOS"
        platform_version = platform.mac_ver()[0] or "Unknown"
        is_native = True  # Always native on macOS
    elif current_platform == PlatformType.WINDOWS:
        platform_name = "Windows"
        platform_version = platform.version()
        # Check for WSL
        is_native = "microsoft-standard" not in platform.release().lower()
    elif current_platform == PlatformType.LINUX:
        platform_name = "Linux"
        platform_version = platform.release()
        is_native = True
    else:
        platform_name = "Unknown"
        platform_version = "Unknown"
        is_native = False
    
    return PlatformInfo(
        platform=current_platform,
        platform_name=platform_name,
        platform_version=platform_version,
        python_version=platform.python_version(),
        architecture=platform.machine(),
        is_native=is_native,
    )


def get_hardware_capabilities() -> HardwareCapabilities:
    """
    Get hardware capabilities for current platform.
    
    Returns:
        HardwareCapabilities with detected hardware features
    """
    current_platform = get_platform()
    
    if current_platform == PlatformType.MACOS:
        return _get_macos_hardware()
    elif current_platform == PlatformType.WINDOWS:
        return _get_windows_hardware()
    else:
        return _get_generic_hardware()


def _get_macos_hardware() -> HardwareCapabilities:
    """Get macOS hardware capabilities."""
    try:
        from .utils.hardware import detect_hardware, get_mlx_device_name
        
        hw_info = detect_hardware()
        
        # Check MLX availability
        try:
            import mlx.core as mx
            mlx_available = mx.metal.is_available()
        except Exception:
            mlx_available = False
        
        backend = InferenceBackend.MLX if mlx_available else InferenceBackend.CPU
        
        return HardwareCapabilities(
            backend=backend,
            gpu_name=hw_info.chip_name,
            gpu_vendor="Apple",
            total_ram_gb=hw_info.total_memory_gb,
            available_ram_gb=hw_info.total_memory_gb * 0.75,  # Estimate
            vram_gb=0,  # Unified memory
            max_context_length=8192,
            max_batch_size=32,
            supports_fp16=True,
            supports_int8=True,
        )
    
    except Exception as e:
        logger.warning(f"Failed to get macOS hardware info: {e}")
        return _get_generic_hardware()


def _get_windows_hardware() -> HardwareCapabilities:
    """Get Windows hardware capabilities."""
    try:
        from .utils.hardware_windows import detect_hardware, get_recommended_backend
        
        hw_info = detect_hardware()
        
        # Determine backend
        backend_name = get_recommended_backend()
        backend_map = {
            "cuda": InferenceBackend.CUDA,
            "directml": InferenceBackend.DIRECTML,
            "openvino": InferenceBackend.OPENVINO,
            "cpu": InferenceBackend.CPU,
        }
        backend = backend_map.get(backend_name, InferenceBackend.CPU)
        
        return HardwareCapabilities(
            backend=backend,
            gpu_name=hw_info.gpu_name,
            gpu_vendor=hw_info.gpu_vendor,
            total_ram_gb=hw_info.total_memory_gb,
            available_ram_gb=hw_info.available_memory_gb,
            vram_gb=hw_info.vram_gb,
            max_context_length=4096,
            max_batch_size=8,
            supports_fp16=backend != InferenceBackend.CPU,
            supports_int8=backend in (InferenceBackend.CUDA, InferenceBackend.OPENVINO),
        )
    
    except Exception as e:
        logger.warning(f"Failed to get Windows hardware info: {e}")
        return _get_generic_hardware()


def _get_generic_hardware() -> HardwareCapabilities:
    """Get generic hardware capabilities (fallback)."""
    try:
        import psutil
        
        total_ram = psutil.virtual_memory().total / (1024 ** 3)
        available_ram = psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        total_ram = 16.0
        available_ram = 8.0
    
    return HardwareCapabilities(
        backend=InferenceBackend.CPU,
        gpu_name="CPU",
        gpu_vendor="Unknown",
        total_ram_gb=total_ram,
        available_ram_gb=available_ram,
        vram_gb=0,
        max_context_length=2048,
        max_batch_size=4,
        supports_fp16=False,
        supports_int8=False,
    )


def get_inference_engine(
    model_path: str,
    backend: Optional[InferenceBackend] = None,
    **kwargs,
) -> Any:
    """
    Get appropriate inference engine for platform and backend.
    
    Args:
        model_path: Path to model
        backend: Preferred backend (auto-detected if None)
        **kwargs: Additional engine configuration
    
    Returns:
        Inference engine instance
    """
    current_platform = get_platform()
    
    # Auto-detect backend if not specified
    if backend is None:
        hw_caps = get_hardware_capabilities()
        backend = hw_caps.backend
    
    # Select engine based on backend
    if backend == InferenceBackend.MLX:
        return _get_mlx_engine(model_path, **kwargs)
    elif backend in (InferenceBackend.DIRECTML, InferenceBackend.CUDA, InferenceBackend.CPU):
        return _get_directml_engine(model_path, backend, **kwargs)
    elif backend == InferenceBackend.OPENVINO:
        return _get_openvino_engine(model_path, **kwargs)
    elif backend == InferenceBackend.GGUF:
        return _get_gguf_engine(model_path, **kwargs)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def _get_mlx_engine(model_path: str, **kwargs):
    """Get MLX engine for macOS."""
    try:
        from .engine.vlm import VLMEngine
        from .engine.llm import LLMEngine
        
        # Auto-detect model type
        model_path_obj = Path(model_path)
        
        # Check if VLM
        is_vlm = _is_vlm_model(model_path_obj)
        
        if is_vlm:
            return VLMEngine(model_path, **kwargs)
        else:
            return LLMEngine(model_path, **kwargs)
    
    except ImportError as e:
        logger.error(f"MLX not available: {e}")
        raise RuntimeError("MLX backend not available. Install mlx-lm.")


def _get_directml_engine(model_path: str, backend: InferenceBackend, **kwargs):
    """Get DirectML/ONNX engine for Windows."""
    from .engine.directml_engine import DirectMLEngine, EngineConfig
    
    config = EngineConfig(
        backend=backend.value,
        **kwargs,
    )
    
    return DirectMLEngine(model_path, config=config)


def _get_openvino_engine(model_path: str, **kwargs):
    """Get OpenVINO engine for Intel hardware."""
    try:
        from .engine.openvino_engine import OpenVINOEngine
        
        return OpenVINOEngine(model_path, **kwargs)
    
    except ImportError as e:
        logger.error(f"OpenVINO not available: {e}")
        raise RuntimeError("OpenVINO backend not available. Install optimum-openvino.")


def _get_gguf_engine(model_path: str, **kwargs):
    """Get GGUF/llama.cpp engine."""
    from .engine.directml_engine import DirectMLEngine, EngineConfig
    
    config = EngineConfig(
        backend="gguf",
        **kwargs,
    )
    
    return DirectMLEngine(model_path, config=config)


def _is_vlm_model(model_path: Path) -> bool:
    """Check if model is a Vision-Language Model."""
    # Check for vision config files
    vision_indicators = [
        "vision_config.json",
        "preprocessor_config.json",
        "image_processor.json",
    ]
    
    for indicator in vision_indicators:
        if (model_path / indicator).exists():
            return True
    
    # Check model config for vision-related keys
    config_file = model_path / "config.json"
    if config_file.exists():
        try:
            import json
            
            with open(config_file) as f:
                config = json.load(f)
            
            # Check for vision-related architecture
            arch = config.get("architectures", [])
            if any("vision" in str(a).lower() for a in arch):
                return True
            
            # Check for vision config
            if "vision_config" in config:
                return True
        
        except Exception:
            pass
    
    return False


def get_system_tray_app():
    """Get system tray application for current platform."""
    current_platform = get_platform()
    
    if current_platform == PlatformType.WINDOWS:
        from .tray_app import oMLXTrayApp
        return oMLXTrayApp()
    elif current_platform == PlatformType.MACOS:
        # macOS menu bar app (existing implementation)
        logger.warning("macOS tray app not yet implemented in this refactor")
        return None
    else:
        logger.warning(f"System tray not supported on {current_platform}")
        return None


def get_service_manager():
    """Get service manager for current platform."""
    current_platform = get_platform()
    
    if current_platform == PlatformType.WINDOWS:
        from .integrations.windows_service import WindowsServiceManager
        return WindowsServiceManager()
    elif current_platform == PlatformType.LINUX:
        # Linux systemd service
        logger.warning("Linux systemd service not yet implemented")
        return None
    else:
        logger.warning(f"Service manager not supported on {current_platform}")
        return None


def get_optimal_settings() -> Dict[str, Any]:
    """
    Get optimal settings for current hardware.
    
    Returns:
        Dictionary of recommended settings
    """
    hw_caps = get_hardware_capabilities()
    platform_info = get_platform_info()
    
    settings = {
        "platform": platform_info.platform.value,
        "backend": hw_caps.backend.value,
        "max_context_length": hw_caps.max_context_length,
        "max_batch_size": hw_caps.max_batch_size,
        "enable_fp16": hw_caps.supports_fp16,
        "enable_int8": hw_caps.supports_int8,
    }
    
    # Adjust based on available memory
    if hw_caps.available_ram_gb < 8:
        settings["max_context_length"] = min(settings["max_context_length"], 2048)
        settings["max_batch_size"] = min(settings["max_batch_size"], 2)
    elif hw_caps.available_ram_gb < 16:
        settings["max_context_length"] = min(settings["max_context_length"], 4096)
        settings["max_batch_size"] = min(settings["max_batch_size"], 4)
    
    # Adjust based on VRAM (for discrete GPUs)
    if hw_caps.vram_gb > 0:
        if hw_caps.vram_gb < 6:
            settings["max_batch_size"] = min(settings["max_batch_size"], 2)
        elif hw_caps.vram_gb < 12:
            settings["max_batch_size"] = min(settings["max_batch_size"], 4)
    
    return settings


def print_platform_summary():
    """Print platform and hardware summary."""
    platform_info = get_platform_info()
    hw_caps = get_hardware_capabilities()
    optimal = get_optimal_settings()
    
    print("\n" + "="*60)
    print("oMLX Platform Summary")
    print("="*60)
    print(f"Platform:        {platform_info.platform_name} {platform_info.platform_version}")
    print(f"Python:          {platform_info.python_version}")
    print(f"Architecture:    {platform_info.architecture}")
    print(f"Native:          {'Yes' if platform_info.is_native else 'No (Emulated)'}")
    print()
    print(f"GPU:             {hw_caps.gpu_name} ({hw_caps.gpu_vendor})")
    print(f"Backend:         {hw_caps.backend.value}")
    print(f"Total RAM:       {hw_caps.total_ram_gb:.1f} GB")
    print(f"Available RAM:   {hw_caps.available_ram_gb:.1f} GB")
    if hw_caps.vram_gb > 0:
        print(f"VRAM:            {hw_caps.vram_gb:.1f} GB")
    print()
    print("Recommended Settings:")
    print(f"  Max Context:     {optimal['max_context_length']}")
    print(f"  Max Batch:       {optimal['max_batch_size']}")
    print(f"  FP16:            {'Enabled' if optimal['enable_fp16'] else 'Disabled'}")
    print(f"  INT8:            {'Enabled' if optimal['enable_int8'] else 'Disabled'}")
    print("="*60 + "\n")
