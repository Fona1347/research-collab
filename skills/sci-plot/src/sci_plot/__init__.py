"""Sci Plot: deterministic, safe scientific figure generation."""

__version__ = "0.3.0"

from .render import AppliedStyle, project_style
from .delivery import capture_inputs, export_and_audit, verify_bundle

__all__ = ["AppliedStyle", "__version__", "project_style", "capture_inputs", "export_and_audit", "verify_bundle"]
