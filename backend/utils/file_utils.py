"""
backend/utils/file_utils.py

Shared file-handling helpers: safe filename generation and extension/size
validation. Kept dependency-free so it's usable from any layer.
"""
import re
import uuid
from pathlib import Path
from typing import Tuple


def sanitize_filename(original_name: str) -> str:
    """
    Strip path components and unsafe characters, prefix with a UUID to avoid
    collisions and directory traversal via crafted filenames.
    """
    base = Path(original_name).name  # drop any directory components
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    if not base:
        base = "file"
    return f"{uuid.uuid4().hex}_{base}"


def validate_extension(filename: str, allowed_extensions: list[str]) -> Tuple[bool, str]:
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return False, f"File extension '{ext}' not allowed. Allowed: {', '.join(allowed_extensions)}"
    return True, ""


def validate_size(size_bytes: int, max_bytes: int) -> Tuple[bool, str]:
    if size_bytes > max_bytes:
        mb = max_bytes / (1024 * 1024)
        return False, f"File exceeds max upload size of {mb:.0f} MB"
    return True, ""
