import os

# NumPy 1.26.4 + SciPy 1.14+ compatibility patch for PaddleX / PaddleOCR
try:
    import numpy as _np
    if not hasattr(_np, "long"):
        _np.long = _np.int_
    if not hasattr(_np, "ulong"):
        _np.ulong = _np.uint
except ImportError:
    pass

# Disable OneDNN in PaddleX to avoid PIR attribute crashes on CPU
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from rag.config import config, RAGConfig

__version__ = "1.0.0"
__all__ = ["config", "RAGConfig"]
