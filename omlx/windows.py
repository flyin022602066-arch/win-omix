# SPDX-License-Identifier: Apache-2.0
"""
oMLX Windows - LLM inference server optimized for Windows
"""

__version__ = "1.0.0-windows"

# Import platform detection
from omlx.platform import get_platform, PlatformType

# Verify we're on Windows
import sys
if sys.platform != "win32":
    import warnings
    warnings.warn("oMLX Windows is optimized for Windows systems")

# Export main components
from omlx.engine.directml_engine import DirectMLEngine, EngineConfig, SamplingParams
from omlx.memory_manager_windows import MemoryManager, MemoryConfig, get_memory_manager
from omlx.cache.paged_cache_windows import WindowsPagedCache, WindowsCacheManager
from omlx.benchmark_windows import WindowsBenchmark, BenchmarkConfig, run_benchmark
from omlx.utils.hardware_windows import (
    detect_hardware,
    get_recommended_backend,
    is_directml_available,
    is_cuda_available,
)

__all__ = [
    # Engine
    "DirectMLEngine",
    "EngineConfig",
    "SamplingParams",
    
    # Memory Management
    "MemoryManager",
    "MemoryConfig",
    "get_memory_manager",
    
    # Cache
    "WindowsPagedCache",
    "WindowsCacheManager",
    
    # Benchmark
    "WindowsBenchmark",
    "BenchmarkConfig",
    "run_benchmark",
    
    # Hardware Detection
    "detect_hardware",
    "get_recommended_backend",
    "is_directml_available",
    "is_cuda_available",
    
    # Platform
    "get_platform",
    "PlatformType",
    
    # Version
    "__version__",
]
