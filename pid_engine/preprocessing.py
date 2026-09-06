from __future__ import annotations
from pathlib import Path
from typing import Any

def load_image(path: str) -> Any:
    """Load an image with OpenCV. PDF conversion is intentionally separate."""
    import cv2
    image = cv2.imread(str(Path(path)))
    if image is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return image

def preprocess_image(image: Any, scale: float = 1.0) -> Any:
    # Allows injected detector tests/demos to run without an actual image.
    if image is None:
        return None
    import cv2
    if scale != 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Preserve line structure while reducing scanner noise.
    return cv2.bilateralFilter(gray, 5, 50, 50)
