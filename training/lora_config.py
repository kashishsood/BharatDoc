"""
BharatDoc-VLM: Shared LoRA Configuration
==========================================

Centralised LoRA (Low-Rank Adaptation) configuration applied to all models.
Uses PEFT library for parameter-efficient fine-tuning.

Why LoRA with these settings:
- r=16: Good balance between expressiveness and parameter count
- target q_proj/v_proj: Attention projections capture task-specific patterns
  while keeping FFN weights frozen (prevents catastrophic forgetting)
- lora_alpha=32 (2x r): Standard scaling factor for stable training
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


def load_lora_config(config_path: Optional[str] = None) -> dict:
    """Load LoRA settings from the central config.yaml."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent / "config.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("lora", {})


def get_peft_config(config_path: Optional[str] = None, task_type: Optional[str] = None):
    """
    Create a PEFT LoraConfig object from our config.yaml.
    
    Returns the config object, or a dict if peft is not installed.
    """
    lora_cfg = load_lora_config(config_path)
    
    config_dict = {
        "r": lora_cfg.get("r", 16),
        "lora_alpha": lora_cfg.get("lora_alpha", 32),
        "lora_dropout": lora_cfg.get("lora_dropout", 0.05),
        "target_modules": lora_cfg.get("target_modules", ["q_proj", "v_proj"]),
        "bias": lora_cfg.get("bias", "none"),
        "task_type": task_type or lora_cfg.get("task_type", "CAUSAL_LM"),
    }

    try:
        from peft import LoraConfig
        peft_config = LoraConfig(**config_dict)
        logger.info(f"Created LoRA config: r={config_dict['r']}, alpha={config_dict['lora_alpha']}, "
                     f"targets={config_dict['target_modules']}")
        return peft_config
    except ImportError:
        logger.warning("PEFT not installed, returning config dict")
        return config_dict


def apply_lora_to_model(model, config_path: Optional[str] = None,
                         task_type: Optional[str] = None):
    """
    Apply LoRA adapters to any HuggingFace model.
    
    This is the single function all training scripts call to add LoRA.
    Keeps LoRA application consistent across Donut, TrOCR, LayoutLM, etc.
    """
    try:
        from peft import get_peft_model
        peft_config = get_peft_config(config_path, task_type)
        if not hasattr(peft_config, 'r'):
            logger.warning("PEFT config is a dict (library not installed), skipping LoRA")
            return model
        
        lora_model = get_peft_model(model, peft_config)
        trainable = sum(p.numel() for p in lora_model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in lora_model.parameters())
        pct = 100 * trainable / total if total > 0 else 0
        logger.info(f"LoRA applied: {trainable:,} trainable / {total:,} total ({pct:.2f}%)")
        return lora_model
    except ImportError:
        logger.warning("PEFT not installed, returning model without LoRA")
        return model


def print_trainable_parameters(model) -> dict:
    """Print and return trainable parameter statistics."""
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    pct = 100 * trainable / total if total > 0 else 0
    stats = {"trainable": trainable, "total": total, "percentage": round(pct, 2)}
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({pct:.2f}%)")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = get_peft_config()
    print(f"LoRA config: {cfg}")
