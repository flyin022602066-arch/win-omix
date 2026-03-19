# SPDX-License-Identifier: Apache-2.0
"""
Hardware detection for Windows systems.

Provides unified hardware information for Windows:
- GPU detection (NVIDIA, AMD, Intel)
- Memory detection (RAM, VRAM)
- DirectML and CUDA availability
"""

from __future__ import annotations

import logging
import platform
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Default fallback value (conservative)
DEFAULT_MEMORY_BYTES = 16 * 1024 * 1024 * 1024  # 16GB


@dataclass
class WindowsHardwareInfo:
    """Hardware information for Windows systems."""

    gpu_name: str
    gpu_vendor: str  # "NVIDIA", "AMD", "Intel", "Unknown"
    total_memory_gb: float
    available_memory_gb: float
    vram_gb: float
    directml_available: bool
    cuda_available: bool
    openvino_available: bool


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32"


def get_gpu_info() -> tuple[str, str]:
    """
    Get GPU information via WMI or pynvml.
    
    Returns:
        (gpu_name, gpu_vendor) tuple
    """
    gpu_name = "Unknown GPU"
    gpu_vendor = "Unknown"
    
    # Try pynvml for NVIDIA GPUs first
    try:
        import pynvml
        
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(gpu_name, bytes):
                gpu_name = gpu_name.decode("utf-8")
            gpu_vendor = "NVIDIA"
            
            pynvml.nvmlShutdown()
            return gpu_name, gpu_vendor
    except Exception:
        pass
    
    # Fallback to WMI via PowerShell
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-WmiObject Win32_VideoController | Select-Object -First 1 -ExpandProperty Name"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        gpu_name = result.stdout.strip()
        
        if gpu_name:
            if "NVIDIA" in gpu_name.upper():
                gpu_vendor = "NVIDIA"
            elif "AMD" in gpu_name.upper() or "RADEON" in gpu_name.upper():
                gpu_vendor = "AMD"
            elif "INTEL" in gpu_name.upper():
                gpu_vendor = "Intel"
            elif "MICROSOFT" in gpu_name.upper():
                gpu_vendor = "Microsoft"
                
            return gpu_name, gpu_vendor
    except Exception as e:
        logger.warning(f"Failed to get GPU info: {e}")
    
    return gpu_name, gpu_vendor


def get_vram_gb() -> float:
    """
    Get dedicated VRAM in GB.
    
    Returns:
        VRAM in GB, or 0 if not available
    """
    # Try pynvml for NVIDIA
    try:
        import pynvml
        
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_bytes = memory_info.total
            pynvml.nvmlShutdown()
            return vram_bytes / (1024 ** 3)
    except Exception:
        pass
    
    # Fallback to WMI
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-WmiObject Win32_VideoController | Select-Object -First 1 -ExpandProperty AdapterRAM"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        vram_bytes = int(result.stdout.strip())
        return vram_bytes / (1024 ** 3)
    except Exception:
        pass
    
    return 0.0


def get_total_memory_bytes() -> int:
    """
    Get total system RAM in bytes.
    
    Returns:
        Total memory in bytes
    """
    try:
        import psutil
        
        return psutil.virtual_memory().total
    except Exception:
        pass
    
    # Fallback to PowerShell
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        return int(result.stdout.strip())
    except Exception:
        pass
    
    logger.warning(f"Using default memory size: {DEFAULT_MEMORY_BYTES // (1024**3)} GB")
    return DEFAULT_MEMORY_BYTES


def get_total_memory_gb() -> float:
    """Get total system RAM in GB."""
    return get_total_memory_bytes() / (1024 ** 3)


def get_available_memory_gb() -> float:
    """Get available system RAM in GB."""
    try:
        import psutil
        
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        pass
    
    return get_total_memory_gb() * 0.5  # Conservative estimate


def is_directml_available() -> bool:
    """Check if DirectML is available on Windows."""
    if not is_windows():
        return False
    
    try:
        import onnxruntime as ort
        
        # Check if DirectMLExecutionProvider is available
        available_providers = ort.get_available_providers()
        return "DirectMLExecutionProvider" in available_providers
    except Exception:
        return False


def is_cuda_available() -> bool:
    """Check if CUDA is available (for NVIDIA GPUs)."""
    try:
        import torch
        
        return torch.cuda.is_available()
    except Exception:
        pass
    
    # Alternative check via pynvml
    try:
        import pynvml
        
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        pynvml.nvmlShutdown()
        
        return device_count > 0
    except Exception:
        return False


def is_openvino_available() -> bool:
    """Check if OpenVINO is available (for Intel hardware)."""
    try:
        from openvino.runtime import Core
        
        core = Core()
        available_devices = core.available_devices
        return len(available_devices) > 0
    except Exception:
        return False


def detect_hardware() -> WindowsHardwareInfo:
    """
    Detect Windows hardware and return complete info.
    
    Returns:
        WindowsHardwareInfo with all hardware specifications
    """
    gpu_name, gpu_vendor = get_gpu_info()
    vram_gb = get_vram_gb()
    
    return WindowsHardwareInfo(
        gpu_name=gpu_name,
        gpu_vendor=gpu_vendor,
        total_memory_gb=get_total_memory_gb(),
        available_memory_gb=get_available_memory_gb(),
        vram_gb=vram_gb,
        directml_available=is_directml_available(),
        cuda_available=is_cuda_available(),
        openvino_available=is_openvino_available(),
    )


def get_recommended_backend() -> str:
    """
    Get recommended inference backend based on hardware.
    
    Returns:
        Backend name: "cuda", "directml", "openvino", or "cpu"
    """
    if is_cuda_available():
        return "cuda"
    
    if is_openvino_available():
        return "openvino"
    
    if is_directml_available():
        return "directml"
    
    return "cpu"


def format_bytes(bytes_value: int) -> str:
    """Format bytes as human-readable string."""
    if bytes_value >= 1024 ** 3:
        return f"{bytes_value / 1024**3:.2f} GB"
    elif bytes_value >= 1024 ** 2:
        return f"{bytes_value / 1024**2:.2f} MB"
    elif bytes_value >= 1024:
        return f"{bytes_value / 1024:.2f} KB"
    else:
        return f"{bytes_value} B"


def get_processor_info() -> str:
    """Get CPU information."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return platform.processor() or "Unknown CPU"


def get_os_version() -> str:
    """Get Windows version string."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "(Get-CimInstance Win32_OperatingSystem).Caption"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return f"Windows {platform.version()}"
