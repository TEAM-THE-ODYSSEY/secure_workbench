from __future__ import annotations

import math

from .models import FusedObject, LineDetection, Relationship


def point_segment_distance(p, a, b):
    """Minimum distance between point p and line segment a-b."""
    px, py = p
    ax, ay = a
    bx, by = b

    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)

    t = (
        (px - ax) * dx + (py - ay) * dy
    ) / (dx * dx + dy * dy)

    t = max(0.0, min(1.0, t))

    closest_x = ax + t * dx
    closest_y = ay + t * dy

    return math.hypot(
        px - closest_x,
        py - closest_y,
    )


class TopologyEngine:

    def __init__(
        self,
        attach_distance: float = 18.0,
        max_object_distance: float = 500.0,
        min_line_confidence: float = 0.55,
    ):
        self.attach_distance = attach_distance
        self.max_object_distance = max_object_distance
        self.min_line_confidence = min_line_confidence

    # ---------------------------------------------------------
    # LINE GEOMETRY
    # ---------------------------------------------------------

    def _line_points(self, line):
        """
        Extract the two endpoints of a detected line.
        """
        if not line.points:
            return None

        if len(line.points) < 2:
            return None

        return (
            tuple(line.points[0]),
            tuple(line.points[-1]),
        )

    def _line_length(self, line):
        points = self._line_points(line)

        if points is None:
            return 0.0

        a, b = points

        return math.hypot(
            b[0] - a[0],
            b[1] - a[1],
        )

    def _line_angle(self, line):
        points = self._line_points(line)

        if points is None:
            return None

        a, b = points

        dx = b[0] - a[0]
        dy = b[1] - a[1]

        angle = math.degrees(
            math.atan2(dy, dx)
        )

        return angle

    def _is_horizontal_or_vertical(
        self,
        line,
        tolerance=10.0,
    ):
        angle = self._line_angle(line)

        if angle is None:
            return False

        angle = abs(angle)

        horizontal = (
            angle <= tolerance
            or angle >= 180.0 - tolerance
        )

        vertical = (
            abs(angle - 90.0) <= tolerance
        )

        return horizontal or vertical

    # ---------------------------------------------------------
    # SEGMENT INTERSECTION
    # ---------------------------------------------------------

    def _segments_intersect(self, a, b, c, d):
        """
        Check whether line segment A-B intersects
        line segment C-D.
        """

        def orientation(p, q, r):
            value = (
                (q[1] - p[1]) * (r[0] - q[0])
                -
                (q[0] - p[0]) * (r[1] - q[1])
            )

            if abs(value) < 1e-9:
                return 0

            if value > 0:
                return 1

            return 2

        def on_segment(p, q, r):
            return (
                min(p[0], r[0])
                <= q[0]
                <= max(p[0], r[0])
                and
                min(p[1], r[1])
                <= q[1]
                <= max(p[1], r[1])
            )

        o1 = orientation(a, b, c)
        o2 = orientation(a, b, d)
        o3 = orientation(c, d, a)
        o4 = orientation(c, d, b)

        # General intersection
        if o1 != o2 and o3 != o4:
            return True

        # Collinear cases
        if o1 == 0 and on_segment(a, c, b):
            return True

        if o2 == 0 and on_segment(a, d, b):
            return True

        if o3 == 0 and on_segment(c, a, d):
            return True

        if o4 == 0 and on_segment(c, b, d):
            return True

        return False

    def _segment_intersects_bbox(
        self,
        a,
        b,
        bbox,
    ):
        """
        Check whether line segment A-B intersects
        an object's bounding box.
        """

        x1, y1, x2, y2 = bbox

        min_x = min(x1, x2)
        max_x = max(x1, x2)

        min_y = min(y1, y2)
        max_y = max(y1, y2)

        ax, ay = a
        bx, by = b

        # -----------------------------------------------------
        # Quick rejection
        # -----------------------------------------------------

        if max(ax, bx) < min_x:
            return False

        if min(ax, bx) > max_x:
            return False

        if max(ay, by) < min_y:
            return False

        if min(ay, by) > max_y:
            return False

        # -----------------------------------------------------
        # Bounding-box edges
        # -----------------------------------------------------

        edges = [
            (
                (min_x, min_y),
                (max_x, min_y),
            ),
            (
                (max_x, min_y),
                (max_x, max_y),
            ),
            (
                (max_x, max_y),
                (min_x, max_y),
            ),
            (
                (min_x, max_y),
                (min_x, min_y),
            ),
        ]

        # -----------------------------------------------------
        # Check intersection with bbox edges
        # -----------------------------------------------------

        for edge_a, edge_b in edges:

            if self._segments_intersect(
                a,
                b,
                edge_a,
                edge_b,
            ):
                return True

        # -----------------------------------------------------
        # Check if endpoint A is inside bbox
        # -----------------------------------------------------

        if (
            min_x <= ax <= max_x
            and
            min_y <= ay <= max_y
        ):
            return True

        # -----------------------------------------------------
        # Check if endpoint B is inside bbox
        # -----------------------------------------------------

        if (
            min_x <= bx <= max_x
            and
            min_y <= by <= max_y
        ):
            return True

        return False

    # ---------------------------------------------------------
    # OBJECT / LINE DISTANCE
    # ---------------------------------------------------------

    def _line_object_distance(
        self,
        line,
        obj,
    ):
        """
        Calculate the distance between a process line
        and an object bounding box.

        If the line crosses the bounding box,
        distance = 0.
        """

        points = self._line_points(line)

        if points is None:
            return float("inf")

        a, b = points

        # Direct intersection
        if self._segment_intersects_bbox(
            a,
            b,
            obj.bbox,
        ):
            return 0.0

        # Otherwise calculate distance from bbox corners
        x1, y1, x2, y2 = obj.bbox

        corners = [
            (x1, y1),
            (x2, y1),
            (x2, y2),
            (x1, y2),
        ]

        distances = [
            point_segment_distance(
                corner,
                a,
                b,
            )
            for corner in corners
        ]

        return min(distances)

    # ---------------------------------------------------------
    # OBJECT-OBJECT DISTANCE
    # ---------------------------------------------------------

    def _object_distance(
        self,
        obj_a,
        obj_b,
    ):
        """
        Distance between centers of two detected objects.
        """

        ax1, ay1, ax2, ay2 = obj_a.bbox
        bx1, by1, bx2, by2 = obj_b.bbox

        acx = (ax1 + ax2) / 2.0
        acy = (ay1 + ay2) / 2.0

        bcx = (bx1 + bx2) / 2.0
        bcy = (by1 + by2) / 2.0

        return math.hypot(
            acx - bcx,
            acy - bcy,
        )

    # ---------------------------------------------------------
    # BUILD RELATIONSHIPS
    # ---------------------------------------------------------

    def build_relationships(
        self,
        objects,
        lines,
    ):
        relationships = []

        for line in lines:

            # -------------------------------------------------
            # Ignore weak lines
            # -------------------------------------------------

            if line.confidence < self.min_line_confidence:
                continue

            # -------------------------------------------------
            # Ignore diagonal/non-process lines
            # -------------------------------------------------

            if not self._is_horizontal_or_vertical(line):
                continue

            # -------------------------------------------------
            # Find objects attached to this line
            # -------------------------------------------------

            attached = []

            for obj in objects:

                distance = self._line_object_distance(
                    line,
                    obj,
                )

                if distance <= self.attach_distance:

                    attached.append(
                        (
                            obj,
                            distance,
                        )
                    )

            # Need at least two objects
            if len(attached) < 2:
                continue

            # -------------------------------------------------
            # Compare object pairs
            # -------------------------------------------------

            for i in range(len(attached)):

                for j in range(
                    i + 1,
                    len(attached),
                ):

                    obj_a, distance_a = attached[i]
                    obj_b, distance_b = attached[j]

                    object_distance = self._object_distance(
                        obj_a,
                        obj_b,
                    )

                    # Prevent unrelated objects from being
                    # connected by a very long line.
                    if object_distance > self.max_object_distance:
                        continue

                    # -------------------------------------------------
                    # Confidence
                    # -------------------------------------------------

                    attachment_score = max(
                        0.0,
                        min(
                            1.0,
                            1.0
                            -
                            (
                                distance_a
                                +
                                distance_b
                            )
                            /
                            (
                                2.0
                                *
                                self.attach_distance
                            ),
                        ),
                    )

                    distance_score = max(
                        0.0,
                        min(
                            1.0,
                            1.0
                            -
                            object_distance
                            /
                            self.max_object_distance,
                        ),
                    )

                    confidence = (
                        0.45
                        * line.confidence
                        +
                        0.40
                        * attachment_score
                        +
                        0.15
                        * distance_score
                    )

                    relationships.append(
                        Relationship(
                            source=obj_a.object_id,
                            target=obj_b.object_id,
                            relationship="connected_by_line",
                            pipe=line.line_id,
                            confidence=float(
                                max(
                                    0.0,
                                    min(
                                        1.0,
                                        confidence,
                                    ),
                                )
                            ),
                            evidence=[
                                f"line={line.line_id}",
                                (
                                    "attach_distances="
                                    f"{distance_a:.2f},"
                                    f"{distance_b:.2f}"
                                ),
                                (
                                    "object_distance="
                                    f"{object_distance:.2f}"
                                ),
                            ],
                        )
                    )

        # -----------------------------------------------------
        # Remove duplicate physical relationships
        # -----------------------------------------------------

        unique = {}

        for relationship in relationships:

            object_pair = tuple(
                sorted(
                    [
                        relationship.source,
                        relationship.target,
                    ]
                )
            )

            key = (
                object_pair,
                relationship.pipe,
            )

            # Keep strongest relationship
            if (
                key not in unique
                or
                relationship.confidence
                >
                unique[key].confidence
            ):
                unique[key] = relationship

        return list(unique.values())