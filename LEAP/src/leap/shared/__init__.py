"""Shared configuration and device utilities."""

from .config import load_json_config
from .device import select_device

__all__ = ["load_json_config", "select_device"]
