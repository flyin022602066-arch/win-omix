# SPDX-License-Identifier: Apache-2.0
"""
Paged cache implementation optimized for Windows.

This module provides Windows-specific cache optimizations:
- Memory-mapped file I/O for efficient SSD caching
- DirectML-aware buffer management
- Windows-specific memory pressure handling
"""

import logging
import mmap
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Windows-specific constants
WINDOWS_CACHE_DEFAULT = Path.home() / ".omlx" / "cache"
DEFAULT_BLOCK_SIZE = 512  # KB
DEFAULT_MAX_CACHE_SIZE = 100 * 1024 * 1024 * 1024  # 100GB


@dataclass
class CacheBlock:
    """A single cache block."""
    
    block_id: int
    data: np.ndarray
    last_access_time: float = field(default_factory=time.time)
    access_count: int = 0
    is_dirty: bool = False  # Modified but not written to disk
    size_bytes: int = 0


@dataclass
class CacheStats:
    """Cache statistics."""
    
    total_blocks: int = 0
    used_blocks: int = 0
    hit_count: int = 0
    miss_count: int = 0
    evictions: int = 0
    disk_reads: int = 0
    disk_writes: int = 0
    total_size_bytes: int = 0
    used_size_bytes: int = 0


class WindowsPagedCache:
    """
    Paged cache optimized for Windows systems.
    
    Features:
    - Memory-mapped file I/O for efficient SSD access
    - LRU eviction policy
    - DirectML buffer compatibility
    - Windows memory pressure handling
    - Async write-back for dirty blocks
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
        block_size_kb: int = DEFAULT_BLOCK_SIZE,
        enable_memory_map: bool = True,
    ):
        """
        Initialize the paged cache.
        
        Args:
            cache_dir: Directory for cache storage
            max_cache_size: Maximum cache size in bytes
            block_size_kb: Block size in KB
            enable_memory_map: Use memory-mapped files
        """
        self.cache_dir = cache_dir or WINDOWS_CACHE_DEFAULT
        self.max_cache_size = max_cache_size
        self.block_size = block_size_kb * 1024  # Convert to bytes
        self.enable_memory_map = enable_memory_map
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Block storage
        self.blocks: Dict[int, CacheBlock] = {}
        self.block_index: Dict[str, Set[int]] = {}  # prefix -> block_ids
        
        # LRU tracking
        self.access_order: List[int] = []
        
        # Memory-mapped files
        self.mapped_files: Dict[str, mmap.mmap] = {}
        
        # Statistics
        self.stats = CacheStats()
        
        # Write-back queue
        self.dirty_blocks: Set[int] = set()
        
        logger.info(f"WindowsPagedCache initialized at {self.cache_dir}")
        logger.info(f"Max cache size: {max_cache_size / (1024**3):.1f}GB")
    
    def _get_block_file(self, block_id: int) -> Path:
        """Get file path for a block."""
        # Distribute blocks across subdirectories to avoid too many files in one dir
        subdir = f"block_{block_id % 1000:03d}"
        return self.cache_dir / subdir / f"block_{block_id}.npy"
    
    def _ensure_subdir(self, block_id: int) -> None:
        """Ensure subdirectory exists."""
        subdir = self.cache_dir / f"block_{block_id % 1000:03d}"
        subdir.mkdir(exist_ok=True)
    
    def get(
        self,
        prefix_hash: str,
        block_idx: int,
    ) -> Optional[np.ndarray]:
        """
        Get a block from cache.
        
        Args:
            prefix_hash: Hash of the prefix
            block_idx: Block index within the prefix
        
        Returns:
            Block data or None if not found
        """
        # Check if prefix exists in index
        if prefix_hash not in self.block_index:
            self.stats.miss_count += 1
            return None
        
        # Calculate global block ID
        block_id = hash(f"{prefix_hash}_{block_idx}") % (2**31)
        
        # Check if block is in memory
        if block_id in self.blocks:
            block = self.blocks[block_id]
            block.last_access_time = time.time()
            block.access_count += 1
            
            # Update LRU order
            if block_id in self.access_order:
                self.access_order.remove(block_id)
            self.access_order.append(block_id)
            
            self.stats.hit_count += 1
            logger.debug(f"Cache hit for block {block_id}")
            return block.data.copy()
        
        # Try to load from disk
        block_file = self._get_block_file(block_id)
        
        if block_file.exists():
            try:
                if self.enable_memory_map and block_file.stat().st_size > 0:
                    # Memory-mapped read
                    data = self._load_mapped(block_file)
                else:
                    # Regular read
                    data = np.load(block_file)
                
                # Add to memory
                self._add_to_memory(block_id, data)
                
                self.stats.disk_reads += 1
                self.stats.hit_count += 1
                logger.debug(f"Cache hit (disk) for block {block_id}")
                return data.copy()
            
            except Exception as e:
                logger.warning(f"Failed to load block {block_id}: {e}")
        
        self.stats.miss_count += 1
        return None
    
    def put(
        self,
        prefix_hash: str,
        block_idx: int,
        data: np.ndarray,
    ) -> None:
        """
        Put a block into cache.
        
        Args:
            prefix_hash: Hash of the prefix
            block_idx: Block index within the prefix
            data: Block data
        """
        # Calculate global block ID
        block_id = hash(f"{prefix_hash}_{block_idx}") % (2**31)
        
        # Check if we need to evict
        current_size = self.stats.used_size_bytes + data.nbytes
        if current_size > self.max_cache_size:
            self._evict_blocks(data.nbytes)
        
        # Add to memory
        self._add_to_memory(block_id, data)
        
        # Update index
        if prefix_hash not in self.block_index:
            self.block_index[prefix_hash] = set()
        self.block_index[prefix_hash].add(block_id)
        
        logger.debug(f"Cached block {block_id} for prefix {prefix_hash[:8]}")
    
    def _add_to_memory(self, block_id: int, data: np.ndarray) -> None:
        """Add block to memory with LRU tracking."""
        size_bytes = data.nbytes
        
        # Create block
        block = CacheBlock(
            block_id=block_id,
            data=data,
            last_access_time=time.time(),
            size_bytes=size_bytes,
        )
        
        # Remove old entry if exists
        if block_id in self.blocks:
            old_block = self.blocks[block_id]
            self.stats.used_size_bytes -= old_block.size_bytes
        
        # Add new block
        self.blocks[block_id] = block
        self.stats.used_size_bytes += size_bytes
        self.stats.used_blocks = len(self.blocks)
        
        # Update LRU order
        if block_id in self.access_order:
            self.access_order.remove(block_id)
        self.access_order.append(block_id)
    
    def _evict_blocks(self, needed_bytes: int) -> None:
        """Evict blocks to make room."""
        bytes_to_free = needed_bytes - (self.max_cache_size - self.stats.used_size_bytes)
        
        if bytes_to_free <= 0:
            return
        
        # Sort by LRU (least recently used first)
        blocks_to_evict = []
        freed_bytes = 0
        
        for block_id in self.access_order:
            if freed_bytes >= bytes_to_free:
                break
            
            if block_id in self.blocks:
                block = self.blocks[block_id]
                
                # Write dirty blocks to disk before evicting
                if block.is_dirty:
                    self._write_block_to_disk(block_id, block.data)
                
                blocks_to_evict.append(block_id)
                freed_bytes += block.size_bytes
        
        # Evict blocks
        for block_id in blocks_to_evict:
            self._evict_block(block_id)
        
        self.stats.evictions += len(blocks_to_evict)
        logger.debug(f"Evicted {len(blocks_to_evict)} blocks")
    
    def _evict_block(self, block_id: int) -> None:
        """Evict a single block."""
        if block_id not in self.blocks:
            return
        
        block = self.blocks[block_id]
        
        # Remove from tracking
        self.blocks.pop(block_id, None)
        if block_id in self.access_order:
            self.access_order.remove(block_id)
        if block_id in self.dirty_blocks:
            self.dirty_blocks.remove(block_id)
        
        # Update stats
        self.stats.used_size_bytes -= block.size_bytes
        self.stats.used_blocks = len(self.blocks)
    
    def _write_block_to_disk(self, block_id: int, data: np.ndarray) -> None:
        """Write a block to disk."""
        try:
            self._ensure_subdir(block_id)
            block_file = self._get_block_file(block_id)
            
            # Write atomically (write to temp, then rename)
            temp_file = block_file.with_suffix(".tmp")
            np.save(temp_file, data)
            temp_file.rename(block_file)
            
            self.stats.disk_writes += 1
            logger.debug(f"Wrote block {block_id} to disk")
        
        except Exception as e:
            logger.error(f"Failed to write block {block_id}: {e}")
    
    def _load_mapped(self, file_path: Path) -> np.ndarray:
        """Load data using memory-mapped file."""
        try:
            # Open file and create memory map
            fd = os.open(str(file_path), os.O_RDONLY)
            file_size = os.fstat(fd).st_size
            
            if file_size == 0:
                os.close(fd)
                return np.array([])
            
            # Create memory map (read-only)
            mm = mmap.mmap(fd, 0, prot=mmap.PROT_READ)
            
            # Load data
            data = np.load(mm, allow_pickle=False)
            
            # Close memory map (but keep data)
            mm.close()
            os.close(fd)
            
            return data
        
        except Exception as e:
            logger.warning(f"Memory-mapped read failed: {e}, falling back to regular read")
            return np.load(file_path)
    
    def flush(self) -> None:
        """Flush all dirty blocks to disk."""
        if not self.dirty_blocks:
            return
        
        logger.info(f"Flushing {len(self.dirty_blocks)} dirty blocks to disk")
        
        for block_id in list(self.dirty_blocks):
            if block_id in self.blocks:
                block = self.blocks[block_id]
                self._write_block_to_disk(block_id, block.data)
                block.is_dirty = False
        
        self.dirty_blocks.clear()
        logger.info("Cache flush complete")
    
    def clear(self) -> None:
        """Clear all cache."""
        logger.info("Clearing all cache")
        
        # Flush dirty blocks first
        self.flush()
        
        # Clear memory
        self.blocks.clear()
        self.block_index.clear()
        self.access_order.clear()
        self.dirty_blocks.clear()
        
        # Clear stats
        self.stats = CacheStats()
        
        # Close memory-mapped files
        for mm in self.mapped_files.values():
            try:
                mm.close()
            except Exception:
                pass
        self.mapped_files.clear()
        
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = 0.0
        if self.stats.hit_count + self.stats.miss_count > 0:
            hit_rate = self.stats.hit_count / (self.stats.hit_count + self.stats.miss_count)
        
        return {
            "total_blocks": self.stats.total_blocks,
            "used_blocks": self.stats.used_blocks,
            "hit_count": self.stats.hit_count,
            "miss_count": self.stats.miss_count,
            "hit_rate": hit_rate,
            "evictions": self.stats.evictions,
            "disk_reads": self.stats.disk_reads,
            "disk_writes": self.stats.disk_writes,
            "total_size_bytes": self.stats.total_size_bytes,
            "used_size_bytes": self.stats.used_size_bytes,
            "used_size_gb": self.stats.used_size_bytes / (1024 ** 3),
            "max_size_gb": self.max_cache_size / (1024 ** 3),
            "dirty_blocks": len(self.dirty_blocks),
        }
    
    def shutdown(self) -> None:
        """Shutdown cache and cleanup."""
        logger.info("Shutting down cache")
        
        # Flush all dirty blocks
        self.flush()
        
        # Close memory-mapped files
        for mm in self.mapped_files.values():
            try:
                mm.close()
            except Exception:
                pass
        
        logger.info("Cache shutdown complete")
    
    def mark_dirty(self, block_id: int) -> None:
        """Mark a block as dirty (modified)."""
        if block_id in self.blocks:
            self.blocks[block_id].is_dirty = True
            self.dirty_blocks.add(block_id)
    
    def get_cache_dir(self) -> Path:
        """Get cache directory."""
        return self.cache_dir


class WindowsCacheManager:
    """
    Manager for Windows paged cache.
    
    Handles:
    - Multiple cache instances
    - Memory pressure monitoring
    - Automatic cleanup
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Cache directory
            max_cache_size: Maximum cache size in bytes
        """
        self.cache = WindowsPagedCache(
            cache_dir=cache_dir,
            max_cache_size=max_cache_size,
        )
        
        # Memory pressure monitoring
        self.memory_threshold = 0.9  # Trigger eviction at 90% memory usage
        
        logger.info("WindowsCacheManager initialized")
    
    def get(self, prefix_hash: str, block_idx: int) -> Optional[np.ndarray]:
        """Get block from cache."""
        return self.cache.get(prefix_hash, block_idx)
    
    def put(self, prefix_hash: str, block_idx: int, data: np.ndarray) -> None:
        """Put block into cache."""
        self.cache.put(prefix_hash, block_idx, data)
    
    def check_memory_pressure(self) -> bool:
        """
        Check if system is under memory pressure.
        
        Returns:
            True if under pressure
        """
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            usage_ratio = memory.percent / 100.0
            
            if usage_ratio > self.memory_threshold:
                logger.warning(f"Memory pressure detected: {memory.percent:.1f}%")
                return True
            
            return False
        
        except Exception:
            return False
    
    def handle_memory_pressure(self) -> None:
        """Handle memory pressure by evicting blocks."""
        if not self.check_memory_pressure():
            return
        
        # Aggressive eviction - free 50% of cache
        target_size = self.cache.max_cache_size * 0.5
        
        while self.cache.stats.used_size_bytes > target_size:
            if self.cache.access_order:
                block_id = self.cache.access_order[0]
                self.cache._evict_block(block_id)
            else:
                break
        
        logger.info("Handled memory pressure")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def flush(self) -> None:
        """Flush cache to disk."""
        self.cache.flush()
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
    
    def shutdown(self) -> None:
        """Shutdown cache manager."""
        self.cache.shutdown()
