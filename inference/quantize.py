"""
BharatDoc-VLM: Quantisation Module
=====================================

IMPORTANT: 4-bit quantisation via bitsandbytes requires CUDA.
This module provides a stub implementation for CPU-only environments.

For CPU-friendly quantised inference, use:
- llama-cpp-python with GGUF format models
- ONNX Runtime with INT8 quantisation
- OpenVINO for Intel CPU acceleration

When running on GPU, uncomment bitsandbytes in requirements.txt and
set use_quantization=true in config.yaml.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def check_gpu_available() -> bool:
    """Check if CUDA GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def quantize_model(model_name: str, bits: int = 4, use_real: bool = False):
    """
    Quantize a model for efficient inference.
    
    On GPU (CUDA): Uses bitsandbytes for 4-bit NF4 quantisation
    On CPU: Returns a stub that logs a warning
    
    Args:
        model_name: HuggingFace model name
        bits: Quantisation bits (4 or 8)
        use_real: Force real quantisation (requires GPU)
    """
    if not use_real or not check_gpu_available():
        logger.info(f"Quantisation stub: {model_name} ({bits}-bit)")
        logger.info("  GPU not available. For CPU inference, consider:")
        logger.info("  1. llama-cpp-python with GGUF models (recommended)")
        logger.info("  2. ONNX Runtime INT8 quantisation")
        logger.info("  3. torch.quantization for PyTorch models")
        return MockQuantizedModel(model_name, bits)

    # Real GPU quantisation path
    try:
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig
        import torch

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=(bits == 4),
            load_in_8bit=(bits == 8),
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
        )
        logger.info(f"Model quantized: {model_name} ({bits}-bit via bitsandbytes)")
        return model

    except ImportError as e:
        logger.error(f"bitsandbytes not installed: {e}")
        return MockQuantizedModel(model_name, bits)


class MockQuantizedModel:
    """Stub quantized model for CPU environments."""

    def __init__(self, model_name: str, bits: int):
        self.model_name = model_name
        self.bits = bits
        self.is_mock = True
        logger.info(f"MockQuantizedModel created: {model_name} ({bits}-bit stub)")

    def generate(self, **kwargs):
        """Mock generation."""
        return ["Mock quantized output — use GPU for real inference"]

    def __repr__(self):
        return f"MockQuantizedModel({self.model_name}, {self.bits}-bit)"


# CPU-friendly alternative using llama-cpp-python (reference implementation)
def load_gguf_model(model_path: str, n_ctx: int = 2048):
    """
    Load a GGUF quantized model for CPU inference.
    
    This is the recommended approach for CPU-only deployment.
    Download GGUF models from: https://huggingface.co/models?search=gguf
    
    Example:
        model = load_gguf_model("models/phi-2-q4_k_m.gguf")
        output = model("Extract fields from this document")
    """
    try:
        from llama_cpp import Llama
        model = Llama(model_path=model_path, n_ctx=n_ctx)
        logger.info(f"GGUF model loaded: {model_path}")
        return model
    except ImportError:
        logger.warning("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model = quantize_model("microsoft/phi-2", bits=4)
    print(f"Quantized model: {model}")
