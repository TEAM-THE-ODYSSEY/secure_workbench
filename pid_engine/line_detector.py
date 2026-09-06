from __future__ import annotations

from typing import Any, Iterable
import math

from .models import LineDetection


class LineDetector:
    """
    P&ID process-line detector.

    Pipeline:

        Edge Detection
             ↓
        Morphological Cleanup
             ↓
        Hough Line Detection
             ↓
        Orientation Filtering
             ↓
        Border/Layout Filtering
             ↓
        Short-Line Filtering
             ↓
        Collinear Line Merging
             ↓
        Duplicate Removal
             ↓
        Line Classification

    Important:
        A detected line is still only a geometric candidate.
        This class does NOT claim that every candidate is a
        physical process pipe.
    """

    def __init__(
        self,
        threshold: int = 60,
        min_line_length: int = 50,
        max_line_gap: int = 12,
        angle_tolerance: float = 8.0,

        # Layout filtering
        border_margin: int = 8,
        border_length_ratio: float = 0.80,
        layout_length_ratio: float = 0.92,

        # Collinear merging
        merge_angle_tolerance: float = 5.0,
        merge_distance: float = 8.0,
        merge_gap: float = 35.0,

    ):
        self.threshold = threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.angle_tolerance = angle_tolerance

        self.border_margin = border_margin
        self.border_length_ratio = border_length_ratio
        self.layout_length_ratio = layout_length_ratio

        self.merge_angle_tolerance = merge_angle_tolerance
        self.merge_distance = merge_distance
        self.merge_gap = merge_gap

    # =========================================================
    # GEOMETRY
    # =========================================================

    @staticmethod
    def line_length(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:

        return math.hypot(
            x2 - x1,
            y2 - y1,
        )

    @staticmethod
    def line_angle(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> float:

        angle = math.degrees(
            math.atan2(
                y2 - y1,
                x2 - x1,
            )
        )

        if angle < 0:
            angle += 180

        return angle

    # =========================================================
    # ORIENTATION
    # =========================================================

    def is_structural_line(
        self,
        angle: float,
    ) -> bool:
        """
        Keep mostly horizontal and vertical lines.
        """

        horizontal = (
            angle <= self.angle_tolerance
            or
            angle >= 180 - self.angle_tolerance
        )

        vertical = (
            abs(angle - 90)
            <= self.angle_tolerance
        )

        return horizontal or vertical

    # =========================================================
    # BORDER / LAYOUT FILTERING
    # =========================================================

    def _touches_image_border(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: int,
        height: int,
    ) -> bool:

        margin = self.border_margin

        return (
            x1 <= margin
            or x2 <= margin
            or y1 <= margin
            or y2 <= margin
            or x1 >= width - 1 - margin
            or x2 >= width - 1 - margin
            or y1 >= height - 1 - margin
            or y2 >= height - 1 - margin
        )

    def _is_page_layout_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: int,
        height: int,
    ) -> bool:
        """
        Detect lines that are probably page/layout boundaries.

        We remove:
            1. Lines spanning almost the whole image.
            2. Very long lines touching the image border.
        """

        length = self.line_length(
            x1,
            y1,
            x2,
            y2,
        )

        angle = self.line_angle(
            x1,
            y1,
            x2,
            y2,
        )

        horizontal = (
            angle <= self.angle_tolerance
            or
            angle >= 180 - self.angle_tolerance
        )

        vertical = (
            abs(angle - 90)
            <= self.angle_tolerance
        )

        # Almost entire image width
        if horizontal:

            ratio = length / max(width, 1)

            if ratio >= self.layout_length_ratio:
                return True

        # Almost entire image height
        if vertical:

            ratio = length / max(height, 1)

            if ratio >= self.layout_length_ratio:
                return True

        # Very long line touching page border
        if self._touches_image_border(
            x1,
            y1,
            x2,
            y2,
            width,
            height,
        ):

            if horizontal:

                ratio = length / max(width, 1)

                if ratio >= self.border_length_ratio:
                    return True

            if vertical:

                ratio = length / max(height, 1)

                if ratio >= self.border_length_ratio:
                    return True

        return False

    # =========================================================
    # LINE DISTANCE
    # =========================================================

    @staticmethod
    def _point_line_distance(
        point,
        line,
    ):
        """
        Perpendicular distance from a point to an infinite line.
        """

        px, py = point

        x1, y1, x2, y2 = line

        dx = x2 - x1
        dy = y2 - y1

        denominator = math.hypot(
            dx,
            dy,
        )

        if denominator == 0:
            return float("inf")

        return abs(
            dy * px
            -
            dx * py
            +
            x2 * y1
            -
            y2 * x1
        ) / denominator

    # =========================================================
    # LINE ORIENTATION
    # =========================================================

    @staticmethod
    def _angle_difference(
        angle_a,
        angle_b,
    ):
        """
        Difference between two line orientations.

        Lines are treated as undirected, therefore
        0 degrees and 180 degrees are equivalent.
        """

        difference = abs(
            angle_a - angle_b
        )

        return min(
            difference,
            180 - difference,
        )

    # =========================================================
    # COLLINEAR CHECK
    # =========================================================

    def _are_collinear(
        self,
        line_a,
        line_b,
    ):
        """
        Determine whether two line segments belong to the
        same horizontal/vertical physical line.
        """

        ax1, ay1, ax2, ay2 = line_a
        bx1, by1, bx2, by2 = line_b

        angle_a = self.line_angle(
            ax1,
            ay1,
            ax2,
            ay2,
        )

        angle_b = self.line_angle(
            bx1,
            by1,
            bx2,
            by2,
        )

        # -----------------------------------------------------
        # 1. Similar orientation
        # -----------------------------------------------------

        if (
            self._angle_difference(
                angle_a,
                angle_b,
            )
            >
            self.merge_angle_tolerance
        ):
            return False

        # -----------------------------------------------------
        # 2. Similar position
        # -----------------------------------------------------

        distance_1 = self._point_line_distance(
            (bx1, by1),
            line_a,
        )

        distance_2 = self._point_line_distance(
            (bx2, by2),
            line_a,
        )

        if (
            distance_1 > self.merge_distance
            or
            distance_2 > self.merge_distance
        ):
            return False

        return True

    # =========================================================
    # SEGMENT GAP
    # =========================================================

    def _segment_gap(
        self,
        line_a,
        line_b,
    ):
        """
        Estimate the gap between two approximately collinear
        line segments.
        """

        ax1, ay1, ax2, ay2 = line_a
        bx1, by1, bx2, by2 = line_b

        angle = self.line_angle(
            ax1,
            ay1,
            ax2,
            ay2,
        )

        # -----------------------------------------------------
        # Horizontal
        # -----------------------------------------------------

        if (
            angle <= self.angle_tolerance
            or
            angle >= 180 - self.angle_tolerance
        ):

            a_min = min(ax1, ax2)
            a_max = max(ax1, ax2)

            b_min = min(bx1, bx2)
            b_max = max(bx1, bx2)

            if a_max < b_min:
                return b_min - a_max

            if b_max < a_min:
                return a_min - b_max

            return 0.0

        # -----------------------------------------------------
        # Vertical
        # -----------------------------------------------------

        a_min = min(ay1, ay2)
        a_max = max(ay1, ay2)

        b_min = min(by1, by2)
        b_max = max(by1, by2)

        if a_max < b_min:
            return b_min - a_max

        if b_max < a_min:
            return a_min - b_max

        return 0.0

    # =========================================================
    # MERGE TWO LINES
    # =========================================================

    def _merge_two_lines(
        self,
        line_a,
        line_b,
    ):
        """
        Merge two approximately collinear segments.
        """

        ax1, ay1, ax2, ay2 = line_a
        bx1, by1, bx2, by2 = line_b

        angle = self.line_angle(
            ax1,
            ay1,
            ax2,
            ay2,
        )

        # -----------------------------------------------------
        # Horizontal
        # -----------------------------------------------------

        if (
            angle <= self.angle_tolerance
            or
            angle >= 180 - self.angle_tolerance
        ):

            x_values = [
                ax1,
                ax2,
                bx1,
                bx2,
            ]

            y_values = [
                ay1,
                ay2,
                by1,
                by2,
            ]

            min_x = min(x_values)
            max_x = max(x_values)

            mean_y = sum(y_values) / len(y_values)

            return (
                min_x,
                mean_y,
                max_x,
                mean_y,
            )

        # -----------------------------------------------------
        # Vertical
        # -----------------------------------------------------

        x_values = [
            ax1,
            ax2,
            bx1,
            bx2,
        ]

        y_values = [
            ay1,
            ay2,
            by1,
            by2,
        ]

        min_y = min(y_values)
        max_y = max(y_values)

        mean_x = sum(x_values) / len(x_values)

        return (
            mean_x,
            min_y,
            mean_x,
            max_y,
        )

    # =========================================================
    # COLLINEAR MERGING
    # =========================================================

    def _merge_collinear_lines(
        self,
        lines,
    ):
        """
        Merge nearby collinear Hough segments.

        Example:

            ───────
                   ───────
                          ─────

        becomes:

            ─────────────────────

        This reduces Hough fragmentation before topology.
        """

        if not lines:
            return []

        merged = list(lines)

        changed = True

        while changed:

            changed = False

            result = []

            used = set()

            for i in range(len(merged)):

                if i in used:
                    continue

                current = merged[i]

                for j in range(
                    i + 1,
                    len(merged),
                ):

                    if j in used:
                        continue

                    candidate = merged[j]

                    # -----------------------------------------
                    # Check collinearity
                    # -----------------------------------------

                    if not self._are_collinear(
                        current,
                        candidate,
                    ):
                        continue

                    # -----------------------------------------
                    # Check gap
                    # -----------------------------------------

                    gap = self._segment_gap(
                        current,
                        candidate,
                    )

                    if gap > self.merge_gap:
                        continue

                    # -----------------------------------------
                    # Merge
                    # -----------------------------------------

                    current = self._merge_two_lines(
                        current,
                        candidate,
                    )

                    used.add(j)

                    changed = True

                result.append(current)
                used.add(i)

            merged = result

        return merged

    # =========================================================
    # DUPLICATE REMOVAL
    # =========================================================

    @staticmethod
    def _similar_line(
        a,
        b,
        distance_threshold: float = 6,
    ) -> bool:

        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b

        angle_a = math.degrees(
            math.atan2(
                ay2 - ay1,
                ax2 - ax1,
            )
        )

        angle_b = math.degrees(
            math.atan2(
                by2 - by1,
                bx2 - bx1,
            )
        )

        angle_a = abs(angle_a) % 180
        angle_b = abs(angle_b) % 180

        if abs(
            angle_a - angle_b
        ) > 5:

            return False

        d1 = math.hypot(
            ax1 - bx1,
            ay1 - by1,
        )

        d2 = math.hypot(
            ax2 - bx2,
            ay2 - by2,
        )

        d3 = math.hypot(
            ax1 - bx2,
            ay1 - by2,
        )

        d4 = math.hypot(
            ax2 - bx1,
            ay2 - by1,
        )

        return (
            (
                d1 <= distance_threshold
                and
                d2 <= distance_threshold
            )
            or
            (
                d3 <= distance_threshold
                and
                d4 <= distance_threshold
            )
        )

    def _remove_duplicates(
        self,
        lines,
    ):

        unique = []

        for line in lines:

            duplicate = False

            for existing in unique:

                if self._similar_line(
                    line,
                    existing,
                ):

                    duplicate = True
                    break

            if not duplicate:
                unique.append(line)

        return unique

    # =========================================================
    # LINE CLASSIFICATION
    # =========================================================

    def _classify_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: int,
        height: int,
    ) -> str:

        if self._is_page_layout_line(
            x1,
            y1,
            x2,
            y2,
            width,
            height,
        ):

            return "layout_candidate"

        return "process_candidate"

    # =========================================================
    # CONFIDENCE
    # =========================================================

    def _line_confidence(
        self,
        length: float,
        line_type: str,
    ) -> float:

        if line_type == "layout_candidate":
            return 0.20

        confidence = 0.50

        confidence += min(
            0.40,
            length / 1000.0,
        )

        return min(
            0.95,
            confidence,
        )

    # =========================================================
    # MAIN DETECTOR
    # =========================================================

    def detect(
        self,
        gray: Any,
    ) -> list[LineDetection]:

        import cv2
        import numpy as np

        if gray is None:
            return []

        height, width = gray.shape[:2]

        # -----------------------------------------------------
        # 1. Edge Detection
        # -----------------------------------------------------

        edges = cv2.Canny(
            gray,
            50,
            150,
            apertureSize=3,
        )

        # -----------------------------------------------------
        # 2. Morphological cleanup
        # -----------------------------------------------------

        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (15, 1),
        )

        vertical_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (1, 15),
        )

        horizontal = cv2.morphologyEx(
            edges,
            cv2.MORPH_CLOSE,
            horizontal_kernel,
        )

        vertical = cv2.morphologyEx(
            edges,
            cv2.MORPH_CLOSE,
            vertical_kernel,
        )

        structural_edges = cv2.bitwise_or(
            horizontal,
            vertical,
        )

        # -----------------------------------------------------
        # 3. Hough detection
        # -----------------------------------------------------

        lines = cv2.HoughLinesP(
            structural_edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap,
        )

        if lines is None:
            return []

        candidates = []

        # -----------------------------------------------------
        # 4. Geometric filtering
        # -----------------------------------------------------

        for item in lines[:, 0]:

            x1, y1, x2, y2 = map(
                float,
                item,
            )

            length = self.line_length(
                x1,
                y1,
                x2,
                y2,
            )

            if length < self.min_line_length:
                continue

            angle = self.line_angle(
                x1,
                y1,
                x2,
                y2,
            )

            if not self.is_structural_line(
                angle
            ):
                continue

            line_type = self._classify_line(
                x1,
                y1,
                x2,
                y2,
                width,
                height,
            )

            # Do not pass layout lines forward.
            if line_type == "layout_candidate":
                continue

            candidates.append(
                (
                    x1,
                    y1,
                    x2,
                    y2,
                )
            )

        # -----------------------------------------------------
        # 5. Merge collinear segments
        # -----------------------------------------------------

        candidates = self._merge_collinear_lines(
            candidates
        )

        # -----------------------------------------------------
        # 6. Remove duplicates
        # -----------------------------------------------------

        candidates = self._remove_duplicates(
            candidates
        )

        # -----------------------------------------------------
        # 7. Convert to LineDetection
        # -----------------------------------------------------

        output = []

        for i, (
            x1,
            y1,
            x2,
            y2,
        ) in enumerate(
            candidates,
            start=1,
        ):

            length = self.line_length(
                x1,
                y1,
                x2,
                y2,
            )

            confidence = self._line_confidence(
                length,
                "process_candidate",
            )

            output.append(
                LineDetection(
                    line_id=f"line{i}",
                    points=[
                        (x1, y1),
                        (x2, y2),
                    ],
                    line_type="process_candidate",
                    confidence=confidence,
                )
            )

        return output

    # =========================================================
    # TEST INJECTION
    # =========================================================

    @staticmethod
    def inject_lines(
        items: Iterable[dict],
    ) -> list[LineDetection]:

        return [
            LineDetection(**x)
            for x in items
        ]