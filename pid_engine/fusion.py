from __future__ import annotations

import math
import re

from .models import SymbolDetection, OCRText, FusedObject


# ---------------------------------------------------------
# Regular expressions for common P&ID text types
# ---------------------------------------------------------

# Examples:
# FV-1401
# FV 1401
# FI-1405
# P-302
# V-101
TAG_RE = re.compile(
    r"^[A-Za-z]{1,5}[- ]?\d+[A-Za-z0-9-]*$",
    re.IGNORECASE
)

# Instrument prefix such as:
# FI, FV, FIC, FT, FE, SP, PI, etc.
INSTRUMENT_PREFIX_RE = re.compile(
    r"^[A-Za-z]{1,5}$",
    re.IGNORECASE
)

# Pure number:
# 2
# 1401
# 300
PURE_NUMBER_RE = re.compile(
    r"^\d+(?:\.\d+)?$"
)

# Pipe size:
# 2"
# 6"
# 1/2"
# 1 1/2"
PIPE_SIZE_RE = re.compile(
    r'^\d+(?:\s+\d+/\d+|/\d+)?["”]$'
)

# Reducer / size notation:
# 6"x10"
# 6”x10”
REDUCER_SIZE_RE = re.compile(
    r'^\d+(?:\.\d+)?["”]?\s*[xX×]\s*\d+(?:\.\d+)?["”]?$'
)

# Pipe line identifiers:
# 6"-P-302-1409-A22K-IC
# 1 1/2"-P-302-1416-A22K-IC
PIPE_LINE_RE = re.compile(
    r'^\s*'
    r'\d+(?:\s+\d+/\d+|/\d+)?'
    r'["”]?'
    r'\s*-\s*'
    r'[A-Za-z]+'
    r'-\d+'
    r'-\d+'
    r'-[A-Za-z0-9]+'
    r'(?:-[A-Za-z0-9]+)*'
    r'\s*$',
    re.IGNORECASE
)

NOTE_RE = re.compile(
    r"^\(?\s*NOTE[- ]?\s*\d+\s*\)?$",
    re.IGNORECASE
)

DIAGRAM_RE = re.compile(
    r"^DIAG\s+[A-Za-z0-9-]+$",
    re.IGNORECASE
)

PRESSURE_CLASS_RE = re.compile(
    r"^\d+#$"
)

# Common P&ID instrument prefixes.
# This is deliberately conservative.
INSTRUMENT_PREFIXES = {
    "FI",
    "FV",
    "FIC",
    "FT",
    "FE",
    "PI",
    "PT",
    "PE",
    "PIC",
    "TI",
    "TT",
    "TE",
    "TIC",
    "LI",
    "LT",
    "LE",
    "LIC",
    "LA",
    "LC",
    "SP",
}


# ---------------------------------------------------------
# Geometry
# ---------------------------------------------------------

def center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def point_to_box_distance(point, bbox):
    x, y = point
    x1, y1, x2, y2 = bbox

    dx = max(x1 - x, 0, x - x2)
    dy = max(y1 - y, 0, y - y2)

    return math.hypot(dx, dy)


# ---------------------------------------------------------
# Text classification
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize OCR text without aggressively changing content.
    """

    text = text.strip()

    # OCR sometimes produces curly quotes.
    text = text.replace("”", '"').replace("“", '"')

    # Normalize repeated spaces.
    text = re.sub(r"\s+", " ", text)

    return text


def classify_text(text: str) -> str:
    """
    Classify OCR text into a P&ID-oriented category.
    """

    text = normalize_text(text)

    if not text:
        return "EMPTY"

    upper = text.upper()

    if NOTE_RE.match(text):
        return "NOTE"

    if DIAGRAM_RE.match(text):
        return "DIAGRAM_REFERENCE"

    if PIPE_LINE_RE.match(text):
        return "PIPE_LINE"

    if REDUCER_SIZE_RE.match(text):
        return "REDUCER_SIZE"

    if PIPE_SIZE_RE.match(text):
        return "PIPE_SIZE"

    if PRESSURE_CLASS_RE.match(text):
        return "PRESSURE_CLASS"

    if PURE_NUMBER_RE.match(text):
        return "NUMBER"

    if upper in INSTRUMENT_PREFIXES:
        return "INSTRUMENT_PREFIX"

    if TAG_RE.match(text):
        return "TAG"

    return "OTHER"


# ---------------------------------------------------------
# Instrument grouping
# ---------------------------------------------------------

def find_instrument_tag(
    prefix_index: int,
    prefix_text: OCRText,
    texts: list[OCRText],
    used: set[int],
    max_distance: float = 80.0,
):
    """
    Find a nearby numeric OCR result for an instrument prefix.

    Example:

        FV
        1401

    becomes:

        FV-1401
    """

    prefix_center = center(prefix_text.bbox)

    best = None
    best_distance = float("inf")

    for i, txt in enumerate(texts):

        if i == prefix_index:
            continue

        if i in used:
            continue

        category = classify_text(txt.text)

        if category != "NUMBER":
            continue

        distance = math.hypot(
            prefix_center[0] - center(txt.bbox)[0],
            prefix_center[1] - center(txt.bbox)[1],
        )

        if distance <= max_distance and distance < best_distance:
            best_distance = distance
            best = (i, txt)

    if best is None:
        return None

    return best[0], best[1], best_distance


# ---------------------------------------------------------
# Spatial Fusion
# ---------------------------------------------------------

class SpatialFusion:
    """
    P&ID-aware spatial fusion.

    Important difference from the original implementation:

    The nearest OCR text is NOT automatically treated as
    an object's tag.

    Text must first pass P&ID-specific classification.

    This prevents examples such as:

        Ball Valve + "2""

    from becoming:

        Ball Valve tag = 2"
    """

    def __init__(
        self,
        max_distance: float = 140.0,
        tag_distance: float = 120.0,
        instrument_distance: float = 100.0,
    ):
        self.max_distance = max_distance
        self.tag_distance = tag_distance
        self.instrument_distance = instrument_distance

    def fuse(
        self,
        symbols: list[SymbolDetection],
        texts: list[OCRText],
    ) -> list[FusedObject]:

        # -------------------------------------------------
        # Pre-classify OCR
        # -------------------------------------------------

        classified = []

        for i, txt in enumerate(texts):

            text = normalize_text(txt.text)
            category = classify_text(text)

            classified.append(
                {
                    "index": i,
                    "text": text,
                    "category": category,
                    "ocr": txt,
                }
            )

        # -------------------------------------------------
        # Group instrument prefixes with nearby numbers
        # -------------------------------------------------

        used_text = set()

        instrument_groups = []

        for item in classified:

            i = item["index"]

            if i in used_text:
                continue

            if item["category"] != "INSTRUMENT_PREFIX":
                continue

            prefix = item["text"].upper()

            if prefix not in INSTRUMENT_PREFIXES:
                continue

            match = find_instrument_tag(
                prefix_index=i,
                prefix_text=item["ocr"],
                texts=texts,
                used=used_text,
                max_distance=self.instrument_distance,
            )

            if match:

                number_index, number_text, distance = match

                combined_tag = f"{prefix}-{normalize_text(number_text.text)}"

                instrument_groups.append(
                    {
                        "prefix_index": i,
                        "number_index": number_index,
                        "tag": combined_tag,
                        "confidence": min(
                            float(item["ocr"].confidence),
                            float(number_text.confidence),
                        ),
                        "distance": distance,
                        "bbox": (
                            min(
                                item["ocr"].bbox[0],
                                number_text.bbox[0],
                            ),
                            min(
                                item["ocr"].bbox[1],
                                number_text.bbox[1],
                            ),
                            max(
                                item["ocr"].bbox[2],
                                number_text.bbox[2],
                            ),
                            max(
                                item["ocr"].bbox[3],
                                number_text.bbox[3],
                            ),
                        ),
                    }
                )

                used_text.add(i)
                used_text.add(number_index)

        # -------------------------------------------------
        # Build candidates
        # -------------------------------------------------

        candidates = []

        # Normal tag candidates.
        for item in classified:

            if item["index"] in used_text:
                continue

            if item["category"] == "TAG":

                candidates.append(
                    {
                        "index": item["index"],
                        "text": item["text"],
                        "category": "TAG",
                        "confidence": float(item["ocr"].confidence),
                        "bbox": item["ocr"].bbox,
                    }
                )

        # Instrument groups are also tag candidates.
        for group in instrument_groups:

            candidates.append(
                {
                    "index": group["prefix_index"],
                    "text": group["tag"],
                    "category": "INSTRUMENT_TAG",
                    "confidence": group["confidence"],
                    "bbox": group["bbox"],
                }
            )

        # -------------------------------------------------
        # Associate symbols with valid tag candidates
        # -------------------------------------------------

        result = []

        assigned_candidates = set()

        for sym in symbols:

            best = None
            best_score = -1.0

            for candidate_index, candidate in enumerate(candidates):

                if candidate_index in assigned_candidates:
                    continue

                distance = point_to_box_distance(
                    center(sym.bbox),
                    candidate["bbox"],
                )

                if distance > self.tag_distance:
                    continue

                proximity = max(
                    0.0,
                    1.0 - distance / self.tag_distance,
                )

                text_conf = candidate["confidence"]

                # Valid P&ID tag gets strong weight.
                score = (
                    0.60 * proximity
                    + 0.40 * text_conf
                )

                if score > best_score:

                    best_score = score

                    best = (
                        candidate_index,
                        candidate,
                        distance,
                    )

            tag = None
            ocr_conf = 0.0

            evidence = [
                f"symbol_confidence={sym.confidence:.3f}"
            ]

            # -------------------------------------------------
            # Only assign a tag if we actually found a
            # tag-like candidate.
            # -------------------------------------------------

            if best is not None:

                candidate_index, candidate, distance = best

                # Require reasonable association confidence.
                if best_score >= 0.45:

                    assigned_candidates.add(candidate_index)

                    tag = candidate["text"]

                    ocr_conf = candidate["confidence"]

                    evidence.append(
                        f"tag_type={candidate['category']}"
                    )

                    evidence.append(
                        f"tag_distance={distance:.2f}px"
                    )

                    evidence.append(
                        f"tag_confidence={ocr_conf:.3f}"
                    )

                    evidence.append(
                        f"association_score={best_score:.3f}"
                    )

            # -------------------------------------------------
            # If no valid tag exists, leave tag as None.
            # -------------------------------------------------

            result.append(
                FusedObject(
                    object_id=sym.object_id,
                    object_type=sym.object_type,
                    tag=tag,
                    bbox=sym.bbox,
                    symbol_confidence=sym.confidence,
                    ocr_confidence=ocr_conf,
                    association_confidence=max(
                        0.0,
                        min(
                            1.0,
                            best_score if tag is not None else 0.0,
                        ),
                    ),
                    evidence=evidence,
                )
            )

        return result