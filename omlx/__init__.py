# SPDX-License-Identifier: Apache-2.0
"""
omlx: Cross-platform LLM inference server

Platform-specific imports are handled automatically:
- Windows: DirectML/CUDA/OpenVINO/GGUF backends
- macOS: MLX framework (Apple Silicon)
"""

import sys
import warnings

from omlx._version import __version__

# Detect platform
_is_windows = sys.platform == "win32"
_is_macos = sys.platform == "darwin"

# Platform-specific imports
if _is_windows:
    # Windows imports - lazy loading to avoid mlx dependency
    __all__ = [
        "__version__",
        "Request", "RequestOutput", "RequestStatus", "SamplingParams",
        "Scheduler", "SchedulerConfig", "SchedulerOutput",
    ]
    
    def __getattr__(name):
        # Lazy imports for Windows
        if name in ("Request", "RequestOutput", "RequestStatus", "SamplingParams"):
            from omlx.request import (
                Request, RequestOutput, RequestStatus, SamplingParams
            )
            return {
                "Request": Request,
                "RequestOutput": RequestOutput,
                "RequestStatus": RequestStatus,
                "SamplingParams": SamplingParams,
            }[name]
        elif name in ("Scheduler", "SchedulerConfig", "SchedulerOutput"):
            from omlx.scheduler import (
                Scheduler, SchedulerConfig, SchedulerOutput
            )
            return {
                "Scheduler": Scheduler,
                "SchedulerConfig": SchedulerConfig,
                "SchedulerOutput": SchedulerOutput,
            }[name]
        else:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    
    # Export Windows-specific components
    try:
        from omlx.windows import (
            DirectMLEngine, EngineConfig, SamplingParams as WindowsSamplingParams,
            MemoryManager, MemoryConfig, get_memory_manager,
            WindowsPagedCache, WindowsCacheManager,
            WindowsBenchmark, BenchmarkConfig, run_benchmark,
            detect_hardware, get_recommended_backend,
        )
        
        __all__.extend([
            "DirectMLEngine",
            "EngineConfig",
            "MemoryManager",
            "MemoryConfig",
            "get_memory_manager",
            "WindowsPagedCache",
            "WindowsCacheManager",
            "WindowsBenchmark",
            "BenchmarkConfig",
            "run_benchmark",
            "detect_hardware",
            "get_recommended_backend",
        ])
    except ImportError as e:
        warnings.warn(f"Could not import Windows-specific components: {e}")

elif _is_macos:
    # macOS imports (original behavior)
    from omlx.scheduler import Scheduler, SchedulerConfig, SchedulerOutput
    from omlx.engine_core import EngineCore, AsyncEngineCore, EngineConfig
    from omlx.cache.prefix_cache import BlockAwarePrefixCache
    from omlx.cache.paged_cache import PagedCacheManager, CacheBlock, BlockTable
    from omlx.cache.stats import PrefixCacheStats, PagedCacheStats
    from omlx.model_registry import get_registry, ModelOwnershipError
    
    # Backward compatibility alias
    CacheStats = PagedCacheStats
    
    __all__ = [
        # Request management
        "Request", "RequestOutput", "RequestStatus", "SamplingParams",
        # Scheduler
        "Scheduler", "SchedulerConfig", "SchedulerOutput",
        # Engine
        "EngineCore", "AsyncEngineCore", "EngineConfig",
        # Model registry
        "get_registry", "ModelOwnershipError",
        # Prefix cache
        "BlockAwarePrefixCache",
        # Paged cache
        "PagedCacheManager", "CacheBlock", "BlockTable",
        "PagedCacheStats", "CacheStats",
        # Version
        "__version__",
    ]
else:
    warnings.warn(f"Linux support is experimental. Detected platform: {sys.platform}")

__all__ = [
    # Request management
    "Request",
    "RequestOutput",
    "RequestStatus",
    "SamplingParams",
    # Scheduler
    "Scheduler",
    "SchedulerConfig",
    "SchedulerOutput",
    # Engine
    "EngineCore",
    "AsyncEngineCore",
    "EngineConfig",
    # Model registry
    "get_registry",
    "ModelOwnershipError",
    # Prefix cache (paged SSD-only)
    "BlockAwarePrefixCache",
    # Paged cache (memory efficiency)
    "PagedCacheManager",
    "CacheBlock",
    "BlockTable",
    "PagedCacheStats",
    "CacheStats",  # Backward compatibility alias
    # Version
    "__version__",
]
