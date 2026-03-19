# SPDX-License-Identifier: Apache-2.0
"""
Performance benchmarking tool for oMLX Windows.

Provides comprehensive benchmarks for:
- Token generation speed (tokens/s)
- Time to first token (TTFT)
- Memory usage
- GPU utilization
- Model loading time
"""

import json
import logging
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    
    model_path: str
    backend: str = "auto"
    context_length: int = 512
    generate_tokens: int = 256
    num_runs: int = 3
    warmup_runs: int = 1
    prompt: str = "The quick brown fox jumps over the lazy dog."


@dataclass
class BenchmarkResult:
    """Benchmark result for a single run."""
    
    run_id: int
    model_loading_time: float = 0.0
    time_to_first_token: float = 0.0
    total_generation_time: float = 0.0
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    peak_memory_mb: float = 0.0
    gpu_memory_mb: float = 0.0
    error: Optional[str] = None


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    
    model_name: str
    backend: str
    timestamp: str
    system_info: Dict[str, Any]
    config: BenchmarkConfig
    results: List[BenchmarkResult] = field(default_factory=list)
    
    # Aggregated metrics
    avg_tokens_per_second: float = 0.0
    avg_ttft: float = 0.0
    peak_memory_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "backend": self.backend,
            "timestamp": self.timestamp,
            "system_info": self.system_info,
            "config": {
                "model_path": self.config.model_path,
                "backend": self.config.backend,
                "context_length": self.config.context_length,
                "generate_tokens": self.config.generate_tokens,
            },
            "results": [
                {
                    "run_id": r.run_id,
                    "model_loading_time": r.model_loading_time,
                    "time_to_first_token": r.time_to_first_token,
                    "total_generation_time": r.total_generation_time,
                    "tokens_generated": r.tokens_generated,
                    "tokens_per_second": r.tokens_per_second,
                    "peak_memory_mb": r.peak_memory_mb,
                    "gpu_memory_mb": r.gpu_memory_mb,
                    "error": r.error,
                }
                for r in self.results
            ],
            "aggregated": {
                "avg_tokens_per_second": self.avg_tokens_per_second,
                "avg_ttft": self.avg_ttft,
                "peak_memory_mb": self.peak_memory_mb,
            },
        }


class WindowsBenchmark:
    """
    Performance benchmark for oMLX Windows.
    """
    
    def __init__(self, config: BenchmarkConfig):
        """
        Initialize benchmark.
        
        Args:
            config: Benchmark configuration
        """
        self.config = config
        self.report = BenchmarkReport(
            model_name=Path(config.model_path).name,
            backend=config.backend,
            timestamp=datetime.now().isoformat(),
            system_info=self._get_system_info(),
            config=config,
        )
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        }
        
        # Get GPU info
        try:
            import psutil
            
            # Get memory info
            memory = psutil.virtual_memory()
            info["total_ram_gb"] = memory.total / (1024 ** 3)
            info["available_ram_gb"] = memory.available / (1024 ** 3)
        
        except Exception:
            pass
        
        # Get NVIDIA GPU info if available
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info["gpu_name"] = pynvml.nvmlDeviceGetName(handle)
                info["gpu_memory_gb"] = (
                    pynvml.nvmlDeviceGetMemoryInfo(handle).total / (1024 ** 3)
                )
            
            pynvml.nvmlShutdown()
        except Exception:
            pass
        
        return info
    
    def run(self) -> BenchmarkReport:
        """
        Run all benchmark iterations.
        
        Returns:
            Complete benchmark report
        """
        logger.info(f"Starting benchmark for {self.config.model_path}")
        logger.info(f"Backend: {self.config.backend}")
        logger.info(f"Running {self.config.warmup_runs} warmup runs")
        logger.info(f"Running {self.config.num_runs} benchmark runs")
        
        # Warmup runs
        for i in range(self.config.warmup_runs):
            logger.info(f"Warmup run {i + 1}/{self.config.warmup_runs}")
            try:
                self._run_benchmark(warmup=True)
            except Exception as e:
                logger.warning(f"Warmup failed: {e}")
        
        # Benchmark runs
        for i in range(self.config.num_runs):
            logger.info(f"Benchmark run {i + 1}/{self.config.num_runs}")
            
            result = self._run_benchmark(warmup=False)
            self.report.results.append(result)
            
            if result.error:
                logger.error(f"Benchmark run failed: {result.error}")
            else:
                logger.info(
                    f"Tokens/s: {result.tokens_per_second:.2f}, "
                    f"TTFT: {result.time_to_first_token:.3f}s"
                )
        
        # Calculate aggregated metrics
        self._calculate_aggregates()
        
        return self.report
    
    def _run_benchmark(self, warmup: bool = False) -> BenchmarkResult:
        """
        Run a single benchmark iteration.
        
        Args:
            warmup: If True, don't record results
        
        Returns:
            Benchmark result
        """
        result = BenchmarkResult(run_id=0 if warmup else len(self.report.results) + 1)
        
        start_time = time.time()
        
        try:
            # Load model
            model_load_start = time.time()
            engine = self._load_engine()
            model_load_end = time.time()
            result.model_loading_time = model_load_end - model_load_start
            
            # Get initial memory
            result.peak_memory_mb = self._get_memory_usage()
            
            # Generate first token (TTFT)
            ttft_start = time.time()
            first_token = self._generate_first_token(engine)
            ttft_end = time.time()
            result.time_to_first_token = ttft_end - ttft_start
            
            # Generate remaining tokens
            gen_start = time.time()
            tokens = self._generate_remaining_tokens(engine, first_token)
            gen_end = time.time()
            
            result.total_generation_time = gen_end - gen_start
            result.tokens_generated = len(tokens)
            result.tokens_per_second = (
                result.tokens_generated / result.total_generation_time
                if result.total_generation_time > 0
                else 0.0
            )
            
            # Get peak memory
            result.peak_memory_mb = max(
                result.peak_memory_mb,
                self._get_memory_usage()
            )
            
            # Get GPU memory if available
            result.gpu_memory_mb = self._get_gpu_memory()
        
        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            result.error = str(e)
        
        return result
    
    def _load_engine(self):
        """Load inference engine."""
        from .engine.directml_engine import DirectMLEngine, EngineConfig
        
        config = EngineConfig(
            backend=self.config.backend,
            max_context_length=self.config.context_length,
        )
        
        return DirectMLEngine(self.config.model_path, config=config)
    
    def _generate_first_token(self, engine) -> List[int]:
        """Generate first token."""
        from .engine.directml_engine import SamplingParams
        
        params = SamplingParams(
            max_tokens=1,
            temperature=0,
        )
        
        output = engine.generate(
            prompt=self.config.prompt,
            sampling_params=params,
            stream=False,
        )
        
        # Return token IDs
        if output.tokens:
            return output.tokens
        elif output.text:
            # Fallback: tokenize text
            return [ord(c) for c in output.text]
        return []
    
    def _generate_remaining_tokens(self, engine, initial_tokens: List[int]) -> List[int]:
        """Generate remaining tokens."""
        from .engine.directml_engine import SamplingParams
        
        params = SamplingParams(
            max_tokens=self.config.generate_tokens - len(initial_tokens),
            temperature=0.7,
            top_p=0.9,
        )
        
        # Continue from initial tokens
        output = engine.generate(
            prompt=self.config.prompt,
            sampling_params=params,
            stream=False,
        )
        
        if output.tokens:
            return initial_tokens + output.tokens
        elif output.text:
            return initial_tokens + [ord(c) for c in output.text]
        return initial_tokens
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return memory_info.rss / (1024 ** 2)  # Convert to MB
        
        except Exception:
            return 0.0
    
    def _get_gpu_memory(self) -> float:
        """Get GPU memory usage in MB."""
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                used_mb = memory_info.used / (1024 ** 2)
                pynvml.nvmlShutdown()
                return used_mb
            
            pynvml.nvmlShutdown()
        except Exception:
            pass
        
        return 0.0
    
    def _calculate_aggregates(self) -> None:
        """Calculate aggregated metrics."""
        valid_results = [r for r in self.report.results if not r.error]
        
        if not valid_results:
            return
        
        # Average tokens per second
        self.report.avg_tokens_per_second = (
            sum(r.tokens_per_second for r in valid_results) / len(valid_results)
        )
        
        # Average TTFT
        self.report.avg_ttft = (
            sum(r.time_to_first_token for r in valid_results) / len(valid_results)
        )
        
        # Peak memory
        self.report.peak_memory_mb = max(r.peak_memory_mb for r in valid_results)
    
    def save_report(self, output_path: Path) -> None:
        """
        Save benchmark report to file.
        
        Args:
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report.to_dict(), f, indent=2)
        
        logger.info(f"Benchmark report saved to {output_path}")
    
    def print_summary(self) -> None:
        """Print benchmark summary."""
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        print(f"Model: {self.report.model_name}")
        print(f"Backend: {self.report.backend}")
        print(f"Timestamp: {self.report.timestamp}")
        print()
        print("System:")
        for key, value in self.report.system_info.items():
            print(f"  {key}: {value}")
        print()
        print("Results:")
        print(f"  Runs: {len(self.report.results)}")
        print(f"  Avg Tokens/s: {self.report.avg_tokens_per_second:.2f}")
        print(f"  Avg TTFT: {self.report.avg_ttft:.3f}s")
        print(f"  Peak Memory: {self.report.peak_memory_mb:.1f} MB")
        print()
        
        # Per-run details
        print("Per-run details:")
        for i, result in enumerate(self.report.results, 1):
            if result.error:
                print(f"  Run {i}: FAILED - {result.error}")
            else:
                print(
                    f"  Run {i}: {result.tokens_per_second:.2f} t/s, "
                    f"TTFT: {result.time_to_first_token:.3f}s, "
                    f"Memory: {result.peak_memory_mb:.1f} MB"
                )
        
        print("="*70 + "\n")


def run_benchmark(
    model_path: str,
    backend: str = "auto",
    context_length: int = 512,
    generate_tokens: int = 256,
    num_runs: int = 3,
    output_file: Optional[str] = None,
) -> BenchmarkReport:
    """
    Run benchmark with specified parameters.
    
    Args:
        model_path: Path to model
        backend: Inference backend
        context_length: Context length
        generate_tokens: Number of tokens to generate
        num_runs: Number of benchmark runs
        output_file: Optional output file path
    
    Returns:
        Benchmark report
    """
    config = BenchmarkConfig(
        model_path=model_path,
        backend=backend,
        context_length=context_length,
        generate_tokens=generate_tokens,
        num_runs=num_runs,
    )
    
    benchmark = WindowsBenchmark(config)
    report = benchmark.run()
    benchmark.print_summary()
    
    if output_file:
        benchmark.save_report(Path(output_file))
    
    return report


def main():
    """CLI for benchmark."""
    import argparse
    
    parser = argparse.ArgumentParser(description="oMLX Windows Performance Benchmark")
    parser.add_argument(
        "model_path",
        type=str,
        help="Path to model file or directory"
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="auto",
        choices=["auto", "cuda", "directml", "openvino", "cpu", "gguf"],
        help="Inference backend (default: auto)"
    )
    parser.add_argument(
        "--context-length",
        type=int,
        default=512,
        help="Context length (default: 512)"
    )
    parser.add_argument(
        "--generate-tokens",
        type=int,
        default=256,
        help="Number of tokens to generate (default: 256)"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of benchmark runs (default: 3)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Number of warmup runs (default: 1)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (JSON)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Run benchmark
    report = run_benchmark(
        model_path=args.model_path,
        backend=args.backend,
        context_length=args.context_length,
        generate_tokens=args.generate_tokens,
        num_runs=args.runs,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
