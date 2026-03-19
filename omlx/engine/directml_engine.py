# SPDX-License-Identifier: Apache-2.0
"""
DirectML/ONNX inference engine for Windows.

This module provides Windows-optimized inference using:
- ONNX Runtime with DirectML for GPU acceleration
- llama-cpp-python for GGUF format support
- OpenVINO for Intel hardware (optional)
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    import onnxruntime as ort
    from onnxruntime import InferenceSession, SessionOptions, GraphOptimizationLevel
    
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    ort = None
    InferenceSession = None

try:
    from llama_cpp import Llama
    
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False
    Llama = None

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


@dataclass
class EngineConfig:
    """Configuration for Windows inference engine."""
    
    backend: str = "auto"  # "auto", "cuda", "directml", "openvino", "cpu", "gguf"
    max_context_length: int = 4096
    max_batch_size: int = 8
    gpu_id: int = 0
    enable_memory_efficient_attention: bool = True
    enable_graph_optimization: bool = True
    num_threads: int = 0  # 0 = auto-detect


@dataclass
class SamplingParams:
    """Generation parameters."""
    
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repeat_penalty: float = 1.1
    stop_sequences: List[str] = field(default_factory=list)


@dataclass
class RequestOutput:
    """Output from a generation request."""
    
    request_id: str
    text: str = ""
    tokens: List[int] = field(default_factory=list)
    finished: bool = False
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class DirectMLEngine:
    """
    DirectML/ONNX inference engine for Windows.
    
    Supports multiple backends:
    - ONNX Runtime with DirectML (AMD/Intel GPUs)
    - ONNX Runtime with CUDA (NVIDIA GPUs)
    - llama-cpp-python (GGUF models)
    - Transformers (CPU fallback)
    """
    
    def __init__(
        self,
        model_path: str,
        config: Optional[EngineConfig] = None,
        engine_id: Optional[str] = None,
    ):
        """
        Initialize the engine.
        
        Args:
            model_path: Path to model file or directory
            config: Engine configuration
            engine_id: Unique engine ID
        """
        self.model_path = Path(model_path)
        self.config = config or EngineConfig()
        self._engine_id = engine_id or str(uuid.uuid4())
        self._model = None
        self._tokenizer = None
        self._session: Optional[InferenceSession] = None
        
        # Auto-detect backend
        if self.config.backend == "auto":
            self.config.backend = self._detect_backend()
        
        logger.info(f"Using backend: {self.config.backend}")
        
    def _detect_backend(self) -> str:
        """Auto-detect best available backend."""
        
        # Check for GGUF model
        if self.model_path.suffix.lower() == ".gguf":
            return "gguf"
        
        # Check for ONNX model
        if self.model_path.suffix.lower() == ".onnx":
            # Prefer CUDA if available
            if self._is_cuda_available():
                return "cuda"
            # Fall back to DirectML
            if self._is_directml_available():
                return "directml"
            return "cpu"
        
        # Transformers model directory
        if self.model_path.is_dir():
            if self._is_cuda_available():
                return "cuda"
            return "cpu"
        
        logger.warning("Unknown model format, defaulting to GGUF")
        return "gguf"
    
    def _is_cuda_available(self) -> bool:
        """Check if CUDA is available."""
        if not HAS_ONNX:
            return False
        
        try:
            providers = ort.get_available_providers()
            return "CUDAExecutionProvider" in providers
        except Exception:
            return False
    
    def _is_directml_available(self) -> bool:
        """Check if DirectML is available."""
        if not HAS_ONNX:
            return False
        
        try:
            providers = ort.get_available_providers()
            return "DirectMLExecutionProvider" in providers
        except Exception:
            return False
    
    def load_model(self) -> None:
        """Load the model into memory."""
        logger.info(f"Loading model from {self.model_path}")
        
        backend = self.config.backend
        
        if backend == "gguf":
            self._load_gguf_model()
        elif backend in ("cuda", "directml", "cpu"):
            self._load_onnx_model()
        elif backend == "cuda":
            self._load_transformers_model()
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        logger.info("Model loaded successfully")
    
    def _load_gguf_model(self) -> None:
        """Load GGUF model using llama-cpp-python."""
        if not HAS_LLAMA_CPP:
            raise ImportError(
                "llama-cpp-python not installed. "
                "Install with: pip install llama-cpp-python"
            )
        
        # Determine device
        n_gpu_layers = -1 if self._is_cuda_available() else 0
        
        self._model = Llama(
            model_path=str(self.model_path),
            n_ctx=self.config.max_context_length,
            n_batch=self.config.max_batch_size,
            n_gpu_layers=n_gpu_layers,
            n_threads=self.config.num_threads or 0,
            verbose=False,
        )
        
        # GGUF models include tokenizer
        self._tokenizer = None
    
    def _load_onnx_model(self) -> None:
        """Load ONNX model with DirectML/CUDA."""
        if not HAS_ONNX:
            raise ImportError(
                "onnxruntime not installed. "
                "Install with: pip install onnxruntime-directml"
            )
        
        # Configure session options
        session_options = SessionOptions()
        
        if self.config.enable_graph_optimization:
            session_options.graph_optimization_level = GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Select execution provider
        if self.config.backend == "cuda":
            providers = [
                ("CUDAExecutionProvider", {"device_id": self.config.gpu_id}),
                "CPUExecutionProvider"
            ]
        elif self.config.backend == "directml":
            providers = [
                ("DirectMLExecutionProvider", {"device_id": self.config.gpu_id}),
                "CPUExecutionProvider"
            ]
        else:
            providers = ["CPUExecutionProvider"]
        
        # Create inference session
        self._session = InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=providers,
        )
        
        # Load tokenizer
        self._load_tokenizer()
    
    def _load_transformers_model(self) -> None:
        """Load Transformers model for CUDA."""
        if not HAS_TRANSFORMERS:
            raise ImportError(
                "transformers not installed. "
                "Install with: pip install transformers accelerate"
            )
        
        import torch
        
        # Determine device and dtype
        device = f"cuda:{self.config.gpu_id}" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        
        # Load model
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=dtype,
            device_map="auto" if device.startswith("cuda") else None,
            trust_remote_code=True,
        )
        
        self._load_tokenizer()
    
    def _load_tokenizer(self) -> None:
        """Load tokenizer from model directory or HuggingFace."""
        if not HAS_TRANSFORMERS:
            logger.warning("Transformers not available, using basic tokenizer")
            return
        
        try:
            # Try loading from model directory
            tokenizer_path = self.model_path.parent if self.model_path.is_file() else self.model_path
            self._tokenizer = AutoTokenizer.from_pretrained(
                str(tokenizer_path),
                trust_remote_code=True,
            )
        except Exception as e:
            logger.warning(f"Failed to load tokenizer: {e}")
            self._tokenizer = None
    
    def generate(
        self,
        prompt: Union[str, List[int]],
        sampling_params: Optional[SamplingParams] = None,
        request_id: Optional[str] = None,
        stream: bool = False,
    ) -> Union[RequestOutput, AsyncIterator[RequestOutput]]:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt (text or token IDs)
            sampling_params: Generation parameters
            request_id: Optional request ID
            stream: Whether to stream output
        
        Returns:
            RequestOutput or async generator
        """
        request_id = request_id or str(uuid.uuid4())
        sampling_params = sampling_params or SamplingParams()
        
        if stream:
            return self._generate_stream(prompt, sampling_params, request_id)
        else:
            return self._generate_sync(prompt, sampling_params, request_id)
    
    def _generate_sync(
        self,
        prompt: Union[str, List[int]],
        sampling_params: SamplingParams,
        request_id: str,
    ) -> RequestOutput:
        """Synchronous generation."""
        start_time = time.time()
        
        try:
            if self.config.backend == "gguf":
                text = self._generate_gguf(prompt, sampling_params)
            elif self.config.backend in ("cuda", "directml", "cpu"):
                text = self._generate_onnx(prompt, sampling_params)
            else:
                text = self._generate_transformers(prompt, sampling_params)
            
            # Count tokens
            input_tokens = 0
            output_tokens = 0
            
            if self._tokenizer:
                input_tokens = len(self._tokenizer.encode(prompt if isinstance(prompt, str) else ""))
                output_tokens = len(self._tokenizer.encode(text))
            
            return RequestOutput(
                request_id=request_id,
                text=text,
                finished=True,
                finish_reason="stop",
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
            )
        
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return RequestOutput(
                request_id=request_id,
                error=str(e),
                finished=True,
                finish_reason="error",
            )
    
    def _generate_gguf(
        self,
        prompt: Union[str, List[int]],
        sampling_params: SamplingParams,
    ) -> str:
        """Generate using llama-cpp-python."""
        if isinstance(prompt, list):
            prompt = self._model.tokenizer().decode(prompt)
        
        output = self._model(
            prompt,
            max_tokens=sampling_params.max_tokens,
            temperature=sampling_params.temperature,
            top_p=sampling_params.top_p,
            top_k=sampling_params.top_k,
            repeat_penalty=sampling_params.repeat_penalty,
            stop=sampling_params.stop_sequences,
        )
        
        return output["choices"][0]["text"]
    
    def _generate_onnx(
        self,
        prompt: Union[str, List[int]],
        sampling_params: SamplingParams,
    ) -> str:
        """Generate using ONNX Runtime."""
        if not self._session:
            raise RuntimeError("Model not loaded")
        
        # Tokenize input
        if isinstance(prompt, str):
            if self._tokenizer:
                inputs = self._tokenizer(prompt, return_tensors="np")
                input_ids = inputs["input_ids"].astype(np.int64)
                attention_mask = inputs["attention_mask"].astype(np.int64)
            else:
                # Basic tokenization fallback
                input_ids = np.array([[ord(c) for c in prompt]], dtype=np.int64)
                attention_mask = np.ones_like(input_ids)
        else:
            input_ids = np.array([prompt], dtype=np.int64)
            attention_mask = np.ones_like(input_ids)
        
        # Prepare inputs for ONNX model
        ort_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        
        # Run inference
        outputs = self._session.run(None, ort_inputs)
        
        # Extract generated text
        if len(outputs) > 0:
            logits = outputs[0]
            next_token = np.argmax(logits[:, -1, :], axis=-1)[0]
            
            if self._tokenizer:
                return self._tokenizer.decode([next_token], skip_special_tokens=True)
            else:
                return chr(next_token)
        
        return ""
    
    def _generate_transformers(
        self,
        prompt: Union[str, List[int]],
        sampling_params: SamplingParams,
    ) -> str:
        """Generate using Transformers."""
        if not self._model or not self._tokenizer:
            raise RuntimeError("Model not loaded")
        
        import torch
        
        # Tokenize
        inputs = self._tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"]
        attention_mask = inputs["attention_mask"]
        
        # Generate
        with torch.no_grad():
            outputs = self._model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=sampling_params.max_tokens,
                temperature=sampling_params.temperature if sampling_params.temperature > 0 else 1.0,
                top_p=sampling_params.top_p,
                top_k=sampling_params.top_k,
                repetition_penalty=sampling_params.repeat_penalty,
                do_sample=sampling_params.temperature > 0,
            )
        
        # Decode
        generated_ids = outputs[0][input_ids.shape[1]:]
        return self._tokenizer.decode(generated_ids, skip_special_tokens=True)
    
    async def _generate_stream(
        self,
        prompt: Union[str, List[int]],
        sampling_params: SamplingParams,
        request_id: str,
    ) -> AsyncIterator[RequestOutput]:
        """Streaming generation."""
        # For now, implement simple chunked streaming
        # Can be enhanced with true token-by-token streaming
        
        output = self._generate_sync(prompt, sampling_params, request_id)
        
        # Stream in chunks
        chunk_size = 10
        text = output.text
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield RequestOutput(
                request_id=request_id,
                new_text=chunk,
                text=text[:i + chunk_size],
                finished=(i + chunk_size >= len(text)),
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        stats = {
            "backend": self.config.backend,
            "model_path": str(self.model_path),
            "max_context_length": self.config.max_context_length,
            "max_batch_size": self.config.max_batch_size,
        }
        
        # Add GPU memory info if available
        if self.config.backend == "cuda":
            try:
                import torch
                
                if torch.cuda.is_available():
                    stats["gpu_memory_allocated"] = torch.cuda.memory_allocated()
                    stats["gpu_memory_reserved"] = torch.cuda.memory_reserved()
            except Exception:
                pass
        
        return stats
