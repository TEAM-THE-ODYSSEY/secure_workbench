from __future__ import annotations
from typing import Any, Iterable
from .models import OCRText

class OCRAdapter:
    """PaddleOCR adapter with an injection path for deterministic testing."""
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._ocr = None

    def _load(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=True,
                    lang=self.lang,
                    enable_mkldnn=False
                )
                self._is_rapid = False
            except (ImportError, Exception):
                from rapidocr_onnxruntime import RapidOCR
                self._ocr = RapidOCR()
                self._is_rapid = True
        return self._ocr

    def detect(self, image: Any) -> list[OCRText]:
        ocr = self._load()
        if getattr(self, "_is_rapid", False):
            result, _ = ocr(image)
            out = []
            if result:
                for item in result:
                    box, text, score = item[0], item[1], item[2]
                    min_x = min(p[0] for p in box)
                    min_y = min(p[1] for p in box)
                    max_x = max(p[0] for p in box)
                    max_y = max(p[1] for p in box)
                    out.append(OCRText(
                        text=str(text).strip(),
                        bbox=(float(min_x), float(min_y), float(max_x), float(max_y)),
                        confidence=float(score)
                    ))
            return out

        result = ocr.predict(image)
        out = []
        for page in result:
            data = page.json if hasattr(page, "json") else page
            # PaddleOCR versions differ; normalize common JSON shape.
            if isinstance(data, str):
                import json
                data = json.loads(data)
            data = data.get("res", data) if isinstance(data, dict) else {}
            texts = data.get("rec_texts", [])
            scores = data.get("rec_scores", [])
            boxes = data.get("rec_boxes", [])
            for i, text in enumerate(texts):
                b = boxes[i]
                out.append(OCRText(
                    text=str(text).strip(),
                    bbox=(float(b[0]), float(b[1]), float(b[2]), float(b[3])),
                    confidence=float(scores[i]) if i < len(scores) else 0.0
                ))
        return out

    @staticmethod
    def inject_text(items: Iterable[dict]) -> list[OCRText]:
        return [OCRText(**x) for x in items]
