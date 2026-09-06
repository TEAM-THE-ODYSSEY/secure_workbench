from __future__ import annotations
from typing import Any, Iterable
from .models import SymbolDetection

class SymbolDetector:
    """
    Adapter around YOLO. The class is deliberately model-agnostic:
    pass a trained YOLO weights path, or inject detections during tests.
    """
    def __init__(self, weights: str | None = None, conf: float = 0.25):
        self.weights = weights
        self.conf = conf
        self._model = None

    def _load(self):
        if self._model is None:
            if not self.weights:
                raise RuntimeError("No YOLO weights supplied. Use inject_detections() for tests.")
            from ultralytics import YOLO
            self._model = YOLO(self.weights)
        return self._model

    def detect(self, image: Any) -> list[SymbolDetection]:
        model = self._load()
        result = model.predict(image, conf=self.conf, verbose=False)[0]
        names = result.names
        detections = []
        for i, box in enumerate(result.boxes):
            xyxy = box.xyxy[0].tolist()
            cls = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            detections.append(SymbolDetection(
                object_id=f"obj{i+1}",
                object_type=str(names[cls]),
                bbox=tuple(map(float, xyxy)),
                confidence=conf,
            ))
        return detections

    @staticmethod
    def inject_detections(items: Iterable[dict]) -> list[SymbolDetection]:
        return [SymbolDetection(**x) for x in items]
