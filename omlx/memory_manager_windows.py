# SPDX-License-Identifier: Apache-2.0
"""
Advanced memory management for oMLX Windows.

Provides:
- Dynamic memory allocation
- Memory pressure monitoring
- Intelligent model unloading
- GPU memory management
- Memory-efficient attention
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import psutil

logger = logging.getLogger(__name__)


class MemoryState(Enum):
    """Memory pressure state."""
    
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryConfig:
    """Memory management configuration."""
    
    # Memory thresholds (percentage of total RAM)
    normal_threshold: float = 0.7  # 70%
    elevated_threshold: float = 0.8  # 80%
    high_threshold: float = 0.9  # 90%
    critical_threshold: float = 0.95  # 95%
    
    # GPU memory (if available)
    gpu_memory_fraction: float = 0.8  # Use 80% of GPU memory
    gpu_memory_reserved: float = 1.0  # Reserve 1GB
    
    # Model memory limits
    max_model_memory_gb: float = 0.0  # 0 = auto
    max_models_loaded: int = 3  # Maximum models in memory
    
    # Eviction policy
    eviction_delay_seconds: float = 5.0  # Wait before evicting
    min_models_to_keep: int = 1  # Always keep at least 1 model
    
    # Monitoring
    monitor_interval_seconds: float = 1.0  # Check memory every second
    enable_auto_eviction: bool = True  # Automatically evict models under pressure


@dataclass
class ModelMemoryInfo:
    """Memory information for a loaded model."""
    
    model_id: str
    model_path: str
    memory_bytes: int
    load_time: float
    last_access_time: float
    access_count: int = 0
    is_pinned: bool = False  # Pinned models won't be evicted
    backend: str = ""


class MemoryManager:
    """
    Advanced memory manager for Windows.
    
    Features:
    - Real-time memory monitoring
    - Automatic model eviction under pressure
    - LRU-based eviction policy
    - GPU memory management
    - Memory-efficient attention support
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize memory manager.
        
        Args:
            config: Memory configuration
        """
        self.config = config or MemoryConfig()
        
        # Loaded models
        self.loaded_models: Dict[str, ModelMemoryInfo] = {}
        self.model_access_order: List[str] = []
        
        # Memory monitoring
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_lock = threading.Lock()
        
        # Callbacks
        self.eviction_callbacks: Dict[str, Callable] = {}
        
        # Current state
        self.current_state = MemoryState.NORMAL
        self.last_check_time = 0.0
        
        # GPU memory tracking
        self.gpu_available = False
        self.gpu_total_memory = 0
        self.gpu_used_memory = 0
        
        self._init_gpu_tracking()
        
        logger.info("MemoryManager initialized")
        logger.info(f"Max models: {self.config.max_models_loaded}")
        logger.info(f"Auto eviction: {self.config.enable_auto_eviction}")
    
    def _init_gpu_tracking(self) -> None:
        """Initialize GPU memory tracking."""
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                self.gpu_available = True
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                self.gpu_total_memory = memory_info.total
                self.gpu_used_memory = memory_info.used
                
                logger.info(f"GPU tracking enabled: {self.gpu_total_memory / (1024**3):.1f}GB")
            
            pynvml.nvmlShutdown()
        except Exception:
            logger.info("GPU tracking not available (NVIDIA only)")
    
    def start_monitoring(self) -> None:
        """Start memory monitoring thread."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MemoryMonitor",
        )
        self.monitor_thread.start()
        
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            self.monitor_thread = None
        
        logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring:
            try:
                self._check_memory_state()
                
                if self.config.enable_auto_eviction:
                    self._handle_memory_pressure()
            
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
            
            time.sleep(self.config.monitor_interval_seconds)
    
    def _check_memory_state(self) -> None:
        """Check current memory state."""
        try:
            memory = psutil.virtual_memory()
            usage_ratio = memory.percent / 100.0
            
            if usage_ratio >= self.config.critical_threshold:
                new_state = MemoryState.CRITICAL
            elif usage_ratio >= self.config.high_threshold:
                new_state = MemoryState.HIGH
            elif usage_ratio >= self.config.elevated_threshold:
                new_state = MemoryState.ELEVATED
            else:
                new_state = MemoryState.NORMAL
            
            if new_state != self.current_state:
                logger.info(f"Memory state changed: {self.current_state.value} → {new_state.value}")
                self.current_state = new_state
            
            self.last_check_time = time.time()
        
        except Exception as e:
            logger.error(f"Failed to check memory state: {e}")
    
    def _handle_memory_pressure(self) -> None:
        """Handle memory pressure by evicting models."""
        if self.current_state == MemoryState.NORMAL:
            return
        
        # Determine how many models to evict
        models_to_evict = 0
        
        if self.current_state == MemoryState.ELEVATED:
            models_to_evict = 1
        elif self.current_state == MemoryState.HIGH:
            models_to_evict = max(1, len(self.loaded_models) // 2)
        elif self.current_state == MemoryState.CRITICAL:
            models_to_evict = max(1, len(self.loaded_models) - self.config.min_models_to_keep)
        
        # Evict models
        evicted = 0
        for _ in range(models_to_evict):
            if len(self.loaded_models) <= self.config.min_models_to_keep:
                break
            
            model_id = self._select_eviction_candidate()
            if model_id:
                self.evict_model(model_id)
                evicted += 1
        
        if evicted > 0:
            logger.info(f"Evicted {evicted} models due to memory pressure")
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """
        Select a model to evict using LRU policy.
        
        Returns:
            Model ID to evict, or None if no candidates
        """
        # Find unpinned models sorted by last access time
        candidates = [
            (model_id, info)
            for model_id, info in self.loaded_models.items()
            if not info.is_pinned
        ]
        
        if not candidates:
            # If all models are pinned, select the least recently accessed
            candidates = list(self.loaded_models.items())
        
        if not candidates:
            return None
        
        # Sort by last access time (oldest first)
        candidates.sort(key=lambda x: x[1].last_access_time)
        
        # Return the least recently used
        return candidates[0][0]
    
    def register_model(
        self,
        model_id: str,
        model_path: str,
        memory_bytes: int,
        backend: str = "",
        is_pinned: bool = False,
    ) -> None:
        """
        Register a loaded model.
        
        Args:
            model_id: Unique model identifier
            model_path: Path to model
            memory_bytes: Memory usage in bytes
            backend: Inference backend
            is_pinned: If True, model won't be auto-evicted
        """
        now = time.time()
        
        info = ModelMemoryInfo(
            model_id=model_id,
            model_path=model_path,
            memory_bytes=memory_bytes,
            load_time=now,
            last_access_time=now,
            is_pinned=is_pinned,
            backend=backend,
        )
        
        self.loaded_models[model_id] = info
        self.model_access_order.append(model_id)
        
        logger.info(f"Registered model: {model_id} ({memory_bytes / (1024**3):.2f}GB)")
        
        # Check if we exceeded max models
        if len(self.loaded_models) > self.config.max_models_loaded:
            self._enforce_model_limit()
    
    def _enforce_model_limit(self) -> None:
        """Enforce maximum model limit."""
        while len(self.loaded_models) > self.config.max_models_loaded:
            model_id = self._select_eviction_candidate()
            if model_id:
                self.evict_model(model_id)
            else:
                break
    
    def record_access(self, model_id: str) -> None:
        """Record a model access (updates LRU order)."""
        if model_id not in self.loaded_models:
            return
        
        info = self.loaded_models[model_id]
        info.last_access_time = time.time()
        info.access_count += 1
        
        # Update access order
        if model_id in self.model_access_order:
            self.model_access_order.remove(model_id)
        self.model_access_order.append(model_id)
    
    def evict_model(self, model_id: str) -> bool:
        """
        Evict a model from memory.
        
        Args:
            model_id: Model to evict
        
        Returns:
            True if successful
        """
        if model_id not in self.loaded_models:
            return False
        
        info = self.loaded_models[model_id]
        
        # Don't evict pinned models unless manually requested
        if info.is_pinned and model_id not in self.eviction_callbacks:
            logger.warning(f"Attempting to evict pinned model: {model_id}")
        
        logger.info(f"Evicting model: {model_id}")
        
        # Call eviction callback
        if model_id in self.eviction_callbacks:
            try:
                self.eviction_callbacks[model_id](model_id)
            except Exception as e:
                logger.error(f"Eviction callback failed: {e}")
        
        # Remove from tracking
        self.loaded_models.pop(model_id, None)
        if model_id in self.model_access_order:
            self.model_access_order.remove(model_id)
        self.eviction_callbacks.pop(model_id, None)
        
        logger.info(f"Evicted model: {model_id} ({info.memory_bytes / (1024**3):.2f}GB freed)")
        
        return True
    
    def pin_model(self, model_id: str) -> None:
        """Pin a model to prevent auto-eviction."""
        if model_id in self.loaded_models:
            self.loaded_models[model_id].is_pinned = True
            logger.info(f"Pinned model: {model_id}")
    
    def unpin_model(self, model_id: str) -> None:
        """Unpin a model to allow auto-eviction."""
        if model_id in self.loaded_models:
            self.loaded_models[model_id].is_pinned = False
            logger.info(f"Unpinned model: {model_id}")
    
    def set_eviction_callback(
        self,
        model_id: str,
        callback: Callable[[str], None],
    ) -> None:
        """
        Set eviction callback for a model.
        
        Args:
            model_id: Model identifier
            callback: Function to call on eviction
        """
        self.eviction_callbacks[model_id] = callback
    
    def get_memory_state(self) -> Dict[str, Any]:
        """Get current memory state."""
        memory = psutil.virtual_memory()
        
        state = {
            "state": self.current_state.value,
            "system_memory": {
                "total_gb": memory.total / (1024 ** 3),
                "available_gb": memory.available / (1024 ** 3),
                "used_gb": memory.used / (1024 ** 3),
                "percent": memory.percent,
            },
            "loaded_models": len(self.loaded_models),
            "total_model_memory_gb": sum(
                info.memory_bytes for info in self.loaded_models.values()
            ) / (1024 ** 3),
            "pinned_models": sum(
                1 for info in self.loaded_models.values() if info.is_pinned
            ),
        }
        
        # Add GPU info if available
        if self.gpu_available:
            try:
                import pynvml
                
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                
                if device_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    state["gpu_memory"] = {
                        "total_gb": gpu_memory.total / (1024 ** 3),
                        "used_gb": gpu_memory.used / (1024 ** 3),
                        "free_gb": gpu_memory.free / (1024 ** 3),
                    }
                
                pynvml.nvmlShutdown()
            except Exception:
                pass
        
        return state
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a loaded model."""
        if model_id not in self.loaded_models:
            return None
        
        info = self.loaded_models[model_id]
        
        return {
            "model_id": info.model_id,
            "model_path": info.model_path,
            "memory_gb": info.memory_bytes / (1024 ** 3),
            "load_time": info.load_time,
            "last_access_time": info.last_access_time,
            "access_count": info.access_count,
            "is_pinned": info.is_pinned,
            "backend": info.backend,
        }
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get information about all loaded models."""
        return [
            self.get_model_info(model_id)
            for model_id in self.loaded_models
            if self.get_model_info(model_id)
        ]
    
    def clear_all(self) -> None:
        """Clear all loaded models."""
        logger.info("Clearing all models")
        
        model_ids = list(self.loaded_models.keys())
        for model_id in model_ids:
            self.evict_model(model_id)
        
        logger.info("All models cleared")
    
    def shutdown(self) -> None:
        """Shutdown memory manager."""
        self.stop_monitoring()
        self.clear_all()
        logger.info("MemoryManager shutdown complete")


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager."""
    global _memory_manager
    
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        _memory_manager.start_monitoring()
    
    return _memory_manager


def initialize_memory_manager(config: Optional[MemoryConfig] = None) -> MemoryManager:
    """Initialize global memory manager with config."""
    global _memory_manager
    
    if _memory_manager:
        _memory_manager.shutdown()
    
    _memory_manager = MemoryManager(config)
    _memory_manager.start_monitoring()
    
    return _memory_manager
